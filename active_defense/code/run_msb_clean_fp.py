#!/usr/bin/env python3
"""Replay reachable benign MSB tool metadata to measure detector false positives."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path


REACHABLE_SERVERS = (
    "DuckDuckGo_Search_Server",
    "Flux_ImageGen_Server",
    "Office_Word_Document_Server",
    "Terminal_Controller",
)


async def main_async(args) -> None:
    msb_root = args.msb_root.resolve()
    sys.path.insert(0, str(msb_root))
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from mcp_use import MCPClient
    from msb_baseline_guard import get_guard

    clean_inputs = []
    for server in REACHABLE_SERVERS:
        config_path = msb_root / "data/tools/normal_tools" / f"{server}.json"
        config = json.loads(config_path.read_text(encoding="utf-8"))
        client = MCPClient.from_dict(config)
        try:
            sessions = await client.create_all_sessions()
            for session in sessions.values():
                for tool in await session.connector.list_tools():
                    clean_inputs.append(
                        {"server": server, "tool_name": tool.name, "description": str(tool.description)}
                    )
        finally:
            await client.close_all_sessions()

    # Deduplicate exact catalog entries while retaining server provenance.
    unique = {(x["server"], x["tool_name"], x["description"]): x for x in clean_inputs}
    clean_inputs = list(unique.values())
    guard = get_guard(args.baseline)
    blocked = 0
    rows = []
    for item in clean_inputs:
        allowed = await guard.check(item["description"], "clean_metadata", item["tool_name"])
        rows.append({**item, "allowed": allowed})
        blocked += not allowed
    result = {
        "benchmark": "MSB reachable clean MCP metadata catalog",
        "baseline": args.baseline,
        "servers": list(REACHABLE_SERVERS),
        "n": len(rows),
        "fp": blocked,
        "fpr": blocked / len(rows),
        "detector_utility": 1 - blocked / len(rows),
        "rows": rows,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({key: result[key] for key in ("baseline", "n", "fp", "fpr", "detector_utility")}, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--msb-root", type=Path, required=True)
    parser.add_argument("--baseline", choices=("stackone", "mcpguard", "pipelock"), required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    asyncio.run(main_async(args))


if __name__ == "__main__":
    main()
