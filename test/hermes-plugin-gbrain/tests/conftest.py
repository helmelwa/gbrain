"""Real GBrain subprocess fixtures for plugin tests.

Spawns `gbrain serve` as a real stdio subprocess per test, talks JSON-RPC.
Uses PGLite (zero-setup brain), one tmp dir per test for isolation.
"""
import json
import os
import select
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any

import pytest


# Skip everything if gbrain not in PATH
pytestmark = pytest.mark.skipif(
    shutil.which("gbrain") is None,
    reason="gbrain binary not in PATH",
)


def _gbrain_init(brain_dir: Path) -> None:
    """Initialize a PGLite brain (no embeddings) in brain_dir. Idempotent."""
    config_path = brain_dir / ".gbrain" / "config.json"
    if config_path.exists():
        return
    env = os.environ.copy()
    env["GBRAIN_HOME"] = str(brain_dir)
    r = subprocess.run(
        ["gbrain", "init", "--pglite", "--no-embedding"],
        env=env, capture_output=True, text=True, timeout=120,
    )
    if r.returncode != 0:
        raise RuntimeError(f"gbrain init failed: {r.stderr[:500] or r.stdout[:500]}")


class McpStdio:
    """Thin JSON-RPC client over `gbrain serve` stdio subprocess."""

    def __init__(self, proc: subprocess.Popen):
        self._proc = proc
        self._next_id = 1

    def _send(self, payload: dict) -> None:
        line = json.dumps(payload) + "\n"
        self._proc.stdin.write(line.encode())
        self._proc.stdin.flush()

    def _recv(self, timeout: float) -> dict:
        deadline = time.time() + timeout
        while time.time() < deadline:
            r, _, _ = select.select([self._proc.stdout], [], [], max(0.1, deadline - time.time()))
            if r:
                raw = self._proc.stdout.readline()
                if not raw:
                    raise RuntimeError("gbrain subprocess closed stdout")
                raw = raw.strip()
                if not raw:
                    continue
                try:
                    return json.loads(raw)
                except json.JSONDecodeError:
                    continue
        raise TimeoutError(f"gbrain did not respond within {timeout}s")

    def call(self, method: str, params: dict | None = None, timeout: float = 30.0) -> dict:
        req = {"jsonrpc": "2.0", "id": self._next_id, "method": method, "params": params or {}}
        self._next_id += 1
        self._send(req)
        return self._recv(timeout)

    def call_tool(self, name: str, arguments: dict | None = None, timeout: float = 30.0) -> dict:
        """Call an MCP tool, return the raw JSON-RPC response.

        Result shape on success: {"result": {"content": [{"type":"text","text":"<json>"}], ...}}
        On error: {"error": {"code": ..., "message": ...}}
        """
        return self.call("tools/call", {"name": name, "arguments": arguments or {}}, timeout)

    def tool_result_text(self, name: str, arguments: dict | None = None, timeout: float = 30.0) -> str:
        """Convenience: extract first text content. Raises if response is an error."""
        resp = self.call_tool(name, arguments, timeout)
        if "error" in resp:
            err = resp["error"]
            raise RuntimeError(f"tool {name} failed: {err.get('message', err)}")
        content = resp.get("result", {}).get("content", [])
        if not content:
            return ""
        return content[0].get("text", "")

    def close(self):
        if self._proc.poll() is None:
            self._proc.stdin.close()
            try:
                self._proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._proc.kill()
                self._proc.wait()


@pytest.fixture
def brain_dir(tmp_path) -> Path:
    """Hermetic PGLite brain per integration test.

    Function-scoped because PGLite is a single-writer engine (own comment
    in src/mcp/server.ts: 'orphaned serve processes accumulate and contend
    for the PGLite write lock'). One brain per test = clean isolation.

    Cost: ~7s setup per integration test. Acceptable for Phase 1.
    Future: switch to docker-compose pgvector for session-scoped brain.
    """
    bd = tmp_path / "brain"
    bd.mkdir()
    _gbrain_init(bd)
    return bd


@pytest.fixture
def gbrain_home_env(brain_dir: Path, monkeypatch) -> dict:
    """Set GBRAIN_HOME for the test, return the env dict."""
    monkeypatch.setenv("GBRAIN_HOME", str(brain_dir))
    return os.environ.copy()


@pytest.fixture
def gbrain_mcp(gbrain_home_env: dict) -> McpStdio:
    """Live `gbrain serve` subprocess scoped to brain_dir."""
    proc = subprocess.Popen(
        ["gbrain", "serve"],
        env=gbrain_home_env,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        bufsize=0,
    )
    client = McpStdio(proc)
    deadline = time.time() + 30
    last_err: Any = None
    while time.time() < deadline:
        try:
            resp = client.call("tools/list", timeout=5)
            if "result" in resp:
                return client
        except Exception as e:
            last_err = e
            time.sleep(0.3)
    client.close()
    stderr = proc.stderr.read().decode(errors="replace") if proc.stderr else ""
    raise RuntimeError(f"gbrain serve did not become ready: {last_err}\nstderr: {stderr[:500]}")
