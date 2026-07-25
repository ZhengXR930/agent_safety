"""Find existing AgentDojo cells suitable for authorization-metadata laundering.

Selection uses only benchmark structure: the clean user task and injection task
must share an effect tool, and DirectAttack must expose at least one legitimate
injection vector on the clean task's path.  No defense outputs or labels are
used to manufacture tasks.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


EFFECT_HINTS = (
    "send_", "post_", "create_", "add_", "remove_", "delete_", "update_",
    "invite_", "reserve_", "schedule_", "share_", "append_", "cancel_",
)


def _is_effect(name: str) -> bool:
    return name.startswith(EFFECT_HINTS)


def discover(suites: list[str]) -> list[dict[str, Any]]:
    root = Path(__file__).resolve().parents[1]
    src = root / "baseline" / "AutoDojo" / "agentdojo" / "src"
    if str(src) not in sys.path:
        sys.path.insert(0, str(src))
    from agentdojo.attacks.baseline_attacks import DirectAttack
    from agentdojo.task_suite.load_suites import get_suite

    rows: list[dict[str, Any]] = []
    for suite_name in suites:
        suite = get_suite("v1.2.2", suite_name)
        base_env = suite.load_and_inject_default_environment({})
        direct = DirectAttack(suite, None)
        for user_task in suite.user_tasks.values():
            env = user_task.init_environment(base_env.model_copy(deep=True))
            try:
                user_calls = user_task.ground_truth(env)
            except Exception:
                continue
            user_effects = {call.function for call in user_calls if _is_effect(call.function)}
            if not user_effects:
                continue
            for injection_task in suite.injection_tasks.values():
                try:
                    injection_calls = injection_task.ground_truth(env)
                    vectors = tuple(direct.attack(user_task, injection_task))
                except Exception:
                    continue
                injection_effects = {
                    call.function for call in injection_calls if _is_effect(call.function)
                }
                shared = sorted(user_effects & injection_effects)
                if not shared or not vectors:
                    continue
                rows.append({
                    "suite": suite_name,
                    "user_task": user_task.ID,
                    "injection_task": injection_task.ID,
                    "shared_effects": shared,
                    "vectors": list(vectors),
                    "user_prompt": user_task.PROMPT,
                    "attacker_goal": injection_task.GOAL,
                    "priority": len(shared),
                })
    return sorted(rows, key=lambda row: (-row["priority"], row["suite"],
                                         row["user_task"], row["injection_task"]))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--suites", nargs="+", default=["slack", "workspace", "banking", "travel"])
    parser.add_argument("--output", default="experiment_stage/authority_laundering_cells.json")
    args = parser.parse_args()
    rows = discover(args.suites)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps({"count": len(rows), "cells": rows}, indent=2,
                                 ensure_ascii=False), encoding="utf-8")
    print(json.dumps({"count": len(rows), "output": str(output)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
