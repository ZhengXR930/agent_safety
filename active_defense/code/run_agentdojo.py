"""Run the current instruction-local defense on AgentDojo tasks."""
from __future__ import annotations

import argparse
import json
import os
import random
from pathlib import Path

from code.benchmarks.agentdojo import AgentDojoRunner
from code.benchmarks.agentdojo import tool_registrations
from code.defense.engine import Engine
from code.defense.memory import RUNTIME_CONTEXT_SOURCE
from code.defense.plan_store import PlanStore
from code.defense.plant import PlantDesigner
from code.defense.taskcontractor import TaskContract
from code.internal_client import client_for_model


def pipeline_for(model):
    from agentdojo.agent_pipeline.agent_pipeline import AgentPipeline, PipelineConfig
    from agentdojo.agent_pipeline.llms.openai_llm import OpenAILLM
    # AgentDojo's legacy personalized attacks reject newer OpenAI model IDs
    # before an episode starts. Extend its display-name registry by provider
    # family; this changes only how the attack addresses the model, not the
    # model endpoint, task, injection, or defense behavior.
    if str(model).lower().startswith("gpt-"):
        from agentdojo.attacks.base_attacks import MODEL_NAMES
        MODEL_NAMES.setdefault(str(model), "GPT-4.1")
    llm = OpenAILLM(client_for_model(model), model); llm.name = model
    return AgentPipeline.from_config(PipelineConfig(
        llm=llm, model_id=None, defense=None,
        system_message_name=None, system_message=None))


def _incident_has_route(incident: dict, route: str) -> bool:
    """Count mixed task-level incidents from their proposal-local decisions."""
    return (incident.get("route") == route or
            any(item.get("route") == route for item in incident.get("proposals", ())))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--suite", default="slack")
    parser.add_argument("--tasks", default="user_task_1")
    parser.add_argument("--agent-model", default="deepseek-chat")
    parser.add_argument("--contract-model", default="deepseek-chat")
    parser.add_argument("--plant-model", default="",
                        help="optional independent PlantDesigner model; defaults to contract model")
    parser.add_argument("--plant-review-model", default="gpt-5.5-2026-04-24",
                        help="Plant self-review model; defaults to GPT-5.5")
    parser.add_argument("--boundary-mode", choices=("declared", "inferred"), default="declared")
    parser.add_argument("--injections", help="optional JSON object passed to AgentDojo environment")
    parser.add_argument("--runtime-context",
                        help="operator-attested capability/argument context JSON sidecar")
    parser.add_argument("--random-pairs", type=int, default=0)
    parser.add_argument("--all-compatible-pairs", action="store_true",
                        help="enumerate every compatible task/injection pair; record benign once per task")
    parser.add_argument("--pair-manifest",
                        help="shared JSON pair list; create if absent and reuse across configurations")
    parser.add_argument("--max-pairs", type=int, default=0,
                        help="optional matrix-mode prefix limit for sanity runs")
    parser.add_argument("--pairs", default="",
                        help="comma-separated user_task_id:injection_task_id evaluation pairs")
    parser.add_argument("--random-offset", type=int, default=0,
                        help="skip this many compatible unique tasks in the seeded sample")
    parser.add_argument("--seed", type=int, default=20260717)
    parser.add_argument("--attack", default="direct")
    parser.add_argument("--no-plant", action="store_true")
    parser.add_argument("--output", required=True)
    parser.add_argument("--resume", action="store_true",
                        help="continue from task rows already checkpointed in --output")
    parser.add_argument("--contract-file",
                        help="optional task-id to TaskContract JSON mapping for oracle ablations")
    parser.add_argument("--plan-store", default="experiment_stage/defense_plan_effect_deepseek_v1")
    args = parser.parse_args()
    # Keep optional substrate-side policy inference on the same declared model.
    # The current AgentDojo pipeline sets defense=None, but must not inherit a
    # different hidden model if a tool activates that path later.
    os.environ["SECAGENT_POLICY_MODEL"] = args.contract_model
    from agentdojo.task_suite.load_suites import get_suite
    suite = get_suite("v1", args.suite)
    runtime_context = (json.loads(Path(args.runtime_context).read_text())
                       if args.runtime_context else {})
    engine = Engine(client_for_model(args.contract_model), args.contract_model)
    scope = f"agentdojo_{args.suite}_{args.boundary_mode}"
    source_carriers = ([vars(RUNTIME_CONTEXT_SOURCE)] if runtime_context else [])
    engine.register_trusted_tools(
        tool_registrations(suite, args.boundary_mode), PlanStore(args.plan_store, scope),
        source_carriers=source_carriers)
    runner = AgentDojoRunner(suite, pipeline_for(args.agent_model), engine)
    injections = json.loads(Path(args.injections).read_text()) if args.injections else {}
    contract_overrides = (json.loads(Path(args.contract_file).read_text())
                          if args.contract_file else {})
    plant_model = args.plant_model or args.contract_model
    plant_client = client_for_model(plant_model)
    plant_review_client = client_for_model(args.plant_review_model)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)

    def write_checkpoint(value):
        """Persist completed tasks so a long suite run can resume/inspect partial progress."""
        pending = output.with_suffix(output.suffix + ".tmp")
        pending.write_text(json.dumps(value, indent=2, ensure_ascii=False, default=str),
                           encoding="utf-8")
        pending.replace(output)

    def checkpoint():
        write_checkpoint(rows)

    def plant_for(contract):
        return ((lambda source, output: False) if args.no_plant else
                PlantDesigner(plant_client, plant_model, contract,
                              reviewer_client=plant_review_client,
                              reviewer_model=args.plant_review_model))

    if args.all_compatible_pairs:
        from agentdojo.attacks.attack_registry import load_attack
        attacker = load_attack(args.attack, suite, runner.pipeline)
        manifest_path = Path(args.pair_manifest) if args.pair_manifest else None
        if manifest_path is not None and manifest_path.exists():
            pairs = [tuple(item) for item in json.loads(manifest_path.read_text(encoding="utf-8"))]
        else:
            pairs = []
            for task_id in suite.user_tasks:
                user_task = suite.get_user_task_by_id(task_id)
                for injection_id in suite.injection_tasks:
                    injection_task = suite.get_injection_task_by_id(injection_id)
                    try:
                        attacker.attack(user_task, injection_task)
                    except ValueError:
                        continue
                    pairs.append((task_id, injection_id))
            if manifest_path is not None:
                manifest_path.parent.mkdir(parents=True, exist_ok=True)
                pending = manifest_path.with_suffix(manifest_path.suffix + ".tmp")
                pending.write_text(json.dumps(pairs, indent=2), encoding="utf-8")
                pending.replace(manifest_path)
        selected_pairs = pairs[:args.max_pairs] if args.max_pairs else pairs
        state = {"schema": "agentdojo-matrix-v1", "suite": args.suite,
                 "pair_manifest": str(manifest_path) if manifest_path else None,
                 "expected_pairs": len(pairs), "benign_by_task": {}, "attacks": []}
        if args.resume and output.exists():
            try:
                saved = json.loads(output.read_text(encoding="utf-8"))
                if isinstance(saved, dict) and saved.get("schema") == state["schema"]:
                    state.update(saved)
            except (OSError, json.JSONDecodeError):
                pass
        completed = {(row["task"], row["injection"]) for row in state["attacks"]}
        contracts = {}
        for task_id, injection_id in selected_pairs:
            user_task = suite.get_user_task_by_id(task_id)
            if task_id not in contracts:
                raw_contract = contract_overrides.get(task_id)
                contracts[task_id] = (TaskContract.from_dict(raw_contract)
                                      if raw_contract is not None
                                      else engine.contract(user_task.PROMPT))
            contract = contracts[task_id]
            if task_id not in state["benign_by_task"]:
                benign = runner.run(user_task, contract=contract,
                                    plant_factory=plant_for(contract),
                                    runtime_context=runtime_context)
                benign.pop("environment", None)
                state["benign_by_task"][task_id] = benign
                write_checkpoint(state)
            if (task_id, injection_id) in completed:
                continue
            injection_task = suite.get_injection_task_by_id(injection_id)
            attack_injections = attacker.attack(user_task, injection_task)
            attack_result = runner.run(
                user_task, injection_task=injection_task, injections=attack_injections,
                contract=contract, plant_factory=plant_for(contract),
                runtime_context=runtime_context)
            attack_result.pop("environment", None)
            state["attacks"].append({"task": task_id, "injection": injection_id,
                                     "attack_name": args.attack, "result": attack_result})
            completed.add((task_id, injection_id))
            write_checkpoint(state)
            print(json.dumps({"progress": len(state["attacks"]), "pairs": len(selected_pairs),
                              "task": task_id, "injection": injection_id,
                              "output": str(output)}, ensure_ascii=False), flush=True)
        attacks = state["attacks"]
        by_task = {}
        for row in attacks:
            by_task.setdefault(row["task"], []).append(row["result"])
        macro_utility = (sum(sum(item["utility"] for item in values) / len(values)
                             for values in by_task.values()) / len(by_task) if by_task else 0.0)
        macro_asr = (sum(sum(item["asr"] for item in values) / len(values)
                         for values in by_task.values()) / len(by_task) if by_task else 0.0)
        summary = {
            "output": str(output), "expected_pairs": len(pairs), "completed_pairs": len(attacks),
            "benign_tasks": len(state["benign_by_task"]),
            "benign_utility": sum(item["utility"] for item in state["benign_by_task"].values()),
            "attack_utility": sum(row["result"]["utility"] for row in attacks),
            "asr": sum(row["result"]["asr"] for row in attacks),
            "macro_attack_utility": macro_utility, "macro_asr": macro_asr,
            "approval_episodes": sum(any(_incident_has_route(i, "approval")
                                         for i in row["result"]["incidents"])
                                     for row in attacks),
            "auditor_episodes": sum(any(_incident_has_route(i, "auditor")
                                        for i in row["result"]["incidents"])
                                    for row in attacks),
            "plant_deployed": sum(len(row["result"]["plants_deployed"]) for row in attacks),
            "plant_committed": sum(len(row["result"]["plant_events"]) for row in attacks),
        }
        print(json.dumps(summary, ensure_ascii=False))
        return
    rows = []
    if args.resume and output.exists():
        try:
            saved = json.loads(output.read_text(encoding="utf-8"))
            if isinstance(saved, list):
                rows = saved
        except (OSError, json.JSONDecodeError):
            pass
    if args.random_pairs or args.pairs:
        from agentdojo.attacks.attack_registry import load_attack
        attacker = load_attack(args.attack, suite, runner.pipeline)
        if args.pairs:
            candidates = [tuple(item.split(":", 1)) for item in args.pairs.split(",") if ":" in item]
        else:
            candidates = [(uid, iid) for uid in suite.user_tasks for iid in suite.injection_tasks]
            random.Random(args.seed).shuffle(candidates)
        selected_tasks = {str(row.get("task")) for row in rows if isinstance(row, dict)}
        compatible_index = 0
        for task_id, injection_id in candidates:
            if args.random_pairs and len(rows) >= args.random_pairs: break
            if task_id in selected_tasks: continue
            user_task, injection_task = (suite.get_user_task_by_id(task_id),
                                         suite.get_injection_task_by_id(injection_id))
            try: attack_injections = attacker.attack(user_task, injection_task)
            except ValueError: continue
            selected_tasks.add(task_id)
            if compatible_index < args.random_offset:
                compatible_index += 1
                continue
            raw_contract = contract_overrides.get(task_id)
            contract = (TaskContract.from_dict(raw_contract) if raw_contract is not None
                        else engine.contract(user_task.PROMPT))
            benign = runner.run(user_task, contract=contract, plant_factory=plant_for(contract),
                                runtime_context=runtime_context)
            attack = runner.run(user_task, injection_task=injection_task,
                                injections=attack_injections, contract=contract,
                                plant_factory=plant_for(contract),
                                runtime_context=runtime_context)
            benign.pop("environment", None); attack.pop("environment", None)
            rows.append({"task": task_id, "injection": injection_id,
                         "attack_name": args.attack, "benign": benign, "attack": attack})
            checkpoint()
            print(json.dumps({"progress": len(rows), "task": task_id,
                              "output": str(output)}, ensure_ascii=False), flush=True)
            compatible_index += 1
    else:
        for task_id in filter(None, map(str.strip, args.tasks.split(","))):
            contract = engine.contract(suite.get_user_task_by_id(task_id).PROMPT)
            result = runner.run(suite.get_user_task_by_id(task_id), injections=injections,
                                contract=contract, plant_factory=plant_for(contract),
                                runtime_context=runtime_context)
            result.pop("environment", None)
            rows.append({"task": task_id, **result})
            checkpoint()
    checkpoint()
    if args.random_pairs or args.pairs:
        summary = {"pairs": len(rows),
                   "benign_utility": sum(row["benign"]["utility"] for row in rows),
                   "attack_utility": sum(row["attack"]["utility"] for row in rows),
                   "asr": sum(row["attack"]["asr"] for row in rows),
                   "pass": sum(d["route"] == "pass" for row in rows for d in row["attack"]["decisions"]),
                   "auditor": sum(_incident_has_route(i, "auditor")
                                  for row in rows for i in row["attack"]["incidents"]),
                   "approval": sum(_incident_has_route(i, "approval")
                                   for row in rows for i in row["attack"]["incidents"]),
                   "approved": sum(_incident_has_route(i, "approval") and i.get("approved") is True
                                   for row in rows for i in row["attack"]["incidents"]),
                   "rejected": sum(_incident_has_route(i, "approval") and i.get("approved") is False
                                   for row in rows for i in row["attack"]["incidents"]),
                   "benign_auditor": sum(_incident_has_route(i, "auditor")
                                         for row in rows for i in row["benign"]["incidents"]),
                   "benign_approval": sum(_incident_has_route(i, "approval")
                                          for row in rows for i in row["benign"]["incidents"]),
                   "benign_approved": sum(_incident_has_route(i, "approval") and
                                          i.get("approved") is True
                                          for row in rows for i in row["benign"]["incidents"]),
                   "plant_deployed": sum(len(row["attack"]["plants_deployed"]) for row in rows),
                   "plant_committed": sum(len(row["attack"]["plant_events"]) for row in rows),
                   "benign_plant_deployed": sum(len(row["benign"]["plants_deployed"])
                                                  for row in rows),
                   "benign_plant_committed": sum(len(row["benign"]["plant_events"])
                                                   for row in rows)}
    else:
        summary = {"tasks": len(rows), "utility": sum(row["utility"] for row in rows)}
    print(json.dumps({"output": str(output), **summary}, ensure_ascii=False))


if __name__ == "__main__": main()
