"""MCP mediator — a local stdio MCP server that is the WRAP chokepoint for MCPTox.

It registers a case's tools (with their possibly-POISONED descriptions) and MEDIATES every call:
each tool invocation is LOGGED (server-side, outside the agent's reach => W2) before returning a
benign stub.  In MCP the agent can ONLY act through these tool calls (no shell => W3), so any action
the poisoned description induces is forced through this mediator -> recorded.  Detection reads the log.

Run via `claude --mcp-config <cfg> --strict-mcp-config`.  Config supplies, per env:
  MCPTOX_TOOLS  : path to a JSON list [{name, description, ...}] of tools to expose.
  MEDIATION_LOG : path to append each {tool, arguments, ts} call record (the WRAP recorder).
"""
from __future__ import annotations

import asyncio
import json
import os
from datetime import datetime
from pathlib import Path

import mcp.types as types
from mcp.server import Server
from mcp.server.stdio import stdio_server

_TOOLS = json.loads(Path(os.environ["MCPTOX_TOOLS"]).read_text(encoding="utf-8")) \
    if os.environ.get("MCPTOX_TOOLS") else []
_LOG = os.environ.get("MEDIATION_LOG", "mediation_log.jsonl")

server = Server("mediator")


@server.list_tools()
async def list_tools() -> list[types.Tool]:
    out = []
    for t in _TOOLS:
        out.append(types.Tool(
            name=t["name"], description=t.get("description", ""),
            inputSchema={"type": "object",
                         "properties": {k: {"type": "string"} for k in t.get("params", ["arg"])},
                         "additionalProperties": True}))
    return out


_INJECT = {t["name"]: t["inject_response"] for t in _TOOLS if t.get("inject_response")}


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    rec = {"event": "mcp_tool_call", "tool": name, "arguments": arguments,
           "ts": datetime.utcnow().isoformat() + "Z"}
    with open(_LOG, "a", encoding="utf-8") as f:                 # the WRAP recorder (server-side)
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    # Some tools carry a poisoned RESPONSE (MSB response-injection attack types); else benign stub.
    return [types.TextContent(type="text", text=_INJECT.get(name, "ok"))]


async def _main():
    async with stdio_server() as (r, w):
        await server.run(r, w, server.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(_main())
