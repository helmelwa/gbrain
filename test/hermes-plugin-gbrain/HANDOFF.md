# GBrain Memory Provider Plugin — Handoff for New Agent

**Date:** 2026-06-02
**Goal:** Build a working `MemoryProvider` plugin for Hermes Agent that talks to a
local GBrain via MCP stdio. Previous attempt got 90% there but had stability
issues. This document is the complete handoff.

---

## 1. Background

**User:** Wladimir Helmel (Russian-speaking, prefers detailed answers).
**Setup:** Linux 6.8, Python 3.12, GBrain 0.41.29.0 at `/root/gbrain` (Docker Postgres).
**Hermes install:** Source at `/home/lighthouse/.hermes/hermes-agent/`.
**User Hermes home:** `/root/.hermes/` (this is a symlink, real path is
`/home/lighthouse/.hermes/`, see Memory).

The user already has 146k pages in their GBrain. They want a Hermes memory
plugin that:
- Surfaces GBrain content automatically in every turn (prefetch)
- Exposes `gbrain_search` / `gbrain_get_page` / `gbrain_recall` as agent tools
- Saves new facts automatically after each turn (sync_turn)
- Survives session restarts (the killer feature vs. file-based `MEMORY.md`)

---

## 2. Reference: How Memory Providers Work in Hermes

**Read these first** (official docs, fetch with `web_extract` if needed):
- https://hermes-agent.nousresearch.com/docs/developer-guide/memory-provider-plugin
- https://hermes-agent.nousresearch.com/docs/user-guide/features/memory-providers
- https://docs.mem0.ai/integrations/hermes (reference implementation)

**Key docs from official source (extracted earlier):**

```python
# REQUIRED methods (must implement):
def name(self) -> str: ...
def is_available(self) -> bool: ...                # NO network calls
def initialize(self, session_id, **kwargs) -> None: ...
def get_tool_schemas(self) -> list[dict]: ...
def handle_tool_call(self, tool_name, args, **kwargs) -> str: ...  # SYNC, returns JSON str
def get_config_schema(self) -> list[dict]: ...
def save_config(self, values, hermes_home) -> None: ...

# OPTIONAL hooks (the value-add):
def system_prompt_block(self) -> str: ...          # static text, injected into system prompt
async def prefetch(self, query, *, session_id="") -> str: ...  # before each turn, return markdown
async def queue_prefetch(self, query, *, session_id="") -> None: ...  # after each turn
async def sync_turn(self, user, assistant, *, session_id="", messages=None) -> None: ...  # non-blocking
async def on_session_end(self, messages) -> None: ...
def shutdown(self) -> None: ...
```

**Critical contracts** (learned the hard way):
- `handle_tool_call` MUST be **sync** (not `async def`). `MemoryManager.handle_tool_call`
  at `agent/memory_manager.py:453` does NOT await — it returns the result directly.
  Then `agent/tool_executor.py:906` does `len(function_result)`. An async def
  returns a coroutine → `TypeError: object of type 'coroutine' has no len()`.
- `prefetch` / `queue_prefetch` / `sync_turn` CAN be async. MemoryManager
  handles them in fire-and-forget style.
- `sync_turn` MUST be non-blocking. Use `asyncio.create_task()` or
  `threading.Thread(daemon=True)`.
- Only ONE external memory provider can be active at a time
  (set via `memory.provider` in `~/.hermes/config.yaml`). Built-in
  `MEMORY.md`/`USER.md` coexists.

**Reference impl: Mem0 plugin** (374 lines, bundled, works correctly):
`/home/lighthouse/.hermes/hermes-agent/plugins/memory/mem0/__init__.py`
Note how it does `from agent.memory_provider import MemoryProvider` directly
(works because it's bundled — see Section 5).

---

## 3. Reference: How GBrain Works

**Read these:**
- `/root/gbrain/docs/guides/brain-vs-memory.md` — mental model: GBrain = world
  knowledge (people, companies, ideas), built-in MEMORY.md = operational state
  (preferences, decisions). They are complementary, not competing.
- `/root/gbrain/docs/mcp/DEPLOY.md` — MCP server deploy
- `gbrain --help` and `gbrain serve --help` (CLI subcommands)

**GBrain basics:**
- CLI binary at `/root/.local/bin/gbrain` (also in PATH)
- Config: `~/.gbrain/config.json`
- MCP server: `gbrain serve` (stdio, JSON-RPC). Talk to it via stdin/stdout.
- Operations: 47+ tools. The ones we use: `search`, `get_page`, `recall`, `extract_facts`, `put_page`.
- **Critical instability:** GBrain releases daily. Operation names may rename.
  Our plugin uses MCP `tools/list` discovery to avoid hardcoding — but the
  NAMES we ask for (`search`, `get_page`, etc.) are still hardcoded. If
  GBrain renames `search` → `synthesize`, the plugin silently breaks.

---

## 4. Existing Artifacts

**Source code** at `/root/gbrain/test/hermes-plugin-gbrain/`:

```
pyproject.toml                                        # pytest config (markers: unit, integration)
src/plugins/memory/gbrain/__init__.py    (333 lines)  # GBrainMemoryProvider class
src/plugins/memory/gbrain/mcp_client.py (116 lines)  # subprocess + JSON-RPC transport
tests/conftest.py                          (152 lines)  # fixtures, brain init helper
tests/test_provider.py                     (328 lines)  # 10 unit tests
tests/test_session_end.py                  (97 lines)   # 5 tests for on_session_end
tests/test_system_prompt.py                (63 lines)   # 4 tests for system_prompt_block
tests/test_queue_prefetch_failures.py      (123 lines)  # 4 tests for queue_prefetch failure
tests/test_handle_tool_call.py             (188 lines)  # 9 tests for handle_tool_call
```

**Test status:** 32/32 unit tests pass in 0.05s. 7 integration tests pass in ~67s.
**Total: 39 passing tests.**

**Production path:** The plugin is also installed at `~/.hermes/plugins/gbrain/`
(user-install). It has been actively used but with stability issues (see
Section 6).

---

## 5. The 4 Critical Bugs (already fixed in code, may regress)

Each of these was discovered during live testing, NOT unit testing. They
illustrate why live integration tests matter.

### Bug 5.1: `register(ctx)` used wrong method
**Original (broken):**
```python
def register(ctx):
    ctx.add_provider(GBrainMemoryProvider())  # AttributeError
```
**Fix:** Use `ctx.register_memory_provider(...)`. The `_ProviderCollector`
class (Hermes' internal) has `register_memory_provider`, not `add_provider`.
`_add_provider` is a `MemoryManager` method, not available on the plugin
context.

### Bug 5.2: ABC import fails for user-installed plugins
**Original (broken):**
```python
from agent.memory_provider import MemoryProvider  # ImportError for user-install
class GBrainMemoryProvider(MemoryProvider): ...
```
**Fix option A (current code):** Try/except fallback to `MemoryProvider = object`.
This makes the plugin LOAD but breaks isinstance checks. **NOT recommended
for production.**

**Fix option B (recommended, the user wants this):** Install as **bundled**
plugin at `/home/lighthouse/.hermes/hermes-agent/plugins/memory/gbrain/`.
Hermes' loader injects `plugins.memory` into `sys.modules` before exec,
so `from agent.memory_provider import MemoryProvider` works.

### Bug 5.3: `handle_tool_call` was async
**Original (broken):**
```python
async def handle_tool_call(self, name, args, **kwargs) -> str:
    return self._mcp.call_tool(mcp_name, args, timeout=10.0)
```
**Fix:** Make it sync. `MemoryManager.handle_tool_call` (memory_manager.py:453)
does `return provider.handle_tool_call(...)` without await, then
`tool_executor.py:906` does `len(function_result)`. An async def returns
coroutine → `TypeError: object of type 'coroutine' has no len()`.

**Regression test added** (test_handle_tool_call.py):
`test_handle_tool_call_is_synchronous_not_coroutine` — asserts
`isinstance(result, str)` not a coroutine.

### Bug 5.4: mcp_servers.gbrain name collision
There was a `mcp_servers.gbrain` block in `~/.hermes/config.yaml` pointing
to `http://localhost:3131/mcp` with a bearer token. The user removed it
on 2026-06-02. This was **causing name conflicts** with our memory plugin's
`gbrain_search` tool. The user now has ONLY our plugin managing `gbrain_*`
tools, which is correct.

---

## 6. Remaining Issues (where previous attempt stopped)

### 6.1 Plugin doesn't always register in new sessions
Live evidence (session `20260602_113349_b845bc`):
- `Memory provider 'gbrain' registered (3 tools)` log line **missing**
- No `gbrain.*` log lines from our `logger.info()` calls
- Agent used `terminal` + `read_file` instead of `gbrain_*` tools

**Hypothesis:** Python module caching OR `from agent.memory_provider`
fallback to `object` means the class is loaded but doesn't pass ABC checks,
so MemoryManager's isinstance guard may skip it in some code paths.

**Diagnostic script** at `/tmp/diag_gbrain.py`:
```bash
python3 /tmp/diag_gbrain.py
```
Confirms loadable, but MRO = `[GBrainMemoryProvider, object]` (not
`[GBrainMemoryProvider, MemoryProvider, object]`). This is the smoking gun.

### 6.2 MRO problem (root cause of 6.1)
The fallback `MemoryProvider = object` makes the plugin **loadable but
non-ABC-compliant**. Fix is to install as bundled (Section 5 Bug 5.2 option B).

---

## 7. Concrete Plan for New Agent

**Estimated time: 30-60 minutes. TDD discipline: RED → GREEN → REFACTOR.**

### Step 1: Move plugin to bundled location
```bash
# Backup current
cp -r /home/lighthouse/.hermes/hermes-agent/plugins/memory/mem0 /tmp/mem0_ref
# Copy our plugin to bundled location
cp -r /root/.hermes/plugins/gbrain /home/lighthouse/.hermes/hermes-agent/plugins/memory/gbrain
# Remove user-install to avoid duplicates
rm -rf /root/.hermes/plugins/gbrain
# Clear all stale bytecode
find /home/lighthouse/.hermes/hermes-agent -name '__pycache__' -path '*gbrain*' -exec rm -rf {} +
find /root/.hermes -name '__pycache__' -path '*gbrain*' -exec rm -rf {} +
```

### Step 2: Remove the `MemoryProvider = object` fallback
In `/home/lighthouse/.hermes/hermes-agent/plugins/memory/gbrain/__init__.py`,
replace the `try/except` block at top of file with a clean direct import:
```python
from agent.memory_provider import MemoryProvider
```
**RED test first:** Run `python3 -m pytest tests/test_provider.py -v -k "isinstance or subclass"`.
If we have a test asserting `isinstance(provider, MemoryProvider)`, it should
**fail** before this change and **pass** after. (We may need to add this test.)

### Step 3: Verify MRO is correct
```bash
python3 -c "
import sys
sys.path.insert(0, '/home/lighthouse/.hermes/hermes-agent')
from plugins.memory import load_memory_provider
p = load_memory_provider('gbrain')
print('MRO:', [c.__name__ for c in type(p).__mro__])
# Expected: ['GBrainMemoryProvider', 'MemoryProvider', 'object']
"
```

### Step 4: Run full test suite, all should pass
```bash
cd /root/gbrain/test/hermes-plugin-gbrain
python3 -m pytest -m unit  # should be ~0.05s
python3 -m pytest -m integration  # should be ~67s
```

### Step 5: Live integration test
```bash
hermes memory setup gbrain     # should say "saved to config.yaml"
hermes memory status          # should show gbrain as active
hermes chat "What do I know about the Citation Fixer skill in my GBrain?"
# Get session ID from TUI, then:
grep "$SESSION_ID" ~/.hermes/logs/agent.log | grep -E 'gbrain|tool gbrain'
# Should see:
#   Memory provider 'gbrain' registered (3 tools)
#   gbrain plugin initialized: session=XXX
#   gbrain.system_prompt_block called: 295 chars
#   gbrain.prefetch called: query='What...'
#   gbrain.handle_tool_call: name='gbrain_search'
#   gbrain.sync_turn queued: user=NN assistant=MM
```

### Step 6: If all 6 log lines appear → Phase 1 done.
If any are missing → that hook is broken → write a test for it, fix it, repeat.

---

## 8. Anti-patterns to Avoid

1. **Don't fall back to `MemoryProvider = object` silently.** This hides
   bugs and produces non-ABC-compliant plugins. If `from agent.memory_provider`
   fails, **fix the install location**, don't mask the failure.

2. **Don't use `async def handle_tool_call`.** It MUST be sync. Write
   tests asserting `isinstance(result, str)`, not a coroutine.

3. **Don't trust `pytest .lastfailed == {}` as proof of green.** We had
   `lastfailed = {}` and still had broken bugs in live. Always live-test
   at least once with the user's real config.

4. **Don't add tests as a "checklist" exercise.** Each test should
   represent a real failure mode we want to catch. If you can't name
   the bug it would catch, don't write it.

5. **Don't hardcode GBrain operation names unless you have to.** Use
   MCP `tools/list` discovery. If you must hardcode `search`/`get_page`,
   document which GBrain version was tested and add a note that
   `gbrain doctor` can be used to verify operations exist.

6. **Don't skip the `_hermes_user_memory.gbrain` vs `plugins.memory.gbrain`
   namespace distinction.** Different code paths, different cache
   behavior, different ABC import success.

---

## 9. Useful Commands

```bash
# Diagnostic
python3 /tmp/diag_gbrain.py

# Tests
cd /root/gbrain/test/hermes-plugin-gbrain
python3 -m pytest -m unit --durations=5
python3 -m pytest -m integration --durations=5

# Live
hermes memory status
hermes memory setup gbrain
hermes chat "What do I know about X?"

# Logs
tail -F ~/.hermes/logs/agent.log | grep -iE 'gbrain|memory|error'
sed -n '/SESSION_ID.*ERROR/,/^2026/p' ~/.hermes/logs/errors.log

# GBrain health
gbrain doctor 2>&1 | tail -5
```

---

## 10. Key File Paths

| Path | Purpose |
|---|---|
| `/root/gbrain/test/hermes-plugin-gbrain/src/plugins/memory/gbrain/` | Source code (read-only reference after Step 1) |
| `/home/lighthouse/.hermes/hermes-agent/plugins/memory/gbrain/` | Bundled install (production after Step 1) |
| `/home/lighthouse/.hermes/hermes-agent/plugins/memory/mem0/` | Reference impl (read for patterns) |
| `/home/lighthouse/.hermes/hermes-agent/agent/memory_provider.py` | ABC definition |
| `/home/lighthouse/.hermes/hermes-agent/agent/memory_manager.py` | MemoryManager (line 453 = handle_tool_call routing) |
| `/home/lighthouse/.hermes/hermes-agent/agent/tool_executor.py` | tool_executor.py:906 = the `len()` that fails on coroutine |
| `/root/.hermes/config.yaml` | `memory.provider: gbrain` lives here |
| `/root/.gbrain/config.json` | GBrain config (managed by gbrain CLI, don't touch) |
| `/root/.hermes/logs/agent.log` | Memory provider logs (look for `Memory provider 'gbrain' registered`) |
| `/root/.hermes/logs/errors.log` | Error logs (look for `Outer loop error`, `TypeError: coroutine has no len()`) |
| `/tmp/diag_gbrain.py` | Diagnostic that checks load/MRO/registration |

---

## 11. When to Ask the User

The user is hands-on, knows their stack, and prefers evidence over
speculation. They will:
- Run live tests in TUI themselves
- Paste session IDs and log lines
- Say "stop, do X instead" firmly when something's wrong

Don't:
- Spend more than 1 hour without surfacing findings
- Hide failures behind optimistic language
- Make changes the user didn't approve

Do:
- Show diffs before applying
- Show test output (red AND green)
- Cite exact file:line for claims
- Propose the smallest change that fixes the actual bug

---

## 12. End State

When done correctly, every Hermes chat turn produces this in `agent.log`:
```
INFO  agent.memory_manager: Memory provider 'gbrain' registered (3 tools)
INFO  plugins.memory.gbrain: gbrain plugin initialized: session=XXX transport=stdio
INFO  plugins.memory.gbrain: gbrain.system_prompt_block called: 295 chars
INFO  plugins.memory.gbrain: gbrain.prefetch called: query='What do I know about...'
INFO  plugins.memory.gbrain: gbrain.prefetch MCP search returned NNN chars
INFO  plugins.memory.gbrain: gbrain.handle_tool_call: name='gbrain_search' args_keys=['query', 'limit']
INFO  plugins.memory.gbrain: gbrain.sync_turn queued: user=NN assistant=MM
```

All 7 lines, every turn, no errors in `errors.log`. That's the definition
of done.
