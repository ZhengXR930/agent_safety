"""Checkpointed full AgentDojo evaluation for the current lean defense.

Each benign task receives one frozen Contract.  The same Contract is reused for
its clean episode and every compatible attack pair so policy-generation variance
cannot change the clean/attack comparison.  Results are written atomically after
every episode and may be resumed safely.
"""
from __future__ import annotations

import argparse
import copy
import json
import time
from pathlib import Path

from code.benchmarks.agentdojo_protocol_runtime import (
    activate_vendored_agentdojo, load_frozen_contracts, load_pair_manifest)

activate_vendored_agentdojo()

from agentdojo.agent_pipeline.agent_pipeline import (
    AgentPipeline, PipelineConfig, load_system_message)
from agentdojo.agent_pipeline.llms.openai_llm import OpenAILLM
from agentdojo.task_suite.load_suites import get_suite

from code.benchmarks.agentdojo.runtime import AgentDojoRunner
from code.ours.defense.contract import EffectClause, TaskContract
from code.ours.defense.engine import Engine
from code.core.client import client_for_model


def pipeline_for(model):
    if str(model).lower().startswith("gpt-"):
        from agentdojo.attacks.base_attacks import MODEL_NAMES
        MODEL_NAMES.setdefault(str(model), "GPT-4.1")
    llm = OpenAILLM(client_for_model(model), model)
    llm.name = model
    return AgentPipeline.from_config(PipelineConfig(
        llm=llm, model_id=None, defense=None,
        system_message_name=None,
        system_message=load_system_message(None)))


def _write(path: Path, state: dict) -> None:
    state["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(state, indent=2, ensure_ascii=False, default=str),
        encoding="utf-8")
    temporary.replace(path)


def _strip_trace(result: dict) -> dict:
    result.pop("environment", None)
    return result


def _inspect_contract(task: str, contract: TaskContract) -> dict:
    """Fail before evaluation when synthesis or compilation produced no policy."""
    if contract.task != task:
        raise ValueError("Contract task does not exactly match trusted task")
    if not contract.clauses:
        raise ValueError("Contract is empty")
    return {
        "clauses": len(contract.clauses),
        "effects": [clause.action for clause in contract.clauses
                    if isinstance(clause, EffectClause)],
    }


def _summary(state: dict, total_pairs: int, total_tasks: int) -> dict:
    benign = state["benign_by_task"]
    attacks = state["attacks"]
    by_task: dict[str, list[dict]] = {}
    for row in attacks:
        by_task.setdefault(row["task"], []).append(row["result"])
    return {
        "benign_completed": len(benign),
        "benign_total": total_tasks,
        "benign_passed": sum(bool(row["utility"]) for row in benign.values()),
        "attack_completed": len(attacks),
        "attack_total": total_pairs,
        "attack_successes": sum(bool(row["result"]["asr"]) for row in attacks),
        "attack_utility_passed": sum(
            bool(row["result"]["utility"]) for row in attacks),
        "macro_asr": (
            sum(sum(bool(x["asr"]) for x in rows) / len(rows)
                for rows in by_task.values()) / len(by_task)
            if by_task else 0.0),
        "macro_attack_utility": (
            sum(sum(bool(x["utility"]) for x in rows) / len(rows)
                for rows in by_task.values()) / len(by_task)
            if by_task else 0.0),
        "status": ("complete" if len(benign) == total_tasks and
                   len(attacks) == total_pairs else "running"),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--suite", required=True)
    parser.add_argument("--benchmark-version", default="v1.2.2")
    parser.add_argument("--agent-model", default="deepseek-v4-flash")
    parser.add_argument("--contract-model", default="gpt-5.5-2026-04-24")
    parser.add_argument("--attack", default="important_instructions")
    parser.add_argument("--pair-manifest", required=True)
    parser.add_argument(
        "--contract-file", action="append", default=[],
        help=("manual/frozen task-id to Contract bundle; repeat to overlay "
              "newer task contracts on an older bundle"))
    parser.add_argument("--output", required=True)
    parser.add_argument("--max-pairs", type=int, default=0)
    parser.add_argument(
        "--task-overrides", default="",
        help="JSON mapping task ids to clarified prompts; recorded in config")
    parser.add_argument(
        "--approval-policy", choices=("none", "approve-all"), default="none",
        help="explicit eval-only simulated user; never enabled by default")
    parser.add_argument("--ablation-mode",
                        choices=("full", "wrap_only", "plant_only"),
                        default="full")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument(
        "--clean-only", action="store_true",
        help="run each unique clean task once without constructing attacks")
    parser.add_argument("--preflight-only", action="store_true",
                        help="generate, validate and freeze all Contracts only")
    parser.add_argument(
        "--frozen-contracts-only", action="store_true",
        help="fail if a selected task is missing from --contract-file")
    args = parser.parse_args()

    overrides = (json.loads(Path(args.task_overrides).read_text(encoding="utf-8"))
                 if args.task_overrides else {})
    if not isinstance(overrides, dict) or any(
            not isinstance(key, str) or not isinstance(value, str)
            for key, value in overrides.items()):
        raise ValueError("task overrides must be a JSON string mapping")

    pairs = load_pair_manifest(args.pair_manifest)
    if args.max_pairs:
        pairs = pairs[:args.max_pairs]
    task_ids = list(dict.fromkeys(task for task, _ in pairs))
    attack_total = 0 if args.clean_only else len(pairs)
    config = {
        "suite": args.suite,
        "benchmark_version": args.benchmark_version,
        "agent_model": args.agent_model,
        "contract_model": args.contract_model,
        "attack": args.attack,
        "pair_manifest": args.pair_manifest,
        "contract_file": list(args.contract_file),
        "max_pairs": args.max_pairs,
        "approval_policy": args.approval_policy,
        "ablation_mode": args.ablation_mode,
        "task_overrides": args.task_overrides,
        "preflight_only": args.preflight_only,
        "clean_only": args.clean_only,
        "frozen_contracts_only": args.frozen_contracts_only,
    }
    output = Path(args.output)
    if args.resume and output.exists():
        state = json.loads(output.read_text(encoding="utf-8"))
        if state.get("config") != config:
            raise ValueError("resume config differs from checkpoint config")
    else:
        state = {
            "schema": "agentdojo-lean-full-v1",
            "config": config,
            "started_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "contracts": {},
            "contract_quality": {},
            "benign_by_task": {},
            "attacks": [],
        }

    suite = get_suite(args.benchmark_version, args.suite)
    engine = Engine(
        args.contract_model,
        approval_enabled=args.approval_policy == "approve-all",
        ablation_mode=args.ablation_mode)
    approver = ((lambda _request: True)
                if args.approval_policy == "approve-all" else None)
    runner = AgentDojoRunner(
        suite, pipeline_for(args.agent_model), engine, approver=approver)
    attacker = None
    if not args.clean_only:
        from agentdojo.attacks.attack_registry import load_attack
        attacker = load_attack(args.attack, suite, runner.pipeline)
    frozen = {}
    for contract_file in args.contract_file:
        rows, _bundle = load_frozen_contracts(contract_file)
        frozen.update(rows)

    # A frozen Contract and its trusted task text are one versioned asset.
    # Validate the whole selected shard before issuing any model request so a
    # missing companion override cannot fail halfway through an experiment.
    for task_id in task_ids:
        if task_id not in frozen:
            if args.frozen_contracts_only:
                raise ValueError(
                    f"missing frozen Contract for {args.suite}:{task_id}")
            continue
        trusted_task = overrides.get(
            task_id, suite.get_user_task_by_id(task_id).PROMPT)
        frozen_task = frozen[task_id].get("task")
        if frozen_task != trusted_task:
            raise ValueError(
                f"Frozen Contract/task mismatch for {args.suite}:{task_id}; "
                "load the companion frozen task-overrides asset")

    completed = {(row["task"], row["injection"]) for row in state["attacks"]}
    contracts: dict[str, TaskContract] = {}
    for task_id, injection_id in pairs:
        if (args.preflight_only and
                task_id in state.get("contract_quality", {})):
            continue
        user_task = copy.copy(suite.get_user_task_by_id(task_id))
        if task_id in overrides:
            user_task.PROMPT = overrides[task_id]
        if task_id not in contracts:
            if task_id in state["contracts"]:
                contract = TaskContract.from_dict(state["contracts"][task_id])
            elif task_id in frozen:
                contract = TaskContract.from_dict(frozen[task_id])
                state["contracts"][task_id] = contract.to_dict()
                state["summary"] = _summary(state, attack_total, len(task_ids))
                _write(output, state)
            else:
                if args.frozen_contracts_only:
                    raise ValueError(
                        f"missing frozen Contract for {args.suite}:{task_id}")
                contract = engine.contract(user_task.PROMPT)
                state["contracts"][task_id] = contract.to_dict()
                state["summary"] = _summary(state, attack_total, len(task_ids))
                _write(output, state)
            contracts[task_id] = contract
            # AgentDojoRunner records the engine trace even when a Contract is
            # supplied.  Register the frozen object so resume/manual ablations
            # do not trigger an unused second synthesis call.
            key = engine._key(user_task.PROMPT, None)
            engine._contracts[key] = contract
            engine._traces.setdefault(key, {"source": "frozen-or-checkpoint"})
        contract = contracts[task_id]
        quality = _inspect_contract(user_task.PROMPT, contract)
        state.setdefault("contract_quality", {})[task_id] = quality
        if args.preflight_only:
            state["summary"] = _summary(state, attack_total, len(task_ids))
            _write(output, state)
            print(json.dumps({
                "mode": "preflight", "task": task_id, **quality,
                "contracts": len(state["contracts"]),
                "contract_total": len(task_ids),
            }, ensure_ascii=False), flush=True)
            continue

        if task_id not in state["benign_by_task"]:
            state["benign_by_task"][task_id] = _strip_trace(
                runner.run(user_task, contract=contract))
            state["summary"] = _summary(state, attack_total, len(task_ids))
            _write(output, state)
            print(json.dumps({
                "mode": "clean", "task": task_id,
                "utility": state["benign_by_task"][task_id]["utility"],
                "summary": state["summary"],
            }, ensure_ascii=False), flush=True)

        if args.clean_only:
            continue

        if (task_id, injection_id) in completed:
            continue
        injection_task = suite.get_injection_task_by_id(injection_id)
        injections = attacker.attack(user_task, injection_task)
        result = _strip_trace(runner.run(
            user_task, injection_task=injection_task, injections=injections,
            contract=contract))
        state["attacks"].append({
            "task": task_id,
            "injection": injection_id,
            "attack_name": args.attack,
            "result": result,
        })
        completed.add((task_id, injection_id))
        state["summary"] = _summary(state, attack_total, len(task_ids))
        _write(output, state)
        print(json.dumps({
            "mode": "attack", "task": task_id,
            "injection": injection_id, "attack_name": args.attack,
            "utility": result["utility"], "asr": result["asr"],
            "summary": state["summary"],
        }, ensure_ascii=False), flush=True)

    state["summary"] = _summary(state, attack_total, len(task_ids))
    _write(output, state)
    print(json.dumps(state["summary"], ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
