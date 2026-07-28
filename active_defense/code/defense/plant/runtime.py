"""PLANT deployment materialization and commitment detection."""
import hashlib
import json

from .model import Plant, PlantDeployment, PlantEvent, PlantSlotTrace
from .structure import _changed_leaf, _contains, _plain, _token_locations


class PlantRuntime:
    """Deploy after source resolution and before exposing an observation."""
    def __init__(self, plants=(), placement_agent=None):
        self.plants = {plant.source: plant for plant in plants}
        self._versions: dict[tuple[str, str, str], Plant | None] = {}
        self.deployed: dict[str, Plant] = {}
        self.deployment_trace: dict[str, PlantDeployment] = {}
        self.slot_trace: dict[tuple[str, str], PlantSlotTrace] = {}
        self.placement_agent = placement_agent
        self._model_calls_start = int(getattr(placement_agent, "model_calls", 0))
        self._cache_hits_start = int(getattr(placement_agent, "cache_hits", 0))

    def stats(self) -> dict[str, int]:
        return {
            "model_calls": int(getattr(self.placement_agent, "model_calls", 0)) - self._model_calls_start,
            "cache_hits": int(getattr(self.placement_agent, "cache_hits", 0)) - self._cache_hits_start,
        }

    def register(self, plant: Plant) -> None:
        self.plants[plant.source] = plant

    def expose(self, source: str, observation, injector, source_kind: str | None = None,
               normal_operand_guard=None, *, placement_context=None,
               receipt_digest: str = ""):
        source = str(source)
        plant = self.plants.get(source)
        source_version = None
        if plant is None:
            original = _plain(observation)
            encoded = json.dumps(original, ensure_ascii=False, sort_keys=True,
                                 separators=(",", ":"), default=str)
            content_version = hashlib.sha256(encoded.encode()).hexdigest()
            version = (source, content_version, str(receipt_digest or ""))
            source_version = (str(source_kind or source), content_version)
            skeleton_selected = bool(
                self.placement_agent is not None and
                self.placement_agent.has_slot(str(source_kind or source)))
            if skeleton_selected and source_version not in self.slot_trace:
                self.slot_trace[source_version] = PlantSlotTrace(
                    source_version[0], source_version[1], source, "exposed")
            if version in self._versions:
                plant = self._versions[version]
            else:
                if self.placement_agent is None:
                    candidate = None
                elif normal_operand_guard is None and placement_context is None:
                    candidate = self.placement_agent.place(
                        source, observation, str(source_kind or source))
                else:
                    candidate = self.placement_agent.place(
                        source, observation, str(source_kind or source),
                        normal_operand_guard, placement_context)
                plant = candidate if isinstance(candidate, Plant) else None
                self._versions[version] = plant
        if plant is None:
            if source_version is not None and source_version in self.slot_trace:
                trace = self.slot_trace[source_version]
                self.slot_trace[source_version] = PlantSlotTrace(
                    trace.source_kind, trace.version, trace.source, "abstained")
            return observation
        planted = injector(observation, plant.payload)
        if _contains(planted, plant.token, exact=False):
            self.deployed[plant.token] = plant
            changed = _changed_leaf(_plain(observation), _plain(planted))
            if plant.token not in self.deployment_trace:
                if changed is not None:
                    locator, before, after = changed
                    digest = str(receipt_digest or "")
                    canonical_ref = digest + "#" + locator if digest else ""
                    self.deployment_trace[plant.token] = PlantDeployment(
                        plant.token, plant.source, locator, before, after,
                        digest, canonical_ref,
                        (canonical_ref,) if canonical_ref else ())
            elif changed is not None:
                prior = self.deployment_trace[plant.token]
                locator, before, after = changed
                digest = str(receipt_digest or "")
                canonical_ref = digest + "#" + locator if digest else ""
                refs = tuple(dict.fromkeys(
                    prior.canonical_refs +
                    ((canonical_ref,) if canonical_ref else ())))
                self.deployment_trace[plant.token] = PlantDeployment(
                    prior.plant, prior.source, prior.locator,
                    prior.before, prior.after, prior.receipt_digest,
                    prior.canonical_ref, refs)
            if source_version is not None and source_version in self.slot_trace:
                trace = self.slot_trace[source_version]
                self.slot_trace[source_version] = PlantSlotTrace(
                    trace.source_kind, trace.version, trace.source, "deployed")
        elif source_version is not None and source_version in self.slot_trace:
            trace = self.slot_trace[source_version]
            self.slot_trace[source_version] = PlantSlotTrace(
                trace.source_kind, trace.version, trace.source, "abstained")
        return planted

    def detect(self, value, channel: str = "effect") -> list[PlantEvent]:
        events = []
        for plant in self.deployed.values():
            locations = tuple(_token_locations(value, plant.token))
            if locations:
                events.append(PlantEvent(
                    plant.token, plant.source, channel,
                    locations[0] if len(locations) == 1 else ""))
        return events

    def close(self) -> dict:
        """Erase task-local markers and raw deployment operands."""
        audit = {
            "deployed": [plant.token for plant in self.deployed.values()],
            "deployments": [{
                "plant": item.plant,
                "locator": item.locator,
                "receipt_digest": item.receipt_digest,
                "canonical_ref": item.canonical_ref,
                "canonical_refs": list(item.canonical_refs),
            } for item in self.deployment_trace.values()],
            "slots": [{
                "source_kind": item.source_kind,
                "version": item.version,
                "source_digest": hashlib.sha256(
                    item.source.encode()).hexdigest(),
                "outcome": item.outcome,
            } for item in self.slot_trace.values()],
            "placements": [{
                "source_kind": item.get("source_kind", ""),
                "binding": item.get("binding", {}),
                "bound_acquire_clauses": item.get(
                    "bound_acquire_clauses", []),
                "sink_clauses": item.get("sink_clauses", []),
                "outcome": item.get("outcome", ""),
                "answer_status": (item.get("answer") or {}).get("status", ""),
                "selected_sink": ":".join(filter(None, (
                    str((item.get("answer") or {}).get("sink_clause", "")),
                    str((item.get("answer") or {}).get("sink_argument", ""))))),
                "extra_count": int(
                    (item.get("answer") or {}).get("status") == "place"),
                "operand_digest": (hashlib.sha256(str(
                    (item.get("answer") or {}).get("exact_text", "")).encode()).hexdigest()
                                   if (item.get("answer") or {}).get("exact_text") else ""),
            } for item in getattr(self.placement_agent, "trace", ())],
            **self.stats(),
        }
        self.plants.clear()
        self._versions.clear()
        self.deployed.clear()
        self.deployment_trace.clear()
        self.slot_trace.clear()
        close_task = getattr(self.placement_agent, "close_task", None)
        if callable(close_task):
            close_task()
        return audit
