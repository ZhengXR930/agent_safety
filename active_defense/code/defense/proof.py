"""One constrained proposal-time Binding placement over unordered Receipts.

Persistent state owns only Clause→Receipt edges.  This module builds all
unresolved semantic goals from the current Receipt snapshot, enumerates their
Clause-reachable evidence, and asks one Binding Agent to select opaque ids.
The Agent never writes a Receipt ref, span, value, operator, Clause, or Effect.
Code projects exact node/span/list/object values and replays every Conditional.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
import re

from code.defense.contract import (AcquireClause, ConditionalClause,
                                   DeriveClause, EffectClause)
from code.defense.resolver import (LazyResolver, Resolved,
                                   operator_operand_type,
                                   operator_value_matches)
from code.defense.state import QUERY_REF, SEMANTIC_REF, RuntimeState, stable


@dataclass(frozen=True)
class BindingGoal:
    id: str
    clause_id: str
    argument: str
    target_ref: str
    instruction: str
    mode: str                 # intermediate | direct | delegated
    expected_type: str
    proposed: object
    allow_semantic: bool
    candidates: tuple[dict, ...]

    def public(self) -> dict:
        compose = (["list"] if self.mode != "intermediate" and
                   isinstance(self.proposed, (list, tuple)) else
                   ["object"] if self.mode != "intermediate" and
                   isinstance(self.proposed, dict) else
                   ["scalar", "list"] if self.expected_type == "number-list"
                   else ["scalar"])
        return {
            "goal_id": self.id,
            "argument": self.argument,
            "role": self.instruction,
            "mode": self.mode,
            "expected_type": self.expected_type,
            "proposed": None if self.mode == "intermediate" else self.proposed,
            "allowed_compose": compose,
            "candidates": [
                {"candidate_id": row["id"], "value": row["value"]}
                for row in self.candidates],
        }


def _nodes(value, ref):
    yield value, ref
    if isinstance(value, dict):
        for key, child in value.items():
            part = str(key).replace("~", "~0").replace("/", "~1")
            yield from _nodes(child, ref + "/" + part)
    elif isinstance(value, (list, tuple)):
        for index, child in enumerate(value):
            yield from _nodes(child, ref + "/" + str(index))


def _numeric_spans(value, ref):
    if not isinstance(value, str):
        return
    for match in re.finditer(r"(?<![\w.])-?\d+(?:\.\d+)?(?!\w|\.\d)", value):
        number = Decimal(match.group(0))
        parsed = (int(number) if number == number.to_integral()
                  else float(number))
        yield parsed, f"{ref}@{match.start()}:{match.end()}"


def _typed_spans(value, ref, expected_type):
    # Numbers are self-describing exact spans even when an upstream schema
    # cannot propagate a narrower type through a generic equality operator.
    # Enumerating them does not interpret their role; the Agent may only pick
    # one of these code-issued spans and replay still checks the operator.
    if expected_type in {"any", "number", "number-list"}:
        yield from _numeric_spans(value, ref) or ()
    if not isinstance(value, str) or expected_type not in {"string", "datetime"}:
        return
    patterns = (
        r"\b\d{4}-\d{2}-\d{2}(?:[ T]\d{1,2}:\d{2})?\b",
        r"\b\d{1,2}:\d{2}\b",
        r"\b(?:one|two|three|four|\d+(?:\.\d+)?)\s+"
        r"(?:minute|minutes|hour|hours)\b",
    )
    for pattern in patterns:
        for match in re.finditer(pattern, value, re.I):
            yield match.group(0), f"{ref}@{match.start()}:{match.end()}"


def _source_leaves(value, ref):
    if isinstance(value, dict):
        for key, child in value.items():
            part = str(key).replace("~", "~0").replace("/", "~1")
            yield from _source_leaves(child, ref + "/" + part)
    elif isinstance(value, (list, tuple)):
        for index, child in enumerate(value):
            yield from _source_leaves(child, ref + "/" + str(index))
    else:
        yield value, ref


def _project_scalar(value, selected):
    exact, spans = [], []
    for row in selected:
        for leaf, ref in _source_leaves(row["value"], row["ref"]):
            if leaf == value and type(leaf) is type(value):
                exact.extend(row.get("refs") or (ref,))
            elif isinstance(value, str) and isinstance(leaf, str) and value:
                starts = [item.start() for item in re.finditer(
                    re.escape(value), leaf)]
                if len(starts) == 1:
                    start = starts[0]
                    spans.extend(row.get("refs") or
                                 (f"{ref}@{start}:{start + len(value)}",))
            elif (isinstance(value, (int, float)) and
                  not isinstance(value, bool) and isinstance(leaf, str)):
                for match in re.finditer(
                        r"(?<![\w.])-?\d+(?:\.\d+)?(?!\w|\.\d)", leaf):
                    try:
                        same = Decimal(match.group(0)) == Decimal(str(value))
                    except (InvalidOperation, ValueError):
                        same = False
                    if same:
                        spans.extend(row.get("refs") or
                                     (f"{ref}@{match.start()}:{match.end()}",))
    witnesses = list(dict.fromkeys(exact or spans))
    return tuple(witnesses) if len(witnesses) == 1 else ()


def project_value(value, selected):
    """Replay exact node/span or recursive list/object composition."""
    for row in selected:
        if stable(row["value"]) == stable(value):
            return tuple(row.get("refs") or (row["ref"],))
    if isinstance(value, dict):
        refs = []
        for child in value.values():
            proof = project_value(child, selected)
            if not proof:
                return ()
            refs.extend(proof)
        return tuple(dict.fromkeys(refs)) if value else ()
    if isinstance(value, (list, tuple)):
        refs = []
        for child in value:
            proof = project_value(child, selected)
            if not proof:
                return ()
            refs.extend(proof)
        return tuple(dict.fromkeys(refs)) if value else ()
    return _project_scalar(value, selected)


def _reachable_receipts(state, contract, target_ref):
    by_ref = {clause.output_ref: clause for clause in contract.clauses
              if clause.output_ref}
    found = {}

    def visit(ref, seen=frozenset()):
        ref = str(ref)
        if ref in seen:
            return
        clause = by_ref.get(ref)
        if isinstance(clause, AcquireClause):
            for receipt in state.receipts_for(clause.id):
                found[receipt.digest] = receipt
        elif isinstance(clause, DeriveClause):
            for source in clause.input_refs:
                if source != "task":
                    visit(source, seen | {ref})
        elif isinstance(clause, ConditionalClause):
            for source in clause.operand_refs:
                visit(source, seen | {ref})

    clause = by_ref.get(str(target_ref))
    task_reachable = isinstance(clause, DeriveClause) and "task" in clause.input_refs
    visit(target_ref)
    return tuple(found.values()), task_reachable


def _candidate_rows(state, contract, target_ref, expected_type):
    receipts, task_reachable = _reachable_receipts(
        state, contract, target_ref)
    rows = []
    if task_reachable:
        rows.append({"ref": QUERY_REF, "value": contract.task})
        rows.extend({"ref": ref, "value": value}
                    for value, ref in _typed_spans(
                        contract.task, QUERY_REF, expected_type) or ())
    for receipt in receipts:
        for value, ref in _nodes(receipt.value, receipt.digest + "#"):
            rows.append({"ref": ref, "value": value})
            rows.extend({"ref": span_ref, "value": span_value}
                        for span_value, span_ref in
                        (_typed_spans(value, ref, expected_type) or ()))
        if receipt.arguments:
            for value, ref in _nodes(
                    receipt.arguments, receipt.digest + "#/$arguments"):
                rows.append({"ref": ref, "value": value})

    # A semantic role may consume a value produced by an already-closed
    # Conditional (for example keys(object) or sort_by(records,...)). Expose
    # those replayed outputs as code-owned candidates; the Agent still sees
    # only opaque ids and cannot invent a value, ref, operator, or scope.
    by_ref = {clause.output_ref: clause for clause in contract.clauses
              if clause.output_ref}
    target = by_ref.get(str(target_ref))
    if isinstance(target, DeriveClause):
        resolver = LazyResolver(state, contract)
        for source in target.input_refs:
            if source in {"task", "runtime-context"}:
                continue
            # Acquire values are already enumerated above with their exact
            # JSON node/span locators. Re-emitting them here would coarsen a
            # precise span into the Conditional's aggregate provenance. Only
            # closed replay outputs add genuinely new candidate values.
            if not isinstance(by_ref.get(str(source)), ConditionalClause):
                continue
            for resolved in resolver.values(source):
                if not resolved.refs:
                    continue
                for value, ref in _nodes(resolved.value, "<replay>:" + source):
                    rows.append({"ref": ref, "refs": resolved.refs,
                                 "value": value})
    unique, seen = [], set()
    for row in rows:
        key = (row["ref"], tuple(row.get("refs") or ()),
               stable(row["value"]))
        if key not in seen:
            seen.add(key)
            unique.append({**row, "id": "n" + str(len(unique))})
    return tuple(unique)


def _collect_leaves(contract, ref, expected, found, seen=frozenset()):
    by_ref = {clause.output_ref: clause for clause in contract.clauses
              if clause.output_ref}
    ref = str(ref)
    if ref in seen:
        return
    clause = by_ref.get(ref)
    if isinstance(clause, (AcquireClause, DeriveClause)):
        found.setdefault(ref, set()).add(expected)
    elif isinstance(clause, ConditionalClause):
        for index, operand in enumerate(clause.operands):
            if isinstance(operand, str) and operand in by_ref:
                _collect_leaves(
                    contract, operand,
                    operator_operand_type(clause.operator, index), found,
                    seen | {ref})


def compile_goals(state: RuntimeState, contract, action, arguments, surface,
                  equal):
    resolver = LazyResolver(state, contract)
    goals, immediate, immediate_delegated, seen = [], {}, {}, set()
    effects = [clause for clause in contract.clauses
               if isinstance(clause, EffectClause) and clause.action == action]
    for effect in effects:
        for name, spec in effect.effect_arguments.items():
            if name not in arguments or not isinstance(spec, dict) or "from" not in spec:
                continue
            raw = spec["from"]
            sources = [raw] if isinstance(raw, str) else list(raw or ())
            matches = [row for source in sources for row in resolver.values(source)
                       if equal(name, row.value, arguments[name])]
            if matches:
                refs = tuple(dict.fromkeys(
                    ref for row in matches for ref in row.refs))
                target = (immediate_delegated
                          if spec.get("delegated") is True else immediate)
                target[(effect.id, name)] = refs
                continue

            leaves = {}
            for source in sources:
                _collect_leaves(contract, source, "any", leaves)
            direct = len(leaves) == 1 and any(str(source) in leaves for source in sources)
            delegated = (set(spec) == {"from", "delegated"} and
                         spec.get("delegated") is True)
            for target_ref, kinds in leaves.items():
                # A closed suffix can already consume this value. Only a
                # direct Effect projection still needs the Agent to select the
                # exact node within an acquired collection.
                if not direct and resolver.values(target_ref):
                    continue
                key = (effect.id, name, target_ref)
                if key in seen:
                    continue
                seen.add(key)
                concrete = kinds - {"any"}
                expected = (next(iter(concrete)) if len(concrete) == 1 else
                            "any" if not concrete else "conflict")
                if expected == "conflict":
                    continue
                clause = next(item for item in contract.clauses
                              if item.output_ref == target_ref)
                rows = list(_candidate_rows(
                    state, contract, target_ref, expected))
                if not direct:
                    rows = [row for row in rows
                            if operator_value_matches(expected, row["value"])]
                if not rows:
                    continue
                mode = ("delegated" if delegated and direct else
                        "direct" if direct else "intermediate")
                goal_id = "g" + str(len(goals))
                rows = tuple({**row, "id": goal_id + "." + row["id"]}
                             for row in rows)
                goals.append(BindingGoal(
                    goal_id, effect.id, name, target_ref,
                    clause.instruction, mode, expected,
                    arguments[name] if direct else None,
                    bool(direct and not delegated and surface is not None and
                         surface.accepts_semantic_support(name)), rows))
    return tuple(goals), immediate, immediate_delegated


def apply_placements(state, contract, action, arguments, surface, goals,
                     immediate, immediate_delegated, proposal, equal):
    """Validate id-only placements and return ordinary/delegated proof refs."""
    rows = proposal.get("placements") if isinstance(proposal, dict) else None
    if not isinstance(rows, list):
        rows = []
    by_goal = {goal.id: goal for goal in goals}
    selected = {}
    for row in rows:
        if not isinstance(row, dict) or set(row) != {
                "goal_id", "candidate_ids", "compose"}:
            return {}, {}, {}
        goal = by_goal.get(str(row.get("goal_id")))
        ids, compose = row.get("candidate_ids"), row.get("compose")
        allowed = set(goal.public()["allowed_compose"]) if goal else set()
        if (goal is None or goal.id in selected or
                not isinstance(ids, list) or not ids or
                len(set(map(str, ids))) != len(ids) or compose not in allowed):
            return {}, {}, {}
        choices = {item["id"]: item for item in goal.candidates}
        if any(str(item) not in choices for item in ids):
            return {}, {}, {}
        selected[goal.id] = (compose, [choices[str(item)] for item in ids])

    placements, direct_exact, direct_semantic = {}, {}, {}
    delegated = dict(immediate_delegated)
    for goal in goals:
        choice = selected.get(goal.id)
        if choice is None:
            continue
        compose, candidates = choice
        if goal.mode == "intermediate":
            if compose == "scalar" and len(candidates) != 1:
                continue
            value = (candidates[0]["value"] if compose == "scalar" else
                     [item["value"] for item in candidates])
            if not operator_value_matches(goal.expected_type, value):
                continue
            refs = tuple(dict.fromkeys(
                ref for item in candidates
                for ref in (item.get("refs") or (item["ref"],))))
            placements[goal.target_ref] = (Resolved(value, refs),)
            continue

        if (compose == "list") != isinstance(goal.proposed, (list, tuple)):
            continue
        if (compose == "object") != isinstance(goal.proposed, dict):
            continue
        refs = project_value(goal.proposed, candidates)
        key = (goal.clause_id, goal.argument)
        if refs:
            placements[goal.target_ref] = (
                Resolved(goal.proposed, refs),)
            (delegated if goal.mode == "delegated" else direct_exact)[key] = refs
        elif goal.allow_semantic:
            evidence_refs = tuple(dict.fromkeys(
                ref.split("@", 1)[0] for item in candidates
                for ref in (item.get("refs") or (item["ref"],))))
            if evidence_refs:
                direct_semantic[key] = (SEMANTIC_REF, *evidence_refs)

    resolver = LazyResolver(state, contract, placements)
    exact = dict(immediate)
    effects = [clause for clause in contract.clauses
               if isinstance(clause, EffectClause) and clause.action == action]
    for effect in effects:
        for name, spec in effect.effect_arguments.items():
            if name not in arguments or not isinstance(spec, dict) or "from" not in spec:
                continue
            raw = spec["from"]
            sources = [raw] if isinstance(raw, str) else list(raw or ())
            matches = [row for source in sources for row in resolver.values(source)
                       if equal(name, row.value, arguments[name])]
            if matches:
                refs = tuple(dict.fromkeys(
                    ref for row in matches for ref in row.refs))
                target = (delegated if spec.get("delegated") is True else exact)
                target[(effect.id, name)] = refs
    exact.update(direct_exact)
    semantic = {**exact, **direct_semantic}
    return semantic, delegated, placements
