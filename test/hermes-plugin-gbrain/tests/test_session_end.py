"""Unit tests for on_session_end lifecycle.

on_session_end is called by MemoryManager when a session ends gracefully
(CLI exit, /reset, gateway session expiry). It must:
  1. Close the gbrain subprocess if one was spawned.
  2. Be safe to call when no subprocess exists.
  3. Be safe to call multiple times (idempotent).

These tests are pure unit — mock the McpClient to avoid subprocess spawn.

NOTE: After Phase 2 (doc-compliance refactor), on_session_end is a SYNC
def — no asyncio.run() needed.
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock
import sys

import pytest

PLUGIN_ROOT = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(PLUGIN_ROOT))

from plugins.memory.gbrain import GBrainMemoryProvider  # noqa: E402


def _make_provider_with_mock_client(tmp_path) -> tuple[GBrainMemoryProvider, MagicMock]:
    """Build a provider with a mocked McpClient attached (no real subprocess)."""
    p = GBrainMemoryProvider()
    p.initialize("sess-1", hermes_home=str(tmp_path), platform="cli")
    p._mcp = MagicMock()
    p._proc = MagicMock()
    p._proc.poll.return_value = None  # process is alive
    return p, p._mcp


@pytest.mark.unit
def test_on_session_end_closes_mcp_client(tmp_path):
    """on_session_end calls close() on the MCP client to terminate subprocess."""
    p, mcp = _make_provider_with_mock_client(tmp_path)

    p.on_session_end(messages=[])

    mcp.close.assert_called_once()


@pytest.mark.unit
def test_on_session_end_clears_mcp_and_proc_references(tmp_path):
    """After on_session_end, internal refs are cleared so next call won't reuse dead process."""
    p, _ = _make_provider_with_mock_client(tmp_path)

    p.on_session_end(messages=[])

    assert p._mcp is None
    assert p._proc is None


@pytest.mark.unit
def test_on_session_end_is_safe_when_no_subprocess(tmp_path):
    """Calling on_session_end before any MCP call must not raise."""
    p = GBrainMemoryProvider()
    p.initialize("sess-1", hermes_home=str(tmp_path), platform="cli")
    # No _mcp/_proc set — should be a no-op.
    p.on_session_end(messages=[])

    assert p._mcp is None
    assert p._proc is None


@pytest.mark.unit
def test_on_session_end_is_idempotent(tmp_path):
    """Calling on_session_end twice must not raise on the second call."""
    p, mcp = _make_provider_with_mock_client(tmp_path)

    p.on_session_end(messages=[])
    p.on_session_end(messages=[])  # must not raise

    # First call closes; second call sees _mcp=None and is a no-op.
    assert mcp.close.call_count == 1


@pytest.mark.unit
def test_on_session_end_swallows_close_errors(tmp_path):
    """If close() raises (e.g. subprocess already dead), on_session_end must not propagate."""
    p, mcp = _make_provider_with_mock_client(tmp_path)
    mcp.close.side_effect = RuntimeError("subprocess already terminated")

    # Must not raise, even if close() blows up.
    p.on_session_end(messages=[])

    # State is still cleared (best-effort cleanup).
    assert p._mcp is None
    assert p._proc is None
