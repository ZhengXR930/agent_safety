"""Deterministic receipt -> clause binding, with one validated semantic escape.

Map an observation receipt to the AcquireClause role it fulfils.  The common
case is an exact match on capability + call arguments and uses no model.  When
the match is genuinely ambiguous (no exact match, or more than one), a single
binding-agent call may PROPOSE which clause the receipt fulfils; deterministic
code then VALIDATES that the proposed clause is a real candidate and computes
the binding itself.  The agent chooses the mapping; it never emits authority.

There is no fallback: an ambiguous receipt with no resolver, an abstaining
resolver, or a proposal outside the candidate set binds nothing (the receipt
stays an unowned observation).
"""
from __future__ import annotations

from code.defense.contract import AcquireClause
from code.defense.state import (Binding, Receipt, RuntimeState, UNRESOLVED,
                                stable)


def _arg_matches(state: RuntimeState, spec, proposed) -> bool:
    """Whether one call-argument spec is satisfied by the receipt's value."""
    if isinstance(spec, dict) and set(spec) == {"literal"}:
        return spec["literal"] == proposed
    if isinstance(spec, dict) and set(spec) == {"from"}:
        sources = spec["from"]
        sources = [sources] if isinstance(sources, str) else list(sources or ())
        return any(state.output(src) == proposed for src in sources)
    return spec == proposed  # bare literal


def _clause_matches(state: RuntimeState, clause: AcquireClause,
                    arguments: dict) -> bool:
    """Deterministic: every declared call argument is present and matches."""
    for name, spec in clause.call_arguments.items():
        if name not in arguments or not _arg_matches(state, spec, arguments[name]):
            return False
    return True


def literal_arguments_compatible(
        clause: AcquireClause, arguments: dict) -> bool:
    """Semantic matching may bridge workflow variance, never literal conflict."""
    for name, spec in clause.call_arguments.items():
        if isinstance(spec, dict) and set(spec) == {"literal"}:
            literal = spec["literal"]
        elif not isinstance(spec, dict):
            literal = spec
        else:
            continue
        if name not in arguments or arguments[name] != literal:
            return False
    return True


def _single_object_leaf(value):
    """Return the sole scalar leaf of an object and its JSON pointer.

    This is a proof-preserving projection, not semantic field selection: a
    list or an object with multiple leaves remains the whole Acquire output.
    """
    if not isinstance(value, dict):
        return None
    leaves = []

    def walk(node, path):
        if isinstance(node, dict):
            for key, child in node.items():
                part = str(key).replace("~", "~0").replace("/", "~1")
                walk(child, path + "/" + part)
            return
        if isinstance(node, (list, tuple)):
            leaves.append((path, node, False))
            return
        leaves.append((path, node, True))

    walk(value, "")
    if len(leaves) != 1 or not leaves[0][2]:
        return None
    return leaves[0][1], leaves[0][0]


def _bind_receipt(state, clause, receipt):
    projected = _single_object_leaf(receipt.value)
    value, path = projected if projected is not None else (receipt.value, "")
    return state.bind(Binding(clause.id, "acquire", value,
                              (receipt.digest + "#" + path,)))


def _quantified_axis(state: RuntimeState, clause: AcquireClause):
    """Return the single finite call axis declared by a quantified Acquire."""
    axes = []
    for name, spec in clause.call_arguments.items():
        if not (isinstance(spec, dict) and set(spec) == {"from"}):
            continue
        source = spec["from"]
        sources = [source] if isinstance(source, str) else list(source or ())
        if len(sources) != 1:
            return None
        domain = state.output(sources[0])
        if not isinstance(domain, (list, tuple)):
            return None
        axes.append((name, list(domain)))
    return axes[0] if len(axes) == 1 else None


def _bind_quantified(state: RuntimeState, clause: AcquireClause,
                     current: Receipt) -> Binding | None:
    """Bind only after one exact Receipt exists for every domain member.

    Values and refs are ordered by the upstream domain, never by Agent call
    order. Repeated identical calls are harmless; conflicting returns leave the
    role unresolved.
    """
    axis = _quantified_axis(state, clause)
    if axis is None:
        return None
    argument, domain = axis
    receipts = list(state.receipts)
    if all(item.digest != current.digest for item in receipts):
        receipts.append(current)
    values, refs = [], []
    for member in domain:
        matches = [item for item in receipts
                   if item.capability == clause.capability and
                   literal_arguments_compatible(clause, item.arguments) and
                   argument in item.arguments and
                   stable(item.arguments[argument]) == stable(member)]
        if not matches:
            return None
        projected = [_single_object_leaf(item.value) for item in matches]
        normalized = [item if item is not None else (receipt.value, "")
                      for item, receipt in zip(projected, matches)]
        if len({stable(value) for value, _path in normalized}) != 1:
            return None
        value, path = normalized[0]
        values.append(value)
        refs.append(matches[0].digest + "#" + path)
    return state.bind(Binding(
        clause.id, "acquire-quantified", values, tuple(refs)))


def bind_acquire(state: RuntimeState, contract, receipt: Receipt,
                 resolve_ambiguous=None) -> Binding | None:
    """Bind ``receipt`` to the AcquireClause it fulfils, or return None.

    ``resolve_ambiguous`` is the optional single binding agent, a callable
    ``(task, capability, arguments, candidates) -> {"clause_id": str} | None``.
    """
    candidates = [
        clause for clause in contract.clauses
        if isinstance(clause, AcquireClause) and
        clause.capability == receipt.capability and
        clause.id not in state.bindings and
        literal_arguments_compatible(clause, receipt.arguments)]
    if not candidates:
        return None
    quantified = [clause for clause in candidates if clause.quantified and
                  _quantified_axis(state, clause) is not None]
    if len(quantified) == 1:
        binding = _bind_quantified(state, quantified[0], receipt)
        if binding is not None:
            return binding
    candidates = [clause for clause in candidates if not clause.quantified]
    exact = [clause for clause in candidates
             if _clause_matches(state, clause, receipt.arguments)]
    if len(exact) == 1:
        return _bind_receipt(state, exact[0], receipt)
    if resolve_ambiguous is None:
        return None
    proposal = resolve_ambiguous(
        task=contract.task, capability=receipt.capability,
        arguments=dict(receipt.arguments),
        candidates=[clause.id for clause in candidates]) or {}
    chosen = next((clause for clause in candidates
                   if clause.id == proposal.get("clause_id")), None)
    if chosen is None:
        return None
    return _bind_receipt(state, chosen, receipt)
