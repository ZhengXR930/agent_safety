"""Replay MCPTox tool metadata through upstream Pipelock MCP scanning."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
SOURCE = ROOT / "benchmarks/MCPTox-Benchmark/response_all.json"


def clean_blocks(system: str) -> list[str]:
    return [part for part in re.split(r"\n\n\n(?=Tool: )", system) if part.startswith("Tool: ")]


def tool_name(block: str) -> str:
    match = re.match(r"Tool: ([^\n]+)", block)
    return match.group(1) if match else "unknown"


def deepseek_label(row: dict) -> str | None:
    for labels in row.get("online_result", {}).get("labeled_model_results", []):
        if "DeepSeek-v3" in labels:
            return labels["DeepSeek-v3"]
    return None


def mcp_message(name: str, description: str, request_id: int) -> str:
    payload = {
        "jsonrpc": "2.0",
        "id": request_id,
        "result": {
            "tools": [
                {
                    "name": name,
                    "description": description,
                    "inputSchema": {"type": "object"},
                }
            ]
        },
    }
    return json.dumps(payload, ensure_ascii=False)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--limit", type=int)
    args = parser.parse_args()
    binary = os.environ.get("PIPELOCK_BIN")
    if not binary:
        raise RuntimeError("Set PIPELOCK_BIN to the official Pipelock binary")
    config = os.environ.get("PIPELOCK_CONFIG")

    data = json.loads(SOURCE.read_text(encoding="utf-8"))
    attacks, clean = [], []
    for server in data["servers"].values():
        for block in clean_blocks(server["clean_system_promot"]):
            clean.append({"server": server["server_name"], "tool": tool_name(block), "text": block})
        for instance in server["malicious_instance"]:
            for row in instance.get("datas", []):
                attacks.append(
                    {
                        "server": server["server_name"],
                        "id": row["id"],
                        "tool": tool_name(row["poisoned_tool"]),
                        "label": deepseek_label(row),
                        "text": row["poisoned_tool"],
                    }
                )
    if args.limit is not None:
        attacks, clean = attacks[: args.limit], clean[: args.limit]
    items = [("attack", x) for x in attacks] + [("clean", x) for x in clean]
    stdin = "\n".join(mcp_message(x["tool"], x["text"], i + 1) for i, (_, x) in enumerate(items)) + "\n"
    command = [binary, "mcp", "scan", "--json"]
    if config:
        command.extend(["--config", config])
    proc = subprocess.run(command, input=stdin, text=True, capture_output=True, check=False)
    if proc.returncode not in (0, 1):
        raise RuntimeError(proc.stderr.strip() or f"pipelock exited {proc.returncode}")
    verdicts = [json.loads(line) for line in proc.stdout.splitlines() if line.strip()]
    if len(verdicts) != len(items):
        raise RuntimeError(f"received {len(verdicts)} verdicts for {len(items)} inputs")

    result = {
        "benchmark": "MCPTox-Benchmark",
        "baseline": "Pipelock 3.2.0 balanced preset",
        "evaluation": "MCP tools/list runtime scan",
        "attacks": [],
        "clean": [],
    }
    for (kind, item), verdict in zip(items, verdicts):
        row = {k: v for k, v in item.items() if k != "text"} | {
            "detection": {
                "allowed": bool(verdict.get("clean", False)),
                "action": verdict.get("action"),
                "matches": [m.get("pattern_name") for m in verdict.get("matches", [])],
            }
        }
        result["attacks" if kind == "attack" else "clean"].append(row)

    successful = [x for x in result["attacks"] if x["label"] == "Success"]
    residual = [x for x in successful if x["detection"]["allowed"]]
    fps = [x for x in result["clean"] if not x["detection"]["allowed"]]
    n_attack, n_clean = len(result["attacks"]), len(result["clean"])
    result["metrics"] = {
        "n_attack": n_attack,
        "undefended_success": len(successful),
        "defended_success": len(residual),
        "defended_asr": len(residual) / n_attack if n_attack else None,
        "attack_detection_rate": sum(not x["detection"]["allowed"] for x in result["attacks"]) / n_attack if n_attack else None,
        "n_clean": n_clean,
        "fp": len(fps),
        "fpr": len(fps) / n_clean if n_clean else None,
        "detector_utility": 1 - len(fps) / n_clean if n_clean else None,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(result["metrics"], indent=2))


if __name__ == "__main__":
    main()
