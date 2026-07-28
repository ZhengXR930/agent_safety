"""Task-scoped runtime witnesses for the four Clause variants."""
from __future__ import annotations

from dataclasses import dataclass

from .model import (AcquireClause, ConditionalClause, DeriveClause,
                    EffectClause)


@dataclass(frozen=True)
class ClauseBinding:
    task_id: str
    task_digest: str
    contract_digest: str
    clause_id: str

    @property
    def kind(self) -> str:
        raise NotImplementedError

    def _base(self) -> dict:
        return {"type": self.kind, "task_id": self.task_id,
                "task": self.task_digest, "contract": self.contract_digest,
                "clause": self.clause_id}


@dataclass(frozen=True)
class AcquireBinding(ClauseBinding):
    receipt_digest: str
    capability: str
    arguments_digest: str

    @property
    def kind(self): return "acquire"

    def to_dict(self):
        return {**self._base(), "receipt": self.receipt_digest,
                "capability": self.capability,
                "arguments_digest": self.arguments_digest}


@dataclass(frozen=True)
class DeriveBinding(ClauseBinding):
    input_refs: tuple[str, ...]
    output_digest: str
    proof: str

    @property
    def kind(self): return "derive"

    def to_dict(self):
        return {**self._base(), "inputs": list(self.input_refs),
                "output_digest": self.output_digest, "proof": self.proof}


@dataclass(frozen=True)
class ConditionalBinding(ClauseBinding):
    operator: str
    operand_refs: tuple[str, ...]
    output_digest: str
    domain_complete: bool

    @property
    def kind(self): return "conditional"

    def to_dict(self):
        return {**self._base(), "operator": self.operator,
                "operands": list(self.operand_refs),
                "output_digest": self.output_digest,
                "domain_complete": self.domain_complete}


@dataclass(frozen=True)
class EffectBinding(ClauseBinding):
    action: str
    arguments_digest: str
    argument_refs: tuple[tuple[str, tuple[str, ...]], ...]
    call_id: str = ""

    @property
    def kind(self): return "effect"

    def to_dict(self):
        return {**self._base(), "action": self.action,
                "arguments_digest": self.arguments_digest,
                "argument_refs": {name: list(refs)
                                  for name, refs in self.argument_refs},
                "call_id": self.call_id}


_EXPECTED = {
    AcquireClause: AcquireBinding,
    DeriveClause: DeriveBinding,
    ConditionalClause: ConditionalBinding,
    EffectClause: EffectBinding,
}


class ClauseBindingStore:
    """Append-only runtime witnesses, isolated to one task execution."""

    def __init__(self, task_id: str, task_digest: str,
                 contract_digest: str, clauses, receipt_owned=None):
        self.task_id = str(task_id)
        self.task_digest = str(task_digest)
        self.contract_digest = str(contract_digest)
        self._clauses = {clause.id: clause for clause in clauses}
        self._receipt_owned = receipt_owned
        self.bindings: list[ClauseBinding] = []
        self.active = True

    def register_clause(self, clause) -> None:
        """Register one task-local Child Clause under the Root Contract digest."""
        if not self.active:
            raise RuntimeError(f"binding store for task {self.task_id} is closed")
        if clause.id in self._clauses:
            raise ValueError("duplicate dynamic Clause id")
        self._clauses[clause.id] = clause

    def add(self, binding: ClauseBinding) -> bool:
        if not self.active:
            raise RuntimeError(f"binding store for task {self.task_id} is closed")
        if (binding.task_id != self.task_id or
                binding.task_digest != self.task_digest or
                binding.contract_digest != self.contract_digest):
            raise ValueError("ClauseBinding task or Contract identity mismatch")
        clause = self._clauses.get(binding.clause_id)
        if clause is None:
            raise ValueError("ClauseBinding references an unknown Clause")
        expected = next((binding_type for clause_type, binding_type in _EXPECTED.items()
                         if isinstance(clause, clause_type)), None)
        if expected is None or not isinstance(binding, expected):
            raise ValueError("ClauseBinding kind does not match its Clause")
        if isinstance(binding, AcquireBinding):
            if binding.capability != clause.capability:
                raise ValueError("AcquireBinding capability does not match its Clause")
            if callable(self._receipt_owned) and not self._receipt_owned(
                    binding.receipt_digest, binding.capability):
                raise ValueError("AcquireBinding receipt is not owned by this task")
        elif isinstance(binding, ConditionalBinding) and binding.operator != clause.operator:
            raise ValueError("ConditionalBinding operator does not match its Clause")
        elif isinstance(binding, EffectBinding) and binding.action != clause.action:
            raise ValueError("EffectBinding action does not match its Clause")
        encoded = binding.to_dict()
        if any(item.to_dict() == encoded for item in self.bindings):
            return False
        self.bindings.append(binding)
        return True

    def for_clause(self, clause_id: str):
        return tuple(item for item in self.bindings
                     if item.clause_id == str(clause_id))

    def snapshot(self):
        return [item.to_dict() for item in self.bindings]

    def close(self):
        audit = self.snapshot()
        self.bindings.clear()
        self._clauses.clear()
        self.active = False
        return audit


# Read compatibility only. New code should say AcquireBinding.
ClauseReceiptBinding = AcquireBinding
