"""MCP-ITP runner for the MCPTox unit.

No public MCP-ITP implementation was found during setup. This runner invokes
our paper-faithful reproduction of the official black-box optimization setting
over frozen MCPTox cases.
"""
from __future__ import annotations

import subprocess
import sys

from code.core.adapter import BenchmarkAdapter
from code.core.types import RunRequest


class MCPITPRunner:
    method = "mcp_itp"

    def command(self, adapter: BenchmarkAdapter, request: RunRequest) -> list[str]:
        if adapter.protocol.benchmark != "MCPTox":
            raise ValueError("MCP-ITP-style runner only applies to the MCPTox unit")
        command = [
            sys.executable,
            "-m",
            "code.benchmarks.mcptox.adaptive.mcp_itp",
            "--model",
            request.target_model,
            "--judge-model",
            request.judge_model or "gpt-5.4-2026-03-05",
            "--workers",
            str(request.workers),
            "--output",
            str(request.output),
        ]
        if request.resume:
            command.append("--resume")
        return [*command, *request.extra]

    def run(self, adapter: BenchmarkAdapter, request: RunRequest) -> None:
        subprocess.run(self.command(adapter, request), check=True)


RUNNER = MCPITPRunner()
