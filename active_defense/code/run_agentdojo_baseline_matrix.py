"""Run the four-suite, five-baseline AgentDojo matrix with bounded concurrency."""
from __future__ import annotations

import argparse
import json
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path


SUITES = ("banking", "slack", "travel", "workspace")


def jobs(root: Path, manifest_root: Path):
    for suite in SUITES:
        manifest = manifest_root / f"{suite}_pairs.json"
        common = ["--suite", suite, "--pair-manifest", str(manifest),
                  "--agent-model", "deepseek-v4-flash"]
        yield f"tool_filter_{suite}", [
            "python3", "-m", "code.run_agentdojo_native_baseline",
            "--defense", "tool_filter", *common, "--attack", "direct",
            "--output", str(root / "tool_filter" / f"{suite}.json"), "--resume"]
        yield f"spotlighting_{suite}", [
            "python3", "-m", "code.run_agentdojo_native_baseline",
            "--defense", "spotlighting", *common, "--attack", "direct",
            "--output", str(root / "spotlighting" / f"{suite}.json"), "--resume"]
        yield f"melon_{suite}", [
            "python3", "-m", "code.run_agentdojo_melon", *common,
            "--attack", "direct", "--output", str(root / "melon" / f"{suite}.json"),
            "--resume"]
        for defense in ("progent", "camel"):
            defense_common = ["--policy-model", "deepseek-v4-flash"]
            if defense == "progent":
                defense_common += ["--progent-cache-label", "deepseek-v4-flash"]
            yield f"{defense}_clean_{suite}", [
                "python3", "-m", "code.run_progent_clean_suite",
                "--defense", defense, *common, *defense_common,
                "--output", str(root / defense / f"{suite}_clean.json"), "--resume"]
            yield f"{defense}_attack_{suite}", [
                "python3", "-m", "code.run_progent_attack_suite",
                "--defense", defense, *common, *defense_common,
                "--attack", "direct",
                "--output", str(root / defense / f"{suite}_attack.json"), "--resume"]


def run_one(name: str, command: list[str], log_root: Path) -> dict:
    started = time.time()
    log = log_root / f"{name}.log"
    log.parent.mkdir(parents=True, exist_ok=True)
    with log.open("a", encoding="utf-8") as stream:
        stream.write("\nCOMMAND " + json.dumps(command) + "\n")
        stream.flush()
        result = subprocess.run(command, stdout=stream, stderr=subprocess.STDOUT)
    return {"job": name, "returncode": result.returncode,
            "elapsed_seconds": round(time.time() - started, 3), "log": str(log)}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-root", required=True)
    parser.add_argument("--manifest-root", default=
                        "results/agentdojo_v29_full_20260722/manifests")
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()
    root = Path(args.output_root)
    log_root = Path("logs") / root.name
    root.mkdir(parents=True, exist_ok=True)
    matrix = list(jobs(root, Path(args.manifest_root)))
    state_path = root / "matrix_status.json"
    state = {"schema": "agentdojo-four-suite-five-baseline-v1",
             "workers": args.workers, "jobs": {}}
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        pending = {pool.submit(run_one, name, command, log_root): name
                   for name, command in matrix}
        for future in as_completed(pending):
            record = future.result()
            state["jobs"][record["job"]] = record
            temporary = state_path.with_suffix(".json.tmp")
            temporary.write_text(json.dumps(state, indent=2), encoding="utf-8")
            temporary.replace(state_path)
            print(json.dumps(record), flush=True)


if __name__ == "__main__":
    main()
