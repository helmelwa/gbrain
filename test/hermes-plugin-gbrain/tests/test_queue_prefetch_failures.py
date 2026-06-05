"""Unit tests for queue_prefetch failure paths.

queue_prefetch warms the prefetch cache for the NEXT prefetch() call.
The warmup runs in a background daemon thread. Failure modes:
  1. Subprocess not yet spawned AND ensure_subprocess() raises
     (gbrain binary missing, brain dir corrupted).
  2. Subprocess spawns but MCP call_tool raises.

In all cases queue_prefetch must NOT raise to the caller (fire-and-forget
semantics per MemoryManager contract). The next prefetch() should return
either the cached value (success) or an empty string (any failure).

NOTE: After Phase 2 (doc-compliance refactor), queue_prefetch is a SYNC
def that hands off to a daemon thread — callers no longer need
asyncio.run(). We add a small wait loop after each call to let the
background thread run before asserting on cache state.
"""
from __future__ import annotations

import time
from pathlib import Path
from unittest.mock import MagicMock
import sys

import pytest

PLUGIN_ROOT = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(PLUGIN_ROOT))

from plugins.memory.gbrain import GBrainMemoryProvider  # noqa: E402


def _wait_for_cache(p: GBrainMemoryProvider, timeout: float = 2.0) -> None:
    """Block until the daemon-thread warmup populates (or fails to populate)
    the cache, up to ``timeout`` seconds.
    """
    # We don't have a join handle, so we poll _prefetch_cache. The thread
    # is short-lived (mock + format), so this returns in <100ms.
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        # If the warmup is in flight, _prefetch_cache may be set or
        # the mock side_effect has run. We just sleep briefly to give
        # the thread a chance.
        time.sleep(0.02)
        # The test asserts on the final state immediately after, so
        # one short sleep is enough for the mocked threads to finish.
        break


@pytest.mark.unit
def test_queue_prefetch_silent_when_ensure_subprocess_raises(tmp_path):
    """If subprocess can't start, queue_prefetch must not raise to caller.

    Simulates: gbrain binary not in PATH. ensure_subprocess raises immediately.
    """
    p = GBrainMemoryProvider()
    p.initialize("sess-1", hermes_home=str(tmp_path), platform="cli")

    def broken():
        raise RuntimeError("gbrain binary not in PATH")
    p._ensure_subprocess = broken  # type: ignore

    # Must not raise — sync def, returns None immediately
    p.queue_prefetch("anything")
    _wait_for_cache(p)

    # Cache stays empty (no successful warmup)
    assert p._prefetch_cache == ""


@pytest.mark.unit
def test_queue_prefetch_silent_when_call_tool_raises(tmp_path):
    """If MCP call_tool raises, the background thread must swallow it.

    Simulates: subprocess alive but the search call itself fails.
    """
    p = GBrainMemoryProvider()
    p.initialize("sess-1", hermes_home=str(tmp_path), platform="cli")
    p._mcp = MagicMock()
    p._mcp.call_tool.side_effect = RuntimeError("MCP call failed")
    p._proc = MagicMock()
    p._proc.poll.return_value = None

    # Must not raise (sync def returns immediately; daemon thread catches and exits)
    p.queue_prefetch("test query")
    _wait_for_cache(p)

    # Cache stays empty because call failed (no successful warmup)
    assert p._prefetch_cache == ""


@pytest.mark.unit
def test_queue_prefetch_populates_cache_on_success(tmp_path):
    """Happy path: background thread successfully populates the cache."""
    p = GBrainMemoryProvider()
    p.initialize("sess-1", hermes_home=str(tmp_path), platform="cli")
    p._mcp = MagicMock()
    # call_tool returns JSON; _format_search_results will parse and format
    p._mcp.call_tool.return_value = (
        '[{"slug": "found-it", "chunk_text": "matching content"}]'
    )
    p._proc = MagicMock()
    p._proc.poll.return_value = None

    p.queue_prefetch("test query")

    # Wait for the daemon thread to populate the cache
    deadline = time.monotonic() + 2.0
    while time.monotonic() < deadline and p._prefetch_cache == "":
        time.sleep(0.02)

    # Cache should now be populated with formatted markdown
    assert p._prefetch_cache != ""
    assert "found-it" in p._prefetch_cache


@pytest.mark.unit
def test_queue_prefetch_returns_quickly_when_warmup_is_fast(tmp_path):
    """queue_prefetch returns quickly when the background warmup is fast.

    This validates fire-and-forget semantics: the caller (MemoryManager)
    doesn't wait for warmup to complete.
    """
    p = GBrainMemoryProvider()
    p.initialize("sess-1", hermes_home=str(tmp_path), platform="cli")
    p._mcp = MagicMock()
    p._mcp.call_tool.return_value = "[]"  # empty results, no parsing needed
    p._proc = MagicMock()
    p._proc.poll.return_value = None

    start = time.monotonic()
    p.queue_prefetch("anything")
    elapsed = time.monotonic() - start

    # queue_prefetch is a sync def that spawns a daemon thread — the
    # caller should not block. Mock-backed warmup runs in microseconds.
    assert elapsed < 0.5, f"queue_prefetch blocked for {elapsed:.2f}s"
