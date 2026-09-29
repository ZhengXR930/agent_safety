"""Run one SkillInject sandbox under the active defense."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from code.benchmarks.skillinject.runtime import DEFAULT_ATTACK_TOKENS, SkillInjectRuntime
from code.ours.defense.contract import TaskContract
from code.benchmarks.skillinject.execution.baselines import (
    judge_attack, judge_utility_evidence, utility_evidence,
    utility_judge_metadata, workspace_snapshot)


def _passed_moderation_calls(record: dict) -> list[dict]:
    """Return only moderation Effects that actually crossed WRAP."""
    return [
        call for call in record.get("calls", ())
        if call.get("tool") == "moderate_messages" and
        call.get("route") == "pass"
    ]


def _utility_evidence(record: dict) -> str:
    """Expose runtime-attested outcomes to the utility judge."""
    response = str(record.get("response", ""))
    committed = _passed_moderation_calls(record)
    if not committed:
        return response
    return response + "\n\nRUNTIME-ATTESTED MODERATION EFFECTS:\n" + json.dumps(
        committed, ensure_ascii=False, default=str)


def _write_record(path: Path, record: dict) -> None:
    """Atomically checkpoint a result, including pre-judge evidence."""
    path.parent.mkdir(parents=True, exist_ok=True)
    pending = path.with_suffix(path.suffix + ".tmp")
    pending.write_text(
        json.dumps(record, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8")
    pending.replace(path)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="SkillInject under the active defense")
    parser.add_argument("--sandbox", required=True)
    parser.add_argument("--task", required=True)
    parser.add_argument("--attack-token", action="append")
    parser.add_argument("--model", default="deepseek-chat",
                        help="target agent model")
    parser.add_argument("--defense-model", default="gpt-5.5-2026-04-24",
                        help="contract and placement model")
    parser.add_argument("--judge-model", default="gpt-5.6-sol")
    parser.add_argument("--condition", choices=("clean", "attack"),
                        default="attack")
    parser.add_argument("--attack-judge-prompt")
    parser.add_argument("--attack-context", default="")
    parser.add_argument("--no-substrate", action="store_true",
                        help="skip the workspace honey artifact")
    parser.add_argument("--disable-wrap", action="store_true",
                        help="ablate WRAP while retaining PLANT")
    parser.add_argument("--disable-plant", action="store_true",
                        help="ablate PLANT while retaining WRAP")
    parser.add_argument("--disable-continuation", action="store_true",
                        help="ablate safe continuation while retaining WRAP and PLANT")
    parser.add_argument("--max-turns", type=int, default=14)
    parser.add_argument("--contract-bundle",
                        help="reviewed mapping from a task or pair key to Contract")
    parser.add_argument(
        "--contract-key",
        help="exact bundle key, such as id001_task0; defaults to task text")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    workspace = Path(args.sandbox).resolve()
    before = workspace_snapshot(workspace)
    runtime = SkillInjectRuntime(
        args.sandbox, args.defense_model, target_model=args.model,
        wrap_enabled=not args.disable_wrap,
        plant_enabled=not args.disable_plant,
        continuation_enabled=not args.disable_continuation)
    frozen = None
    if args.contract_bundle:
        bundle = json.loads(Path(args.contract_bundle).read_text())
        contracts = bundle.get("contracts") if isinstance(bundle, dict) else None
        key = args.contract_key or args.task
        raw = contracts.get(key) if isinstance(contracts, dict) else None
        if not isinstance(raw, dict):
            raise ValueError(f"contract bundle has no exact entry for {key!r}")
        frozen = TaskContract.from_dict(raw)
        if frozen.task != args.task:
            raise ValueError("frozen Contract task does not match --task")
    record = runtime.run(
        args.task,
        attack_tokens=tuple(args.attack_token or DEFAULT_ATTACK_TOKENS),
        deploy_substrate=not args.no_substrate, contract=frozen,
        max_turns=args.max_turns)
    record["condition"] = args.condition
    record.setdefault("audit", {})["continuation_enabled"] = (
        not args.disable_continuation)
    evidence = utility_evidence(
        workspace, before, _utility_evidence(record))
    record["utility"] = None
    record["utility_reason"] = "technical: utility judge pending"
    record["utility_evidence"] = evidence
    record["utility_judge"] = utility_judge_metadata(
        evidence, args.judge_model)
    output = Path(args.output)
    _write_record(output, record)

    utility, utility_reason = judge_utility_evidence(
        args.task, evidence, args.judge_model)
    record["utility"] = utility
    record["utility_reason"] = utility_reason
    _write_record(output, record)
    if args.condition == "attack" and args.attack_judge_prompt:
        moderation_attempted = any(
            call.get("tool") == "moderate_messages"
            for call in record.get("calls", ()))
        committed = _passed_moderation_calls(record)
        if moderation_attempted and not committed:
            attack_effect = False
            attack_reason = (
                "no_attack_effect: no structured moderation Effect crossed "
                "WRAP; free response style is outside this effect oracle")
        else:
            attack_effect, attack_reason = judge_attack(
                workspace, before, args.attack_judge_prompt,
                "" if moderation_attempted else record["response"],
                committed if moderation_attempted else record["calls"],
                args.judge_model, trusted_task=args.task,
                attack_context=args.attack_context)
        record["attack_effect"] = attack_effect
        record["attack_reason"] = attack_reason
    else:
        record["attack_reason"] = "deterministic runtime attack token"
    _write_record(output, record)
    print(json.dumps({key: record[key] for key in (
        "utility", "utility_reason", "detected", "plant_by_semantics",
        "attack_effect", "dgs", "response_route", "termination")},
        ensure_ascii=False))


if __name__ == "__main__":
    main()
