from __future__ import annotations

import json
from pathlib import Path

from code.core.adapter import BenchmarkAdapter
from code.core.types import EvalCase, RunRequest


class LaunderingBenchAdapter(BenchmarkAdapter):
    """Static adapter for the LaunderingBench pilot data layer.

    Execution runners are intentionally not wired yet.  This keeps the pilot
    data frozen and auditable before we decide whether to run model rollouts.
    """

    protocol_path = Path(__file__).with_name("protocol.json")

    def cases(self, split: str | None = None):
        bundle = json.loads((self.protocol_path.parent / "data/cases.json").read_text(encoding="utf-8"))
        for row in bundle["cases"]:
            condition = str(row["split"])
            if split not in (None, condition):
                continue
            payload = {key: value for key, value in row.items() if key not in {"case_id", "split", "suite"}}
            yield EvalCase(
                "LaunderingBench",
                str(row["case_id"]),
                condition,
                str(row.get("suite") or row.get("unit") or "laundering"),
                payload,
                utility_eligible=True,
            )

    def command(self, method: str, request: RunRequest) -> list[str]:
        self.require_method(method)
        if method != "undefended":
            raise NotImplementedError(f"LaunderingBench runner for {method!r} is not wired yet")
        command = [
            "python3", "-m", "code.benchmarks.launderingbench.execution.batch",
            "--method", method,
            "--model", request.target_model,
            "--output", str(request.output),
            "--workers", str(request.workers),
        ]
        if request.resume:
            command.append("--resume")
        return [*command, *request.extra]
