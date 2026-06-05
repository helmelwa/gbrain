"""Unit tests for system_prompt_block.

system_prompt_block() returns static text that the MemoryManager injects
into the agent's system prompt. The text tells the model it has long-term
memory available (and how to use it). Per the official Hermes docs this
text is STATIC — dynamic recall context goes through prefetch(), not here.

Behavior:
  1. Returns a non-empty string.
  2. Mentions 'gbrain' so the model knows the backend.
  3. Does NOT include any dynamic query results (no markdown results).
  4. Is safe to call before initialize() — no required state.
"""
from __future__ import annotations

from pathlib import Path
import sys

import pytest

PLUGIN_ROOT = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(PLUGIN_ROOT))

from plugins.memory.gbrain import GBrainMemoryProvider  # noqa: E402


@pytest.mark.unit
def test_system_prompt_block_returns_non_empty_string():
    """Block is non-empty so MemoryManager has something to inject."""
    p = GBrainMemoryProvider()
    block = p.system_prompt_block()
    assert isinstance(block, str)
    assert len(block) > 0


@pytest.mark.unit
def test_system_prompt_block_mentions_gbrain_backend():
    """Agent should know the memory is GBrain-backed (transparency)."""
    p = GBrainMemoryProvider()
    block = p.system_prompt_block()
    assert "gbrain" in block.lower()


@pytest.mark.unit
def test_system_prompt_block_is_static_no_dynamic_content():
    """Block must not contain query results, page content, or call results.

    Dynamic recall goes through prefetch(), not the static block.
    """
    p = GBrainMemoryProvider()
    block = p.system_prompt_block()
    # Static block should be a brief description, not a wall of data
    assert len(block) < 1000, "block suspiciously long; maybe leaking prefetch data?"


@pytest.mark.unit
def test_system_prompt_block_safe_before_initialize():
    """No required state — must work on a fresh provider."""
    p = GBrainMemoryProvider()
    # No initialize() called. Should still return a valid block.
    block = p.system_prompt_block()
    assert isinstance(block, str)
    assert len(block) > 0
