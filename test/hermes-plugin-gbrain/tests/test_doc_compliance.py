"""Tests that GBrainMemoryProvider conforms to the official Hermes MemoryProvider API.

Reference: https://hermes-agent.nousresearch.com/docs/developer-guide/memory-provider-plugin
Source of truth: /home/lighthouse/.hermes/hermes-agent/agent/memory_provider.py

These tests assert the API contract that MemoryManager depends on. They
load the BUNDLED plugin (Phase 1 install location) so they catch the
exact runtime path the live agent uses.
"""
import asyncio
import inspect
import sys
import threading
from pathlib import Path
from unittest.mock import MagicMock

import pytest

# Match Hermes' bundled plugin loader: hermes-agent/ on sys.path
HERMES_AGENT_ROOT = Path("/home/lighthouse/.hermes/hermes-agent")
if str(HERMES_AGENT_ROOT) not in sys.path:
    sys.path.insert(0, str(HERMES_AGENT_ROOT))

from agent.memory_provider import MemoryProvider  # noqa: E402

BUNDLED_PLUGIN = HERMES_AGENT_ROOT / "plugins" / "memory" / "gbrain" / "__init__.py"


def _load_bundled_class():
    """Import the bundled plugin and return the GBrainMemoryProvider class.

    Bypasses sys.path-cached user-install copies by loading directly from
    the bundled file path. This matches how Hermes' plugin loader
    resolves the plugin.
    """
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "bundled_gbrain_plugin", str(BUNDLED_PLUGIN)
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.GBrainMemoryProvider


# -- Lifecycle hooks must be SYNC (per MemoryManager contract) --------------

@pytest.mark.unit
def test_prefetch_is_synchronous_function():
    """prefetch() must be a regular def, not async def.

    MemoryManager.prefetch_all (memory_manager.py:348) calls
    ``provider.prefetch(query, session_id=...)`` synchronously and
    expects a str back. An async def returns a coroutine — MemoryManager
    would then call ``.strip()`` on a coroutine and crash. Per official
    docs and ABC contract, prefetch is SYNC.
    """
    ProviderClass = _load_bundled_class()
    prefetch = ProviderClass.prefetch
    assert not inspect.iscoroutinefunction(prefetch), (
        "prefetch() is async; MemoryManager calls it synchronously. "
        "This causes 'coroutine has no len()' / 'was never awaited' errors. "
        "Make it a regular `def` that delegates to a daemon thread."
    )


@pytest.mark.unit
def test_queue_prefetch_is_synchronous_function():
    """queue_prefetch() must be a regular def, not async def.

    MemoryManager.queue_prefetch_all (memory_manager.py:362) calls
    ``provider.queue_prefetch(query, session_id=...)`` synchronously.
    """
    ProviderClass = _load_bundled_class()
    queue_prefetch = ProviderClass.queue_prefetch
    assert not inspect.iscoroutinefunction(queue_prefetch), (
        "queue_prefetch() is async; MemoryManager calls it synchronously."
    )


@pytest.mark.unit
def test_sync_turn_is_synchronous_function():
    """sync_turn() must be a regular def, not async def.

    MemoryManager.sync_all (memory_manager.py:395, 402) calls
    ``provider.sync_turn(...)`` synchronously. Per official docs,
    sync_turn() MUST be non-blocking — it should hand off work to a
    daemon thread and return immediately.
    """
    ProviderClass = _load_bundled_class()
    sync_turn = ProviderClass.sync_turn
    assert not inspect.iscoroutinefunction(sync_turn), (
        "sync_turn() is async; MemoryManager calls it synchronously. "
        "Per official docs, sync_turn() MUST be non-blocking — use a "
        "daemon thread, not asyncio.create_task."
    )


@pytest.mark.unit
def test_sync_turn_uses_documented_param_names():
    """sync_turn() parameter names must match the official ABC.

    ABC signature (memory_provider.py:115-122):
        sync_turn(self, user_content, assistant_content, *, session_id="", messages=None)
    """
    ProviderClass = _load_bundled_class()
    sig = inspect.signature(ProviderClass.sync_turn)
    # First two NON-self POSITIONAL_OR_KEYWORD params must be user_content, assistant_content
    po_params = [
        name for name, p in sig.parameters.items()
        if name != "self"
        and p.kind in (inspect.Parameter.POSITIONAL_OR_KEYWORD, inspect.Parameter.POSITIONAL_ONLY)
    ]
    assert po_params[:2] == ["user_content", "assistant_content"], (
        f"Expected first two params to be ['user_content', 'assistant_content'], "
        f"got {po_params[:2]}. ABC contract violated."
    )


@pytest.mark.unit
def test_on_session_end_is_synchronous_function():
    """on_session_end() must be a regular def, not async def.

    MemoryManager.on_session_end (memory_manager.py:481) calls
    ``provider.on_session_end(messages)`` synchronously. Our current
    async def returns a coroutine → RuntimeWarning "was never awaited".
    """
    ProviderClass = _load_bundled_class()
    on_session_end = ProviderClass.on_session_end
    assert not inspect.iscoroutinefunction(on_session_end), (
        "on_session_end() is async; MemoryManager calls it synchronously. "
        "Live evidence: 'RuntimeWarning: coroutine "
        "GBrainMemoryProvider.on_session_end was never awaited'."
    )


@pytest.mark.unit
def test_handle_tool_call_uses_tool_name_param():
    """handle_tool_call() parameter must be named 'tool_name'.

    ABC signature (memory_provider.py:143) and MemoryManager (line 453)
    both call it as ``provider.handle_tool_call(tool_name, args, **kwargs)``.
    A method named `name` works positionally but breaks keyword-based
    callers and confuses static analysis.
    """
    ProviderClass = _load_bundled_class()
    sig = inspect.signature(ProviderClass.handle_tool_call)
    params = list(sig.parameters.keys())
    # Skip 'self'; first param should be 'tool_name'
    non_self = [p for p in params if p != "self"]
    assert non_self[0] == "tool_name", (
        f"Expected first param to be 'tool_name', got '{non_self[0]}'. "
        "ABC and MemoryManager call it positionally as tool_name."
    )


# -- name must be a @property (per ABC) -------------------------------------

@pytest.mark.unit
def test_name_is_property():
    """name must be a @property on the class, not a class-level literal.

    ABC declares (memory_provider.py:45-48):
        @property
        @abstractmethod
        def name(self) -> str: ...
    """
    ProviderClass = _load_bundled_class()
    name_attr = inspect.getattr_static(ProviderClass, "name")
    assert isinstance(name_attr, property), (
        f"name is {type(name_attr).__name__}, expected property. "
        "ABC requires @property @abstractmethod def name(self)."
    )
    # The property should return the string "gbrain"
    instance = ProviderClass()
    assert instance.name == "gbrain"


# -- Optional hooks that the docs list and we should implement -------------

@pytest.mark.unit
def test_on_pre_compress_is_implemented():
    """on_pre_compress(messages) must be a real override, not the ABC default.

    Per docs "Optional Hooks" table, on_pre_compress is called before
    context compression discards old messages. The ABC default returns
    empty string — for gbrain we want to actually capture insights from
    about-to-be-discarded messages so the compression summary preserves
    them. A no-op means we silently lose memory at compression time.
    """
    ProviderClass = _load_bundled_class()
    # Method must exist and be defined on the provider (not just inherited
    # from ABC's empty default).
    assert "on_pre_compress" in ProviderClass.__dict__, (
        "on_pre_compress not implemented on GBrainMemoryProvider. "
        "ABC default returns '' which means compression silently loses "
        "our insights. See docs 'Optional Hooks' table."
    )


@pytest.mark.unit
def test_on_memory_write_is_implemented_when_advertised():
    """If plugin.yaml advertises on_memory_write as a hook, the provider
    MUST implement it. Otherwise the manifest lies about capability.
    """
    import re
    plugin_yaml = HERMES_AGENT_ROOT / "plugins" / "memory" / "gbrain" / "plugin.yaml"
    if not plugin_yaml.exists():
        pytest.skip("plugin.yaml not present")
    text = plugin_yaml.read_text()
    # Parse the hooks list
    m = re.search(r"^hooks:\s*\n((?:\s*-\s*\w+\s*\n?)+)", text, re.MULTILINE)
    if not m:
        pytest.skip("plugin.yaml has no hooks list")
    declared_hooks = re.findall(r"-\s*(\w+)", m.group(1))

    ProviderClass = _load_bundled_class()
    for hook in declared_hooks:
        assert hook in ProviderClass.__dict__, (
            f"plugin.yaml declares hook '{hook}' but GBrainMemoryProvider "
            f"does not implement it. Either implement the hook or remove "
            f"it from the hooks list."
        )


# -- Threading Contract ----------------------------------------------------

@pytest.mark.unit
def test_sync_turn_tracks_thread_reference_for_subsequent_join():
    """sync_turn must store its Thread on self so the next call can join it.

    Per official docs Threading Contract:
        if self._sync_thread and self._sync_thread.is_alive():
            self._sync_thread.join(timeout=5.0)
        self._sync_thread = threading.Thread(target=_sync, daemon=True)
        self._sync_thread.start()

    Without this, every turn spawns a fresh thread with no upper bound
    on concurrency. A 50-turn session can leave 50 daemon threads in
    flight, all racing to talk to the same gbrain subprocess.
    """
    ProviderClass = _load_bundled_class()
    p = ProviderClass()
    # Initialize needs hermes_home. Use tmp_path via tmpdir-style
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        p.initialize("s1", hermes_home=td, platform="cli")
        # Sync thread slot must exist (initialized to None in initialize)
        assert hasattr(p, "_sync_thread"), (
            "sync_turn has no self._sync_thread slot. "
            "Docs Threading Contract requires tracking the previous "
            "thread so the next call can join(timeout=5.0)."
        )


# -- Profile Isolation -----------------------------------------------------
# NOTE: We deliberately do NOT redirect gbrain's data dir to a
# hermes_home-scoped subdirectory. GBrain is a shared system-level
# service whose brain lives wherever gbrain's own configDir() finds
# it ($GBRAIN_HOME or ~/.gbrain). The plugin must respect that, not
# shadow the operator's real brain. See gbrain/src/core/config.ts:765.

# -- Prefetch fallback -----------------------------------------------------

@pytest.mark.unit
def test_prefetch_uses_query_for_natural_language_queries(monkeypatch):
    """For natural-language queries, prefetch must use gbrain's `query`
    MCP tool (hybrid vector+keyword+rerank), not `search` (BM25 keyword
    only).

    Live evidence: gbrain `search` returns [] for queries like
    "Что я знаю о Wladimir Helmel?" (Russian NL) but `query` (hybrid)
    returns 1793 chars of relevant results. Without this fix, the
    agent never gets auto-context and must call gbrain_search
    explicitly (visible in live logs as repeated handle_tool_call).

    Reference: gbrain/src/core/operations.ts:1214 (search, keyword-only)
    vs :1265 (query, full hybrid pipeline). See also
    docs/architecture/RETRIEVAL.md.
    """
    from plugins.memory.gbrain import GBrainMemoryProvider
    p = GBrainMemoryProvider()
    p._mcp = MagicMock()
    p._proc = MagicMock()
    p._proc.poll.return_value = None
    p._mcp.call_tool.return_value = (
        '[{"slug": "people/wladimir-helmel", "chunk_text": "Wladimir career page content"}]'
    )
    p._prefetch_cache = ""
    p._session_id = "test"
    p._hermes_home = "/tmp"
    p._agent_context = "primary"

    result = p.prefetch("Что я знаю о Wladimir Helmel?")

    # One call: `query` (the hybrid tool), not `search` (keyword-only)
    assert p._mcp.call_tool.call_count == 1
    args = p._mcp.call_tool.call_args
    assert args.args[0] == "query", (
        f"prefetch must use 'query' (hybrid), got {args.args[0]!r}. "
        f"'search' is keyword-only and returns [] for NL queries."
    )
    assert "Wladimir career page content" in result


@pytest.mark.unit
def test_prefetch_uses_search_when_search_returns_results(monkeypatch):
    """When gbrain `search` returns real results, prefetch must use them
    directly without falling back to `query` (saves the second call).
    """
    from plugins.memory.gbrain import GBrainMemoryProvider
    p = GBrainMemoryProvider()
    p._mcp = MagicMock()
    p._proc = MagicMock()
    p._proc.poll.return_value = None
    p._mcp.call_tool.return_value = (
        '[{"slug": "people/wladimir-helmel", "chunk_text": "Real result from search"}]'
    )
    p._prefetch_cache = ""
    p._session_id = "test"
    p._hermes_home = "/tmp"
    p._agent_context = "primary"

    result = p.prefetch("Wladimir Helmel career")

    # Only one call — search succeeded, no fallback needed
    assert p._mcp.call_tool.call_count == 1, (
        f"Expected 1 call (search only, no fallback), got {p._mcp.call_tool.call_count}"
    )
    assert "Real result from search" in result


@pytest.mark.unit
def test_prefetch_calls_query_with_documented_params(monkeypatch):
    """prefetch must use the `query` MCP tool (hybrid vector+keyword+rerank)
    not `search` (BM25 keyword only). The query tool's args must be
    explicit so the operator can predict cost/quality.

    Per docs/architecture/RETRIEVAL.md and
    docs/eval/SEARCH_MODE_METHODOLOGY.md:
    - `query` is the full hybrid pipeline (vector + BM25 + RRF + reranker)
    - `search` is keyword-only (misses NL/Russian queries)

    Args for our prefetch (per
    src/core/operations.ts:1274-1335 + src/core/search/hybrid.ts:529):
    - query: the user message
    - limit: 20 (default per ops.ts:1280)
    - expand: false (we have no Anthropic/Minimax chat API key for the
      Haiku expansion; even if we did, $0.001 + 200ms per prefetch is
      not worth it for a context-injection call)
    - detail: "medium" (default; "low" can return [] and auto-escalate,
      "high" is too expensive for prefetch)
    """
    from plugins.memory.gbrain import GBrainMemoryProvider
    p = GBrainMemoryProvider()
    p._mcp = MagicMock()
    p._proc = MagicMock()
    p._proc.poll.return_value = None
    p._mcp.call_tool.return_value = (
        '[{"slug": "people/wladimir-helmel", "chunk_text": "Wladimir content from query"}]'
    )
    p._prefetch_cache = ""
    p._session_id = "test"
    p._hermes_home = "/tmp"
    p._agent_context = "primary"

    result = p.prefetch("Wladimir Helmel career")

    # Must call the `query` tool, not `search`
    assert p._mcp.call_tool.call_count == 1
    args = p._mcp.call_tool.call_args
    assert args.args[0] == "query", (
        f"prefetch must use 'query' (hybrid), got {args.args[0]!r}. "
        f"'search' is keyword-only and returns [] for NL queries."
    )
    params = args.args[1]
    # query text
    assert params["query"] == "Wladimir Helmel career"
    # limit
    assert params.get("limit") == 20, (
        f"limit should be 20 (default), got {params.get('limit')!r}"
    )
    # expand off (no API key for Haiku; saves cost anyway)
    assert params.get("expand") is False, (
        f"expand must be False (no chat API key), got {params.get('expand')!r}"
    )
    # detail medium (default; balanced)
    assert params.get("detail") == "medium", (
        f"detail should be 'medium', got {params.get('detail')!r}"
    )
    # Result not empty
    assert "Wladimir content from query" in result


# -- On_pre_compress hook ---------------------------------------------------

@pytest.mark.unit
def test_get_config_schema_only_prompts_required_fields():
    """Per docs 'Minimal vs Full Schema':

        Providers with many options should keep the schema minimal —
        only include fields the user must configure.

    A field with a default is NOT required — the user can skip it.
    Prompting for it in the setup wizard is UX noise.
    """
    p = _load_bundled_class()()
    schema = p.get_config_schema()
    for field in schema:
        is_required = field.get("required", False)
        has_default = "default" in field
        if has_default and not is_required:
            pytest.fail(
                f"get_config_schema field {field.get('key')!r} has a default "
                f"({field.get('default')!r}) but is not marked required. "
                f"Per docs 'Minimal vs Full Schema', optional fields with "
                f"defaults should be documented in README, not prompted "
                f"in the setup wizard."
            )
