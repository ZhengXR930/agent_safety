from __future__ import annotations

from pathlib import Path
import sys

from code.core.adapter import BenchmarkAdapter
from code.core.types import EvalCase, RunRequest
from code.benchmarks.mcptox.protocol_runtime import load_cases


class MCPToxAdapter(BenchmarkAdapter):
    protocol_path = Path(__file__).with_name("protocol.json")
    _modules = {
        "ours": "code.benchmarks.mcp_common.runtime",
        "wrap_only": "code.benchmarks.mcp_common.runtime",
        "plant_only": "code.benchmarks.mcp_common.runtime",
        "undefended": "code.benchmarks.mcptox.execution.undefended",
        "mcp_itp": "code.benchmarks.mcptox.adaptive.mcp_itp",
        "mcp_guard": "code.benchmarks.mcptox.execution.mcpguard_e2e",
        "pipelock": "code.benchmarks.mcptox.execution.pipelock",
        "stackone": "code.benchmarks.mcptox.execution.stackone_e2e",
    }

    def cases(self, split: str | None = None):
        clean, attack = load_cases()
        selected = clean if split == "clean" else attack if split == "attack" else [*clean, *attack]
        for row in selected:
            yield EvalCase(
                "MCPTox", row["case_id"], row["mode"], row["server_name"],
                {key: value for key, value in row.items()
                 if key not in {"case_id", "key", "mode", "server_name"}})

    def command(self, method: str, request: RunRequest) -> list[str]:
        self.require_method(method)
        command = [sys.executable, "-m", self._modules[method]]
        active_defense = method in {"ours", "wrap_only", "plant_only"}
        if active_defense or method in {"undefended", "mcp_itp", "mcp_guard", "stackone"}:
            command.extend(["--model", request.target_model])
        if active_defense:
            command.extend([
                "--dataset", "mcptox",
                "--contracts-input",
                str(Path(__file__).resolve().parents[3] /
                    "code/ours/contracts/mcptox/contracts.json"),
                "--ablation-mode",
                {
                    "ours": "full",
                    "wrap_only": "wrap_only",
                    "plant_only": "plant_only",
                }[method],
            ])
        if active_defense and request.defense_model:
            command.extend(["--contract-model", request.defense_model])
        if (method in {"undefended", "mcp_guard", "stackone"}
                and request.judge_model):
            command.extend(["--evaluation-model", request.judge_model])
        if method == "mcp_itp" and request.judge_model:
            command.extend(["--judge-model", request.judge_model])
        if active_defense or method in {"undefended", "mcp_itp", "mcp_guard", "stackone"}:
            command.extend(["--workers", str(request.workers)])
        command.extend(["--output", str(request.output)])
        if request.resume and method != "pipelock":
            command.append("--resume")
        return [*command, *request.extra]
