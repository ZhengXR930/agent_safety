"""Checkpointed full fresh-agent MCPTox evaluation for the current defense."""
from __future__ import annotations

import argparse
import concurrent.futures
import json
import threading
import time
from pathlib import Path

from code.defense.plant import PlantPlacementAgent
from code.internal_client import client_for_model
from code.run_mcp_pilot import RuntimeCache, _mcptox_once
from code.run_mcptox_undefended import ROOT, _cases, _judge


def _pilot_row(case: dict, clean_systems: dict[str, str]) -> dict:
    return {"server": case["server"], "query": case["query"],
            "clean_system": clean_systems[case["server"]],
            "attack_system": case.get("system", clean_systems[case["server"]]),
            "poison_tool": case.get("poison_tool", ""),
            "paradigm": case.get("paradigm"),
            "attack_specification": case.get("attack_specification", "")}


def _source_clean_systems() -> dict[str, str]:
    from code.run_mcp_pilot import MCPTox
    data = json.loads(MCPTox.read_text(encoding="utf-8"))
    return {server["server_name"]: server["clean_system_promot"]
            for server in data["servers"].values()}


class WorkerState:
    def __init__(self, args, cache_root: Path):
        self.args, self.cache_root, self.local = args, cache_root, threading.local()

    def get(self):
        if not hasattr(self.local, "clients"):
            agent = client_for_model(self.args.model)
            contract = client_for_model(self.args.contract_model)
            plant = client_for_model(self.args.plant_model)
            evaluator = client_for_model(self.args.evaluation_model)
            thread_root = self.cache_root / str(threading.get_ident())
            cache = RuntimeCache(contract, self.args.contract_model, thread_root,
                                 trusted_manifest=self.args.trusted_manifest)
            self.local.clients = (agent, cache, plant, evaluator)
        return self.local.clients


def _run_one(state: WorkerState, clean_systems: dict[str, str], case: dict,
             mode: str) -> dict:
    started = time.time()
    agent, cache, plant, evaluator = state.get()
    attacked = mode == "attack"
    try:
        row = _pilot_row(case, clean_systems)
        defended = _mcptox_once(
            agent, state.args.model, row, attacked, cache=cache,
            plant_client=plant, plant_model=state.args.plant_model,
            score_attack=False)
        verdict = _judge(evaluator, state.args.evaluation_model, case,
                         defended["call"], attacked)
        task_complete = defended["committed"] and verdict["task_complete"]
        malicious_success = defended["committed"] and verdict["malicious_success"]
        return {k: v for k, v in case.items() if k not in {"system", "attack_specification"}} | {
            "mode": mode, "status": "ok", **defended,
            "task_complete": task_complete, "malicious_success": malicious_success,
            "attack_success": malicious_success,
            "no_proposal": defended["route"] == "no_proposal",
            "evaluator_response": verdict["evaluator_response"],
            "elapsed_seconds": time.time() - started,
        }
    except Exception as exc:  # noqa: BLE001 - durable error accounting
        return {k: v for k, v in case.items() if k not in {"system", "attack_specification"}} | {
            "mode": mode, "status": "error",
            "error": type(exc).__name__ + ": " + str(exc)[:500],
            "elapsed_seconds": time.time() - started}


def _summary(rows: list[dict]) -> dict:
    ok = [row for row in rows if row.get("status") == "ok"]
    n = len(ok)
    incidents = [row for row in ok if row.get("route") in {"approval", "auditor"}]
    return {"rows": len(rows), "completed": n,
            "errors": sum(row.get("status") == "error" for row in rows),
            "task_success": sum(row.get("task_complete", False) for row in ok),
            "utility": (sum(row.get("task_complete", False) for row in ok) / n if n else None),
            "attack_success": sum(row.get("malicious_success", False) for row in ok),
            "asr": (sum(row.get("malicious_success", False) for row in ok) / n if n else None),
            "incidents": len(incidents),
            "no_proposal": sum(row.get("no_proposal", False) for row in ok),
            "plant_deployments": sum(row.get("plants_deployed", 0) for row in ok),
            "plant_commitments": sum(row.get("plant_commitments", 0) for row in ok)}


def _checkpoint(path: Path, result: dict) -> None:
    result["clean_summary"] = _summary(result["clean"])
    result["attack_summary"] = _summary(result["attack"])
    result["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    pending = path.with_suffix(path.suffix + ".tmp")
    pending.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    pending.replace(path)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="deepseek-chat")
    parser.add_argument("--contract-model", default="gpt-5.5-2026-04-24")
    parser.add_argument("--plant-model", default="deepseek-chat")
    parser.add_argument("--evaluation-model", default="gpt-5.5-2026-04-24")
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--output", default="experiment_stage/mcptox_ours_full_20260720.json")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--trusted-manifest", type=Path)
    parser.add_argument("--select-cells", type=Path,
                        help="Registry JSON containing utility_loss_coverage.cells")
    parser.add_argument("--clean-only", action="store_true")
    args = parser.parse_args()
    if args.workers < 1 or (args.limit is not None and args.limit < 1):
        raise ValueError("workers and limit must be positive")
    clean_cases, attack_cases = _cases(None)
    if args.select_cells:
        selection = json.loads(args.select_cells.read_text(encoding="utf-8"))
        cells = (selection.get("utility_loss_coverage") or {}).get("cells") or []
        selected = {(str(row["server"]), str(row["query"])) for row in cells}
        clean_cases = [row for row in clean_cases
                       if (str(row["server"]), str(row["query"])) in selected]
        attack_cases = []
    if args.limit is not None:
        clean_cases, attack_cases = clean_cases[:args.limit], attack_cases[:args.limit]
    if args.clean_only:
        attack_cases = []
    clean_systems = _source_clean_systems()
    output = ROOT / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    result = (json.loads(output.read_text(encoding="utf-8"))
              if args.resume and output.exists() else {
                  "benchmark": "MCPTox", "condition": "ours", "model": args.model,
                  "contract_model": args.contract_model, "plant_model": args.plant_model,
                  "evaluation_model": args.evaluation_model, "workers": args.workers,
                  "limit": args.limit, "clean": [], "attack": []})
    state = WorkerState(args, ROOT / "experiment_stage/mcptox_ours_full_plan_cache_20260720")
    for mode, cases in (("clean", clean_cases), ("attack", attack_cases)):
        done = {row["key"] for row in result[mode] if row.get("status") == "ok"}
        pending_cases = [case for case in cases if case["key"] not in done]
        with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
            futures = {pool.submit(_run_one, state, clean_systems, case, mode): case
                       for case in pending_cases}
            for index, future in enumerate(concurrent.futures.as_completed(futures), 1):
                row = future.result()
                result[mode] = [old for old in result[mode] if old["key"] != row["key"]]
                result[mode].append(row)
                if index % 5 == 0 or index == len(pending_cases):
                    _checkpoint(output, result)
                    print(mode, len(result[mode]), "/", len(cases),
                          json.dumps(_summary(result[mode]), ensure_ascii=False), flush=True)
    _checkpoint(output, result)
    print(json.dumps({"output": str(output), "clean": result["clean_summary"],
                      "attack": result["attack_summary"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
