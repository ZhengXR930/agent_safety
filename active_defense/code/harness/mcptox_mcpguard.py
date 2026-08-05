"""Checkpointed full MCP-Guard replay on MCPTox attacks and clean tool blocks."""

from __future__ import annotations

import asyncio
import argparse
import contextlib
import json
import os
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
BENCHMARKS = REPO.parent / "benchmarks"
MCP_GUARD = BENCHMARKS / "external/MCP-Guard"
SOURCE = BENCHMARKS / "MCPTox-Benchmark/response_all.json"
RUN_DIR = REPO / "experiment_stage/mcp_baselines_20260731"


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


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path,
                        default=RUN_DIR / "mcpguard_mcptox.json")
    parser.add_argument("--detail-log", type=Path,
                        default=RUN_DIR / "mcpguard_mcptox_detector.log")
    parser.add_argument("--limit", type=int)
    args = parser.parse_args()
    # ``MCP-Guard`` requires its own repository as cwd.  Resolve caller paths
    # before changing directory so artifacts stay under this repository.
    args.output = args.output.resolve()
    args.detail_log = args.detail_log.resolve()
    sys.path.insert(0, str(MCP_GUARD))
    os.chdir(MCP_GUARD)
    from src.mcp_guard.core import guardrail_scan
    from src.mcp_guard.schemas import GuardrailRequest

    data = json.loads(SOURCE.read_text(encoding="utf-8"))
    attacks, cleans = [], []
    for server in data["servers"].values():
        for block in clean_blocks(server["clean_system_promot"]):
            cleans.append({"server": server["server_name"], "tool": tool_name(block), "text": block})
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

    # The clean benchmark catalog repeats a few registrations.  A manifest
    # capability is identified by its owning server and method name, so count
    # each clean interface once, matching the trusted-manifest denominator.
    cleans = list({(row["server"], row["tool"]): row for row in cleans}.values())
    if args.limit is not None:
        attacks, cleans = attacks[:args.limit], cleans[:args.limit]

    result = (
        json.loads(args.output.read_text(encoding="utf-8"))
        if args.output.exists()
        else {"benchmark": "MCPTox-Benchmark", "baseline": "MCP-Guard", "label_model": "DeepSeek-v3", "attacks": [], "clean": []}
    )
    attack_done = {(x["server"], x["id"]) for x in result["attacks"]}
    clean_done = {(x["server"], x["tool"]) for x in result["clean"]}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.detail_log.parent.mkdir(parents=True, exist_ok=True)

    async def scan(text: str, name: str, log) -> dict:
        with contextlib.redirect_stdout(log), contextlib.redirect_stderr(log):
            response = await guardrail_scan(
                GuardrailRequest(tool_name=name, tool_description=text, tool_input_schema={})
            )
        if hasattr(response, "dict"):
            response = response.dict()
        return {
            "allowed": response.get("allowed", True),
            "stage": response.get("detection_stage"),
            "issue_count": len(response.get("issues", [])),
            "degraded_detectors": list(response.get("degraded_detectors") or ()),
        }

    with args.detail_log.open("a", encoding="utf-8") as log:
        for item in attacks:
            if (item["server"], item["id"]) not in attack_done:
                detection = await scan(item["text"], item["tool"], log)
                result["attacks"].append({k: v for k, v in item.items() if k != "text"} | {"detection": detection})
                attack_done.add((item["server"], item["id"]))
                if len(result["attacks"]) % 25 == 0:
                    args.output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
                    print(f"attack {len(result['attacks'])}/{len(attacks)}", flush=True)
        for item in cleans:
            if (item["server"], item["tool"]) not in clean_done:
                detection = await scan(item["text"], item["tool"], log)
                result["clean"].append({k: v for k, v in item.items() if k != "text"} | {"detection": detection})
                clean_done.add((item["server"], item["tool"]))
                if len(result["clean"]) % 25 == 0:
                    args.output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
                    print(f"clean {len(result['clean'])}/{len(cleans)}", flush=True)

    successful = [x for x in result["attacks"] if x["label"] == "Success"]
    residual = [x for x in successful if x["detection"]["allowed"]]
    false_positives = [x for x in result["clean"] if not x["detection"]["allowed"]]
    n_attack, n_clean = len(result["attacks"]), len(result["clean"])
    result["metrics"] = {
        "n_attack": len(result["attacks"]),
        "undefended_success": len(successful),
        "undefended_asr": len(successful) / n_attack if n_attack else None,
        "defended_success": len(residual),
        "defended_asr": len(residual) / n_attack if n_attack else None,
        "attack_detection_rate": sum(not x["detection"]["allowed"] for x in result["attacks"]) / n_attack if n_attack else None,
        "n_clean": len(result["clean"]),
        "fp": len(false_positives),
        "fpr": len(false_positives) / n_clean if n_clean else None,
        "detector_utility": 1 - len(false_positives) / n_clean if n_clean else None,
        "degraded_scans": sum(bool(x["detection"].get("degraded_detectors"))
                              for x in (*result["attacks"], *result["clean"])),
    }
    args.output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(result["metrics"], indent=2), flush=True)


if __name__ == "__main__":
    asyncio.run(main())
