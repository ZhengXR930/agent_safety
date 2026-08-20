from __future__ import annotations

import json
from pathlib import Path
import sys

from code.core.adapter import BenchmarkAdapter
from code.core.types import EvalCase, RunRequest


ACTIVE_DEFENSE_METHODS = {"ours", "wrap_only", "plant_only"}


class SCRAdapter(BenchmarkAdapter):
    protocol_path = Path(__file__).with_name("protocol.json")

    def cases(self, split: str | None = None):
        capflow = json.loads((self.protocol_path.parent / "data/capflow.json").read_text())
        suites = {
            "capflow": tuple(sorted(capflow["cases"], key=int)),
            "authblur": tuple(str(i) for i in range(1, 117)),
            "trustlift": tuple(str(i) for i in range(1, 402)),
        }
        for suite, identifiers in suites.items():
            for identifier in identifiers:
                for condition in ("clean", "attack"):
                    if split not in (None, condition):
                        continue
                    yield EvalCase("SCR", f"{suite}:{identifier}", condition,
                                   suite, {"case": int(identifier)})

    def command(self, method: str, request: RunRequest) -> list[str]:
        self.require_method(method)
        if method in ACTIVE_DEFENSE_METHODS:
            module = "code.benchmarks.scr.execution.batch"
            command = [sys.executable, "-m", module,
                       "--output-root", str(request.output),
                       "--workers", str(request.workers),
                       "--target-model", request.target_model,
                       "--phase", "evaluate",
                       "--frozen-contract-root",
                       str(Path(__file__).resolve().parents[3] /
                           "code/ours/contracts/scr")]
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
        else:
            module = "code.benchmarks.scr.execution.baseline_batch"
            command = [sys.executable, "-m", module,
                       "--output-root", str(request.output),
                       "--workers", str(request.workers),
                       "--model", request.target_model]
            if method == "undefended":
                command.append("--undefended-only")
            else:
                command.extend(["--baseline", method])
            if request.defense_model:
                command.extend(["--guard-model", request.defense_model])
        return [*command, *request.extra]
