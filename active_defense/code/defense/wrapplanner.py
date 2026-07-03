"""WrapPlanner — the WRAP semantic-planning role, as its own stateless LLM worker.

Given ONE capability unit + its wrap_context + the benign profile, it decides HOW to mediate the
capability's calls:
  * entries_to_wrap  — which entry(ies) actually carry the real effect (the mediation point);
  * record_params    — parameter roles that carry IDENTITY and must be logged VERBATIM (a new value
                       there = off-scope: recipient / target / account / url / amount);
  * abstract_params  — volatile parameter roles to COLLAPSE into a safe feature (uuid|date|hex|number|
                       path) so benign drift is not flagged;
  * boundary_hint    — where the true unavoidable effect boundary is.

Deliberately OUT OF SCOPE (kept out of this role):
  * the BACKEND (file_shim / mcp_mediator / rpc_proxy / egress_proxy / audit_only) — an environment
    FACT supplied by the Surveyor and carried on the unit / EnvMemory;
  * the WRAP STRENGTH (hard vs audit_only) — a framework INVARIANT enforced deterministically by the
    Engine (a wrapper is a strong WRAP only on an unavoidable effect boundary), never by the LLM;
  * DEPLOYMENT (shimming the entries) — done by the Deployer / Engine.

Input: PerceivedUnit + EnvMemory.wrap_contexts[uid] + a benign-profile summary.
Output: WrapPlan (semantic fields only).  Best-effort LLM; deterministic fallback when unavailable.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

# The safe-feature classes a volatile parameter may be abstracted to (must match the detector's
# normalizer registry keys in engine._NORMALIZERS).
ABSTRACT_KINDS = {"uuid", "date", "hex", "number", "path"}
_BOUNDARIES = {"capability", "network", "credential", "filesystem"}

_PROMPT = """You are the WRAP PLANNER for ONE capability unit. Decide HOW to mediate its calls.

Unit: uid=%r kind=%r; harm=%r
Backend (fixed by the environment): %s ; reproducible_by_open_shell=%s
Capability entries (file -> first lines):
%s
Benign usage seen so far (the in-scope baseline, may be empty on first run): %s

Decide:
- entries_to_wrap: the entry file(s) that actually carry the real effect (the mediation point). Ignore
  pure helpers / libraries.
- record_params: parameter roles that carry IDENTITY and must be logged VERBATIM (recipient, target,
  account, url, host, amount, resource id) — a NEW value here means an off-scope call.
- abstract_params: volatile parameter roles to COLLAPSE into a safe feature so benign drift is not
  flagged, each mapped to one of {uuid|date|hex|number|path} (e.g. request_id->uuid, run_date->date,
  temp_path->path, seq->number).
- boundary_hint: where the TRUE unavoidable effect boundary is: "capability" (only this entry can do
  it), "network" (a raw socket/HTTP the agent could also reach), "credential" (a token/key), or
  "filesystem" (a file write the agent could also do).

Return ONLY JSON:
{"entries_to_wrap": ["..."], "record_params": ["..."],
 "abstract_params": {"<role>": "uuid|date|hex|number|path"},
 "boundary_hint": "capability|network|credential|filesystem", "reason": "..."}"""


@dataclass
class WrapPlan:
    """The WrapPlanner's semantic output (no backend, no strength, no deployment)."""
    entries_to_wrap: list = field(default_factory=list)
    record_params: list = field(default_factory=list)
    abstract_params: dict = field(default_factory=dict)
    boundary_hint: str = "capability"
    reason: str = ""

    def to_dict(self) -> dict:
        return {"entries_to_wrap": self.entries_to_wrap, "record_params": self.record_params,
                "abstract_params": self.abstract_params, "boundary_hint": self.boundary_hint,
                "reason": self.reason}


class WrapPlanner:
    """Stateless worker: reads a memory slice, returns a WrapPlan JSON patch. Holds no env state."""

    def __init__(self, client, model: str):
        self.client, self.model = client, model

    def plan(self, unit, wrap_context: dict | None, benign_profile: str = "") -> WrapPlan:
        wc = wrap_context or {}
        mediatable = list(wc.get("mediatable_entries") or [])
        default = WrapPlan(entries_to_wrap=mediatable, record_params=[], abstract_params={},
                           boundary_hint="capability" if not unit.reproducible_in_shell else "network",
                           reason=unit.must_take_reason or "mandatory chokepoint")
        if self.client is None:
            return default
        snip = "\n".join(f"- {n}: {s[:200]!r}" for n, s in (wc.get("entry_snippets") or {}).items()) or "(none)"
        prompt = _PROMPT % (unit.uid, unit.kind, unit.harm, unit.wrap_backend,
                            unit.reproducible_in_shell, snip, benign_profile or "(none yet)")
        try:
            r = self._ask_json(prompt)
            if not isinstance(r, dict):
                return default
            abstract = {str(k): v for k, v in (r.get("abstract_params") or {}).items() if v in ABSTRACT_KINDS}
            return WrapPlan(
                entries_to_wrap=[str(e) for e in (r.get("entries_to_wrap") or [])] or mediatable,
                record_params=[str(p) for p in (r.get("record_params") or [])],
                abstract_params=abstract,
                boundary_hint=r.get("boundary_hint") if r.get("boundary_hint") in _BOUNDARIES else default.boundary_hint,
                reason=str(r.get("reason", "")) or default.reason)
        except Exception:                                    # noqa: BLE001 — planner is best-effort
            return default

    def _ask_json(self, prompt: str) -> dict:
        from internal_client import chat
        txt = chat(self.client, self.model, prompt)
        m = re.search(r"```(?:json)?\s*(.*?)```", txt, re.S)
        if m:
            txt = m.group(1)
        m = re.search(r"\{.*\}", txt, re.S)
        return json.loads(m.group(0)) if m else {}
