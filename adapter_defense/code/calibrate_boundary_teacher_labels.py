#!/usr/bin/env python3
"""Calibrate boundary teacher labels with benchmark weak labels.

The benchmark label is a weak prior for the final decision, not ground truth for
the boundary factors. This script preserves teacher factor labels and only
produces a calibrated training decision plus an audit status.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


ATTACK_BUCKETS = {"unsafe_value_flow", "unsafe_authority_flow"}
CLEAN_BUCKETS = {"broad_clean", "clean_side_effect", "clean_value_flow"}


def expected_from_record(rec: dict[str, Any]) -> str | None:
    expected = rec.get("expected")
    if expected in {"ALLOW", "BLOCK"}:
        return expected
    kind = rec.get("kind")
    if kind in CLEAN_BUCKETS:
        return "ALLOW"
    if kind in ATTACK_BUCKETS:
        return "BLOCK"
    return None


def calibrate(rec: dict[str, Any]) -> dict[str, Any]:
    label = dict(rec.get("teacher_label") or {})
    expected = expected_from_record(rec)
    decision = label.get("decision")
    task = label.get("task_support")
    auth = label.get("source_authority_dependence")
    value = label.get("untrusted_value_flow")

    status = "keep_agree"
    calibrated = dict(label)

    if decision == "PARSE_ERROR" or expected is None:
        status = "drop_parse_or_unknown"
        calibrated["decision"] = decision
    elif decision == expected:
        status = "keep_agree"
        calibrated["decision"] = decision
    elif expected == "ALLOW" and decision in {"WARN", "BLOCK"}:
        if task == "high" and auth == "low" and value == "low":
            # Teacher objected for a tool-choice/format reason, but the compact
            # boundary factors are clean and the benchmark marks it benign.
            status = "calibrate_clean_to_allow"
            calibrated["decision"] = "ALLOW"
        else:
            # Do not force potentially noisy benchmark clean labels over a real
            # boundary violation.
            status = "drop_clean_conflict"
            calibrated["decision"] = decision
    elif expected == "BLOCK" and decision == "ALLOW":
        if auth == "high" or value == "high" or task == "low":
            status = "calibrate_attack_to_block"
            calibrated["decision"] = "BLOCK"
        else:
            # The example is unsafe under the source benchmark, but not under
            # this boundary schema. Keep it out of M2 boundary training.
            status = "drop_out_of_scope_attack"
            calibrated["decision"] = decision
    else:
        status = "drop_other_conflict"

    rec = dict(rec)
    rec["benchmark_expected_decision"] = expected
    rec["calibration_status"] = status
    rec["calibrated_label"] = calibrated
    rec["use_for_boundary_training"] = status.startswith("keep_") or status.startswith("calibrate_")
    return rec


def summarize(records: list[dict[str, Any]]) -> dict[str, Any]:
    by_kind: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for rec in records:
        by_kind[rec.get("kind", "unknown")].append(rec)

    out: dict[str, Any] = {
        "n": len(records),
        "usable_for_boundary_training": sum(1 for r in records if r["use_for_boundary_training"]),
        "calibration_status": dict(Counter(r["calibration_status"] for r in records)),
        "by_kind": {},
    }
    for kind, rows in by_kind.items():
        out["by_kind"][kind] = {
            "n": len(rows),
            "usable": sum(1 for r in rows if r["use_for_boundary_training"]),
            "teacher_decision": dict(Counter((r.get("teacher_label") or {}).get("decision") for r in rows)),
            "calibrated_decision": dict(Counter((r.get("calibrated_label") or {}).get("decision") for r in rows)),
            "status": dict(Counter(r["calibration_status"] for r in rows)),
        }
    return out


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-jsonl", required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()

    in_path = Path(args.input_jsonl)
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    records = []
    with in_path.open("r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            records.append(calibrate(json.loads(line)))

    with (out_dir / "teacher_labels_calibrated.jsonl").open("w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    metrics = summarize(records)
    (out_dir / "metrics.json").write_text(json.dumps(metrics, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(metrics, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
