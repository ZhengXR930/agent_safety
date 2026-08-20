"""Checkpointed paired SkillInject evaluation with one Contract per task pair."""
from __future__ import annotations

import argparse
import copy
import json
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path


REPO = Path(__file__).resolve().parents[4]
BENCH = REPO.parent / "benchmarks" / "skill-inject"
sys.path.insert(0, str(BENCH / "scripts"))

from build_sandbox import build_sandbox  # noqa: E402
from config import SKILL_ROOT  # noqa: E402
from code.benchmarks.skillinject.runtime import SkillInjectRuntime  # noqa: E402
from code.ours.defense.contract import EffectClause, TaskContract  # noqa: E402

FROZEN_CONTRACT_BUNDLE = (
    REPO / "code" / "ours" / "contracts" / "skillinject" / "contracts.json")


def _sandbox(row, task, root: Path, clean: bool) -> Path:
    source = copy.deepcopy(row)
    if clean:
        source["instructions"] = {}
        source["task_scripts"] = {}
        source["root_files"] = []
    manifest = build_sandbox(
        source, task, root, SKILL_ROOT, "SKILL.md",
        skill_layout="codex", sandbox_suffix="run")
    return root / manifest["sandbox_path"]


def _run(command: list[str], timeout: int) -> None:
    subprocess.run(command, cwd=REPO, check=True, timeout=timeout)


def _contract_path(output: Path, stem: str) -> Path:
    return output / "contracts" / f"{stem}.json"


def _write_reviewed_contract(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pending = path.with_suffix(".json.tmp")
    pending.write_text(json.dumps(
        payload, ensure_ascii=False, indent=2), encoding="utf-8")
    pending.replace(path)


def _contract_identity(row: dict, task: dict) -> str:
    """Trusted inputs that determine a Skill task's Contract.

    Injection location and payload are deliberately absent: variants with the
    same request and clean Skill surface must share one Contract.
    """
    return json.dumps({
        "prompt": task["prompt"],
        "skill": task.get("skill"),
        "task_files": task.get("task_files") or {},
        "startup_scripts": row.get("startup_scripts") or [],
    }, sort_keys=True, ensure_ascii=False)


def _inspect_contract(task: str, contract) -> dict:
    """Reject transport/compiler failures before any target Agent executes."""
    if contract.task != task:
        raise ValueError("Contract task does not exactly match trusted task")
    if not contract.clauses:
        raise ValueError("Contract is empty")
    effects = [clause.action for clause in contract.clauses
               if isinstance(clause, EffectClause)]
    return {"clauses": len(contract.clauses), "effects": effects}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", default=str(
        Path(__file__).resolve().parents[1] / "data" / "cases.json"))
    parser.add_argument("--output-root", required=True)
    parser.add_argument("--work-root", required=True)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--injection-limit", type=int, default=0)
    parser.add_argument("--task-limit", type=int, default=0)
    parser.add_argument(
        "--pair", action="append", default=[],
        help="run only an exact idNNN_taskN pair; repeatable")
    parser.add_argument("--model", default="deepseek-v4-flash")
    parser.add_argument("--defense-model", default="gpt-5.5-2026-04-24")
    parser.add_argument("--ablation-mode",
                        choices=("full", "wrap_only", "plant_only"),
                        default="full")
    parser.add_argument("--frozen-contract-bundle",
                        default=str(FROZEN_CONTRACT_BUNDLE))
    parser.add_argument("--frozen-contracts-only", action="store_true",
                        help="fail instead of generating when a frozen Contract is missing")
    parser.add_argument("--judge-model", default="gpt-5.4-2026-03-05")
    parser.add_argument("--max-turns", type=int, default=14)
    parser.add_argument(
        "--case-timeout", type=int, default=900,
        help="wall-clock limit in seconds for one clean or attack condition")
    parser.add_argument("--phase", choices=("preflight", "evaluate", "all"),
                        default="all")
    args = parser.parse_args()
    if args.workers < 1:
        raise ValueError("workers must be positive")
    if args.case_timeout < 1:
        raise ValueError("case timeout must be positive")
    out, work = Path(args.output_root), Path(args.work_root)
    out.mkdir(parents=True, exist_ok=True)
    work.mkdir(parents=True, exist_ok=True)
    rows = json.loads(Path(args.dataset).read_text(encoding="utf-8"))
    if args.injection_limit > 0:
        rows = rows[:args.injection_limit]

    pairs = []
    for row in rows:
        tasks = list(row.get("tasks") or ())
        if args.task_limit > 0:
            tasks = tasks[:args.task_limit]
        pairs.extend((row, index, task) for index, task in enumerate(tasks))
    if args.pair:
        selected = set(args.pair)
        available = {
            f"id{int(row['id']):03d}_task{index}"
            for row, index, _task in pairs
        }
        unknown = selected - available
        if unknown:
            raise ValueError(f"unknown pair(s): {sorted(unknown)}")
        pairs = [
            pair for pair in pairs
            if f"id{int(pair[0]['id']):03d}_task{pair[1]}" in selected
        ]

    contract_groups: dict[str, list[tuple[dict, int, dict]]] = {}
    for pair in pairs:
        contract_groups.setdefault(
            _contract_identity(pair[0], pair[2]), []).append(pair)

    frozen_bundle = {}
    frozen_contracts = {}
    if args.frozen_contract_bundle:
        frozen_path = Path(args.frozen_contract_bundle)
        if frozen_path.is_file():
            frozen_bundle = json.loads(frozen_path.read_text(encoding="utf-8"))
            frozen_contracts = frozen_bundle.get("contracts") or {}
            if not isinstance(frozen_contracts, dict):
                raise ValueError("frozen SkillInject contract bundle is invalid")

    def reviewed_from_frozen(stem: str, task: dict) -> dict | None:
        raw_contract = frozen_contracts.get(stem)
        if not isinstance(raw_contract, dict):
            return None
        contract_payload = (
            raw_contract.get("contract")
            if isinstance(raw_contract.get("contract"), dict)
            else raw_contract)
        contract = TaskContract.from_dict(contract_payload)
        quality = _inspect_contract(task["prompt"], contract)
        return {
            "schema": "skillinject-reviewed-contract-v1",
            "pair": stem,
            "task": task["prompt"],
            "quality": quality,
            "contract": contract.to_dict(),
            "trace": {"source": str(args.frozen_contract_bundle)},
        }

    def preflight_group(group):
        representative = None
        for row, index, task in group:
            stem = f"id{int(row['id']):03d}_task{index}"
            target = _contract_path(out, stem)
            if not target.is_file():
                continue
            reviewed = json.loads(target.read_text(encoding="utf-8"))
            contract = TaskContract.from_dict(reviewed["contract"])
            _inspect_contract(task["prompt"], contract)
            representative = reviewed
            break

        if representative is None:
            row, index, task = group[0]
            stem = f"id{int(row['id']):03d}_task{index}"
            representative = reviewed_from_frozen(stem, task)
            if representative is not None:
                representative = copy.deepcopy(representative)
                representative.pop("pair", None)
            elif args.frozen_contracts_only:
                raise ValueError(stem + " has no frozen Contract")
            else:
                with tempfile.TemporaryDirectory(
                        prefix=stem + "_contract_", dir=work) as raw:
                    sandbox = _sandbox(row, task, Path(raw) / "clean", True)
                    runtime = SkillInjectRuntime(
                        sandbox, args.defense_model, target_model=args.model,
                        ablation_mode=args.ablation_mode)
                    contract = runtime.engine.contract(task["prompt"])
                    quality = _inspect_contract(task["prompt"], contract)
                    representative = {
                        "schema": "skillinject-reviewed-contract-v1",
                        "task": task["prompt"],
                        "quality": quality,
                        "contract": contract.to_dict(),
                        "trace": runtime.engine.contract_trace(task["prompt"]),
                    }

        results = []
        for row, index, task in group:
            stem = f"id{int(row['id']):03d}_task{index}"
            target = _contract_path(out, stem)
            if target.is_file():
                results.append({"pair": stem, "status": "contract-skip"})
                continue
            payload = copy.deepcopy(representative)
            payload["pair"] = stem
            payload["task"] = task["prompt"]
            _write_reviewed_contract(target, payload)
            results.append({"pair": stem, "status": "contract-done",
                            **payload["quality"]})
        return results

    preflight_failures = []
    if args.phase in ("preflight", "all"):
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            pending = {pool.submit(preflight_group, group): group
                       for group in contract_groups.values()}
            for future in as_completed(pending):
                try:
                    for result in future.result():
                        print(json.dumps(result), flush=True)
                except Exception as exc:
                    row, index, _task = pending[future][0]
                    failure = {"id": row.get("id"), "task": index,
                               "phase": "preflight", "error": repr(exc)}
                    preflight_failures.append(failure)
                    print(json.dumps(failure), flush=True)
        if preflight_failures:
            state = {"pairs": len(pairs), "phase": "preflight",
                     "failures": preflight_failures}
            (out / "run_state.json").write_text(
                json.dumps(state, indent=2), encoding="utf-8")
            raise SystemExit(1)
        if args.phase == "preflight":
            state = {"pairs": len(pairs), "phase": "preflight",
                     "contracts": len(list((out / "contracts").glob("*.json"))),
                     "failures": []}
            (out / "run_state.json").write_text(
                json.dumps(state, indent=2), encoding="utf-8")
            print(json.dumps(state), flush=True)
            return

    def run_pair(row, index, task):
        stem = f"id{int(row['id']):03d}_task{index}"
        clean_out, attack_out = out / f"{stem}_clean.json", out / f"{stem}_attack.json"
        if clean_out.is_file() and attack_out.is_file():
            return {"pair": stem, "status": "skip"}
        reviewed_path = _contract_path(out, stem)
        if not reviewed_path.is_file():
            reviewed = reviewed_from_frozen(stem, task)
            if reviewed is None:
                raise ValueError(stem + " has no reviewed Contract")
            _write_reviewed_contract(reviewed_path, reviewed)
        reviewed = json.loads(reviewed_path.read_text(encoding="utf-8"))
        contract = reviewed.get("contract")
        if not isinstance(contract, dict):
            raise ValueError(stem + " reviewed Contract is invalid")
        with tempfile.TemporaryDirectory(prefix=stem + "_", dir=work) as raw:
            root = Path(raw)
            bundle = root / "contract.json"
            bundle.write_text(json.dumps({
                "contracts": {task["prompt"]: contract}}, ensure_ascii=False),
                encoding="utf-8")
            if not clean_out.is_file():
                clean_box = _sandbox(row, task, root / "clean", True)
                _run([
                    sys.executable, "-m",
                    "code.benchmarks.skillinject.execution.ours",
                    "--sandbox", str(clean_box), "--task", task["prompt"],
                    "--condition", "clean", "--model", args.model,
                    "--defense-model", args.defense_model,
                    "--ablation-mode", args.ablation_mode,
                    "--judge-model", args.judge_model,
                    "--max-turns", str(args.max_turns),
                    "--contract-bundle", str(bundle),
                    "--output", str(clean_out),
                ], args.case_timeout)
            if not attack_out.is_file():
                attack_box = _sandbox(row, task, root / "attack", False)
                command = [
                    sys.executable, "-m",
                    "code.benchmarks.skillinject.execution.ours",
                    "--sandbox", str(attack_box), "--task", task["prompt"],
                    "--condition", "attack", "--model", args.model,
                    "--defense-model", args.defense_model,
                    "--ablation-mode", args.ablation_mode,
                    "--judge-model", args.judge_model,
                    "--max-turns", str(args.max_turns),
                    "--contract-bundle", str(bundle),
                    "--attack-judge-prompt", str(row["judge_prompt"]),
                    "--attack-context", json.dumps(
                        row.get("instructions") or {}, ensure_ascii=False),
                    "--output", str(attack_out),
                ]
                for token in (row.get("task_scripts") or {}):
                    command.extend(["--attack-token", str(token)])
                _run(command, args.case_timeout)
        return {"pair": stem, "status": "done"}

    failures = []
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        pending = {pool.submit(run_pair, *pair): pair for pair in pairs}
        for future in as_completed(pending):
            try:
                print(json.dumps(future.result()), flush=True)
            except Exception as exc:
                row, index, _task = pending[future]
                failure = {"id": row.get("id"), "task": index,
                           "error": repr(exc)}
                failures.append(failure)
                print(json.dumps(failure), flush=True)
    state = {"pairs": len(pairs),
             "clean": len(list(out.glob("*_clean.json"))),
             "attack": len(list(out.glob("*_attack.json"))),
             "failures": failures}
    (out / "run_state.json").write_text(
        json.dumps(state, indent=2), encoding="utf-8")
    print(json.dumps(state), flush=True)


if __name__ == "__main__":
    main()
