"""Small orchestration kernel for the current PLANT–WRAP design."""
from __future__ import annotations

import hashlib
from dataclasses import dataclass

from .detector import Decision, Detector, ProposalBuffer
from .plant import Plant, PlantDesigner, PlantRuntime
from .surveyor import Surveyor
from .taskcontractor import TaskContractor
from .taskcontractor import TaskContract
from .wrap import SemanticJudge, WrapRuntime


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
        plant_events = self.plant.detect(arguments, channel=f"effect:{effect}")
        decision = self.detector.decide(
            self.contract.task, effect, arguments, evidence, plant_events,
            self.wrap.context())
        if decision.route != "pass":
            self.proposals.add(evidence.clause, effect, arguments, decision)
        return decision

    def review(self, scope: str): return self.proposals.drain(scope)


class Engine:
    """Perceive once; specialize by trusted task; run independent PLANT and WRAP."""
    def __init__(self, client=None, model: str = "deepseek-chat"):
        self.client, self.model = client, model
        self.plan = None
        self._contracts = {}
        self.store = None

    def perceive(self, tool_schemas, source_carriers=(), store=None, refresh: bool = False):
        self.store = store
        if store is not None and not refresh:
            saved = store.load()
            if saved and (saved.get("payload") or {}).get("environment"):
                from .memory import EnvironmentPlan
                self.plan = EnvironmentPlan.from_dict(saved["payload"]["environment"])
                return self.plan
        self.plan = Surveyor(self.client, self.model).perceive(tool_schemas, source_carriers)
        if store is not None:
            store.save({"environment": self.plan.to_dict()}, "environment perception")
        return self.plan

    def perceive_skills(self, skill_files):
        self.plan = Surveyor(self.client, self.model).perceive_skills(skill_files)
        return self.plan

    def contract(self, trusted_task: str, effect_entries=None):
        if self.plan is None:
            raise RuntimeError("perceive() must run before contract synthesis")
        entries = tuple(sorted(map(str, effect_entries or ())))
        material = ("clauses-v10-compact\0" + str(getattr(self.plan, "id", "")) +
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

    def start(self, contract, plants=()) -> Episode:
        return Episode(contract, WrapRuntime(
            contract, getattr(self.plan, "capabilities", {}),
            SemanticJudge(self.client, self.model)), PlantRuntime(
                plants, PlantDesigner(self.client, self.model, contract)),
            Detector(self.client, self.model), ProposalBuffer())
