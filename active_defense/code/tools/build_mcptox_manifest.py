"""Build a trusted MCPTox operator manifest without trusting tool prose.

The runtime adapter attests method identity and JSON schema.  Descriptions in
an MCP catalog remain untrusted observation content: clean descriptions are
useful documentation, while attack-only methods receive a neutral description
derived solely from their registered method name.  This lets the Contract use
an actually installed computation/read method without accepting a poisoned
description's alleged prerequisite.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from code.defense.memory import CapabilitySurface, EnvironmentPlan
from code.harness.mcp_ours import _blocks, _canonical


_OBSERVATION_PREFIXES = (
    "get_", "read_", "list_", "search_", "find_", "fetch_",
    "retrieve_", "query_", "lookup_", "describe_", "check_",
    "simple_", "calculate_", "compute_", "count_",
)


def _neutral_description(method: str) -> str:
    operation = str(method).replace("-", " ").replace("_", " ").strip()
    return (operation[:1].upper() + operation[1:] +
            " through the operator-registered MCP method.")


def _observation_only(method: str) -> bool:
    """Conservative direction attestation from the registered operation name."""
    name = str(method).casefold()
    return name.startswith(_OBSERVATION_PREFIXES) or name in {
        "gettime", "get-time", "current_time", "time", "now",
    }


def _merge_schema(left: dict, right: dict) -> dict:
    """Merge runtime-attested schema variants without inventing arguments."""
    if not left:
        return json.loads(json.dumps(right))
    result = json.loads(json.dumps(left))
    properties = result.setdefault("properties", {})
    for name, schema in (right.get("properties") or {}).items():
        if name in properties and properties[name].get("type") != schema.get("type"):
            raise ValueError(f"conflicting runtime types for argument {name!r}")
        properties.setdefault(name, schema)
    result["required"] = sorted(
        set(result.get("required") or ()) & set(right.get("required") or ()))
    result["additionalProperties"] = False
    return result


def _sha(value) -> str:
    body = json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), default=str)
    return hashlib.sha256(body.encode()).hexdigest()


def build(path: Path) -> tuple[dict, dict]:
    benchmark = json.loads(path.read_text(encoding="utf-8"))
    servers = benchmark.get("servers") or {}
    capabilities = {}
    entries = []
    for server_name, server in sorted(servers.items()):
        clean_prompt = server.get("clean_system_promot")
        if not isinstance(clean_prompt, str) or not clean_prompt.strip():
            raise ValueError(f"MCPTox server {server_name!r} has no clean catalog")
        tools = _blocks(clean_prompt)
        if not tools:
            raise ValueError(f"MCPTox server {server_name!r} exposes no tools")
        runtime_tools = dict(tools)
        runtime_sources = {name: "benchmark-clean-interface" for name in tools}
        for malicious in server.get("malicious_instance", ()):
            for row in malicious.get("datas", ()):
                for name, tool in _blocks(str(row.get("system", ""))).items():
                    if name in runtime_tools:
                        tool = {**runtime_tools[name], "inputSchema": _merge_schema(
                            runtime_tools[name]["inputSchema"], tool["inputSchema"])}
                    else:
                        tool = {**tool, "description": _neutral_description(name)}
                        runtime_sources[name] = "operator-runtime-name+schema"
                    runtime_tools[name] = tool
        for tool_name, tool in sorted(runtime_tools.items()):
            capability = _canonical(server_name, tool_name)
            if capability in capabilities:
                raise ValueError(f"duplicate MCPTox capability {capability!r}")
            schema = tool["inputSchema"]
            properties = schema.get("properties") or {}
            observation_only = _observation_only(tool_name)
            surface = CapabilitySurface.from_dict({
                "name": capability,
                "description": tool["description"],
                "inputSchema": schema,
                "required_arguments": list(schema.get("required") or ()),
                "argument_schemas": properties,
                "output_schema": {"type": "string"},
                "effect": not observation_only,
                "observation": True,
                "effect_return": not observation_only,
            })
            capabilities[capability] = surface
            entries.append({
                "capability": capability,
                "server": server_name,
                "method": tool_name,
                "schema_source": runtime_sources[tool_name],
                "boundary_attestation": (
                    "observation-return" if observation_only else
                    "mcp-invocation+text-return"),
            })
    source_hash = _sha(servers)
    plan = EnvironmentPlan(
        "mcptox-clean-" + source_hash[:12], {}, capabilities).to_dict()
    provenance = {
        "benchmark": "MCPTox",
        "source": str(path),
        "source_sha256": source_hash,
        "counts": {
            "benchmark-clean-interface": sum(
                row["schema_source"] == "benchmark-clean-interface"
                for row in entries),
            "operator-runtime-name+schema": sum(
                row["schema_source"] == "operator-runtime-name+schema"
                for row in entries),
            "fallback": 0,
        },
        "entries": entries,
    }
    return plan, provenance


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--benchmark", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--provenance", type=Path, required=True)
    args = parser.parse_args()
    plan, provenance = build(args.benchmark.resolve())
    for path, value in ((args.output, plan), (args.provenance, provenance)):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n",
                        encoding="utf-8")
    print(json.dumps({
        "capabilities": len(plan["capabilities"]),
        "fallback": provenance["counts"]["fallback"],
        "output": str(args.output),
    }))


if __name__ == "__main__":
    main()
