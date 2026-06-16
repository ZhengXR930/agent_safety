#!/usr/bin/env python3
"""Defense runner adapter over benchmark_manifest.jsonl.

This file is the stable data-layer adapter. Concrete defense implementations
plug in behind the adapter without changing benchmark ingestion.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = ROOT / "experiment-stage" / "adaptive_attack_eval" / "benchmark_manifest.jsonl"


def load_manifest(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def iter_selected(
    rows: Iterable[dict[str, Any]],
    *,
    benchmark: str | None,
    defense: str,
    limit: int | None,
) -> Iterable[dict[str, Any]]:
    n = 0
    for row in rows:
        if row.get("status") == "placeholder":
            continue
        if benchmark and row.get("benchmark") != benchmark:
            continue
        if defense not in row.get("compatible_defenses", []):
            continue
        yield row
        n += 1
        if limit is not None and n >= limit:
            break


def to_defense_input(row: dict[str, Any], defense: str) -> dict[str, Any]:
    """Normalize one manifest row into the input expected by a defense family."""
    text_payload = "\n\n".join(
        f"[{field.get('trust')}::{field.get('name')}]\n{field.get('text', '')}"
        for field in row.get("text_fields", [])
        if field.get("text")
    )
    step = row.get("step_candidate") or {}
    provenance = row.get("provenance") or {}
    target = row.get("target") or {}

    if defense == "TS-Guard":
        return {
            "case_id": row["case_id"],
            "defense": defense,
            "mode": "step_guard",
            "instruction": row.get("clean_input") or row.get("attacked_input") or text_payload,
            "history_or_context": text_payload,
            "tool_name": step.get("tool_name") or target.get("tool_name"),
            "tool_args": step.get("tool_args") or {},
            "thought": step.get("thought") or row.get("attacked_input") or "",
            "surface": row.get("surface"),
            "risk_categories": row.get("risk_categories"),
        }
    if defense in {"PromptGuard2_LlamaFirewall", "DataFilter"}:
        return {
            "case_id": row["case_id"],
            "defense": defense,
            "mode": "text_guard" if defense.startswith("PromptGuard") else "purification",
            "text": text_payload,
            "fields": row.get("text_fields", []),
            "surface": row.get("surface"),
            "risk_categories": row.get("risk_categories"),
        }
    if defense == "FIDES_deferred":
        return {
            "case_id": row["case_id"],
            "defense": defense,
            "mode": "source_sink_provenance",
            "source": {
                "type": provenance.get("source_type"),
                "trust": provenance.get("source_trust"),
                "fields": row.get("controlled_fields", []),
            },
            "sink": {
                "type": provenance.get("sink_type"),
                "target": provenance.get("target_sink"),
                "tool_name": step.get("tool_name") or target.get("tool_name"),
                "tool_args": step.get("tool_args") or {},
            },
            "value_flow": provenance.get("value_flow"),
            "surface": row.get("surface"),
            "risk_categories": row.get("risk_categories"),
        }
    raise ValueError(f"Unsupported defense adapter: {defense}")


def run_dry(row: dict[str, Any], defense: str) -> dict[str, Any]:
    payload = to_defense_input(row, defense)
    return {
        "case_id": row["case_id"],
        "benchmark": row["benchmark"],
        "defense": defense,
        "adapter_status": "ok",
        "payload": payload,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--defense", required=True, choices=["TS-Guard", "PromptGuard2_LlamaFirewall", "DataFilter", "FIDES_deferred"])
    parser.add_argument("--benchmark")
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--out", type=Path, default=ROOT / "experiment-stage" / "adaptive_attack_eval" / "defense_adapter_dryrun.jsonl")
    args = parser.parse_args()

    rows = load_manifest(args.manifest)
    selected = list(iter_selected(rows, benchmark=args.benchmark, defense=args.defense, limit=args.limit))
    if not args.out.is_absolute():
        args.out = ROOT / args.out
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8") as f:
        for row in selected:
            f.write(json.dumps(run_dry(row, args.defense), ensure_ascii=False, sort_keys=True) + "\n")
    print(json.dumps({"defense": args.defense, "selected": len(selected), "out": str(args.out.relative_to(ROOT))}, indent=2))


if __name__ == "__main__":
    main()
