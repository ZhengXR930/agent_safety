"""Checkpointed full MCP-Guard replay on MCPTox attacks and clean tool blocks."""

from __future__ import annotations

import asyncio
import contextlib
import json
import os
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
MCP_GUARD = ROOT / "benchmarks/external/MCP-Guard"
SOURCE = ROOT / "benchmarks/MCPTox-Benchmark/response_all.json"
RUN_DIR = HERE.parent / "experiment_stage/mcp_full_20260718"
OUT = RUN_DIR / "mcpguard_mcptox.json"
DETAIL_LOG = RUN_DIR / "mcpguard_mcptox_detector.log"


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

    result = (
        json.loads(OUT.read_text(encoding="utf-8"))
        if OUT.exists()
        else {"benchmark": "MCPTox-Benchmark", "baseline": "MCP-Guard", "label_model": "DeepSeek-v3", "attacks": [], "clean": []}
    )
    attack_done = {(x["server"], x["id"]) for x in result["attacks"]}
    clean_done = {(x["server"], x["tool"]) for x in result["clean"]}
    RUN_DIR.mkdir(parents=True, exist_ok=True)

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
        }

    with DETAIL_LOG.open("a", encoding="utf-8") as log:
        for item in attacks:
            if (item["server"], item["id"]) not in attack_done:
                detection = await scan(item["text"], item["tool"], log)
                result["attacks"].append({k: v for k, v in item.items() if k != "text"} | {"detection": detection})
                if len(result["attacks"]) % 10 == 0:
                    OUT.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
                    print(f"attack {len(result['attacks'])}/{len(attacks)}", flush=True)
        for item in cleans:
            if (item["server"], item["tool"]) not in clean_done:
                detection = await scan(item["text"], item["tool"], log)
                result["clean"].append({k: v for k, v in item.items() if k != "text"} | {"detection": detection})
                if len(result["clean"]) % 10 == 0:
                    OUT.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
                    print(f"clean {len(result['clean'])}/{len(cleans)}", flush=True)

    successful = [x for x in result["attacks"] if x["label"] == "Success"]
    residual = [x for x in successful if x["detection"]["allowed"]]
    false_positives = [x for x in result["clean"] if not x["detection"]["allowed"]]
    result["metrics"] = {
        "n_attack": len(result["attacks"]),
        "undefended_success": len(successful),
        "undefended_asr": len(successful) / len(result["attacks"]),
        "defended_success": len(residual),
        "defended_asr": len(residual) / len(result["attacks"]),
        "attack_detection_rate": sum(not x["detection"]["allowed"] for x in result["attacks"]) / len(result["attacks"]),
        "n_clean": len(result["clean"]),
        "fp": len(false_positives),
        "fpr": len(false_positives) / len(result["clean"]),
        "detector_utility": 1 - len(false_positives) / len(result["clean"]),
    }
    OUT.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(result["metrics"], indent=2), flush=True)


if __name__ == "__main__":
    asyncio.run(main())
