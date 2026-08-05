"""Checkpointed full SCR suite runner."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path


REPO = Path(__file__).resolve().parents[2]
SCR = REPO.parent / "benchmarks" / "SCR_Bench"
CAPFLOW_MANIFEST = (REPO / "experiment_stage" /
                    "scr_capflow_operator_manifest_v2" / "manifest.json")
sys.path.insert(0, str(REPO))

from code.harness.scr_clawguard import load_auth_cases  # noqa: E402
from code.harness.scr_capflow import (_condition_name, _load_case,
                                      _manifest)  # noqa: E402
from code.harness.scr_authblur import authblur_tools  # noqa: E402
from code.harness.scr_trustlift import SCAN_TASK, TOOLS as TRUSTLIFT_TOOLS  # noqa: E402
from code.benchmarks.scr import SkillRuntime  # noqa: E402
from code.benchmarks.manifest import validate_registrations  # noqa: E402
from code.defense.contract import EffectClause  # noqa: E402
from code.defense.engine import Engine  # noqa: E402


TARGET_MODEL = "deepseek-v4-flash"
DEFENSE_MODEL = "gpt-5.5-2026-04-24"
CAPFLOW_CONDITIONS = (
    "A_only", "B_only", "A+B_neutral", "A+B_explicit")


def _inspect(task, contract):
    if contract.task != task:
        raise ValueError("Contract task does not exactly match trusted task")
    if not contract.clauses:
        raise ValueError("Contract is empty")
    return {"clauses": len(contract.clauses),
            "effects": [clause.action for clause in contract.clauses
                        if isinstance(clause, EffectClause)]}


def _write_contract(path: Path, contracts: dict, quality: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pending = path.with_suffix(path.suffix + ".tmp")
    pending.write_text(json.dumps({
        "schema": "scr-reviewed-contracts-v1",
        "contracts": contracts, "quality": quality,
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    pending.replace(path)


def _jobs(output: Path, capflow_conditions=CAPFLOW_CONDITIONS):
    for case in range(1, 151):
        module, _ = _load_case(SCR, case)
        if all(callable(getattr(module, name, None))
               for name in ("reset_sandbox", "verify_ground_truth")):
            target = output / "capflow" / f"case{case:03d}.json"
            contract = output / "contracts" / "capflow" / f"case{case:03d}.json"
            conditions = [part for condition in capflow_conditions
                          for part in ("--condition", condition)]
            yield "capflow", target, [
                "python3", "code/run_scr.py", "--suite", "capflow",
                "--scr-root", str(SCR), "--manifest-file", str(CAPFLOW_MANIFEST),
                "--case", str(case), *conditions, "--target-model", TARGET_MODEL,
                "--defense-model", DEFENSE_MODEL,
                "--contract-file", str(contract), "--output", str(target)]
    for case, config in sorted(load_auth_cases(SCR).items()):
        skills = (SCR / "SCR-AuthBlur" / "cases" / f"case{case}" /
                  "cli_skills" / "skills")
        required = {config["control_skill"],
                    *(value[0] for value in config["conditions"].values())}
        if all((skills / name / "SKILL.md").is_file() for name in required):
            target = output / "authblur" / f"case{case:03d}.json"
            contract = output / "contracts" / "authblur" / f"case{case:03d}.json"
            yield "authblur", target, [
                "python3", "code/run_scr.py", "--suite", "authblur",
                "--scr-root", str(SCR), "--case", str(case),
                "--model", TARGET_MODEL, "--contract-file", str(contract),
                "--output", str(target)]
    root = SCR / "SCR-TrustLift" / "experiment-group"
    for case in sorted(path.name for path in root.iterdir() if
                       (path / "cli_skills" / "skills" / "secure-skill" /
                        "SKILL.md").is_file()):
        target = output / "trustlift" / f"{case}.json"
        scratch = output / "work" / "trustlift" / case
        yield "trustlift", target, [
            "python3", "code/run_scr.py", "--suite", "trustlift",
            "--scr-root", str(SCR), "--case", "experiment-group/" + case,
            "--scratch", str(scratch), "--model", TARGET_MODEL,
            "--defense-model", DEFENSE_MODEL,
            "--contract-file", str(output / "contracts" / "trustlift.json"),
            "--output", str(target)]


def _preflight_jobs(output: Path, suites: set[str]):
    if "capflow" in suites:
        for case in range(1, 151):
            module, case_dir = _load_case(SCR, case)
            if not all(callable(getattr(module, name, None))
                       for name in ("reset_sandbox", "verify_ground_truth")):
                continue
            target = output / "contracts" / "capflow" / f"case{case:03d}.json"

            def capflow(case=case, module=module, case_dir=case_dir, target=target):
                if target.is_file():
                    return "capflow", "skip", str(target)
                manifest, _frozen = _manifest(CAPFLOW_MANIFEST, case)
                runtime = SkillRuntime(
                    case_dir / "cli_skills" / "skills", DEFENSE_MODEL,
                    manifest, target_model=TARGET_MODEL)
                contracts, quality = {}, {}
                for condition in ("A_only", "B_only", "A+B_neutral",
                                  "A+B_explicit"):
                    name = _condition_name(module, condition)
                    task = module.CONDITIONS[name]["t1_prompt"]
                    contract = runtime.engine.contract(task)
                    contracts[condition] = contract.to_dict()
                    quality[condition] = _inspect(task, contract)
                _write_contract(target, contracts, quality)
                return "capflow", "done", str(target)

            yield capflow
    if "authblur" in suites:
        for case, config in sorted(load_auth_cases(SCR).items()):
            skills = (SCR / "SCR-AuthBlur" / "cases" / f"case{case}" /
                      "cli_skills" / "skills")
            required = {config["control_skill"],
                        *(value[0] for value in config["conditions"].values())}
            if not all((skills / name / "SKILL.md").is_file()
                       for name in required):
                continue
            target = output / "contracts" / "authblur" / f"case{case:03d}.json"

            def authblur(config=config, target=target):
                if target.is_file():
                    return "authblur", "skip", str(target)
                engine = Engine(DEFENSE_MODEL, approval_enabled=False)
                registrations = authblur_tools()
                validate_registrations(registrations, "SCR/AuthBlur")
                engine.perceive(registrations)
                contracts, quality = {}, {}
                for condition in ("level2_findings", "level3_fullauth"):
                    task = config["conditions"][condition][1] + "\nThen, " + config["t2"]
                    contract = engine.contract(task)
                    contracts[condition] = contract.to_dict()
                    quality[condition] = _inspect(task, contract)
                _write_contract(target, contracts, quality)
                return "authblur", "done", str(target)

            yield authblur
    if "trustlift" in suites:
        target = output / "contracts" / "trustlift.json"

        def trustlift():
            if target.is_file():
                return "trustlift", "skip", str(target)
            registrations = [{
                "name": tool["name"], "description": tool["description"],
                "inputSchema": tool["inputSchema"],
                "outputSchema": tool["outputSchema"],
                "effect": tool["effect"], "observation": tool["observation"],
                "effect_return": tool["effect_return"],
            } for tool in TRUSTLIFT_TOOLS]
            validate_registrations(registrations, "SCR/TrustLift")
            engine = Engine(DEFENSE_MODEL, approval_enabled=False)
            engine.perceive(registrations)
            contract = engine.contract(SCAN_TASK)
            quality = _inspect(SCAN_TASK, contract)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(json.dumps(
                contract.to_dict(), ensure_ascii=False, indent=2),
                encoding="utf-8")
            return "trustlift", "done", str(target), quality

        yield trustlift


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-root", required=True)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--suite", action="append",
                        choices=("capflow", "authblur", "trustlift"))
    parser.add_argument("--phase", choices=("preflight", "evaluate", "all"),
                        default="all")
    parser.add_argument("--capflow-condition", action="append",
                        choices=CAPFLOW_CONDITIONS,
                        help="CapFlow conditions to evaluate; repeat as needed")
    args = parser.parse_args()
    output = Path(args.output_root)
    output.mkdir(parents=True, exist_ok=True)
    suites = set(args.suite or ("capflow", "authblur", "trustlift"))
    if args.phase in ("preflight", "all"):
        preflight = list(_preflight_jobs(output, suites))
        failures = []
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            pending = {pool.submit(job): job for job in preflight}
            for future in as_completed(pending):
                try:
                    print(json.dumps(future.result()), flush=True)
                except Exception as exc:
                    failures.append({"phase": "preflight", "error": repr(exc)})
                    print(json.dumps(failures[-1]), flush=True)
        if failures:
            raise SystemExit(1)
        if args.phase == "preflight":
            print(json.dumps({"phase": "preflight",
                              "contracts": len(preflight)}), flush=True)
            return
    capflow_conditions = tuple(
        args.capflow_condition or CAPFLOW_CONDITIONS)
    jobs = [job for job in _jobs(output, capflow_conditions)
            if job[0] in suites]

    def run(job):
        suite, target, command = job
        if target.is_file():
            return suite, "skip", str(target)
        target.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(command, cwd=REPO, check=True)
        return suite, "done", str(target)

    failures = []
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        pending = {pool.submit(run, job): job for job in jobs}
        for future in as_completed(pending):
            try:
                print(json.dumps(future.result()), flush=True)
            except Exception as exc:
                suite, target, _ = pending[future]
                failures.append({"suite": suite, "output": str(target),
                                 "error": repr(exc)})
    state = {"requested": len(jobs),
             "completed": sum(target.is_file() for _, target, _ in jobs),
             "failures": failures}
    (output / "run_state.json").write_text(
        json.dumps(state, indent=2), encoding="utf-8")
    print(json.dumps(state), flush=True)


if __name__ == "__main__":
    main()
