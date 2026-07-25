"""Run the matched AgentDyn clean pilot with an undefended DeepSeek agent."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from code.internal_client import client_for_model
from code.run_agentdyn_camel_clean_pilot import DEFAULT_TASKS, ROOT, STRATA


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT / "experiment_stage" / "agentdyn_undefended_clean15_20260723",
    )
    parser.add_argument("--model", default="deepseek-chat")
    parser.add_argument("--max-input-tokens", type=int, default=30_000)
    parser.add_argument("--full", action="store_true", help="run all 20 clean tasks per suite")
    parser.add_argument("--force-rerun", action="store_true")
    return parser.parse_args()


def build_pipeline(model: str, max_input_tokens: int):
    from agentdojo.agent_pipeline.agent_pipeline import AgentPipeline, PipelineConfig
    from agentdojo.agent_pipeline.llms.openai_llm import OpenAILLM

    llm = OpenAILLM(client_for_model(model), model)
    llm.name = model
    return AgentPipeline.from_config(
        PipelineConfig(
            llm=llm,
            model_id=None,
            defense=None,
            suite_name=None,
            system_message_name=None,
            system_message=None,
            max_input_tokens=max_input_tokens,
        )
    )


def result_path(output_dir: Path, model: str, suite: str, task_id: int) -> Path:
    return (
        output_dir
        / model
        / "no_defense"
        / suite
        / f"user_task_{task_id}"
        / "none"
        / "none.json"
    )


def main() -> None:
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    selected_tasks = (
        {suite: tuple(range(20)) for suite in DEFAULT_TASKS}
        if args.full
        else DEFAULT_TASKS
    )

    from agentdojo.benchmark import benchmark_suite_without_injections
    from agentdojo.logging import OutputLogger
    from agentdojo.task_suite.load_suites import get_suite

    manifest = {
        "schema": (
            "agentdyn-undefended-clean-full-v1"
            if args.full
            else "agentdyn-undefended-clean-pilot-v1"
        ),
        "matched_to": "agentdyn-camel-clean-full-v1" if args.full else "agentdyn-camel-clean-pilot-v1",
        "model": args.model,
        "benchmark_version": "v1",
        "defense": None,
        "tasks": {suite: list(tasks) for suite, tasks in selected_tasks.items()},
        "strata": None if args.full else STRATA,
        "max_input_tokens": args.max_input_tokens,
    }
    (args.output_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n"
    )

    pipeline = build_pipeline(args.model, args.max_input_tokens)
    with OutputLogger(str(args.output_dir)):
        for suite_name, tasks in selected_tasks.items():
            pending = [
                task_id
                for task_id in tasks
                if args.force_rerun
                or not result_path(args.output_dir, args.model, suite_name, task_id).exists()
            ]
            if not pending:
                print(f"[{suite_name}] complete; skipping", flush=True)
                continue
            print(f"[{suite_name}] pending={pending}", flush=True)
            benchmark_suite_without_injections(
                pipeline,
                get_suite("v1", suite_name),
                args.output_dir,
                args.force_rerun,
                user_tasks=[f"user_task_{task_id}" for task_id in pending],
                benchmark_version="v1",
            )

    rows = []
    for suite_name, tasks in selected_tasks.items():
        for task_id in tasks:
            path = result_path(args.output_dir, args.model, suite_name, task_id)
            if not path.exists():
                rows.append(
                    {
                        "suite": suite_name,
                        "task": task_id,
                        "status": "missing",
                        "utility": None,
                        "error": None,
                    }
                )
                continue
            result = json.loads(path.read_text())
            rows.append(
                {
                    "suite": suite_name,
                    "task": task_id,
                    "status": "done",
                    "utility": bool(result.get("utility")),
                    "error": result.get("error"),
                }
            )
    summary = {
        "schema": (
            "agentdyn-undefended-clean-full-summary-v1"
            if args.full
            else "agentdyn-undefended-clean-pilot-summary-v1"
        ),
        "completed": sum(row["status"] == "done" for row in rows),
        "utility_passed": sum(row["utility"] is True for row in rows),
        "runtime_errors": sum(bool(row["error"]) for row in rows),
        "by_suite": {
            suite: {
                "passed": sum(
                    row["utility"] is True for row in rows if row["suite"] == suite
                ),
                "total": sum(row["suite"] == suite for row in rows),
            }
            for suite in selected_tasks
        },
        "rows": rows,
    }
    (args.output_dir / "summary.json").write_text(
        json.dumps(summary, indent=2) + "\n"
    )
    print(json.dumps(summary, indent=2), flush=True)


if __name__ == "__main__":
    main()
