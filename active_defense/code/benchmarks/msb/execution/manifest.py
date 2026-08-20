#!/usr/bin/env python3
"""CLI wrapper for the centralized trusted MSB case manifest."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
from pathlib import Path

from code.ours.manifests.msb import attest_tools, build, case_ids_from_logs


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


async def _discover_tools(root: Path, servers: list[str],
                          local_servers: dict[str, Path]) -> dict:
    """Snapshot clean MCP ``tools/list`` results into a trusted manifest."""
    from mcp_use import MCPClient

    result = {"schema": "msb-mcp-tool-manifest-v1", "servers": {}}
    for server_name in servers:
        source = local_servers.get(server_name)
        if source is not None:
            source = source.resolve()
            # Preserve the venv launcher path; resolving its symlink would
            # execute the base interpreter without the server dependencies.
            python = root / "data/tools/attack_tools/.venv/bin/python"
            client = MCPClient.from_dict({"mcpServers": {server_name: {
                "command": str(python), "args": [str(source)]}}})
        else:
            source = (root / "data" / "tools" / "normal_tools" /
                      f"{server_name}.json")
            if not source.is_file():
                source = (root / "data" / "tools" / "support_tools" /
                          f"{server_name}.json")
            if not source.is_file():
                raise FileNotFoundError(
                    f"missing clean MCP config: {server_name}")
            client = MCPClient.from_config_file(str(source))
        try:
            await client.create_all_sessions()
            tools = []
            for session in client.sessions.values():
                for model in session.connector._tools:
                    raw = model.model_dump(mode="json")
                    tools.append({
                        "name": raw["name"],
                        "description": raw.get("description") or "",
                        "inputSchema": raw.get("inputSchema") or {
                            "type": "object", "properties": {}},
                        "outputSchema": raw.get("outputSchema"),
                        "annotations": raw.get("annotations"),
                    })
        finally:
            await client.close_all_sessions()
        if not tools:
            raise RuntimeError(f"clean MCP server exposed no Tools: {server_name}")
        result["servers"][server_name] = {
            "server_identity": server_name,
            "source_config": str(source.relative_to(root)),
            "source_config_sha256": _digest(source),
            "tools": attest_tools(server_name, tools),
        }
    return result


def _refresh_attestations(path: Path) -> dict:
    """Re-apply operator attestations without changing tools/list evidence."""
    manifest = json.loads(path.read_text(encoding="utf-8"))
    if manifest.get("schema") != "msb-mcp-tool-manifest-v1":
        raise ValueError("unsupported MSB Tool manifest schema")
    for name, server in (manifest.get("servers") or {}).items():
        server["tools"] = attest_tools(name, server.get("tools") or [])
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--msb-root", type=Path, required=True)
    parser.add_argument("--config", type=Path)
    parser.add_argument("--baseline-log-dir", type=Path)
    parser.add_argument("--baseline")
    parser.add_argument("--expected-case-count", type=int)
    parser.add_argument("--server", action="append")
    parser.add_argument("--refresh-attestations", type=Path)
    parser.add_argument(
        "--local-server", action="append", default=[], metavar="NAME=PATH",
        help="snapshot a clean local server implementation instead of its remote config")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = args.msb_root.resolve()
    local_servers = {}
    for value in args.local_server:
        name, separator, path = value.partition("=")
        if not separator or not name or not path:
            parser.error("--local-server must be NAME=PATH")
        local_servers[name] = (root / path).resolve()
    servers = list(dict.fromkeys((args.server or []) + list(local_servers)))
    if args.refresh_attestations:
        if servers or args.config:
            parser.error(
                "--refresh-attestations cannot be combined with discovery or case generation")
        manifest = _refresh_attestations(args.refresh_attestations.resolve())
    elif servers:
        manifest = asyncio.run(_discover_tools(
            root, servers, local_servers))
    else:
        if args.config is None:
            parser.error("--config is required unless --server is supplied")
        allowed = None
        alignment = None
        if args.baseline_log_dir or args.baseline:
            if not args.baseline_log_dir or not args.baseline:
                parser.error(
                    "--baseline-log-dir and --baseline must be supplied together")
            allowed = case_ids_from_logs(
                args.baseline_log_dir.resolve(), args.baseline)
            alignment = {
                "baseline": args.baseline,
                "completed_case_count": len(allowed),
            }
        manifest = build(root, args.config.resolve(),
                         allowed_case_ids=allowed, alignment=alignment)
        if (args.expected_case_count is not None and
                manifest["case_count"] != args.expected_case_count):
            raise ValueError(
                f"expected {args.expected_case_count} cases, got "
                f"{manifest['case_count']}")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.output.with_suffix(args.output.suffix + ".tmp")
    temporary.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")
    temporary.replace(args.output)
    print(json.dumps({"output": str(args.output),
                      "count": (manifest.get("case_count") or
                                len(manifest.get("servers", {})))}))


if __name__ == "__main__":
    main()
