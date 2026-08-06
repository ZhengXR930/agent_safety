"""Deterministic continuation after a WRAP or PLANT refusal.

The controller is deliberately not an Agent.  It can only replay already
proved values, invalidate evidence, and expose machine-checkable obligations.
It never interprets the task, creates a Clause, or grants an Effect.
"""
from __future__ import annotations

from dataclasses import dataclass

from code.defense.contract import EffectClause
from code.defense.resolver import LazyResolver
from code.defense.state import SEMANTIC_REF, RuntimeState, digest


REPAIR = "repair"
REPLAN = "replan"
ABORT = "abort"


class ReplanRequired(RuntimeError):
    """Adapter suspension carrying only a sanitized continuation state."""

    def __init__(self, state: dict):
        super().__init__("sanitized replan required")
        self.state = dict(state)


def replan_state_from_exception(error: BaseException) -> dict | None:
    """Recover a suspension after an Agent SDK wraps the tool exception."""
    current, seen = error, set()
    while current is not None and id(current) not in seen:
        seen.add(id(current))
        if isinstance(current, ReplanRequired):
            return dict(current.state)
        current = current.__cause__ or current.__context__
    return None


@dataclass(frozen=True)
class RepairStep:
    argument: str
    rule: str
    value: object
    sources: tuple[str, ...] = ()
    refs: tuple[str, ...] = ()

    def to_dict(self) -> dict:
        return {
            "argument": self.argument,
            "rule": self.rule,
            "value": self.value,
            "sources": list(self.sources),
            "refs": list(self.refs),
        }


@dataclass(frozen=True)
class Obligation:
    kind: str
    action: str
    argument: str = ""
    allowed_sources: tuple[str, ...] = ()
    invalid_value: object = None

    def to_dict(self) -> dict:
        value = {
            "kind": self.kind,
            "action": self.action,
            "allowed_sources": list(self.allowed_sources),
        }
        if self.argument:
            value["argument"] = self.argument
        if self.invalid_value is not None:
            value["invalid_value"] = self.invalid_value
        return value


@dataclass(frozen=True)
class ContinuationPlan:
    id: str
    mode: str
    reason: str
    action: str = ""
    candidate_arguments: dict | None = None
    repair_proof: tuple[RepairStep, ...] = ()
    invalidated_refs: tuple[str, ...] = ()
    invalidated_derivations: tuple[str, ...] = ()
    denied_resources: tuple[str, ...] = ()
    obligations: tuple[Obligation, ...] = ()
    proof_refs: tuple[str, ...] = ()
    retry_budget: int = 0

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "mode": self.mode,
            "reason": self.reason,
            "action": self.action,
            "candidate_arguments": self.candidate_arguments,
            "repair_proof": [step.to_dict() for step in self.repair_proof],
            "invalidated_refs": list(self.invalidated_refs),
            "invalidated_derivations": list(self.invalidated_derivations),
            "denied_resources": list(self.denied_resources),
            "obligations": [item.to_dict() for item in self.obligations],
            "proof_refs": list(self.proof_refs),
            "retry_budget": self.retry_budget,
        }


class ContinuationController:
    """One episode-local, conflict-bounded continuation state machine."""

    def __init__(self, contract, *, max_replans: int = 1):
        self.contract = contract
        # One retry applies to one conflict class, not the whole episode.  A
        # path mismatch must not consume the later content obligation, while a
        # second path mismatch must not create an unbounded loop.
        self.max_replans = max(0, int(max_replans))
        obligation_slots = sum(
            max(1, len(clause.effect_arguments))
            for clause in contract.clauses
            if isinstance(clause, EffectClause))
        self.max_total_replans = self.max_replans * max(1, obligation_slots)
        self.replans_used = 0
        self._replans_by_conflict: dict[str, int] = {}
        self.denied_resources: set[str] = set()
        self.completed_effects: list[dict] = []
        self._plans: dict[str, ContinuationPlan] = {}
        self._pending: dict[str, str] = {}
        self._consumed_failures: set[str] = set()
        self._consumed_plans: set[str] = set()
        self._plan_conflicts: dict[str, str] = {}

    @staticmethod
    def _sources(spec) -> tuple[str, ...]:
        if not isinstance(spec, dict) or "from" not in spec:
            return ()
        raw = spec["from"]
        return ((str(raw),) if isinstance(raw, str)
                else tuple(map(str, raw or ())))

    @staticmethod
    def _argument_from_reason(reason: str) -> str:
        prefixes = (
            "untraceable-arg:", "uncontracted-arg:", "missing-arg:",
        )
        return next((reason[len(prefix):] for prefix in prefixes
                     if reason.startswith(prefix)), "")

    def _conflict(self, action: str, reason: str, events) -> str:
        """Stable retry identity; proposal values cannot mint new retries."""
        if events:
            category, action = "plant-commitment", "*"
        elif reason.startswith("unauthorized-action:"):
            category, action = "unauthorized-action", "*"
        else:
            category = reason.split(":", 1)[0]
        return digest({
            "action": action,
            "category": category,
            "argument": self._argument_from_reason(reason),
        })

    def _repair_candidates(self, state: RuntimeState, action: str,
                           arguments: dict, required, equal):
        """Yield complete proposals determined only by replayable bindings."""
        resolver = LazyResolver(state, self.contract)
        for clause in self.contract.clauses:
            if not (isinstance(clause, EffectClause) and
                    clause.action == action):
                continue
            specs = clause.effect_arguments
            if any(name not in specs for name in arguments):
                continue
            if any(name not in arguments for name in required):
                continue
            candidate, steps = {}, []
            for name in arguments:
                spec = specs[name]
                if isinstance(spec, dict) and set(spec) == {"literal"}:
                    value, sources, refs, rule = (
                        spec["literal"], (), ("<query>",), "literal")
                elif isinstance(spec, dict) and set(spec) == {"from"}:
                    sources = self._sources(spec)
                    resolved = []
                    refs = []
                    for source in sources:
                        values = resolver.values(source)
                        exact = [row for row in values
                                 if SEMANTIC_REF not in row.refs]
                        unique = {digest(row.value): row for row in exact}
                        if len(unique) != 1:
                            resolved = []
                            break
                        row = next(iter(unique.values()))
                        resolved.append(row.value)
                        refs.extend(row.refs)
                    if not resolved:
                        break
                    value = resolved[0]
                    if any(not equal(name, value, other)
                           for other in resolved[1:]):
                        break
                    refs, rule = tuple(dict.fromkeys(refs)), "binding-replay"
                elif not isinstance(spec, dict):
                    value, sources, refs, rule = spec, (), ("<query>",), "literal"
                else:
                    # Delegated and proposal-local semantic values are not
                    # deterministic repairs.
                    break
                candidate[name] = value
                steps.append(RepairStep(name, rule, value, sources, refs))
            else:
                yield candidate, tuple(steps)

    def _repair(self, state, action, arguments, required, equal, validate):
        unique: dict[str, tuple[dict, tuple[RepairStep, ...]]] = {}
        for candidate, proof in self._repair_candidates(
                state, action, arguments, required, equal):
            if candidate == arguments:
                continue
            ok, _refs = validate(candidate)
            if ok:
                unique.setdefault(digest(candidate), (candidate, proof))
        if len(unique) != 1:
            return None
        return next(iter(unique.values()))

    def _derivations_for(self, state: RuntimeState, refs) -> tuple[str, ...]:
        roots = tuple(str(ref).split("#", 1)[0] + "#"
                      for ref in refs if "#" in str(ref))
        return tuple(sorted(
            clause_id for clause_id, binding in state.bindings.items()
            if any(str(ref).startswith(root)
                   for ref in binding.refs for root in roots)))

    def _root_obligations(self) -> tuple[Obligation, ...]:
        """Describe Contract work that can still finish the trusted task."""
        effects: dict[str, set[str]] = {}
        for clause in self.contract.clauses:
            if not isinstance(clause, EffectClause):
                continue
            sources = effects.setdefault(clause.action, set())
            for spec in clause.effect_arguments.values():
                sources.update(self._sources(spec))
        if effects:
            return tuple(
                Obligation("complete_root_effect", action,
                           allowed_sources=tuple(sorted(sources)))
                for action, sources in effects.items())

        # A read/compute-only task has no external Effect.  Its terminal
        # Clause outputs are the bounded inputs of the final response; the
        # fresh Agent may reacquire/compute them but cannot invent an Effect.
        produced = {
            clause.output_ref for clause in self.contract.clauses
            if clause.output_ref}
        consumed = {
            str(source) for clause in self.contract.clauses
            for source in clause.sources if str(source) in produced}
        terminal = tuple(sorted(produced - consumed))
        return ((Obligation("complete_response", "$response",
                            allowed_sources=terminal),)
                if terminal else ())

    def _obligations(self, action: str, arguments: dict, reason: str,
                     events) -> tuple[Obligation, ...]:
        if events:
            kind = ("resource_unavailable" if any(
                row.get("plane") == "substrate" for row in events)
                    else "invalid_dependency")
            return (Obligation(kind, action),)
        if reason.startswith("unauthorized-action:"):
            return self._root_obligations()
        argument = self._argument_from_reason(reason)
        sources = ()
        for clause in self.contract.clauses:
            if (isinstance(clause, EffectClause) and clause.action == action and
                    argument in clause.effect_arguments):
                sources = self._sources(clause.effect_arguments[argument])
                break
        if reason == "insufficient-authority-proof":
            return (Obligation("missing_authority", action),)
        if argument:
            return (Obligation(
                "missing_binding", action, argument, sources,
                arguments.get(argument)),)
        if reason.startswith("unauthorized-content-atom:"):
            return (Obligation(
                "invalid_dependency", action, invalid_value=reason.split(":", 1)[1]),)
        return (Obligation("revalidate_effect", action),)

    def propose(self, state: RuntimeState, *, action: str, arguments: dict,
                reason: str, refs=(), events=(), plant_scopes=None,
                required=(), equal=None, validate=None, proof_refs=(),
                ) -> ContinuationPlan:
        """Choose repair, replan, or abort without changing episode state."""
        action, arguments = str(action), dict(arguments or {})
        refs, events = tuple(map(str, refs or ())), tuple(events or ())
        plant_scopes = dict(plant_scopes or {})
        equal = equal or (lambda _name, left, right: left == right)
        validate = validate or (lambda _candidate: (False, ()))
        failure = digest({
            "action": action, "arguments": arguments, "reason": reason,
            "refs": refs, "events": events,
        })
        conflict = self._conflict(action, reason, events)
        pending = self._pending.get(failure)
        if pending is not None and failure not in self._consumed_failures:
            return self._plans[pending]

        repair = None
        if (failure not in self._consumed_failures and not events and
                not reason.startswith("unauthorized-action:")):
            repair = self._repair(
                state, action, arguments, frozenset(required), equal, validate)
        if repair is not None:
            candidate, proof = repair
            mode, retry_budget = REPAIR, 0
        else:
            candidate, proof = None, ()
            root_effects = tuple(
                clause for clause in self.contract.clauses
                if isinstance(clause, EffectClause))
            root_obligations = self._root_obligations()
            has_root = any(clause.action == action for clause in root_effects)
            unauthorized = reason.startswith("unauthorized-action:")
            if unauthorized:
                # An unknown action has no repairable value.  Before any
                # external Effect succeeds, one fresh Agent may instead
                # complete the Contract's existing Root Effects.  The denied
                # action identity is episode-local and can never be retried.
                can_replan = bool(
                    root_obligations and not self.completed_effects and
                    action not in self.denied_resources)
            else:
                can_replan = bool(events or has_root or action == "$response")
            can_replan = (can_replan and
                          self.replans_used < self.max_total_replans and
                          self._replans_by_conflict.get(conflict, 0) <
                          self.max_replans and
                          failure not in self._consumed_failures)
            mode, retry_budget = ((REPLAN, 1) if can_replan else (ABORT, 0))

        invalidated, denied = set(), set()
        if (mode == REPLAN and
                reason.startswith("unauthorized-action:")):
            denied.add(action)
        for event in events:
            token = str(event.get("token", ""))
            scope = plant_scopes.get(token, {})
            invalidated.update(map(str, scope.get("refs", ())))
            invalidated.update(map(str, scope.get("source_refs", ())))
            denied.update(map(str, scope.get("identities", (token,))))
        derivations = self._derivations_for(state, invalidated)
        obligations = (() if mode == REPAIR else
                       self._obligations(action, arguments, reason, events))
        plan_id = "CONT-" + digest({
            "failure": failure, "mode": mode, "candidate": candidate,
            "invalidated": sorted(invalidated), "denied": sorted(denied),
        })[:20]
        plan = ContinuationPlan(
            plan_id, mode, str(reason), action, candidate, proof,
            tuple(sorted(invalidated)), derivations, tuple(sorted(denied)),
            obligations, tuple(map(str, proof_refs or ())),
            retry_budget)
        self._plans[plan_id] = plan
        self._pending[failure] = plan_id
        self._plan_conflicts[plan_id] = conflict
        return plan

    def consume(self, plan_id: str) -> ContinuationPlan:
        plan = self._plans.get(str(plan_id))
        if plan is None:
            raise ValueError("unknown continuation plan")
        if plan.id in self._consumed_plans:
            # Parallel Agent tool calls can observe the same suspension before
            # the first callback consumes it.  Replaying REPLAN/ABORT is safe:
            # neither authorizes or executes an Effect, and their state update
            # is idempotent.  A verified REPAIR can cross the Effect boundary,
            # so it remains strictly one-shot.
            if plan.mode == REPAIR:
                raise ValueError("continuation plan already consumed")
            return plan
        failure = next((key for key, value in self._pending.items()
                        if value == plan.id), None)
        if failure is None:
            raise ValueError("continuation plan already consumed")
        self._consumed_plans.add(plan.id)
        self._consumed_failures.add(failure)
        if plan.mode == REPLAN:
            self.replans_used += 1
            conflict = self._plan_conflicts[plan.id]
            self._replans_by_conflict[conflict] = (
                self._replans_by_conflict.get(conflict, 0) + 1)
            self.denied_resources.update(plan.denied_resources)
        return plan

    def record_effect(self, action: str, arguments: dict) -> None:
        self.completed_effects.append({
            "action": str(action), "arguments": dict(arguments or {})})

    def _visible_receipt_roots(
            self, state: RuntimeState, plan: ContinuationPlan
    ) -> set[str] | None:
        """Return the Receipt roots reachable from the current obligations.

        WRAP retains every active Receipt.  A fresh Agent only receives values
        that can feed its unresolved Root Effect, so unrelated observations do
        not enlarge or distract the continuation prompt.  Response replans are
        the exception: their output may legitimately depend on any surviving
        task Receipt.
        """
        if plan.action == "$response":
            return None

        sources = {
            source for obligation in plan.obligations
            for source in obligation.allowed_sources
        }
        if not sources:
            for clause in self.contract.clauses:
                if (isinstance(clause, EffectClause) and
                        clause.action == plan.action):
                    for spec in clause.effect_arguments.values():
                        sources.update(self._sources(spec))

        clauses = {
            clause.output_ref: clause for clause in self.contract.clauses
            if clause.output_ref
        }
        roots, seen, pending = set(), set(), list(sources)
        while pending:
            source = str(pending.pop())
            if source in seen:
                continue
            seen.add(source)
            binding = state.bindings.get(source.partition(".")[0])
            if binding is not None:
                roots.update(
                    str(ref).split("#", 1)[0] + "#"
                    for ref in binding.refs if "#" in str(ref))
            clause = clauses.get(source)
            if clause is not None:
                roots.update(receipt.digest + "#"
                             for receipt in state.receipts_for(clause.id))
                pending.extend(clause.sources)
        return roots

    def context(self, state: RuntimeState, plan: ContinuationPlan) -> dict:
        """Return the only state an adapter should expose to a fresh replanner."""
        visible = self._visible_receipt_roots(state, plan)
        return {
            "trusted_task": self.contract.task,
            "valid_receipts": [
                {"capability": receipt.capability,
                 "arguments": dict(receipt.arguments),
                 "value": receipt.value,
                 "ref": receipt.digest + "#"}
                for receipt in state.receipts
                if visible is None or receipt.digest + "#" in visible],
            "completed_effects": list(self.completed_effects),
            "denied_resources": sorted(self.denied_resources),
            "obligations": [item.to_dict() for item in plan.obligations],
            "retry_budget": max(
                0, self.max_total_replans - self.replans_used),
        }

    def close(self) -> dict:
        return {
            "plans": [plan.to_dict() for plan in self._plans.values()],
            "replans_used": self.replans_used,
            "replans_by_conflict": dict(self._replans_by_conflict),
            "denied_resources": sorted(self.denied_resources),
            "completed_effects": list(self.completed_effects),
        }
