#!/usr/bin/env python3
"""Audit why clean AgentDyn tasks fail under the online CaMeL path."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path


MARKERS = {
    "explicit_policy_denial": ("SecurityPolicyDeniedError",),
    "quarantined_information_failure": ("NotEnoughInformationError",),
    "restricted_interpreter_failure": (
        "UndefinedClassError",
        "InvalidProgram",
        "SyntaxError",
        "Unsupported",
        "InvalidStatement",
        "InvalidExpression",
    ),
    "tool_or_argument_failure": (
        "not found",
        "Not Found",
        "verification required",
        "Verification required",
        "invalid input",
        "Invalid input",
    ),
}


def load_rows(root: Path) -> dict[tuple[str, int], dict]:
    rows = {}
    for path in sorted(root.rglob("none.json")):
        payload = json.loads(path.read_text())
        task_id = int(payload["user_task_id"].rsplit("_", 1)[1])
        rows[(payload["suite_name"], task_id)] = payload
    return rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--camel-root", type=Path, required=True)
    parser.add_argument("--undefended-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    camel = load_rows(args.camel_root)
    undefended = load_rows(args.undefended_root)
    if camel.keys() != undefended.keys():
        raise ValueError("CaMeL and undefended task sets do not match")

    categories: Counter[str] = Counter()
    repairs = Counter()
    paired = Counter()
    details = []
    for key in sorted(camel):
        camel_row = camel[key]
        undefended_row = undefended[key]
        text = json.dumps(camel_row.get("messages", []), ensure_ascii=False)
        labels = [name for name, markers in MARKERS.items() if any(marker in text for marker in markers)]
        repair_count = text.count("Running the code gave the following error")
        for label in labels:
            categories[label] += 1
        repairs["tasks_with_repair_feedback"] += repair_count > 0
        repairs["total_repair_feedback_turns"] += repair_count

        c_pass = bool(camel_row.get("utility"))
        u_pass = bool(undefended_row.get("utility"))
        pair_label = (
            "both_pass"
            if c_pass and u_pass
            else "undefended_only_pass"
            if u_pass
            else "camel_only_pass"
            if c_pass
            else "both_fail"
        )
        paired[pair_label] += 1
        details.append(
            {
                "suite": key[0],
                "task": key[1],
                "camel_utility": c_pass,
                "undefended_utility": u_pass,
                "labels": labels,
                "repair_feedback_turns": repair_count,
            }
        )

    result = {
        "schema": "agentdyn-camel-clean-decision-audit-v1",
        "tasks": len(camel),
        "configuration": {
            "use_original": False,
            "replay_with_policies": False,
            "security_policy_engine": "ADNoSecurityPolicyEngine",
            "engine_check_policy_result": "Allowed",
        },
        "paired_utility": dict(paired),
        "failure_markers": dict(categories),
        "repair_activity": dict(repairs),
        "note": "Failure-marker counts are multi-label trace diagnostics, not mutually exclusive causes.",
        "rows": details,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({key: value for key, value in result.items() if key != "rows"}, indent=2))


if __name__ == "__main__":
    main()
