#!/usr/bin/env python3
"""Run PromptGuard 2 / LlamaFirewall-style detector on benchmark_manifest.jsonl."""

from __future__ import annotations

import argparse
import json
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import torch
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score
from transformers import AutoModelForSequenceClassification, AutoTokenizer


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = ROOT / "experiment-stage" / "adaptive_attack_eval" / "benchmark_manifest.jsonl"
DEFAULT_OUT_DIR = ROOT / "experiment-stage" / "adaptive_attack_eval" / "promptguard2_baseline"
DEFAULT_MODEL = "meta-llama/Llama-Prompt-Guard-2-86M"


def load_manifest(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def row_label(row: dict[str, Any]) -> int:
    return 0 if row.get("primary_attack_category") == "clean" else 1


def build_text(row: dict[str, Any], mode: str) -> str:
    fields = row.get("text_fields") or []
    if mode == "attacked_input":
        return row.get("attacked_input") or row.get("clean_input") or ""
    if mode == "untrusted_only":
        texts = [
            str(field.get("text") or "")
            for field in fields
            if field.get("text") and field.get("trust") in {"attacker_controlled", "user_supplied"}
        ]
        return "\n\n".join(texts) or row.get("attacked_input") or row.get("clean_input") or ""
    if mode == "text_fields":
        parts = []
        for field in fields:
            text = field.get("text")
            if text:
                parts.append(f"[{field.get('trust')}::{field.get('name')}]\n{text}")
        return "\n\n".join(parts) or row.get("attacked_input") or row.get("clean_input") or ""
    raise ValueError(f"Unknown input mode: {mode}")


def select_rows(
    rows: list[dict[str, Any]],
    *,
    benchmark: str | None,
    surface: str | None,
    category: str | None,
    limit: int | None,
) -> list[dict[str, Any]]:
    selected = []
    for row in rows:
        if row.get("status") == "placeholder":
            continue
        if "PromptGuard2_LlamaFirewall" not in row.get("compatible_defenses", []):
            continue
        if benchmark and row.get("benchmark") != benchmark:
            continue
        if surface and row.get("surface") != surface:
            continue
        if category and row.get("primary_attack_category") != category:
            continue
        selected.append(row)
        if limit is not None and len(selected) >= limit:
            break
    return selected


def is_attack_label(label: str) -> bool:
    normalized = label.lower()
    benign_markers = ["benign", "safe", "clean", "allowed", "none"]
    return not any(marker in normalized for marker in benign_markers)


def summarize(records: list[dict[str, Any]], model_id: str, input_mode: str, elapsed_s: float) -> dict[str, Any]:
    y_true = [int(r["label"]) for r in records]
    y_pred = [int(r["pred_block"]) for r in records]
    summary: dict[str, Any] = {
        "model_id": model_id,
        "input_mode": input_mode,
        "n": len(records),
        "elapsed_s": elapsed_s,
        "label_counts": dict(Counter(y_true)),
        "pred_counts": dict(Counter(y_pred)),
    }
    if records:
        summary.update(
            {
                "accuracy": accuracy_score(y_true, y_pred),
                "precision_block": precision_score(y_true, y_pred, zero_division=0),
                "recall_block_attack_catch": recall_score(y_true, y_pred, zero_division=0),
                "f1_block": f1_score(y_true, y_pred, zero_division=0),
            }
        )
        clean = [r for r in records if r["label"] == 0]
        attacks = [r for r in records if r["label"] == 1]
        summary["clean_allow"] = (
            sum(1 for r in clean if r["pred_block"] == 0) / len(clean) if clean else None
        )
        summary["clean_false_block"] = (
            sum(1 for r in clean if r["pred_block"] == 1) / len(clean) if clean else None
        )
        summary["attack_catch"] = (
            sum(1 for r in attacks if r["pred_block"] == 1) / len(attacks) if attacks else None
        )

    for group_key in ["benchmark", "surface", "primary_attack_category"]:
        grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for record in records:
            grouped[str(record[group_key])].append(record)
        summary[f"by_{group_key}"] = {}
        for key, group in sorted(grouped.items()):
            gy = [int(r["label"]) for r in group]
            gp = [int(r["pred_block"]) for r in group]
            attacks = [r for r in group if r["label"] == 1]
            clean = [r for r in group if r["label"] == 0]
            summary[f"by_{group_key}"][key] = {
                "n": len(group),
                "label_counts": dict(Counter(gy)),
                "pred_counts": dict(Counter(gp)),
                "accuracy": accuracy_score(gy, gp),
                "attack_catch": (
                    sum(1 for r in attacks if r["pred_block"] == 1) / len(attacks)
                    if attacks
                    else None
                ),
                "clean_allow": (
                    sum(1 for r in clean if r["pred_block"] == 0) / len(clean)
                    if clean
                    else None
                ),
            }
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--benchmark")
    parser.add_argument("--surface")
    parser.add_argument("--category")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--max-length", type=int, default=512)
    parser.add_argument(
        "--attack-label-ids",
        default="1",
        help="Comma-separated class ids treated as detector-positive. PromptGuard 2 uses 0=benign, 1=malicious.",
    )
    parser.add_argument(
        "--input-mode",
        choices=["text_fields", "untrusted_only", "attacked_input"],
        default="text_fields",
    )
    parser.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    args = parser.parse_args()

    rows = select_rows(
        load_manifest(args.manifest),
        benchmark=args.benchmark,
        surface=args.surface,
        category=args.category,
        limit=args.limit,
    )
    args.out_dir.mkdir(parents=True, exist_ok=True)
    config = vars(args).copy()
    config["manifest"] = str(args.manifest)
    config["out_dir"] = str(args.out_dir)
    (args.out_dir / "config.json").write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")

    tokenizer = AutoTokenizer.from_pretrained(args.model)
    model = AutoModelForSequenceClassification.from_pretrained(args.model)
    model.to(args.device)
    model.eval()
    id2label = {int(k): v for k, v in model.config.id2label.items()}
    if all(str(label).startswith("LABEL_") for label in id2label.values()):
        attack_ids = {int(item.strip()) for item in args.attack_label_ids.split(",") if item.strip()}
    else:
        attack_ids = {idx for idx, label in id2label.items() if is_attack_label(label)}

    records: list[dict[str, Any]] = []
    start = time.time()
    for begin in range(0, len(rows), args.batch_size):
        batch = rows[begin : begin + args.batch_size]
        texts = [build_text(row, args.input_mode) for row in batch]
        encoded = tokenizer(
            texts,
            padding=True,
            truncation=True,
            max_length=args.max_length,
            return_tensors="pt",
        )
        encoded = {key: value.to(args.device) for key, value in encoded.items()}
        with torch.inference_mode():
            logits = model(**encoded).logits
            probs = torch.softmax(logits, dim=-1).detach().cpu()
        for row, text, prob in zip(batch, texts, probs):
            pred_id = int(torch.argmax(prob).item())
            pred_label = id2label[pred_id]
            pred_block = int(pred_id in attack_ids)
            records.append(
                {
                    "case_id": row["case_id"],
                    "benchmark": row["benchmark"],
                    "suite": row.get("suite"),
                    "surface": row.get("surface"),
                    "primary_attack_category": row.get("primary_attack_category"),
                    "risk_categories": row.get("risk_categories"),
                    "label": row_label(row),
                    "pred_id": pred_id,
                    "pred_label": pred_label,
                    "pred_block": pred_block,
                    "probs": {id2label[i]: float(prob[i]) for i in range(len(prob))},
                    "text_chars": len(text),
                }
            )
    elapsed = time.time() - start
    summary = summarize(records, args.model, args.input_mode, elapsed)
    summary["id2label"] = id2label
    summary["attack_label_ids"] = sorted(attack_ids)

    with (args.out_dir / "records.jsonl").open("w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
    (args.out_dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
