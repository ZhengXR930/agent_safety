#!/usr/bin/env python3
"""Summarize existing attack results for the systematic adaptive study."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "experiment-stage/systematic_adaptive_attack"


RESULTS = [
    {
        "name": "pair_agentdojo_tsguard_177",
        "path": "code/results/pair_source_span_tsguard_182_proxy_thought_deepseek/summary.json",
        "surface": "OPI",
        "category": "authority",
        "target": "TS-Guard",
        "status": "completed",
        "reuse": True,
        "interpretation": "Existing PAIR authority-surface evidence on AgentDojo/ToolSafe. Do not rerun unless target or attack family changes.",
    },
    {
        "name": "pair_agentdojo_tsguard_50_source_only",
        "path": "code/results/pair_source_span_tsguard_50_source_only/summary.json",
        "surface": "OPI",
        "category": "authority",
        "target": "TS-Guard",
        "status": "completed",
        "reuse": True,
        "interpretation": "Small source-only PAIR slice.",
    },
    {
        "name": "pair_asb_opi_tsguard_50",
        "path": "code/results/pair_asb_opi_output_span_tsguard_50_source_only/summary.json",
        "surface": "OPI",
        "category": "authority/value",
        "target": "TS-Guard",
        "status": "completed",
        "reuse": True,
        "interpretation": "PAIR is weak on ASB OPI; use as negative baseline, not as main adaptive attack.",
    },
    {
        "name": "pair_agentdojo_authority_adapter_50",
        "path": "code/results/pair_source_span_authority_adapter_50_deepseek/summary.json",
        "surface": "OPI",
        "category": "authority",
        "target": "authority_adapter",
        "status": "completed",
        "reuse": True,
        "interpretation": "Authority adapter resists old PAIR better than TS-Guard.",
    },
    {
        "name": "soc_agentdojo_tsguard_50",
        "path": "code/results/soc_paper_repro_tsguard_50/summary.json",
        "surface": "OPI",
        "category": "authority",
        "target": "TS-Guard",
        "status": "completed",
        "reuse": True,
        "interpretation": "Non-PAIR source-obfuscation comparison.",
    },
]


def read_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def compact_metrics(summary: dict[str, Any] | None) -> dict[str, Any]:
    if not summary:
        return {"available": False}
    keys = [
        "cases",
        "target_queries",
        "weak_asr",
        "strong_asr",
        "strict_strong_asr",
        "mean_best_score",
        "mean_queries_per_case",
    ]
    return {"available": True, **{k: summary[k] for k in keys if k in summary}}


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    rows = []
    for item in RESULTS:
        summary = read_json(ROOT / item["path"])
        rows.append({**item, "metrics": compact_metrics(summary)})
    out_path = OUT / "inventory.json"
    out_path.write_text(json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(rows, indent=2, ensure_ascii=False))
    print(out_path)


if __name__ == "__main__":
    main()
