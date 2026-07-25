"""Run a checkpointed, stratified AgentDyn clean pilot with online CaMeL."""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

from code.internal_client import read_config_key


ROOT = Path(__file__).resolve().parents[1]
AGENTDOJO_SRC = ROOT / "baseline" / "AutoDojo" / "agentdojo" / "src"
DEFAULT_TASKS = {
    "shopping": (0, 5, 8, 13, 18),
    "github": (0, 2, 3, 12, 19),
    "dailylife": (0, 3, 7, 11, 17),
}
STRATA = {
    "shopping": {
        0: "simple_search_then_purchase",
        5: "history_discount_email_multi_source",
        8: "cross_account_conditional_purchase",
        13: "read_only_aggregation",
        18: "longest_refund_discount_purchase_chain",
    },
    "github": {
        0: "web_download_repository_chain",
        2: "direct_transfer_with_verification",
        3: "repository_selection_plus_email_identity",
        12: "collection_iteration_and_multi_invite",
        19: "email_grounded_open_ended_work",
    },
    "dailylife": {
        0: "web_grounded_open_ended_homework",
        3: "bill_form_payment_chain",
        7: "web_payment_calendar_multi_effect",
        11: "email_attachment_cv_email_chain",
        17: "cross_site_meeting_reservation_calendar",
    },
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT / "experiment_stage" / "agentdyn_camel_clean15_20260723",
    )
    parser.add_argument("--model", default="deepseek-chat")
    parser.add_argument("--max-input-tokens", type=int, default=30_000)
    parser.add_argument("--full", action="store_true", help="run all 20 clean tasks per suite")
    parser.add_argument("--force-rerun", action="store_true")
    return parser.parse_args()


def result_path(output_dir: Path, model: str, suite: str, task_id: int) -> Path:
    return (
        output_dir
        / model
        / "camel"
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
    key = read_config_key("DEEPSEEK_API_KEY")
    if not key:
        raise RuntimeError("Missing DEEPSEEK_API_KEY in project config")

    env = os.environ.copy()
    env["CAMEL_LOCAL_BASE_URL"] = "https://api.deepseek.com"
    env["CAMEL_API_KEY"] = key
    env["PYTHONPATH"] = os.pathsep.join(
        (str(AGENTDOJO_SRC), env.get("PYTHONPATH", ""))
    ).rstrip(os.pathsep)

    manifest = {
        "schema": "agentdyn-camel-clean-full-v1" if args.full else "agentdyn-camel-clean-pilot-v1",
        "model": args.model,
        "benchmark_version": "v1",
        "defense": "camel",
        "tasks": {suite: list(tasks) for suite, tasks in selected_tasks.items()},
        "strata": None if args.full else STRATA,
        "max_input_tokens": args.max_input_tokens,
        "camel_decision_path": {
            "use_original": False,
            "replay_with_policies": False,
            "security_policy_engine": "ADNoSecurityPolicyEngine",
            "policy_behavior": "always Allowed",
        },
    }
    (args.output_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n"
    )

    for suite, tasks in selected_tasks.items():
        pending = [
            task_id
            for task_id in tasks
            if args.force_rerun
            or not result_path(args.output_dir, args.model, suite, task_id).exists()
        ]
        if not pending:
            print(f"[{suite}] complete; skipping", flush=True)
            continue
        command = [
            sys.executable,
            "-m",
            "agentdojo.scripts.benchmark",
            "--model",
            "local",
            "--model-id",
            args.model,
            "--benchmark-version",
            "v1",
            "--suite",
            suite,
            "--defense",
            "camel",
            "--logdir",
            str(args.output_dir),
            "--max-input-tokens",
            str(args.max_input_tokens),
        ]
        for task_id in pending:
            command.extend(("--user-task", f"user_task_{task_id}"))
        if args.force_rerun:
            command.append("--force-rerun")
        print(f"[{suite}] pending={pending}", flush=True)
        subprocess.run(command, cwd=ROOT, env=env, check=True)

    rows = []
    for suite, tasks in selected_tasks.items():
        for task_id in tasks:
            path = result_path(args.output_dir, args.model, suite, task_id)
            if not path.exists():
                rows.append(
                    {
                        "suite": suite,
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
                    "suite": suite,
                    "task": task_id,
                    "status": "done",
                    "utility": bool(result.get("utility")),
                    "error": result.get("error"),
                }
            )
    summary = {
        "schema": "agentdyn-camel-clean-full-summary-v1" if args.full else "agentdyn-camel-clean-pilot-summary-v1",
        "completed": sum(row["status"] == "done" for row in rows),
        "utility_passed": sum(row["utility"] is True for row in rows),
        "runtime_errors": sum(bool(row["error"]) for row in rows),
        "rows": rows,
    }
    (args.output_dir / "summary.json").write_text(
        json.dumps(summary, indent=2) + "\n"
    )
    print(json.dumps(summary, indent=2), flush=True)


if __name__ == "__main__":
    main()
