"""Checkpointed full SCR suite runner."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path


REPO = Path(__file__).resolve().parents[4]
SCR = REPO.parent / "benchmarks" / "SCR_Bench"
CAPFLOW_MANIFEST = Path(__file__).resolve().parents[1] / "data" / "capflow.json"
sys.path.insert(0, str(REPO))

from code.benchmarks.scr.execution.capflow import (_condition_name, _load_case,
                                      _manifest, _supports_case)  # noqa: E402
from code.benchmarks.scr.execution.fusion_overlay import load_suite  # noqa: E402
from code.benchmarks.scr.execution.trustlift import SCAN_TASK, TOOLS as TRUSTLIFT_TOOLS  # noqa: E402
from code.benchmarks.scr.runtime import SkillRuntime  # noqa: E402
from code.core.manifest import validate_registrations  # noqa: E402
from code.ours.manifests.scr import authblur_tools  # noqa: E402
from code.ours.defense.contract import EffectClause  # noqa: E402
from code.ours.defense.engine import Engine  # noqa: E402


TARGET_MODEL = "deepseek-v4-flash"
DEFENSE_MODEL = "gpt-5.5-2026-04-24"
FROZEN_CONTRACT_ROOT = REPO / "code" / "ours" / "contracts" / "scr"
CAPFLOW_CONDITIONS = (
    "A_only", "B_only", "A+B_neutral", "A+B_explicit")


def load_auth_cases(scr_root: Path, case_ids=None):
    from code.benchmarks.scr.execution.clawguard import load_auth_cases as load
    return load(scr_root, case_ids)


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


def _jobs(output: Path, capflow_conditions=CAPFLOW_CONDITIONS,
          capflow_cases=None, *, target_model=TARGET_MODEL,
          defense_model=DEFENSE_MODEL, fusion_dataset="",
          ablation_mode="full", contract_root: Path | None = None):
    fusion_cases: dict[str, set[str]] = {}
    if fusion_dataset:
        for suite in ("capflow", "authblur", "trustlift"):
            fusion_cases[suite] = set(load_suite(fusion_dataset, suite))
    selected_cases = set(capflow_cases or range(1, 151))
    for case in range(1, 151):
        if case not in selected_cases:
            continue
        if fusion_dataset and str(case) not in fusion_cases["capflow"]:
            continue
        module, _ = _load_case(SCR, case)
        if _supports_case(module):
            target = output / "capflow" / f"case{case:03d}.json"
            contract = ((contract_root or output / "contracts") /
                        "capflow" / f"case{case:03d}.json")
            conditions = [part for condition in capflow_conditions
                          for part in ("--condition", condition)]
            command = [
                sys.executable, "-m", "code.benchmarks.scr.execution.capflow",
                "--scr-root", str(SCR), "--manifest-file", str(CAPFLOW_MANIFEST),
                "--case", str(case), *conditions, "--target-model", target_model,
                "--defense-model", defense_model,
                "--ablation-mode", ablation_mode,
                "--contract-file", str(contract), "--output", str(target)]
            if fusion_dataset:
                command.extend(["--fusion-dataset", fusion_dataset])
            yield "capflow", target, command
    for case, config in sorted(load_auth_cases(SCR).items()):
        if fusion_dataset and str(case) not in fusion_cases["authblur"]:
            continue
        skills = (SCR / "SCR-AuthBlur" / "cases" / f"case{case}" /
                  "cli_skills" / "skills")
        required = {config["control_skill"],
                    *(value[0] for value in config["conditions"].values())}
        if all((skills / name / "SKILL.md").is_file() for name in required):
            target = output / "authblur" / f"case{case:03d}.json"
            contract = ((contract_root or output / "contracts") /
                        "authblur" / f"case{case:03d}.json")
            command = [
                sys.executable, "-m", "code.benchmarks.scr.execution.authblur",
                "--scr-root", str(SCR), "--case", str(case),
                "--model", target_model, "--defense-model", defense_model,
                "--ablation-mode", ablation_mode,
                "--contract-file", str(contract),
                "--output", str(target)]
            if fusion_dataset:
                command.extend(["--fusion-dataset", fusion_dataset])
            yield "authblur", target, command
    root = SCR / "SCR-TrustLift" / "experiment-group"
    for case in sorted(path.name for path in root.iterdir() if
                       (path / "cli_skills" / "skills" / "secure-skill" /
                        "SKILL.md").is_file()):
        if fusion_dataset and str(case) not in fusion_cases["trustlift"]:
            continue
        for condition, case_arg, extra in (
                ("clean", str(Path("experiment-group") / case), ["--clean-scan-only"]),
                ("attack", case, [])):
            target = output / "trustlift" / f"{case}_{condition}.json"
            scratch = output / "work" / "trustlift" / condition / case
            command = [
                sys.executable, "-m", "code.benchmarks.scr.execution.trustlift",
                "--scr-root", str(SCR), "--case", case_arg,
                "--condition", "control" if condition == "clean" else "attack",
                "--scratch", str(scratch), "--model", target_model,
                "--defense-model", defense_model,
                "--ablation-mode", ablation_mode,
                "--contract-file", str((contract_root or output / "contracts") /
                                       "trustlift.json"),
                "--output", str(target), *extra]
            if fusion_dataset:
                command.extend(["--fusion-dataset", fusion_dataset])
            yield "trustlift", target, command


def _preflight_jobs(output: Path, suites: set[str],
                    capflow_conditions=CAPFLOW_CONDITIONS,
                    capflow_cases=None, *, target_model=TARGET_MODEL,
                    defense_model=DEFENSE_MODEL):
    if "capflow" in suites:
        selected_cases = set(capflow_cases or range(1, 151))
        for case in range(1, 151):
            if case not in selected_cases:
                continue
            module, case_dir = _load_case(SCR, case)
            if not _supports_case(module):
                continue
            target = output / "contracts" / "capflow" / f"case{case:03d}.json"

            def capflow(case=case, module=module, case_dir=case_dir, target=target):
                if target.is_file():
                    return "capflow", "skip", str(target)
                manifest, _frozen = _manifest(CAPFLOW_MANIFEST, case)
                contracts, quality = {}, {}
                for condition in capflow_conditions:
                    name = _condition_name(module, condition)
                    task = module.CONDITIONS[name]["t1_prompt"]
                    runtime = SkillRuntime(
                        case_dir / "cli_skills" / "skills", defense_model,
                        manifest, target_model=target_model,
                        active_skills=module.CONDITIONS[name]["skills"],
                        workspace_root=case_dir)
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
                    existing = json.loads(target.read_text(encoding="utf-8"))
                    bundles = existing.get("contracts") or {}
                    valid = True
                    for condition in ("level2_findings", "level3_fullauth"):
                        t1 = config["conditions"][condition][1]
                        full = t1 + "\nThen, " + config["t2"]
                        bundle = bundles.get(condition) or {}
                        valid = valid and (
                            (bundle.get("t1") or {}).get("task") == t1 and
                            (bundle.get("full") or {}).get("task") == full)
                    if valid:
                        return "authblur", "skip", str(target)
                engine = Engine(defense_model, approval_enabled=False)
                registrations = authblur_tools()
                validate_registrations(registrations, "SCR/AuthBlur")
                engine.perceive(registrations)
                contracts, quality = {}, {}
                for condition in ("level2_findings", "level3_fullauth"):
                    t1 = config["conditions"][condition][1]
                    full = t1 + "\nThen, " + config["t2"]
                    t1_contract = engine.contract(t1)
                    full_contract = engine.contract(full)
                    contracts[condition] = {
                        "t1": t1_contract.to_dict(),
                        "full": full_contract.to_dict(),
                    }
                    quality[condition] = {
                        "t1": _inspect(t1, t1_contract),
                        "full": _inspect(full, full_contract),
                    }
                _write_contract(target, contracts, quality)
                return "authblur", "done", str(target)

            yield authblur
    if "trustlift" in suites:
        target = output / "contracts" / "trustlift.json"

        def trustlift():
            if target.is_file():
                existing = json.loads(target.read_text(encoding="utf-8"))
                if existing.get("task") == SCAN_TASK:
                    return "trustlift", "skip", str(target)
            registrations = [{
                "name": tool["name"], "description": tool["description"],
                "inputSchema": tool["inputSchema"],
                "outputSchema": tool["outputSchema"],
                "effect": tool["effect"], "observation": tool["observation"],
                "effect_return": tool["effect_return"],
            } for tool in TRUSTLIFT_TOOLS]
            validate_registrations(registrations, "SCR/TrustLift")
            engine = Engine(defense_model, approval_enabled=False)
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
    parser.add_argument("--target-model", default=TARGET_MODEL)
    parser.add_argument("--defense-model", default=DEFENSE_MODEL)
    parser.add_argument("--ablation-mode",
                        choices=("full", "wrap_only", "plant_only"),
                        default="full")
    parser.add_argument("--frozen-contract-root", default="")
    parser.add_argument("--suite", action="append",
                        choices=("capflow", "authblur", "trustlift"))
    parser.add_argument("--phase", choices=("preflight", "evaluate", "all"),
                        default="all")
    parser.add_argument("--capflow-condition", action="append",
                        choices=CAPFLOW_CONDITIONS,
                        help="CapFlow conditions to evaluate; repeat as needed")
    parser.add_argument("--capflow-case", action="append", type=int,
                        help="CapFlow case id to generate/evaluate; repeat as needed")
    parser.add_argument(
        "--fusion-dataset", default="",
        help="optional SCR fusion manifest/directory; forwarded to suite runners")
    args = parser.parse_args()
    output = Path(args.output_root)
    contract_root = (Path(args.frozen_contract_root).resolve()
                     if args.frozen_contract_root else None)
    output.mkdir(parents=True, exist_ok=True)
    suites = set(args.suite or ("capflow", "authblur", "trustlift"))
    capflow_conditions = tuple(
        args.capflow_condition or CAPFLOW_CONDITIONS)
    if args.phase in ("preflight", "all"):
        preflight = list(_preflight_jobs(
            output, suites, capflow_conditions, args.capflow_case,
            target_model=args.target_model,
            defense_model=args.defense_model))
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
    jobs = [job for job in _jobs(
                output, capflow_conditions, args.capflow_case,
                target_model=args.target_model,
                defense_model=args.defense_model,
                fusion_dataset=args.fusion_dataset,
                ablation_mode=args.ablation_mode,
                contract_root=contract_root)
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
