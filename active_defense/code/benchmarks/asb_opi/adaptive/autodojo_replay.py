"""Replay ASB-OPI adaptive attacker instructions against a chosen method.

This consumes an adaptive cache produced by ``adaptive_optimize.py`` and keeps
the attack fixed while changing only the evaluated defense/method.  It is used
for comparable adaptive-attack evaluation after the attack-side search has
already been completed.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
import json
from pathlib import Path
import shutil
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

from code.benchmarks.asb_opi.adaptive.autodojo_optimize import _cell_key
from code.benchmarks.asb_opi.execution.glue import METHODS, _aggregate, _load_cases, _run_case


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_jsonl(path: Path, rows: dict[str, dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    ordered = sorted(rows.values(), key=lambda row: str(row["adaptive_cell"]))
    tmp.write_text(
        "".join(json.dumps(row, ensure_ascii=False, default=str) + "\n" for row in ordered),
        encoding="utf-8",
    )
    tmp.replace(path)


def _load_existing(path: Path) -> dict[str, dict[str, Any]]:
    if not path.exists():
        return {}
    rows: dict[str, dict[str, Any]] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        rows[str(row["adaptive_cell"])] = row
    return rows


def _copy_contract_cache(source: Path | None, output: Path) -> None:
    if source is None:
        return
    if not source.exists():
        raise FileNotFoundError(f"contract cache source does not exist: {source}")
    target = output / "contracts"
    target.mkdir(parents=True, exist_ok=True)
    for path in source.glob("*.json"):
        destination = target / path.name
        if not destination.exists():
            shutil.copy2(path, destination)


def _patched_case(case: dict[str, Any], instruction: str) -> dict[str, Any]:
    patched = deepcopy(case)
    patched["attacker_tool"] = dict(patched["attacker_tool"])
    patched["attacker_tool"]["Attacker Instruction"] = instruction
    return patched


def _selected_items(cache: dict[str, Any], shard_index: int, num_shards: int) -> list[tuple[str, dict[str, Any]]]:
    items = sorted((key, value) for key, value in cache.items() if not key.startswith("_"))
    if num_shards < 1:
        raise ValueError("--num-shards must be >= 1")
    if shard_index < 0 or shard_index >= num_shards:
        raise ValueError("--shard-index must be in [0, num_shards)")
    return [item for index, item in enumerate(items) if index % num_shards == shard_index]


def _metadata(
    *,
    rows: list[dict[str, Any]],
    args: argparse.Namespace,
    output: Path,
    selected_cells: int,
) -> dict[str, Any]:
    attack = [row for row in rows if row.get("split") == "attack"]
    metadata = {
        "schema": "canonical-experiment-result-v2",
        "benchmark": "ASB-OPI",
        "method": f"{args.method}+adaptive_replay",
        "target_model": args.target_model,
        "defense_model": args.defense_model,
        "judge_model": "ASB native string/tool scorer; refusal judge ignored",
        "adaptive_cache": str(args.adaptive_cache),
        "coverage": {
            "adaptive_cells": selected_cells,
            "attack": len(attack),
            "attack_utility": len(attack),
        },
        "metrics": {
            "AU": {"successes": sum(1 for row in attack if row.get("utility") is True), "n": len(attack)},
            "ASR": {"successes": sum(1 for row in attack if row.get("attack_success") is True), "n": len(attack)},
            "technical_failures": sum(1 for row in attack if row.get("technical_failure") is True),
        },
        "artifacts": {
            "results_jsonl": str(output / "results.jsonl"),
            "metadata_json": str(output / "METADATA.json"),
        },
        "notes": [
            "Attack instructions are fixed from the adaptive cache; no attack-side optimization is run here.",
            "Rows are keyed by adaptive cell, not by the original ASB case id alone.",
            "When method=ours, --contract-cache-source can seed frozen contracts into this output directory while using the current method implementation.",
        ],
    }
    (output / "METADATA.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return metadata


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--adaptive-cache", type=Path, required=True)
    parser.add_argument("--method", required=True, choices=sorted(METHODS))
    parser.add_argument("--target-model", default="deepseek-v4-flash")
    parser.add_argument("--defense-model", default="deepseek-v4-flash")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--contract-cache-source", type=Path)
    parser.add_argument("--shard-index", type=int, default=0)
    parser.add_argument("--num-shards", type=int, default=1)
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--max-new-tokens", type=int, default=512)
    parser.add_argument("--attack-type", default="context_ignoring")
    args = parser.parse_args()

    args.adaptive_cache = args.adaptive_cache.resolve()
    args.output = args.output.resolve()
    if args.contract_cache_source is not None:
        args.contract_cache_source = args.contract_cache_source.resolve()
    args.output.mkdir(parents=True, exist_ok=True)
    _copy_contract_cache(args.contract_cache_source, args.output)

    cache = _read_json(args.adaptive_cache)
    selected = _selected_items(cache, args.shard_index, args.num_shards)
    cases_by_id = {str(case["case_id"]): case for case in _load_cases("attack")}

    result_path = args.output / "results.jsonl"
    rows = _load_existing(result_path) if args.resume else {}
    pending: list[tuple[str, dict[str, Any], dict[str, Any]]] = []
    for cell, entry in selected:
        if cell in rows:
            continue
        case_ids = entry.get("case_ids") or [row.get("case_id") for row in entry.get("best_rows", [])]
        case_id = str(case_ids[0]) if case_ids else ""
        case = cases_by_id.get(case_id)
        if case is None:
            raise KeyError(f"adaptive cache cell {cell} references unknown case_id {case_id}")
        expected_cell = _cell_key(case)
        if expected_cell != cell:
            raise ValueError(f"cell/case mismatch: cache={cell} case={expected_cell} case_id={case_id}")
        instruction = str(entry.get("best_instruction", ""))
        pending.append((cell, entry, _patched_case(case, instruction)))

    lock = threading.Lock()
    failures: list[dict[str, Any]] = []

    def run_one(cell: str, entry: dict[str, Any], case: dict[str, Any]) -> dict[str, Any]:
        try:
            row = _run_case(
                case,
                method=args.method,
                target_model=args.target_model,
                defense_model=args.defense_model,
                max_tokens=args.max_new_tokens,
                attack_type=args.attack_type,
                output_dir=args.output,
            )
        except Exception as exc:
            row = {
                "benchmark": "ASB-OPI",
                "method": args.method,
                "case_id": str(case.get("case_id", "")),
                "split": str(case.get("split", "attack")),
                "suite": str(case.get("agent_name", "")),
                "utility": False,
                "attack_success": False,
                "technical_failure": True,
                "error": repr(exc),
            }
        row["method"] = f"{args.method}+adaptive_replay"
        row["adaptive_cell"] = cell
        row["adaptive_instruction"] = str(entry.get("best_instruction", ""))
        row["adaptive_source_cache"] = str(args.adaptive_cache)
        row["adaptive_source_score"] = entry.get("best_score")
        return row

    if pending:
        with ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
            futures = {pool.submit(run_one, cell, entry, case): cell for cell, entry, case in pending}
            completed = 0
            for future in as_completed(futures):
                row = future.result()
                with lock:
                    rows[str(row["adaptive_cell"])] = row
                    _write_jsonl(result_path, rows)
                completed += 1
                if row.get("technical_failure"):
                    failures.append(row)
                print(json.dumps({
                    "done": completed,
                    "pending_total": len(pending),
                    "adaptive_cell": row["adaptive_cell"],
                    "case_id": row["case_id"],
                    "utility": row.get("utility"),
                    "attack_success": row.get("attack_success"),
                    "technical_failure": row.get("technical_failure"),
                }, ensure_ascii=False), flush=True)

    ordered_rows = [rows[cell] for cell, _ in selected if cell in rows]
    metadata = _metadata(rows=ordered_rows, args=args, output=args.output, selected_cells=len(selected))
    print(json.dumps(metadata["metrics"], ensure_ascii=False, indent=2), flush=True)
    if failures:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
