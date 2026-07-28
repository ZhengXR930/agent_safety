"""Small orchestration kernel for the current PLANT–WRAP design."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

from .detector import Decision, Detector, ProposalBuffer
from .plant import Plant, PlantPlacementAgent, PlantRuntime
from .surveyor import Surveyor
from .taskcontractor import TaskContractor
from .taskcontractor import TaskContract
from .wrap import (BindingPlacementAgent, GateResult, Provenance,
                   SavedStateStore, WrapRuntime)


@dataclass
class Episode:
    contract: object
    wrap: WrapRuntime
    plant: PlantRuntime
    detector: Detector
    proposals: ProposalBuffer

    def expose(self, source: str, observation, injector, source_kind: str | None = None):
        kind = str(source_kind or source)
        return self.plant.expose(
            source, observation, injector, kind,
            placement_context=self.wrap.plant_manifest_context(kind))

    def observe(self, capability: str, arguments: dict, observation, injector,
                *, source: str | None = None, receipt_value=None,
                call_id: str | None = None, recovery=None):
        """Log the canonical return, then expose an independently decorated view."""
        capability, arguments = str(capability), dict(arguments or {})
        source = str(source or (capability + ":" + json.dumps(
            arguments, sort_keys=True, ensure_ascii=False, default=str,
            separators=(",", ":"))))
        canonical = receipt_value(observation) if callable(receipt_value) else observation
        receipt = self.wrap.observe(capability, arguments, canonical, call_id=call_id)

        visible = recovery.sanitize(receipt) if recovery is not None else canonical
        base = (injector(observation, visible)
                if recovery is not None and visible != canonical else observation)
        exposed = self.plant.expose(
            source, base, injector, capability,
            lambda operand: self.wrap.protects_plant_operand(
                operand, receipt.digest),
            placement_context=self.wrap.plant_placement_context(receipt.digest),
            receipt_digest=receipt.digest)
        return exposed

    def _recover_plant_commitment(self, effect: str, arguments: dict,
                                  decision: Decision, call_id: str | None):
        """Quarantine the committed operand and replay only exact WRAP evidence.

        Commitment rejects the current proposal, not the whole task.  Recovery
        cannot restore the original planted operand; it must reconstruct every
        argument from remaining Contract authority and pass both defenses again.
        """
        if not decision.plant_events or decision.evidence is None:
            return None
        clause = decision.evidence.clause
        if not clause:
            return None
        excluded = []
        for event in decision.plant_events:
            deployment = self.plant.deployment_trace.get(event.plant)
            if deployment is not None:
                excluded.extend(deployment.canonical_refs or
                                ((deployment.canonical_ref,)
                                 if deployment.canonical_ref else ()))
        excluded = tuple(dict.fromkeys(ref for ref in excluded if ref))
        if not excluded:
            return None
        self.wrap.quarantine_refs(excluded)
        clean = self.wrap.recovery_bindings(clause, excluded)
        if not clean or self.plant.detect(clean, channel=f"recovery:{effect}"):
            return None
        evidence = self.wrap.evidence(effect, clean)
        recovered = self.detector.decide(
            self.contract.task, effect, clean, evidence, (), self.wrap.context())
        if recovered.route != "pass":
            return None
        return Decision(
            "pass", "PLANT commitment recovered", evidence.clause, evidence,
            decision.plant_events, clean)

    def propose(self, effect: str, arguments: dict,
                call_id: str | None = None) -> Decision:
        evidence = self.wrap.evidence(effect, arguments)
        if (not evidence.complete and
                self.wrap.try_dynamic_expansion(effect, arguments, "effect")):
            evidence = self.wrap.evidence(effect, arguments)
            if self.plant.placement_agent is not None:
                self.plant.placement_agent.contract = self.contract
        # A mediated capability may be a final effect for one clause and an
        # observation source for another.  Do not let the first failed final
        # interpretation suppress a complete intermediate interpretation.
        if not evidence.complete:
            intermediate = self.wrap.intermediate_evidence(effect, arguments)
            if intermediate.complete:
                evidence = intermediate
            elif intermediate.provenance.clause is not None:
                # A concrete receipt location exists, but its local semantic
                # role is not proved. This is an Approval gap, not an
                # unauthorized-action conflict.
                evidence = intermediate
            elif evidence.conflicts and self.wrap.has_declared_intermediate(effect):
                evidence = GateResult(Provenance(action=effect),
                                      unresolved=("$interpretation",))
        if (evidence.conflicts == ("$action",) and
                self.wrap.active_open_delegation_regions()):
            evidence = GateResult(
                Provenance(action=effect), unresolved=("$delegated_action",))
        plant_events = self.plant.detect(arguments, channel=f"effect:{effect}")
        decision = self.detector.decide(
            self.contract.task, effect, arguments, evidence, plant_events,
            self.wrap.context())
        if plant_events:
            decision = (self._recover_plant_commitment(
                effect, arguments, decision, call_id) or decision)
        if decision.route == "pass":
            passed = decision.evidence or evidence
            committed = decision.recovered_arguments or arguments
            if self.wrap.bind_effect(passed, committed, call_id):
                admitted = self.wrap.admit_effect_return(
                    effect, committed, call_id, passed.provenance.clause)
                if not admitted:
                    self.wrap.admit_observation_call(
                        effect, committed, passed.provenance.clause, call_id)
            else:
                self.wrap.admit_observation_call(
                    effect, committed, passed.provenance.clause, call_id)
        if decision.route != "pass":
            self.proposals.add(evidence.provenance.clause, effect, arguments, decision)
        return decision

    def propose_intermediate(self, capability: str, arguments: dict,
                             call_id: str | None = None) -> Decision:
        """Mediate only the outbound side of an observation-producing call.

        A dual capability is not interpreted as a final task effect.  Its call
        arguments are reconciled against an authorizing observation Clause;
        the returned value remains an unowned receipt.
        """
        observation_evidence = self.wrap.intermediate_evidence(capability, arguments)
        evidence = observation_evidence
        if (not evidence.complete and self.wrap.try_dynamic_expansion(
                capability, arguments, "intermediate")):
            observation_evidence = self.wrap.intermediate_evidence(
                capability, arguments)
            effect_evidence = self.wrap.evidence(capability, arguments)
            evidence = (effect_evidence if effect_evidence.complete else
                        observation_evidence)
            if self.plant.placement_agent is not None:
                self.plant.placement_agent.contract = self.contract
        plant_events = self.plant.detect(
            arguments, channel=f"effect:{capability}")
        decision = self.detector.decide(
            self.contract.task, capability, arguments, evidence, plant_events,
            self.wrap.context())
        if plant_events:
            decision = (self._recover_plant_commitment(
                capability, arguments, decision, call_id) or decision)
        if decision.route == "pass":
            passed = decision.evidence or evidence
            committed = decision.recovered_arguments or arguments
            if self.wrap.bind_effect(passed, committed, call_id):
                admitted = self.wrap.admit_effect_return(
                    capability, committed, call_id,
                    passed.provenance.clause)
                if not admitted:
                    self.wrap.admit_observation_call(
                        capability, committed,
                        observation_evidence.provenance.clause, call_id)
            else:
                self.wrap.admit_observation_call(
                    capability, committed, passed.provenance.clause, call_id)
        if decision.route != "pass":
            self.proposals.add(
                evidence.provenance.clause, capability, arguments, decision)
        return decision

    def prepare_observation(self, capability: str, arguments: dict,
                            call_id: str | None = None) -> bool:
        """Admit a pure read when its task role is proved; never block the read."""
        evidence = self.wrap.intermediate_evidence(capability, arguments)
        if (not evidence.complete and self.wrap.try_dynamic_expansion(
                capability, arguments, "intermediate")):
            evidence = self.wrap.intermediate_evidence(capability, arguments)
            if self.plant.placement_agent is not None:
                self.plant.placement_agent.contract = self.contract
        if not evidence.complete:
            return False
        return self.wrap.admit_observation_call(
            capability, arguments, evidence.provenance.clause, call_id)

    def review(self, scope: str): return self.proposals.drain(scope)

    def approve(self, effect: str, arguments: dict,
                parent_clause: str | None = None) -> Decision:
        """Install one exact one-shot user grant and re-run WRAP."""
        clause = self.wrap.install_approval_grant(
            effect, arguments, parent_clause)
        if clause is None:
            evidence = self.wrap.evidence(effect, arguments)
            return Decision("auditor", "approval cannot authorize this capability",
                            evidence.clause, evidence)
        return self.propose(effect, arguments, "approval:" + clause.id)

    def executable_arguments(self, effect: str, arguments: dict,
                             decision: Decision) -> dict:
        """Return the exact argument set that may be committed after Pass."""
        if decision.route != "pass":
            return dict(arguments or {})
        if decision.recovered_arguments:
            arguments = dict(decision.recovered_arguments)
        clause = decision.evidence.clause if decision.evidence is not None else None
        return self.wrap.executable_arguments(effect, arguments, clause)

    def record_state(self, state_id: str, value, arguments: dict, decision: Decision) -> bool:
        """Record only an actually allowed state commit."""
        if decision.route != "pass" or decision.evidence is None:
            return False
        return self.wrap.record_state(state_id, value, arguments, decision.evidence)

    def observe_state(self, source: str, arguments: dict, state_id: str, value):
        return self.wrap.observe_state(source, arguments, state_id, value)

    @property
    def task_id(self) -> str:
        return self.wrap.task_id

    def close(self) -> dict:
        """Finish this task and erase its live Runtime Receipts."""
        audit = self.wrap.close()
        audit["plant"] = self.plant.close()
        self.proposals.drain("task-close")
        return audit

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        self.close()
        return False


class Engine:
    """Perceive once; specialize by trusted task; run independent PLANT and WRAP."""
    def __init__(self, client=None, model: str = "deepseek-chat",
                 reference_resolvers=None):
        self.client, self.model = client, model
        self.reference_resolvers = dict(reference_resolvers or {})
        self.plan = None
        self._contracts = {}
        self._contract_traces = {}
        self._plant_plan_caches = {}
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
        Surveyor.validate_boundary_manifest(tool_schemas)
        material = json.dumps({"plant_skeleton": "observation-v1",
                               "tools": tool_schemas, "sources": source_carriers},
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

    def perceive_skills(self, skill_files, capability_manifest):
        self.plan = Surveyor(self.client, self.model).perceive_skills(
            skill_files, capability_manifest)
        return self.plan

    def register_trusted_tools(self, tools, store, source_carriers=(), refresh: bool = False):
        """Persist a compact manifest from an operator-approved tool registration."""
        self._attach_state_store(store)
        tools = list(tools or ())
        source_carriers = list(source_carriers or ())
        Surveyor.validate_boundary_manifest(tools)
        material = json.dumps({"plant_skeleton": "observation-v1",
                               "tools": tools, "sources": source_carriers},
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

    def _contract_key(self, trusted_task: str, effect_entries=None) -> tuple[str, tuple[str, ...]]:
        entries = tuple(sorted(map(str, effect_entries or ())))
        material = ("clauses-agent-semantic-binding\0" +
                    TaskContractor.prompt_digest() + "\0" +
                    str(getattr(self.plan, "id", "")) + "\0" +
                    str(trusted_task) + "\0" + repr(entries))
        return hashlib.sha256(material.encode()).hexdigest(), entries

    def contract(self, trusted_task: str, effect_entries=None):
        if self.plan is None:
            raise RuntimeError("perceive() must run before contract synthesis")
        key, entries = self._contract_key(trusted_task, effect_entries)
        if key not in self._contracts:
            saved = self.store.load_contract(key) if self.store is not None else None
            if saved:
                self._contracts[key] = TaskContract.from_dict(saved)
                self._contract_traces[key] = self.store.load_contract_trace(key)
            else:
                contractor = TaskContractor(self.client, self.model)
                contract, trace = contractor.extract_with_trace(
                    trusted_task, self.plan, effect_entries=entries or None)
                self._contracts[key] = contract
                self._contract_traces[key] = trace
                if self.store is not None:
                    self.store.save_contract(key, contract.to_dict(), trace)
        return self._contracts[key]

    def contract_trace(self, trusted_task: str, effect_entries=None) -> dict | None:
        """Return the exact cached synthesis trace for research diagnostics."""
        key, _ = self._contract_key(trusted_task, effect_entries)
        if key not in self._contracts:
            self.contract(trusted_task, effect_entries)
        return self._contract_traces.get(key)

    def plant_agent(self, contract, client=None, model: str | None = None):
        """Create an Episode-local Agent over one shared immutable PlantPlan cache."""
        client = self.client if client is None else client
        model = str(model or self.model)
        material = json.dumps({
            "environment": str(getattr(self.plan, "id", "")),
            "contract": contract.to_dict(),
            "model": model,
        }, sort_keys=True, ensure_ascii=False, default=str,
           separators=(",", ":"))
        key = hashlib.sha256(material.encode()).hexdigest()
        plan_cache = self._plant_plan_caches.setdefault(key, {})
        return PlantPlacementAgent(
            client, model, contract,
            environment_sources=getattr(self.plan, "sources", {}),
            plan_cache=plan_cache)

    def clear_plant_plans(self) -> None:
        """End a benchmark/task group and destroy its non-authority plan cache."""
        self._plant_plan_caches.clear()

    def start(self, contract, plants=(), runtime_context=None,
              task_id: str | None = None) -> Episode:
        if runtime_context:
            source = getattr(self.plan, "sources", {}).get("runtime-context")
            if source is None or source.plantable:
                raise ValueError("runtime context requires a non-plantable registered SourceSurface")
        execution_contract = TaskContract.from_dict(contract.to_dict())
        binding_agent = BindingPlacementAgent(self.client, self.model)
        return Episode(execution_contract, WrapRuntime(
            execution_contract, getattr(self.plan, "capabilities", {}),
            binding_agent, runtime_context,
            self.state_store, self.reference_resolvers, task_id,
            binding_agent), PlantRuntime(
                plants, self.plant_agent(execution_contract)),
            Detector(self.client, self.model), ProposalBuffer())
