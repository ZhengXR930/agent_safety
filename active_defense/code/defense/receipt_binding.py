"""Deterministic Receipt ownership for Acquire clauses.

Map every observation Receipt to every compatible Acquire role.  Ownership is
monotonic and many-to-many: a clause is not frozen to the first Receipt that
arrives.  A model is used only to choose among multiple already-compatible
clauses; code validates the choice and records the edge.

There is no fallback: an ambiguous receipt with no resolver, an abstaining
resolver, or a proposal outside the candidate set binds nothing (the receipt
stays an unowned observation).
"""
from __future__ import annotations

from code.defense.contract import AcquireClause
from code.defense.resolver import LazyResolver
from code.defense.state import ClauseReceiptBinding, Receipt, RuntimeState


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


def _bind_receipt(state, clause, receipt):
    if not state.admit(clause.id, receipt):
        return None
    return ClauseReceiptBinding(clause.id, receipt.digest)


def bind_acquire(state: RuntimeState, contract, receipt: Receipt,
                 resolve_ambiguous=None) -> ClauseReceiptBinding | None:
    """Bind ``receipt`` to the AcquireClause it fulfils, or return None.

    ``resolve_ambiguous`` is the optional single binding agent, a callable
    ``(task, capability, arguments, candidates) -> {"clause_id": str} | None``.
    """
    resolver = LazyResolver(state, contract)
    candidates = [
        clause for clause in contract.clauses
        if isinstance(clause, AcquireClause) and
        clause.capability == receipt.capability and
        literal_arguments_compatible(clause, receipt.arguments)]
    if not candidates:
        return None
    exact = [clause for clause in candidates
             if resolver.call_matches(clause, receipt.arguments)]
    if exact:
        # Ownership is many-to-many. If invocation arguments match several
        # declared Acquire roles, the same immutable fact is reachable from
        # each role; no semantic choice or authority is created here.
        bindings = [_bind_receipt(state, clause, receipt) for clause in exact]
        return next((binding for binding in bindings
                     if binding is not None),
                    ClauseReceiptBinding(exact[0].id, receipt.digest))
    if resolve_ambiguous is None:
        return None
    choices = candidates
    proposal = resolve_ambiguous(
        task=contract.task, capability=receipt.capability,
        arguments=dict(receipt.arguments),
        candidates=[{
            "clause_id": clause.id,
            "instruction": clause.instruction,
            "call_arguments": clause.call_arguments,
            "output": clause.output,
        } for clause in choices]) or {}
    chosen = next((clause for clause in choices
                   if clause.id == proposal.get("clause_id")), None)
    if chosen is None:
        return None
    return _bind_receipt(state, chosen, receipt)
