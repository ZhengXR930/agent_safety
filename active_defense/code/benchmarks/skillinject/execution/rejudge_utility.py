"""Replay SkillInject utility judging without rerunning the target agent.

New result records persist the exact evidence shown to the utility judge.  This
command consumes that evidence and writes new result files to a separate output
directory, so a transient judge outage never forces an agent rerun or overwrites
the original trace.
"""
from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path

from code.benchmarks.skillinject.execution.baselines import (
    judge_utility_evidence, utility_judge_metadata)


def _inputs(source: Path) -> list[Path]:
    if source.is_file():
        return [source]
    if not source.is_dir():
        raise ValueError(f"input does not exist: {source}")
    return sorted({*source.glob("*_clean.json"), *source.glob("*_attack.json")})


def _write_atomic(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pending = path.with_suffix(path.suffix + ".tmp")
    pending.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8")
    pending.replace(path)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output-root", required=True)
    parser.add_argument("--judge-model", required=True)
    parser.add_argument("--attempts", type=int, default=3)
    parser.add_argument(
        "--all", action="store_true",
        help="rejudge boolean results too; by default only technical/null results")
    parser.add_argument(
        "--resume", action="store_true",
        help="skip output files that already exist")
    args = parser.parse_args()
    if args.attempts < 1:
        raise ValueError("attempts must be positive")

    source = Path(args.input).resolve()
    output = Path(args.output_root).resolve()
    if source == output:
        raise ValueError("output-root must differ from input")

    written = skipped = failed = 0
    for path in _inputs(source):
        target = output / path.name
        if target.exists():
            if args.resume:
                skipped += 1
                continue
            raise FileExistsError(target)

        record = json.loads(path.read_text(encoding="utf-8"))
        if not args.all and isinstance(record.get("utility"), bool):
            skipped += 1
            continue
        evidence = record.get("utility_evidence")
        task = record.get("task")
        if not isinstance(evidence, str) or not isinstance(task, str):
            failed += 1
            print(json.dumps({
                "input": str(path), "status": "missing-persisted-evidence"
            }, ensure_ascii=False), flush=True)
            continue

        updated = copy.deepcopy(record)
        updated.setdefault("utility_rejudge_history", []).append({
            "utility": record.get("utility"),
            "utility_reason": record.get("utility_reason"),
            "utility_judge": record.get("utility_judge"),
            "source": str(path),
        })
        utility, reason = judge_utility_evidence(
            task, evidence, args.judge_model, attempts=args.attempts)
        updated["utility"] = utility
        updated["utility_reason"] = reason
        updated["utility_judge"] = {
            **utility_judge_metadata(evidence, args.judge_model),
            "attempts": args.attempts,
            "rejudged_from": str(path),
        }
        _write_atomic(target, updated)
        written += 1
        print(json.dumps({
            "input": str(path), "output": str(target),
            "utility": utility, "utility_reason": reason,
        }, ensure_ascii=False), flush=True)

    summary = {"written": written, "skipped": skipped, "failed": failed}
    print(json.dumps(summary, ensure_ascii=False), flush=True)
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
