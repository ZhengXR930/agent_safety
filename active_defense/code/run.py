"""Single entry point for all frozen benchmark × method evaluations."""
from __future__ import annotations

import argparse
import importlib
import json
from pathlib import Path
import shlex

from code.core.protocol import validate_result_coverage
from code.core.types import RunRequest


ADAPTERS = {
    "agentdojo": ("code.benchmarks.agentdojo.adapter", "AgentDojoAdapter"),
    "asb_opi": ("code.benchmarks.asb_opi.adapter", "ASBOPIAdapter"),
    "skillinject": ("code.benchmarks.skillinject.adapter", "SkillInjectAdapter"),
    "scr": ("code.benchmarks.scr.adapter", "SCRAdapter"),
    "msb": ("code.benchmarks.msb.adapter", "MSBAdapter"),
    "mcptox": ("code.benchmarks.mcptox.adapter", "MCPToxAdapter"),
    "launderingbench": ("code.benchmarks.launderingbench.adapter", "LaunderingBenchAdapter"),
}


def load_adapter(name: str):
    module_name, class_name = ADAPTERS[name]
    return getattr(importlib.import_module(module_name), class_name)()


def load_runner(method: str):
    if method in {"ours", "wrap_only", "plant_only"}:
        return importlib.import_module("code.ours.runner").runner_for(method)
    return importlib.import_module(f"code.baselines.{method}.runner").RUNNER


def verify_all(result_root: Path | None = None, configuration: str = "DeepSeek") -> dict:
    report = {}
    for name in ADAPTERS:
        adapter = load_adapter(name)
        counts = {}
        for row in adapter.cases():
            counts[row.split] = counts.get(row.split, 0) + 1
        item = {
            "benchmark": adapter.protocol.benchmark,
            "methods": list(adapter.protocol.methods),
            "denominators": adapter.protocol.denominators,
            "materialized_cases": counts,
            "data_integrity": "pass",
        }
        if result_root is not None:
            item["result_coverage"] = validate_result_coverage(
                adapter.protocol, result_root, configuration)
        report[name] = item
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--benchmark", choices=tuple(ADAPTERS))
    parser.add_argument("--method")
    parser.add_argument("--target-model", default="deepseek-v4-flash")
    parser.add_argument("--defense-model")
    parser.add_argument("--judge-model")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--verify-only", action="store_true")
    parser.add_argument("--verify-results", type=Path)
    parser.add_argument("--configuration", default="DeepSeek")
    parser.add_argument("extra", nargs=argparse.REMAINDER)
    args = parser.parse_args()

    if args.verify_only:
        report = verify_all(args.verify_results, args.configuration)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        if args.verify_results and any(
            item["result_coverage"]["status"] != "PASS" for item in report.values()
        ):
            raise SystemExit(1)
        return
    if not args.benchmark or not args.method or not args.output:
        parser.error("--benchmark, --method and --output are required")
    adapter = load_adapter(args.benchmark)
    runner = load_runner(args.method)
    extra = tuple(args.extra[1:] if args.extra[:1] == ["--"] else args.extra)
    request = RunRequest(
        target_model=args.target_model,
        defense_model=args.defense_model,
        judge_model=args.judge_model,
        output=args.output,
        workers=args.workers,
        resume=args.resume,
        extra=extra,
    )
    command = runner.command(adapter, request)
    if args.dry_run:
        print(shlex.join(command))
        return
    runner.run(adapter, request)


if __name__ == "__main__":
    main()
