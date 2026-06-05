"""Test that GBrainMemoryProvider properly subclasses Hermes' MemoryProvider ABC.

Background: HANDOFF.md §6.2. When the plugin is loaded from
~/.hermes/plugins/gbrain/ (user-install), the `agent` package is not on
sys.path, so the `from agent.memory_provider import MemoryProvider` fails.
The current code falls back to `MemoryProvider = object`, which makes the
plugin loadable but produces a non-ABC-compliant class:
  MRO = [GBrainMemoryProvider, object]  (BAD)
instead of the correct:
  MRO = [GBrainMemoryProvider, MemoryProvider, object]  (GOOD)

Hermes' MemoryManager and PluginLoader may guard registration on the ABC
(`isinstance` / ABC registration), so the silent fallback breaks live
registration in new sessions (HANDOFF.md §6.1).

This test loads the plugin in the SAME way Hermes' bundled plugin loader
does: by inserting /home/lighthouse/.hermes/hermes-agent onto sys.path
before importing. With the correct bundled install (Phase 1 Step 1+2),
the test must pass.
"""
import sys
from pathlib import Path

import pytest

# Match Hermes' bundled plugin loader: when loaded as
# plugins/memory/gbrain/__init__.py from inside the hermes-agent source
# tree, the parent of `plugins/` is on sys.path, so `import agent.*`
# works. We simulate that by inserting /home/lighthouse/.hermes/hermes-agent.
HERMES_AGENT_ROOT = Path("/home/lighthouse/.hermes/hermes-agent")
if str(HERMES_AGENT_ROOT) not in sys.path:
    sys.path.insert(0, str(HERMES_AGENT_ROOT))


@pytest.mark.unit
def test_gbrain_provider_subclasses_memory_provider_abc():
    """GBrainMemoryProvider must be a real subclass of MemoryProvider.

    Verifies the ABC is in the MRO. Catches the `MemoryProvider = object`
    fallback regression described in HANDOFF.md §5.2 and §6.2.
    """
    # Import MemoryProvider FIRST (with hermes-agent on sys.path) so the
    # plugin's `from agent.memory_provider import MemoryProvider` succeeds.
    from agent.memory_provider import MemoryProvider

    # Now import the plugin — this must use the REAL MemoryProvider, not
    # the `object` fallback. We import from the BUNDLED location because
    # that's where Phase 1 Step 1 installs it.
    bundled_plugin = HERMES_AGENT_ROOT / "plugins" / "memory" / "gbrain" / "__init__.py"
    assert bundled_plugin.exists(), (
        f"Bundled plugin not found at {bundled_plugin}. "
        "Phase 1 Step 1 (move to bundled location) must run first."
    )

    # Import by file path to bypass any sys.path-cached user-install copy.
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "bundled_gbrain_plugin", str(bundled_plugin)
    )
    assert spec is not None and spec.loader is not None, (
        f"Could not create module spec for {bundled_plugin}"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    ProviderClass = module.GBrainMemoryProvider
    mro_names = [c.__name__ for c in ProviderClass.__mro__]
    assert "MemoryProvider" in mro_names, (
        f"MemoryProvider missing from MRO: {mro_names}. "
        "The plugin is falling back to MemoryProvider=object. "
        "Phase 1 Step 2 (remove the silent fallback) must run."
    )
    # Also assert the strict subclass relationship (not just name in MRO).
    assert issubclass(ProviderClass, MemoryProvider), (
        f"issubclass(GBrainMemoryProvider, MemoryProvider) is False. "
        f"MRO: {mro_names}"
    )
