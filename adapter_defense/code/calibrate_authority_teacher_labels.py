#!/usr/bin/env python3
"""Calibrate authority teacher labels.

Primary training keeps only teacher/benchmark agreement. Conflicts are retained
in the calibrated file for audit, but not used by default.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


def calibrate(rec: dict[str, Any]) -> dict[str, Any]:
    label = dict(rec.get("teacher_label") or {})
    expected = rec.get("expected")
    decision = label.get("decision")
    if decision == "PARSE_ERROR" or expected not in {"ALLOW", "BLOCK"}:
        status = "drop_parse_or_unknown"
        use = False
    elif decision == expected:
        status = "keep_agree"
        use = True
    elif expected == "ALLOW" and decision == "BLOCK":
        status = "drop_clean_conflict"
        use = False
    elif expected == "BLOCK" and decision == "ALLOW":
        status = "drop_unsafe_conflict"
        use = False
    else:
        status = "drop_other"
        use = False
    out = dict(rec)
    out["benchmark_expected_decision"] = expected
    out["calibration_status"] = status
    out["calibrated_label"] = label
    out["use_for_authority_training"] = use
    return out


def summarize(records: list[dict[str, Any]]) -> dict[str, Any]:
    by_kind: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for rec in records:
        by_kind[rec.get("kind", "unknown")].append(rec)
    return {
        "n": len(records),
        "usable_for_authority_training": sum(r["use_for_authority_training"] for r in records),
        "status": dict(Counter(r["calibration_status"] for r in records)),
        "by_kind": {
            kind: {
                "n": len(rows),
                "usable": sum(r["use_for_authority_training"] for r in rows),
                "teacher_decision": dict(Counter((r.get("teacher_label") or {}).get("decision") for r in rows)),
                "expected": dict(Counter(r.get("expected") for r in rows)),
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
