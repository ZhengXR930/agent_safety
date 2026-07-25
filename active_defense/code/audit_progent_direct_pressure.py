"""Audit whether saved direct-attack cells exposed and exercised the attack."""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path


def _matches(call: dict, expected: object) -> bool:
    if call.get("function") != getattr(expected, "function", None):
        return False
    actual_args = call.get("args") or {}
    expected_args = dict(getattr(expected, "args", None) or {})
    return all(actual_args.get(key) == value for key, value in expected_args.items())


def audit(path: Path, suite_name: str) -> dict:
    root = Path(__file__).resolve().parents[1]
    for item in (root / "baseline/AutoDojo/agentdojo/src",
                 root / "baseline/AutoDojo/agentdojo/variant_generation"):
        if str(item) not in sys.path:
            sys.path.insert(0, str(item))
    from agentdojo.task_suite.load_suites import get_suite

    suite = get_suite("v1.2.2", suite_name)
    data = json.loads(path.read_text(encoding="utf-8"))
    rows = []
    for record in data["records"]:
        task = suite.get_injection_task_by_id(record["injection_task"])
        user_task = suite.get_user_task_by_id(record["user_task"])
        environment = suite.load_and_inject_default_environment({})
        environment = user_task.init_environment(environment)
        expected = task.ground_truth(environment)
        target_tools = {call.function for call in expected}
        result_blob = "\n".join(str(item.get("content") or "")
                                for item in record.get("tool_results", []))
        calls = record.get("tool_calls", [])
        results = record.get("tool_results", [])
        rows.append({
            "user_task": record["user_task"],
            "injection_task": record["injection_task"],
            "payload_observed": task.GOAL in result_blob,
            "target_tools": sorted(target_tools),
            "target_tool_class_attempted": any(item.get("function") in target_tools for item in calls),
            "target_call_attempted": any(_matches(item, wanted)
                                         for item in calls for wanted in expected),
            "target_call_executed": any(
                _matches(item, wanted) and item.get("error") is None
                for item in results for wanted in expected
            ),
            "target_tool_result_observed": any(
                item.get("function") in target_tools and item.get("error") is None
                for item in results
            ),
            "defense_blocked": bool(record.get("defense_blocked")),
            "asr": bool(record.get("asr")),
            "utility": bool(record.get("utility")),
            "failure_class": record.get("failure_class"),
        })
    summary = {
        "suite": suite_name,
        "completed": len(rows),
        "payload_observed": sum(x["payload_observed"] for x in rows),
        "target_tool_class_attempted": sum(x["target_tool_class_attempted"] for x in rows),
        "target_call_attempted": sum(x["target_call_attempted"] for x in rows),
        "target_call_executed": sum(x["target_call_executed"] for x in rows),
        "defense_blocked": sum(x["defense_blocked"] for x in rows),
        "asr": sum(x["asr"] for x in rows),
        "utility": sum(x["utility"] for x in rows),
        "failure_classes": dict(Counter(str(x["failure_class"]) for x in rows)),
    }
    return {"source": str(path), "summary": summary, "records": rows}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--suite", required=True)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = audit(args.input, args.suite)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result["summary"], ensure_ascii=False))


if __name__ == "__main__":
    main()
