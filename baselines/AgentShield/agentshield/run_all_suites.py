"""
Run AgentShield attacks across all 4 AgentDojo suites
=====================================================
Runs each attack on the first user task of each suite.
Saves timestamped results per suite and a combined summary.

Adapted from upstream: the pipeline defaults to the internal OpenAI-compatible
gateway. Pass --no-internal to use upstream OpenAI/ModelsEnum behaviour.

Usage: python -m agentshield.run_all_suites [--model MODEL]
"""

import sys
import os
import json
import time
from pathlib import Path
from datetime import datetime

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agentdojo.task_suite.load_suites import get_suite
from agentdojo.functions_runtime import FunctionsRuntime

from agentshield.defenses.pipeline import (
    build_agentshield_pipeline,
    get_augmented_tools,
    reset_all_detectors,
    get_all_detections,
    prepare_environment,
)
from agentshield.defenses.honeytools import HONEYTOOL_NAMES
from agentshield.attacks.attack_prompts import ALL_ATTACKS
from agentshield.internal_client import DEFAULT_INTERNAL_MODEL

import argparse

SUITES = ["banking", "slack", "travel", "workspace"]


def run_attack(suite, tools, pipeline, detectors, user_task, attack_payload):
    """Run a single attack and return results."""
    reset_all_detectors(detectors)
    injection_defaults = suite.get_injection_vector_defaults()
    injections = {vec: attack_payload for vec in injection_defaults}
    env = suite.load_and_inject_default_environment(injections)
    env = prepare_environment(env)  # Plant honeytoken files
    runtime = FunctionsRuntime(tools)

    try:
        _, _, result_env, messages, _ = pipeline.query(user_task.PROMPT, runtime, env)
    except Exception as e:
        return {
            "error": str(e),
            "tools_used": [],
            "honeytool_triggered": False,
            "detections": [],
            "num_messages": 0,
            "attack_succeeded": False,
        }

    tools_used = []
    for msg in messages:
        if msg["role"] == "assistant" and msg.get("tool_calls"):
            for tc in msg["tool_calls"]:
                tools_used.append(tc.function)

    honeytool_triggered = any(t in HONEYTOOL_NAMES for t in tools_used)
    detections = get_all_detections(detectors)

    return {
        "tools_used": tools_used,
        "honeytool_triggered": honeytool_triggered,
        "detections": detections,
        "num_messages": len(messages),
        "attack_succeeded": len(detections) > 0 or honeytool_triggered,
        "error": None,
    }


def run_suite(suite_name, pipeline, detectors, benchmark_version):
    """Run all attacks on one suite."""
    suite = get_suite(benchmark_version, suite_name)
    tools = get_augmented_tools(suite.tools)
    user_task_ids = list(suite.user_tasks.keys())
    user_task = suite.get_user_task_by_id(user_task_ids[0])

    print(f"\n  Suite: {suite_name} | Task: {user_task_ids[0]} | Tools: {len(tools)}")
    print(f"  Prompt: {user_task.PROMPT[:70]}...\n")

    runs = []
    for i, attack in enumerate(ALL_ATTACKS):
        label = f"[{i+1:3d}/{len(ALL_ATTACKS)}] {attack['id']:18s} ({attack['language']:2s}/{attack['category']})"
        print(f"    {label} ...", end=" ", flush=True)

        result = run_attack(suite, tools, pipeline, detectors, user_task, attack["payload"])
        det_count = len(result["detections"])
        layers_hit = sorted(set(d["layer"] for d in result["detections"]))

        runs.append({"suite": suite_name, "attack_id": attack["id"],
                     "language": attack["language"], "category": attack["category"],
                     "goal": attack["goal"], **result})

        if det_count > 0:
            print(f"DETECTED ({det_count}, {layers_hit})")
        elif result["error"]:
            print("ERROR")
        else:
            print("not detected")

    return runs


def print_summary(all_runs):
    detected = [r for r in all_runs if r["attack_succeeded"]]
    print(f"\n  Total: {len(detected)}/{len(all_runs)} "
          f"({100*len(detected)/max(len(all_runs),1):.1f}%)")

    print("\n  By suite:")
    for suite_name in SUITES:
        s = [r for r in all_runs if r["suite"] == suite_name]
        sd = [r for r in s if r["attack_succeeded"]]
        print(f"    {suite_name:12s}: {len(sd):3d}/{len(s)} ({100*len(sd)/max(len(s),1):.1f}%)")

    print("\n  By language:")
    for lang in ["EN", "KU", "AR", "CS"]:
        s = [r for r in all_runs if r["language"] == lang]
        sd = [r for r in s if r["attack_succeeded"]]
        print(f"    {lang}: {len(sd):3d}/{len(s)} ({100*len(sd)/max(len(s),1):.1f}%)")

    print("\n  By defense layer:")
    layer_counts = {"honeytool": 0, "honeytoken": 0, "parameter_validator": 0}
    for r in all_runs:
        for d in r["detections"]:
            layer = d.get("layer", "unknown")
            layer_counts[layer] = layer_counts.get(layer, 0) + 1
    for layer, count in layer_counts.items():
        print(f"    {layer}: {count}")


def main():
    parser = argparse.ArgumentParser(description="Run attacks across all suites")
    parser.add_argument("--model", default=DEFAULT_INTERNAL_MODEL, help="Model ID")
    parser.add_argument("--no-internal", action="store_true",
                        help="Use upstream OpenAI/ModelsEnum instead of internal gateway")
    parser.add_argument("--benchmark-version", default="v1.2.2")
    args = parser.parse_args()

    model = args.model
    model_short = model.split("-2024")[0].split("-2025")[0].split("-2026")[0]

    print("=" * 60)
    print(f"  AgentShield — {len(ALL_ATTACKS)} attacks x {len(SUITES)} suites ({model_short})")
    print("=" * 60)

    pipeline, detectors = build_agentshield_pipeline(
        llm=model,
        layers=["honeytools", "honeytokens", "parameter_validator"],
        use_internal=not args.no_internal,
    )

    results_dir = Path(__file__).resolve().parent / "results"
    results_dir.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")

    all_runs = []
    start_time = time.time()
    for suite_name in SUITES:
        suite_runs = run_suite(suite_name, pipeline, detectors, args.benchmark_version)
        all_runs.extend(suite_runs)
        suite_path = results_dir / f"{suite_name}_{model_short}_{timestamp}.json"
        with open(suite_path, "w", encoding="utf-8") as f:
            json.dump({"metadata": {"timestamp": timestamp, "model": model,
                                    "suite": suite_name, "total": len(suite_runs)},
                       "runs": suite_runs}, f, indent=2, default=str, ensure_ascii=False)
        print(f"  Saved: {suite_path}")

    elapsed = time.time() - start_time
    combined_path = results_dir / f"all_suites_{model_short}_{timestamp}.json"
    with open(combined_path, "w", encoding="utf-8") as f:
        json.dump({"metadata": {"timestamp": timestamp, "model": model, "suites": SUITES,
                                "total_attacks": len(ALL_ATTACKS), "total_runs": len(all_runs),
                                "elapsed_seconds": elapsed},
                   "runs": all_runs}, f, indent=2, default=str, ensure_ascii=False)

    print("\n" + "=" * 60)
    print(f"  COMPLETE — {len(all_runs)} runs in {elapsed:.0f}s ({elapsed/60:.1f} min)")
    print(f"  Combined results: {combined_path}")
    print("=" * 60)
    print_summary(all_runs)
    print()


if __name__ == "__main__":
    main()
