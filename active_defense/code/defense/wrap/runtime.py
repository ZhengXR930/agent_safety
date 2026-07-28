"""Clause-local WRAP gates with provenance separated from gate verdicts."""
from __future__ import annotations

import hashlib
import uuid

from ..contract import (AcquireClause, ClauseBindingStore, EffectClause, TaskContract)
from .model import InstalledGate, RuntimeReceiptRecorder, _stable
from .binding import BindingPlacementAgent
from .gate import GateRuntimeMixin
from .dynamic import DynamicExpansionRuntimeMixin
from .receipts import ReceiptRuntimeMixin
from .resolver import ResolutionRuntimeMixin


class SavedStateStore:
    """Persist only an exact state version and whether upstream authority existed."""
    def __init__(self, data=None, persist=None):
        data = data if isinstance(data, dict) else {}
        self.states = dict(data.get("states") or {})
        self.persist = persist

    @staticmethod
    def _value_digest(value):
        return hashlib.sha256(_stable(value).encode()).hexdigest()

    def record(self, state_id: str, value, authorized: bool):
        self.states[str(state_id)] = {"digest": self._value_digest(value),
                                      "authorized": bool(authorized)}
        if callable(self.persist): self.persist(self.to_dict())

    def restore(self, state_id: str, value) -> str:
        saved = self.states.get(str(state_id))
        if not isinstance(saved, dict) or saved.get("digest") != self._value_digest(value):
            return "unknown"
        return "authorized" if saved.get("authorized") is True else "unauthorized"

    def to_dict(self):
        return {"states": self.states}


class WrapRuntime(ReceiptRuntimeMixin, ResolutionRuntimeMixin, GateRuntimeMixin,
                  DynamicExpansionRuntimeMixin):
    """Install clause gates once; bind receipts and derive clause outputs at runtime."""
    def __init__(self, contract: TaskContract, capabilities=None, placement_agent=None,
                 runtime_context=None, state_store=None, reference_resolvers=None,
                 task_id: str | None = None, expansion_agent=None):
        self.contract, self.capabilities = contract, capabilities or {}
        self._root_contract = contract.to_dict()
        self._root_effect_clauses = tuple(
            clause for clause in contract.clauses
            if isinstance(clause, EffectClause))
        self.expansion_agent = expansion_agent
        self.dynamic_contract_trace = []
        self._expansion_cache = {}
        self.task_id = str(task_id or uuid.uuid4().hex)
        self.receipt_recorder = RuntimeReceiptRecorder(self.task_id)
        self.placement_agent = placement_agent
        if isinstance(placement_agent, BindingPlacementAgent):
            placement_agent.output_schemas = {
                name: surface.output_schema for name, surface in self.capabilities.items()
                if surface.output_schema is not None}
        self.reference_resolvers = dict(reference_resolvers or {})
        self._task_receipt = self.receipt_recorder.issue(
            "task", {}, contract.task, record=False)
        self._contract_digest = hashlib.sha256(
            _stable(contract.to_dict()).encode()).hexdigest()
        self.binding_store = ClauseBindingStore(
            self.task_id, self._task_receipt.digest, self._contract_digest,
            contract.clauses,
            lambda digest, capability: any(
                receipt.digest == digest and receipt.source == capability
                for receipt in self.receipt_recorder.observations))
        trusted_context = {}
        for action, values in (runtime_context or {}).items():
            surface = self.capabilities.get(str(action))
            if surface is not None and isinstance(values, dict):
                kept = {str(k): v for k, v in values.items()
                        if str(k) in set(surface.arguments)}
                if kept: trusted_context[str(action)] = kept
        self._context_receipt = (self.receipt_recorder.issue(
            "runtime-context", {}, trusted_context, record=False)
                                 if trusted_context else None)
        self.state_store = state_store or SavedStateStore()
        self._state_status = {}
        self.observations = self.receipt_recorder.observations
        self._source_clauses: dict[str, tuple[AcquireClause, ...]] = {}
        for clause in self.contract.clauses:
            if isinstance(clause, AcquireClause):
                self._source_clauses.setdefault(clause.capability, ())
                self._source_clauses[clause.capability] += (clause,)
        # Install the complete commit boundary once, before the Agent runs.
        # Runtime data may populate these gates but cannot create another gate.
        self.gates = tuple(InstalledGate.from_clause(clause)
                           for clause in self.contract.clauses
                           if isinstance(clause, EffectClause))
        self._gates_by_action: dict[str, tuple[InstalledGate, ...]] = {}
        for gate in self.gates:
            self._gates_by_action.setdefault(gate.action, ())
            self._gates_by_action[gate.action] += (gate,)
        self.intermediate_trace = []
        self._placement_cache = {}
        self._binding_agent_runs = set()
        self.clause_bindings = self.binding_store.bindings
        self.receipt_bindings = self.clause_bindings  # legacy result key
        self._bound_receipts: dict[str, set[str]] = {}
        self._pending_observation_calls: dict[str, tuple[str, tuple[str, ...]]] = {}
        self._pending_effect_return_calls: set[str] = set()
        self._pending_effect_return_parents: dict[str, str] = {}
        self._effect_return_receipts: set[tuple[str, str]] = set()
        self._effect_return_origins: dict[str, str] = {}
        self._invalid_schema_receipts: set[str] = set()
        self._superseded_receipts: set[str] = set()
        self._quarantined_refs: set[str] = set()
        self._approval_grants: dict[str, dict] = {}
        self._approval_effect_bindings: list[dict] = []
        self._delegation_slice_cache: dict[tuple[str, str, str], dict | None] = {}
        self._dynamic_output_values: dict[str, tuple] = {}

    def _binding_proposal_version(self, action: str, arguments: dict) -> str:
        """One semantic-call budget for one proposal and evidence version."""
        material = {
            "action": str(action),
            "arguments": dict(arguments or {}),
            "receipts": sorted(
                receipt.digest for receipt in self._authority_observations()),
            "quarantined": sorted(self._quarantined_refs),
            "superseded": sorted(self._superseded_receipts),
        }
        return hashlib.sha256(_stable(material).encode()).hexdigest()

    def close(self) -> dict:
        """End this task and destroy all live receipt values and Clause bindings."""
        audit = self.receipt_recorder.close()
        audit["clause_bindings"] = self.binding_store.close()
        audit["dynamic_contracts"] = list(self.dynamic_contract_trace)
        audit["dynamic_agent_calls"] = int(
            getattr(self.expansion_agent, "model_calls", 0))
        audit["approval_effects"] = list(self._approval_effect_bindings)
        self._task_receipt = None
        self._context_receipt = None
        self._bound_receipts.clear()
        self._pending_observation_calls.clear()
        self._pending_effect_return_calls.clear()
        self._pending_effect_return_parents.clear()
        self._effect_return_receipts.clear()
        self._effect_return_origins.clear()
        self._invalid_schema_receipts.clear()
        self._superseded_receipts.clear()
        self._quarantined_refs.clear()
        self._approval_grants.clear()
        self._approval_effect_bindings.clear()
        self._delegation_slice_cache.clear()
        self._dynamic_output_values.clear()
        self._placement_cache.clear()
        self._binding_agent_runs.clear()
        self._expansion_cache.clear()
        self.dynamic_contract_trace.clear()
        self._state_status.clear()
        return audit

