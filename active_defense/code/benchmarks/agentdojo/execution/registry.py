"""Canonical AgentDojo method-to-runner registry.

This module is the only place where an AgentDojo method is mapped to an
execution implementation.  Dataset selection remains owned by the benchmark
adapter; full and efficiency runs differ only in the manifest forwarded to the
same implementation.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MethodSpec:
    module: str
    native_defense: str | None = None
    defense_model_flag: str | None = None
    contract_file: bool = False
    runnable: bool = True
    unavailable_reason: str | None = None

    def require_runnable(self, method: str) -> None:
        if not self.runnable:
            raise RuntimeError(
                f"AgentDojo method {method!r} is disabled: "
                f"{self.unavailable_reason}"
            )


METHODS: dict[str, MethodSpec] = {
    "ours": MethodSpec(
        "code.benchmarks.agentdojo.execution.ours",
        defense_model_flag="--contract-model",
        contract_file=True,
    ),
    "undefended": MethodSpec("code.benchmarks.agentdojo.execution.undefended"),
    "melon": MethodSpec("code.benchmarks.agentdojo.execution.melon"),
    "agentshield": MethodSpec("code.benchmarks.agentdojo.execution.agentshield"),
    "taskshield": MethodSpec(
        "code.benchmarks.agentdojo.execution.taskshield",
        defense_model_flag="--guard-model",
    ),
    "progent": MethodSpec(
        "code.benchmarks.agentdojo.execution.native",
        native_defense="progent",
        defense_model_flag="--policy-model",
    ),
    "spotlighting": MethodSpec(
        "code.benchmarks.agentdojo.execution.native",
        native_defense="spotlighting",
    ),
    "tool_filter": MethodSpec(
        "code.benchmarks.agentdojo.execution.native",
        native_defense="tool_filter",
    ),
    # These full results were produced by dedicated integrations that were
    # removed during the architecture refactor.  The generic native runner is
    # not equivalent: CaMeL requires its local-model transport configuration,
    # and DRIFT requires the AgentDyn pipeline plus transport normalization.
    # Fail before an API call until those exact integrations are restored.
    "camel": MethodSpec(
        "code.benchmarks.agentdojo.execution.camel",
        runnable=False,
        unavailable_reason=(
            "the canonical Progent-compatible CaMeL integration must be "
            "restored from the full-run implementation"
        ),
    ),
    "drift": MethodSpec(
        "code.benchmarks.agentdojo.execution.drift",
        runnable=False,
        unavailable_reason=(
            "the canonical AgentDyn DRIFT integration and DeepSeek transport "
            "normalization must be restored from the full-run implementation"
        ),
    ),
}
