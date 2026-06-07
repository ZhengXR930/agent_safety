#!/usr/bin/env python3
"""Build split-aware M1 Binary LoRA SFT data for TS-Guard hardening.

M1 is intentionally conservative: it keeps the TS-Guard three-field output
schema and adds only train-split adaptive hard negatives with static replay.
The resulting JSONL is chat-style SFT data:

{"messages": [{"role": "user", "content": ...}, {"role": "assistant", ...}], ...}

This script does not train. It prepares leakage-safe data so the downstream
LoRA run can test whether adaptive hard-negative SFT helps held-out ASR.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
TOOLSAFE_SRC = ROOT / "benchmarks" / "ToolSafe" / "src"
sys.path.insert(0, str(TOOLSAFE_SRC))

from agent.agent_prompts import GUARD_TEMPLATES  # noqa: E402


AGENTDOJO_META = ROOT / "code/results/toolsafe_local_guard_slice_tsguard/meta_data.json"
PAIR_RECORDS = ROOT / "code/results/pair_source_span_tsguard_182_proxy_thought_deepseek/records.jsonl"
AGENTHARM_HARMFUL = ROOT / "benchmarks/ToolSafe/TS-Bench/agentharm-traj/harmful_steps.json"
AGENTHARM_BENIGN = ROOT / "benchmarks/ToolSafe/TS-Bench/agentharm-traj/benign_steps.json"
ASB_FILES = {
    "asb_opi_success": ROOT / "benchmarks/ToolSafe/TS-Bench/asb-traj/test/OPI_attack_success.json",
    "asb_dpi_success": ROOT / "benchmarks/ToolSafe/TS-Bench/asb-traj/test/DPI_attack_success.json",
    "asb_attack_failure": ROOT / "benchmarks/ToolSafe/TS-Bench/asb-traj/test/atttack_failure.json",
}


def stable_bucket(text: str) -> int:
    digest = hashlib.md5(text.encode("utf-8")).hexdigest()
    return int(digest[:8], 16) % 100


def split_for_group(group_id: str, *, train_pct: int, dev_pct: int) -> str:
    bucket = stable_bucket(group_id)
    if bucket < train_pct:
        return "train"
    if bucket < train_pct + dev_pct:
        return "dev"
    return "test"


def normalize_score(score: Any) -> float:
    if score in ["0", 0, 0.0]:
        return 0.0
    if score in ["0.5", 0.5]:
        return 0.5
    if score in ["1", 1, 1.0]:
        return 1.0
    raise ValueError(f"Unsupported score: {score!r}")


def target_text(*, malicious_user: bool, being_attacked: bool, harmfulness: float) -> str:
    return (
        f"<Malicious_User_Request> {'yes' if malicious_user else 'no'} <\\Malicious_User_Request>\n"
        f"<Being_Attacked> {'yes' if being_attacked else 'no'} <\\Being_Attacked>\n"
        f"<Harmfulness_Rating> {harmfulness:.1f} <\\Harmfulness_Rating>"
    )


def prompt_for_sample(sample: dict[str, Any]) -> str:
    return GUARD_TEMPLATES["TS-Guard"].format(
        env_info=sample["env_info"],
        user_request=sample["instruction"],
        agent_action={
            "interaction_history": sample.get("history", ""),
            "current_action": sample["current_action"],
        },
    )


def make_sft_record(
    *,
    sample: dict[str, Any],
    source: str,
    split: str,
    group_id: str,
    target: str,
    record_type: str,
    label_source: str,
    extra_meta: dict[str, Any] | None = None,
) -> dict[str, Any]:
    meta = {
        "source": source,
        "split": split,
        "group_id": group_id,
        "record_type": record_type,
        "label_source": label_source,
        "id_interaction": sample.get("id-interaction", sample.get("case_id")),
        "id_segment": sample.get("id-segment", sample.get("segment_id")),
        "score": sample.get("score"),
    }
    if extra_meta:
        meta.update(extra_meta)
    return {
        "messages": [
            {"role": "user", "content": prompt_for_sample(sample)},
            {"role": "assistant", "content": target},
        ],
        "meta": meta,
    }


def labels_for_static(sample: dict[str, Any], source: str) -> tuple[str, dict[str, Any]]:
    score = normalize_score(sample.get("score"))
    malicious_user = False
    being_attacked = False

    if source == "agentdojo":
        malicious_user = False
        being_attacked = score > 0
    elif source == "agentharm":
        malicious_user = score > 0
        being_attacked = False
    elif source == "asb_opi_success":
        malicious_user = False
        being_attacked = score > 0
    elif source == "asb_dpi_success":
        # ASB-DPI places the harmful directive in the user-side prompt.
        malicious_user = score > 0
        being_attacked = False
    elif source == "asb_attack_failure":
        malicious_user = False
        being_attacked = False
    else:
        raise ValueError(source)

    target = target_text(
        malicious_user=malicious_user,
        being_attacked=being_attacked,
        harmfulness=score,
    )
    fields = {
        "Malicious_User_Request": "yes" if malicious_user else "no",
        "Being_Attacked": "yes" if being_attacked else "no",
        "Harmfulness_Rating": score,
    }
    return target, fields


def load_agentdojo_static() -> list[dict[str, Any]]:
    meta = json.loads(AGENTDOJO_META.read_text(encoding="utf-8"))
    return [item["meta_sample"] for item in meta]


def load_json(path: Path) -> list[dict[str, Any]]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_pair_records() -> list[dict[str, Any]]:
    rows = []
    with PAIR_RECORDS.open("r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def choose_hard_negatives(
    pair_records: list[dict[str, Any]],
    split_by_group: dict[str, str],
    *,
    min_score: int,
    best_only: bool,
) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for rec in pair_records:
        candidate = rec["candidate"]
        group_id = f"agentdojo:{candidate.get('id-interaction', rec.get('case_id'))}"
        if split_by_group.get(group_id) != "train":
            continue
        if int(rec.get("score", 0)) < min_score:
            continue
        grouped[f"{candidate.get('id-interaction')}::{candidate.get('id-segment')}"].append(rec)

    chosen: list[dict[str, Any]] = []
    for rows in grouped.values():
        rows = sorted(
            rows,
            key=lambda r: (
                int(r.get("score", 0)),
                bool(r.get("strict_strong_success")),
                bool(r.get("strong_success")),
                -int(r.get("round", 99)),
            ),
            reverse=True,
        )
        if best_only:
            chosen.append(rows[0])
        else:
            chosen.extend(rows)
    return chosen


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", default=str(ROOT / "code/data/guard_mvp_m1"))
    parser.add_argument("--train-pct", type=int, default=70)
    parser.add_argument("--dev-pct", type=int, default=15)
    parser.add_argument("--hard-negative-min-score", type=int, default=5)
    parser.add_argument("--all-hard-negative-attempts", action="store_true")
    parser.add_argument("--max-asb-train", type=int, default=2000)
    parser.add_argument("--max-asb-dev", type=int, default=500)
    parser.add_argument("--max-asb-test", type=int, default=500)
    args = parser.parse_args()

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    static_sources: list[tuple[str, list[dict[str, Any]]]] = [
        ("agentdojo", load_agentdojo_static()),
        ("agentharm", load_json(AGENTHARM_HARMFUL) + load_json(AGENTHARM_BENIGN)),
    ]
    for name, path in ASB_FILES.items():
        static_sources.append((name, load_json(path)))

    split_by_group: dict[str, str] = {}
    static_records: list[dict[str, Any]] = []
    split_caps = {
        "train": args.max_asb_train,
        "dev": args.max_asb_dev,
        "test": args.max_asb_test,
    }
    asb_counts_by_split: Counter[tuple[str, str]] = Counter()

    for source, samples in static_sources:
        for sample in samples:
            group_id = f"{source}:{sample.get('id-interaction')}"
            split = split_for_group(group_id, train_pct=args.train_pct, dev_pct=args.dev_pct)
            split_by_group[group_id] = split
            if source.startswith("asb_"):
                key = (source, split)
                if asb_counts_by_split[key] >= split_caps[split]:
                    continue
                asb_counts_by_split[key] += 1
            target, fields = labels_for_static(sample, source)
            static_records.append(
                make_sft_record(
                    sample=sample,
                    source=source,
                    split=split,
                    group_id=group_id,
                    target=target,
                    record_type="static_replay",
                    label_source="benchmark_score_to_tsguard_fields_silver",
                    extra_meta={"target_fields": fields},
                )
            )

    pair_records = load_pair_records()
    hard_recs = choose_hard_negatives(
        pair_records,
        split_by_group,
        min_score=args.hard_negative_min_score,
        best_only=not args.all_hard_negative_attempts,
    )
    hard_records: list[dict[str, Any]] = []
    for rec in hard_recs:
        candidate = rec["candidate"]
        group_id = f"agentdojo:{candidate.get('id-interaction', rec.get('case_id'))}"
        target = target_text(malicious_user=False, being_attacked=True, harmfulness=1.0)
        hard_records.append(
            make_sft_record(
                sample=candidate,
                source="agentdojo_pair_deepseek",
                split="train",
                group_id=group_id,
                target=target,
                record_type="adaptive_hard_negative",
                label_source="pair_attack_candidate_fixed_unsafe_action",
                extra_meta={
                    "target_fields": {
                        "Malicious_User_Request": "no",
                        "Being_Attacked": "yes",
                        "Harmfulness_Rating": 1.0,
                    },
                    "attack_score": rec.get("score"),
                    "weak_success": rec.get("weak_success"),
                    "strong_success": rec.get("strong_success"),
                    "strict_strong_success": rec.get("strict_strong_success"),
                    "round": rec.get("round"),
                    "stream": rec.get("stream"),
                },
            )
        )

    all_records = static_records + hard_records
    by_split = {"train": [], "dev": [], "test": []}
    for rec in all_records:
        by_split[rec["meta"]["split"]].append(rec)

    for split, rows in by_split.items():
        write_jsonl(out_dir / f"{split}.jsonl", rows)
    write_jsonl(out_dir / "static_replay.jsonl", static_records)
    write_jsonl(out_dir / "adaptive_hard_negatives_train.jsonl", hard_records)

    summary = {
        "config": vars(args),
        "paths": {
            "agentdojo_meta": str(AGENTDOJO_META),
            "pair_records": str(PAIR_RECORDS),
            "output_dir": str(out_dir),
        },
        "counts": {
            "static_records": len(static_records),
            "adaptive_hard_negatives_train": len(hard_records),
            "total_records": len(all_records),
            "by_split": {k: len(v) for k, v in by_split.items()},
            "by_source": dict(Counter(rec["meta"]["source"] for rec in all_records)),
            "by_record_type": dict(Counter(rec["meta"]["record_type"] for rec in all_records)),
            "by_split_source": {
                f"{split}/{source}": count
                for (split, source), count in Counter(
                    (rec["meta"]["split"], rec["meta"]["source"]) for rec in all_records
                ).items()
            },
        },
        "label_note": (
            "M1 keeps TS-Guard's three-field output schema. Labels are silver mappings "
            "from benchmark score and dataset attack surface; this is appropriate for "
            "binary-LoRA MVP but not final factor-supervision claims."
        ),
    }
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    (out_dir / "splits.json").write_text(json.dumps(split_by_group, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
