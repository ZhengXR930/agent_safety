"""Build a one-bit, method-level MCP capability manifest from public schemas."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from code.defense.plan_store import PlanStore
from code.defense.surveyor import Surveyor
from code.internal_client import client_for_model
from code.run_mcp_pilot import MCPTox, ROOT, _canonical, _tool_blocks


DEFAULT_MSB_CATALOG = ROOT / "experiment_stage/mcp_full_20260718/mcpguard_msb_clean_fp.json"


def mcptox_catalog(server_names: set[str]) -> list[dict]:
    data = json.loads(MCPTox.read_text(encoding="utf-8"))
    rows = []
    for server in data["servers"].values():
        name = server["server_name"]
        if server_names and name not in server_names:
            continue
        for schema in _tool_blocks(server["clean_system_promot"]):
            rows.append({"benchmark": "MCPTox", "server": name, **schema})
    return rows


def msb_catalog(path: Path) -> list[dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return [{"benchmark": "MSB", "server": row["server"],
             "name": row["tool_name"], "description": row["description"],
             "arguments": []}
            for row in data["rows"]]


def build_manifest(client, model: str, rows: list[dict], store_root: Path) -> dict:
    grouped = {}
    for row in rows:
        grouped.setdefault((row["benchmark"], row["server"]), []).append(row)
    methods, environments = [], []
    for (benchmark, server), items in sorted(grouped.items()):
        schemas = [{"name": _canonical(server, item["name"]),
                    "description": item["description"],
                    "arguments": item.get("arguments", [])}
                   for item in items]
        store = PlanStore(store_root, benchmark + "-" + server)
        plan = Surveyor(client, model).perceive(schemas)
        store.save({"environment": plan.to_dict()}, "method-level one-bit MCP manifest")
        environments.append({"benchmark": benchmark, "server": server,
                             "environment_id": plan.id, "method_n": len(items)})
        for item in items:
            capability = _canonical(server, item["name"])
            methods.append({"benchmark": benchmark, "server": server,
                            "method": item["name"], "capability": capability,
                            "effect": bool(plan.capabilities[capability].effect)})
    return {"schema": "server::method -> effect bool", "model": model,
            "environment_count": len(environments), "method_count": len(methods),
            "effect_true": sum(row["effect"] for row in methods),
            "effect_false": sum(not row["effect"] for row in methods),
            "environments": environments, "methods": methods}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="deepseek-chat")
    parser.add_argument("--mcptox-servers", default="FileSystem,Commander")
    parser.add_argument("--msb-catalog", type=Path, default=DEFAULT_MSB_CATALOG)
    parser.add_argument("--store", type=Path,
                        default=ROOT / "experiment_stage/mcp_method_manifest_store")
    parser.add_argument("--output", type=Path,
                        default=ROOT / "experiment_stage/mcp_method_manifest_pilot.json")
    args = parser.parse_args()
    servers = {value.strip() for value in args.mcptox_servers.split(",") if value.strip()}
    rows = mcptox_catalog(servers) + msb_catalog(args.msb_catalog)
    result = build_manifest(client_for_model(args.model), args.model, rows, args.store)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({key: result[key] for key in
                      ("environment_count", "method_count", "effect_true", "effect_false")},
                     indent=2))


if __name__ == "__main__":
    main()
