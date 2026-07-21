"""Collect a registration-time MCP ``tools/list`` snapshot from a trusted command.

This utility never invokes a tool.  It performs only initialize, initialized, and
tools/list, then stores the exact server response with command/source provenance.
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import selectors
import subprocess
import time
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


def collect(command: list[str], timeout: float = 30.0,
            extra_env: dict[str, str] | None = None) -> tuple[dict, str]:
    environment = dict(os.environ)
    environment.update(extra_env or {})
    process = subprocess.Popen(
        command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        text=True, bufsize=1, env=environment)
    assert process.stdin is not None and process.stdout is not None and process.stderr is not None
    messages = [
        {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {
            "protocolVersion": "2025-06-18", "capabilities": {},
            "clientInfo": {"name": "trusted-schema-registration", "version": "1"}}},
        {"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}},
        {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
    ]
    for message in messages:
        process.stdin.write(json.dumps(message, separators=(",", ":")) + "\n")
    process.stdin.flush()
    selector = selectors.DefaultSelector()
    selector.register(process.stdout, selectors.EVENT_READ, "stdout")
    selector.register(process.stderr, selectors.EVENT_READ, "stderr")
    deadline, errors = time.monotonic() + timeout, []
    try:
        while time.monotonic() < deadline:
            if process.poll() is not None and not selector.get_map():
                break
            for key, _ in selector.select(timeout=min(0.5, max(0, deadline - time.monotonic()))):
                line = key.fileobj.readline()
                if not line:
                    selector.unregister(key.fileobj)
                    continue
                if key.data == "stderr":
                    errors.append(line.rstrip())
                    continue
                try:
                    response = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if response.get("id") == 2:
                    if response.get("error"):
                        raise RuntimeError("tools/list error: " + json.dumps(response["error"]))
                    return response["result"], "\n".join(errors[-40:])
        detail = "\n".join(errors[-40:])
        raise RuntimeError(f"tools/list unavailable (exit={process.poll()}): {detail}")
    finally:
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=3)


async def collect_sdk(command: list[str], timeout: float,
                      extra_env: dict[str, str] | None = None) -> tuple[dict, str]:
    """Use the reference MCP client so protocol framing/version negotiation is exact."""
    parameters = StdioServerParameters(
        command=command[0], args=command[1:], env=extra_env or None)
    async with stdio_client(parameters, errlog=subprocess.DEVNULL) as (read, write):
        async with ClientSession(read, write) as session:
            await asyncio.wait_for(session.initialize(), timeout=timeout)
            result = await asyncio.wait_for(session.list_tools(), timeout=timeout)
            return result.model_dump(by_alias=True, exclude_none=True), ""


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--server", required=True)
    parser.add_argument("--source-url", required=True)
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--timeout", type=float, default=30)
    parser.add_argument("--env", action="append", default=[], metavar="NAME=VALUE",
                        help="non-secret registration placeholder required for server startup")
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    command = args.command[1:] if args.command[:1] == ["--"] else args.command
    if not command:
        raise ValueError("command is required after --")
    extra_env = dict(item.split("=", 1) for item in args.env)
    result, stderr = asyncio.run(collect_sdk(command, args.timeout, extra_env))
    tools = result.get("tools") or []
    canonical = json.dumps(tools, sort_keys=True, ensure_ascii=False,
                           separators=(",", ":"), default=str)
    document = {
        "server": args.server, "source_url": args.source_url,
        "source_commit": args.source_commit, "command": command,
        "startup_env_names": sorted(extra_env),
        "schema_hash": hashlib.sha256(canonical.encode()).hexdigest(),
        "tool_count": len(tools), "tools": tools, "stderr_tail": stderr,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(document, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"server": args.server, "tool_count": len(tools),
                      "schema_hash": document["schema_hash"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
