"""Checkpointed paired SkillInject runs with independent target/guard models."""
from __future__ import annotations

import argparse
import json
import subprocess
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from code.benchmarks.skillinject.execution.batch import BENCH, REPO, _sandbox


def _run(command: list[str], timeout: int) -> None:
    subprocess.run(command, cwd=REPO, check=True, timeout=timeout)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", default=str(
        Path(__file__).resolve().parents[1] / "data" / "cases.json"))
    parser.add_argument("--output-root", required=True)
    parser.add_argument("--work-root", required=True)
    parser.add_argument("--baseline", action="append",
                        choices=("undefended", "clawguard", "progent",
                                 "taskshield"))
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--injection-limit", type=int, default=0)
    parser.add_argument("--task-limit", type=int, default=0)
    parser.add_argument("--model", default="deepseek-v4-flash")
    parser.add_argument("--guard-model", default="gpt-5.5-2026-04-24")
    parser.add_argument("--judge-model", default="gpt-5.4-2026-03-05")
    parser.add_argument("--case-timeout", type=int, default=900)
    args = parser.parse_args()
    if args.workers < 1 or args.case_timeout < 1:
        raise ValueError("workers and case-timeout must be positive")

    output = Path(args.output_root)
    work = Path(args.work_root)
    output.mkdir(parents=True, exist_ok=True)
    work.mkdir(parents=True, exist_ok=True)
    rows = json.loads(Path(args.dataset).read_text(encoding="utf-8"))
    if args.injection_limit:
        rows = rows[:args.injection_limit]
    pairs = []
    for row in rows:
        tasks = list(row.get("tasks") or ())
        if args.task_limit:
            tasks = tasks[:args.task_limit]
        pairs.extend((row, index, task) for index, task in enumerate(tasks))
    baselines = args.baseline or ["progent", "taskshield"]

    def run_pair(baseline: str, row: dict, index: int, task: dict) -> dict:
        stem = f"id{int(row['id']):03d}_task{index}"
        target_dir = output / baseline
        clean_out = target_dir / f"{stem}_clean.json"
        attack_out = target_dir / f"{stem}_attack.json"
        if clean_out.is_file() and attack_out.is_file():
            return {"baseline": baseline, "pair": stem, "status": "skip"}
        with tempfile.TemporaryDirectory(
                prefix=f"{baseline}_{stem}_", dir=work) as raw:
            root = Path(raw)
            for condition, destination, clean in (
                ("clean", clean_out, True), ("attack", attack_out, False),
            ):
                if destination.is_file():
                    continue
                sandbox = _sandbox(row, task, root / condition, clean)
                command = [
                    "python3", "-m", "code.benchmarks.skillinject.execution.baselines",
                    "--baseline", baseline, "--sandbox", str(sandbox),
                    "--task", task["prompt"], "--condition", condition,
                    "--model", args.model, "--guard-model", args.guard_model,
                    "--judge-model", args.judge_model,
                    "--attack-judge-prompt", str(row.get("judge_prompt") or ""),
                    "--attack-context", json.dumps(
                        row.get("instructions") or {}, ensure_ascii=False),
                    "--output", str(destination),
                ]
                for token in (row.get("task_scripts") or {}):
                    command.extend(["--attack-token", str(token)])
                _run(command, args.case_timeout)
        return {"baseline": baseline, "pair": stem, "status": "done"}

    jobs = [(baseline, *pair) for baseline in baselines for pair in pairs]
    failures = []
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        pending = {pool.submit(run_pair, *job): job for job in jobs}
        for future in as_completed(pending):
            try:
                print(json.dumps(future.result()), flush=True)
            except Exception as exc:
                baseline, row, index, _task = pending[future]
                failure = {"baseline": baseline, "id": row.get("id"),
                           "task": index, "error": repr(exc)}
                failures.append(failure)
                print(json.dumps(failure), flush=True)
    state = {
        "agent_model": args.model,
        "guard_model": args.guard_model,
        "judge_model": args.judge_model,
        "pairs_per_baseline": len(pairs),
        "baselines": baselines,
        "completed": {
            baseline: {
                "clean": len(list((output / baseline).glob("*_clean.json"))),
                "attack": len(list((output / baseline).glob("*_attack.json"))),
            } for baseline in baselines
        },
        "failures": failures,
    }
    (output / "run_state.json").write_text(
        json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(state, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
