from __future__ import annotations

import json
from pathlib import Path
import sys

from code.core.adapter import BenchmarkAdapter
from code.core.types import EvalCase, RunRequest


class AgentLABTaskInjectionAdapter(BenchmarkAdapter):
    """Separate entry for AgentLAB's long-horizon task-injection benchmark."""

    protocol_path = Path(__file__).with_name("protocol.json")

    def cases(self, split: str | None = None):
        data = self.protocol_path.parent / "data"
        if split in (None, "clean"):
            suites = json.loads((data / "clean_tasks.json").read_text(encoding="utf-8"))
            for suite, tasks in suites.items():
                for task in tasks:
                    yield EvalCase(
                        "AgentLAB-TaskInjection",
                        f"{suite}:{task}",
                        "clean",
                        suite,
                        {"task": task},
                    )
        if split in (None, "attack"):
            for path in sorted(data.glob("*_pairs.json")):
                suite = path.stem.removesuffix("_pairs")
                for task, injection in json.loads(path.read_text(encoding="utf-8")):
                    yield EvalCase(
                        "AgentLAB-TaskInjection",
                        f"{suite}:{task}:{injection}",
                        "attack",
                        suite,
                        {"task": task, "injection": injection},
                    )

    def command(self, method: str, request: RunRequest) -> list[str]:
        self.require_method(method)
        command = [
            sys.executable,
            "-m",
            "code.benchmarks.agentlab_task_injection.execution.baselines",
            "--method",
            method,
            "--output-root",
            str(request.output),
            "--agent-model",
            request.target_model,
            "--workers",
            str(request.workers),
        ]
        if request.resume:
            command.append("--resume")
        return [*command, *request.extra]
