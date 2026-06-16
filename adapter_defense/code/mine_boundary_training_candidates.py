#!/usr/bin/env python3
"""Mine candidate data for value+authority boundary training.

No API calls and no synthetic samples. This script scans existing TS-Bench /
ToolSafe trajectory files and classifies rows into coarse training buckets for
the compact boundary schema:

- broad_clean
- clean_side_effect
- clean_value_flow
- unsafe_value_flow
- unsafe_authority_flow
- unsafe_user_or_policy
- unsafe_other

The output is a data map used to decide whether GPT teacher labeling and LoRA
training have enough coverage.
"""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from code_zxr.agent_safety.adapter_defense.code.tooluse_attack_common import ROOT


INFO_RE = re.compile(r"<INFORMATION>.*?</INFORMATION>", re.DOTALL)
VALUE_RE = re.compile(
    r"[A-Z]{2}\d[A-Z0-9]{8,}|[\w.%-]+@[\w.-]+\.[A-Za-z]{2,}|https?://[^\s\"']+|\b\d{4,}\b"
)
ACTION_RE = re.compile(r"\(2\)\s*Action:\s*([A-Za-z_][A-Za-z0-9_]*)")

SIDE_EFFECT_HINTS = {
    "send",
    "delete",
    "update",
    "post",
    "create",
    "reserve",
    "upload",
    "transfer",
    "purchase",
    "submit",
    "edit",
    "change",
    "shutdown",
    "reallocate",
    "redirect",
    "duplicate",
    "access",
    "download",
    "install",
    "execute",
    "run",
    "pay",
    "login",
}

READ_ONLY_HINTS = {
    "get",
    "search",
    "query",
    "read",
    "list",
    "analyze",
    "summarize",
    "calculate",
    "evaluate",
    "market_data",
}


DATASETS = [
    ("agentdojo_banking", "benchmarks/ToolSafe/TS-Bench/agentdojo-traj/banking.json"),
    ("agentdojo_slack", "benchmarks/ToolSafe/TS-Bench/agentdojo-traj/slack.json"),
    ("agentdojo_travel", "benchmarks/ToolSafe/TS-Bench/agentdojo-traj/travel.json"),
    ("agentdojo_workspace", "benchmarks/ToolSafe/TS-Bench/agentdojo-traj/workspace.json"),
    ("agentharm_benign", "benchmarks/ToolSafe/TS-Bench/agentharm-traj/benign_steps.json"),
    ("agentharm_harmful", "benchmarks/ToolSafe/TS-Bench/agentharm-traj/harmful_steps.json"),
    ("asb_opi_success", "benchmarks/ToolSafe/TS-Bench/asb-traj/test/OPI_attack_success.json"),
    ("asb_dpi_success", "benchmarks/ToolSafe/TS-Bench/asb-traj/test/DPI_attack_success.json"),
    ("asb_attack_failure", "benchmarks/ToolSafe/TS-Bench/asb-traj/test/atttack_failure.json"),
]


def load_json(path: Path) -> list[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise TypeError(f"Expected list in {path}")
    return data


def action_tool(row: dict[str, Any]) -> str:
    if row.get("tool"):
        return str(row["tool"])
    m = ACTION_RE.search(str(row.get("current_action", "")))
    return m.group(1) if m else ""


def action_values(row: dict[str, Any]) -> set[str]:
    text = str(row.get("action_input") or row.get("current_action") or "")
    return {v for v in VALUE_RE.findall(text) if len(v) >= 4}


def history_values(row: dict[str, Any]) -> set[str]:
    return {v for v in VALUE_RE.findall(str(row.get("history") or "")) if len(v) >= 4}


def env_tool_names(row: dict[str, Any]) -> set[str]:
    names = set()
    for m in re.finditer(r"^([A-Za-z_][A-Za-z0-9_]*)\s*:", str(row.get("env_info", "")), re.M):
        names.add(m.group(1))
    return names


def is_side_effect(row: dict[str, Any]) -> bool:
    tool = action_tool(row)
    low = tool.lower()
    if any(h in low for h in SIDE_EFFECT_HINTS):
        return True
    if any(h in low for h in READ_ONLY_HINTS):
        return False
    action = str(row.get("current_action", "")).lower()
    return any(h in action for h in SIDE_EFFECT_HINTS)


def score_value(row: dict[str, Any], dataset: str) -> float | None:
    score = row.get("score")
    if score is None:
        return None
    try:
        return float(score)
    except Exception:
        return None


def is_clean(row: dict[str, Any], dataset: str) -> bool:
    score = score_value(row, dataset)
    if dataset == "asb_attack_failure":
        return True
    if dataset == "agentharm_benign":
        return True if score == 0 else False
    return score == 0.0


def is_unsafe(row: dict[str, Any], dataset: str) -> bool:
    score = score_value(row, dataset)
    if dataset == "agentharm_harmful":
        return score == 1.0
    if dataset in {"asb_opi_success", "asb_dpi_success"}:
        return bool(row.get("attack_success", True))
    return score == 1.0


def has_external_source(row: dict[str, Any]) -> bool:
    history = str(row.get("history") or "")
    if INFO_RE.search(history):
        return True
    return "Observation:" in history or "tool_call_result" in history


def value_flow_overlap(row: dict[str, Any]) -> list[str]:
    return sorted(action_values(row) & history_values(row))


def task_tool_match(row: dict[str, Any]) -> bool:
    """Rough proxy for whether current tool is named in user request."""
    tool = action_tool(row).lower()
    instr = str(row.get("instruction") or "").lower()
    if not tool:
        return False
    return tool in instr or tool.replace("_", " ") in instr


def classify(row: dict[str, Any], dataset: str) -> str:
    side = is_side_effect(row)
    external = has_external_source(row)
    overlap = value_flow_overlap(row)
    clean = is_clean(row, dataset)
    unsafe = is_unsafe(row, dataset)

    if clean:
        if side and overlap:
            return "clean_value_flow"
        if side:
            return "clean_side_effect"
        return "broad_clean"

    if unsafe:
        if overlap and side:
            return "unsafe_value_flow"
        if dataset.startswith("agentdojo") and external:
            return "unsafe_authority_flow"
        if dataset in {"asb_dpi_success", "agentharm_harmful"}:
            return "unsafe_user_or_policy"
        if dataset == "asb_opi_success":
            return "unsafe_authority_flow"
        return "unsafe_other"

    return "other"


def make_record(row: dict[str, Any], dataset: str, bucket: str) -> dict[str, Any]:
    return {
        "dataset": dataset,
        "bucket": bucket,
        "id_interaction": row.get("id-interaction"),
        "id_segment": row.get("id-segment"),
        "score": row.get("score"),
        "attack_success": row.get("attack_success"),
        "tool": action_tool(row),
        "side_effect": is_side_effect(row),
        "has_external_source": has_external_source(row),
        "value_overlap": value_flow_overlap(row),
        "task_tool_match": task_tool_match(row),
        "instruction": row.get("instruction"),
        "history": row.get("history", ""),
        "current_action": row.get("current_action"),
        "env_info": row.get("env_info"),
        "raw": row,
    }


def summarize(records: list[dict[str, Any]]) -> dict[str, Any]:
    by_bucket = Counter(r["bucket"] for r in records)
    by_dataset = Counter(r["dataset"] for r in records)
    by_dataset_bucket: dict[str, Counter[str]] = defaultdict(Counter)
    by_bucket_tool: dict[str, Counter[str]] = defaultdict(Counter)
    for r in records:
        by_dataset_bucket[r["dataset"]][r["bucket"]] += 1
        by_bucket_tool[r["bucket"]][r["tool"]] += 1

    selected_training = [
        "broad_clean",
        "clean_side_effect",
        "clean_value_flow",
        "unsafe_value_flow",
        "unsafe_authority_flow",
        "unsafe_user_or_policy",
    ]
    return {
        "total_records": len(records),
        "by_dataset": dict(by_dataset),
        "by_bucket": dict(by_bucket),
        "by_dataset_bucket": {k: dict(v) for k, v in by_dataset_bucket.items()},
        "top_tools_by_bucket": {
            k: v.most_common(20) for k, v in by_bucket_tool.items()
        },
        "candidate_training_total": sum(by_bucket[b] for b in selected_training),
        "candidate_training_buckets": {b: by_bucket[b] for b in selected_training},
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", default=str(ROOT / "code/data/boundary_training_candidates"))
    args = parser.parse_args()

    records = []
    for dataset, rel in DATASETS:
        path = ROOT / rel
        if not path.exists():
            print(f"missing {path}")
            continue
        for row in load_json(path):
            bucket = classify(row, dataset)
            records.append(make_record(row, dataset, bucket))

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    with (out_dir / "candidates.jsonl").open("w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    summary = summarize(records)
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")

    # Write per-bucket files for easy inspection and later teacher-labeling.
    buckets: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for rec in records:
        buckets[rec["bucket"]].append(rec)
    for bucket, items in buckets.items():
        with (out_dir / f"{bucket}.jsonl").open("w", encoding="utf-8") as f:
            for rec in items:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
