"""Unit tests for handle_tool_call.

handle_tool_call(name, args) is called by MemoryManager when the agent
invokes one of the tools declared in get_tool_schemas(). It must:
  1. Strip the 'gbrain_' prefix to get the MCP tool name.
  2. Forward the call to the subprocess via MCP call_tool.
  3. Return the result as a JSON string (per MemoryManager contract).
  4. Handle unknown tool names gracefully.
  5. Not raise if the subprocess is not yet running (best-effort).

Dispatch mapping:
  gbrain_search  -> search
  gbrain_get_page -> get_page
  gbrain_recall  -> recall
"""
from __future__ import annotations

import asyncio
import json
from pathlib import Path
from unittest.mock import MagicMock
import sys

import pytest

PLUGIN_ROOT = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(PLUGIN_ROOT))

from plugins.memory.gbrain import GBrainMemoryProvider  # noqa: E402


def _run(coro):
    """Run an async call from a sync test. Stub: handle_tool_call is now sync."""
    return coro

def _direct(value):
    """Pass-through for sync methods (formerly async)."""
    return value
    return asyncio.run(coro)


def _make_provider_with_mock_client(tmp_path) -> tuple[GBrainMemoryProvider, MagicMock]:
    p = GBrainMemoryProvider()
    p.initialize("sess-1", hermes_home=str(tmp_path), platform="cli")
    p._mcp = MagicMock()
    p._proc = MagicMock()
    p._proc.poll.return_value = None
    return p, p._mcp


# -- prefix stripping -------------------------------------------------------

@pytest.mark.unit
def test_handle_tool_call_strips_gbrain_prefix(tmp_path):
    """gbrain_search is dispatched to MCP 'search', not 'gbrain_search'."""
    p, mcp = _make_provider_with_mock_client(tmp_path)
    mcp.call_tool.return_value = "[]"

    p.handle_tool_call("gbrain_search", {"query": "x", "limit": 5})

    # MCP was called with the unprefixed name
    called_name = mcp.call_tool.call_args[0][0]
    assert called_name == "search"
    # Args were forwarded unchanged
    called_args = mcp.call_tool.call_args[0][1]
    assert called_args == {"query": "x", "limit": 5}


@pytest.mark.unit
def test_handle_tool_call_get_page_dispatches_correctly(tmp_path):
    p, mcp = _make_provider_with_mock_client(tmp_path)
    mcp.call_tool.return_value = '{"slug": "x", "content": "y"}'

    p.handle_tool_call("gbrain_get_page", {"slug": "test"})

    called_name = mcp.call_tool.call_args[0][0]
    assert called_name == "get_page"
    called_args = mcp.call_tool.call_args[0][1]
    assert called_args == {"slug": "test"}


@pytest.mark.unit
def test_handle_tool_call_recall_dispatches_correctly(tmp_path):
    p, mcp = _make_provider_with_mock_client(tmp_path)
    mcp.call_tool.return_value = '[]'

    p.handle_tool_call("gbrain_recall", {"entity": "alice", "limit": 10})

    called_name = mcp.call_tool.call_args[0][0]
    assert called_name == "recall"


# -- return format -----------------------------------------------------------

@pytest.mark.unit
def test_handle_tool_call_returns_string_type(tmp_path):
    """Per MemoryManager contract, the result must be a JSON string."""
    p, mcp = _make_provider_with_mock_client(tmp_path)
    mcp.call_tool.return_value = '["a", "b"]'

    result = p.handle_tool_call("gbrain_search", {"query": "x"})

    assert isinstance(result, str)


@pytest.mark.unit
def test_handle_tool_call_returns_mcp_result_as_json(tmp_path):
    """The MCP text content is returned as-is (it's already JSON from GBrain)."""
    p, mcp = _make_provider_with_mock_client(tmp_path)
    expected = '[{"slug": "found", "chunk_text": "matching"}]'
    mcp.call_tool.return_value = expected

    result = p.handle_tool_call("gbrain_search", {"query": "x"})

    # The MCP call_tool returns text content; we pass it through.
    assert result == expected


# -- error handling ----------------------------------------------------------

@pytest.mark.unit
def test_handle_tool_call_unknown_tool_returns_error_json(tmp_path):
    """Unknown tool name should return a structured error JSON, not raise."""
    p, mcp = _make_provider_with_mock_client(tmp_path)
    # Simulate GBrain rejecting the tool: returns an error envelope
    mcp.call_tool.return_value = '{"error": "tool not found"}'

    result = p.handle_tool_call("gbrain_nonexistent", {})

    parsed = json.loads(result)
    assert "error" in parsed


@pytest.mark.unit
def test_handle_tool_call_mcp_failure_returns_error_json(tmp_path):
    """If MCP call_tool raises, handle_tool_call returns error JSON, not raises."""
    p, mcp = _make_provider_with_mock_client(tmp_path)
    mcp.call_tool.side_effect = RuntimeError("gbrain subprocess died")

    result = p.handle_tool_call("gbrain_search", {"query": "x"})

    parsed = json.loads(result)
    assert "error" in parsed


@pytest.mark.unit
def test_handle_tool_call_no_subprocess_returns_error_json(tmp_path):
    """If no subprocess ever spawned, return error JSON, don't raise.

    Sabotage _ensure_subprocess to simulate 'binary not available' —
    otherwise the test would hit a real gbrain install on this machine.
    """
    p = GBrainMemoryProvider()
    p.initialize("sess-1", hermes_home=str(tmp_path), platform="cli")
    # No _mcp/_proc — handle_tool_call must not crash.
    # Sabotage: prevent any real subprocess spawn.
    def broken():
        raise RuntimeError("gbrain not available in test env")
    p._ensure_subprocess = broken  # type: ignore

    result = p.handle_tool_call("gbrain_search", {"query": "x"})

    parsed = json.loads(result)
    assert "error" in parsed


# -- synchronous contract --------------------------------------------------

@pytest.mark.unit
def test_handle_tool_call_is_synchronous_not_coroutine(tmp_path):
    """MemoryManager.handle_tool_call returns `provider.handle_tool_call(...)`
    WITHOUT awaiting it (see agent/memory_manager.py:453). The result is
    then passed to `tool_executor.py:906` which does `len(function_result)`.

    If our handle_tool_call is `async def`, the returned value is a
    coroutine — len() raises TypeError, killing the agent turn.

    Regression test: caught during live install (2026-06-02).
    """
    p, mcp = _make_provider_with_mock_client(tmp_path)
    mcp.call_tool.return_value = "[]"

    result = p.handle_tool_call("gbrain_search", {"query": "x"})

    # Must be a real str, not a coroutine
    assert isinstance(result, str), f"got {type(result).__name__}, expected str"
    # And must work with len() (what tool_executor.py:906 does)
    assert len(result) >= 0  # would raise TypeError on coroutine
