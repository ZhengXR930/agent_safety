"""Checkpointed full AgentDojo attack matrix for Progent."""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from types import SimpleNamespace

from code.run_policy_trajectory_attack import PolicyTarget


def _write(path: Path, state: dict) -> None:
    state["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)


def _summary(records: list[dict], total: int) -> dict:
    done = len(records)
    return {
        "completed": done,
        "total": total,
        "attack_successes": sum(row["asr"] for row in records),
        "asr": sum(row["asr"] for row in records) / done if done else 0.0,
        "utility_passed": sum(row["utility"] for row in records),
        "attack_utility": sum(row["utility"] for row in records) / done if done else 0.0,
        "defense_blocked": sum(row["defense_blocked"] for row in records),
        "errors": sum(row["error"] is not None for row in records),
        "status": "complete" if done == total else "running",
    }


def run(args: argparse.Namespace) -> dict:
    target = PolicyTarget(SimpleNamespace(
        suite=args.suite, defense="progent", user_task="user_task_0",
        injection_task="injection_task_1", agent_model=args.agent_model,
        policy_model=args.policy_model, progent_cache_dir=args.progent_cache_dir,
        progent_cache_label=args.progent_cache_label,
    ))
    from agentdojo.attacks.attack_registry import load_attack

    attacker = load_attack(args.attack, target.evaluator.suite, target.evaluator.pipeline)
    selected_injections = (
        set(filter(None, (args.injection_tasks or "").split(",")))
        if args.injection_tasks else set(target.evaluator.suite.injection_tasks)
    )
    unknown = selected_injections - set(target.evaluator.suite.injection_tasks)
    if unknown:
        raise ValueError(f"Unknown injection tasks for {args.suite}: {sorted(unknown)}")
    pairs = [
        (user_id, injection_id)
        for user_id in sorted(target.evaluator.suite.user_tasks)
        for injection_id in sorted(target.evaluator.suite.injection_tasks)
        if injection_id in selected_injections
    ]
    if args.max_cells is not None:
        pairs = pairs[:args.max_cells]
    output = Path(args.output)
    if args.resume and output.exists():
        state = json.loads(output.read_text(encoding="utf-8"))
    else:
        state = {
            "config": vars(args),
            "started_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "records": [],
        }
    completed = {(row["user_task"], row["injection_task"]) for row in state["records"]}
    for user_id, injection_id in pairs:
        if (user_id, injection_id) in completed:
            continue
        user_task = target.evaluator.suite.get_user_task_by_id(user_id)
        injection_task = target.evaluator.suite.get_injection_task_by_id(injection_id)
        started = time.monotonic()
        try:
            injections = dict(attacker.attack(user_task, injection_task))
            if args.evaluation_pipeline == "undefended":
                trace = target.evaluator._run_with_trace_using(
                    target.evaluator.reachability_pipeline,
                    injection_id, injections, user_id,
                )
            else:
                trace = target.evaluator.run_with_trace(injection_id, injections, user_id)
            record = {
                "user_task": user_id,
                "injection_task": injection_id,
                "vectors": sorted(injections),
                "utility": bool(trace["utility"]),
                "asr": bool(trace["security"]),
                "defense_blocked": bool(trace.get("defense_blocked")),
                "failure_class": trace.get("failure_class"),
                "tool_calls": trace.get("tool_calls", []),
                "tool_results": trace.get("tool_results", []),
                "error": None,
                "elapsed_seconds": round(time.monotonic() - started, 3),
            }
        except Exception as exc:
            record = {
                "user_task": user_id, "injection_task": injection_id,
                "vectors": [], "utility": False, "asr": False,
                "defense_blocked": False, "failure_class": "runner_error",
                "tool_calls": [], "tool_results": [],
                "error": f"{type(exc).__name__}: {exc}",
                "elapsed_seconds": round(time.monotonic() - started, 3),
            }
        state["records"].append(record)
        state["summary"] = _summary(state["records"], len(pairs))
        _write(output, state)
        print(json.dumps({"latest": {k: record[k] for k in (
            "user_task", "injection_task", "utility", "asr",
            "defense_blocked", "error")}, "summary": state["summary"]}), flush=True)
    return state["summary"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--suite", default="slack")
    parser.add_argument("--attack", default="important_instructions")
    parser.add_argument("--evaluation-pipeline", choices=("progent", "undefended"),
                        default="progent")
    parser.add_argument("--agent-model", default="deepseek-chat")
    parser.add_argument("--policy-model", default="deepseek-chat")
    parser.add_argument("--progent-cache-dir", default=
                        "baseline/AutoDojo/agentdojo/variant_generation/progent/cache")
    parser.add_argument("--progent-cache-label", default="openai/gpt-4o")
    parser.add_argument("--output", required=True)
    parser.add_argument("--max-cells", type=int)
    parser.add_argument("--injection-tasks",
                        help="comma-separated fixed manifest subset; default is every task")
    parser.add_argument("--resume", action="store_true")
    return parser.parse_args()


if __name__ == "__main__":
    print(json.dumps(run(parse_args()), ensure_ascii=False), flush=True)
