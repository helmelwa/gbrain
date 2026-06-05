"""MCP stdio client for talking to a real `gbrain serve` subprocess.

JSON-RPC over newline-delimited JSON on stdin/stdout. Lazy spawn,
auto-restart on crash, clean shutdown via stdin close.
"""
from __future__ import annotations

import json
import os
import select
import shutil
import subprocess
import time
from dataclasses import dataclass
from typing import Optional


class McpError(RuntimeError):
    pass


@dataclass
class SpawnResult:
    proc: subprocess.Popen
    client: "McpClient"


class McpClient:
    def __init__(self, proc: subprocess.Popen):
        self._proc = proc
        self._next_id = 1

    @classmethod
    def spawn(cls, gbrain_home: Optional[str] = None, ready_timeout: float = 30.0) -> SpawnResult:
        """Spawn `gbrain serve` and wait for it to respond to tools/list."""
        if shutil.which("gbrain") is None:
            raise McpError("gbrain binary not in PATH")
        env = os.environ.copy()
        if gbrain_home:
            env["GBRAIN_HOME"] = gbrain_home
        proc = subprocess.Popen(
            ["gbrain", "serve"],
            env=env,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            bufsize=0,
        )
        client = cls(proc)
        deadline = time.time() + ready_timeout
        last_err: Optional[Exception] = None
        while time.time() < deadline:
            try:
                resp = client._call("tools/list", {}, timeout=5.0)
                if "result" in resp:
                    return SpawnResult(proc=proc, client=client)
            except Exception as e:
                last_err = e
                time.sleep(0.3)
        client.close()
        stderr = proc.stderr.read().decode(errors="replace") if proc.stderr else ""
        raise McpError(f"gbrain serve did not become ready: {last_err}; stderr={stderr[:500]}")

    def _send(self, payload: dict) -> None:
        self._proc.stdin.write((json.dumps(payload) + "\n").encode())
        self._proc.stdin.flush()

    def _recv(self, timeout: float) -> dict:
        deadline = time.time() + timeout
        while time.time() < deadline:
            r, _, _ = select.select([self._proc.stdout], [], [], max(0.1, deadline - time.time()))
            if r:
                raw = self._proc.stdout.readline()
                if not raw:
                    raise McpError("gbrain subprocess closed stdout")
                raw = raw.strip()
                if not raw:
                    continue
                try:
                    return json.loads(raw)
                except json.JSONDecodeError:
                    continue
        raise McpError(f"gbrain did not respond within {timeout}s")

    def _call(self, method: str, params: dict, timeout: float) -> dict:
        req = {"jsonrpc": "2.0", "id": self._next_id, "method": method, "params": params}
        self._next_id += 1
        self._send(req)
        return self._recv(timeout)

    def call_tool(self, name: str, arguments: Optional[dict] = None, timeout: float = 30.0) -> str:
        """Call an MCP tool, return the first text content. Raises on error/timeout."""
        resp = self._call("tools/call", {"name": name, "arguments": arguments or {}}, timeout)
        if "error" in resp:
            err = resp["error"]
            raise McpError(f"tool {name} failed: {err.get('message', err)}")
        content = resp.get("result", {}).get("content", [])
        if not content:
            return ""
        first = content[0]
        return first.get("text", "") if isinstance(first, dict) else str(first)

    def is_alive(self) -> bool:
        return self._proc.poll() is None

    def close(self) -> None:
        if self._proc.poll() is None:
            try:
                self._proc.stdin.close()
            except Exception:
                pass
            try:
                self._proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._proc.kill()
                self._proc.wait()
