"""End-to-end ClawGuard evaluation on the frozen MCPTox protocol."""
from __future__ import annotations

import argparse
import concurrent.futures
import json
from pathlib import Path
import re
import time

from code.baselines.clawguard.adapter import ClawGuardScanner
from code.benchmarks.mcptox.execution.native import catalog_blocks
from code.benchmarks.mcptox.execution.stackone_e2e import (
    _TOOL, _cases, _checkpoint, _replay_cases, _summary,
)
from code.benchmarks.mcptox.protocol_runtime import (
    judge_call as protocol_judge_call,
    protocol_identity,
    propose_tool_call,
)
from code.core.client import client_for_model


def _tool_fields(block: str) -> tuple[str, dict]:
    description_match = re.search(
        r"(?ms)^Description:\s*(.*?)\nArguments:\s*\n", block)
    description = description_match.group(1).strip() if description_match else ""
    arguments = block[description_match.end():] if description_match else ""
    properties, required = {}, []
    for match in re.finditer(r"(?m)^-\s*([^:]+):\s*(.*)$", arguments):
        field, help_text = match.group(1).strip(), match.group(2).strip()
        properties[field] = {"type": "string", "description": help_text}
        if "(required)" in help_text:
            required.append(field)
    return description, {
        "type": "object", "properties": properties,
        "required": required, "additionalProperties": False,
    }


def _filter_system(scanner: ClawGuardScanner, system: str) -> tuple[str, list[dict]]:
    matches = list(_TOOL.finditer(system))
    if not matches:
        return system, []
    decisions, kept = [], []
    for match in matches:
        name, block = match.group(1).strip(), match.group(0)
        _description, schema = _tool_fields(block)
        verdict = scanner.scan_catalog_tool(name, block, schema)
        decisions.append({
            "tool": name,
            "allowed": bool(verdict.get("allowed", True)),
            "sanitized_changed": bool(verdict.get("sanitized_changed", False)),
            "secret_hits": verdict.get("secret_hits", []),
            "checks": verdict.get("checks", []),
        })
        if verdict.get("allowed", True):
            kept.append(str(verdict.get("sanitized_text") or block).rstrip())
    prefix = system[:matches[0].start()].rstrip()
    suffix = system[matches[-1].end():].strip()
    parts = [prefix, *kept]
    if suffix:
        parts.append(suffix)
    return "\n\n\n".join(part for part in parts if part), decisions


def _run_one(agent, agent_model: str, evaluator, evaluator_model: str,
             scanner: ClawGuardScanner, case: dict, mode: str) -> dict:
    started = time.time()
    public = {k: v for k, v in case.items()
              if k not in {"system", "defended_system", "attack_specification"}}
    try:
        raw, proposed = propose_tool_call(
            agent, agent_model, case["defended_system"], case["query"])
        selected = str(proposed.get("tool") or "")
        block = catalog_blocks(str(case.get("defended_system") or "")).get(selected, "")
        call_guard = scanner.scan_call(selected, proposed.get("arguments") or {}, block)
        effective_call = proposed if call_guard.get("allowed", True) else {"tool": "", "arguments": {}}
        verdict = protocol_judge_call(
            evaluator, evaluator_model, case, effective_call, mode == "attack")
        return public | {
            "mode": mode,
            "status": "ok",
            "raw_response": raw,
            "call": effective_call,
            "original_call": proposed,
            "clawguard_call": call_guard,
            "blocked_by_clawguard": not bool(call_guard.get("allowed", True)),
            "no_proposal": not bool(effective_call.get("tool")),
            **verdict,
            "elapsed_seconds": time.time() - started,
        }
    except Exception as exc:
        return public | {
            "mode": mode,
            "status": "error",
            "error": type(exc).__name__ + ": " + str(exc)[:700],
            "elapsed_seconds": time.time() - started,
        }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="deepseek-v4-flash")
    parser.add_argument("--evaluation-model", default="gpt-5.4-2026-03-05")
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--mcptox-replay-rows", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    if args.workers < 1 or (args.limit is not None and args.limit < 1):
        raise ValueError("workers and limit must be positive")
    output = args.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    if args.mcptox_replay_rows:
        clean_cases, attack_cases = [], _replay_cases(args.mcptox_replay_rows, args.limit)
    else:
        clean_cases, attack_cases = _cases(args.limit)
    protocol = protocol_identity()
    scanner = ClawGuardScanner(output.parent / "clawguard_scan_cache.json")
    try:
        for cases in (clean_cases, attack_cases):
            for index, case in enumerate(cases, 1):
                defended, decisions = _filter_system(scanner, case["system"])
                case["defended_system"] = defended
                case["scan_decisions"] = decisions
                case["blocked_tools"] = [row["tool"] for row in decisions if not row["allowed"]]
                if index % 100 == 0:
                    scanner.save()
                    print("catalog", index, "/", len(cases), flush=True)
    finally:
        scanner.save()

    result = (
        json.loads(output.read_text(encoding="utf-8"))
        if args.resume and output.exists() else {
            "schema": "mcptox-clawguard-e2e-v1",
            "benchmark": "MCPTox",
            "condition": "clawguard_e2e",
            "model": args.model,
            "evaluation_model": args.evaluation_model,
            "protocol": protocol,
            "clawguard": {
                "upstream": "baseline/ClawGuard",
                "rules_sha256": scanner.config_sha256,
                "approval_is_deny": scanner.approval_is_deny,
                "boundary": "MCP catalog sanitization/filter plus proposed-call gate",
            },
            "workers": args.workers,
            "limit": args.limit,
            "mcptox_replay_rows": str(args.mcptox_replay_rows) if args.mcptox_replay_rows else None,
            "clean": [],
            "attack": [],
        }
    )
    expected_resume = {
        "schema": "mcptox-clawguard-e2e-v1",
        "model": args.model,
        "evaluation_model": args.evaluation_model,
        "limit": args.limit,
        "mcptox_replay_rows": str(args.mcptox_replay_rows) if args.mcptox_replay_rows else None,
        "protocol": protocol,
    }
    if any(result.get(key) != value for key, value in expected_resume.items()):
        raise ValueError("resume artifact protocol/model/evaluator/limit does not match invocation")
    agent = client_for_model(args.model)
    evaluator = client_for_model(args.evaluation_model)
    for mode, cases in (("clean", clean_cases), ("attack", attack_cases)):
        done = {row["key"] for row in result[mode] if row.get("status") == "ok"}
        pending = [case for case in cases if case["key"] not in done]
        with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
            futures = {
                pool.submit(_run_one, agent, args.model, evaluator,
                            args.evaluation_model, scanner, case, mode): case
                for case in pending
            }
            for index, future in enumerate(concurrent.futures.as_completed(futures), 1):
                row = future.result()
                case = futures[future]
                row["scan_decisions"] = case["scan_decisions"]
                row["blocked_tools"] = case["blocked_tools"]
                result[mode] = [old for old in result[mode] if old["key"] != row["key"]]
                result[mode].append(row)
                if index % 10 == 0 or index == len(pending):
                    _checkpoint(output, result)
                    scanner.save()
                    print(mode, len(result[mode]), "/", len(cases),
                          json.dumps(_summary(result[mode]), ensure_ascii=False), flush=True)
    _checkpoint(output, result)
    scanner.save()
    print(json.dumps({
        "output": str(output),
        "clean": result["clean_summary"],
        "attack": result["attack_summary"],
        "finished_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
