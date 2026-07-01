"""Orchestrator — the deploy-time CONDUCTOR at the top of the agent/subagent nesting.

It schedules the defender SUBAGENTS and the optimization into one coherent multi-agent plan,
then hands a calibrated, deployable placement to evaluation.  This is the single entry the
driver calls; it makes the multi-agent dispatch explicit instead of hiding it inside bindings.

  Orchestrator (this file) — conductor; schedules the roles below and the phases
    ├─ Surveyor       SUBAGENT  perceive: a Claude agent EXPLORES the env -> units (all kinds)
    ├─ Camoufleur     SUBAGENT  design covers (script names / gateway prose / decoys) blended
    │                           into THIS env's style; templates are only a fallback
    ├─ Calibrator     code+agent benign-fit: learn delta per role-class via benign episodes
    ├─ Optimizer      code      keep all FP-clean: wrap=full cut-set coverage, plant=certify-gate
    └─ Deployer       code      apply the camouflaged markers into the environment
  Runtime (light, not scheduled here):
       Logger         records commitment-touch (the recorder side-effect)
       Updater        online benign-fit (FP self-correction) + drift adaptation

The Surveyor and Camoufleur are real Claude Code subagents (see defense/subagent.py); the
Calibrator/Optimizer/Deployer are deterministic steps the conductor sequences (the Calibrator
drives the TARGET agent for benign episodes).  Concurrency across cases is the harness worker
pool; the conductor owns the phase order and reporting.
"""
from __future__ import annotations

from dataclasses import dataclass

from . import backend
from .harness import Harness, summarize
from .subagent import Session

ROSTER = [
    ("Surveyor",   "SUBAGENT", "perceive: explore env -> units (skills/tools/credentials/data)"),
    ("Camoufleur", "SUBAGENT", "design env-blended covers (names/gateway prose/decoys)"),
    ("Distinguisher", "SUBAGENT", "certify-gate: try to pick the decoy out of real peers"),
    ("Calibrator", "code+agent", "benign-fit: learn delta per role-class on held-out envs"),
    ("Optimizer",  "code",     "keep all FP-clean: wrap=cut-set coverage, plant=certify-gate"),
    ("Deployer",   "code",     "apply camouflaged markers into the environment"),
    ("Logger",     "runtime",  "record commitment-touch side-effects"),
    ("Updater",    "runtime",  "online benign-fit (FP self-correction) + drift adaptation"),
]


def _log(msg: str) -> None:
    print(f"  [orchestrator] {msg}", flush=True)


def _api_distinguisher(client, model: str):
    """The certify-gate Distinguisher is a simple classifier (pick the planted item out of a
    listing).  Run it as a DIRECT API call, not a `claude` CLI subagent — one cheap HTTP round-trip
    per trial instead of a subprocess cold-start (the certify bottleneck)."""
    from .perceive import _chat
    return lambda prompt: _chat(client, model, prompt)


@dataclass
class Orchestrator:
    harness: Harness

    def roster(self) -> None:
        _log("defender roles scheduled this run:")
        for name, kind, desc in ROSTER:
            print(f"      - {name:11s} [{kind:9s}] {desc}", flush=True)

    def open_sessions_build_plans(self, cases) -> tuple[dict, set]:
        """Open the Surveyor + Camoufleur SESSIONS once per distinct env and build a cached
        Plan (units structure + camouflage covers).  This is the orchestrator's core job:
        open the subagent sessions, drive them, control the flow.

        Returns (plans, failed):
          - plans : env_key -> Plan for session-based bindings that built successfully.
          - failed: env_keys whose build_plan RAISED (flaky subagent) — these are dropped.
        A binding that legitimately returns None (non-session, e.g. capflow) is NOT failed:
        it falls back to per-case perceive and keeps all its cases."""
        b, model = self.harness.binding, self.harness.perceive_model
        reps: dict[str, object] = {}
        for c in cases:                                   # one representative case per env
            reps.setdefault(b.env_key(c), c)
        plans: dict[str, dict] = {}
        failed: set = set()
        distinguish = _api_distinguisher(self.harness.client, model)   # cheap classifier, not a CLI subagent
        for key, case in reps.items():
            with backend.isolated_env(case.attack_dir) as env:
                surveyor = Session("Surveyor", env, model, timeout=self.harness.timeout)
                camoufleur = Session("Camoufleur", env, model, timeout=self.harness.timeout)
                _log(f"opening Surveyor + Camoufleur sessions for env '{key}' (Distinguisher=API) ...")
                try:
                    plan = b.build_plan(surveyor, camoufleur, case, env, distinguish=distinguish)
                except Exception as e:                    # one flaky subagent call must not nuke the run
                    _log(f"  Plan[{key}] FAILED ({type(e).__name__}: {e}); skipping this env")
                    failed.add(key)
                    plan = None
            if plan is not None:
                plans[key] = plan
                _log(f"  Plan[{key}]: {plan.get('summary', 'built')}")
        b.set_plans(plans)
        return plans, failed

    def conduct(self, calib_cases, eval_cases) -> dict:
        """Schedule the deploy-time multi-agent plan and return metrics."""
        self.roster()
        _log("Phase 0 — PLAN: open defender sessions, build per-env Plan")
        plans, failed = self.open_sessions_build_plans(calib_cases + eval_cases)
        b = self.harness.binding
        # drop ONLY envs whose planning RAISED; non-session bindings (failed=∅) keep all cases
        # and fall back to per-case perceive.
        calib_cases = [c for c in calib_cases if b.env_key(c) not in failed]
        eval_cases = [c for c in eval_cases if b.env_key(c) not in failed]
        _log(f"Phase 1/2 — CALIBRATE on {len(calib_cases)} held-out env(s); benign-fit delta")
        deltas = self.harness.calibrate(calib_cases)
        _log(f"  learned delta_by_role = {{{', '.join(f'{k}:{v:.2f}' for k, v in deltas.items())}}}")
        _log(f"Phase 2/2 — SELECT + DEPLOY + EVALUATE on {len(eval_cases)} env(s): "
             f"keep all FP-clean (wrap cut-set / plant certify); deploy camouflaged; attack + control")
        rows = self.harness.evaluate(eval_cases, deltas)
        return {"delta_by_role": deltas, "rows": rows, "metrics": summarize(rows)}
