"""Clause-local WRAP gates with provenance separated from gate verdicts."""
from __future__ import annotations

import hashlib

from ..contract import (AcquireClause, EffectBinding, EffectClause,
                        is_clause_ref)
from ..memory import argument_values_equal
from .model import (ArgumentProvenance, GateResult, InstalledGate, Provenance,
                    _Resolved, _source_names, _stable)


class GateRuntimeMixin:
    def evidence(self, action: str, arguments: dict) -> GateResult:
        surface = self.capabilities.get(str(action))
        matches = [(gate, self._lazy_check(
            gate, dict(arguments or {}), omit_uncontracted_optional=True))
                   for gate in self._gates_by_action.get(str(action), ())
                   if surface is not None and surface.effect]
        complete = [result for _clause, result in matches if result.complete]
        if len(complete) == 1: return complete[0]
        if len(complete) > 1:
            # Clause ids are program locations, not distinct authority when all
            # runtime argument origins are identical. Avoid an Approval caused
            # solely by duplicated equivalent blueprints.
            signatures = {
                _stable({name: origin.to_dict()
                         for name, origin in result.provenance.arguments.items()})
                for result in complete
            }
            if len(signatures) == 1:
                return complete[0]
            merged = {}
            for result in complete:
                for name, origin in result.provenance.arguments.items():
                    prior = merged.get(name, ArgumentProvenance())
                    merged[name] = ArgumentProvenance(
                        tuple(dict.fromkeys(prior.sources + origin.sources)),
                        tuple(dict.fromkeys(prior.inputs + origin.inputs)))
            return GateResult(Provenance(action=action, arguments=merged),
                              unresolved=("$clause",))
        if matches:
            return min((result for _gate, result in matches),
                       key=lambda x: len(x.conflicts) + len(x.unresolved))
        # The trusted Contract is the complete action-authority boundary.
        # Runtime observations may instantiate arguments and outputs, but can
        # never add an action.  Absence is therefore a definite control
        # conflict, not an evidence gap requiring user interpretation.
        return GateResult(Provenance(action=action), conflicts=("$action",))

    def _lazy_check(self, gate: InstalledGate, arguments: dict,
                    omit_uncontracted_optional: bool = False) -> GateResult:
        """Reconcile one proposal against a gate and one receipt snapshot."""
        clause, action = gate.clause, gate.action
        surface = self.capabilities.get(action)
        allowed = set(getattr(surface, "arguments", ()) or ())
        required = set(getattr(surface, "required", ()) or ())
        specs = dict(gate.arguments)
        conflicts, unresolved, provenance_args = [], [], {}
        memo: dict[str, tuple[_Resolved, ...]] = {}

        for name in arguments:
            if allowed and name not in allowed:
                conflicts.append(name)
            elif name not in specs and not (
                    omit_uncontracted_optional and name not in required):
                # A required position missing from the trusted Contract is an
                # evidence gap. It is not authorized by every Clause source.
                specs[name] = "unknown"

        placement_specs = {
            name: spec for name, spec in specs.items()
            if not (name in arguments and isinstance(arguments[name], str) and
                    surface is not None and surface.grammars(name) is not None)
        }
        memo["$placements"] = self._proposal_placements(
            action, arguments, placement_specs)
        for name, spec in specs.items():
            if name not in arguments:
                if name in required:
                    unresolved.append(name)
                continue
            if allowed and name not in allowed:
                continue
            proposed = arguments[name]
            grammars = surface.grammars(name) if surface is not None else None
            if grammars is not None and isinstance(proposed, str):
                status, refs = self._content_references(
                    clause, proposed, grammars)
                provenance_args[name] = ArgumentProvenance(
                    ("content",), refs)
                if status == "conflict":
                    conflicts.append(name)
                elif status != "supported":
                    unresolved.append(name)
                continue
            if spec != "unknown" and (
                    spec is None or isinstance(
                        spec, (str, int, float, bool, list, tuple))):
                spec = {"literal": spec}
            if isinstance(spec, dict) and set(spec) == {"literal"}:
                refs = (self._task_receipt.digest + "#",)
                provenance_args[name] = ArgumentProvenance(("task",), refs)
                if argument_values_equal(surface, name, proposed, spec["literal"]):
                    continue
                conflicts.append(name)
                continue
            if spec == "unknown":
                provenance_args[name] = ArgumentProvenance(("unknown",), ())
                unresolved.append(name)
                continue
            origins = _source_names(spec)
            if not origins:
                provenance_args[name] = ArgumentProvenance((), ())
                unresolved.append(name)
                continue
            status, refs = "supported", []
            for origin in origins:
                if origin == "runtime-context":
                    value = self._context_value(action, name)
                    if value is None:
                        status = "uncertain"
                        break
                    expected, node_ref = value
                    refs.append(node_ref)
                    if not argument_values_equal(surface, name, expected, proposed):
                        status = "conflict"
                        break
                elif is_clause_ref(origin):
                    local_status, local_refs = self._lazy_argument(
                        origin, proposed, memo, surface, name)
                    refs.extend(local_refs)
                    if local_status != "supported":
                        status = local_status
                        break
                else:
                    # Runtime authority may not jump directly from a capability
                    # name to an effect. It must pass through a bound Clause output.
                    status = "uncertain"
                    break
            provenance_args[name] = ArgumentProvenance(
                origins, tuple(dict.fromkeys(refs)))
            if status == "conflict":
                conflicts.append(name)
            elif status != "supported" or not refs:
                unresolved.append(name)
        return GateResult(
            Provenance(clause.id, action, provenance_args),
            tuple(dict.fromkeys(conflicts)),
            tuple(dict.fromkeys(unresolved)),
        )


    def bind_effect(self, result: GateResult, arguments: dict,
                    call_id: str | None = None) -> bool:
        """Record one effect authorization only after the outer detector Passes."""
        if not result.complete:
            return False
        clause = next((item for item in self.contract.clauses
                       if item.id == result.clause), None)
        if not isinstance(clause, EffectClause):
            grant = self._approval_grants.pop(str(result.clause), None)
            if grant is None:
                return False
            clause = grant["clause"]
            digest = hashlib.sha256(
                _stable(dict(arguments or {})).encode()).hexdigest()
            if (clause.action != result.provenance.action or
                    digest != grant["arguments_digest"]):
                self._approval_grants[clause.id] = grant
                return False
            self.gates = tuple(gate for gate in self.gates
                               if gate.clause.id != clause.id)
            self._gates_by_action[clause.action] = tuple(
                gate for gate in self._gates_by_action.get(clause.action, ())
                if gate.clause.id != clause.id)
            self._approval_effect_bindings.append({
                "type": "approval-effect", "task_id": self.task_id,
                "action": clause.action, "proposal_digest": grant["proposal_digest"],
                "arguments_digest": digest, "call_id": str(call_id or "")})
            return True
        refs = tuple(sorted(
            (str(name), tuple(dict.fromkeys(origin.inputs)))
            for name, origin in result.provenance.arguments.items()))
        return self.binding_store.add(EffectBinding(
            self.task_id, self._task_receipt.digest, self._contract_digest,
            clause.id, clause.action,
            hashlib.sha256(_stable(dict(arguments or {})).encode()).hexdigest(),
            refs, str(call_id or "")))

    def has_effect_gate(self, action: str) -> bool:
        return bool(self._gates_by_action.get(str(action)))

    def requires_effect_gate(self, action: str) -> bool:
        """Whether the operator says the receipt exists only after a commit."""
        surface = self.capabilities.get(str(action))
        return bool(surface is not None and surface.effect and
                    not surface.observation)

    def executable_arguments(self, action: str, arguments: dict,
                             clause_id: str | None) -> dict:
        """Remove optional positions outside the selected Contract gate.

        PLANT and Detector inspect the original proposal first. This method is
        called only after Pass, immediately before substrate commit, so an
        uncontracted optional field can neither expand authority nor cause a
        synthetic Approval.
        """
        arguments = dict(arguments or {})
        surface = self.capabilities.get(str(action))
        required = set(getattr(surface, "required", ()) or ())
        gates = [gate for gate in self._gates_by_action.get(str(action), ())
                 if gate.clause.id == clause_id]
        if len(gates) != 1:
            return arguments
        contracted = set(gates[0].arguments)
        return {name: value for name, value in arguments.items()
                if name in contracted or name in required}

    def intermediate_evidence(self, action: str, arguments: dict,
                              remember: bool = True) -> GateResult:
        """Check a dual-use observation call without assigning its return.

        Pure observations never call this method. For a manifest-declared
        commit-capable observation, the Contract may still pre-authorize the
        call shape through an output Clause; successful returns remain passive
        receipts and gain no Clause ownership.
        """
        surface = self.capabilities.get(str(action))
        if surface is None or not surface.observation:
            return GateResult(
                Provenance(action=str(action)), unresolved=("$intermediate",))
        results = []
        for clause in self._source_clauses.get(str(action), ()):
            if not isinstance(clause, AcquireClause):
                continue
            memo: dict[str, tuple[_Resolved, ...]] = {}
            conflicts, unresolved, provenance_args = [], [], {}
            specs = dict(clause.arguments)
            memo["$placements"] = self._proposal_placements(
                str(action), arguments, specs)
            if not specs and arguments:
                unresolved.extend(map(str, arguments))
            for name, spec in specs.items():
                if name not in arguments:
                    unresolved.append(name)
                    continue
                proposed = arguments[name]
                origins = _source_names(spec)
                local_argument_refs = []
                if origins:
                    status = "supported"
                    for origin in origins:
                        if not is_clause_ref(origin):
                            status = "uncertain"
                            break
                        local_status, local_refs = self._lazy_argument(
                            origin, proposed, memo)
                        local_argument_refs.extend(local_refs)
                        if local_status != "supported":
                            status = local_status
                            break
                    if status == "conflict":
                        conflicts.append(name)
                    elif status != "supported":
                        unresolved.append(name)
                else:
                    literal = (spec.get("literal") if isinstance(spec, dict)
                               and set(spec) == {"literal"} else spec)
                    local_argument_refs.append(self._task_receipt.digest + "#")
                    if not argument_values_equal(surface, name, literal, proposed):
                        conflicts.append(name)
                provenance_args[name] = ArgumentProvenance(
                    origins or ("task",),
                    tuple(dict.fromkeys(local_argument_refs)))
            provenance = Provenance(clause.id, str(action), provenance_args)
            results.append(GateResult(
                provenance, tuple(dict.fromkeys(conflicts)),
                tuple(dict.fromkeys(unresolved))))
        complete = [item for item in results if item.complete]
        if len(complete) == 1:
            return complete[0]
        if len(complete) > 1:
            return GateResult(
                Provenance(action=str(action)), unresolved=("$clause",))
        if results:
            return min(results, key=lambda item:
                       len(item.conflicts) + len(item.unresolved))
        return GateResult(
            Provenance(action=str(action)), unresolved=("$intermediate",))

    def has_declared_intermediate(self, action):
        surface = self.capabilities.get(str(action))
        return bool(surface and surface.observation and any(
            isinstance(clause, AcquireClause) and
            clause.capability == str(action)
            for clause in self.contract.clauses))

    def declared_clause_ids(self, action):
        """Task-time Clause scopes in which this capability may participate."""
        ids = {gate.id for gate in self._gates_by_action.get(str(action), ())}
        ids.update(clause.id for clause in self._source_clauses.get(str(action), ()))
        return frozenset(ids)

    def record_state(self, state_id, value, arguments, result: GateResult):
        if not result.complete: return False
        self.state_store.record(state_id, value, True)
        return True
