#!/usr/bin/env python3
"""Calibrate compact value-boundary teacher labels with weak benchmark labels."""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


CLEAN = {"broad_clean", "clean_side_effect", "clean_value_flow"}
UNSAFE = {"unsafe_value_flow"}


def expected(rec: dict[str, Any]) -> str | None:
    if rec.get("expected") in {"ALLOW", "BLOCK"}:
        return rec["expected"]
    kind = rec.get("kind")
    if kind in CLEAN:
        return "ALLOW"
    if kind in UNSAFE:
        return "BLOCK"
    return None


def calibrate(rec: dict[str, Any]) -> dict[str, Any]:
    label = dict(rec.get("teacher_label") or {})
    exp = expected(rec)
    decision = label.get("decision")
    action_ok = label.get("task_authorizes_action") == "yes"
    values_ok = label.get("task_authorizes_values") == "yes"
    ext_auth = label.get("external_authority_used") == "yes"
    status = "keep_agree"
    calibrated = dict(label)

    if decision == "PARSE_ERROR" or exp is None:
        status = "drop_parse_or_unknown"
    elif decision == exp:
        status = "keep_agree"
    elif exp == "ALLOW" and decision in {"WARN", "BLOCK"}:
        if action_ok and values_ok and not ext_auth:
            status = "calibrate_clean_to_allow"
            calibrated["decision"] = "ALLOW"
        else:
            status = "calibrate_clean_conflict_to_warn"
            calibrated["decision"] = "WARN"
    elif exp == "BLOCK" and decision == "ALLOW":
        if (not action_ok) or (not values_ok) or ext_auth:
            status = "calibrate_attack_to_block"
            calibrated["decision"] = "BLOCK"
        else:
            status = "calibrate_unsafe_conflict_to_warn"
            calibrated["decision"] = "WARN"
    else:
        status = "drop_other_conflict"

    out = dict(rec)
    out["benchmark_expected_decision"] = exp
    out["calibration_status"] = status
    out["calibrated_label"] = calibrated
    out["use_for_compact_value_training"] = (
        status.startswith("keep_")
        or status.startswith("calibrate_clean")
        or status == "calibrate_unsafe_conflict_to_warn"
        or status == "calibrate_attack_to_block"
    )
    return out


def summarize(records: list[dict[str, Any]]) -> dict[str, Any]:
    by_kind: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for rec in records:
        by_kind[rec.get("kind", "unknown")].append(rec)
    return {
        "n": len(records),
        "usable_for_compact_value_training": sum(r["use_for_compact_value_training"] for r in records),
        "status": dict(Counter(r["calibration_status"] for r in records)),
        "by_kind": {
            kind: {
                "n": len(rows),
                "usable": sum(r["use_for_compact_value_training"] for r in rows),
                "teacher_decision": dict(Counter((r.get("teacher_label") or {}).get("decision") for r in rows)),
                "calibrated_decision": dict(Counter((r.get("calibrated_label") or {}).get("decision") for r in rows)),
                "status": dict(Counter(r["calibration_status"] for r in rows)),
            }
            for kind, rows in by_kind.items()
        },
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input-jsonl", required=True)
    ap.add_argument("--output-dir", required=True)
    args = ap.parse_args()

    records = []
    with Path(args.input_jsonl).open("r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                records.append(calibrate(json.loads(line)))

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    with (out_dir / "teacher_labels_calibrated.jsonl").open("w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    metrics = summarize(records)
    (out_dir / "metrics.json").write_text(json.dumps(metrics, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(metrics, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
