"""Small orchestration kernel for the current PLANT–WRAP design."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

from .detector import Decision, Detector, ProposalBuffer
from .plant import Plant, PlantDesigner, PlantRuntime
from .surveyor import Surveyor
from .taskcontractor import TaskContractor
from .taskcontractor import TaskContract
from .wrap import GateResult, Provenance, SavedStateStore, SemanticJudge, WrapRuntime


@dataclass
class Episode:
    contract: object
    wrap: WrapRuntime
    plant: PlantRuntime
    detector: Detector
    proposals: ProposalBuffer

    def expose(self, source: str, observation, injector, source_kind: str | None = None):
        return self.plant.expose(source, observation, injector, source_kind)

    def propose(self, effect: str, arguments: dict) -> Decision:
        evidence = self.wrap.evidence(effect, arguments)
        # A mediated capability may be a final effect for one clause and an
        # observation source for another.  Do not let the first failed final
        # interpretation suppress a complete intermediate interpretation.
        if not evidence.complete:
            intermediate = self.wrap.intermediate_evidence(effect, arguments)
            if intermediate.complete:
                evidence = intermediate
            elif evidence.conflicts and self.wrap.has_declared_intermediate(effect):
                evidence = GateResult(Provenance(action=effect),
                                      unresolved=("$interpretation",))
        plant_events = self.plant.detect(arguments, channel=f"effect:{effect}")
        decision = self.detector.decide(
            self.contract.task, effect, arguments, evidence, plant_events,
            self.wrap.context())
        if decision.route != "pass":
            self.proposals.add(evidence.provenance.clause, effect, arguments, decision)
        return decision

    def review(self, scope: str): return self.proposals.drain(scope)

    def record_state(self, state_id: str, value, arguments: dict, decision: Decision) -> bool:
        """Record only an actually allowed state commit."""
        if decision.route != "pass" or decision.evidence is None:
            return False
        return self.wrap.record_state(state_id, value, arguments, decision.evidence)

    def observe_state(self, source: str, arguments: dict, state_id: str, value):
        return self.wrap.observe_state(source, arguments, state_id, value)


class Engine:
    """Perceive once; specialize by trusted task; run independent PLANT and WRAP."""
    def __init__(self, client=None, model: str = "deepseek-chat"):
        self.client, self.model = client, model
        self.plan = None
        self._contracts = {}
        self.store = None
        self.state_store = SavedStateStore()

    def _attach_state_store(self, store) -> None:
        self.store = store
        if store is None:
            return
        self.state_store = SavedStateStore(
            store.load_state_receipts(), store.save_state_receipts)

    def perceive(self, tool_schemas, source_carriers=(), store=None, refresh: bool = False):
        self._attach_state_store(store)
        tool_schemas, source_carriers = list(tool_schemas or ()), list(source_carriers or ())
        material = json.dumps({"tools": tool_schemas, "sources": source_carriers},
                              sort_keys=True, ensure_ascii=False, default=str,
                              separators=(",", ":"))
        schema_hash = hashlib.sha256(material.encode()).hexdigest()
        if store is not None and not refresh:
            saved = store.load()
            payload = (saved or {}).get("payload") or {}
            if payload.get("environment") and payload.get("schema_hash") == schema_hash:
                from .memory import EnvironmentPlan
                self.plan = EnvironmentPlan.from_dict(payload["environment"])
                return self.plan
        self.plan = Surveyor(self.client, self.model).perceive(tool_schemas, source_carriers)
        if store is not None:
            store.save({"schema_hash": schema_hash, "environment": self.plan.to_dict()},
                       "environment schema changed")
        return self.plan

    def perceive_skills(self, skill_files):
        self.plan = Surveyor(self.client, self.model).perceive_skills(skill_files)
        return self.plan

    def register_trusted_tools(self, tools, store, source_carriers=(), refresh: bool = False):
        """Persist a compact manifest from an operator-approved tool registration."""
        self._attach_state_store(store)
        tools = list(tools or ())
        source_carriers = list(source_carriers or ())
        material = json.dumps({"tools": tools, "sources": source_carriers},
                              sort_keys=True, ensure_ascii=False, default=str,
                              separators=(",", ":"))
        schema_hash = hashlib.sha256(material.encode()).hexdigest()
        if not refresh:
            saved = store.load()
            payload = (saved or {}).get("payload") or {}
            if payload.get("environment") and payload.get("schema_hash") == schema_hash:
                from .memory import EnvironmentPlan
                self.plan = EnvironmentPlan.from_dict(payload["environment"])
                return self.plan
        self.plan = Surveyor(self.client, self.model).perceive_mcp_registration(
            tools, source_carriers)
        store.save({"schema_hash": schema_hash, "environment": self.plan.to_dict()},
                   "operator-approved MCP registration changed")
        return self.plan

    def register_trusted_mcp(self, tools, store, refresh: bool = False):
        """Backward-compatible MCP registration entry point."""
        return self.register_trusted_tools(tools, store, refresh=refresh)

    def contract(self, trusted_task: str, effect_entries=None):
        if self.plan is None:
            raise RuntimeError("perceive() must run before contract synthesis")
        entries = tuple(sorted(map(str, effect_entries or ())))
        material = ("clauses-v16-object-boundary\0" + str(getattr(self.plan, "id", "")) +
                    "\0" + str(trusted_task) + "\0" + repr(entries))
        key = hashlib.sha256(material.encode()).hexdigest()
        if key not in self._contracts:
            saved = self.store.load_contract(key) if self.store is not None else None
            if saved:
                self._contracts[key] = TaskContract.from_dict(saved)
            else:
                self._contracts[key] = TaskContractor(self.client, self.model).extract(
                    trusted_task, self.plan, effect_entries=entries or None)
                if self.store is not None:
                    self.store.save_contract(key, self._contracts[key].to_dict())
        return self._contracts[key]

    def start(self, contract, plants=(), runtime_context=None) -> Episode:
        if runtime_context:
            source = getattr(self.plan, "sources", {}).get("runtime-context")
            if source is None or source.plantable:
                raise ValueError("runtime context requires a non-plantable registered SourceSurface")
        return Episode(contract, WrapRuntime(
            contract, getattr(self.plan, "capabilities", {}),
            SemanticJudge(self.client, self.model), runtime_context,
            self.state_store), PlantRuntime(
                plants, PlantDesigner(
                    self.client, self.model, contract,
                    environment_sources=getattr(self.plan, "sources", {}))),
            Detector(self.client, self.model), ProposalBuffer())
