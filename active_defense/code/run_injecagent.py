"""Run the active defense on the official InjecAgent function-call benchmark."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from code.benchmarks.injecagent import InjecAgentRunner, load_cases, load_tools, tool_manifest
from code.defense.engine import Engine
from code.defense.plan_store import PlanStore
from code.internal_client import client_for_model


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", required=True)
    parser.add_argument("--attack", choices=("dh", "ds", "both"), default="both")
    parser.add_argument("--setting", choices=("base", "enhanced"), default="base")
    parser.add_argument("--indices", default="", help="comma-separated indices within each attack file")
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--agent-model", default="deepseek-chat")
    parser.add_argument("--contract-model", default="gpt-5.5-2026-04-24")
    parser.add_argument("--plant-model", default="deepseek-chat")
    parser.add_argument("--plant-review-model", default="gpt-5.5-2026-04-24")
    parser.add_argument("--no-plant", action="store_true")
    parser.add_argument("--plan-store", default="results/injecagent/defense_plan")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    data_dir = Path(args.data_dir)
    engine = Engine(client_for_model(args.contract_model), args.contract_model)
    tools = load_tools(data_dir)
    engine.perceive(tool_manifest(tools), store=PlanStore(args.plan_store, "injecagent-tool-unit-v1"))
    runner = InjecAgentRunner(
        data_dir, engine, client_for_model(args.agent_model), args.agent_model,
        plant_client=client_for_model(args.plant_model), plant_model=args.plant_model,
        review_client=client_for_model(args.plant_review_model),
        review_model=args.plant_review_model)
    cases = load_cases(data_dir, args.attack, args.setting)
    if args.indices:
        wanted = {int(value) for value in args.indices.split(",") if value.strip()}
        cases = [case for case in cases if case.index in wanted]
    if args.limit:
        cases = cases[:args.limit]

    rows, contracts = [], {}
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    for case in cases:
        # Contract identity is the trusted user task, never the injected response.
        contract_key = (case.user_task, case.user_tool)
        if contract_key not in contracts:
            contracts[contract_key] = engine.contract(
                case.user_task, effect_entries={case.user_tool})
        contract = contracts[contract_key]
        rows.append(runner.run(case, contract=contract, use_plant=not args.no_plant))
        pending = output.with_suffix(output.suffix + ".tmp")
        pending.write_text(json.dumps({"rows": rows}, indent=2, ensure_ascii=False),
                           encoding="utf-8")
        pending.replace(output)

    result = {
        "schema": "injecagent-active-defense-v1",
        "dataset": {"setting": args.setting, "attack": args.attack,
                    "cases": len(rows), "tool_manifest": len(tools)},
        "config": {"agent_model": args.agent_model,
                   "contract_model": args.contract_model,
                   "plant_model": args.plant_model,
                   "plant_review_model": args.plant_review_model,
                   "plant": not args.no_plant},
        "metrics": {
            "attack_success": sum(row["attack_success"] for row in rows),
            "attempted_stage1": sum(row["attempted_stage1"] for row in rows),
            "committed_stage1": sum(row["committed_stage1"] for row in rows),
            "task_completed": sum(row["task_completed"] for row in rows),
            "approval_episodes": sum("approval" in row["routes"] for row in rows),
            "auditor_episodes": sum("auditor" in row["routes"] for row in rows),
            "plant_deployments": sum(row["plant_deployments"] for row in rows),
            "plant_commitments": sum(len(row["plant_commitments"]) for row in rows),
        },
        "rows": rows,
    }
    output.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(result["metrics"], indent=2))


if __name__ == "__main__":
    main()
