"""Canonical paper-evaluation benchmark and baseline registry.

Frozen protocol files own datasets, hashes, and denominators.  This registry
owns the code-level compatibility matrix: which benchmark adapters are part of
the paper and which defense methods they support.
"""
from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import shutil


ACTIVE_DEFENSE_METHODS = ("ours",)

# The paper compares thirteen defense baselines. Undefended is the reference
# condition and is intentionally tracked separately. Adaptive payload builders
# (mcp_itp and skillject) are attacks, not defense baselines.
PAPER_BASELINES = (
    "agentshield",
    "camel",
    "clawguard",
    "drift",
    "dynamic_guardian",
    "mcp_guard",
    "melon",
    "pipelock",
    "progent",
    "spotlighting",
    "stackone",
    "taskshield",
    "tool_filter",
)
REFERENCE_METHOD = "undefended"


@dataclass(frozen=True)
class BenchmarkRegistration:
    key: str
    display_name: str
    adapter_module: str
    adapter_class: str
    baselines: tuple[str, ...]

    @property
    def methods(self) -> tuple[str, ...]:
        return (*ACTIVE_DEFENSE_METHODS, REFERENCE_METHOD, *self.baselines)


PAPER_BENCHMARKS: dict[str, BenchmarkRegistration] = {
    "agentdojo": BenchmarkRegistration(
        "agentdojo", "AgentDojo",
        "code.benchmarks.agentdojo.adapter", "AgentDojoAdapter",
        ("drift", "camel", "progent", "melon", "spotlighting",
         "tool_filter", "agentshield", "taskshield"),
    ),
    "asb_opi": BenchmarkRegistration(
        "asb_opi", "ASB-OPI",
        "code.benchmarks.asb_opi.adapter", "ASBOPIAdapter",
        ("progent", "camel", "drift", "melon", "spotlighting",
         "tool_filter", "agentshield", "taskshield"),
    ),
    "skillinject": BenchmarkRegistration(
        "skillinject", "SkillInject",
        "code.benchmarks.skillinject.adapter", "SkillInjectAdapter",
        ("clawguard", "progent", "taskshield", "dynamic_guardian"),
    ),
    "scr": BenchmarkRegistration(
        "scr", "SCR",
        "code.benchmarks.scr.adapter", "SCRAdapter",
        ("clawguard", "progent", "taskshield", "dynamic_guardian"),
    ),
    "msb": BenchmarkRegistration(
        "msb", "MSB",
        "code.benchmarks.msb.adapter", "MSBAdapter",
        ("mcp_guard", "pipelock", "stackone", "clawguard"),
    ),
    "mcptox": BenchmarkRegistration(
        "mcptox", "MCPTox",
        "code.benchmarks.mcptox.adapter", "MCPToxAdapter",
        ("mcp_guard", "pipelock", "stackone", "clawguard"),
    ),
}


EXPERIMENTAL_BENCHMARKS: dict[str, BenchmarkRegistration] = {
    "launderingbench": BenchmarkRegistration(
        "launderingbench", "LaunderingBench",
        "code.benchmarks.launderingbench.adapter", "LaunderingBenchAdapter",
        (),
    ),
    "agentlab_task_injection": BenchmarkRegistration(
        "agentlab_task_injection", "AgentLAB-TaskInjection",
        "code.benchmarks.agentlab_task_injection.adapter",
        "AgentLABTaskInjectionAdapter", (),
    ),
}


# Static integration blockers only. Environment-specific dependencies (for
# example a local Pipelock binary) belong in runner preflight checks.
BLOCKED_INTEGRATIONS: dict[tuple[str, str], str] = {
    ("agentdojo", "camel"): (
        "restore the Progent-compatible CaMeL integration used by the full run"
    ),
    ("agentdojo", "drift"): (
        "restore the AgentDyn DRIFT integration with DeepSeek transport normalization"
    ),
}


VALIDATION_REQUIRED: dict[tuple[str, str], str] = {
    ("msb", "mcp_guard"): (
        "the existing efficiency attempt completed only one case; validate the "
        "official MSB runtime and detector dependencies before a new subset run"
    ),
}


def method_status(benchmark: str, method: str) -> tuple[str, str | None]:
    """Return static applicability plus current-machine runnability."""
    blocked = BLOCKED_INTEGRATIONS.get((benchmark, method))
    if blocked:
        return "blocked", blocked
    validation = VALIDATION_REQUIRED.get((benchmark, method))
    if validation:
        return "validation_required", validation
    if method == "pipelock" and benchmark in {"msb", "mcptox"}:
        configured = os.environ.get("PIPELOCK_BIN")
        binary = Path(configured) if configured else None
        available = bool(binary and binary.is_file() and os.access(binary, os.X_OK))
        if not available and shutil.which("pipelock") is None:
            return "dependency_missing", (
                "set PIPELOCK_BIN to an executable official Pipelock binary"
            )
    return "supported", None


def all_benchmarks(include_experimental: bool = True) -> dict[str, BenchmarkRegistration]:
    if not include_experimental:
        return dict(PAPER_BENCHMARKS)
    return {**PAPER_BENCHMARKS, **EXPERIMENTAL_BENCHMARKS}


def matrix_rows() -> list[dict]:
    rows = []
    for benchmark, spec in PAPER_BENCHMARKS.items():
        supported = set(spec.baselines)
        states = {}
        notes = {}
        for method in PAPER_BASELINES:
            if method not in supported:
                states[method] = "not_applicable"
                continue
            status, note = method_status(benchmark, method)
            states[method] = status
            if note:
                notes[method] = note
        rows.append({
            "benchmark": benchmark,
            "display_name": spec.display_name,
            "adapter": f"{spec.adapter_module}:{spec.adapter_class}",
            "undefended": True,
            "baselines": states,
            "notes": notes,
        })
    return rows
