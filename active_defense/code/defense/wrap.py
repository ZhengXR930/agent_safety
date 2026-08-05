"""WRAP: one deterministic gate from Root Effect Clauses to runtime calls.

There is exactly one authorization path.  The trusted Contract fixes the
Effect action and every argument role; runtime Binding resolves Clause outputs
from task-local Receipts, and this gate compares the complete proposal against
those outputs.  Runtime content may instantiate a declared Derive role, but it
cannot create a new Effect or an undeclared argument.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from code.defense.contract import EffectClause
from code.defense.state import (QUERY_REF, SEMANTIC_REF, RuntimeState,
                                UNRESOLVED)


@dataclass(frozen=True)
class Verdict:
    ok: bool
    reason: str
    refs: tuple[str, ...] = field(default_factory=tuple)


_AUTHORITY_PATTERNS = {
    "url": re.compile(r"(?:https?://|www\.)[^\s<>'\"]+", re.I),
    "email": re.compile(r"(?<![\w.+-])[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}"),
    "mention": re.compile(r"(?<![\w@])@[A-Za-z0-9_.-]+"),
}


def authority_atoms(value, grammars) -> tuple[str, ...]:
    """Parse only authority grammars explicitly attested by the operator."""
    atoms = []

    def scan(node):
        if isinstance(node, dict):
            for child in node.values():
                scan(child)
            return
        if isinstance(node, (list, tuple)):
            for child in node:
                scan(child)
            return
        if not isinstance(node, str):
            return
        for grammar in grammars or ():
            pattern = _AUTHORITY_PATTERNS.get(str(grammar))
            if pattern is not None:
                atoms.extend(match.group(0).rstrip(".,;:!?)")
                             for match in pattern.finditer(node))

    scan(value)
    return tuple(dict.fromkeys(atoms))


def _atom_authorized(state, contract, atom: str) -> bool:
    """An authority atom must come from a trusted or closed source.

    Open prose can be summarized or rewritten, but an acquired document cannot
    smuggle a new endpoint, recipient or mention through a content argument.
    A trusted task literal or a deterministically replayed Conditional may
    introduce such an atom; ordinary Acquire/Derive provenance may not.
    """
    if atom in contract.task:
        return True
    for clause in contract.clauses:
        for spec in clause.arguments.values():
            if (isinstance(spec, dict) and set(spec) == {"literal"} and
                    isinstance(spec["literal"], str) and atom in spec["literal"]):
                return True

    def exact_node(value):
        if isinstance(value, dict):
            return any(exact_node(child) for child in value.values())
        if isinstance(value, (list, tuple)):
            return any(exact_node(child) for child in value)
        return value == atom

    return any(binding.kind in {"conditional", "supporting-conditional"} and
               SEMANTIC_REF not in binding.refs and
               exact_node(binding.value) for binding in state.bindings.values())


def _trace_argument(state: RuntimeState, spec, value, equal,
                    delegated_refs=(), semantic_refs=(),
                    allow_semantic=False):
    """Return the exact proof refs for one Contract argument specification."""
    if isinstance(spec, dict) and set(spec) == {"literal"}:
        return (equal(spec["literal"], value), (QUERY_REF,))
    if isinstance(spec, dict) and set(spec) == {"from"}:
        sources = spec["from"]
        sources = [sources] if isinstance(sources, str) else list(sources or ())
        for source in sources:
            resolved = state.output(source)
            if resolved is not UNRESOLVED and equal(resolved, value):
                binding = state.bindings.get(str(source).partition(".")[0])
                if (binding is not None and
                        SEMANTIC_REF in binding.refs and not allow_semantic):
                    continue
                return (True, binding.refs if binding is not None else ())
        refs = tuple(dict.fromkeys(map(str, semantic_refs or ())))
        if refs and (allow_semantic or SEMANTIC_REF not in refs):
            return (True, refs)
        return (False, ())
    if (isinstance(spec, dict) and
            set(spec) == {"from", "delegated"} and
            spec.get("delegated") is True):
        refs = tuple(dict.fromkeys(map(str, delegated_refs or ())))
        return (bool(refs), refs)
    return (equal(spec, value), (QUERY_REF,))


def _check_clause(state: RuntimeState, contract, clause: EffectClause,
                  arguments: dict, required, content, content_atoms,
                  delegated_proofs, semantic_proofs, equal) -> Verdict:
    contracted = frozenset(clause.effect_arguments)
    extra = next((name for name in arguments if name not in contracted), None)
    if extra is not None:
        return Verdict(False, f"uncontracted-arg:{extra}")
    missing = next((name for name in required if name not in arguments), None)
    if missing is not None:
        return Verdict(False, f"missing-arg:{missing}")

    refs = []
    for name, value in arguments.items():
        ok, proof_refs = _trace_argument(
            state, clause.effect_arguments.get(name), value,
            lambda left, right: equal(name, left, right),
            delegated_proofs.get((clause.id, name), ()),
            semantic_proofs.get((clause.id, name), ()),
            name in content)
        if not ok:
            return Verdict(False, f"untraceable-arg:{name}")
        refs.extend(proof_refs)

    unauthorized = None
    for name, atoms in content_atoms.items():
        spec = clause.effect_arguments.get(name)
        local_delegation = (
            isinstance(spec, dict) and
            set(spec) == {"from", "delegated"} and
            bool(delegated_proofs.get((clause.id, name))))
        unauthorized = next(
            (atom for atom in atoms
             if not local_delegation and
             not _atom_authorized(state, contract, atom)), None)
        if unauthorized is not None:
            break
    if unauthorized is not None:
        return Verdict(False, "unauthorized-content-atom:" + unauthorized)
    return Verdict(True, "traced", tuple(dict.fromkeys(refs)))


def check_effect(state: RuntimeState, contract, action: str, arguments: dict,
                 *, required=frozenset(), content=frozenset(),
                 content_atoms=None, delegated_proofs=None,
                 semantic_proofs=None,
                 equal=None) -> Verdict:
    """PASS iff one Root Effect Clause closes every supplied argument."""
    action, arguments = str(action), dict(arguments or {})
    content_atoms = dict(content_atoms or {})
    delegated_proofs = dict(delegated_proofs or {})
    semantic_proofs = dict(semantic_proofs or {})
    equal = equal or (lambda _name, left, right: left == right)
    clauses = [clause for clause in contract.clauses
               if isinstance(clause, EffectClause) and clause.action == action]
    if not clauses:
        return Verdict(False, f"unauthorized-action:{action}")
    first_failure = None
    for clause in clauses:
        verdict = _check_clause(
            state, contract, clause, arguments, frozenset(required),
            frozenset(content), content_atoms, delegated_proofs,
            semantic_proofs, equal)
        if verdict.ok:
            return verdict
        first_failure = first_failure or verdict
    return first_failure or Verdict(False, "untraceable")
