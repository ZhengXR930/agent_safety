"""Compile the clean MCPTox capability surface into one auditable EnvironmentPlan.

Exact name matches use version-pinned official ``tools/list`` schemas. Public
benchmark prompt shapes are used only when that official schema is unavailable;
their provenance is emitted beside, not inside, the runtime manifest.
"""
from __future__ import annotations

import argparse
import ast
import json
import re
from pathlib import Path

from code.defense.surveyor import Surveyor
from code.internal_client import client_for_model
from code.run_mcp_pilot import MCPTox, _canonical, _tool_blocks


def _fallback_input_schema(tool: dict) -> dict:
    """Recover the top-level wrapper actually documented by MCPTox.

    Some AdFin prompts list only ``request_data`` under Arguments while embedding
    path/query parameters in the preceding public description. They are still
    top-level fields in the calls expected by the benchmark wrapper.
    """
    arguments = list(map(str, tool.get("arguments") or []))
    required = list(map(str, tool.get("required") or []))
    description = str(tool.get("description", ""))
    match = re.search(r"parameters should be:\s*(\[.*?\])(?:\.|$)", description)
    if match:
        try:
            params = ast.literal_eval(match.group(1))
        except (SyntaxError, ValueError):
            params = []
        for param in params if isinstance(params, list) else []:
            if not isinstance(param, dict) or not param.get("name"):
                continue
            name = str(param["name"])
            if name not in arguments:
                arguments.append(name)
            if param.get("required") is True and name not in required:
                required.append(name)
    return {"type": "object", "properties": {name: {} for name in arguments},
            "required": required}


def compile_inputs(registry: dict, benchmark: dict) -> tuple[list[dict], list[dict]]:
    official = {(row["server"], row["name"]): row for row in registry["trusted_tools"]}
    tools, provenance = [], []
    for server in benchmark["servers"].values():
        server_name = str(server["server_name"])
        advertised = {row["name"]: row for row in _tool_blocks(server["clean_system_promot"])}
        for method in map(str, server.get("tool_names") or []):
            exact = official.get((server_name, method))
            if exact is not None:
                tool = dict(exact)
                source = "official-exact"
            else:
                fallback = advertised.get(method)
                if fallback is None:
                    raise ValueError(f"benchmark schema missing for {server_name}::{method}")
                tool = {
                    "name": method,
                    "description": fallback.get("description", ""),
                    "inputSchema": _fallback_input_schema(fallback),
                }
                source = "benchmark-interface-fallback"
            canonical = _canonical(server_name, method)
            tool["name"] = canonical
            # MCPTox exposes one complete request as its smallest commit unit
            # and has no post-call Agent observation turn.
            tool["effect"], tool["observation"] = True, False
            tools.append(tool)
            provenance.append({"capability": canonical, "server": server_name,
                               "method": method, "schema_source": source})
    return tools, provenance


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--registry", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--provenance", type=Path, required=True)
    parser.add_argument("--model", default="deepseek-chat")
    parser.add_argument("--no-summary-model", action="store_true")
    parser.add_argument("--reuse-descriptions", type=Path)
    args = parser.parse_args()
    registry = json.loads(args.registry.read_text(encoding="utf-8"))
    benchmark = json.loads(MCPTox.read_text(encoding="utf-8"))
    tools, provenance = compile_inputs(registry, benchmark)
    client = None if args.no_summary_model else client_for_model(args.model)
    plan = Surveyor(client, args.model).perceive_mcp_registration(tools)
    serialized = plan.to_dict()
    if args.reuse_descriptions:
        prior = json.loads(args.reuse_descriptions.read_text(encoding="utf-8"))
        prior_capabilities = prior.get("capabilities") or {}
        for name, capability in serialized["capabilities"].items():
            if name in prior_capabilities:
                capability["description"] = str(
                    prior_capabilities[name].get("description", capability["description"]))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(serialized, ensure_ascii=False, indent=2), encoding="utf-8")
    counts = {source: sum(row["schema_source"] == source for row in provenance)
              for source in ("official-exact", "benchmark-interface-fallback")}
    args.provenance.write_text(json.dumps({"counts": counts, "entries": provenance},
                                          ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"manifest": str(args.output), "capabilities": len(tools), **counts},
                     ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
