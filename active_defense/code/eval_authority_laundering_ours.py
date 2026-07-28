"""Replay one successful baseline laundering payload against the current method."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from code.internal_client import client_for_model
from code.run_tap_ours import build_target


def _strip(result: dict) -> dict:
    value = dict(result)
    value.pop("environment", None)
    return value


def run(args: argparse.Namespace) -> dict:
    source = json.loads(Path(args.source_result).read_text(encoding="utf-8"))
    successful = next(record for record in source["records"] if record.get("asr"))
    payload = successful["injection"]
    target = build_target(args)

    def plant_factory():
        return target.engine.plant_agent(
            target.contract, client_for_model(args.plant_model), args.plant_model)

    clean = target.runner.run(
        target.user_task, contract=target.contract, plant_factory=plant_factory(),
    )
    direct = target.evaluate(target.injection_task.GOAL)
    laundering = target.evaluate(payload)
    result = {
        "config": vars(args),
        "source_payload": payload,
        "source_baseline_record": {
            "defense": source.get("summary", {}).get("defense"),
            "asr": successful.get("asr"),
            "utility": successful.get("utility"),
            "laundering_witness": successful.get("laundering_witness"),
        },
        "clean": _strip(clean),
        "direct": _strip(direct),
        "laundering": _strip(laundering),
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return {
        "clean_utility": bool(clean.get("utility")),
        "direct_utility": bool(direct.get("utility")),
        "direct_asr": bool(direct.get("asr")),
        "laundering_utility": bool(laundering.get("utility")),
        "laundering_asr": bool(laundering.get("asr")),
        "laundering_routes": [item.get("route") for item in laundering.get("decisions", [])],
        "output": str(output),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--suite", default="slack")
    parser.add_argument("--defense", default="ours")
    parser.add_argument("--user-task", default="user_task_1")
    parser.add_argument("--injection-task", default="injection_task_1")
    parser.add_argument("--source-result", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--agent-model", default="deepseek-chat")
    parser.add_argument("--contract-model", default="deepseek-chat")
    parser.add_argument("--plant-model", default="deepseek-chat")
    parser.add_argument("--plan-store", default="experiment_stage/authority_laundering_ours_plan_20260722")
    parser.add_argument("--attacker-model", default="deepseek-chat")
    parser.add_argument("--judge-model", default="deepseek-chat")
    return parser.parse_args()


if __name__ == "__main__":
    print(json.dumps(run(parse_args()), ensure_ascii=False), flush=True)
