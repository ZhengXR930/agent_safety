"""Task-local materialization of missing non-Effect evidence paths.

The trusted TaskContract never changes. A supporting clause only binds one
existing unresolved role consumed by an existing Root Effect, using Receipts
recorded by the current Episode.  A delegated proof is proposal-local: it
instantiates one declared argument without mutating the ClauseBinding table.
Neither form can create an Effect.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
import re

from code.defense.contract import (AcquireClause, ConditionalClause,
                                   DeriveClause, EffectClause)
from code.defense.receipt_binding import literal_arguments_compatible
from code.defense.resolver import (operator_operand_type,
                                   operator_value_matches, replay_operator)
from code.defense.state import (Binding, QUERY_REF, RuntimeState, UNRESOLVED,
                                stable)


@dataclass(frozen=True)
class SupportingClause:
    """Ephemeral evidence edge from exact Receipt nodes to one Contract role."""
    kind: str
    target_ref: str
    receipt_refs: tuple[str, ...]
    operator: str = ""

    def to_dict(self) -> dict:
        data = {
            "type": self.kind,
            "target": self.target_ref,
            "receipts": list(self.receipt_refs),
        }
        if self.operator:
            data["operator"] = self.operator
        return data


def _nodes(state: RuntimeState) -> list[dict]:
    """Enumerate code-owned Receipt roots and exact scalar JSON nodes."""
    rows = []

    def walk(value, ref, path):
        if path or not isinstance(value, (dict, list, tuple)):
            rows.append({
                "id": "r" + str(len(rows)), "ref": ref + path, "value": value})
        if isinstance(value, dict):
            for key, child in value.items():
                part = str(key).replace("~", "~0").replace("/", "~1")
                walk(child, ref, path + "/" + part)
        elif isinstance(value, (list, tuple)):
            for index, child in enumerate(value):
                walk(child, ref, path + "/" + str(index))

    for receipt in state.receipts:
        # The structured root is useful for semantic Derive, while scalar nodes
        # preserve precise provenance for recipients, URLs, accounts and IDs.
        rows.append({
            "id": "r" + str(len(rows)), "ref": receipt.digest + "#",
            "value": receipt.value, "capability": receipt.capability,
            "arguments": receipt.arguments,
            "effect_return": receipt.effect_return})
        # Effect-return arguments are facts of the authorized call and often
        # carry the exact created helper/resource identity needed downstream.
        # Keep them in the same immutable Receipt, under a disjoint JSON-pointer
        # namespace, rather than inventing a second evidence object.
        if receipt.arguments:
            walk(receipt.arguments, receipt.digest + "#", "/$arguments")
        if isinstance(receipt.value, (dict, list, tuple)):
            walk(receipt.value, receipt.digest + "#", "")
    return rows


def _numeric_candidates(value, ref: str, prefix: str) -> list[dict]:
    """Enumerate exact numeric JSON nodes and numeric text spans."""
    rows = []

    def add(number, exact_ref):
        rows.append({"id": prefix + str(len(rows)),
                     "ref": exact_ref, "value": number})

    def walk(node, path):
        if isinstance(node, bool):
            return
        if isinstance(node, (int, float)):
            add(node, ref + path)
            return
        if isinstance(node, str):
            for match in re.finditer(
                    r"(?<![\w.])-?\d+(?:\.\d+)?(?!\w|\.\d)",
                                     node):
                add(match.group(0), ref + path +
                    f"@{match.start()}:{match.end()}")
            return
        if isinstance(node, dict):
            for key, child in node.items():
                part = str(key).replace("~", "~0").replace("/", "~1")
                walk(child, path + "/" + part)
        elif isinstance(node, (list, tuple)):
            for index, child in enumerate(node):
                walk(child, path + "/" + str(index))

    walk(value, "")
    return rows




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


def _project_scalar(value, selected) -> tuple[str, ...]:
    """Find one exact/canonical scalar node or text span without type lists."""
    exact = []
    spans = []
    for row in selected:
        for leaf, ref in _source_leaves(row["value"], row["ref"]):
            if leaf == value and type(leaf) is type(value):
                exact.append(ref)
                continue
            if isinstance(value, str) and isinstance(leaf, str):
                start = leaf.find(value)
                if start >= 0 and leaf.find(value, start + len(value)) < 0:
                    spans.append(f"{ref}@{start}:{start + len(value)}")
                continue
            if (isinstance(value, (int, float)) and not isinstance(value, bool)
                    and isinstance(leaf, str)):
                for match in re.finditer(
                        r"(?<![\w.])-?\d+(?:\.\d+)?(?!\w|\.\d)", leaf):
                    try:
                        same = Decimal(match.group(0)) == Decimal(str(value))
                    except (InvalidOperation, ValueError):
                        same = False
                    if same:
                        spans.append(
                            f"{ref}@{match.start()}:{match.end()}")
    witnesses = list(dict.fromkeys(exact or spans))
    return (tuple(witnesses) if len(witnesses) == 1 else ())


def _project_value(value, selected) -> tuple[str, ...]:
    """Proof for exact node/span or recursive list/object composition."""
    for row in selected:
        if stable(row["value"]) == stable(value):
            return (row["ref"],)
    if isinstance(value, dict):
        refs = []
        for child in value.values():
            child_refs = _project_value(child, selected)
            if not child_refs:
                return ()
            refs.extend(child_refs)
        return tuple(dict.fromkeys(refs)) if value else ()
    if isinstance(value, (list, tuple)):
        refs = []
        for child in value:
            child_refs = _project_value(child, selected)
            if not child_refs:
                return ()
            refs.extend(child_refs)
        return tuple(dict.fromkeys(refs)) if value else ()
    return _project_scalar(value, selected)

def _binding_refs(state: RuntimeState, ref: str) -> tuple[str, ...]:
    binding = state.bindings.get(str(ref).partition(".")[0])
    return binding.refs if binding is not None else ()


def materialize_intermediate_derive(
        state: RuntimeState, contract, clause: DeriveClause, *, choose=None
        ) -> Binding | None:
    """Resolve one ready intermediate Derive from exact reachable evidence.

    The semantic agent selects candidate ids and a scalar/list composition; it
    never emits a value or provenance reference. Code restricts candidates to
    Receipt roots already backing the Derive inputs and constructs the value.
    """
    if choose is None or clause.id in state.bindings:
        return None
    inputs = {}
    allowed_roots = set()
    for input_ref in clause.input_refs:
        if input_ref == "task":
            inputs[input_ref] = contract.task
            continue
        value = state.output(input_ref)
        if value is UNRESOLVED:
            return None
        inputs[input_ref] = value
        for ref in _binding_refs(state, input_ref):
            if "#" in ref:
                allowed_roots.add(ref.split("#", 1)[0] + "#")
    if not allowed_roots:
        return None

    candidates = [
        row for row in _nodes(state)
        if any(str(row["ref"]).startswith(root) for root in allowed_roots)
    ]
    for receipt in state.receipts:
        root = receipt.digest + "#"
        if root in allowed_roots:
            candidates.extend(_numeric_candidates(
                receipt.value, root, "numeric"))

    requirements = {
        operator_operand_type(consumer.operator, index)
        for consumer in contract.clauses
        if isinstance(consumer, ConditionalClause)
        for index, operand in enumerate(consumer.operand_refs)
        if operand == clause.output_ref
    } - {"any"}
    if len(requirements) > 1:
        return None
    requirement = next(iter(requirements), "any")

    # The Agent may select exact nodes/spans, but a downstream closed operator
    # owns their admissible type.  For a numeric list, individual exact numeric
    # witnesses may be composed into the list; other requirements validate the
    # selected value after composition below.
    if requirement == "number":
        candidates = [row for row in candidates
                      if operator_value_matches("number", row["value"])]
    elif requirement == "number-list":
        candidates = [row for row in candidates
                      if (operator_value_matches("number", row["value"]) or
                          operator_value_matches("number-list", row["value"]))]

    unique = []
    seen = set()
    for row in candidates:
        key = (str(row["ref"]), stable(row["value"]))
        if key in seen:
            continue
        seen.add(key)
        unique.append({**row, "id": "i" + str(len(unique))})
    if not unique:
        return None

    proposal = choose(
        task=contract.task, clause=clause.to_dict(), inputs=inputs,
        expected_type=requirement,
        candidates=[{"id": row["id"], "value": row["value"]}
                    for row in unique]) or {}
    ids, compose = proposal.get("candidate_ids"), proposal.get("compose")
    if not isinstance(ids, list) or not ids or compose not in {"scalar", "list"}:
        return None
    by_id = {row["id"]: row for row in unique}
    if (len(set(map(str, ids))) != len(ids) or
            any(item not in by_id for item in ids) or
            (compose == "scalar" and len(ids) != 1)):
        return None
    selected = [by_id[item] for item in ids]
    value = selected[0]["value"] if compose == "scalar" else [
        row["value"] for row in selected]
    if not operator_value_matches(requirement, value):
        return None
    refs = tuple(dict.fromkeys(str(row["ref"]) for row in selected))
    binding = state.bind(Binding(
        clause.id, "supporting-derive", value, refs))
    state.supporting_clauses.append(
        SupportingClause("derive", clause.output_ref, refs).to_dict())
    return binding


def materialize_delegated_support(
        state: RuntimeState, contract, effect: EffectClause,
        argument: str, value, *, choose=None) -> tuple[str, ...]:
    """Prove one locally delegated argument from its declared Receipt scope.

    The Contract already fixes the Root Effect and the delegated argument role.
    The Binding Agent may select exact nodes only from Receipts reachable through
    that role's upstream Clause inputs.  Code then projects ``value`` from those
    nodes.  No persistent Clause output is bound, so a quantified role can prove
    several calls (for example ``general`` and ``random``) independently.
    """
    spec = effect.effect_arguments.get(argument)
    if (not isinstance(spec, dict) or
            set(spec) != {"from", "delegated"} or
            spec.get("delegated") is not True or choose is None):
        return ()
    raw_sources = spec.get("from")
    sources = ([raw_sources] if isinstance(raw_sources, str)
               else list(raw_sources or ()))
    clauses = {clause.output_ref: clause for clause in contract.clauses
               if not isinstance(clause, EffectClause) and clause.output_ref}
    targets = [source for source in sources
               if isinstance(clauses.get(source), DeriveClause)]
    if not targets:
        return ()

    # Delegation scope is inherited from the target Derive's already-bound
    # Clause inputs, never from all Receipts visible in the episode.
    allowed_roots = set()
    for target_ref in targets:
        target = clauses[target_ref]
        for input_ref in target.input_refs:
            for ref in _binding_refs(state, input_ref):
                if ref not in {QUERY_REF} and "#" in ref:
                    allowed_roots.add(ref.split("#", 1)[0] + "#")
    if not allowed_roots:
        return ()
    nodes = [row for row in _nodes(state)
             if any(str(row["ref"]).startswith(root)
                    for root in allowed_roots)]
    if not nodes:
        return ()

    proposal = choose(
        task=contract.task, action=effect.action, argument=argument, value=value,
        delegated=True,
        targets=[{"ref": target, "clause": clauses[target].to_dict()}
                 for target in targets],
        candidates=[{"id": row["id"], "value": row["value"],
                     "capability": row.get("capability", ""),
                     "arguments": row.get("arguments", {})}
                    for row in nodes]) or {}
    target_ref, ids = proposal.get("target_ref"), proposal.get("candidate_ids")
    if target_ref not in targets or not isinstance(ids, list) or not ids:
        return ()
    by_id = {row["id"]: row for row in nodes}
    if (len(set(map(str, ids))) != len(ids) or
            any(item not in by_id for item in ids)):
        return ()
    refs = _project_value(value, [by_id[item] for item in ids])
    if not refs:
        return ()
    state.supporting_clauses.append(
        SupportingClause("delegated", target_ref, refs).to_dict())
    return refs


def materialize_guard(state: RuntimeState, contract,
                      clause: ConditionalClause, candidate, *,
                      choose=None, equal=None) -> Binding | None:
    """Materialize a gt/lt guard from task threshold and exact Receipt score.

    Semantics are recursive guarded selection: [candidate, score, threshold].
    The Agent selects only exact numeric witnesses; code owns their provenance,
    executes the comparison, and binds the candidate only when it succeeds.
    """
    if clause.operator not in {"gt", "lt"} or choose is None:
        return None
    candidate_ref, score_ref, threshold_ref = clause.operand_refs
    clauses = {item.output_ref: item for item in contract.clauses
               if not isinstance(item, EffectClause) and item.output_ref}
    equal = equal or (lambda left, right: left == right)

    # The candidate is either already proven by an earlier guard, or is a
    # trusted task literal exposed by a task-only Derive role.
    current_candidate = state.output(candidate_ref)
    candidate_refs = ()
    if current_candidate is not UNRESOLVED:
        if not equal(current_candidate, candidate):
            return None
        candidate_refs = _binding_refs(state, candidate_ref)
    else:
        source = clauses.get(candidate_ref)
        if isinstance(source, ConditionalClause) and source.operator in {"gt", "lt"}:
            bound = materialize_guard(
                state, contract, source, candidate, choose=choose, equal=equal)
            if bound is None:
                return None
            candidate_refs = bound.refs
        elif (isinstance(source, DeriveClause) and
              set(source.input_refs).issubset({"task", "runtime-context"}) and
              isinstance(candidate, str) and candidate in contract.task):
            candidate_refs = (QUERY_REF,)
        else:
            return None

    receipt_numbers = []
    for receipt in state.receipts:
        receipt_numbers.extend(_numeric_candidates(
            receipt.value, receipt.digest + "#", "r"))
    # Reassign ids after concatenating multiple Receipts.
    receipt_numbers = [{**row, "id": "r" + str(index)}
                       for index, row in enumerate(receipt_numbers)]
    task_numbers = _numeric_candidates(contract.task, QUERY_REF, "q")

    def role_pool(ref, task_pool, receipt_pool):
        value = state.output(ref)
        if value is not UNRESOLVED:
            return value, _binding_refs(state, ref), []
        role = clauses.get(ref)
        if (isinstance(role, DeriveClause) and
                set(role.input_refs).issubset({"task", "runtime-context"})):
            return UNRESOLVED, (), task_pool
        return UNRESOLVED, (), receipt_pool

    score, score_refs, score_pool = role_pool(
        score_ref, task_numbers, receipt_numbers)
    threshold, threshold_refs, threshold_pool = role_pool(
        threshold_ref, task_numbers, receipt_numbers)
    if ((score is UNRESOLVED and not score_pool) or
            (threshold is UNRESOLVED and not threshold_pool)):
        return None

    proposal = choose(
        task=contract.task, candidate=candidate,
        operator=clause.operator,
        score_role=(clauses.get(score_ref).to_dict()
                    if score_ref in clauses else {"ref": score_ref}),
        threshold_role=(clauses.get(threshold_ref).to_dict()
                        if threshold_ref in clauses else {"ref": threshold_ref}),
        score_candidates=[{"id": row["id"], "value": row["value"]}
                          for row in score_pool],
        threshold_candidates=[{"id": row["id"], "value": row["value"]}
                              for row in threshold_pool]) or {}

    def selected(value, refs, pool, field):
        if value is not UNRESOLVED:
            return value, refs
        by_id = {row["id"]: row for row in pool}
        row = by_id.get(proposal.get(field))
        return ((row["value"], (row["ref"],))
                if row is not None else (UNRESOLVED, ()))

    score, score_refs = selected(
        score, score_refs, score_pool, "score_candidate_id")
    threshold, threshold_refs = selected(
        threshold, threshold_refs, threshold_pool, "threshold_candidate_id")
    if score is UNRESOLVED or threshold is UNRESOLVED:
        return None
    try:
        result = replay_operator(clause.operator, [candidate, score, threshold])
    except (TypeError, ValueError):
        return None
    if result is UNRESOLVED:
        return None

    refs = tuple(dict.fromkeys(
        (*candidate_refs, *score_refs, *threshold_refs)))
    binding = state.bind(Binding(
        clause.id, "supporting-conditional", candidate, refs))
    state.supporting_clauses.append(
        SupportingClause("conditional", clause.output_ref, refs,
                         clause.operator).to_dict())
    return binding

def materialize_support(state: RuntimeState, contract, effect: EffectClause,
                        argument: str, value, *, choose=None, equal=None,
                        allow_semantic: bool = False
                        ) -> Binding | None:
    """Bind one existing unresolved role through one validated supporting path."""
    spec = effect.effect_arguments.get(argument)
    if not isinstance(spec, dict) or set(spec) != {"from"} or choose is None:
        return None
    sources = spec["from"]
    sources = [sources] if isinstance(sources, str) else list(sources or ())
    unresolved = [source for source in sources
                  if state.output(source) is UNRESOLVED]
    if not unresolved:
        return None
    clauses = {clause.output_ref: clause for clause in contract.clauses
               if not isinstance(clause, EffectClause) and clause.output_ref}
    targets = [source for source in unresolved if source in clauses]
    if not targets:
        return None

    nodes = _nodes(state)
    if not nodes:
        return None
    proposal = choose(
        task=contract.task, action=effect.action, argument=argument, value=value,
        targets=[{"ref": target, "clause": clauses[target].to_dict()}
                 for target in targets],
        candidates=[{"id": row["id"], "value": row["value"],
                     "capability": row.get("capability", ""),
                     "arguments": row.get("arguments", {})}
                    for row in nodes]) or {}
    target_ref = proposal.get("target_ref")
    ids = proposal.get("candidate_ids")
    if target_ref not in targets or not isinstance(ids, list) or not ids:
        return None
    by_id = {row["id"]: row for row in nodes}
    if len(set(map(str, ids))) != len(ids) or any(item not in by_id for item in ids):
        return None
    selected = [by_id[item] for item in ids]
    target = clauses[target_ref]
    kind, operator, derived = "", "", None

    if isinstance(target, AcquireClause):
        roots = [row for row in selected if "capability" in row]
        if (len(roots) != 1 or
                roots[0].get("capability") != target.capability or
                not literal_arguments_compatible(
                    target, roots[0].get("arguments") or {})):
            return None
        kind, derived = "acquire", roots[0]["value"]
    elif isinstance(target, ConditionalClause):
        operator = target.operator
        try:
            derived = replay_operator(
                operator, [row["value"] for row in selected])
        except (IndexError, TypeError, ValueError):
            return None
        kind = "conditional"
    elif isinstance(target, DeriveClause):
        if not allow_semantic:
            return None
        # Selection is the bounded semantic judgment: values and provenance
        # remain code-owned and the Agent cannot invent either.
        kind, derived = "derive", value
    else:
        return None

    equal = equal or (lambda left, right: left == right)
    if not equal(derived, value):
        return None
    if kind == "derive":
        # Derive supporting is a provenance projection, not a semantic
        # authority mint. This single rule covers URLs, email, IBAN, amounts,
        # identifiers and structured compositions without category whitelists.
        refs = _project_value(value, selected)
        if not refs:
            return None
    else:
        refs = tuple(dict.fromkeys(row["ref"] for row in selected))
    clause = SupportingClause(kind, target_ref, refs, operator)
    binding = state.bind(Binding(
        target_ref.partition(".")[0], "supporting-" + kind, value, refs))
    state.supporting_clauses.append(clause.to_dict())
    return binding
