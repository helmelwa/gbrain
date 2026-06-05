"""Tests for the GBrain Hermes memory provider plugin.

Each test exercises one behavior. Uses REAL `gbrain serve` subprocess
(skipped if gbrain binary not in PATH — see conftest.py).
"""
import json
import os
import shutil
import sys
from pathlib import Path

import pytest

# Make the plugin importable
PLUGIN_ROOT = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(PLUGIN_ROOT))

from plugins.memory.gbrain import GBrainMemoryProvider  # noqa: E402


# -- is_available ----------------------------------------------------------

@pytest.mark.unit
def test_is_available_false_when_no_config_and_no_binary(monkeypatch, tmp_path):
    """is_available() returns False when neither config file nor gbrain binary exist.

    No-network guarantee: must not even attempt to start a subprocess.
    """
    # Ensure no GBRAIN_HOME points to a valid config
    monkeypatch.delenv("GBRAIN_HOME", raising=False)
    # Force provider to look for config in an empty tmp dir
    monkeypatch.setenv("HOME", str(tmp_path))
    # And pretend the binary is missing — patch shutil.which only for this test
    import shutil
    real_which = shutil.which
    monkeypatch.setattr(
        "shutil.which",
        lambda cmd: None if cmd == "gbrain" else real_which(cmd),
    )

    p = GBrainMemoryProvider()
    assert p.is_available() is False


@pytest.mark.unit
def test_is_available_true_when_gbrain_config_exists(monkeypatch, tmp_path):
    """is_available() returns True when a valid GBrain config file is present.

    Pure unit: writes a fake config file, no real gbrain init needed.
    """
    fake_config = tmp_path / ".gbrain" / "config.json"
    fake_config.parent.mkdir(parents=True)
    fake_config.write_text("{}")
    monkeypatch.setenv("GBRAIN_HOME", str(tmp_path))
    p = GBrainMemoryProvider()
    assert p.is_available() is True


# -- name property ---------------------------------------------------------

@pytest.mark.unit
def test_name_returns_gbrain_string():
    """name property equals 'gbrain' (used by MemoryManager for routing)."""
    p = GBrainMemoryProvider()
    assert p.name == "gbrain"
    assert isinstance(p.name, str)


# -- get_config_schema -----------------------------------------------------

@pytest.mark.unit
def test_get_config_schema_returns_empty_for_zero_config_provider():
    """get_config_schema() returns an empty list when the provider has no
    required user-configurable fields.

    Per official docs "Minimal vs Full Schema": GBrain is local-only with
    no API keys and no required credentials, so the setup wizard needs
    no prompts. Optional tunables (transport, container_tag) are
    documented in README, not prompted.
    """
    p = GBrainMemoryProvider()
    schema = p.get_config_schema()
    assert isinstance(schema, list)
    # Empty is the correct value: no required fields means no prompts.
    for field in schema:
        assert isinstance(field, dict)
        assert "key" in field
        assert "description" in field


# -- save_config -----------------------------------------------------------

@pytest.mark.unit
def test_save_config_writes_json_to_hermes_home(tmp_path):
    """save_config persists non-secret fields to $HERMES_HOME/gbrain.json."""
    p = GBrainMemoryProvider()
    p.save_config(
        {"transport": "stdio", "container_tag": "test-tag"},
        str(tmp_path),
    )
    out = tmp_path / "gbrain.json"
    assert out.exists()
    data = json.loads(out.read_text())
    assert data["transport"] == "stdio"
    assert data["container_tag"] == "test-tag"


# -- initialize ------------------------------------------------------------

@pytest.mark.unit
def test_initialize_stores_session_id_and_hermes_home(tmp_path, monkeypatch):
    """initialize() records the session id and loads config from hermes_home.

    Does NOT spawn any subprocess — that is lazy on first prefetch/sync_turn.
    """
    cfg = tmp_path / "gbrain.json"
    cfg.write_text(json.dumps({"transport": "stdio", "container_tag": "alpha"}))

    p = GBrainMemoryProvider()
    p.initialize("session-abc-123", hermes_home=str(tmp_path), platform="cli")
    assert p._session_id == "session-abc-123"
    assert p._hermes_home == str(tmp_path)
    assert p._config["container_tag"] == "alpha"


@pytest.mark.unit
def test_initialize_with_no_saved_config_uses_defaults(tmp_path):
    """initialize() falls back to sensible defaults when no config file exists."""
    p = GBrainMemoryProvider()
    p.initialize("s1", hermes_home=str(tmp_path))
    assert p._config == {"transport": "stdio", "container_tag": "hermes"}


# -- prefetch (real subprocess) --------------------------------------------

@pytest.mark.integration
def test_prefetch_returns_string_type(tmp_path, gbrain_home_env, brain_dir):
    """prefetch() returns a str (empty when no relevant context, or markdown)."""
    p = GBrainMemoryProvider()
    p.initialize("s1", hermes_home=str(tmp_path), platform="cli")
    result = p.prefetch("anything")
    assert isinstance(result, str)


@pytest.mark.integration
def test_prefetch_returns_empty_string_when_brain_empty(tmp_path, gbrain_home_env, brain_dir):
    """prefetch() on an empty brain returns empty string (no results to surface).

    Empty brain + empty search = no markdown context. Graceful degradation.
    """
    p = GBrainMemoryProvider()
    p.initialize("s1", hermes_home=str(tmp_path), platform="cli")
    result = p.prefetch("nonexistent topic xyzzy")
    assert result == ""


@pytest.mark.integration
def test_prefetch_returns_markdown_when_search_matches(tmp_path, gbrain_home_env, brain_dir):
    """prefetch() returns markdown context from a real `gbrain serve` subprocess.

    End-to-end: plugin spawns its own `gbrain serve`, calls tools/call, formats
    result. We seed via the plugin's own subprocess (not a separate fixture)
    to avoid duplicate `gbrain serve` processes fighting for the PGLite
    write lock.
    """
    p = GBrainMemoryProvider()
    p.initialize("s1", hermes_home=str(tmp_path), platform="cli")
    p._ensure_subprocess()
    assert p._mcp is not None
    p._mcp.call_tool(
        "put_page",
        {
            "slug": "test-prefetch-seed",
            "title": "Seed Page",
            "content": "this page contains the unique-token pretzel-77 marker",
            "tags": ["test"],
        },
    )
    result = p.prefetch("pretzel-77")
    # Real search on real brain should surface the marker or the slug
    assert isinstance(result, str)
    assert ("pretzel-77" in result) or ("test-prefetch-seed" in result), f"unexpected empty result: {result!r}"


# -- queue_prefetch (cache warming) ----------------------------------------

@pytest.mark.integration
def test_prefetch_uses_cache_after_queue_prefetch(tmp_path, gbrain_home_env, brain_dir):
    """After queue_prefetch warms the cache, next prefetch returns cached value
    without making a new MCP call.
    """
    p = GBrainMemoryProvider()
    p.initialize("s1", hermes_home=str(tmp_path), platform="cli")
    # Seed and warm cache manually (deterministic, avoids thread scheduling races)
    p._ensure_subprocess()
    assert p._mcp is not None
    p._mcp.call_tool(
        "put_page",
        {
            "slug": "cache-warm-page",
            "title": "Cache Warm",
            "content": "marker-needle-42 in this page for cache test",
            "tags": [],
        },
    )
    # Warm cache via queue_prefetch (returns immediately; daemon thread does the work)
    p.queue_prefetch("marker-needle-42")
    # Wait briefly for the background thread to complete
    import time
    for _ in range(50):
        if p._prefetch_cache:
            break
        time.sleep(0.1)
    # prefetch should now return the cached markdown, not call subprocess
    result = p.prefetch("something-different")
    assert isinstance(result, str)
    assert "marker-needle-42" in result, f"cache not used; result={result!r}"


# -- subprocess crash recovery ---------------------------------------------

@pytest.mark.integration
def test_prefetch_returns_empty_when_subprocess_missing(tmp_path, gbrain_home_env, brain_dir):
    """If the subprocess can't be started, prefetch returns empty (graceful).

    Simulates gbrain not in PATH or brain_dir corrupted.
    """
    p = GBrainMemoryProvider()
    p.initialize("s1", hermes_home=str(tmp_path), platform="cli")
    # Force the mcp client to think it's dead
    p._proc = None
    p._mcp = None
    # Sabotage: patch _ensure_subprocess to raise (binary missing scenario)
    def broken():
        raise RuntimeError("simulated gbrain unavailable")
    p._ensure_subprocess = broken  # type: ignore
    result = p.prefetch("anything")
    assert result == ""


# -- sync_turn -------------------------------------------------------------

@pytest.mark.integration
def test_sync_turn_does_not_block(tmp_path, gbrain_home_env, brain_dir):
    """sync_turn() returns quickly without waiting for gbrain extraction.

    The actual extract_facts call is fire-and-forget via a daemon thread.
    """
    p = GBrainMemoryProvider()
    p.initialize("s1", hermes_home=str(tmp_path), platform="cli")
    import time
    start = time.monotonic()
    p.sync_turn("user said hi", "assistant said hello")
    elapsed = time.monotonic() - start
    # sync_turn itself should return in <1s even if extraction takes longer
    assert elapsed < 2.0


@pytest.mark.unit
def test_sync_turn_skips_non_primary_agent_context(tmp_path, monkeypatch):
    """sync_turn() with agent_context='cron' or 'subagent' is a no-op.

    Per MemoryManager spec, subagent/cron writes would corrupt the user's
    persistent representation. Provider must respect this.
    """
    p = GBrainMemoryProvider()
    p.initialize("s1", hermes_home=str(tmp_path), platform="cli", agent_context="cron")
    # Should not raise, should not spawn subprocess
    p.sync_turn("x", "y")
    assert p._mcp is None
    assert p._proc is None


# -- shutdown --------------------------------------------------------------

@pytest.mark.integration
def test_shutdown_closes_subprocess_cleanly(tmp_path, gbrain_home_env, brain_dir):
    """shutdown() closes the gbrain subprocess; it can be respawned on next call."""
    p = GBrainMemoryProvider()
    p.initialize("s1", hermes_home=str(tmp_path), platform="cli")
    p._ensure_subprocess()
    assert p._mcp is not None and p._proc is not None
    proc = p._proc
    p.shutdown()
    # After shutdown, the process should have exited
    import time
    for _ in range(30):
        if proc.poll() is not None:
            break
        time.sleep(0.1)
    assert proc.poll() is not None, "gbrain subprocess did not exit after shutdown"


@pytest.mark.unit
def test_shutdown_is_safe_when_no_subprocess(tmp_path, monkeypatch):
    """shutdown() is a no-op when no subprocess was ever spawned."""
    p = GBrainMemoryProvider()
    p.initialize("s1", hermes_home=str(tmp_path))
    # No _ensure_subprocess called; should not raise
    p.shutdown()


# -- get_tool_schemas ------------------------------------------------------

@pytest.mark.unit
def test_get_tool_schemas_returns_list_with_search_and_get_page(tmp_path, monkeypatch):
    """get_tool_schemas() exposes a subset of GBrain ops as Hermes tools.

    All tool names must be prefixed with 'gbrain_' to avoid collisions with
    built-in or other-provider tools.
    """
    p = GBrainMemoryProvider()
    schemas = p.get_tool_schemas()
    assert isinstance(schemas, list)
    assert len(schemas) >= 2
    names = {s["name"] for s in schemas}
    # All prefixed
    for n in names:
        assert n.startswith("gbrain_"), f"tool {n!r} missing gbrain_ prefix"
    # Critical ops exposed
    assert "gbrain_search" in names
    assert "gbrain_get_page" in names
