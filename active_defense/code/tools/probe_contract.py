"""Generate minimal contracts from a benchmark's trusted tasks; no runtime or GT review."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from code.benchmarks.agentdojo import tool_schemas
from code.defense.engine import Engine


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--suite", default="slack")
    parser.add_argument("--tasks", default="user_task_1")
    parser.add_argument("--model", default="deepseek-chat")
    parser.add_argument("--boundary-mode", choices=("declared", "inferred"), default="declared")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    from agentdojo.task_suite.load_suites import get_suite
    suite = get_suite("v1", args.suite)
    engine = Engine(args.model)
    plan = engine.perceive(tool_schemas(suite, args.boundary_mode))
    rows = []
    for task_id in filter(None, map(str.strip, args.tasks.split(","))):
        task = suite.get_user_task_by_id(task_id)
        contract = engine.contract(task.PROMPT)
        rows.append({"task": task_id, "contract": contract.to_dict()})
    result = {"suite": args.suite, "model": args.model, "plan": plan.to_dict(), "tasks": rows}
    output = Path(args.output); output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({"output": str(output), "tasks": len(rows)}, ensure_ascii=False))


if __name__ == "__main__": main()
