"""Checkpointed clean-utility evaluation for a Progent AgentDojo suite."""
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


def run(args: argparse.Namespace) -> dict:
    target_args = SimpleNamespace(
        suite=args.suite,
        defense="progent",
        user_task="user_task_0",
        injection_task="injection_task_1",
        agent_model=args.agent_model,
        policy_model=args.policy_model,
        progent_cache_dir=args.progent_cache_dir,
        progent_cache_label=args.progent_cache_label,
    )
    target = PolicyTarget(target_args)
    output = Path(args.output)
    if args.resume and output.exists():
        state = json.loads(output.read_text(encoding="utf-8"))
    else:
        state = {
            "config": vars(args),
            "started_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "records": [],
        }
    completed = {row["user_task"] for row in state["records"]}
    task_ids = sorted(target.evaluator.suite.user_tasks)
    if args.max_tasks is not None:
        task_ids = task_ids[:args.max_tasks]
    for task_id in task_ids:
        if task_id in completed:
            continue
        task = target.evaluator.suite.get_user_task_by_id(task_id)
        started = time.monotonic()
        try:
            utility, _ = target.evaluator.suite.run_task_with_pipeline(
                target.evaluator.pipeline, task, injection_task=None, injections={},
            )
            record = {
                "user_task": task_id,
                "utility": bool(utility),
                "error": None,
                "elapsed_seconds": round(time.monotonic() - started, 3),
            }
        except Exception as exc:  # preserve failures rather than losing the checkpoint
            record = {
                "user_task": task_id,
                "utility": False,
                "error": f"{type(exc).__name__}: {exc}",
                "elapsed_seconds": round(time.monotonic() - started, 3),
            }
        state["records"].append(record)
        done = len(state["records"])
        passed = sum(row["utility"] for row in state["records"])
        state["summary"] = {
            "completed": done,
            "total": len(task_ids),
            "utility_passed": passed,
            "utility_rate": passed / done,
            "errors": sum(row["error"] is not None for row in state["records"]),
            "status": "complete" if done == len(task_ids) else "running",
        }
        _write(output, state)
        print(json.dumps({"latest": record, "summary": state["summary"]}), flush=True)
    return state["summary"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--suite", default="slack")
    parser.add_argument("--agent-model", default="deepseek-chat")
    parser.add_argument("--policy-model", default="deepseek-chat")
    parser.add_argument(
        "--progent-cache-dir",
        default="baseline/AutoDojo/agentdojo/variant_generation/progent/cache",
    )
    parser.add_argument("--progent-cache-label", default="openai/gpt-4o")
    parser.add_argument("--output", required=True)
    parser.add_argument("--max-tasks", type=int)
    parser.add_argument("--resume", action="store_true")
    return parser.parse_args()


if __name__ == "__main__":
    print(json.dumps(run(parse_args()), ensure_ascii=False), flush=True)
