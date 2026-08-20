"""Run MCP catalog baselines on MSB MCP-ITP replay rows.

This runner keeps the adaptive attack denominator fixed: an optimized
payload-aware MCP-ITP poison block is replayed over each clean MSB task
catalog, a baseline filters that catalog, and the target model makes a fresh
single tool proposal.  ASR is scored with the same payload-aware objective used
by ``code.benchmarks.msb.adaptive.mcp_itp``.
"""
from __future__ import annotations

import argparse
import concurrent.futures
from copy import deepcopy
import json
from pathlib import Path
import re
import time

from code.benchmarks.mcptox.adaptive.mcp_itp import _merge_system
from code.benchmarks.mcptox.execution.stackone_e2e import (
    DEFAULT_NODE,
    StackOneScanner,
    _filter_system as _stackone_filter,
)
from code.benchmarks.mcptox.execution.mcpguard_e2e import (
    MCPGuardScanner,
    _filter_system as _mcpguard_filter,
)
from code.benchmarks.mcptox.execution.pipelock import (
    PipelockScanner,
    _filter_system as _pipelock_filter,
)
from code.benchmarks.mcptox.execution.clawguard_e2e import (
    _filter_system as _clawguard_filter,
)
from code.baselines.clawguard.adapter import ClawGuardScanner
from code.benchmarks.mcptox.protocol_runtime import propose_tool_call
from code.benchmarks.msb.execution.clean_runtime import EXPECTED_OPERATION
from code.benchmarks.msb.adaptive.mcp_itp import (
    MSBObjective,
    _catalog_for_case,
    _payload_score,
    _payload_success,
)
from code.core.client import client_for_model


ROOT = Path(__file__).resolve().parents[4]
WORKSPACE = ROOT.parent
CASES = ROOT / "code/benchmarks/msb/data/cases.json"
PIPLELOCK_BIN = ROOT / ".tools/pipelock-3.2.0/pipelock"
_TOOL = re.compile(
    r"(?ms)^Tool:\s*([^\n]+)\n.*?"
    r"(?=\n{3}Tool:\s*|\n{3}Choose the appropriate tool|\Z)"
)


def _objective(value: dict) -> MSBObjective:
    return MSBObjective(
        original_tool=str(value.get("original_tool") or ""),
        target_tool=str(value.get("target_tool") or ""),
        target_tools=tuple(map(str, value.get("target_tools") or ())),
        poison_tool=str(value.get("poison_tool") or value.get("target_tool") or ""),
        kind=str(value.get("kind") or ""),
        reason=str(value.get("reason") or ""),
        objective_text=str(value.get("objective_text") or ""),
        payload_spec=dict(value.get("payload_spec") or {}),
    )


def _load_replay(path: Path, limit: int | None = None) -> list[dict]:
    official = {
        row["case_id"]: row
        for row in json.loads(CASES.read_text(encoding="utf-8"))["cases"]
    }
    artifact = json.loads(path.read_text(encoding="utf-8"))
    rows = artifact.get("rows") if isinstance(artifact, dict) else artifact
    if not isinstance(rows, list):
        raise TypeError("MSB replay artifact must contain a rows list")
    selected = []
    for row in rows:
        if not isinstance(row, dict) or row.get("status") != "ok":
            continue
        case_id = str(row.get("case_id") or "")
        poison_block = str(row.get("optimized_poison_block") or "")
        if not case_id or not poison_block:
            continue
        if case_id not in official:
            raise ValueError(f"unknown MSB replay case id: {case_id}")
        msb_row = deepcopy(official[case_id])
        clean_system, _blocks = _catalog_for_case(msb_row)
        system = _merge_system(clean_system, poison_block)
        selected.append({
            "case_id": case_id,
            "key": case_id,
            "server": msb_row["tool"],
            "server_name": msb_row["tool"],
            "suite": msb_row["attack_type"],
            "attack_type": msb_row["attack_type"],
            "attack_task": msb_row["attack_task"],
            "query": msb_row["task"],
            "task": msb_row["task"],
            "system": system,
            "attack_specification": poison_block,
            "expected_tools": sorted(EXPECTED_OPERATION[msb_row["task"]]),
            "objective": row.get("objective") or {},
            "source_row": {k: v for k, v in row.items()
                           if k not in {"raw_response"}},
        })
    if limit is not None:
        selected = selected[:limit]
    if not selected:
        raise ValueError("MSB replay artifact selected no runnable rows")
    return selected


def _tool_fields(block: str) -> tuple[str, dict]:
    description_match = re.search(
        r"(?ms)^Description:\s*(.*?)\nArguments:\s*\n", block)
    description = description_match.group(1).strip() if description_match else ""
    arguments = block[description_match.end():] if description_match else ""
    properties, required = {}, []
    for match in re.finditer(r"(?m)^-\s*([^(]+)\(([^,)]+),\s*([^)]+)\)", arguments):
        name = match.group(1).strip()
        kind = match.group(2).strip()
        required_text = match.group(3).strip()
        properties[name] = {"type": kind if kind in {"string", "number", "integer", "boolean"} else "string"}
        if required_text == "required":
            required.append(name)
    return description, {
        "type": "object",
        "properties": properties,
        "required": required,
        "additionalProperties": False,
    }


def _mcpguard_filter_msb(scanner: MCPGuardScanner,
                         system: str) -> tuple[str, list[dict]]:
    matches = list(_TOOL.finditer(system))
    decisions, kept = [], []
    for match in matches:
        name, block = match.group(1).strip(), match.group(0)
        description, schema = _tool_fields(block)
        verdict = scanner.scan(name, description, schema)
        decisions.append({"tool": name, **verdict})
        if verdict["allowed"]:
            kept.append(block.rstrip())
    prefix = system[:matches[0].start()].rstrip() if matches else system.rstrip()
    suffix = system[matches[-1].end():].strip() if matches else ""
    parts = [prefix, *kept]
    if suffix:
        parts.append(suffix)
    return "\n\n\n".join(part for part in parts if part), decisions


def _task_complete(call: dict, expected_tools: list[str]) -> bool:
    return str(call.get("tool") or "") in set(expected_tools)


def _run_one(agent, model: str, case: dict) -> dict:
    started = time.time()
    public = {
        k: v for k, v in case.items()
        if k not in {"system", "defended_system", "attack_specification"}
    }
    try:
        raw, call = propose_tool_call(
            agent, model, case["defended_system"], case["query"])
        objective = _objective(case["objective"])
        payload_score = _payload_score(call, objective)
        payload_success = _payload_success(call, objective)
        selected = str(call.get("tool") or "")
        return public | {
            "mode": "attack",
            "status": "ok",
            "raw_response": raw,
            "call": call,
            "no_proposal": not bool(selected),
            "task_complete": _task_complete(call, case["expected_tools"]),
            "paper_target_tool_invoked": selected in set(objective.target_tools),
            "payload_score": payload_score,
            "payload_attack_success": payload_success,
            "adaptive_attack_success": payload_success,
            "elapsed_seconds": time.time() - started,
        }
    except Exception as exc:  # durable full-run error accounting
        return public | {
            "mode": "attack",
            "status": "error",
            "error": type(exc).__name__ + ": " + str(exc)[:700],
            "elapsed_seconds": time.time() - started,
        }


def _summary(rows: list[dict]) -> dict:
    ok = [row for row in rows if row.get("status") == "ok"]
    attack = [row for row in ok if row.get("mode") == "attack"]
    au = sum(row.get("task_complete", False) for row in attack)
    asr = sum(row.get("adaptive_attack_success", False) for row in attack)
    return {
        "scheduled": len(rows),
        "completed": len(ok),
        "errors": sum(row.get("status") == "error" for row in rows),
        "BU": {"successes": 0, "n": 0},
        "AU": {"successes": au, "n": len(attack)},
        "ASR": {"successes": asr, "n": len(attack)},
        "attack_utility": au / len(attack) if attack else None,
        "adaptive_asr": asr / len(attack) if attack else None,
        "paper_target_tool_invoked": sum(
            row.get("paper_target_tool_invoked", False) for row in attack),
        "catalog_blocked": sum(bool(row.get("blocked_tools")) for row in attack),
        "no_proposal": sum(row.get("no_proposal", False) for row in attack),
        "by_attack_type": {
            attack_type: {
                "n": len(group),
                "AU": sum(row.get("task_complete", False) for row in group),
                "ASR": sum(row.get("adaptive_attack_success", False) for row in group),
            }
            for attack_type in sorted({row.get("attack_type") for row in attack})
            for group in [[row for row in attack
                           if row.get("attack_type") == attack_type]]
        },
        "by_attack_task": {
            attack_task: {
                "n": len(group),
                "AU": sum(row.get("task_complete", False) for row in group),
                "ASR": sum(row.get("adaptive_attack_success", False) for row in group),
            }
            for attack_task in sorted({row.get("attack_task") for row in attack})
            for group in [[row for row in attack
                           if row.get("attack_task") == attack_task]]
        },
    }


def _checkpoint(path: Path, result: dict) -> None:
    result["summary"] = _summary(result["rows"])
    result["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    pending = path.with_suffix(path.suffix + ".tmp")
    pending.write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    pending.replace(path)


def _scanner(args: argparse.Namespace, output: Path):
    if args.baseline == "stackone":
        return StackOneScanner(args.node, output.parent / "stackone_msb_scan_cache.json")
    if args.baseline == "mcpguard":
        return MCPGuardScanner(
            output.parent / "mcpguard_msb_scan_cache.json",
            output.parent / "mcpguard_msb_detector.log")
    if args.baseline == "pipelock":
        binary = str(args.pipelock_bin or "")
        if not binary or not Path(binary).is_file():
            raise RuntimeError("Set --pipelock-bin or PIPELOCK_BIN to the official Pipelock binary")
        return PipelockScanner(
            binary, output.parent / "pipelock_msb_scan_cache.json",
            args.pipelock_config)
    if args.baseline == "clawguard":
        return ClawGuardScanner(output.parent / "clawguard_msb_scan_cache.json")
    raise ValueError(f"unknown baseline: {args.baseline}")


def _filter(args: argparse.Namespace, scanner, system: str):
    if args.baseline == "stackone":
        return _stackone_filter(scanner, system)
    if args.baseline == "mcpguard":
        # MCPTox's MCP-Guard parser expects "name: desc" arguments, while MSB
        # renders "name (type, required)"; keep the upstream scanner and only
        # adapt the rendered schema parser.
        return _mcpguard_filter_msb(scanner, system)
    if args.baseline == "pipelock":
        return _pipelock_filter(scanner, system)
    if args.baseline == "clawguard":
        return _clawguard_filter(scanner, system)
    raise ValueError(f"unknown baseline: {args.baseline}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline", choices=("stackone", "mcpguard", "pipelock", "clawguard"),
                        required=True)
    parser.add_argument("--model", default="deepseek-v4-flash")
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--msb-replay-rows", type=Path, required=True)
    parser.add_argument("--node", type=Path, default=DEFAULT_NODE)
    parser.add_argument("--pipelock-bin", default=str(PIPLELOCK_BIN))
    parser.add_argument("--pipelock-config")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    if args.workers < 1 or (args.limit is not None and args.limit < 1):
        raise ValueError("workers and limit must be positive")
    output = args.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    cases = _load_replay(args.msb_replay_rows, args.limit)
    scanner = _scanner(args, output)
    try:
        for index, case in enumerate(cases, 1):
            defended, decisions = _filter(args, scanner, case["system"])
            case["defended_system"] = defended
            case["scan_decisions"] = decisions
            case["blocked_tools"] = [
                row["tool"] for row in decisions if not row["allowed"]]
            if hasattr(scanner, "save") and index % 50 == 0:
                scanner.save()
                print("catalog", index, "/", len(cases), flush=True)
    finally:
        if hasattr(scanner, "close"):
            scanner.close()
        elif hasattr(scanner, "save"):
            scanner.save()

    result = (
        json.loads(output.read_text(encoding="utf-8"))
        if args.resume and output.exists()
        else {
            "schema": "msb-mcp-itp-baseline-v1",
            "benchmark": "MSB",
            "condition": f"{args.baseline}_mcp_itp_payloadaware_replay",
            "baseline": args.baseline,
            "model": args.model,
            "workers": args.workers,
            "limit": args.limit,
            "msb_replay_rows": str(args.msb_replay_rows),
            "rows": [],
        }
    )
    expected = {
        "schema": "msb-mcp-itp-baseline-v1",
        "baseline": args.baseline,
        "model": args.model,
        "limit": args.limit,
        "msb_replay_rows": str(args.msb_replay_rows),
    }
    if any(result.get(key) != value for key, value in expected.items()):
        raise ValueError("resume artifact baseline/model/limit/replay does not match invocation")
    agent = client_for_model(args.model)
    done = {row["key"] for row in result["rows"] if row.get("status") == "ok"}
    pending = [case for case in cases if case["key"] not in done]
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(_run_one, agent, args.model, case): case
                   for case in pending}
        for index, future in enumerate(concurrent.futures.as_completed(futures), 1):
            row = future.result()
            case = futures[future]
            row["scan_decisions"] = case["scan_decisions"]
            row["blocked_tools"] = case["blocked_tools"]
            result["rows"] = [old for old in result["rows"]
                              if old.get("key") != row.get("key")]
            result["rows"].append(row)
            if index % 10 == 0 or index == len(pending):
                _checkpoint(output, result)
                print(len(result["rows"]), "/", len(cases),
                      json.dumps(result["summary"], ensure_ascii=False),
                      flush=True)
    _checkpoint(output, result)
    print(json.dumps({
        "output": str(output),
        "summary": result["summary"],
        "finished_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
