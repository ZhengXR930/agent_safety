"""Fresh two-phase AgentDojo rerun for unified Progent and CaMeL baselines."""
from __future__ import annotations

import argparse
import json
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path


SUITES = ("banking", "slack", "travel", "workspace")


def _run_job(name: str, command: list[str], log_root: Path) -> dict:
    started = time.time()
    log_path = log_root / f"{name}.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as stream:
        stream.write("\nCOMMAND " + json.dumps(command) + "\n")
        stream.flush()
        result = subprocess.run(command, stdout=stream, stderr=subprocess.STDOUT)
    return {
        "job": name,
        "returncode": result.returncode,
        "elapsed_seconds": round(time.time() - started, 3),
        "log": str(log_path),
    }


def _write_status(path: Path, state: dict) -> None:
    temporary = path.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(state, indent=2), encoding="utf-8")
    temporary.replace(path)


def _run_phase(
    phase: str,
    jobs: list[tuple[str, list[str]]],
    workers: int,
    log_root: Path,
    state: dict,
    status_path: Path,
) -> bool:
    with ThreadPoolExecutor(max_workers=workers) as pool:
        pending = {
            pool.submit(_run_job, name, command, log_root): name
            for name, command in jobs
        }
        for future in as_completed(pending):
            record = future.result()
            record["phase"] = phase
            state["jobs"][record["job"]] = record
            _write_status(status_path, state)
            print(json.dumps(record), flush=True)
    return all(state["jobs"][name]["returncode"] == 0 for name, _ in jobs)


def _common(suite: str, model: str, manifest_root: Path) -> list[str]:
    return [
        "--suite", suite,
        "--pair-manifest", str(manifest_root / f"{suite}_pairs.json"),
        "--agent-model", model,
        "--policy-model", model,
    ]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-root", required=True)
    parser.add_argument(
        "--manifest-root", default="results/agentdojo_v29_full_20260722/manifests"
    )
    parser.add_argument("--model", default="deepseek-v4-flash")
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()

    root = Path(args.output_root)
    manifest_root = Path(args.manifest_root)
    log_root = Path("logs") / root.name
    root.mkdir(parents=True, exist_ok=True)
    status_path = root / "matrix_status.json"
    state = {
        "schema": "agentdojo-unified-progent-camel-v1",
        "model": args.model,
        "workers": args.workers,
        "jobs": {},
    }
    _write_status(status_path, state)

    # Build and freeze every DeepSeek-authored initial policy before attacks.
    phase_one: list[tuple[str, list[str]]] = []
    for suite in SUITES:
        phase_one.append((f"progent_clean_{suite}", [
            "python3", "-m", "code.run_progent_clean_suite",
            "--defense", "progent", *_common(suite, args.model, manifest_root),
            "--progent-cache-label", args.model,
            "--output", str(root / "progent" / f"{suite}_clean.json"), "--resume",
        ]))
    if not _run_phase(
        "progent_cache_and_clean", phase_one, args.workers, log_root, state, status_path
    ):
        state["status"] = "failed_progent_clean_gate"
        _write_status(status_path, state)
        raise SystemExit(1)

    phase_two: list[tuple[str, list[str]]] = []
    for suite in SUITES:
        common = _common(suite, args.model, manifest_root)
        phase_two.append((f"progent_attack_{suite}", [
            "python3", "-m", "code.run_progent_attack_suite",
            "--defense", "progent", *common,
            "--progent-cache-label", args.model, "--attack", "direct",
            "--output", str(root / "progent" / f"{suite}_attack.json"), "--resume",
        ]))
        phase_two.append((f"camel_clean_{suite}", [
            "python3", "-m", "code.run_progent_clean_suite",
            "--defense", "camel", *common,
            "--output", str(root / "camel" / f"{suite}_clean.json"), "--resume",
        ]))
        phase_two.append((f"camel_attack_{suite}", [
            "python3", "-m", "code.run_progent_attack_suite",
            "--defense", "camel", *common, "--attack", "direct",
            "--output", str(root / "camel" / f"{suite}_attack.json"), "--resume",
        ]))
    ok = _run_phase("full", phase_two, args.workers, log_root, state, status_path)
    state["status"] = "complete" if ok else "complete_with_failures"
    _write_status(status_path, state)
    raise SystemExit(0 if ok else 1)


if __name__ == "__main__":
    main()
