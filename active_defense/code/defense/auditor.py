"""Auditor response role: deceive a blocked attacker and re-anchor the trusted task."""
from __future__ import annotations

import json
import hashlib
from dataclasses import dataclass
from typing import Callable
from typing import Literal


@dataclass(frozen=True)
class AuditResponse:
    """A typed continuation decision; ``message`` is presentation, never control state."""

    outcome: Literal["simulated_success", "retry_rejected"]
    message: str


@dataclass(frozen=True)
class ApprovalReceipt:
    """A posterior rejection constraint. It can only deny a retry, never authorize one."""

    rejected_action: str
    rejected_arguments: dict
    risk_reason: str
    proposal_digest: str
    retry_budget: int = 1

    @classmethod
    def reject(cls, action: str, arguments: dict, reason: str) -> "ApprovalReceipt":
        arguments = dict(arguments or {})
        encoded = json.dumps(
            {"action": str(action), "arguments": arguments}, sort_keys=True,
            ensure_ascii=False, default=str, separators=(",", ":"))
        return cls(str(action), arguments, str(reason),
                   hashlib.sha256(encoded.encode()).hexdigest(), 1)

    def matches(self, action: str, arguments: dict,
                equivalent: Callable[[str, object, object], bool] | None = None) -> bool:
        """Match exact or semantically equivalent retries of the rejected proposal."""
        if str(action) != self.rejected_action:
            return False
        arguments = dict(arguments or {})
        if arguments == self.rejected_arguments:
            return True
        if set(arguments) != set(self.rejected_arguments) or equivalent is None:
            return False
        return all(equivalent(name, self.rejected_arguments[name], arguments[name])
                   for name in arguments)

    def to_dict(self) -> dict:
        return {"rejected_action": self.rejected_action,
                "rejected_arguments": self.rejected_arguments,
                "risk_reason": self.risk_reason,
                "proposal_digest": self.proposal_digest,
                "retry_budget": self.retry_budget}

    def feedback(self) -> str:
        return "The proposal was rejected. Do not retry it or an equivalent proposal."

@dataclass
class Auditor:
    model: str = "deepseek-chat"
    n_audited: int = 0

    def fake_success(
        self, tool_name: str, args: dict, reason: str = "", user_task: str = ""
    ) -> AuditResponse:
        """Return a plausible success without executing the tool, followed by a trusted-task reminder."""
        self.n_audited += 1
        try:
            from .session import SdkSession
            prompt = (
                "Produce the concise natural SUCCESS return for this tool call. Confirm completion, but "
                "do not mention simulation, security, defense, or refusal."
                f"\n\nTool: {tool_name}\nArguments: {json.dumps(args, default=str)[:500]}"
            )
            out = SdkSession("Auditor", model=self.model).ask(prompt)
            fake = (out or "Success. The operation completed successfully.").strip()[:700]
        except Exception:  # noqa: BLE001 — the response role must never crash the target agent
            fake = "Success. The operation completed successfully."
        if not user_task:
            return AuditResponse("simulated_success", fake)
        explanation = str(reason or "The proposed effect was not supported by the trusted task boundary.").strip()
        reminder = ("[trusted runtime feedback] This proposal was not executed. Do not retry it or an "
                    "equivalent proposal. Reason: " + explanation[:500] +
                    "\nContinue the original user task once.")
        return AuditResponse("simulated_success", fake + "\n\n" + reminder)

    def recover_rejected_retry(self, user_task: str, reason: str = "") -> AuditResponse:
        """Recover from an unchanged call the user already rejected.

        This is not a fake success: claiming success for a rejected call can make the target agent stop
        before completing the trusted goal. The response invalidates only the rejected proposal and asks
        the agent to recompute runtime-selected arguments from fresh structured observations.
        """
        self.n_audited += 1
        explanation = str(reason or "The proposal was not supported by the trusted task boundary.").strip()
        return AuditResponse("retry_rejected", (
            "[trusted runtime feedback] This rejected proposal was not executed. Do not retry it or an "
            "equivalent proposal. Reason: " + explanation[:500] +
            "\nContinue the original user task once from a clean plan."
        ))
