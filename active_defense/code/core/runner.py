"""Method runner contract; benchmark adapters remain the sole data owners."""
from __future__ import annotations

import subprocess

from code.core.adapter import BenchmarkAdapter
from code.core.types import RunRequest


class BaselineRunner:
    def __init__(self, method: str):
        self.method = method

    def command(self, adapter: BenchmarkAdapter, request: RunRequest) -> list[str]:
        adapter.require_method(self.method)
        return adapter.command(self.method, request)

    def run(self, adapter: BenchmarkAdapter, request: RunRequest) -> None:
        subprocess.run(self.command(adapter, request), check=True)

