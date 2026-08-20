from __future__ import annotations

import json
from pathlib import Path
import sys

from code.core.adapter import BenchmarkAdapter
from code.core.types import EvalCase, RunRequest


class AgentDojoAdapter(BenchmarkAdapter):
    protocol_path = Path(__file__).with_name("protocol.json")
    def cases(self, split: str | None = None):
        data = self.protocol_path.parent / "data"
        if split in (None, "clean"):
            suites = json.loads((data / "clean_tasks.json").read_text())
            for suite, tasks in suites.items():
                for task in tasks:
                    yield EvalCase("AgentDojo", f"{suite}:{task}", "clean",
                                   suite, {"task": task})
        if split in (None, "attack"):
            for path in sorted(data.glob("*_pairs.json")):
                suite = path.stem.removesuffix("_pairs")
                for task, injection in json.loads(path.read_text()):
                    yield EvalCase(
                        "AgentDojo", f"{suite}:{task}:{injection}", "attack",
                        suite, {"task": task, "injection": injection})

    def command(self, method: str, request: RunRequest) -> list[str]:
        self.require_method(method)
        command = [
            sys.executable, "-m", "code.benchmarks.agentdojo.execution.all",
            "--method", method,
            "--output-root", str(request.output),
            "--agent-model", request.target_model,
            "--workers", str(request.workers),
        ]
        if request.defense_model:
            command.extend(["--defense-model", request.defense_model])
        if request.resume:
            command.append("--resume")
        return [*command, *request.extra]
