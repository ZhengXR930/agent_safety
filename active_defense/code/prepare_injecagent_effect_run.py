"""Compile deterministic runner inputs for the full effect-derived corpus."""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def _write(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pending = path.with_suffix(path.suffix + ".tmp")
    pending.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    pending.replace(path)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    if manifest.get("schema") != "injecagent-effect-derived-full-v1":
        raise ValueError("unsupported manifest")

    official = {
        family: json.loads(
            (args.data_dir / f"test_cases_{family}_enhanced.json").read_text(
                encoding="utf-8"))
        for family in ("dh", "ds")
    }
    tasks = {}
    clean = {}
    runtime_tools = {}
    case_to_cell = {}
    for cell in manifest["cells"]:
        case_id = f"{cell['family']}-{int(cell['base_index']):04d}"
        if case_id in case_to_cell:
            raise ValueError(f"duplicate base case {case_id}")
        row = official[cell["family"]][int(cell["base_index"])]
        if row["Attacker Instruction"] != cell["original_attacker_instruction"]:
            raise ValueError(f"attacker mismatch for {case_id}")
        if "<Attacker Instruction>" in str(row["Tool Response"]):
            raise ValueError(f"official payload not materialized for {case_id}")
        tasks[case_id] = cell["trusted_task"]
        clean[case_id] = cell["benign_core"]
        runtime_tools[case_id] = cell["runtime_tools"]
        case_to_cell[case_id] = cell["id"]

    augmentations = {
        tool: [{
            "name": "authorization_scope",
            "type": "string",
            "required": True,
            "description": (
                "Benchmark-owned explicit scope distinguishing an authorized "
                "invocation from an untrusted request."
            ),
        }]
        for tool in manifest["conversion"]["augmentation"]
    }
    if len(tasks) != 1054:
        raise ValueError(f"expected 1054 cases, got {len(tasks)}")
    _write(args.output_dir / "user_tasks.json", tasks)
    _write(args.output_dir / "clean_injections.json", clean)
    _write(args.output_dir / "runtime_tools.json", runtime_tools)
    _write(args.output_dir / "case_to_cell.json", case_to_cell)
    _write(args.output_dir / "tool_schema_augmentations.json", augmentations)
    print(json.dumps({
        "cases": len(tasks),
        "dh": sum(case.startswith("dh-") for case in tasks),
        "ds": sum(case.startswith("ds-") for case in tasks),
        "schema_augmented_tools": len(augmentations),
    }))


if __name__ == "__main__":
    main()
