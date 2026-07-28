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
    plant_events: tuple = field(default_factory=tuple)
    recovered_arguments: dict = field(default_factory=dict)


class Detector:
    def __init__(self, client=None, model: str = ""):
        self.client, self.model = client, model

    def decide(self, task: str, action: str, arguments: dict,
               evidence: GateResult, plant_events=(), context=()) -> Decision:
        clause = evidence.provenance.clause
        plant_events = tuple(plant_events or ())
        if plant_events:
            return Decision("auditor", "PLANT commitment", clause, evidence,
                            plant_events)
        if evidence.conflicts:
            return Decision("auditor", "conflict:" + ",".join(evidence.conflicts),
                            clause, evidence, plant_events)
        if evidence.complete:
            return Decision("pass", clause=clause, evidence=evidence,
                            plant_events=plant_events)
        unresolved = evidence.unresolved or ("$control",)
        # Approval may authorize one exact proposal, but unresolved material
        # copied from an observation must not silently become a new authority
        # edge.  Clause-local receipt inputs are deterministic evidence of that
        # origin; route them to deny/recovery unless WRAP first proves the role.
        provenance_args = evidence.provenance.arguments
        untrusted = tuple(name for name in unresolved
                          if name in provenance_args and
                          provenance_args[name].inputs and
                          any(source not in {"task", "runtime-context"}
                              for source in provenance_args[name].sources))
        if untrusted:
            return Decision("auditor", "unresolved-untrusted:" +
                            ",".join(untrusted), clause, evidence, plant_events)
        reason = "unresolved:" + ",".join(unresolved)
        return Decision("approval", reason, clause, evidence, plant_events)


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

    def pop(self, effect: str, arguments: dict) -> Proposal | None:
        """Remove one exact held proposal without draining unrelated incidents."""
        encoded = json.dumps(arguments, sort_keys=True, ensure_ascii=False,
                             default=str, separators=(",", ":"))
        key = (str(effect), hashlib.sha256(encoded.encode()).hexdigest())
        return self._items.pop(key, None)
