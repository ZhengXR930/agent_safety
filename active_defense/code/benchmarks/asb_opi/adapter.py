from __future__ import annotations

import json
from pathlib import Path
import sys

from code.core.adapter import BenchmarkAdapter
from code.core.types import EvalCase, RunRequest


FROZEN_CONTRACT_CACHE_ROOT = (
    Path(__file__).resolve().parents[3] /
    "experiment_results/ASB-OPI/Ours/DeepSeek/contracts")


class ASBOPIAdapter(BenchmarkAdapter):
    protocol_path = Path(__file__).with_name("protocol.json")

    def cases(self, split: str | None = None):
        data = self.protocol_path.parent / "data"
        if split in (None, "clean"):
            for row in json.loads((data / "clean_cases.json").read_text(encoding="utf-8")):
                yield EvalCase("ASB-OPI", row["case_id"], "clean", row["agent_name"], row)
        if split in (None, "attack"):
            for row in json.loads((data / "attack_cases.json").read_text(encoding="utf-8")):
                yield EvalCase("ASB-OPI", row["case_id"], "attack", row["agent_name"], row)

    def command(self, method: str, request: RunRequest) -> list[str]:
        self.require_method(method)
        command = [
            sys.executable,
            "-m",
            "code.benchmarks.asb_opi.execution.glue",
            "--method",
            method,
            "--model",
            request.target_model,
            "--defense-model",
            request.defense_model or request.target_model,
            "--output",
            str(request.output),
            "--workers",
            str(request.workers),
        ]
        if request.resume:
            command.append("--resume")
        if method in {"ours", "wrap_only", "plant_only"}:
            command.extend([
                "--contract-cache-root",
                str(FROZEN_CONTRACT_CACHE_ROOT),
            ])
        return [*command, *request.extra]
