#!/usr/bin/env python3
"""Calibrate pure value-boundary teacher labels.

This keeps the value adapter narrow. A sample is usable only when:

- teacher JSON parses;
- fields and decision are internally consistent;
- teacher decision agrees with the benchmark-derived bucket direction.

Conflicts are preserved for audit instead of being silently converted into
training labels.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


CLEAN_BUCKETS = {"broad_clean", "clean_side_effect", "clean_value_flow"}
UNSAFE_BUCKETS = {"unsafe_value_flow"}
FIELDS = [
    "action_in_user_scope",
    "values_in_user_scope",
    "sensitive_value_from_untrusted_source",
    "decision",
]


def expected_decision(rec: dict[str, Any]) -> str | None:
    if rec.get("expected") in {"ALLOW", "BLOCK"}:
        return rec["expected"]
    kind = rec.get("kind")
    if kind in CLEAN_BUCKETS:
        return "ALLOW"
    if kind in UNSAFE_BUCKETS:
        return "BLOCK"
    return None


def field_consistent(label: dict[str, Any]) -> bool:
    action_ok = label.get("action_in_user_scope") == "yes"
    values_ok = label.get("values_in_user_scope") == "yes"
    sensitive_bad = label.get("sensitive_value_from_untrusted_source") == "yes"
    expected = "ALLOW" if action_ok and values_ok and not sensitive_bad else "BLOCK"
    return label.get("decision") == expected


def status_for(rec: dict[str, Any]) -> tuple[str, bool]:
    label = rec.get("teacher_label") or {}
    exp = expected_decision(rec)
    if label.get("decision") == "PARSE_ERROR":
        return "drop_parse_error", False
    if exp is None:
        return "drop_unknown_expected", False
    missing = [field for field in FIELDS if field not in label]
    if missing:
        return "drop_missing_fields", False
    if not field_consistent(label):
        return "drop_inconsistent_fields", False
    if label.get("decision") != exp:
        return f"drop_teacher_benchmark_conflict_{exp.lower()}_vs_{label.get('decision', 'unknown').lower()}", False
    return "keep_strict_agree", True


def calibrate(rec: dict[str, Any]) -> dict[str, Any]:
    status, usable = status_for(rec)
    out = dict(rec)
    out["benchmark_expected_decision"] = expected_decision(rec)
    out["calibration_status"] = status
    out["calibrated_label"] = rec.get("teacher_label") or {}
    out["use_for_value_pure_training"] = usable
    return out


def summarize(records: list[dict[str, Any]]) -> dict[str, Any]:
    by_kind: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for rec in records:
        by_kind[rec.get("kind", "unknown")].append(rec)
    return {
        "n": len(records),
        "usable_for_value_pure_training": sum(r["use_for_value_pure_training"] for r in records),
        "status": dict(Counter(r["calibration_status"] for r in records)),
        "by_kind": {
            kind: {
                "n": len(rows),
                "usable": sum(r["use_for_value_pure_training"] for r in rows),
                "teacher_decision": dict(Counter((r.get("teacher_label") or {}).get("decision") for r in rows)),
                "expected_decision": dict(Counter(r.get("benchmark_expected_decision") for r in rows)),
                "status": dict(Counter(r["calibration_status"] for r in rows)),
                **{
                    field: dict(Counter((r.get("teacher_label") or {}).get(field, "missing") for r in rows))
                    for field in FIELDS
                },
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
