from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

DATA = Path(__file__).resolve().parent / "data"


def _tool_capability(row: dict[str, Any]) -> dict[str, Any]:
    name = str(row["Tool Name"])
    return {
        "name": name,
        "description": str(row.get("Description", name)),
        "arguments": [],
        "required_arguments": [],
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": [],
            "additionalProperties": False,
        },
        "argument_types": {},
        "output_schema": {"type": "string"},
        "output_types": {"/": "natural_language"},
        "effect": False,
        "observation": True,
        "effect_return": False,
        "receipt_role": "data",
        "x-asb-agent": str(row.get("Corresponding Agent", "")),
        "x-asb-expected-achievement": str(row.get("Expected Achievements", "")),
    }


def build_manifest(data_dir: Path = DATA) -> dict[str, Any]:
    tools = json.loads((data_dir / "tools.json").read_text(encoding="utf-8"))
    normal_tools = list(tools.get("normal_tools") or [])
    by_agent: dict[str, list[str]] = {}
    capabilities = []
    seen = set()
    for row in normal_tools:
        name = str(row["Tool Name"])
        if name in seen:
            continue
        seen.add(name)
        capabilities.append(_tool_capability(row))
        by_agent.setdefault(str(row.get("Corresponding Agent", "")), []).append(name)
    return {
        "schema": "asb-opi-trusted-manifest-v1",
        "benchmark": "ASB-OPI",
        "assumption": (
            "ASB normal tools are operator-registered read/observation capabilities. "
            "OPI attacker tools are runtime-visible injected extras, not trusted registered capabilities."
        ),
        "capabilities": sorted(capabilities, key=lambda item: item["name"]),
        "by_agent": {agent: sorted(names) for agent, names in sorted(by_agent.items())},
        "excluded_runtime_extras": "Attacker tools are intentionally excluded from the trusted manifest and mediated as unknown effects if called.",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", type=Path, default=DATA)
    parser.add_argument("--output", type=Path, default=DATA / "manifest.json")
    args = parser.parse_args()
    manifest = build_manifest(args.data_dir)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(args.output)


if __name__ == "__main__":
    main()
