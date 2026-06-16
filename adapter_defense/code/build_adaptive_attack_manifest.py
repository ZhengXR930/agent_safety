#!/usr/bin/env python3
"""Build public-benchmark-derived manifests for three-category adaptive attacks."""

from __future__ import annotations

import argparse
import json
import random
import re
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
INFO_RE = re.compile(r"<INFORMATION>.*?</INFORMATION>", re.DOTALL)


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def normalize_candidate(row: dict[str, Any], category: str) -> dict[str, Any]:
    return {
        "attack_id": f"{category}:{row.get('dataset')}:{row.get('id_interaction')}:{row.get('id_segment')}",
        "category": category,
        "dataset": row.get("dataset"),
        "bucket": row.get("bucket"),
        "kind": row.get("bucket"),
        "tool": row.get("tool"),
        "id_interaction": row.get("id_interaction"),
        "id_segment": row.get("id_segment"),
        "instruction": row.get("instruction"),
        "history": row.get("history") or "",
        "current_action": row.get("current_action") or "",
        "env_info": row.get("env_info") or "",
        "score": row.get("score"),
        "has_information_span": bool(INFO_RE.search(row.get("history") or "")),
        "value_overlap": row.get("value_overlap", []),
        "structured_values": row.get("structured_values"),
        "public_source": "boundary_training_candidates",
    }


def load_value_structured_lookup(path: Path) -> dict[tuple[str, int, int], dict[str, Any]]:
    lookup = {}
    if not path.exists():
        return lookup
    for row in load_jsonl(path):
        sample = row.get("sample") or {}
        key = (row.get("dataset"), sample.get("id-interaction"), sample.get("id-segment"))
        lookup[key] = row
    return lookup


def sample_bucket(
    *,
    path: Path,
    category: str,
    limit: int,
    seed: int,
    prefer_information_span: bool,
    structured_lookup: dict[tuple[str, int, int], dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    rows = [normalize_candidate(r, category) for r in load_jsonl(path)]
    if structured_lookup:
        for row in rows:
            key = (row["dataset"], row["id_interaction"], row["id_segment"])
            structured = structured_lookup.get(key)
            if structured:
                row["structured_values"] = structured.get("structured_values")
    if prefer_information_span:
        with_info = [r for r in rows if r["has_information_span"]]
        without_info = [r for r in rows if not r["has_information_span"]]
        rows = with_info + without_info
    rng = random.Random(seed)
    # Shuffle within information-span preference groups to avoid same-domain-only heads.
    if prefer_information_span:
        with_info = [r for r in rows if r["has_information_span"]]
        without_info = [r for r in rows if not r["has_information_span"]]
        rng.shuffle(with_info)
        rng.shuffle(without_info)
        rows = with_info + without_info
    else:
        rng.shuffle(rows)
    return rows[:limit]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--output-dir", default=str(ROOT / "experiment-stage/adaptive_attack"))
    ap.add_argument("--limit-per-category", type=int, default=30)
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    candidates = ROOT / "code/data/boundary_training_candidates"
    structured_lookup = load_value_structured_lookup(
        ROOT / "code/data/value_structured_sft_balanced_1p3k/test.jsonl"
    )
    manifests = []
    manifests.extend(
        sample_bucket(
            path=candidates / "unsafe_authority_flow.jsonl",
            category="authority",
            limit=args.limit_per_category,
            seed=args.seed,
            prefer_information_span=True,
        )
    )
    manifests.extend(
        sample_bucket(
            path=candidates / "unsafe_value_flow.jsonl",
            category="value",
            limit=args.limit_per_category,
            seed=args.seed + 1,
            prefer_information_span=True,
            structured_lookup=structured_lookup,
        )
    )
    manifests.extend(
        sample_bucket(
            path=candidates / "unsafe_user_or_policy.jsonl",
            category="policy",
            limit=args.limit_per_category,
            seed=args.seed + 2,
            prefer_information_span=False,
        )
    )

    manifest_path = out_dir / "category_manifest.jsonl"
    with manifest_path.open("w", encoding="utf-8") as f:
        for row in manifests:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    summary: dict[str, Any] = {"n": len(manifests), "by_category": {}, "by_dataset": {}}
    for row in manifests:
        summary["by_category"][row["category"]] = summary["by_category"].get(row["category"], 0) + 1
        summary["by_dataset"][row["dataset"]] = summary["by_dataset"].get(row["dataset"], 0) + 1
    summary["manifest"] = str(manifest_path)
    (out_dir / "category_manifest_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
