"""Deterministic runtime evidence growth under immutable Root Effect authority."""
from __future__ import annotations

import hashlib
import re

from ..contract import (AcquireClause, ConditionalClause, DeriveClause,
                        EffectClause)
from ..memory import argument_value_within_scope, argument_values_equal
from .model import InstalledGate, _Resolved, _contains_value, _nodes, _stable


def _value_kind(value) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, (int, float)):
        return "number"
    if isinstance(value, str):
        return "string"
    if isinstance(value, (list, tuple)):
        return "array"
    if isinstance(value, dict):
        return "object"
    return type(value).__name__


def _safe_name(value: str) -> str:
    text = re.sub(r"[^A-Za-z0-9_]+", "_", str(value)).strip("_").lower()
    return text[:48] or "value"


def _literal_values(value):
    if isinstance(value, dict):
        if set(value) == {"literal"}:
            yield value["literal"]
            return
        for child in value.values():
            yield from _literal_values(child)
    elif isinstance(value, (list, tuple)):
        for child in value:
            yield from _literal_values(child)


def _task_exact_entities(task: str):
    """Extract only delimited URL and path entities; never arbitrary substrings."""
    pattern = r"https?:\/\/[^\s,;]+|www\.[^\s,;]+|\/[A-Za-z0-9._\/-]+"
    return {item.rstrip(".,;:!?)]}") for item in re.findall(pattern, str(task or ""))}


def _receipt_contains_constructible(receipt, value) -> bool:
    """Whether the current closed proof algebra can replay value."""
    if _contains_value(receipt.value, value):
        return True
    # A one-element list is the closed singleton operator over one exact
    # node/span.  Larger compositions are not advertised until the Contract
    # algebra can represent their order explicitly.
    if isinstance(value, (list, tuple)):
        return len(value) == 1 and _receipt_contains_constructible(receipt, value[0])
    if isinstance(value, dict):
        return False
    return bool(isinstance(value, str) and value and any(
        isinstance(node, str) and value in node
        for _path, node in _nodes(receipt.value)))


def _constructible_refs(receipts, value):
    """Enumerate exact replay witnesses from the closed proof algebra."""
    target = (value[0] if isinstance(value, (list, tuple)) and
              len(value) == 1 else value)
    if isinstance(target, (dict, list, tuple)):
        return ()
    refs = []
    for receipt in receipts:
        for path, node in _nodes(receipt.value):
            base = receipt.digest + "#" + path
            if node == target:
                refs.append((base, receipt))
                continue
            if not (isinstance(target, str) and target and
                    isinstance(node, str)):
                continue
            start = 0
            while True:
                position = node.find(target, start)
                if position < 0:
                    break
                refs.append((base + "@%d:%d" % (
                    position, position + len(target)), receipt))
                start = position + max(1, len(target))
    return tuple(refs)



def _value_contains_constructible(container, value) -> bool:
    class _Slice:
        pass
    holder = _Slice()
    holder.value = container
    return _receipt_contains_constructible(holder, value)




class DynamicExpansionRuntimeMixin:
    """Grow an execution graph without changing the immutable Root authority."""

    def _trusted_literal_candidate(self, action: str, name: str, value) -> bool:
        surface = self.capabilities.get(str(action))
        if any(argument_values_equal(surface, name, item, value)
               for clause in self._root_effect_clauses
               for item in _literal_values(clause.to_dict())):
            return True
        if any(argument_values_equal(surface, name, item, value)
               for clause in self.contract.clauses
               for item in _literal_values(clause.to_dict())):
            return True
        if not isinstance(value, (str, int, float)):
            return False
        text = str(value)
        if not text:
            return False
        if isinstance(value, str):
            return value in _task_exact_entities(self.contract.task)
        return re.search(r"(?<![0-9.])" + re.escape(text) + r"(?![0-9.])",
                         self.contract.task) is not None

    def _trusted_scoped_candidate(self, action: str, name: str, value) -> bool:
        surface = self.capabilities.get(str(action))
        return any(argument_value_within_scope(surface, name, item, value)
                   for clause in self.contract.clauses
                   for item in _literal_values(clause.to_dict()))

    def _receipts_for_output(self, ref: str, seen=None):
        seen = set(seen or ())
        if ref in seen:
            return ()
        seen.add(ref)
        producer = next((clause for clause in self.contract.clauses
                         if clause.output_ref == ref), None)
        if producer is None:
            return ()
        receipts = {}
        if isinstance(producer, AcquireClause):
            bound = self._bound_receipts.get(producer.id, set())
            for receipt in self._authority_observations():
                if receipt.digest in bound:
                    receipts[receipt.digest] = receipt
        for source in producer.sources:
            if isinstance(source, str) and source.startswith("c") and "." in source:
                for receipt in self._receipts_for_output(source, seen):
                    receipts[receipt.digest] = receipt
        return tuple(receipts.values())

    def _argument_candidates(self, action: str, name: str, value):
        candidates = []

        def role(source):
            if source == "task":
                return "literal fixed by the trusted task or Root Contract"
            if source == "runtime-context":
                return "operator-attested runtime context"
            producer = next((item for item in self.contract.clauses
                             if item.output_ref == source), None)
            return producer.instruction if producer is not None else ""
        if self._trusted_literal_candidate(action, name, value):
            candidates.append({"source": "task", "mode": "literal",
                               "role": role("task"), "ref": ""})
        elif self._trusted_scoped_candidate(action, name, value):
            candidates.append({"source": "task", "mode": "scoped",
                               "role": "operator-attested same-origin scope from the trusted task",
                               "ref": ""})
        context = self._context_value(action, name)
        if context is not None and context[0] == value:
            candidates.append({"source": "runtime-context", "mode": "literal",
                               "role": role("runtime-context"),
                               "ref": str(context[1])})
        surface = self.capabilities.get(str(action))
        memo = {"$placements": {}}
        for clause in self.contract.clauses:
            ref = clause.output_ref
            if not ref:
                continue
            try:
                status, _refs = self._lazy_argument(
                    ref, value, memo, surface, name)
            except Exception:
                status = "uncertain"
            if status == "supported":
                candidates.append({"source": ref, "mode": "direct",
                                   "role": role(ref), "ref": ""})
                continue
            receipts = self._receipts_for_output(ref)
            for proof_ref, _receipt in _constructible_refs(receipts, value):
                candidates.append({"source": ref, "mode": "derive",
                                   "role": role(ref), "ref": proof_ref})
        unique = []
        for item in candidates:
            if item not in unique:
                unique.append(item)
        return unique

    def _install_dynamic_clauses(self, clauses) -> None:
        """Install evidence Clauses only; runtime content cannot add Effects."""
        for clause in clauses:
            if isinstance(clause, EffectClause):
                raise ValueError("runtime expansion cannot install an Effect Clause")
            self.contract.clauses.append(clause)
            self.binding_store.register_clause(clause)
            if isinstance(clause, AcquireClause):
                self._source_clauses.setdefault(clause.capability, ())
                self._source_clauses[clause.capability] += (clause,)
        self._placement_cache.clear()

    def _install_root_gate(self, root_clause: EffectClause, specs: dict) -> None:
        """Instantiate arguments while retaining the original Root Effect id."""
        gate = InstalledGate(root_clause, root_clause.action,
                             tuple(root_clause.sources), dict(specs))
        existing = self._gates_by_action.get(root_clause.action, ())
        if any(item.clause.id == root_clause.id and
               item.arguments == gate.arguments for item in existing):
            return
        self.gates += (gate,)
        self._gates_by_action.setdefault(gate.action, ())
        self._gates_by_action[gate.action] += (gate,)

    def _active_delegations(self, parent_ids) -> list[dict]:
        """Bind exact delegated slices to existing Root Effects only."""
        parent_ids = tuple(sorted(set(map(str, parent_ids or ()))))
        rows = []
        for grant in self.contract.delegations:
            targets = ((grant.effect_clause_id,)
                       if grant.effect_clause_id else parent_ids)
            targets = tuple(target for target in targets if target in parent_ids)
            if not targets:
                continue
            producer = next((clause for clause in self.contract.clauses
                             if isinstance(clause, AcquireClause) and
                             clause.output_ref == grant.source_ref), None)
            if producer is None:
                continue
            bound = self._bound_receipts.get(producer.id, set())
            for receipt in self._authority_observations():
                if receipt.digest not in bound or receipt.task_id != self.task_id:
                    continue
                cache_key = (grant.source_ref, grant.effect_clause_id,
                             receipt.digest)
                if cache_key not in self._delegation_slice_cache:
                    selector = getattr(
                        self.expansion_agent, "select_delegation_region", None)
                    self._delegation_slice_cache[cache_key] = (
                        selector(
                            task=self.contract.task,
                            source_ref=grant.source_ref,
                            source_instruction=producer.instruction,
                            receipt_digest=receipt.digest,
                            receipt_value=receipt.value)
                        if callable(selector) else None)
                selected = self._delegation_slice_cache[cache_key]
                if not isinstance(selected, dict):
                    continue
                for target in targets:
                    rows.append({
                        "parent": target, "source": grant.source_ref,
                        "receipt_digest": receipt.digest,
                        "receipt_ref": selected["receipt_ref"],
                        "slice_digest": selected["slice_digest"],
                        "content": selected["content"]})
        return rows

    def active_open_delegation_regions(self, receipt_digest: str | None = None):
        """Return exact slices that may request Approval, never automatic authority."""
        wanted = str(receipt_digest or "")
        rows = []
        for grant in self.contract.delegations:
            if grant.effect_clause_id:
                continue
            producer = next((clause for clause in self.contract.clauses
                             if isinstance(clause, AcquireClause) and
                             clause.output_ref == grant.source_ref), None)
            if producer is None:
                continue
            bound = self._bound_receipts.get(producer.id, set())
            for receipt in self._authority_observations():
                if (receipt.digest not in bound or receipt.task_id != self.task_id or
                        (wanted and receipt.digest != wanted)):
                    continue
                cache_key = (grant.source_ref, "", receipt.digest)
                if cache_key not in self._delegation_slice_cache:
                    selector = getattr(
                        self.expansion_agent, "select_delegation_region", None)
                    self._delegation_slice_cache[cache_key] = (
                        selector(
                            task=self.contract.task,
                            source_ref=grant.source_ref,
                            source_instruction=producer.instruction,
                            receipt_digest=receipt.digest,
                            receipt_value=receipt.value)
                        if callable(selector) else None)
                selected = self._delegation_slice_cache[cache_key]
                if isinstance(selected, dict):
                    rows.append({
                        "source": grant.source_ref,
                        "receipt_digest": receipt.digest,
                        "receipt_ref": selected["receipt_ref"],
                        "slice_digest": selected["slice_digest"]})
        return tuple(rows)

    def approval_delegation_context(self):
        """Expose only exact user-delegated slices to one Approval decision."""
        rows = []
        for region in self.active_open_delegation_regions():
            key = (region["source"], "", region["receipt_digest"])
            selected = self._delegation_slice_cache.get(key)
            if not isinstance(selected, dict):
                continue
            if (selected.get("receipt_ref") != region["receipt_ref"] or
                    selected.get("slice_digest") != region["slice_digest"]):
                continue
            rows.append({
                "source": region["source"],
                "receipt_ref": region["receipt_ref"],
                "slice_digest": region["slice_digest"],
                "content": selected.get("content"),
            })
        return tuple(rows)

    def install_approval_grant(self, action: str, arguments: dict,
                               parent_clause: str | None = None):
        """Install one exact, consumable gate without modifying the Contract."""
        action, arguments = str(action), dict(arguments or {})
        surface = self.capabilities.get(action)
        if surface is None or not surface.effect:
            return None
        key = hashlib.sha256(_stable({
            "action": action, "arguments": arguments}).encode()).hexdigest()
        existing = next((
            clause_id for clause_id, grant in self._approval_grants.items()
            if grant["proposal_digest"] == key), None)
        if existing is not None:
            return self._approval_grants[existing]["clause"]
        clause = EffectClause(
            "approval-" + key[:20],
            f"Execute the exact one-shot user-approved {action} proposal",
            action, {name: {"literal": value}
                     for name, value in arguments.items()})
        gate = InstalledGate.from_clause(clause)
        self.gates += (gate,)
        self._gates_by_action.setdefault(action, ())
        self._gates_by_action[action] += (gate,)
        self._approval_grants[clause.id] = {
            "clause": clause, "proposal_digest": key,
            "arguments_digest": hashlib.sha256(
                _stable(arguments).encode()).hexdigest()}
        self.dynamic_contract_trace.append({
            "mode": "approval-grant", "capability": action,
            "parent": parent_clause, "proposal_digest": key})
        return clause

    def try_dynamic_expansion(self, action: str, arguments: dict,
                              mode: str) -> bool:
        action, arguments, mode = str(action), dict(arguments or {}), str(mode)
        if self.expansion_agent is None or mode not in {"intermediate", "effect"}:
            return False
        surface = self.capabilities.get(action)
        if surface is None or not (surface.observation or surface.effect):
            return False
        parent_clauses = self._root_effect_clauses
        parents = [
            {"id": clause.id, "action": clause.action,
             "instruction": clause.instruction}
            for clause in parent_clauses
            if ((mode == "intermediate" and not surface.effect) or
                clause.action == action)
        ]
        delegations = self._active_delegations(item["id"] for item in parents)
        if not parents:
            return False
        delegated_sources = {row["source"] for row in delegations}
        rows = []
        for name, value in arguments.items():
            candidates = self._argument_candidates(action, str(name), value)
            candidates = [
                candidate for candidate in candidates
                if (candidate["source"] not in delegated_sources or any(
                    row["source"] == candidate["source"] and
                    _value_contains_constructible(row["content"], value)
                    for row in delegations))
            ]
            if not candidates:
                return False
            rows.append({"name": str(name), "type": _value_kind(value),
                         "candidates": candidates})
        candidate_sources = {
            item["source"] for row in rows for item in row["candidates"]}
        if delegated_sources & candidate_sources:
            delegated_parents = {row["parent"] for row in delegations
                                 if row["source"] in candidate_sources}
            parents = [row for row in parents
                       if row["id"] in delegated_parents]
            delegations = [row for row in delegations
                           if row["parent"] in delegated_parents]
        direct_effect = any(
            clause.action == action for clause in self._root_effect_clauses)
        # Unpredicted outbound prerequisites are Effects, including login.
        # Workflow necessity is not authority: require Root, Delegation, or Approval.
        if mode == "intermediate" and surface.effect and not direct_effect:
            return False
        cache_key = hashlib.sha256(_stable({
            "mode": mode, "action": action, "arguments": arguments,
            "candidates": rows,
            "delegation_receipts": sorted(
                row["receipt_digest"] for row in delegations),
        }).encode()).hexdigest()
        if cache_key in self._expansion_cache:
            return bool(self._expansion_cache[cache_key])
        run_key = self._binding_proposal_version(action, arguments)
        if run_key in self._binding_agent_runs:
            self._expansion_cache[cache_key] = False
            return False
        capability = {
            "name": action, "description": surface.description[:360],
            "effect": bool(surface.effect), "observation": bool(surface.observation),
            "effect_return": bool(surface.committed_return),
            "arguments": list(surface.arguments),
            "required_arguments": list(surface.required),
        }
        self._binding_agent_runs.add(run_key)
        answer = self.expansion_agent.propose(
            task=self.contract.task, root_contract=self._root_contract,
            mode=mode, capability=capability, arguments=rows, parents=parents,
            delegations=delegations)
        valid_parent_ids = {item["id"] for item in parents}
        raw_origins = answer.get("origins")
        if (answer.get("status") != "expand" or
                answer.get("parent") not in valid_parent_ids or
                not isinstance(raw_origins, list)):
            self._expansion_cache[cache_key] = False
            return False
        by_name = {}
        for item in raw_origins:
            if (not isinstance(item, dict) or
                    set(item) != {"argument", "source", "mode", "ref"} or
                    item.get("argument") in by_name):
                self._expansion_cache[cache_key] = False
                return False
            by_name[item["argument"]] = {
                "source": item.get("source"), "mode": item.get("mode"),
                "ref": item.get("ref")}
        if set(by_name) != set(arguments):
            self._expansion_cache[cache_key] = False
            return False
        allowed = {row["name"]: {
            (item["source"], item["mode"], item["ref"]) for item in row["candidates"]}
            for row in rows}
        if any((item["source"], item["mode"], item["ref"]) not in allowed[name]
               for name, item in by_name.items()):
            self._expansion_cache[cache_key] = False
            return False

        clauses, specs = [], {}
        next_index = len(self.contract.clauses)
        for name, value in arguments.items():
            choice = by_name[str(name)]
            if choice["mode"] in {"literal", "scoped"}:
                specs[str(name)] = {"literal": value}
                continue
            if choice["mode"] == "direct":
                specs[str(name)] = {"from": choice["source"]}
                continue
            output = _safe_name(action + "_" + str(name))
            projected_value = value[0] if isinstance(value, (list, tuple)) and len(value) == 1 else value
            clause = DeriveClause(
                f"c{next_index}",
                f"Derive the task-authorized {name} argument for {action}",
                (str(choice["source"]),), output)
            next_index += 1
            clauses.append(clause)
            proof_ref = str(choice["ref"])
            receipt = next((
                item for item in self._authority_observations()
                if item.digest == proof_ref.partition("#")[0]), None)
            if receipt is None:
                self._expansion_cache[cache_key] = False
                return False
            self._dynamic_output_values[clause.output_ref] = (
                _Resolved(projected_value, (proof_ref,),
                          receipt, "replayed-proof"),)
            if projected_value is not value:
                wrapped = _safe_name(output + "_singleton")
                relation = ConditionalClause(
                    f"c{next_index}",
                    f"Construct the one-item {name} argument for {action}",
                    "singleton", (clause.output_ref,), wrapped)
                next_index += 1
                clauses.append(relation)
                specs[str(name)] = {"from": relation.output_ref}
            else:
                specs[str(name)] = {"from": clause.output_ref}

        if mode == "intermediate" or surface.committed_return:
            clauses.append(AcquireClause(
                f"c{next_index}",
                f"Acquire the task-necessary runtime result from {action}",
                action, specs, _safe_name(action + "_result")))

        root = next((
            clause for clause in self._root_effect_clauses
            if clause.id == answer["parent"] and clause.action == action), None)
        if surface.effect:
            if root is None:
                self._expansion_cache[cache_key] = False
                return False
            self._install_root_gate(root, specs)
        self._install_dynamic_clauses(clauses)
        delegated = next((
            row for row in delegations if row["parent"] == answer["parent"]), None)
        self.dynamic_contract_trace.append({
            "authority": "root-effect",
            "root_effect": answer["parent"],
            "authority_ref": (delegated["receipt_ref"]
                              if delegated is not None else answer["parent"]),
            "receipt_digest": (delegated["receipt_digest"]
                               if delegated is not None else ""),
            "delegated_slice_digest": (delegated["slice_digest"]
                                        if delegated is not None else ""),
            "parent": answer["parent"], "mode": mode,
            "capability": action,
            "proposal_digest": hashlib.sha256(
                _stable(arguments).encode()).hexdigest(),
            "clauses": [clause.to_dict() for clause in clauses],
        })
        self._expansion_cache[cache_key] = True
        return True
