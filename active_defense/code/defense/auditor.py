"""Auditor response role: deceive a blocked attacker and re-anchor the trusted task."""
from __future__ import annotations

import json
import hashlib
from dataclasses import dataclass
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

    def matches(self, action: str, arguments: dict) -> bool:
        """Match only the exact rejected proposal.

        A repaired proposal must be evaluated afresh by WRAP.  Semantic
        similarity to rejected free text is not evidence that the rejected risk
        remains, and using a task-equivalence judge here blocks clean recovery.
        """
        return (str(action) == self.rejected_action and
                dict(arguments or {}) == self.rejected_arguments)

    def to_dict(self) -> dict:
        return {"rejected_action": self.rejected_action,
                "rejected_arguments": self.rejected_arguments,
                "risk_reason": self.risk_reason,
                "proposal_digest": self.proposal_digest,
                "retry_budget": self.retry_budget}

    def feedback(self) -> str:
        return "The proposal was rejected. Do not retry it or an equivalent proposal."


@dataclass
class ApprovalGrant:
    """Episode-local authority for one exact held proposal.

    A grant never mutates the trusted TaskContract and is not persisted across
    episodes.  Exact one-shot authorization is the safe default; a future UI
    may construct a wider template only from an explicitly human-selected
    trusted set.
    """

    action: str
    arguments: dict
    origin: Literal["trusted", "untrusted", "unresolved"]
    remaining: int = 1

    def consume(self, action: str, arguments: dict) -> bool:
        if (self.remaining <= 0 or str(action) != self.action or
                dict(arguments or {}) != self.arguments):
            return False
        self.remaining -= 1
        return True

    def to_dict(self) -> dict:
        return {"action": self.action, "arguments": dict(self.arguments),
                "origin": self.origin, "remaining": self.remaining}


def _plain(value):
    dump = getattr(value, "model_dump", None)
    if callable(dump):
        return dump(mode="json")
    if isinstance(value, dict):
        return {key: _plain(child) for key, child in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain(child) for child in value]
    return value


def _nodes(value, path=""):
    yield path, value
    if isinstance(value, dict):
        for key, child in value.items():
            part = str(key).replace("~", "~0").replace("/", "~1")
            yield from _nodes(child, path + "/" + part)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from _nodes(child, path + "/" + str(index))


def _replace_path(value, target, path=""):
    if path == target:
        return "[content withheld by execution guard]"
    if isinstance(value, dict):
        return {key: _replace_path(
            child, target,
            path + "/" + str(key).replace("~", "~0").replace("/", "~1"))
                for key, child in value.items()}
    if isinstance(value, list):
        return [_replace_path(child, target, path + "/" + str(index))
                for index, child in enumerate(value)]
    return value


@dataclass
class RecoveryState:
    """Deny-only episode recovery state over canonical receipt versions."""

    budget: int = 1

    def __post_init__(self):
        self.quarantine: set[str] = set()
        self.attempts = 0

    def quarantine_unique_values(self, observations, values) -> int:
        """Quarantine a value only when one exact canonical node identifies it."""
        added = 0
        for value in values:
            matches = [
                receipt.digest + "#" + path
                for receipt in observations
                for path, node in _nodes(_plain(receipt.value))
                if node == value and not isinstance(node, (dict, list))
            ]
            if len(matches) == 1 and matches[0] not in self.quarantine:
                self.quarantine.add(matches[0])
                added += 1
        return added

    def quarantine_unique_ref(self, observations, refs) -> int:
        """Quarantine one exact provenance input; never choose among candidates."""
        candidates = tuple(dict.fromkeys(str(ref) for ref in refs if str(ref)))
        if len(candidates) != 1:
            return 0
        candidate = candidates[0]
        digest, marker, path = candidate.partition("#")
        receipt = next((item for item in observations if item.digest == digest), None)
        if receipt is None or not marker:
            return 0
        valid = {node_path for node_path, _value in _nodes(_plain(receipt.value))}
        if path not in valid or candidate in self.quarantine:
            return 0
        self.quarantine.add(candidate)
        return 1

    def quarantine_plant(self, observations, deployment) -> int:
        """Quarantine the exact receipt node recorded when PLANT was deployed."""
        if deployment is None:
            return 0
        canonical_refs = tuple(
            str(ref) for ref in
            (getattr(deployment, "canonical_refs", ()) or ())
            if str(ref))
        if canonical_refs:
            return sum(self.quarantine_unique_ref(
                observations, (canonical_ref,))
                for canonical_ref in canonical_refs)
        canonical_ref = str(getattr(deployment, "canonical_ref", "") or "")
        if canonical_ref:
            return self.quarantine_unique_ref(observations, (canonical_ref,))
        return self.quarantine_unique_values(observations, (deployment.before,))

    def sanitize(self, receipt):
        """Return a view with only quarantined nodes of this version withheld."""
        value = _plain(receipt.value)
        prefix = receipt.digest + "#"
        paths = [ref[len(prefix):] for ref in self.quarantine
                 if ref.startswith(prefix)]
        for path in paths:
            value = _replace_path(value, path)
        return value

    def can_restart(self) -> bool:
        return self.attempts < self.budget

    def begin_restart(self) -> bool:
        if not self.can_restart():
            return False
        self.attempts += 1
        return True


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
        return AuditResponse("simulated_success", fake)

    def local_block(self, user_task: str, reason: str = "") -> AuditResponse:
        """Return a same-conversation tool error for one rejected local call."""
        self.n_audited += 1
        explanation = str(reason or "The call exceeded the trusted task boundary.").strip()
        task = " ".join(str(user_task or "").split())
        return AuditResponse("retry_rejected", (
            "Tool call blocked before execution: " + explanation[:500] +
            ". Do not repeat an equivalent call. The original trusted task is: " + task[:1000] +
            ". Preserve already completed operations and task-local observations, then correct "
            "only the remaining action once."
        ))
