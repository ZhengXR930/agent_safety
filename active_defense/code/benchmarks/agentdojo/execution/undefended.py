"""Run the undefended AgentDojo agent on the project's fixed pairs."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from code.benchmarks.agentdojo_protocol_runtime import (AGENT_MODEL, BENCHMARK_VERSION,
                                     activate_vendored_agentdojo,
                                     load_pair_manifest)
from code.core.client import client_for_model

activate_vendored_agentdojo()


def pipeline_for(model: str):
    from agentdojo.agent_pipeline.agent_pipeline import (AgentPipeline,
                                                         PipelineConfig,
                                                         load_system_message)
    from agentdojo.agent_pipeline.llms.openai_llm import OpenAILLM

    llm = OpenAILLM(client_for_model(model), model)
    llm.name = model
    pipeline = AgentPipeline.from_config(PipelineConfig(
        llm=llm, model_id=None, defense=None, system_message_name=None,
        system_message=load_system_message(None)))
    return pipeline


def write_checkpoint(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pending = path.with_suffix(path.suffix + ".tmp")
    pending.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    pending.replace(path)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--suite", required=True)
    parser.add_argument("--pair-manifest", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--agent-model", default=AGENT_MODEL)
    parser.add_argument("--attack", default="direct")
    parser.add_argument("--max-pairs", type=int, default=0)
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()

    from agentdojo.attacks.attack_registry import load_attack
    from agentdojo.task_suite.load_suites import get_suite

    suite = get_suite(BENCHMARK_VERSION, args.suite)
    pipeline = pipeline_for(args.agent_model)
    attacker = load_attack(args.attack, suite, pipeline)
    pairs = load_pair_manifest(args.pair_manifest)
    selected = pairs[:args.max_pairs] if args.max_pairs else pairs
    output = Path(args.output)
    state = {
        "schema": "agentdojo-undefended-v1",
        "benchmark_version": BENCHMARK_VERSION,
        "suite": args.suite,
        "defense": "undefended",
        "agent_model": args.agent_model,
        "attack": args.attack,
        "pair_manifest": args.pair_manifest,
        "expected_pairs": len(pairs),
        "benign_by_task": {},
        "attacks": [],
    }
    if args.resume and output.exists():
        saved = json.loads(output.read_text(encoding="utf-8"))
        identity = ("schema", "benchmark_version", "suite", "defense",
                    "agent_model", "attack", "pair_manifest", "expected_pairs")
        if any(saved.get(key) != state.get(key) for key in identity):
            raise ValueError("checkpoint does not match this evaluation protocol")
        state.update(saved)
    completed = {(row["task"], row["injection"]) for row in state["attacks"]}

    for task_id, injection_id in selected:
        user_task = suite.get_user_task_by_id(task_id)
        if task_id not in state["benign_by_task"]:
            utility, _ = suite.run_task_with_pipeline(
                pipeline, user_task, injection_task=None, injections={})
            state["benign_by_task"][task_id] = bool(utility)
            write_checkpoint(output, state)
        if (task_id, injection_id) in completed:
            continue
        injection_task = suite.get_injection_task_by_id(injection_id)
        injections = attacker.attack(user_task, injection_task)
        utility, security = suite.run_task_with_pipeline(
            pipeline, user_task, injection_task=injection_task, injections=injections)
        state["attacks"].append({
            "task": task_id, "injection": injection_id,
            "utility": bool(utility), "attack_success": bool(security),
        })
        completed.add((task_id, injection_id))
        write_checkpoint(output, state)
        print(json.dumps({"defense": "undefended",
                          "completed": len(state["attacks"]),
                          "selected": len(selected)}), flush=True)

    attacks = state["attacks"]
    benign_count = len(state["benign_by_task"])
    state["summary"] = {
        "benign_utility": sum(state["benign_by_task"].values()) / benign_count
        if benign_count else 0.0,
        "asr": sum(row["attack_success"] for row in attacks) / len(attacks)
        if attacks else 0.0,
        "utility_under_attack": sum(row["utility"] for row in attacks) / len(attacks)
        if attacks else 0.0,
        "benign_passed": sum(state["benign_by_task"].values()),
        "benign_total": benign_count,
        "attack_successes": sum(row["attack_success"] for row in attacks),
        "attack_utility_passed": sum(row["utility"] for row in attacks),
        "attack_total": len(attacks),
    }
    write_checkpoint(output, state)
    print(json.dumps(state["summary"], ensure_ascii=False, indent=2), flush=True)


if __name__ == "__main__":
    main()
