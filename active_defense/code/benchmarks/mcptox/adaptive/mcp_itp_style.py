"""MCP-ITP-style smoke execution over frozen MCPTox cases.

This is not the official MCP-ITP implementation. It operationalizes the shared
implicit-tool-poisoning threat model on our frozen MCPTox data while we do not
have a public MCP-ITP repository: poison metadata is present in the tool
catalog, the target proposes one tool call, and the shared MCPTox judge scores
task completion and malicious success.
"""
from __future__ import annotations

import argparse
import concurrent.futures
import json
import threading
import time
from pathlib import Path

from code.benchmarks.mcptox.protocol_runtime import (
    judge_call,
    load_cases,
    propose_tool_call,
    protocol_identity,
)
from code.core.client import client_for_model


_WRITE_LOCK = threading.Lock()


def _run_one(agent, agent_model: str, evaluator, evaluator_model: str,
             case: dict, mode: str) -> dict:
    started = time.time()
    try:
        raw, call = propose_tool_call(
            agent, agent_model, case["system"], case["query"])
        verdict = judge_call(evaluator, evaluator_model, case, call, mode == "attack")
        poison_tool = str(case.get("poison_tool") or "")
        return {
            **{k: v for k, v in case.items()
               if k not in {"system", "clean_system", "attack_specification"}},
            "mode": mode,
            "status": "ok",
            "raw_response": raw,
            "call": call,
            "poison_tool_invoked": bool(
                poison_tool and str(call.get("tool") or "") == poison_tool),
            "mcp_itp_style": True,
            **verdict,
            "elapsed_seconds": time.time() - started,
        }
    except Exception as exc:  # noqa: BLE001 - durable smoke accounting
        return {
            **{k: v for k, v in case.items()
               if k not in {"system", "clean_system", "attack_specification"}},
            "mode": mode,
            "status": "error",
            "error": type(exc).__name__ + ": " + str(exc)[:500],
            "elapsed_seconds": time.time() - started,
        }


def _summary(rows: list[dict]) -> dict:
    ok = [row for row in rows if row.get("status") == "ok"]
    n = len(ok)
    attacks = [row for row in ok if row.get("mode") == "attack"]
    clean = [row for row in ok if row.get("mode") == "clean"]
    return {
        "scheduled": len(rows),
        "completed": n,
        "errors": sum(row.get("status") == "error" for row in rows),
        "task_success": sum(row.get("task_complete", False) for row in ok),
        "utility": (sum(row.get("task_complete", False) for row in ok) / n if n else None),
        "attack_success": sum(row.get("malicious_success", False) for row in attacks),
        "asr": (
            sum(row.get("malicious_success", False) for row in attacks) / len(attacks)
            if attacks else None
        ),
        "clean_task_success": sum(row.get("task_complete", False) for row in clean),
        "poison_tool_invoked": sum(row.get("poison_tool_invoked", False) for row in attacks),
    }


def _checkpoint(path: Path, result: dict) -> None:
    with _WRITE_LOCK:
        result["summary"] = _summary(result["rows"])
        result["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
        pending = path.with_suffix(path.suffix + ".tmp")
        pending.write_text(json.dumps(result, ensure_ascii=False, indent=2),
                           encoding="utf-8")
        pending.replace(path)


def _select_cases(split: str, limit: int | None) -> list[tuple[str, dict]]:
    clean, attack = load_cases()
    if split == "clean":
        selected = [("clean", row) for row in clean]
    elif split == "attack":
        selected = [("attack", row) for row in attack]
    else:
        selected = [("clean", row) for row in clean] + [("attack", row) for row in attack]
    return selected[:limit] if limit is not None else selected


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="deepseek-v4-flash")
    parser.add_argument("--evaluation-model", default="gpt-5.4-2026-03-05")
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--split", choices=["attack", "clean", "both"], default="attack")
    parser.add_argument("--output", required=True)
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    if args.workers < 1 or (args.limit is not None and args.limit < 1):
        raise ValueError("workers and limit must be positive")

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    jobs = _select_cases(args.split, args.limit)
    result = (
        json.loads(output.read_text(encoding="utf-8"))
        if args.resume and output.exists()
        else {
            "benchmark": "MCPTox",
            "method": "mcp_itp_style",
            "official_implementation": False,
            "model": args.model,
            "evaluation_model": args.evaluation_model,
            "split": args.split,
            "limit": args.limit,
            "protocol": protocol_identity(),
            "rows": [],
        }
    )
    done = {(row.get("mode"), row.get("key")) for row in result["rows"]
            if row.get("status") == "ok"}
    pending = [(mode, case) for mode, case in jobs
               if (mode, case["key"]) not in done]
    agent = client_for_model(args.model)
    evaluator = client_for_model(args.evaluation_model)

    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
        future_map = {
            pool.submit(_run_one, agent, args.model, evaluator,
                        args.evaluation_model, case, mode): (mode, case)
            for mode, case in pending
        }
        for index, future in enumerate(concurrent.futures.as_completed(future_map), 1):
            row = future.result()
            result["rows"] = [
                old for old in result["rows"]
                if not (old.get("mode") == row.get("mode") and old.get("key") == row.get("key"))
            ]
            result["rows"].append(row)
            if index % 5 == 0 or index == len(pending):
                _checkpoint(output, result)
                print(json.dumps({
                    "done": len(result["rows"]),
                    "scheduled": len(jobs),
                    "summary": result["summary"],
                }, ensure_ascii=False), flush=True)

    _checkpoint(output, result)
    print(json.dumps({"output": str(output), "summary": result["summary"]},
                     ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
