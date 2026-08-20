from __future__ import annotations

import json
from pathlib import Path
import sys

from code.core.adapter import BenchmarkAdapter
from code.core.types import EvalCase, RunRequest


ACTIVE_DEFENSE_METHODS = {"ours", "wrap_only", "plant_only"}


class SkillInjectAdapter(BenchmarkAdapter):
    protocol_path = Path(__file__).with_name("protocol.json")

    def cases(self, split: str | None = None):
        rows = json.loads((self.protocol_path.parent / "data/cases.json").read_text())
        for row in rows:
            for index, task in enumerate(row.get("tasks") or ()):
                for condition in ("clean", "attack"):
                    if split not in (None, condition):
                        continue
                    yield EvalCase(
                        "SkillInject", f"id{int(row['id']):03d}:task{index}",
                        condition, payload={"row": row, "task": task})

    def command(self, method: str, request: RunRequest) -> list[str]:
        self.require_method(method)
        baseline = "undefended" if method == "undefended" else method
        common = [
            "--output-root", str(request.output),
            "--work-root", str(request.output.parent / ".work" / method),
            "--workers", str(request.workers),
            "--model", request.target_model,
        ]
        if method in ACTIVE_DEFENSE_METHODS:
            module = "code.benchmarks.skillinject.execution.batch"
            command = [sys.executable, "-m", module, *common]
            command.extend([
                "--ablation-mode",
                {
                    "ours": "full",
                    "wrap_only": "wrap_only",
                    "plant_only": "plant_only",
                }[method],
            ])
            if request.defense_model:
                command.extend(["--defense-model", request.defense_model])
            command.extend([
                "--frozen-contract-bundle",
                str(Path(__file__).resolve().parents[3] /
                    "code/ours/contracts/skillinject/contracts.json"),
            ])
        else:
            module = "code.benchmarks.skillinject.execution.baseline_batch"
            command = [sys.executable, "-m", module, "--baseline", baseline,
                       *common]
            if request.defense_model:
                command.extend(["--guard-model", request.defense_model])
        if request.judge_model:
            command.extend(["--judge-model", request.judge_model])
        return [*command, *request.extra]
