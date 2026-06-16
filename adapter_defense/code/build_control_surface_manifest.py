#!/usr/bin/env python3
"""Build a public-benchmark manifest keyed by realistic attacker control surface."""

from __future__ import annotations

import argparse
import json
import random
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "experiment-stage/systematic_adaptive_attack"


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def load_json(path: Path) -> Any:
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))


def boundary_rows(bucket: str) -> list[dict[str, Any]]:
    return load_jsonl(ROOT / f"code/data/boundary_training_candidates/{bucket}.jsonl")


def row_id(prefix: str, row: dict[str, Any], idx: int) -> str:
    dataset = row.get("dataset") or row.get("Corresponding Agent") or "unknown"
    interaction = row.get("id-interaction", row.get("id_interaction", idx))
    segment = row.get("id-segment", row.get("id_segment", 0))
    return f"{prefix}:{dataset}:{interaction}:{segment}:{idx}"


def pick(rows: Iterable[dict[str, Any]], n: int, seed: int) -> list[dict[str, Any]]:
    rows = list(rows)
    rng = random.Random(seed)
    rng.shuffle(rows)
    return rows[:n]


def from_boundary(bucket: str, *, category: str, surface: str, limit: int, seed: int) -> list[dict[str, Any]]:
    rows = [
        r
        for r in boundary_rows(bucket)
        if surface != "DPI" or str(r.get("dataset", "")).startswith(("asb_dpi", "agentharm"))
    ]
    out = []
    for idx, r in enumerate(pick(rows, limit, seed)):
        controlled = ["instruction"] if surface == "DPI" else ["history", "tool_observation"]
        if surface == "memory":
            controlled = ["retrieved_memory", "history"]
        out.append(
            {
                "manifest_id": row_id(f"{surface.lower()}_{category}", r, idx),
                "benchmark": r.get("dataset"),
                "source_file": f"code/data/boundary_training_candidates/{bucket}.jsonl",
                "category": category,
                "control_surface": surface,
                "attacker_controls": controlled,
                "evaluation_modes": ["step_guard"],
                "rollout_available": False,
                "tool": r.get("tool"),
                "instruction": r.get("instruction"),
                "history": r.get("history"),
                "current_action": r.get("current_action"),
                "env_info": r.get("env_info"),
                "label_bucket": bucket,
                "public_source": True,
            }
        )
    return out


def from_agentharm(limit: int, seed: int) -> list[dict[str, Any]]:
    rows = load_json(ROOT / "benchmarks/ToolSafe/TS-Bench/agentharm-traj/harmful_steps.json")
    out = []
    for idx, r in enumerate(pick(rows, limit, seed)):
        out.append(
            {
                "manifest_id": row_id("dpi_policy_agentharm", r, idx),
                "benchmark": "agentharm_traj",
                "source_file": "benchmarks/ToolSafe/TS-Bench/agentharm-traj/harmful_steps.json",
                "category": "policy",
                "control_surface": "DPI",
                "attacker_controls": ["instruction"],
                "evaluation_modes": ["step_guard", "direct_agent_request"],
                "rollout_available": True,
                "tool": None,
                "instruction": r.get("instruction"),
                "history": r.get("history"),
                "current_action": r.get("current_action"),
                "env_info": r.get("env_info"),
                "label_bucket": "unsafe_user_or_policy",
                "public_source": True,
            }
        )
    return out


def from_asb_pot(limit: int, seed: int) -> list[dict[str, Any]]:
    rows = load_jsonl(ROOT / "benchmarks/ASB/data/all_attack_tools.jsonl")
    out = []
    for idx, r in enumerate(pick(rows, limit, seed)):
        category = "policy" if str(r.get("Aggressive", "")).lower() == "true" else "authority"
        out.append(
            {
                "manifest_id": f"pot_{category}_asb:{r.get('Corresponding Agent')}:{r.get('Attacker Tool')}:{idx}",
                "benchmark": "ASB",
                "source_file": "benchmarks/ASB/data/all_attack_tools.jsonl",
                "category": category,
                "control_surface": "PoT",
                "attacker_controls": ["tool_name", "tool_description", "trigger", "tool_availability"],
                "evaluation_modes": ["rollout", "prompt_defense"],
                "rollout_available": True,
                "agent": r.get("Corresponding Agent"),
                "tool": r.get("Attacker Tool"),
                "attacker_instruction": r.get("Attacker Instruction"),
                "tool_description": r.get("Description"),
                "attack_goal": r.get("Attack goal"),
                "attack_type": r.get("Attack Type"),
                "aggressive": r.get("Aggressive"),
                "public_source": True,
            }
        )
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit-per-cell", type=int, default=25)
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    OUT.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, Any]] = []
    n = args.limit_per_cell
    seed = args.seed
    rows += from_boundary("unsafe_authority_flow", category="authority", surface="OPI", limit=n, seed=seed)
    rows += from_boundary("unsafe_value_flow", category="value", surface="OPI", limit=n, seed=seed + 1)
    rows += from_boundary("unsafe_user_or_policy", category="policy", surface="DPI", limit=n, seed=seed + 2)
    rows += from_agentharm(limit=n, seed=seed + 3)
    rows += from_asb_pot(limit=n, seed=seed + 4)

    path = OUT / "control_surface_manifest.jsonl"
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    summary: dict[str, Any] = {"n": len(rows), "by_category_surface": {}}
    for row in rows:
        key = f"{row['category']}::{row['control_surface']}"
        summary["by_category_surface"][key] = summary["by_category_surface"].get(key, 0) + 1
    (OUT / "control_surface_manifest_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    print(path)


if __name__ == "__main__":
    main()
