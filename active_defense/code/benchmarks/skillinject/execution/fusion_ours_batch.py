"""Run materialized SkillJect-fusion SkillInject pairs with frozen Contracts."""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from code.benchmarks.skillinject.execution.batch import REPO
from code.benchmarks.skillinject.execution.skillject_style import (
    _build_base_sandbox,
    _stem,
)


def _run(command: list[str], timeout: int) -> None:
    subprocess.run(command, cwd=REPO, check=True, timeout=timeout)


def _load_rows(dataset: Path) -> dict[int, dict]:
    return {int(row["id"]): row
            for row in json.loads(dataset.read_text(encoding="utf-8"))}


def _load_manifest(path: Path, selected: set[str]) -> list[dict]:
    manifest = json.loads(path.read_text(encoding="utf-8"))
    pairs = list(manifest.get("pairs") or ())
    if selected:
        available = {str(item.get("pair")) for item in pairs}
        missing = selected - available
        if missing:
            raise ValueError(f"manifest missing pair(s): {sorted(missing)}")
        pairs = [item for item in pairs if str(item.get("pair")) in selected]
    return pairs


def _replace_skill(sandbox: Path, manifest_root: Path, entry: dict) -> None:
    skill_files = sorted(sandbox.glob(".codex/skills/*/SKILL.md"))
    if len(skill_files) != 1:
        raise ValueError(
            f"expected one installed skill in {sandbox}, found {len(skill_files)}")
    source_skill = manifest_root / str(entry["skill_md_path"])
    if not source_skill.is_file():
        raise ValueError(f"missing materialized SKILL.md: {source_skill}")
    shutil.copy2(source_skill, skill_files[0])

    resource_path = entry.get("resource_path")
    if resource_path:
        source_resource = manifest_root / str(resource_path)
        if not source_resource.is_file():
            raise ValueError(f"missing materialized resource: {source_resource}")
        target = skill_files[0].parent / "resources" / source_resource.name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_resource, target)
        target.chmod(source_resource.stat().st_mode)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--dataset", default=str(
        Path(__file__).resolve().parents[1] / "data" / "cases.json"))
    parser.add_argument("--contract-root", required=True)
    parser.add_argument("--output-root", required=True)
    parser.add_argument("--work-root", required=True)
    parser.add_argument("--pair", action="append", default=[])
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--model", default="deepseek-v4-flash")
    parser.add_argument("--defense-model", default="gpt-5.5-2026-04-24")
    parser.add_argument("--judge-model", default="gpt-5.4-2026-03-05")
    parser.add_argument("--max-turns", type=int, default=14)
    parser.add_argument("--case-timeout", type=int, default=900)
    args = parser.parse_args()
    if args.workers < 1 or args.case_timeout < 1:
        raise ValueError("workers and case-timeout must be positive")

    manifest_path = Path(args.manifest)
    manifest_root = manifest_path.parent
    selected = set(args.pair)
    entries = _load_manifest(manifest_path, selected)
    rows = _load_rows(Path(args.dataset))
    output = Path(args.output_root)
    work = Path(args.work_root)
    contract_root = Path(args.contract_root)
    output.mkdir(parents=True, exist_ok=True)
    work.mkdir(parents=True, exist_ok=True)

    def run_entry(entry: dict) -> dict:
        pair = str(entry["pair"])
        row = rows[int(entry["row_id"])]
        index = int(entry["task_index"])
        task = list(row.get("tasks") or ())[index]
        if _stem(row, index) != pair:
            raise ValueError(f"pair mismatch for {pair}")
        out = output / f"{pair}_attack.json"
        if out.is_file():
            return {"pair": pair, "status": "skip"}
        contract_bundle = contract_root / f"{pair}_contract_bundle.json"
        if not contract_bundle.is_file():
            raise ValueError(f"missing frozen contract bundle: {contract_bundle}")
        with tempfile.TemporaryDirectory(prefix=f"{pair}_", dir=work) as raw:
            sandbox = _build_base_sandbox(
                row, task, Path(raw), include_scripts=True)
            _replace_skill(sandbox, manifest_root, entry)
            command = [
                sys.executable, "-m", "code.benchmarks.skillinject.execution.ours",
                "--sandbox", str(sandbox),
                "--task", task["prompt"],
                "--condition", "attack",
                "--model", args.model,
                "--defense-model", args.defense_model,
                "--judge-model", args.judge_model,
                "--max-turns", str(args.max_turns),
                "--contract-bundle", str(contract_bundle),
                "--attack-judge-prompt", str(row.get("judge_prompt") or ""),
                "--attack-context", json.dumps(
                    row.get("instructions") or {}, ensure_ascii=False),
                "--output", str(out),
            ]
            for token in (row.get("task_scripts") or {}):
                command.extend(["--attack-token", str(token)])
            _run(command, args.case_timeout)
        return {"pair": pair, "status": "done"}

    failures = []
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        pending = {pool.submit(run_entry, entry): entry for entry in entries}
        for future in as_completed(pending):
            pair = pending[future].get("pair")
            try:
                print(json.dumps(future.result()), flush=True)
            except Exception as exc:  # noqa: BLE001 - record all case failures
                failure = {"pair": pair, "error": repr(exc)}
                failures.append(failure)
                print(json.dumps(failure), flush=True)
    state = {
        "pairs": len(entries),
        "attack": len(list(output.glob("*_attack.json"))),
        "failures": failures,
    }
    (Path(args.output_root).parent / "run_state.json").write_text(
        json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(state, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
