from __future__ import annotations

import json
from pathlib import Path
import sys

from code.core.adapter import BenchmarkAdapter
from code.core.types import EvalCase, RunRequest


class MSBAdapter(BenchmarkAdapter):
    protocol_path = Path(__file__).with_name("protocol.json")

    def cases(self, split: str | None = None):
        if split not in (None, "attack"):
            return
        bundle = json.loads((self.protocol_path.parent / "data/cases.json").read_text())
        for row in bundle["cases"]:
            eligible = row["attack_type"] not in {
                "false_error", "simulated_user",
                "prompt_injection-simulated_user", "prompt_injection-false_error",
            }
            yield EvalCase("MSB", row["case_id"], "attack",
                           row["attack_type"], row, eligible)

    def command(self, method: str, request: RunRequest) -> list[str]:
        self.require_method(method)
        if method in {"ours", "wrap_only", "plant_only"}:
            command = [
                sys.executable, "-m", "code.benchmarks.msb.execution.native",
                "--model", request.target_model,
                "--workers", str(request.workers),
                "--contracts-input", str(
                    Path(__file__).resolve().parents[3] /
                    "code/ours/contracts/msb/contracts.json"),
                "--output", str(request.output),
                "--ablation-mode",
                {
                    "ours": "full",
                    "wrap_only": "wrap_only",
                    "plant_only": "plant_only",
                }[method],
            ]
            if request.defense_model:
                command.extend(["--contract-model", request.defense_model])
            if request.resume:
                command.append("--resume")
        else:
            baseline = {"undefended": "none", "mcp_guard": "mcpguard"}.get(
                method, method)
            command = [
                sys.executable, "-m", "code.benchmarks.msb.execution.score",
                "--model", request.target_model,
                "--baseline", baseline,
                "--case-manifest", str(self.protocol_path.parent / "data/cases.json"),
                "--output", str(request.output),
            ]
        return [*command, *request.extra]
