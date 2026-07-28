"""Select one calibration run deterministically and freeze its Contract bundle."""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from code.agentdojo_protocol import (AGENT_MODEL, BENCHMARK_VERSION,
                                     contracts_digest)


def summarize(state: dict) -> dict:
    benign = state.get("benign_by_task") or {}
    attacks = state.get("attacks") or []
    approval_incidents = 0
    auditor_incidents = 0
    intervention_episodes = 0
    for result in benign.values():
        episode_intervened = False
        for incident in result.get("incidents", []):
            routes = {str(incident.get("route", ""))}
            routes.update(str(proposal.get("route", ""))
                          for proposal in incident.get("proposals", []))
            approval_incidents += "approval" in routes
            auditor_incidents += "auditor" in routes
            episode_intervened |= bool(routes & {"approval", "auditor"})
        intervention_episodes += episode_intervened
    return {
        "pairs": len(attacks),
        "benign_tasks": len(benign),
        "benign_utility": sum(bool(result.get("utility")) for result in benign.values()),
        "asr": sum(bool(row.get("result", {}).get("asr")) for row in attacks),
        "attack_utility": sum(
            bool(row.get("result", {}).get("utility")) for row in attacks),
        "approval_incidents": approval_incidents,
        "auditor_incidents": auditor_incidents,
        "intervention_episodes": intervention_episodes,
        "hard_failure_episodes": sum(
            not bool(result.get("utility")) for result in benign.values()),
    }


def selection_key(summary: dict) -> tuple[int, int, int, int, int, int]:
    # Security first, then utility, then independently measured intervention cost.
    return (-summary["asr"], summary["benign_utility"],
            summary["attack_utility"], -summary["approval_incidents"],
            -summary["auditor_incidents"], -summary["hard_failure_episodes"])


def contracts_from(state: dict) -> dict:
    contracts = {}
    for task_id, result in (state.get("benign_by_task") or {}).items():
        contract = result.get("contract")
        if not isinstance(contract, dict):
            raise ValueError(f"candidate is missing Contract for {task_id}")
        contracts[str(task_id)] = contract
    if not contracts:
        raise ValueError("candidate contains no Contracts")
    return contracts


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate", action="append", required=True,
                        help="completed calibration result; repeat for every Contract draw")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    candidates = []
    for name in args.candidate:
        state = json.loads(Path(name).read_text(encoding="utf-8"))
        summary = summarize(state)
        if summary["pairs"] == 0 or summary["benign_tasks"] == 0:
            raise ValueError(f"incomplete calibration candidate: {name}")
        candidates.append((selection_key(summary), name, state, summary))
    # Path is a stable final tie-breaker, never randomness or file order.
    _, selected_name, selected_state, selected_summary = max(
        candidates, key=lambda item: (item[0], item[1]))
    contracts = contracts_from(selected_state)
    bundle = {
        "schema": "frozen-contract-bundle-v1",
        "benchmark_version": BENCHMARK_VERSION,
        "contract_model": AGENT_MODEL,
        "selection_rule": (
            "lexicographic(min_asr,max_bu,max_au,min_approval_incidents,"
            "min_auditor_incidents,min_hard_failures,path)"
        ),
        "selection_split": "calibration",
        "selected_candidate": selected_name,
        "selection_score": selected_summary,
        "candidate_scores": [
            {"path": name, **summary}
            for _, name, _, summary in sorted(candidates, key=lambda item: item[1])],
        "frozen_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "contracts_sha256": contracts_digest(contracts),
        "contracts": contracts,
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    pending = output.with_suffix(output.suffix + ".tmp")
    pending.write_text(json.dumps(bundle, ensure_ascii=False, indent=2), encoding="utf-8")
    pending.replace(output)
    print(json.dumps({k: bundle[k] for k in (
        "selected_candidate", "selection_score", "contracts_sha256")},
        ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
