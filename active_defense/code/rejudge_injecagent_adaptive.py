"""Rejudge saved adaptive trajectories without resampling target behavior."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from code.benchmarks.injecagent import load_cases
from code.internal_client import client_for_model
from code.run_injecagent_adaptive_attack import utility_judge


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--judge-model", default="deepseek-chat")
    args = ap.parse_args()

    artifact = json.loads(args.input.read_text())
    config = artifact["config"]
    data_dir = Path(config["data_dir"])
    assets = json.loads(Path(config["assets"]).read_text())["cases"]
    by_fingerprint = {
        (x["user_instruction"].strip(), x["user_tool"].strip()): x for x in assets
    }
    cases = {
        x.id: x for x in load_cases(
            data_dir, config["attack"], config["setting"])
    }
    judge = client_for_model(args.judge_model)
    for case_result in artifact["cases"]:
        case = cases[case_result["case"]]
        asset = by_fingerprint[(case.user_task.strip(), case.user_tool.strip())]
        for record in case_result["records"]:
            record["previous_task_utility"] = record["task_utility"]
            record["previous_utility_verdict"] = record["utility_verdict"]
            utility, verdict = utility_judge(
                judge, args.judge_model, asset, case, record["target_result"])
            record["task_utility"] = utility
            record["utility_verdict"] = verdict

    baseline = [
        r for c in artifact["cases"] for r in c["records"] if r["round"] == 0
    ]
    adaptive = [
        r for c in artifact["cases"] for r in c["records"] if r["round"] > 0
    ]
    artifact["schema"] = "injecagent-official-blackbox-adaptive-rejudged-v2"
    artifact["judge_model"] = args.judge_model
    artifact["summary"] = {
        "cells": len(artifact["cases"]),
        "baseline_asr": sum(r["attack_success"] for r in baseline),
        "baseline_utility": sum(r["task_utility"] for r in baseline),
        "adaptive_candidates": len(adaptive),
        "adaptive_asr": sum(r["attack_success"] for r in adaptive),
        "adaptive_utility": sum(r["task_utility"] for r in adaptive),
        "utility_preserving_asr": sum(
            r["attack_success"] and r["task_utility"] for r in adaptive),
        "task_displacement": sum(
            r["attack_success"] and not r["task_utility"] for r in adaptive),
        "cells_with_adaptive_success": sum(any(
            r["attack_success"] and r["task_utility"]
            for r in c["records"] if r["round"] > 0)
            for c in artifact["cases"]),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(artifact, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(artifact["summary"], ensure_ascii=False))


if __name__ == "__main__":
    main()
