from __future__ import annotations

import argparse
import csv
import json
import os
from pathlib import Path
import subprocess
import sys

from code.core.client import read_config_key


REPO = Path(__file__).resolve().parents[4]
AGENT_SAFETY = REPO.parent
ASB_ROOT = REPO / "baseline" / "ASB"
DATA = REPO / "code" / "benchmarks" / "asb_opi" / "data"


def _transport_model(model: str) -> str:
    # The vendored ASB registry only knows deepseek-chat; our benchmark label
    # remains deepseek-v4-flash, matching the rest of the paper experiments.
    if model == "deepseek-v4-flash":
        return "deepseek-chat"
    return model


def _env_for_model(model: str) -> dict[str, str]:
    env = os.environ.copy()
    if model.startswith("deepseek"):
        key = read_config_key("DEEPSEEK_API_KEY", root=AGENT_SAFETY)
        if not key:
            raise RuntimeError("Missing DEEPSEEK_API_KEY")
        env["OPENAI_BASE_URL"] = "https://api.deepseek.com"
        env["OPENAI_API_KEY"] = key
    return env


def _write_clean_tool_subset(path: Path) -> None:
    clean = json.loads((DATA / "clean_cases.json").read_text(encoding="utf-8"))
    tools = json.loads((DATA / "tools.json").read_text(encoding="utf-8"))["attacker_tools"]
    by_agent = {}
    for tool in tools:
        by_agent.setdefault(tool["Corresponding Agent"], tool)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in clean:
            tool = by_agent[row["agent_name"]]
            handle.write(json.dumps(tool, ensure_ascii=False) + "\n")


def _run_asb(command: list[str], env: dict[str, str], log_path: Path) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("w", encoding="utf-8") as log:
        subprocess.run(command, cwd=ASB_ROOT, env=env, stdout=log, stderr=subprocess.STDOUT, check=True)


def _rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _count(rows: list[dict[str, str]], column: str) -> int:
    return sum(str(row.get(column, "")).strip() in {"1", "true", "True"} for row in rows)


def _write_metadata(output: Path, model: str, transport_model: str, clean_rows: list[dict[str, str]], attack_rows: list[dict[str, str]]) -> None:
    metadata = {
        "schema": "canonical-experiment-result-v2",
        "benchmark": "ASB-OPI",
        "method": "Undefended",
        "target_model": model,
        "transport_model": transport_model,
        "defense_model": model,
        "judge_model": "ASB native string/tool scorer; refusal judge ignored",
        "coverage": {"clean": len(clean_rows), "attack": len(attack_rows), "attack_utility": len(attack_rows)},
        "metrics": {
            "BU": {"successes": _count(clean_rows, "Original Task Successful"), "n": len(clean_rows)},
            "AU": {"successes": _count(attack_rows, "Original Task Successful"), "n": len(attack_rows)},
            "ASR": {"successes": _count(attack_rows, "Attack Successful"), "n": len(attack_rows)},
        },
        "artifacts": {
            "clean_csv": str(output / "clean_10.csv"),
            "attack_csv": str(output / "attack_400.csv"),
            "clean_log": str(output / "clean_10.log"),
            "attack_log": str(output / "attack_400.log"),
        },
        "notes": [
            "BU/AU/ASR follow code/benchmarks/asb_opi/protocol.json metric_policy.",
            "ASB refusal judge is not used because it is a separate diagnostic and may call a different model.",
        ],
    }
    (output / "METADATA.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="deepseek-v4-flash")
    parser.add_argument("--output", required=True)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--max-new-tokens", type=int, default=512)
    parser.add_argument("--skip-clean", action="store_true")
    parser.add_argument("--skip-attack", action="store_true")
    args = parser.parse_args()

    output = Path(args.output).resolve()
    output.mkdir(parents=True, exist_ok=True)
    transport = _transport_model(args.model)
    env = _env_for_model(transport)
    clean_csv = output / "clean_10.csv"
    attack_csv = output / "attack_400.csv"
    clean_tools = output / "clean_tools_one_per_agent.jsonl"
    _write_clean_tool_subset(clean_tools)

    if not args.skip_clean and not (args.resume and clean_csv.exists()):
        _run_asb([
            sys.executable, "main_attacker.py",
            "--llm_name", transport,
            "--max_new_tokens", str(args.max_new_tokens),
            "--attacker_tools_path", str(clean_tools),
            "--tasks_path", "data/agent_task.jsonl",
            "--tools_info_path", "data/all_normal_tools.jsonl",
            "--clean",
            "--task_num", "1",
            "--res_file", str(clean_csv),
        ], env, output / "clean_10.log")

    if not args.skip_attack and not (args.resume and attack_csv.exists()):
        _run_asb([
            sys.executable, "main_attacker.py",
            "--llm_name", transport,
            "--max_new_tokens", str(args.max_new_tokens),
            "--attacker_tools_path", "data/all_attack_tools.jsonl",
            "--tasks_path", "data/agent_task.jsonl",
            "--tools_info_path", "data/all_normal_tools.jsonl",
            "--observation_prompt_injection",
            "--attack_type", "context_ignoring",
            "--task_num", "1",
            "--res_file", str(attack_csv),
        ], env, output / "attack_400.log")

    clean_rows = _rows(clean_csv)
    attack_rows = _rows(attack_csv)
    _write_metadata(output, args.model, transport, clean_rows, attack_rows)
    print(json.dumps(json.loads((output / "METADATA.json").read_text(encoding="utf-8"))["metrics"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
