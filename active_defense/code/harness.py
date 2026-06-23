"""Multi-role active-defense harness (defense shell around an agent).

Implements the 4 roles from Discussion.md §3 as composable objects, so the same
shell can wrap any AgentDojo-style agent:

  ① Planner     (offline, env-level)   -> build static marker library 𝓜
  ② Selector    (runtime, task-level)  -> pick/place M ⊆ 𝓜 for this task
  ③ TouchLogger (runtime, harness)     -> record every agent action (full touch)
  ④ Updater     (periodic, offline)    -> evolve 𝓜 under I(M)≤ε  (skeleton)
  + Detector    (runtime, policy-free) -> commitment-touch: touch(ρ)∩M ≠ ∅

The marker mechanisms live in markers.py; this file is the orchestration layer.
Benchmark wiring is isolated in AgentDojoBinding so other benchmarks can be added.
"""

from __future__ import annotations

import sys
from pathlib import Path
from dataclasses import asdict, dataclass, field
from typing import Any, Callable

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import markers as M
import role_boundary_actions as RBA


# ============================================================
# Marker library entry (uniform across carriers / families)
# ============================================================

@dataclass
class Marker:
    mid: str
    family: str          # "decoy" | "transition"
    carrier: str         # "capability" | "data" | "memory" | "rag" | "mcp" | "authority"
    spec: dict           # carrier-specific payload (tool spec / source / honey-action ...)


@dataclass
class MarkerLibrary:
    """Static, environment-level candidate set 𝓜 (built offline by the Planner)."""
    env_name: str
    markers: list[Marker] = field(default_factory=list)

    def by_carrier(self, carrier: str) -> list[Marker]:
        return [m for m in self.markers if m.carrier == carrier]


# ============================================================
# ① Planner — offline, environment-level
# ============================================================

class Planner:
    """Scan an environment's affordance surface and build the static marker library 𝓜.

    Environment-agnostic interface: a binding supplies the raw affordance views
    (tool list, sensitive data fields, authority domains); the planner turns them
    into candidate markers across carriers. LLM generation is optional and only
    used to synthesize plausible capability decoys.
    """

    def __init__(self, model: str | None = None, gen_capability_decoys: bool = True):
        self.model = model or M.DEFAULT_INTERNAL_MODEL
        self.gen_capability_decoys = gen_capability_decoys

    def build(self, binding: "BenchmarkBinding") -> MarkerLibrary:
        lib = MarkerLibrary(env_name=binding.env_name)
        # legacy capability-carrier decoys: off-domain dangerous-capability tools.
        # Not Family-1 mainline under the current taxonomy; use only for ablation
        # / AgentShield-style tool-trap comparison.
        if self.gen_capability_decoys:
            for spec in binding.capability_decoy_specs(self.model):
                lib.markers.append(Marker(
                    mid=f"cap::{spec['name']}", family="decoy",
                    carrier="capability", spec=spec))
        # objective-level honeypots (family 1): structured fake identifiers planted into env
        for src in binding.sensitive_sources():
            lib.markers.append(Marker(
                mid=f"data::{src['id']}", family="decoy",
                carrier="data", spec=src))
        # boundary-level honeypots (family 2): per-affordance boundary-action templates
        for act in binding.honey_privileged_actions():
            lib.markers.append(Marker(
                mid=f"auth::{act['name']}", family="transition",
                carrier="authority", spec=act))
        return lib

    def build_role_boundary_actions_from_skills(self, env_name: str, skills_dir: Path,
                                                policy: str = "balanced",
                                                radius: int | None = None,
                                                radius_by_skill: dict[str, int] | None = None) -> MarkerLibrary:
        """Generic Family-2 planner for skill-based agents.

        This does not inject files; it only plans skill-level boundary honey
        actions from SKILL.md files and returns them as boundary-carrier markers.
        Placement granularity is per-affordance: ``radius_by_skill`` overrides
        per skill, ``radius`` is uniform, ``policy`` is the legacy fallback.
        Injection is done by role_boundary_actions.inject_role_boundary_honey_actions
        in the benchmark/agent adapter.
        """
        radius_by_skill = radius_by_skill or {}
        lib = MarkerLibrary(env_name=env_name)
        for _, profile in RBA.discover_skill_profiles(skills_dir):
            r = radius_by_skill.get(profile.skill_id, radius)
            action = RBA.plan_role_boundary_action(profile, policy=policy, radius=r)
            lib.markers.append(Marker(
                mid=f"auth::{action.name}", family="transition",
                carrier="authority", spec=asdict(action)))
        return lib


# ============================================================
# ② Selector — runtime, task-level
# ============================================================

class Selector:
    """Pick the placement M ⊆ 𝓜 for the current user task (off-benign-path),
    under a budget k. Coarse-grained, runs once per task (P3)."""

    def __init__(self, budget: int | None = None, families=("decoy", "transition"),
                 carriers=None):
        self.budget = budget
        self.families = set(families)
        self.carriers = set(carriers) if carriers else None

    def select(self, lib: MarkerLibrary, task_prompt: str,
               binding: "BenchmarkBinding") -> list[Marker]:
        cands = [m for m in lib.markers if m.family in self.families]
        if self.carriers:
            cands = [m for m in cands if m.carrier in self.carriers]
        # off-benign-path filter delegated to the binding (task-conditioned)
        cands = binding.filter_offpath(cands, task_prompt)
        if self.budget is not None:
            cands = cands[: self.budget]
        return cands


# ============================================================
# ③ TouchLogger — runtime, harness (records FULL touch, incl. read/recon)
# ============================================================

@dataclass
class TouchEvent:
    step: int
    kind: str            # "invoke" | "bind_param" | "select_target" | "read"
    tool: str
    args: dict
    raw: Any = None


class TouchLogger:
    """Records every agent action. Full touch stream (incl. recon reads) is kept;
    commitment-touch is only a *filter* applied by the Detector (P2)."""

    def __init__(self):
        self.events: list[TouchEvent] = []

    def reset(self):
        self.events = []

    def log_tool_call(self, step: int, tool: str, args: dict, raw: Any = None):
        # an invoke + parameter binding; both recorded as one commitment-capable event
        self.events.append(TouchEvent(step, "invoke", tool, dict(args or {}), raw))

    def log_read(self, step: int, tool: str, args: dict):
        self.events.append(TouchEvent(step, "read", tool, dict(args or {})))

    def commitment_events(self) -> list[TouchEvent]:
        return [e for e in self.events if e.kind in ("invoke", "bind_param", "select_target")]


# ============================================================
# Detector — runtime, policy-free (commitment-touch)
# ============================================================

class Detector:
    """touch(ρ) ∩ M ≠ ∅ over commitment events only. Aggregates the markers.py
    detectors per carrier. No policy, no taint propagation."""

    def __init__(self, placement: list[Marker]):
        self.placement = placement
        self.cap_names = {m.spec["name"] for m in placement if m.carrier == "capability"}
        self.auth_names = {m.spec["name"] for m in placement if m.carrier == "authority"}
        # data-carrier perturbation registry filled at plant time
        self.perturb_registry: dict = {}
        self.detections: list[dict] = []

    def reset(self):
        self.detections = []

    def check_commitment(self, logger: TouchLogger):
        """Run after a rollout: scan commitment events for marker touches."""
        for e in logger.commitment_events():
            if e.tool in self.cap_names:
                self.detections.append({"family": "decoy", "carrier": "capability",
                                        "marker": e.tool, "step": e.step})
            if e.tool in self.auth_names:
                self.detections.append({"family": "transition", "carrier": "authority",
                                        "marker": e.tool, "step": e.step})
            if self.perturb_registry:
                argtext = " ".join(str(v) for v in e.args.values())
                for pid in M.contains_perturbation(argtext, self.perturb_registry):
                    self.detections.append({"family": "decoy", "carrier": "data",
                                            "marker": pid, "step": e.step})
        return self.detections

    @property
    def fired(self) -> bool:
        return len(self.detections) > 0


# ============================================================
# ④ Updater — periodic, offline (skeleton, constrained optimization)
# ============================================================

class Updater:
    """Evolve 𝓜 across sessions. CONSTRAINT (Discussion §3): may only change
    disguise / rotation / position to optimize r(g) (anti-fingerprint, anti-memory)
    and δ (more off-path); it must NOT learn the off-path判定 from observed touches.
    Objective is constrained: max D(M) s.t. I(M) ≤ ε. (Skeleton for now.)"""

    def __init__(self, epsilon: float = 0.02):
        self.epsilon = epsilon
        self.history: list[dict] = []

    def observe(self, lib: MarkerLibrary, placement: list[Marker],
                detections: list[dict], is_attack: bool):
        self.history.append({"placement": [m.mid for m in placement],
                             "detections": detections, "is_attack": is_attack})

    def propose_rotation(self, lib: MarkerLibrary) -> MarkerLibrary:
        # TODO: rotate/refresh perturbation seeds & decoy names to resist memory/fingerprint,
        #       keeping off-path property by construction (only disguise changes).
        return lib


# ============================================================
# Benchmark binding interface
# ============================================================

class BenchmarkBinding:
    """Abstracts a benchmark so the roles stay benchmark-agnostic."""
    env_name: str = "abstract"

    def capability_decoy_specs(self, model: str) -> list[dict]:
        raise NotImplementedError

    def sensitive_sources(self) -> list[dict]:
        return []

    def honey_privileged_actions(self) -> list[dict]:
        return []

    def filter_offpath(self, cands: list[Marker], task_prompt: str) -> list[Marker]:
        return cands
