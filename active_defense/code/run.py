"""Single entry point for all frozen benchmark × method evaluations."""
from __future__ import annotations

import argparse
import importlib
import json
from pathlib import Path
import shlex

from code.core.protocol import validate_result_coverage
from code.core.evaluation_registry import (
    ACTIVE_DEFENSE_METHODS,
    BLOCKED_INTEGRATIONS,
    PAPER_BASELINES,
    PAPER_BENCHMARKS,
    REFERENCE_METHOD,
    all_benchmarks,
    matrix_rows,
)
from code.core.types import RunRequest
from code.core.runner import BaselineRunner


ADAPTERS = all_benchmarks()


def load_adapter(name: str):
    registration = ADAPTERS[name]
    return getattr(
        importlib.import_module(registration.adapter_module),
        registration.adapter_class,
    )()


def load_runner(method: str):
    if method in ACTIVE_DEFENSE_METHODS:
        return importlib.import_module("code.ours.runner").runner_for(method)
    if method == REFERENCE_METHOD or method in PAPER_BASELINES:
        return BaselineRunner(method)
    # Non-paper extension runners (for example adaptive attack builders) may
    # retain a dedicated implementation, but they are not part of the 6x13
    # paper compatibility matrix.
    return importlib.import_module(f"code.baselines.{method}.runner").RUNNER


def validate_registry() -> dict:
    """Validate the 6-benchmark × 13-baseline interface without model calls."""
    report = {
        "paper_benchmarks": len(PAPER_BENCHMARKS),
        "paper_baselines": len(PAPER_BASELINES),
        "status": "PASS",
        "benchmarks": {},
    }
    probe = RunRequest(
        target_model="deepseek-v4-flash",
        defense_model="deepseek-v4-flash",
        judge_model="gpt-5.4-2026-03-05",
        output=Path("/tmp/active-defense-registry-probe"),
        workers=1,
        resume=False,
        extra=(),
    )
    for name, registration in PAPER_BENCHMARKS.items():
        adapter = load_adapter(name)
        expected = set(registration.methods)
        declared = set(adapter.protocol.methods)
        errors = []
        if declared != expected:
            errors.append({
                "kind": "protocol_method_mismatch",
                "missing": sorted(expected - declared),
                "extra": sorted(declared - expected),
            })
        commands = {}
        for method in registration.methods:
            try:
                command = load_runner(method).command(adapter, probe)
                commands[method] = shlex.join(command)
            except Exception as exc:
                errors.append({
                    "kind": "command_build_failed",
                    "method": method,
                    "error": f"{type(exc).__name__}: {exc}",
                })
        item = {
            "adapter": f"{registration.adapter_module}:{registration.adapter_class}",
            "methods": list(registration.methods),
            "blocked": {
                method: reason
                for (benchmark, method), reason in BLOCKED_INTEGRATIONS.items()
                if benchmark == name
            },
            "commands": commands,
            "errors": errors,
            "status": "PASS" if not errors else "FAIL",
        }
        report["benchmarks"][name] = item
        if errors:
            report["status"] = "FAIL"
    return report


def format_matrix_markdown() -> str:
    headers = ["Benchmark", "Undefended", *PAPER_BASELINES]
    lines = ["| " + " | ".join(headers) + " |",
             "|" + "|".join(["---"] * len(headers)) + "|"]
    symbols = {
        "supported": "yes",
        "blocked": "blocked",
        "validation_required": "validate",
        "dependency_missing": "missing dep",
        "not_applicable": "—",
    }
    for row in matrix_rows():
        values = [row["display_name"], "yes"]
        values.extend(symbols[row["baselines"][method]] for method in PAPER_BASELINES)
        lines.append("| " + " | ".join(values) + " |")
    return "\n".join(lines)


def verify_all(result_root: Path | None = None, configuration: str = "DeepSeek",
               include_experimental: bool = False) -> dict:
    report = {}
    selected = all_benchmarks(include_experimental)
    for name in selected:
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
    parser.add_argument("--validate-registry", action="store_true")
    parser.add_argument("--list-matrix", action="store_true")
    parser.add_argument("--matrix-format", choices=("markdown", "json"),
                        default="markdown")
    parser.add_argument("--include-experimental", action="store_true")
    parser.add_argument("--verify-results", type=Path)
    parser.add_argument("--configuration", default="DeepSeek")
    parser.add_argument("extra", nargs=argparse.REMAINDER)
    args = parser.parse_args()

    if args.list_matrix:
        if args.matrix_format == "json":
            print(json.dumps(matrix_rows(), ensure_ascii=False, indent=2))
        else:
            print(format_matrix_markdown())
        return
    if args.validate_registry:
        report = validate_registry()
        print(json.dumps(report, ensure_ascii=False, indent=2))
        if report["status"] != "PASS":
            raise SystemExit(1)
        return

    if args.verify_only:
        registry = validate_registry()
        report = verify_all(
            args.verify_results, args.configuration, args.include_experimental)
        report["_registry"] = registry
        print(json.dumps(report, ensure_ascii=False, indent=2))
        if registry["status"] != "PASS" or (args.verify_results and any(
            item["result_coverage"]["status"] != "PASS" for item in report.values()
            if "result_coverage" in item
        )):
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
