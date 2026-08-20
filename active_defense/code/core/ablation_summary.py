"""Summarize ablation outputs across benchmark-specific runners.

This module is intentionally read-only.  It accepts the native artifacts written
by each benchmark runner and normalizes them to BU/AU/ASR counts.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


Metric = dict[str, int | float | None]


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _fraction(successes: int, n: int) -> Metric:
    return {
        "successes": int(successes),
        "n": int(n),
        "rate": (successes / n if n else None),
    }


def _metric_value(metric: dict[str, Any]) -> Metric:
    if "successes" in metric or "n" in metric:
        successes = int(metric.get("successes", 0))
        n = int(metric.get("n", 0))
    else:
        successes = int(metric.get("success", 0))
        n = int(metric.get("total", 0))
    return _fraction(successes, n)


def _metadata_metrics(path: Path) -> dict[str, Any]:
    data = _read_json(path)
    metrics = data.get("metrics") or data.get("summary") or {}
    return {
        "BU": _metric_value(metrics.get("BU") or {}),
        "AU": _metric_value(metrics.get("AU") or {}),
        "ASR": _metric_value(metrics.get("ASR") or {}),
        "technical_failures": int(metrics.get("technical_failures", 0)),
    }


def _agentdojo(root: Path) -> dict[str, Any]:
    suites = {}
    totals = {"BU": [0, 0], "AU": [0, 0], "ASR": [0, 0]}
    for path in sorted(root.glob("*.json")):
        data = _read_json(path)
        summary = data.get("summary") or {}
        suite = path.stem
        bu = _fraction(
            int(summary.get("benign_passed", 0)),
            int(summary.get("benign_total", summary.get("benign_completed", 0))),
        )
        au = _fraction(
            int(summary.get("attack_utility_passed", 0)),
            int(summary.get("attack_total", summary.get("attack_completed", 0))),
        )
        asr = _fraction(
            int(summary.get("attack_successes", 0)),
            int(summary.get("attack_total", summary.get("attack_completed", 0))),
        )
        suites[suite] = {"BU": bu, "AU": au, "ASR": asr}
        for name, metric in (("BU", bu), ("AU", au), ("ASR", asr)):
            totals[name][0] += int(metric["successes"] or 0)
            totals[name][1] += int(metric["n"] or 0)
    return {
        "BU": _fraction(*totals["BU"]),
        "AU": _fraction(*totals["AU"]),
        "ASR": _fraction(*totals["ASR"]),
        "by_suite": suites,
        "coverage": {"suite_files": len(suites)},
    }


def _skillinject(root: Path) -> dict[str, Any]:
    clean = []
    attack = []
    for path in sorted(root.glob("*_clean.json")):
        clean.append(_read_json(path))
    for path in sorted(root.glob("*_attack.json")):
        attack.append(_read_json(path))
    failures = 0
    state = root / "run_state.json"
    if state.is_file():
        failures = len((_read_json(state).get("failures") or []))
    return {
        "BU": _fraction(sum(row.get("utility") is True for row in clean), len(clean)),
        "AU": _fraction(sum(row.get("utility") is True for row in attack), len(attack)),
        "ASR": _fraction(sum(row.get("attack_effect") is True for row in attack), len(attack)),
        "technical_failures": failures,
        "coverage": {"clean": len(clean), "attack": len(attack)},
    }


def _scr_capflow(root: Path) -> dict[str, Any]:
    clean = []
    attack = []
    files = sorted((root / "capflow").glob("case*.json"))
    for path in files:
        for row in (_read_json(path).get("rows") or []):
            if row.get("condition") == "B_only":
                clean.append(row)
            elif row.get("condition") == "A+B_neutral":
                attack.append(row)
    return {
        "BU": _fraction(sum(row.get("utility") is True for row in clean), len(clean)),
        "AU": _fraction(sum(row.get("utility") is True for row in attack), len(attack)),
        "ASR": _fraction(sum(row.get("attack_success") is True for row in attack), len(attack)),
        "coverage": {"files": len(files), "clean": len(clean), "attack": len(attack)},
    }


def _scr_authblur(root: Path) -> dict[str, Any]:
    clean = []
    attack = []
    files = sorted((root / "authblur").glob("case*.json"))
    if not files:
        files = sorted((root / "results" / "authblur").glob("case*.json"))
    for path in files:
        for row in (_read_json(path).get("rows") or []):
            if row.get("condition") == "level2_findings":
                clean.append(row)
            elif row.get("condition") == "level3_fullauth":
                attack.append(row)
    return {
        "BU": _fraction(sum(row.get("utility") is True for row in clean), len(clean)),
        "AU": _fraction(sum(row.get("utility") is True for row in attack), len(attack)),
        "ASR": _fraction(sum(row.get("released_decision") == 1 for row in attack), len(attack)),
        "coverage": {"files": len(files), "clean": len(clean), "attack": len(attack)},
    }


def _scr_trustlift(root: Path) -> dict[str, Any]:
    clean = []
    attack = []
    search_roots = [root / "trustlift", root / "results" / "trustlift"]
    files = []
    for base in search_roots:
        files.extend(sorted(base.glob("*.json")))
    for path in files:
        row = _read_json(path)
        condition = row.get("condition")
        if condition in {"control", "clean"} or path.name.endswith("_clean.json"):
            clean.append(row)
        elif condition == "attack" or path.name.endswith("_attack.json"):
            attack.append(row)
    return {
        "BU": _fraction(sum(row.get("utility") is True for row in clean), len(clean)),
        "AU": _fraction(sum(row.get("utility") is True for row in attack), len(attack)),
        "ASR": _fraction(sum(row.get("attack_success") is True for row in attack), len(attack)),
        "coverage": {"files": len(files), "clean": len(clean), "attack": len(attack)},
    }


def _merge_metrics(items: list[dict[str, Any]]) -> dict[str, Metric]:
    merged = {}
    for name in ("BU", "AU", "ASR"):
        successes = sum(int(item[name]["successes"] or 0) for item in items)
        n = sum(int(item[name]["n"] or 0) for item in items)
        merged[name] = _fraction(successes, n)
    return merged


def _scr(root: Path) -> dict[str, Any]:
    by_suite = {
        "CapFlow": _scr_capflow(root),
        "AuthBlur": _scr_authblur(root),
        "TrustLift": _scr_trustlift(root),
    }
    total = _merge_metrics(list(by_suite.values()))
    total["by_suite"] = by_suite
    state = root / "run_state.json"
    total["technical_failures"] = (
        len((_read_json(state).get("failures") or [])) if state.is_file() else 0
    )
    return total


def _asb(root: Path) -> dict[str, Any]:
    metadata = root / "METADATA.json"
    if metadata.is_file():
        return _metadata_metrics(metadata)
    results = root / "results.jsonl"
    rows = []
    if results.is_file():
        for line in results.read_text(encoding="utf-8").splitlines():
            if line.strip():
                rows.append(json.loads(line))
    clean = [row for row in rows if row.get("split") == "clean"]
    attack = [row for row in rows if row.get("split") == "attack"]
    return {
        "BU": _fraction(sum(row.get("utility") is True for row in clean), len(clean)),
        "AU": _fraction(sum(row.get("utility") is True for row in attack), len(attack)),
        "ASR": _fraction(sum(row.get("attack_success") is True for row in attack), len(attack)),
        "technical_failures": sum(row.get("technical_failure") is True for row in rows),
        "coverage": {"clean": len(clean), "attack": len(attack)},
    }


def _mcp_json(path: Path) -> dict[str, Any]:
    data = _read_json(path)
    metrics = data.get("metrics") or data.get("summary") or {}
    return {
        "BU": _metric_value(metrics.get("BU") or {}),
        "AU": _metric_value(metrics.get("AU") or {}),
        "ASR": _metric_value(metrics.get("ASR") or {}),
        "technical_failures": int(metrics.get("errors", 0) or 0),
    }


SUMMARIZERS = {
    "agentdojo": _agentdojo,
    "asb_opi": _asb,
    "skillinject": _skillinject,
    "scr": _scr,
    "mcptox": _mcp_json,
    "msb": _mcp_json,
}


def summarize(benchmark: str, path: Path) -> dict[str, Any]:
    result = SUMMARIZERS[benchmark](path)
    return {
        "schema": "ablation-summary-v1",
        "benchmark": benchmark,
        "input": str(path),
        "metrics": {key: result[key] for key in ("BU", "AU", "ASR")},
        **{key: value for key, value in result.items()
           if key not in {"BU", "AU", "ASR"}},
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--benchmark", required=True,
                        choices=tuple(sorted(SUMMARIZERS)))
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    summary = summarize(args.benchmark, args.input)
    text = json.dumps(summary, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
    print(text, end="")


if __name__ == "__main__":
    main()
