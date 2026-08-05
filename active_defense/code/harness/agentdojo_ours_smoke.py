"""Lean AgentDojo smoke: run a few benign tasks per suite under the
deterministic defense and report utility + gate decisions.

    PYTHONPATH=. python code/run_agentdojo_lean.py --suite banking --n 2
"""
from __future__ import annotations

import argparse
import json

from code.agentdojo_protocol import (activate_vendored_agentdojo,
                                     load_frozen_contracts)

activate_vendored_agentdojo()

from agentdojo.agent_pipeline.agent_pipeline import AgentPipeline, PipelineConfig
from agentdojo.agent_pipeline.llms.openai_llm import OpenAILLM
from agentdojo.task_suite.load_suites import get_suite

from code.benchmarks.agentdojo import AgentDojoRunner
from code.defense.contract import TaskContract
from code.defense.engine import Engine
from code.internal_client import client_for_model


def pipeline_for(model):
    if str(model).lower().startswith("gpt-"):
        from agentdojo.attacks.base_attacks import MODEL_NAMES
        MODEL_NAMES.setdefault(str(model), "GPT-4.1")
    llm = OpenAILLM(client_for_model(model), model)
    llm.name = model
    return AgentPipeline.from_config(PipelineConfig(
        llm=llm, model_id=None, defense=None,
        system_message_name=None, system_message=None))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--suite", required=True)
    parser.add_argument("--benchmark-version", default="v1.2.2")
    parser.add_argument("--agent-model", default="deepseek-v4-flash")
    parser.add_argument("--contract-model", default="gpt-5.5-2026-04-24")
    parser.add_argument("--n", type=int, default=2)
    parser.add_argument("--attack", default="")
    parser.add_argument("--contract-file",
                        help="frozen task-id to TaskContract bundle")
    args = parser.parse_args()

    suite = get_suite(args.benchmark_version, args.suite)
    # Autonomous benchmark runs do not simulate a user approval channel.
    engine = Engine(args.contract_model, approval_enabled=False)
    runner = AgentDojoRunner(suite, pipeline_for(args.agent_model), engine)
    frozen, bundle = (load_frozen_contracts(args.contract_file)
                      if args.contract_file else ({}, {}))

    tasks = list(suite.user_tasks.values())[:args.n]
    passed = 0
    attack_success = 0
    completed = 0
    attacker = None
    if args.attack:
        from agentdojo.attacks.attack_registry import load_attack
        attacker = load_attack(args.attack, suite, runner.pipeline)
    for task in tasks:
        injection_task, injections = None, {}
        if attacker is not None:
            for injection_id in suite.injection_tasks:
                candidate = suite.get_injection_task_by_id(injection_id)
                try:
                    proposed = attacker.attack(task, candidate)
                except ValueError:
                    continue
                injection_task, injections = candidate, proposed
                break
            if injection_task is None:
                print(json.dumps({
                    "task": getattr(task, "ID", "?"),
                    "skipped": "no-compatible-injection",
                }), flush=True)
                continue
        task_id = str(getattr(task, "ID", "?"))
        if args.contract_file:
            if task_id not in frozen:
                raise KeyError(f"frozen Contract missing {task_id}")
            contract = TaskContract.from_dict(frozen[task_id])
        else:
            contract = engine.contract(task.PROMPT)
        result = runner.run(
            task, injection_task=injection_task, injections=injections,
            contract=contract)
        completed += 1
        passed += int(result["utility"])
        attack_success += int(result["asr"])
        audit = result["audit"]
        print(json.dumps({
            "task": task_id,
            "injection": getattr(injection_task, "ID", None),
            "utility": result["utility"],
            "asr": result["asr"],
            "routes": [d["route"] for d in result["decisions"]],
            "reasons": [d["reason"] for d in result["decisions"]],
            "bindings": audit["wrap"]["bindings"],
            "plant": audit["plant"],
        }, ensure_ascii=False), flush=True)
    label = "attack_utility" if attacker is not None else "benign_utility"
    print(json.dumps({
        "suite": args.suite,
        "n": completed,
        "contract_sha256": bundle.get("contracts_sha256"),
        label: (passed / completed) if completed else 0.0,
        "asr": (attack_success / completed) if completed else 0.0,
    }), flush=True)


if __name__ == "__main__":
    main()
