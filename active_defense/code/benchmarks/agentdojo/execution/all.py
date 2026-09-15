"""Run one in-repository method over the frozen four-suite AgentDojo protocol."""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import subprocess
import sys

from code.benchmarks.agentdojo.execution.registry import METHODS


SUITES = ("banking", "slack", "travel", "workspace")


def suite_command(args: argparse.Namespace, extra: list[str], suite: str) -> list[str]:
    """Build one suite command from the canonical method registry."""
    spec = METHODS[args.method]
    spec.require_runnable(args.method)
    benchmark = Path(__file__).resolve().parents[1]
    contracts = Path(__file__).resolve().parents[3] / "ours/contracts/agentdojo"
    value = [
        sys.executable, "-m", spec.module,
        "--suite", suite,
        "--pair-manifest", str(benchmark / "data" / f"{suite}_pairs.json"),
        "--output", str(args.output_root / f"{suite}.json"),
        "--agent-model", args.agent_model,
        "--attack", args.attack,
    ]
    if spec.native_defense:
        value.extend(["--defense", spec.native_defense])
    if spec.defense_model_flag and args.defense_model:
        value.extend([spec.defense_model_flag, args.defense_model])
    if spec.contract_file:
        value.extend([
            "--contract-file", str(contracts / f"{suite}.json"),
        ])
        overrides = contracts / f"task_overrides_{suite}.json"
        if overrides.is_file():
            value.extend(["--task-overrides", str(overrides)])
    if args.resume:
        value.append("--resume")
    return [*value, *extra]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--method", required=True, choices=tuple(METHODS))
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--agent-model", default="deepseek-v4-flash")
    parser.add_argument("--defense-model")
    parser.add_argument("--attack", default="important_instructions")
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument(
        "--suites",
        default=",".join(SUITES),
        help="comma-separated suite subset; manifests still come from the adapter",
    )
    parser.add_argument("--resume", action="store_true")
    args, extra = parser.parse_known_args()

    args.output_root.mkdir(parents=True, exist_ok=True)
    suites = tuple(part.strip() for part in args.suites.split(",") if part.strip())
    unknown = set(suites) - set(SUITES)
    if not suites or unknown:
        parser.error(f"invalid --suites value; unknown={sorted(unknown)}")
    with ThreadPoolExecutor(max_workers=min(args.workers, len(suites))) as pool:
        futures = [pool.submit(
            subprocess.run, suite_command(args, extra, suite), check=True
        ) for suite in suites]
        for future in futures:
            future.result()


if __name__ == "__main__":
    main()
