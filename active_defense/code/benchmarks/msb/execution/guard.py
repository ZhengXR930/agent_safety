"""Reusable baseline adapters for the official MSB runner."""

from __future__ import annotations

import asyncio
import contextlib
import json
import os
import shutil
import signal
import subprocess
import sys
from pathlib import Path

try:
    from code.baselines.clawguard.adapter import ClawGuardScanner
except ModuleNotFoundError:  # external MSB runner imports from active_defense/code
    from baselines.clawguard.adapter import ClawGuardScanner

HERE = Path(__file__).resolve().parent
REPO = Path(__file__).resolve().parents[4]
BENCHMARKS = REPO.parent / "benchmarks"
EVENTS = Path(os.environ.get(
    "ACTIVE_DEFENSE_EVENT_LOG", "/tmp/active_defense_msb_events.jsonl"))


class StackOneGuard:
    def __init__(self) -> None:
        self.cache = {}
        node = BENCHMARKS / "external/defender/.runtime/node-v22.17.0-linux-x64/bin/node"
        server = (REPO / "code/benchmarks/mcptox/execution/"
                  "defender_jsonl_server.mjs")
        self.proc = subprocess.Popen(
            [str(node), str(server)], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True, bufsize=1
        )

    async def check(self, text: str, location: str, tool_name: str) -> bool:
        key = (text, location, tool_name)
        if key in self.cache:
            allowed, result = self.cache[key]
            _record("stackone", location, tool_name, allowed, {**result, "cached": True})
            return allowed
        assert self.proc.stdin and self.proc.stdout
        self.proc.stdin.write(json.dumps({"text": text, "tool_name": tool_name}) + "\n")
        self.proc.stdin.flush()
        result = json.loads(self.proc.stdout.readline())
        allowed = bool(result.get("allowed", True))
        self.cache[key] = (allowed, result)
        _record("stackone", location, tool_name, allowed, result)
        return allowed


class MCPGuard:
    def __init__(self) -> None:
        self.cache = {}
        repo = BENCHMARKS / "external/MCP-Guard"
        sys.path.insert(0, str(repo))
        previous = Path.cwd()
        try:
            os.chdir(repo)
            from src.mcp_guard.core import guardrail_scan
            from src.mcp_guard.schemas import GuardrailRequest
        finally:
            os.chdir(previous)
        self.scan = guardrail_scan
        self.request = GuardrailRequest

    async def check(self, text: str, location: str, tool_name: str) -> bool:
        key = (text, location, tool_name)
        if key in self.cache:
            allowed, details = self.cache[key]
            _record("mcpguard", location, tool_name, allowed, {**details, "cached": True})
            return allowed
        detail = EVENTS.with_suffix(".detector.log")
        detail.parent.mkdir(parents=True, exist_ok=True)
        with detail.open("a", encoding="utf-8") as log, contextlib.redirect_stdout(log), contextlib.redirect_stderr(log):
            result = await self.scan(
                self.request(tool_name=tool_name, tool_description=text, tool_input_schema={})
            )
        if hasattr(result, "dict"):
            result = result.dict()
        allowed = bool(result.get("allowed", True))
        details = {"stage": result.get("detection_stage")}
        self.cache[key] = (allowed, details)
        _record("mcpguard", location, tool_name, allowed, details)
        return allowed


class PipelockGuard:
    """MCP-native response scanner using upstream ``pipelock mcp scan``.

    The adapter only translates the benchmark interception point into a valid
    MCP JSON-RPC response. Detection rules and thresholds remain the upstream
    balanced preset; no benchmark labels or task-specific policy are used.
    """

    def __init__(self) -> None:
        self.cache = {}
        binary = os.environ.get("PIPELOCK_BIN") or shutil.which("pipelock")
        if not binary:
            raise RuntimeError("Set PIPELOCK_BIN to the official Pipelock binary")
        config = os.environ.get("PIPELOCK_CONFIG")
        self.command = [binary, "mcp", "scan", "--json"]
        if config:
            self.command.extend(["--config", config])
        self.proc: asyncio.subprocess.Process | None = None
        self.scan_timeout = float(os.environ.get("PIPELOCK_SCAN_TIMEOUT", "30"))

    async def _start(self) -> asyncio.subprocess.Process:
        if self.proc is None or self.proc.returncode is not None:
            self.proc = await asyncio.create_subprocess_exec(
                *self.command,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.DEVNULL,
                start_new_session=True,
            )
        return self.proc

    async def _discard(self) -> None:
        proc, self.proc = self.proc, None
        if proc is None or proc.returncode is not None:
            return
        if proc.stdin:
            proc.stdin.close()
        with contextlib.suppress(ProcessLookupError):
            os.killpg(proc.pid, signal.SIGTERM)
        try:
            await asyncio.wait_for(proc.wait(), timeout=2)
        except asyncio.TimeoutError:
            with contextlib.suppress(ProcessLookupError):
                os.killpg(proc.pid, signal.SIGKILL)
            await proc.wait()

    async def check(self, text: str, location: str, tool_name: str) -> bool:
        key = (text, location, tool_name)
        if key in self.cache:
            allowed, result = self.cache[key]
            _record("pipelock", location, tool_name, allowed, {**result, "cached": True})
            return allowed
        proc = await self._start()
        assert proc.stdin and proc.stdout
        if location == "metadata":
            result_payload = {
                "tools": [{"name": tool_name, "description": text, "inputSchema": {"type": "object"}}]
            }
        else:
            result_payload = {"content": [{"type": "text", "text": text}]}
        message = {"jsonrpc": "2.0", "id": 1, "result": result_payload}
        proc.stdin.write((json.dumps(message, ensure_ascii=False) + "\n").encode())
        await proc.stdin.drain()
        try:
            line = await asyncio.wait_for(proc.stdout.readline(), self.scan_timeout)
        except asyncio.TimeoutError:
            await self._discard()
            raise RuntimeError(
                f"Pipelock scanner timed out after {self.scan_timeout:g}s"
            ) from None
        if not line:
            await self._discard()
            raise RuntimeError("Pipelock scanner exited without a response")
        try:
            result = json.loads(line)
        except json.JSONDecodeError as exc:
            await self._discard()
            raise RuntimeError("Pipelock scanner returned invalid JSON") from exc
        allowed = bool(result.get("clean", False))
        details = {
            "action": result.get("action"),
            "matches": [m.get("pattern_name") for m in result.get("matches", [])],
        }
        self.cache[key] = (allowed, details)
        _record("pipelock", location, tool_name, allowed, details)
        return allowed


class ClawGuard:
    """MSB content_guard adapter using upstream ClawGuard rules."""

    def __init__(self) -> None:
        self.scanner = ClawGuardScanner(EVENTS.with_suffix(".clawguard_cache.json"))

    async def check(self, text: str, location: str, tool_name: str) -> bool:
        location_text = str(location or "")
        if location_text in {"metadata", "tool", "tool_description", "schema"}:
            result = self.scanner.scan_catalog_tool(tool_name, text, {})
        else:
            result = self.scanner.scan_observation(tool_name, text, location_text)
        allowed = bool(result.get("allowed", True))
        _record("clawguard", location_text, tool_name, allowed, {
            "sanitized_changed": bool(result.get("sanitized_changed", False)),
            "secret_hits": result.get("secret_hits", []),
            "checks": result.get("checks", []),
            "approval_is_deny": self.scanner.approval_is_deny,
        })
        return allowed


def _record(baseline: str, location: str, tool_name: str, allowed: bool, details: dict) -> None:
    EVENTS.parent.mkdir(parents=True, exist_ok=True)
    with EVENTS.open("a", encoding="utf-8") as f:
        f.write(json.dumps({"baseline": baseline,
                            "case_id": os.environ.get("LANGSMITH_PROJECT"),
                            "location": location, "tool_name": tool_name,
                            "allowed": allowed, "details": details}, ensure_ascii=False) + "\n")


_GUARDS = {}


def get_guard(name: str):
    if name == "none":
        return None
    if name not in _GUARDS:
        if name == "stackone":
            _GUARDS[name] = StackOneGuard()
        elif name == "mcpguard":
            _GUARDS[name] = MCPGuard()
        elif name == "pipelock":
            _GUARDS[name] = PipelockGuard()
        elif name == "clawguard":
            _GUARDS[name] = ClawGuard()
        else:
            raise ValueError(f"unknown baseline guard: {name}")
    return _GUARDS[name]
