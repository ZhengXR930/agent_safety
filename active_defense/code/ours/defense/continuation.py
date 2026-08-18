"""Deterministic continuation after a WRAP or PLANT refusal.

The controller is deliberately not an Agent.  It can only replay already
proved values, invalidate evidence, and expose machine-checkable obligations.
It never interprets the task, creates a Clause, or grants an Effect.
"""
from __future__ import annotations

from dataclasses import dataclass
import json

from code.ours.defense.contract import AcquireClause, EffectClause
from code.ours.defense.resolver import LazyResolver
from code.ours.defense.state import (CONTEXT_REF, GROUNDED_REF, QUERY_REF,
                                     SEMANTIC_REF, RuntimeState, digest)


REPAIR = "repair"
REPLAN = "replan"
ABORT = "abort"
RECOVERY_ENVELOPE_SCHEMA = "active-defense-recovery-v3"


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
class RecoveryEnvelope:
    """Runtime-attested public state for one fresh recovery Agent.

    The envelope contains no new authority.  It projects the original
    Contract and surviving Runtime witnesses into the smallest state needed
    to finish authorized work after a refusal.
    """

    trusted_task: str
    required_acquires: tuple[dict, ...] = ()
    remaining_effects: tuple[dict, ...] = ()
    evidence: tuple[dict, ...] = ()
    denied_resources: tuple[str, ...] = ()
    attempted_effects: tuple[dict, ...] = ()
    verified_effects: tuple[dict, ...] = ()

    def to_dict(self) -> dict:
        return {
            "schema": RECOVERY_ENVELOPE_SCHEMA,
            "trusted_task": self.trusted_task,
            "required_acquires": [dict(item)
                                  for item in self.required_acquires],
            "remaining_effects": [dict(item)
                                  for item in self.remaining_effects],
            "evidence": [dict(item) for item in self.evidence],
            "denied_resources": list(self.denied_resources),
            "attempted_effects": [dict(item)
                                  for item in self.attempted_effects],
            "verified_effects": [dict(item)
                                 for item in self.verified_effects],
        }


def render_recovery_task(task: str, envelope: dict) -> str:
    """Render one shared Tool/MCP/Skill recovery protocol."""
    fields = {
        "schema", "trusted_task", "required_acquires",
        "remaining_effects", "evidence", "denied_resources",
        "attempted_effects", "verified_effects",
    }
    if (not isinstance(envelope, dict) or set(envelope) != fields or
            envelope.get("schema") != RECOVERY_ENVELOPE_SCHEMA):
        raise ValueError("invalid RecoveryEnvelope")
    return (
        str(task) +
        "\n\nRECOVERY_ENVELOPE (runtime-attested JSON; no new authority):\n" +
        json.dumps(envelope, ensure_ascii=False, default=str) +
        "\nExecute only the listed required_acquires needed for a "
        "remaining_effect, then complete that remaining_effect. Reuse every "
        "bound_argument exactly. Resolve unresolved_arguments only from the "
        "trusted task and listed evidence. attempted_effects are diagnostic "
        "only and do not prove task completion; use their summaries only to "
        "avoid repeating failed work. Do not repeat verified_effects; use "
        "their summaries as already accepted progress. Do not use "
        "denied_resources."
    )


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
    why_not_supported: str = ""

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
        if self.why_not_supported:
            value["why_not_supported"] = self.why_not_supported
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

    def __init__(self, contract, *, max_replans: int = 1,
                 explanation_agent=None):
        self.contract = contract
        self.explanation_agent = explanation_agent
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
        self.attempted_effects: list[dict] = []
        self.verified_effects: list[dict] = []
        self._receipt_views: dict[str, object] = {}
        self._plans: dict[str, ContinuationPlan] = {}
        self._pending: dict[str, str] = {}
        self._consumed_failures: set[str] = set()
        self._consumed_plans: set[str] = set()
        self._plan_conflicts: dict[str, str] = {}
        self._restricted_arguments: set[tuple[str, str, str]] = set()
        self._explanation_cache: dict[str, str] = {}

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

    def _conflict(self, action: str, arguments: dict, reason: str, events) -> str:
        """Stable retry identity for one failed candidate value."""
        if events:
            category, action = "plant-commitment", "*"
            value_key = ""
        elif reason.startswith("unauthorized-action:"):
            category, action = "unauthorized-action", "*"
            value_key = ""
        else:
            category = reason.split(":", 1)[0]
            argument = self._argument_from_reason(reason)
            value_key = (digest(arguments.get(argument))
                         if argument and argument in arguments else "")
        return digest({
            "action": action,
            "category": category,
            "argument": self._argument_from_reason(reason),
            "value": value_key,
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
            return (Obligation(
                kind, action,
                why_not_supported=self._explain_obligation(
                    kind, action, "", (), None, reason)),)
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
            return (Obligation(
                "missing_authority", action,
                why_not_supported=self._explain_obligation(
                    "missing_authority", action, "", (), None, reason)),)
        if argument:
            return (Obligation(
                "missing_binding", action, argument, sources,
                arguments.get(argument),
                self._explain_obligation(
                    "missing_binding", action, argument, sources,
                    arguments.get(argument), reason)),)
        if reason.startswith("unauthorized-content-atom:"):
            return (Obligation(
                "invalid_dependency", action,
                invalid_value=reason.split(":", 1)[1],
                why_not_supported=self._explain_obligation(
                    "invalid_dependency", action, "", (),
                    reason.split(":", 1)[1], reason)),)
        return (Obligation(
            "revalidate_effect", action,
            why_not_supported=self._explain_obligation(
                "revalidate_effect", action, "", (), None, reason)),)

    @staticmethod
    def _public_summary(value) -> str:
        if value is None:
            return ""
        if isinstance(value, str):
            text = value.replace("\n", " ").strip()
            return text[:180] + ("..." if len(text) > 180 else "")
        if isinstance(value, (int, float, bool)):
            return repr(value)
        if isinstance(value, dict):
            keys = ",".join(map(str, sorted(value)[:8]))
            return f"object with keys: {keys}"
        if isinstance(value, (list, tuple)):
            return f"{type(value).__name__} with {len(value)} items"
        return type(value).__name__

    def _fallback_explanation(
        self, kind: str, action: str, argument: str, sources: tuple[str, ...],
        invalid_value, reason: str,
    ) -> str:
        slot = f" argument '{argument}'" if argument else ""
        source_text = (
            " from " + ", ".join(sources)
            if sources else " from the trusted task or verified runtime state")
        value = self._public_summary(invalid_value)
        value_text = f" The attempted value was {value!r}." if value else ""
        return (
            f"The attempted {action}{slot} is not sufficiently supported"
            f"{source_text} for the trusted task and verified runtime state. "
            f"Internal refusal: {reason}.{value_text}"
        )

    def _explain_obligation(
        self, kind: str, action: str, argument: str,
        sources: tuple[str, ...], invalid_value, reason: str,
    ) -> str:
        context = {
            "trusted_task": self.contract.task,
            "kind": str(kind),
            "action": str(action),
            "argument": str(argument),
            "allowed_sources": list(map(str, sources or ())),
            "invalid_value_summary": self._public_summary(invalid_value),
            "internal_reason": str(reason),
        }
        key = digest(context)
        if key in self._explanation_cache:
            return self._explanation_cache[key]
        explanation = ""
        if callable(self.explanation_agent):
            try:
                explanation = str(self.explanation_agent(context)).strip()
            except Exception:
                explanation = ""
        if not explanation:
            explanation = self._fallback_explanation(
                kind, action, argument, sources, invalid_value, reason)
        self._explanation_cache[key] = explanation
        return explanation

    def restricted_arguments_for(
        self, action: str, arguments: dict | None = None,
    ) -> tuple[str, ...]:
        """Arguments that may not close through model-only semantic support.

        The restriction is value-scoped. A failed candidate must not be
        laundered by restating the same value through semantic support, but one
        bad helper proposal should not poison every later task-local helper for
        the same action argument.
        """
        action = str(action)
        arguments = dict(arguments or {})
        result = []
        for item_action, argument, value_key in self._restricted_arguments:
            if item_action != action:
                continue
            if arguments:
                current = (digest(arguments.get(argument))
                           if argument in arguments else "")
                if value_key and current != value_key:
                    continue
            result.append(argument)
        return tuple(sorted(
            dict.fromkeys(result)))

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
        conflict = self._conflict(action, arguments, reason, events)
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
            unfinished = (bool(self._remaining_effect_clauses(state))
                          if root_effects else bool(root_obligations))
            unauthorized = reason.startswith("unauthorized-action:")
            if unauthorized:
                # An unknown action has no repairable value.  Before any
                # remaining Root Effect succeeds, one fresh Agent may instead
                # complete the Contract's unfinished work.  The denied action
                # identity is episode-local and can never be retried.
                can_replan = bool(
                    unfinished and
                    action not in self.denied_resources)
            else:
                can_replan = bool(
                    ((events or has_root) and unfinished) or
                    action == "$response")
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
            for obligation in plan.obligations:
                argument = obligation.argument
                if argument:
                    value_key = (digest(obligation.invalid_value)
                                 if obligation.invalid_value is not None else "")
                    self._restricted_arguments.add(
                        (plan.action, argument, value_key))
        return plan

    def record_effect(self, action: str, arguments: dict, *,
                      verified: bool = False) -> None:
        row = {"action": str(action), "arguments": dict(arguments or {})}
        self.attempted_effects.append(row)
        if verified:
            self.verified_effects.append(dict(row))

    @staticmethod
    def _effect_summary(item: dict, *, verified: bool) -> dict:
        action = str(item.get("action", ""))
        arguments = dict(item.get("arguments") or {})
        parts = []
        if arguments.get("path"):
            parts.append(f"path={arguments['path']!r}")
        if "argv" in arguments:
            argv = arguments.get("argv")
            if isinstance(argv, list):
                parts.append(f"argv_count={len(argv)}")
            else:
                parts.append("argv=non-list")
        if "content" in arguments:
            content = arguments.get("content")
            if isinstance(content, str):
                parts.append(f"content_length={len(content)}")
            else:
                parts.append("content=non-string")
        omitted = [
            key for key in sorted(arguments)
            if key not in {"path", "argv", "content"}
        ]
        if omitted:
            parts.append("other_args=" + ",".join(omitted))
        detail = "; ".join(parts) if parts else "no public arguments"
        status = "verified" if verified else "attempted"
        return {
            "action": action,
            "summary": f"{status} {action}: {detail}",
        }

    def record_receipt_view(self, receipt, value) -> None:
        """Freeze the exact PLANT-decorated view previously shown to Agent."""
        self._receipt_views[str(receipt.digest)] = value

    def _receipt_roots(self, state: RuntimeState, sources) -> set[str]:
        """Project internal Clause sources to their concrete Receipt roots."""
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

    def _resolved_spec(self, resolver: LazyResolver, spec):
        """Return one Runtime-determined Effect argument, if it exists."""
        if isinstance(spec, dict) and set(spec) == {"literal"}:
            return True, spec["literal"], (QUERY_REF,)
        if isinstance(spec, dict) and "from" in spec:
            sources = self._sources(spec)
            resolved, refs = [], []
            for source in sources:
                unique = {digest(row.value): row
                          for row in resolver.values(source)}
                if len(unique) != 1:
                    return False, None, ()
                row = next(iter(unique.values()))
                resolved.append(row.value)
                refs.extend(row.refs)
            if not resolved or any(
                    type(value) is not type(resolved[0]) or
                    value != resolved[0] for value in resolved[1:]):
                return False, None, ()
            return True, resolved[0], tuple(dict.fromkeys(refs))
        if not isinstance(spec, dict):
            return True, spec, (QUERY_REF,)
        return False, None, ()

    @staticmethod
    def _pointer(value, pointer: str):
        current = value
        for raw in str(pointer).split("/")[1:] if pointer else ():
            part = raw.replace("~1", "/").replace("~0", "~")
            if isinstance(current, dict) and part in current:
                current = current[part]
            elif isinstance(current, (list, tuple)) and part.isdigit() and \
                    int(part) < len(current):
                current = current[int(part)]
            else:
                return False, None
        return True, current

    def _agent_safe_binding(self, state: RuntimeState, value, refs) -> bool:
        """Whether replaying this Binding cannot bypass a decorated carrier."""
        allowed = {QUERY_REF, GROUNDED_REF, CONTEXT_REF}
        receipts = {receipt.digest: receipt for receipt in state.receipts}
        for ref in refs:
            ref = str(ref)
            if "#" not in ref:
                if ref not in allowed:
                    return False
                continue
            root, pointer = ref.split("#", 1)
            receipt, view = receipts.get(root), self._receipt_views.get(root)
            if receipt is None or root not in self._receipt_views:
                return False
            raw_ok, raw_value = self._pointer(receipt.value, pointer)
            view_ok, view_value = self._pointer(view, pointer)
            if not (raw_ok and view_ok and
                    type(raw_value) is type(view_value) and
                    raw_value == view_value):
                return False
        return bool(refs) and SEMANTIC_REF not in refs

    def _remaining_effect_clauses(self, state: RuntimeState):
        """Remove only Effect instances already attested as successful."""
        resolver = LazyResolver(state, self.contract)
        verified = [dict(item) for item in self.verified_effects]
        remaining = []
        for clause in self.contract.clauses:
            if not isinstance(clause, EffectClause):
                continue
            matched = None
            for index, row in enumerate(verified):
                if str(row.get("action", "")) != clause.action:
                    continue
                arguments = dict(row.get("arguments") or {})
                known = [
                    (name, value)
                    for name, spec in clause.effect_arguments.items()
                    for ok, value, _refs in (
                        self._resolved_spec(resolver, spec),)
                    if ok]
                if ((known or not clause.effect_arguments) and
                        all(name in arguments and
                       type(arguments[name]) is type(value) and
                       arguments[name] == value for name, value in known)):
                    matched = index
                    break
            if matched is None:
                remaining.append(clause)
            else:
                verified.pop(matched)
        return tuple(remaining)

    def _terminal_sources(self) -> tuple[str, ...]:
        """Return Contract outputs that feed the read/compute-only response."""
        produced = {
            clause.output_ref for clause in self.contract.clauses
            if clause.output_ref}
        consumed = {
            str(source) for clause in self.contract.clauses
            for source in clause.sources if str(source) in produced}
        return tuple(sorted(produced - consumed))

    def _recovery_sources(self, state: RuntimeState) -> tuple[str, ...]:
        remaining = self._remaining_effect_clauses(state)
        if remaining:
            return tuple(dict.fromkeys(
                source for clause in remaining
                for spec in clause.effect_arguments.values()
                for source in self._sources(spec)))
        if not any(isinstance(clause, EffectClause)
                   for clause in self.contract.clauses):
            return self._terminal_sources()
        return ()

    def _required_acquire_clauses(self, state: RuntimeState, sources):
        """Topologically project unresolved Acquires reachable from roots."""
        by_ref = {clause.output_ref: clause for clause in self.contract.clauses
                  if clause.output_ref}
        visited, output = set(), []

        def visit(source):
            clause = by_ref.get(str(source))
            if clause is None or clause.id in visited:
                return
            visited.add(clause.id)
            for upstream in clause.sources:
                visit(upstream)
            if (isinstance(clause, AcquireClause) and
                    not state.receipts_for(clause.id) and
                    clause.capability not in self.denied_resources):
                output.append(clause)

        for source in sources:
            visit(source)
        return tuple(output)

    @staticmethod
    def _obligation_explanation(plan: ContinuationPlan, action: str,
                                argument: str) -> str:
        """Return the advisory recovery explanation for this unresolved slot."""
        action, argument = str(action), str(argument)
        for obligation in plan.obligations:
            if (obligation.action == action and
                    obligation.argument == argument and
                    obligation.why_not_supported):
                return obligation.why_not_supported
        for obligation in plan.obligations:
            if (obligation.action == action and not obligation.argument and
                    obligation.why_not_supported):
                return obligation.why_not_supported
        return ""

    def _argument_role(self, state: RuntimeState, plan: ContinuationPlan,
                       action: str, name: str, spec,
                       evidence_ids: dict[str, str]) -> dict:
        """Project one unresolved Contract role without exposing Clause ids."""
        by_ref = {clause.output_ref: clause for clause in self.contract.clauses
                  if clause.output_ref}
        sources = self._sources(spec)
        roles = []
        for source in sources:
            clause = by_ref.get(str(source))
            instruction = str(getattr(clause, "instruction", "")).strip()
            if instruction and instruction not in roles:
                roles.append(instruction)
        roots = self._receipt_roots(state, sources)
        evidence = [evidence_id for root, evidence_id in evidence_ids.items()
                    if root in roots]
        value = {"argument": str(name)}
        if roles:
            value["role_requirements"] = roles
        if evidence:
            value["evidence_ids"] = evidence
        explanation = self._obligation_explanation(plan, action, name)
        if explanation:
            value["why_not_supported"] = explanation
        return value

    def _remaining_effects(self, state: RuntimeState,
                           plan: ContinuationPlan,
                           evidence_ids: dict[str, str]) -> tuple[dict, ...]:
        resolver = LazyResolver(state, self.contract)
        output = []
        for clause in self._remaining_effect_clauses(state):
            bound, unresolved = {}, []
            for name, spec in clause.effect_arguments.items():
                ok, value, refs = self._resolved_spec(resolver, spec)
                if ok and self._agent_safe_binding(state, value, refs):
                    bound[name] = value
                else:
                    unresolved.append(self._argument_role(
                        state, plan, clause.action, name, spec, evidence_ids))
            output.append({
                "action": clause.action,
                "instruction": clause.instruction,
                "bound_arguments": bound,
                "unresolved_arguments": unresolved,
            })

        if output or (plan.action != "$response" and any(
                isinstance(clause, EffectClause)
                for clause in self.contract.clauses)):
            return tuple(output)

        terminal = self._root_obligations()
        roles = []
        sources = ()
        for obligation in terminal:
            if obligation.action == "$response":
                sources = obligation.allowed_sources
        by_ref = {clause.output_ref: clause for clause in self.contract.clauses
                  if clause.output_ref}
        for source in sources:
            instruction = str(getattr(
                by_ref.get(str(source)), "instruction", "")).strip()
            if instruction and instruction not in roles:
                roles.append(instruction)
        roots = self._receipt_roots(state, sources)
        evidence = [evidence_id for root, evidence_id in evidence_ids.items()
                    if root in roots]
        content = {"argument": "content"}
        if roles:
            content["role_requirements"] = roles
        if evidence:
            content["evidence_ids"] = evidence
        explanation = self._obligation_explanation(
            plan, "$response", "content")
        if explanation:
            content["why_not_supported"] = explanation
        return ({
            "action": "$response",
            "instruction": "Answer the trusted task from surviving evidence.",
            "bound_arguments": {},
            "unresolved_arguments": [content],
        },)

    def _required_acquires(self, state: RuntimeState, plan: ContinuationPlan,
                           sources,
                           evidence_ids: dict[str, str]) -> tuple[dict, ...]:
        resolver = LazyResolver(state, self.contract)
        output = []
        for clause in self._required_acquire_clauses(state, sources):
            bound, unresolved = {}, []
            for name, spec in clause.call_arguments.items():
                ok, value, refs = self._resolved_spec(resolver, spec)
                if ok and self._agent_safe_binding(state, value, refs):
                    bound[name] = value
                else:
                    unresolved.append(self._argument_role(
                        state, plan, clause.capability, name, spec,
                        evidence_ids))
            output.append({
                "capability": clause.capability,
                "instruction": clause.instruction,
                "bound_arguments": bound,
                "unresolved_arguments": unresolved,
            })
        return tuple(output)

    def context(self, state: RuntimeState, plan: ContinuationPlan) -> dict:
        """Issue the only state an adapter may expose to a recovery Agent."""
        sources = self._recovery_sources(state)
        visible = self._receipt_roots(state, sources)
        receipts = [receipt for receipt in state.receipts
                    if receipt.digest in self._receipt_views and
                    receipt.digest + "#" in visible]
        evidence_ids = {
            receipt.digest + "#": "E" + str(index)
            for index, receipt in enumerate(receipts)}
        return RecoveryEnvelope(
            trusted_task=self.contract.task,
            required_acquires=self._required_acquires(
                state, plan, sources, evidence_ids),
            remaining_effects=self._remaining_effects(
                state, plan, evidence_ids),
            evidence=tuple(
                {"evidence_id": evidence_ids[receipt.digest + "#"],
                 "capability": receipt.capability,
                 "value": self._receipt_views[receipt.digest]}
                for receipt in receipts),
            denied_resources=tuple(sorted(self.denied_resources)),
            attempted_effects=tuple(
                self._effect_summary(item, verified=False)
                for item in self.attempted_effects),
            verified_effects=tuple(
                self._effect_summary(item, verified=True)
                for item in self.verified_effects),
        ).to_dict()

    def close(self) -> dict:
        return {
            "plans": [plan.to_dict() for plan in self._plans.values()],
            "replans_used": self.replans_used,
            "replans_by_conflict": dict(self._replans_by_conflict),
            "denied_resources": sorted(self.denied_resources),
            "restricted_arguments": [
                {"action": action, "argument": argument, "value": value}
                for action, argument, value in sorted(self._restricted_arguments)
            ],
            "attempted_effects": list(self.attempted_effects),
            "verified_effects": list(self.verified_effects),
        }
