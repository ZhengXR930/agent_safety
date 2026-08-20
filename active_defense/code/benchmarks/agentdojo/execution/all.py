"""Run one in-repository method over the frozen four-suite AgentDojo protocol."""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import subprocess
import sys


MODULES = {
    "ours": "code.benchmarks.agentdojo.execution.ours",
    "wrap_only": "code.benchmarks.agentdojo.execution.ours",
    "plant_only": "code.benchmarks.agentdojo.execution.ours",
    "undefended": "code.benchmarks.agentdojo.execution.undefended",
    "drift": "code.benchmarks.agentdojo.execution.native",
    "camel": "code.benchmarks.agentdojo.execution.native",
    "progent": "code.benchmarks.agentdojo.execution.native",
    "melon": "code.benchmarks.agentdojo.execution.melon",
    "spotlighting": "code.benchmarks.agentdojo.execution.native",
    "tool_filter": "code.benchmarks.agentdojo.execution.native",
    "agentshield": "code.benchmarks.agentdojo.execution.agentshield",
}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--method", required=True, choices=tuple(MODULES))
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--agent-model", default="deepseek-v4-flash")
    parser.add_argument("--defense-model")
    parser.add_argument("--attack", default="important_instructions")
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--resume", action="store_true")
    args, extra = parser.parse_known_args()

    benchmark = Path(__file__).resolve().parents[1]
    contracts = Path(__file__).resolve().parents[3] / "ours/contracts/agentdojo"

    def command(suite: str) -> list[str]:
        value = [
            sys.executable, "-m", MODULES[args.method],
            "--suite", suite,
            "--pair-manifest", str(benchmark / "data" / f"{suite}_pairs.json"),
            "--output", str(args.output_root / f"{suite}.json"),
            "--agent-model", args.agent_model,
            "--attack", args.attack,
        ]
        if args.method in {"drift", "camel", "progent", "spotlighting", "tool_filter"}:
            value.extend(["--defense", args.method])
        if args.method == "progent" and args.defense_model:
            value.extend(["--policy-model", args.defense_model])
        if args.method in {"ours", "wrap_only", "plant_only"}:
            value.extend(["--contract-file", str(contracts / f"{suite}.json")])
            overrides = contracts / f"task_overrides_{suite}.json"
            if overrides.is_file():
                value.extend(["--task-overrides", str(overrides)])
            value.extend([
                "--ablation-mode",
                {
                    "ours": "full",
                    "wrap_only": "wrap_only",
                    "plant_only": "plant_only",
                }[args.method],
            ])
            if args.defense_model:
                value.extend(["--contract-model", args.defense_model])
        if args.resume:
            value.append("--resume")
        return [*value, *extra]

    args.output_root.mkdir(parents=True, exist_ok=True)
    suites = ("banking", "slack", "travel", "workspace")
    with ThreadPoolExecutor(max_workers=min(args.workers, len(suites))) as pool:
        futures = [pool.submit(subprocess.run, command(suite), check=True)
                   for suite in suites]
        for future in futures:
            future.result()


if __name__ == "__main__":
    main()
