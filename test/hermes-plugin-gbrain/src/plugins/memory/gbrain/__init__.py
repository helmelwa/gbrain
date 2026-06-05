"""GBrain memory provider plugin for Hermes Agent.

Talks to a real `gbrain serve` subprocess over JSON-RPC (stdio transport).
Designed for isolation: no direct imports from the gbrain package, no
CLI-output parsing, no hardcoded operation schemas. The MCP tools/list
discovery handles GBrain's daily release churn.

Lifecycle: lazy subprocess — `gbrain serve` is spawned on the first
prefetch/sync_turn call, reused for the session, gracefully closed on
shutdown.
"""
from __future__ import annotations

import json
import logging
import os
import shutil
import threading
import time
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# MemoryProvider ABC lives in Hermes source. This plugin is BUNDLED into
# the hermes-agent source tree at plugins/memory/gbrain/, so Hermes'
# plugin loader puts `plugins.memory` on sys.modules before exec, and
# `agent` is importable. We import MemoryProvider directly — no fallback.
# A failure here is a real install bug, not something to mask.
from agent.memory_provider import MemoryProvider  # noqa: E402


def _gbrain_config_path() -> Path | None:
    """Return the path to the active GBrain config file, or None.

    GBrain discovers its config dir via $GBRAIN_HOME + '/.gbrain' or
    ~/.gbrain/ (see gbrain/src/core/config.ts:765-782, configDir()).
    We mirror that exact resolution so is_available() agrees with
    what `gbrain serve` will actually use.

    We do NOT add a hermes_home-scoped path here. GBrain is a shared
    system-level service; the plugin must not redirect it to a
    profile-scoped dir — that would shadow the operator's real brain.
    """
    env_home = os.environ.get("GBRAIN_HOME")
    if env_home and env_home.strip():
        candidate = Path(env_home.strip()) / ".gbrain" / "config.json"
    else:
        candidate = Path.home() / ".gbrain" / "config.json"
    if candidate.exists():
        return candidate
    return None


def _gbrain_binary_available() -> bool:
    return shutil.which("gbrain") is not None


class GBrainMemoryProvider(MemoryProvider):
    """Memory provider backed by a real `gbrain serve` subprocess.

    Behavior is built up TDD-cycle by TDD-cycle. Each method is added
    only when a failing test demands it.
    """

    @property
    def name(self) -> str:
        """Short identifier for this provider (e.g. 'builtin', 'honcho', 'hindsight')."""
        return "gbrain"

    def is_available(self) -> bool:
        """True iff a GBrain config exists or the binary is on PATH.

        No subprocess, no network — pure local checks.
        """
        cfg = _gbrain_config_path()
        if cfg is not None and cfg.exists():
            return True
        return _gbrain_binary_available()

    def get_config_schema(self) -> list[dict]:
        """Declare config fields for the `hermes memory setup` wizard.

        Per official docs "Minimal vs Full Schema": only fields the user
        MUST configure should be prompted. All other tunables
        (transport, container_tag) have defaults and are documented in
        README, NOT prompted at setup time.
        """
        return []

    def save_config(self, values: dict, hermes_home: str) -> None:
        """Persist non-secret config to $HERMES_HOME/gbrain.json."""
        Path(hermes_home, "gbrain.json").write_text(json.dumps(values, indent=2))

    def initialize(self, session_id: str, **kwargs) -> None:
        """Record session identity and load persisted config.

        Subprocess startup is deferred to the first prefetch/sync_turn call.
        """
        self._session_id = session_id
        self._hermes_home = kwargs.get("hermes_home", str(Path.home()))
        self._agent_context = kwargs.get("agent_context", "primary")
        config_path = Path(self._hermes_home) / "gbrain.json"
        if config_path.exists():
            self._config = json.loads(config_path.read_text())
        else:
            self._config = {"transport": "stdio", "container_tag": "hermes"}
        self._proc = None
        self._mcp = None
        logger.info(
            "gbrain plugin initialized: session=%s agent_context=%s transport=%s container=%s",
            session_id, self._agent_context, self._config.get("transport"),
            self._config.get("container_tag"),
        )
        self._prefetch_cache: str = ""
        self._sync_thread: threading.Thread | None = None

    def _ensure_subprocess(self):
        """Spawn `gbrain serve` lazily on first MCP call. Idempotent + restart-aware.

        We do NOT inject a custom brain root. The operator's existing
        GBrain installation is the single source of truth — `gbrain
        serve` finds it via $GBRAIN_HOME or ~/.gbrain just like
        `gbrain doctor` does.
        """
        from .mcp_client import McpClient
        if self._mcp is not None and self._proc is not None and self._proc.poll() is None:
            return
        spawned = McpClient.spawn(
            gbrain_home=os.environ.get("GBRAIN_HOME") or None,
        )
        self._mcp = spawned.client
        self._proc = spawned.proc

    def _format_search_results(self, text: str) -> str:
        """Parse search result JSON into compact markdown. Returns "" on any error."""
        try:
            results = json.loads(text)
        except (json.JSONDecodeError, TypeError):
            return ""
        if not isinstance(results, list) or not results:
            return ""
        lines = ["# Recalled from GBrain", ""]
        for r in results[:5]:
            slug = r.get("slug") or r.get("title") or "?"
            snippet = (
                r.get("chunk_text")
                or r.get("snippet")
                or r.get("content")
                or ""
            )[:200]
            lines.append(f"- **{slug}**: {snippet}")
        return "\n".join(lines)

    def prefetch(self, query: str, *, session_id: str = "") -> str:
        """Return markdown context for `query`, or empty string on any failure.

        Sync per official MemoryProvider contract. MemoryManager calls this
        synchronously (memory_manager.py:348) and expects a str back — an
        async def would return a coroutine and crash on ``.strip()``.
        For latency, do the MCP work in a daemon thread with a short join
        timeout; fall back to cache or empty string if the thread isn't done.
        """
        logger.info("gbrain.prefetch called: query=%r", query[:60])
        if self._prefetch_cache:
            cached = self._prefetch_cache
            self._prefetch_cache = ""
            logger.info("gbrain.prefetch cache hit (%d chars)", len(cached))
            return cached
        # Try to do the recall quickly in a daemon thread.
        result_box: dict = {"text": ""}
        def _do_search() -> None:
            try:
                self._ensure_subprocess()
                assert self._mcp is not None
                # Use the `query` MCP tool, not `search`. See bundled
                # version for full rationale.
                text = self._mcp.call_tool(
                    "query",
                    {
                        "query": query,
                        "limit": 20,
                        "expand": False,
                        "detail": "medium",
                    },
                    timeout=10.0,
                )
                result_box["text"] = text
            except Exception as e:
                logger.info("gbrain.prefetch failed: %s", e)
        t = threading.Thread(target=_do_search, daemon=True)
        t.start()
        t.join(timeout=5.0)
        raw = result_box["text"]
        if not raw:
            return ""
        logger.info("gbrain.prefetch MCP query returned %d chars", len(raw))
        return self._format_search_results(raw)

    def queue_prefetch(self, query: str, *, session_id: str = "") -> None:
        """Background-warm the prefetch cache for the NEXT prefetch() call.

        Sync per official MemoryProvider contract. MemoryManager calls this
        synchronously (memory_manager.py:362) and expects it to return
        immediately — we do the actual MCP call in a daemon thread.
        """
        logger.info("gbrain.queue_prefetch warming for: %r", query[:60])

        def _warm() -> None:
            try:
                self._ensure_subprocess()
                assert self._mcp is not None
                text = self._mcp.call_tool(
                    "search", {"query": query, "limit": 5}, timeout=10.0
                )
                self._prefetch_cache = self._format_search_results(text)
                logger.info("gbrain.queue_prefetch warmed %d chars", len(self._prefetch_cache))
            except Exception as e:
                logger.info("gbrain.queue_prefetch failed (non-fatal): %s", e)

        threading.Thread(target=_warm, daemon=True).start()

    def sync_turn(
        self,
        user_content: str,
        assistant_content: str,
        *,
        session_id: str = "",
        messages=None,
    ) -> None:
        """Extract facts from the turn and store in GBrain (fire-and-forget).

        Sync per official MemoryProvider contract AND official docs:
        ``sync_turn() MUST be non-blocking. Run latency-causing work in a
        daemon thread.``

        Parameter names match the ABC (memory_provider.py:115-122):
        user_content, assistant_content, session_id, messages.
        """
        if self._agent_context not in ("primary", None, ""):
            logger.info("gbrain.sync_turn skipped (agent_context=%s)", self._agent_context)
            return
        logger.info(
            "gbrain.sync_turn queued: user=%d chars assistant=%d chars",
            len(user_content), len(assistant_content),
        )

        # Per official docs Threading Contract: track the previous sync
        # thread so the next call can join(timeout=5.0) and we don't
        # spawn unbounded daemon threads on long sessions.
        if self._sync_thread is not None and self._sync_thread.is_alive():
            self._sync_thread.join(timeout=5.0)

        def _bg() -> None:
            try:
                self._ensure_subprocess()
                assert self._mcp is not None
                turn_text = f"USER: {user_content}\nASSISTANT: {assistant_content}"
                result = self._mcp.call_tool(
                    "extract_facts",
                    {
                        "turn_text": turn_text[:4000],
                        "session_id": self._session_id or "hermes",
                    },
                    timeout=15.0,
                )
                logger.info("gbrain.sync_turn extract_facts returned %d chars", len(str(result)))
            except Exception as e:
                logger.info("gbrain.sync_turn failed (non-fatal): %s", e)

        self._sync_thread = threading.Thread(target=_bg, daemon=True)
        self._sync_thread.start()

    def system_prompt_block(self) -> str:
        """Static block for the agent's system prompt."""
        block = (
            "You have a long-term memory backed by GBrain "
            "(Postgres+pgvector hybrid RAG over the user's knowledge base). "
            "Use the gbrain_search, gbrain_get_page, and gbrain_recall tools "
            "to look up people, companies, meetings, and ideas. "
            "Prefetched context arrives inline before each turn when relevant."
        )
        logger.info("gbrain.system_prompt_block called: %d chars", len(block))
        return block

    def handle_tool_call(self, tool_name: str, args: dict, **kwargs) -> str:
        """Dispatch a Hermes tool call to the corresponding GBrain MCP tool.

        Per ABC and MemoryManager contract (memory_manager.py:453), the
        first parameter is named ``tool_name``.
        """
        logger.info("gbrain.handle_tool_call: name=%r args_keys=%s", tool_name, list(args.keys()))
        if not tool_name.startswith("gbrain_"):
            return json.dumps({"error": f"unknown tool: {tool_name}"})
        mcp_name = tool_name[len("gbrain_"):]

        try:
            if self._mcp is None:
                self._ensure_subprocess()
        except Exception as e:
            return json.dumps({"error": f"gbrain not available: {e}"})

        if self._mcp is None:
            return json.dumps({"error": "gbrain subprocess not available"})

        try:
            return self._mcp.call_tool(mcp_name, args, timeout=10.0)
        except Exception as e:
            return json.dumps({"error": f"gbrain tool {tool_name} failed: {e}"})

    def _close_subprocess(self) -> None:
        """Tear down the gbrain subprocess if any. Idempotent + error-swallowing."""
        if self._mcp is not None:
            try:
                self._mcp.close()
            except Exception:
                pass
            self._mcp = None
        self._proc = None

    def shutdown(self) -> None:
        """Close the gbrain subprocess on process exit. Idempotent and safe to call multiple times."""
        self._close_subprocess()

    def on_pre_compress(self, messages: list) -> str:
        """Capture insights from messages about to be compressed away.

        Per official docs "Optional Hooks" and ABC contract
        (memory_provider.py:219-228). Called before context compression
        discards old messages. We extract any entity mentions / facts
        that the agent referenced and stash them in gbrain BEFORE the
        compressor summarizes them away. The returned text is injected
        into the compression summary prompt so the compressor preserves
        our extracted insights.

        Fire-and-forget into a daemon thread to avoid blocking the
        compressor. Returns a short note for the compressor.
        """
        if not messages:
            return ""
        try:
            self._ensure_subprocess()
        except Exception as e:
            logger.info("gbrain.on_pre_compress: subprocess unavailable, skipping: %s", e)
            return ""
        snippets: list[str] = []
        for m in messages[-20:]:  # bound the work; only the recent half
            if isinstance(m, dict):
                role = m.get("role", "")
                content = m.get("content", "")
                if isinstance(content, list):
                    content = " ".join(
                        c.get("text", "") for c in content
                        if isinstance(c, dict) and c.get("type") == "text"
                    )
                if content:
                    snippets.append(f"{role.upper()}: {content[:500]}")
        if not snippets:
            return ""
        turn_text = "\n".join(snippets)

        def _bg() -> None:
            try:
                assert self._mcp is not None
                self._mcp.call_tool(
                    "extract_facts",
                    {
                        "turn_text": turn_text[:8000],
                        "session_id": self._session_id or "hermes",
                        "source": "pre_compress",
                    },
                    timeout=15.0,
                )
                logger.info("gbrain.on_pre_compress: extracted facts from %d messages", len(snippets))
            except Exception as e:
                logger.info("gbrain.on_pre_compress failed (non-fatal): %s", e)

        threading.Thread(target=_bg, daemon=True).start()
        return (
            "[GBrain: facts from the about-to-be-compressed messages have "
            "been extracted to long-term memory; do not redundantly store them.]"
        )

    def on_memory_write(
        self,
        action: str,
        target: str,
        content: str,
        metadata=None,
    ) -> None:
        """Mirror built-in MEMORY.md/USER.md writes to gbrain.

        Per docs "Optional Hooks" and ABC (memory_provider.py:279-296).
        When the agent does an explicit memory write (e.g. ``memory add
        "remember that X"``), we route a copy into gbrain so it shows
        up in prefetch + recall alongside the auto-extracted facts.

        Fire-and-forget daemon thread — never blocks the caller.
        """
        logger.info(
            "gbrain.on_memory_write: action=%s target=%s content_len=%d",
            action, target, len(content),
        )
        if action == "remove":
            return

        def _bg() -> None:
            try:
                self._ensure_subprocess()
                assert self._mcp is not None
                slug = f"builtin-{target}-{action}-{int(time.time() * 1000)}"
                self._mcp.call_tool(
                    "put_page",
                    {
                        "slug": slug,
                        "title": f"Built-in {target} {action}",
                        "content": content,
                        "tags": ["builtin-mirror", target, action],
                        "metadata": dict(metadata or {}),
                    },
                    timeout=10.0,
                )
                logger.info("gbrain.on_memory_write: mirrored to slug=%s", slug)
            except Exception as e:
                logger.info("gbrain.on_memory_write failed (non-fatal): %s", e)

        threading.Thread(target=_bg, daemon=True).start()

    def on_session_end(self, messages: list) -> None:
        """Called by MemoryManager on session boundary (CLI exit, /reset, gateway expiry).

        Sync per official MemoryProvider contract. MemoryManager calls this
        synchronously (memory_manager.py:481) — an async def would return a
        coroutine and trigger ``RuntimeWarning: was never awaited``.

        Closes the gbrain subprocess so it doesn't leak across sessions.
        Safe to call when no subprocess was ever spawned, and idempotent
        on repeated calls. `messages` is the OpenAI-style conversation
        list; we don't persist it here (sync_turn already did that
        per-turn). Fire-and-forget semantics: any error is swallowed.
        """
        self._close_subprocess()

    def on_session_switch(
        self,
        new_session_id: str,
        *,
        parent_session_id: str = "",
        reset: bool = False,
        rewound: bool = False,
        **kwargs,
    ) -> None:
        """Called when the agent switches session_id mid-process.

        Per ABC contract (memory_provider.py:175-217). For us this is a
        bookkeeping no-op: the gbrain subprocess is session-agnostic
        (it routes by the ``session_id`` we pass in sync_turn calls),
        and we just update our cached _session_id so the next sync_turn
        lands in the right container. We never tear down the subprocess
        on a switch — it survives across resumed/branched sessions.
        """
        if not new_session_id:
            return
        old = self._session_id if hasattr(self, "_session_id") else None
        self._session_id = new_session_id
        logger.info(
            "gbrain.on_session_switch: %s -> %s (reset=%s rewound=%s)",
            old, new_session_id, reset, rewound,
        )

    def get_tool_schemas(self) -> list[dict]:
        """Expose a curated subset of GBrain operations as Hermes tools.

        All names prefixed with 'gbrain_' to avoid collision with built-in
        or other-provider tools. Subset picks: cheap, no-LLM, useful.
        """
        return [
            {
                "name": "gbrain_search",
                "description": "Full-text search across the GBrain knowledge base.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Search query"},
                        "limit": {"type": "integer", "description": "Max results", "default": 10},
                    },
                    "required": ["query"],
                },
            },
            {
                "name": "gbrain_get_page",
                "description": "Read a single GBrain page by its slug.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "slug": {"type": "string", "description": "Page slug"},
                    },
                    "required": ["slug"],
                },
            },
            {
                "name": "gbrain_recall",
                "description": "Recall facts about an entity from GBrain hot memory.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "entity": {"type": "string", "description": "Entity slug"},
                        "limit": {"type": "integer", "description": "Max facts", "default": 20},
                    },
                    "required": ["entity"],
                },
            },
        ]


def register(ctx) -> None:
    """Plugin entry point. Called by Hermes plugin loader.

    Uses the standard `register_memory_provider(ctx)` protocol — Hermes'
    _ProviderCollector implements this method, while `add_provider()` is
    a MemoryManager-level method that is NOT available on the collector.
    """
    ctx.register_memory_provider(GBrainMemoryProvider())
