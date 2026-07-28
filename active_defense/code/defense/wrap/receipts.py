"""Clause-local WRAP gates with provenance separated from gate verdicts."""
from __future__ import annotations

import hashlib
import json
import copy
from dataclasses import dataclass, field

from ..taskcontractor import Clause, TaskContract, is_clause_ref, parse_relation
from ..memory import argument_values_equal, schema_values_equal
from ..contract import AcquireClause, ClauseReceiptBinding


from .model import (ArgumentProvenance, GateResult, InstalledGate,
                    Observation, Provenance, _Resolved, _contains_value, _is_prose_node,
                    _nodes, _replace_pointer, _resolve_ref, _schema_accepts, _source_names,
                    _stable)
class ReceiptRuntimeMixin:
    @staticmethod
    def _call_key(source: str, arguments: dict) -> str:
        return _stable({"source": str(source), "arguments": dict(arguments or {})})

    def admit_observation_call(self, source: str, arguments: dict,
                               clause_id: str | None, call_id: str | None) -> bool:
        """Install one call-instance admission consumed by exactly one return."""
        clause = next((item for item in self.contract.clauses
                       if item.id == str(clause_id)), None)
        call_id = str(call_id or "")
        if (not call_id or call_id in self._pending_observation_calls or
                clause is None or clause.output_ref is None or
                str(source) not in clause.sources):
            return False
        self._pending_observation_calls[call_id] = (
            self._call_key(source, arguments), (clause.id,))
        return True

    def admit_effect_return(self, source: str, arguments: dict,
                            call_id: str | None,
                            effect_clause_id: str | None = None) -> bool:
        """Admit the receipt of this exact already-authorized effect call.

        The effect gate already established its semantic arguments. Binding the
        return repeats no placement judgment: it requires a structurally identical
        acquisition Clause and consumes the same concrete call id exactly once.
        """
        call_id = str(call_id or "")
        if not call_id or call_id in self._pending_observation_calls:
            return False
        effect_clause = next((clause for clause in self.contract.clauses
                              if clause.id == str(effect_clause_id) and
                              clause.effect is not None and
                              clause.effect.action == str(source)), None)
        if effect_clause is None:
            return False
        effect_arguments = dict(effect_clause.effect.arguments or {})
        matches = tuple(
            clause.id for clause in self.contract.clauses
            if clause.output_ref is not None and str(source) in clause.sources and
            dict(clause.arguments or {}) == effect_arguments)
        if not matches:
            surface = self.capabilities.get(str(source))
            if surface is None or not surface.committed_return:
                return False
            # A passed effect already fixes both action and arguments. Its
            # operator-attested return may therefore acquire a runtime output
            # without asking the Contract Agent to predict whether it is later
            # consumed. This extends evidence, never effect authority.
            clause = AcquireClause(
                f"c{len(self.contract.clauses)}",
                f"Acquire the return of the authorized {source} effect",
                str(source), effect_arguments,
                f"effect_return_{len(self.contract.clauses)}")
            self._install_dynamic_clauses((clause,))
            self.dynamic_contract_trace.append({
                "task_id": self.task_id, "parent": effect_clause.id,
                "mode": "effect-return", "capability": str(source),
                "clauses": [clause.to_dict()]})
            matches = (clause.id,)
        self._pending_observation_calls[call_id] = (
            self._call_key(str(source), arguments), matches)
        self._pending_effect_return_calls.add(call_id)
        self._pending_effect_return_parents[call_id] = effect_clause.id
        return True

    def quarantine_refs(self, refs) -> int:
        """Deny quarantined canonical nodes to every WRAP authority path."""
        before = len(self._quarantined_refs)
        self._quarantined_refs.update(str(ref) for ref in refs or () if str(ref))
        if len(self._quarantined_refs) != before:
            self._placement_cache = {}
        return len(self._quarantined_refs) - before

    def _valid_observations(self):
        """Return canonical receipts that may still be considered for binding.

        This is deliberately wider than the WRAP authority view: a freely
        executed pure observation starts here, but is not authority until a
        declared Acquire Clause deterministically binds its exact call.
        """

        rows = []
        for receipt in self.observations:
            if (receipt.digest in self._invalid_schema_receipts or
                    receipt.digest in self._superseded_receipts):
                continue
            value = receipt.value
            prefix = receipt.digest + "#"
            for ref in sorted(self._quarantined_refs):
                if ref.startswith(prefix):
                    value = _replace_pointer(value, ref[len(prefix):].split("@", 1)[0])
            rows.append(Observation(receipt.source, receipt.arguments,
                                    receipt.digest, value, receipt.task_id))
        return tuple(rows)

    def _authority_observations(self):
        """Return only receipts already owned by a task-local Clause binding."""
        bound = {
            digest for digests in self._bound_receipts.values()
            for digest in digests
        }
        return tuple(receipt for receipt in self._valid_observations()
                     if receipt.digest in bound)

    def _deterministic_call_match(self, clause: Clause, arguments: dict) -> bool:
        """Match a pure observation call from already-bound Clause values only."""
        specs = dict(clause.arguments or {})
        arguments = dict(arguments or {})
        capability_names = [source for source in clause.sources
                            if source in self.capabilities]
        surface = (self.capabilities.get(capability_names[0])
                   if len(capability_names) == 1 else None)
        required = set(getattr(surface, "required_arguments", ()) or ())
        if not required.issubset(arguments) or not set(arguments).issubset(specs):
            return False
        memo: dict[str, tuple[_Resolved, ...]] = {"$placements": {}}
        for name, spec in specs.items():
            if name not in arguments:
                # An omitted substrate-optional position is not a runtime value
                # and therefore needs no receipt equality witness.
                continue
            origins = _source_names(spec)
            if origins:
                expected = [
                    item for origin in origins
                    for item in self._lazy_values(origin, memo)
                ]
                if not expected or not any(
                        any(argument_values_equal(
                            surface, name, value, arguments.get(name))
                            for _path, value in _nodes(item.value))
                        for item in expected):
                    return False
                continue
            if isinstance(spec, dict) and set(spec) == {"literal"}:
                expected = spec["literal"]
            elif spec is None or isinstance(spec, (str, int, float, bool, list)):
                expected = spec
            else:
                return False
            if not argument_values_equal(surface, name, arguments.get(name), expected):
                return False
        return True

    def _bind_receipt(self, clause_id: str, receipt: Observation) -> bool:
        digests = self._bound_receipts.setdefault(str(clause_id), set())
        if receipt.digest in digests:
            return False
        # Preserve the append-only audit index while making authority
        # version-exact: a newer return for the same Clause call supersedes
        # the older mutable snapshot instead of accumulating both values.
        for prior in self.observations:
            if (prior.digest in digests and prior.source == receipt.source and
                    self._call_key(prior.source, prior.arguments) ==
                    self._call_key(receipt.source, receipt.arguments)):
                self._superseded_receipts.add(prior.digest)
        digests.add(receipt.digest)
        self.receipt_bindings.append(ClauseReceiptBinding(
            self.task_id, self._task_receipt.digest, self._contract_digest,
            str(clause_id),
            receipt.digest, receipt.source,
            hashlib.sha256(_stable(receipt.arguments).encode()).hexdigest()))
        return True

    def _reconcile_receipt_bindings(self) -> None:
        """Reach a deterministic fixed point over existing calls and Clause inputs."""
        changed = True
        while changed:
            changed = False
            for clause in self.contract.clauses:
                # A receipt can be promoted only by the Contract's explicit
                # outside-to-inside boundary. Merely matching a capability
                # name on another Clause type never creates authority.
                if not isinstance(clause, AcquireClause):
                    continue
                direct_sources = {source for source in clause.sources
                                  if not is_clause_ref(source) and
                                  source not in {"task", "runtime-context"} and
                                  not bool(getattr(
                                      self.capabilities.get(source), "effect", False))}
                if not direct_sources:
                    continue
                for receipt in self._valid_observations():
                    if (receipt.source in direct_sources and
                            receipt.digest not in self._bound_receipts.get(clause.id, set()) and
                            self._deterministic_call_match(clause, receipt.arguments)):
                        changed |= self._bind_receipt(clause.id, receipt)

    def observe(self, source: str, arguments: dict, value,
                call_id: str | None = None) -> Observation:
        """Append a canonical receipt and bind only deterministically admitted Clauses.

        Unbound observations may still be exposed to the target Agent, but they
        can never become WRAP authority during later backward resolution.
        """
        source, arguments = str(source), dict(arguments or {})
        receipt = self.receipt_recorder.issue(source, arguments, value)
        surface = self.capabilities.get(source)
        schema = getattr(surface, "output_schema", None)
        if schema is not None and not _schema_accepts(value, schema):
            self._invalid_schema_receipts.add(receipt.digest)
        call_id = str(call_id or "")
        pending = self._pending_observation_calls.pop(call_id, None)
        effect_return = call_id in self._pending_effect_return_calls
        self._pending_effect_return_calls.discard(call_id)
        effect_return_parent = self._pending_effect_return_parents.pop(
            call_id, "")
        clause_ids = ()
        if pending is not None and pending[0] == self._call_key(source, arguments):
            clause_ids = pending[1]
        if receipt.digest not in self._invalid_schema_receipts:
            for clause_id in sorted(clause_ids):
                self._bind_receipt(clause_id, receipt)
                if effect_return:
                    self._effect_return_receipts.add((str(clause_id), receipt.digest))
                    self._effect_return_origins[receipt.digest] = str(
                        effect_return_parent)
            # A later receipt can close a relation/domain and make an earlier call
            # deterministically attributable. Reconcile monotonically to a fixed point.
            self._reconcile_receipt_bindings()
        return receipt

    def observe_state(self, source, arguments, state_id, value):
        receipt = self.observe(source, arguments, value)
        self._state_status[receipt.digest] = self.state_store.restore(state_id, value)
        return receipt

    def context(self):
        allowed = {source for clause in self.contract.clauses for source in clause.sources
                   if not is_clause_ref(source)}
        return tuple(item for item in self.observations if item.source in allowed)

    @staticmethod
    def _refs_overlap(left: str, right: str) -> bool:
        """Return whether two exact receipt references overlap structurally."""
        left_digest, left_mark, left_path = str(left).partition("#")
        right_digest, right_mark, right_path = str(right).partition("#")
        if not left_mark or not right_mark or left_digest != right_digest:
            return False
        left_path, right_path = left_path.rstrip("/"), right_path.rstrip("/")
        return (left_path == right_path or
                not left_path or not right_path or
                left_path.startswith(right_path + "/") or
                right_path.startswith(left_path + "/"))

    def recover_exact_proposal(self, evidence, arguments: dict) -> dict:
        """Repair only literal conflicts while retaining already-proved values.

        The candidate is not authority: callers must submit it through the
        normal WRAP gate again. Any unresolved role or non-literal conflict
        makes exact recovery impossible.
        """
        clause_id = getattr(getattr(evidence, "provenance", None), "clause", None)
        gate = next((item for item in self.gates
                     if item.clause.id == str(clause_id)), None)
        if gate is None or tuple(getattr(evidence, "unresolved", ()) or ()):
            return {}
        conflicts = set(getattr(evidence, "conflicts", ()) or ())
        arguments = dict(arguments or {})
        recovered = {}
        for name, spec in gate.arguments.items():
            if isinstance(spec, dict) and set(spec) == {"literal"}:
                recovered[name] = spec["literal"]
                continue
            if name in conflicts or name not in arguments:
                return {}
            recovered[name] = arguments[name]
        return recovered

    def recovery_bindings(self, clause_id: str, excluded_refs=()) -> dict:
        """Recompute unique clean bindings without semantic inference.

        Recovery may positively re-anchor an Agent only on authority WRAP can
        reconstruct without the proposal-time Judge: trusted literals, exact
        receipt values, runtime context, and accepted closed relations.  The
        result is presentation-only; it does not mutate the Contract, receipt
        store, or installed gates.
        """
        gate = next((item for item in self.gates
                     if item.clause.id == str(clause_id)), None)
        if gate is None:
            return {}
        # Reuse the normal lazy evaluator with its semantic escape hatch
        # disabled.  This keeps closed-relation semantics identical without
        # introducing a second provenance implementation.
        runtime = copy.copy(self)
        runtime.placement_agent = None
        runtime._placement_cache = {}
        excluded = tuple(dict.fromkeys(str(item) for item in excluded_refs))
        memo: dict[str, tuple[_Resolved, ...]] = {}
        bindings = {}
        for name, spec in gate.arguments.items():
            origins = _source_names(spec)
            if not origins:
                literal = (spec.get("literal") if isinstance(spec, dict)
                           and set(spec) == {"literal"} else spec)
                bindings[name] = literal
                continue
            values = [
                item for origin in origins
                for item in runtime._lazy_values(origin, memo)
                if not any(
                    self._refs_overlap(ref, blocked)
                    for ref in item.refs for blocked in excluded)
            ]
            # A recovery anchor must be one exact scalar.  Structured carrier
            # projection and prose extraction remain semantic and therefore
            # deliberately do not qualify here.
            unique = {}
            for item in values:
                if isinstance(item.value, (dict, list, tuple, set)):
                    continue
                unique.setdefault(_stable(item.value), item.value)
            if len(unique) != 1:
                return {}
            bindings[name] = next(iter(unique.values()))
        return bindings
