"""Deterministically route independent PLANT and structured WRAP evidence."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field

from .wrap import GateResult


@dataclass(frozen=True)
class Decision:
    route: str
    reason: str = ""
    clause: str | None = None
    evidence: GateResult | None = None


class Detector:
    def __init__(self, client=None, model: str = ""):
        self.client, self.model = client, model

    def decide(self, task: str, action: str, arguments: dict,
               evidence: GateResult, plant_events=(), context=()) -> Decision:
        clause = evidence.provenance.clause
        if plant_events:
            return Decision("auditor", "PLANT commitment", clause, evidence)
        if evidence.conflicts:
            return Decision("auditor", "conflict:" + ",".join(evidence.conflicts),
                            clause, evidence)
        if evidence.complete:
            return Decision("pass", clause=clause, evidence=evidence)
        reason = "unresolved:" + ",".join(evidence.unresolved or ("$control",))
        return Decision("approval", reason, clause, evidence)


@dataclass
class Proposal:
    clause: str | None
    effect: str
    arguments: dict
    route: str
    reason: str
    count: int = 1

    def to_dict(self):
        return {"clause": self.clause, "effect": self.effect,
                "arguments": self.arguments, "route": self.route,
                "reason": self.reason, "count": self.count}


@dataclass(frozen=True)
class Incident:
    scope: str
    route: str
    proposals: tuple[Proposal, ...] = field(default_factory=tuple)

    def to_dict(self):
        return {"scope": self.scope, "route": self.route,
                "proposals": [proposal.to_dict() for proposal in self.proposals]}


class ProposalBuffer:
    """Deduplicate quarantined calls and emit at most one incident per task."""
    def __init__(self):
        self._items: dict[tuple[str, str], Proposal] = {}

    def add(self, clause: str | None, effect: str, arguments: dict, decision: Decision):
        encoded = json.dumps(arguments, sort_keys=True, ensure_ascii=False,
                             default=str, separators=(",", ":"))
        key = (str(effect), hashlib.sha256(encoded.encode()).hexdigest())
        if key in self._items:
            self._items[key].count += 1
            return
        self._items[key] = Proposal(clause, str(effect), dict(arguments),
                                    decision.route, decision.reason)

    def drain(self, scope: str) -> Incident | None:
        proposals = tuple(self._items.values())
        self._items.clear()
        if not proposals:
            return None
        route = "auditor" if any(item.route == "auditor" for item in proposals) else "approval"
        return Incident(scope, route, proposals)
