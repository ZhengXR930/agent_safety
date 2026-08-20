"""Run AdapTools over AgentDojo methods through the unified protocol.

This module is intentionally a command generator around ``code.run``. It keeps
AdapTools comparable with our method and baselines by preserving the same
AgentDojo adapter, frozen pair manifests, and result schema used elsewhere.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys
import time


METHODS = (
    "ours",
    "undefended",
    "drift",
    "camel",
    "progent",
    "melon",
    "spotlighting",
    "tool_filter",
)

VARIANTS = (
    "context_note",
    "reconciliation",
    "audit_trail",
    "data_field",
    "soft_delegate",
    "task_bridge",
    "tool_plan",
    "topic_shift",
    "minimal",
)


def _split_csv(value: str, allowed: tuple[str, ...], label: str) -> tuple[str, ...]:
    items = tuple(item.strip() for item in value.split(",") if item.strip())
    unknown = sorted(set(items) - set(allowed))
    if unknown:
        raise ValueError(f"unknown {label}: {unknown}; expected values from {sorted(allowed)}")
    return items


def _command(args: argparse.Namespace, method: str, variant: str) -> list[str]:
    command = [
        sys.executable,
        "-m",
        "code.run",
        "--benchmark",
        "agentdojo",
        "--method",
        method,
        "--target-model",
        args.target_model,
        "--output",
        str(args.output_root / method / variant),
        "--workers",
        str(args.run_workers),
    ]
    if args.defense_model:
        command.extend(["--defense-model", args.defense_model])
    if args.resume:
        command.append("--resume")
    command.extend(["--", "--attack", "adaptools"])
    if args.max_pairs:
        command.extend(["--max-pairs", str(args.max_pairs)])
    command.extend(args.native_extra)
    return command


def _run_one(args: argparse.Namespace, method: str, variant: str) -> dict:
    started = time.time()
    log_path = args.output_root / "_logs" / f"{method}_{variant}.log"
    injection_log = args.output_root / method / variant / "injections.jsonl"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    injection_log.parent.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env["ADAPTOOLS_VARIANT"] = variant
    env["ADAPTOOLS_LOG"] = str(injection_log)
    if args.cache:
        env["ADAPTOOLS_CACHE"] = str(args.cache)
    if args.generator_model:
        env["ADAPTOOLS_GENERATOR_MODEL"] = args.generator_model
    command = _command(args, method, variant)
    with log_path.open("a", encoding="utf-8") as stream:
        stream.write("\nCOMMAND " + shlex.join(command) + "\n")
        stream.write("ADAPTOOLS_VARIANT " + variant + "\n")
        if args.cache:
            stream.write("ADAPTOOLS_CACHE " + str(args.cache) + "\n")
        if args.generator_model:
            stream.write("ADAPTOOLS_GENERATOR_MODEL " + args.generator_model + "\n")
        stream.flush()
        result = subprocess.run(
            command,
            env=env,
            stdout=stream,
            stderr=subprocess.STDOUT,
            check=False,
        )
    return {
        "method": method,
        "variant": variant,
        "returncode": result.returncode,
        "elapsed_seconds": round(time.time() - started, 3),
        "output": str(args.output_root / method / variant),
        "injection_log": str(injection_log),
        "log": str(log_path),
        "command": command,
        "cache": str(args.cache) if args.cache else None,
        "generator_model": args.generator_model,
    }


def _write_status(path: Path, status: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pending = path.with_suffix(path.suffix + ".tmp")
    pending.write_text(json.dumps(status, ensure_ascii=False, indent=2), encoding="utf-8")
    pending.replace(path)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--methods", default=",".join(METHODS))
    parser.add_argument("--variants", default="task_bridge")
    parser.add_argument("--target-model", default="deepseek-v4-flash")
    parser.add_argument("--defense-model")
    parser.add_argument("--cache", type=Path)
    parser.add_argument("--generator-model",
                        help="attack-side model used to generate the cache")
    parser.add_argument("--max-pairs", type=int, default=0)
    parser.add_argument("--workers", type=int, default=1,
                        help="outer method/variant concurrency")
    parser.add_argument("--run-workers", type=int, default=1,
                        help="workers passed to code.run for suite execution")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--continue-on-error", action="store_true")
    parser.add_argument("extra", nargs=argparse.REMAINDER,
                        help="extra native AgentDojo args after --")
    args = parser.parse_args()
    args.output_root = args.output_root.resolve()
    args.native_extra = tuple(args.extra[1:] if args.extra[:1] == ["--"] else args.extra)

    methods = _split_csv(args.methods, METHODS, "methods")
    variants = _split_csv(args.variants, VARIANTS, "variants")
    jobs = [(method, variant) for method in methods for variant in variants]

    if args.dry_run:
        for method, variant in jobs:
            env = f"ADAPTOOLS_VARIANT={variant}"
            if args.cache:
                env += f" ADAPTOOLS_CACHE={args.cache}"
            print(env, shlex.join(_command(args, method, variant)))
        return

    args.output_root.mkdir(parents=True, exist_ok=True)
    status_path = args.output_root / "adaptools_sweep_status.json"
    status = {
        "schema": "agentdojo-adaptools-sweep-v1",
        "methods": list(methods),
        "variants": list(variants),
        "target_model": args.target_model,
        "defense_model": args.defense_model,
        "cache": str(args.cache) if args.cache else None,
        "generator_model": args.generator_model,
        "max_pairs": args.max_pairs,
        "workers": args.workers,
        "run_workers": args.run_workers,
        "jobs": {},
    }
    _write_status(status_path, status)

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        pending = {
            pool.submit(_run_one, args, method, variant): (method, variant)
            for method, variant in jobs
        }
        for future in as_completed(pending):
            record = future.result()
            key = f"{record['method']}/{record['variant']}"
            status["jobs"][key] = record
            _write_status(status_path, status)
            print(json.dumps(record, ensure_ascii=False), flush=True)
            if record["returncode"] != 0 and not args.continue_on_error:
                raise SystemExit(record["returncode"])


if __name__ == "__main__":
    main()
