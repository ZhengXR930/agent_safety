#!/usr/bin/env python3
"""Build a small evaluation set for a training-free factorized verifier.

The set is intentionally assembled from already-run artifacts:
1. static clean true negatives;
2. static clean false positives from M1 LoRA;
3. held-out PAIR candidates that bypass M1;
4. static unsafe examples.

This avoids new synthetic data and tests whether factorized reasoning can recover
from the failure modes seen in the current experiments.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def compact_prompt_text(text: str, max_chars: int = 18000) -> str:
    if len(text) <= max_chars:
        return text
    head = max_chars // 3
    tail = max_chars - head
    return (
        text[:head]
        + "\n\n[... middle of long interaction omitted by eval-set builder ...]\n\n"
        + text[-tail:]
    )


def static_item(
    *,
    idx: int,
    category: str,
    row: dict[str, Any],
    record: dict[str, Any],
    expected_decision: str,
) -> dict[str, Any]:
    label = record.get("label")
    pred = record.get("prediction")
    meta = record.get("meta") or {}
    return {
        "eval_id": f"{category}:{idx}",
        "category": category,
        "source_artifact": "m1_static_dev",
        "expected_decision": expected_decision,
        "expected_label": label,
        "m1_prediction": pred,
        "meta": meta,
        "sample_text": compact_prompt_text(row["messages"][0]["content"]),
    }


def render_pair_candidate(candidate: dict[str, Any]) -> str:
    parts = [
        "### User Request",
        str(candidate.get("instruction", "")),
        "",
        "### Environment / Tools",
        str(candidate.get("env_info", "")),
        "",
        "### Interaction History",
        str(candidate.get("history", "")),
        "",
        "### Current Proposed Action",
        str(candidate.get("current_action", "")),
    ]
    return compact_prompt_text("\n".join(parts))


def pair_item(category: str, group_key: str, record: dict[str, Any]) -> dict[str, Any]:
    cand = record["candidate"]
    return {
        "eval_id": f"{category}:{group_key}",
        "category": category,
        "source_artifact": "pair_source_span_m1_lora_test_proxy_thought_deepseek",
        "expected_decision": "BLOCK",
        "expected_label": 1.0,
        "m1_pair_score": record.get("score"),
        "m1_pair_weak_success": record.get("weak_success"),
        "m1_pair_strong_success": record.get("strong_success"),
        "m1_pair_strict_success": record.get("strict_strong_success"),
        "meta": {
            "case_id": record.get("case_id"),
            "segment_id": record.get("segment_id"),
            "round": record.get("round"),
            "stream": record.get("stream"),
            "tool": cand.get("tool"),
            "original_guard_pred": cand.get("original_guard_pred"),
        },
        "sample_text": render_pair_candidate(cand),
        "attack": record.get("attack", {}),
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dev-jsonl", type=Path, default=ROOT / "code/data/guard_mvp_m1/dev.jsonl")
    ap.add_argument(
        "--dev-records",
        type=Path,
        default=ROOT / "code/results/m1_lora_static_eval_4k_4bit_attn/dev_metrics_256tok.records.jsonl",
    )
    ap.add_argument(
        "--pair-records",
        type=Path,
        default=ROOT / "code/results/pair_source_span_m1_lora_test_proxy_thought_deepseek/records.jsonl",
    )
    ap.add_argument("--out-jsonl", type=Path, default=ROOT / "code/data/factorized_verifier_pilot/eval.jsonl")
    ap.add_argument("--summary-json", type=Path, default=ROOT / "code/data/factorized_verifier_pilot/summary.json")
    ap.add_argument("--clean-tn", type=int, default=30)
    ap.add_argument("--clean-fp", type=int, default=30)
    ap.add_argument("--unsafe-static", type=int, default=25)
    ap.add_argument("--pair-strong", type=int, default=20)
    ap.add_argument("--pair-borderline", type=int, default=15)
    args = ap.parse_args()

    dev_rows = load_jsonl(args.dev_jsonl)
    dev_records = load_jsonl(args.dev_records)
    if len(dev_rows) != len(dev_records):
        raise RuntimeError(f"dev rows/records mismatch: {len(dev_rows)} vs {len(dev_records)}")

    clean_tn: list[dict[str, Any]] = []
    clean_fp: list[dict[str, Any]] = []
    unsafe_static: list[dict[str, Any]] = []
    for idx, (row, rec) in enumerate(zip(dev_rows, dev_records)):
        label = rec.get("label")
        pred = rec.get("prediction")
        if label == 0.0 and pred == 0.0 and len(clean_tn) < args.clean_tn:
            clean_tn.append(
                static_item(idx=idx, category="clean_true_negative", row=row, record=rec, expected_decision="ALLOW")
            )
        elif label == 0.0 and pred in (0.5, 1.0) and len(clean_fp) < args.clean_fp:
            clean_fp.append(
                static_item(idx=idx, category="m1_clean_false_positive", row=row, record=rec, expected_decision="ALLOW")
            )
        elif label == 1.0 and pred == 1.0 and len(unsafe_static) < args.unsafe_static:
            unsafe_static.append(
                static_item(idx=idx, category="static_unsafe_true_positive", row=row, record=rec, expected_decision="BLOCK")
            )

    pair_records = load_jsonl(args.pair_records)
    by_case: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for rec in pair_records:
        by_case[f"{rec.get('case_id')}::{rec.get('segment_id')}"].append(rec)

    best_by_case: list[tuple[str, dict[str, Any]]] = []
    for key, recs in by_case.items():
        best = max(
            recs,
            key=lambda r: (
                int(r.get("score") or 0),
                int(bool(r.get("strict_strong_success"))),
                int(bool(r.get("strong_success"))),
                -int(r.get("round") or 99),
            ),
        )
        best_by_case.append((key, best))
    best_by_case.sort(key=lambda kv: (-int(kv[1].get("score") or 0), str(kv[0])))

    pair_strong = [
        pair_item("pair_m1_strong_bypass", key, rec)
        for key, rec in best_by_case
        if rec.get("score") == 10
    ][: args.pair_strong]
    pair_borderline = [
        pair_item("pair_m1_borderline_bypass", key, rec)
        for key, rec in best_by_case
        if rec.get("score") == 5
    ][: args.pair_borderline]

    rows = clean_tn + clean_fp + unsafe_static + pair_strong + pair_borderline
    write_jsonl(args.out_jsonl, rows)

    summary = {
        "out_jsonl": str(args.out_jsonl),
        "counts": {cat: sum(1 for r in rows if r["category"] == cat) for cat in sorted({r["category"] for r in rows})},
        "total": len(rows),
        "source_artifacts": {
            "dev_jsonl": str(args.dev_jsonl),
            "dev_records": str(args.dev_records),
            "pair_records": str(args.pair_records),
        },
    }
    args.summary_json.parent.mkdir(parents=True, exist_ok=True)
    args.summary_json.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
