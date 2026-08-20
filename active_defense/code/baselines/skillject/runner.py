"""Wrapper for the official SkillJect implementation.

SkillJect is a skill-poisoning generator/evaluator built around OpenSandbox.
This runner intentionally keeps the official repository isolated under
baseline/SkillJect and exposes it through the unified active-defense CLI.
"""
from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

from code.core.adapter import BenchmarkAdapter
from code.core.types import RunRequest


REPO = Path(__file__).resolve().parents[3]
SKILLJECT_ROOT = REPO / "baseline" / "SkillJect"


class SkillJectRunner:
    method = "skillject"

    def command(self, adapter: BenchmarkAdapter, request: RunRequest) -> list[str]:
        if adapter.protocol.benchmark != "SkillInject":
            raise ValueError("SkillJect only applies to the SkillInject unit")
        config = _config_path(request)
        command = [
            "python",
            "run.py",
            "-c",
            str(config),
            "--max-attempts",
            _extra_value(request.extra, "--max-attempts", "1"),
            "--no-retry",
        ]
        skills = _extra_values(request.extra, "--skill")
        if not skills:
            skills = _extra_values(request.extra, "--skills")
        if skills:
            command.extend(["--skills", *skills])
        attack_types = _extra_values(request.extra, "--attack-type")
        if not attack_types:
            attack_types = _extra_values(request.extra, "--attack-types")
        if attack_types:
            command.extend(["--attack-types", *attack_types])
        if "--verbose" in request.extra:
            command.append("--verbose")
        return command

    def run(self, adapter: BenchmarkAdapter, request: RunRequest) -> None:
        if not SKILLJECT_ROOT.is_dir():
            raise RuntimeError(f"Official SkillJect repo is missing: {SKILLJECT_ROOT}")
        missing = _missing_runtime()
        if missing and "--allow-missing-runtime" not in request.extra:
            raise RuntimeError(
                "SkillJect official E2E requires OpenSandbox/Docker runtime; "
                f"missing: {', '.join(missing)}. Use --dry-run to inspect the "
                "command, or pass -- --allow-missing-runtime only for config-level "
                "experiments that you expect to fail before sandbox execution."
            )
        env = os.environ.copy()
        env.setdefault("SKILLJECT_OUTPUT_ROOT", str(request.output))
        subprocess.run(self.command(adapter, request), cwd=SKILLJECT_ROOT,
                       env=env, check=True)


def _config_path(request: RunRequest) -> Path:
    values = _extra_values(request.extra, "--config")
    if values:
        return Path(values[-1]).resolve()
    default = SKILLJECT_ROOT / "config" / "main.yaml"
    return default


def _missing_runtime() -> list[str]:
    missing = []
    if shutil.which("docker") is None:
        missing.append("docker")
    if shutil.which("opensandbox-server") is None:
        missing.append("opensandbox-server")
    try:
        __import__("opensandbox")
    except Exception:
        missing.append("python package opensandbox")
    return missing


def _extra_values(extra: tuple[str, ...], flag: str) -> list[str]:
    values: list[str] = []
    items = list(extra)
    i = 0
    while i < len(items):
        item = items[i]
        if item == flag:
            i += 1
            while i < len(items) and not items[i].startswith("--"):
                values.append(items[i])
                i += 1
            continue
        if item.startswith(flag + "="):
            values.append(item.split("=", 1)[1])
        i += 1
    return values


def _extra_value(extra: tuple[str, ...], flag: str, default: str) -> str:
    values = _extra_values(extra, flag)
    return values[-1] if values else default


RUNNER = SkillJectRunner()
