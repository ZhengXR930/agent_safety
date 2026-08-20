"""Checkpointed matched undefended control for all released MCPTox instances."""
from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import re
import threading
import time
from pathlib import Path

from code.core.client import chat, client_for_model
from code.benchmarks.mcptox.protocol_runtime import (
    judge_call as protocol_judge_call,
    load_cases as protocol_cases,
    propose_tool_call,
)
from code.benchmarks.mcptox.adaptive.mcp_itp import _objective_for_case


ROOT = Path(__file__).resolve().parents[1]
MCPTox = ROOT.parent / "benchmarks/MCPTox-Benchmark/response_all.json"
MCPTox_PURE = ROOT.parent / "benchmarks/MCPTox-Benchmark/pure_tool.json"
_WRITE_LOCK = threading.Lock()


def _official_label(row: dict, model_name: str = "DeepSeek-v3") -> str | None:
    for labels in row.get("online_result", {}).get("labeled_model_results", []):
        if model_name in labels:
            return labels[model_name]
    return None


def _poison_name(block: str) -> str:
    match = re.match(r"\s*Tool:\s*([^\n]+)", str(block or ""))
    return match.group(1).strip() if match else ""


def _specifications() -> dict[tuple[str, str, str], dict]:
    groups = json.loads(MCPTox_PURE.read_text(encoding="utf-8"))
    return {(row["server_name"], row["tool_name"], row["query"]): row
            for group in groups for row in group.values()}


def _cases(limit: int | None = None) -> tuple[list[dict], list[dict]]:
    return protocol_cases(None)


def _judge(evaluator, model: str, case: dict, call: dict, attacked: bool) -> dict:
    return protocol_judge_call(evaluator, model, case, call, attacked)


def _run_one(agent, agent_model: str, evaluator, evaluator_model: str,
             case: dict, mode: str) -> dict:
    started = time.time()
    try:
        raw, call = propose_tool_call(
            agent, agent_model, case["system"], case["query"])
        verdict = _judge(evaluator, evaluator_model, case, call, mode == "attack")
        return {k: v for k, v in case.items() if k not in {"system", "attack_specification"}} | {
            "mode": mode, "status": "ok", "raw_response": raw, "call": call,
            "no_proposal": not bool(call.get("tool")), **verdict,
            "elapsed_seconds": time.time() - started,
        }
    except Exception as exc:  # noqa: BLE001 - durable full-run error accounting
        return {k: v for k, v in case.items() if k not in {"system", "attack_specification"}} | {
            "mode": mode, "status": "error", "error": type(exc).__name__ + ": " + str(exc)[:500],
            "elapsed_seconds": time.time() - started,
        }


def _summary(rows: list[dict]) -> dict:
    ok = [row for row in rows if row.get("status") == "ok"]
    n = len(ok)
    return {"scheduled": len(rows), "completed": n,
            "errors": sum(row.get("status") == "error" for row in rows),
            "task_success": sum(row.get("task_complete", False) for row in ok),
            "utility": (sum(row.get("task_complete", False) for row in ok) / n if n else None),
            "attack_success": sum(row.get("malicious_success", False) for row in ok),
            "asr": (sum(row.get("malicious_success", False) for row in ok) / n if n else None),
            "no_proposal": sum(row.get("no_proposal", False) for row in ok)}


def _checkpoint(path: Path, result: dict) -> None:
    with _WRITE_LOCK:
        result["clean_summary"] = _summary(result["clean"])
        result["attack_summary"] = _summary(result["attack"])
        result["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
        pending = path.with_suffix(path.suffix + ".tmp")
        pending.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        pending.replace(path)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="deepseek-chat")
    parser.add_argument("--evaluation-model", default="gpt-5.5-2026-04-24")
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--case-id", action="append", default=[])
    parser.add_argument("--objective-kind",
                        choices=["all", "tool_hijack", "mcptox_judge"],
                        default="all",
                        help="filter attack cases by parsed MCP-ITP objective kind")
    parser.add_argument("--paradigm",
                        choices=["all", "Template-1", "Template-2", "Template-3"],
                        default="all",
                        help="filter attack cases by MCPTox official paradigm field")
    parser.add_argument("--output", required=True)
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    if args.workers < 1 or (args.limit is not None and args.limit < 1):
        raise ValueError("workers and limit must be positive")
    output = ROOT / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    clean_cases, attack_cases = _cases(args.limit)
    if args.objective_kind != "all":
        clean_cases = []
        attack_cases = [
            case for case in attack_cases
            if _objective_for_case(case).kind == args.objective_kind
        ]
    if args.paradigm != "all":
        clean_cases = []
        attack_cases = [
            case for case in attack_cases
            if str(case.get("paradigm")) == args.paradigm
        ]
    if args.case_id:
        wanted = set(args.case_id)
        clean_cases = [
            case for case in clean_cases
            if str(case.get("case_id")) in wanted or str(case.get("key")) in wanted
        ]
        attack_cases = [
            case for case in attack_cases
            if str(case.get("case_id")) in wanted or str(case.get("key")) in wanted
        ]
        if not clean_cases and not attack_cases:
            raise ValueError("no MCPTox cases matched --case-id")
    if args.limit is not None:
        clean_cases = clean_cases[:args.limit]
        attack_cases = attack_cases[:args.limit]
    result = (json.loads(output.read_text(encoding="utf-8"))
              if args.resume and output.exists() else {
                  "benchmark": "MCPTox", "condition": "undefended",
                  "model": args.model, "evaluation_model": args.evaluation_model,
                  "workers": args.workers, "limit": args.limit,
                  "objective_kind": args.objective_kind,
                  "paradigm": args.paradigm,
                  "clean": [], "attack": []})
    agent, evaluator = client_for_model(args.model), client_for_model(args.evaluation_model)
    for mode, cases in (("clean", clean_cases), ("attack", attack_cases)):
        done = {row["key"] for row in result[mode] if row.get("status") == "ok"}
        pending = [case for case in cases if case["key"] not in done]
        with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
            future_map = {pool.submit(_run_one, agent, args.model, evaluator,
                                      args.evaluation_model, case, mode): case
                          for case in pending}
            for index, future in enumerate(concurrent.futures.as_completed(future_map), 1):
                row = future.result()
                result[mode] = [old for old in result[mode] if old["key"] != row["key"]]
                result[mode].append(row)
                if index % 10 == 0 or index == len(pending):
                    _checkpoint(output, result)
                    print(mode, len(result[mode]), "/", len(cases),
                          json.dumps(_summary(result[mode]), ensure_ascii=False), flush=True)
    _checkpoint(output, result)
    print(json.dumps({"output": str(output), "clean": result["clean_summary"],
                      "attack": result["attack_summary"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
