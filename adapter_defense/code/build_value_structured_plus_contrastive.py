#!/usr/bin/env python3
"""Combine structured pointwise value SFT data with contrastive value pairs."""

from __future__ import annotations

import argparse
import json
import random
import shutil
from collections import Counter
from pathlib import Path
from typing import Any


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "n": len(rows),
        "capability": dict(Counter(row.get("capability", "pointwise") for row in rows)),
        "kind": dict(Counter(row.get("kind", "pair") for row in rows)),
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pointwise-dir", required=True)
    ap.add_argument("--contrastive-dir", required=True)
    ap.add_argument("--output-dir", required=True)
    ap.add_argument("--contrastive-repeat", type=int, default=1)
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    rng = random.Random(args.seed)
    pointwise_dir = Path(args.pointwise_dir)
    contrastive_dir = Path(args.contrastive_dir)
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    train = read_jsonl(pointwise_dir / "train.jsonl")
    contrastive = read_jsonl(contrastive_dir / "train.jsonl") * max(0, args.contrastive_repeat)
    combined = train + contrastive
    rng.shuffle(combined)
    write_jsonl(out_dir / "train.jsonl", combined)

    # Keep dev/test pointwise so generation metrics remain directly comparable
    # to the structured-only adapter.
    shutil.copyfile(pointwise_dir / "dev.jsonl", out_dir / "dev.jsonl")
    shutil.copyfile(pointwise_dir / "test.jsonl", out_dir / "test.jsonl")

    summary = {
        "train": summarize(combined),
        "pointwise_train": summarize(train),
        "contrastive_train": summarize(contrastive),
        "dev": summarize(read_jsonl(out_dir / "dev.jsonl")),
        "test": summarize(read_jsonl(out_dir / "test.jsonl")),
    }
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
