"""Checkpointed SCR baseline matrix with DeepSeek target and GPT guard."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from code.benchmarks.scr.execution.fusion_overlay import load_suite
from code.benchmarks.scr.execution.clawguard import load_auth_cases


REPO = Path(__file__).resolve().parents[4]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scr-root", default=str(REPO.parent / "benchmarks" / "SCR_Bench"))
    parser.add_argument("--manifest-file", default=str(
        REPO / "experiment_results" / "SCR" / "Ours" / "manifest" / "capflow.json"))
    parser.add_argument(
        "--fusion-dataset", default="",
        help="optional SCR fusion manifest/directory; forwarded to suite runners")
    parser.add_argument("--guardian-artifact", default=str(
        REPO.parent / "benchmarks" / "external" / "defenses-enablers"))
    parser.add_argument("--output-root", required=True)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--model", default="deepseek-v4-flash")
    parser.add_argument("--guard-model", default="gpt-5.5-2026-04-24")
    parser.add_argument("--suite", action="append",
                        choices=("capflow", "authblur", "trustlift"))
    parser.add_argument(
        "--baseline", choices=("undefended", "clawguard",
                               "clawguard_approval3", "progent",
                               "taskshield", "dynamic_guardian"),
        help="run only this frozen baseline consumer")
    parser.add_argument(
        "--undefended-only", action="store_true",
        help="run the matched target-model control without a guard",
    )
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--case-timeout", type=int, default=1200)
    args = parser.parse_args()
    suites = args.suite or ["capflow", "authblur", "trustlift"]
    root = Path(args.output_root)
    root.mkdir(parents=True, exist_ok=True)
    scr_root = Path(args.scr_root).resolve()
    jobs: list[tuple[str, str, list[str], Path]] = []
    fusion_cases: dict[str, set[str]] = {}
    if args.fusion_dataset:
        for suite in ("capflow", "authblur", "trustlift"):
            fusion_cases[suite] = set(load_suite(args.fusion_dataset, suite))

    if "capflow" in suites:
        case_ids = sorted(map(int, json.loads(
            Path(args.manifest_file).read_text(encoding="utf-8"))["cases"]))
        if args.fusion_dataset:
            case_ids = [
                case_id for case_id in case_ids
                if str(case_id) in fusion_cases["capflow"]]
        if args.limit:
            case_ids = case_ids[:args.limit]
        capflow_baselines = (("undefended",) if args.undefended_only else
                             ((args.baseline,) if args.baseline else
                              ("clawguard", "progent", "taskshield")))
        capflow_baselines = tuple(
            item for item in capflow_baselines
            if item in {"undefended", "clawguard", "clawguard_approval3",
                        "progent", "taskshield"})
        for baseline in capflow_baselines:
            for case_id in case_ids:
                output = root / "capflow" / baseline / f"case{case_id:03d}.json"
                command = [
                    sys.executable, "-m", "code.benchmarks.scr.execution.baselines",
                    "--baseline", baseline, "--scr-root", str(scr_root),
                    "--manifest-file", str(Path(args.manifest_file).resolve()),
                    "--case", str(case_id), "--condition", "B_only",
                    "--condition", "A+B_neutral", "--model", args.model,
                    "--guard-model", args.guard_model, "--output", str(output),
                ]
                if args.fusion_dataset:
                    command.extend(["--fusion-dataset", args.fusion_dataset])
                jobs.append(("capflow", baseline, command, output))

    if "authblur" in suites:
        case_ids = sorted(load_auth_cases(scr_root))
        if args.fusion_dataset:
            case_ids = [
                case_id for case_id in case_ids
                if str(case_id) in fusion_cases["authblur"]]
        if args.limit:
            case_ids = case_ids[:args.limit]
        authblur_baselines = (("undefended",) if args.undefended_only else
                              ((args.baseline,) if args.baseline else
                               ("taskshield", "dynamic_guardian")))
        authblur_baselines = tuple(
            item for item in authblur_baselines
            if item in {"undefended", "taskshield", "dynamic_guardian"})
        for case_id in case_ids:
            for baseline in authblur_baselines:
                output = root / "authblur" / baseline / f"case{case_id:03d}.json"
                if baseline == "dynamic_guardian":
                    command = [
                        sys.executable, "-m", "code.benchmarks.scr.execution.guardian",
                        "--scr-root", str(scr_root), "--artifact-root",
                        str(Path(args.guardian_artifact).resolve()), "--case",
                        str(case_id), "--model", args.model,
                        "--guardian-model", args.guard_model,
                        "--output", str(output),
                    ]
                else:
                    command = [
                        sys.executable, "-m", "code.benchmarks.scr.execution.clawguard",
                        "--scr-root", str(scr_root), "--suite", "authblur",
                        "--baseline", baseline, "--case", str(case_id),
                        "--model", args.model, "--guard-model", args.guard_model,
                        "--output", str(output),
                    ]
                    if args.fusion_dataset:
                        command.extend(["--fusion-dataset", args.fusion_dataset])
                jobs.append(("authblur", baseline, command, output))

    if "trustlift" in suites:
        names = sorted(path.name for path in
                       (scr_root / "SCR-TrustLift" / "experiment-group").iterdir()
                       if path.is_dir())
        if args.fusion_dataset:
            names = [name for name in names
                     if str(name) in fusion_cases["trustlift"]]
        if args.limit:
            names = names[:args.limit]
        trustlift_baselines = (("undefended",) if args.undefended_only else
                               ((args.baseline,) if args.baseline else
                                ("clawguard", "progent", "taskshield")))
        trustlift_baselines = tuple(
            item for item in trustlift_baselines
            if item in {"undefended", "clawguard", "clawguard_approval3",
                        "progent", "taskshield"})
        for baseline in trustlift_baselines:
            for name in names:
                output = root / "trustlift" / baseline / f"{name}.json"
                command = [
                    sys.executable, "-m", "code.benchmarks.scr.execution.clawguard",
                    "--scr-root", str(scr_root), "--suite", "trustlift",
                    "--baseline", baseline, "--trustlift-case", name,
                    "--model", args.model, "--guard-model", args.guard_model,
                    "--output", str(output),
                ]
                if args.fusion_dataset:
                    command.extend(["--fusion-dataset", args.fusion_dataset])
                jobs.append(("trustlift", baseline, command, output))

    def run(job):
        suite, baseline, command, output = job
        if output.is_file():
            return {"suite": suite, "baseline": baseline,
                    "case": output.stem, "status": "skip"}
        output.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(command, cwd=REPO, check=True, timeout=args.case_timeout)
        return {"suite": suite, "baseline": baseline,
                "case": output.stem, "status": "done"}

    failures = []
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        pending = {pool.submit(run, job): job for job in jobs}
        for future in as_completed(pending):
            try:
                print(json.dumps(future.result()), flush=True)
            except Exception as exc:
                suite, baseline, _command, output = pending[future]
                row = {"suite": suite, "baseline": baseline,
                       "case": output.stem, "error": repr(exc)}
                failures.append(row)
                print(json.dumps(row), flush=True)
    state = {
        "agent_model": args.model, "guard_model": args.guard_model,
        "jobs": len(jobs), "failures": failures,
    }
    (root / "run_state.json").write_text(
        json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(state), flush=True)


if __name__ == "__main__":
    main()
