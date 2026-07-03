"""EnvMemory — the shared BLACKBOARD for one target environment (single source of truth).

Every defender role reads a SLICE of this object and writes its result back; no role keeps a private
context of its own.  The flow that fills it:

  Surveyor   -> units (coarse: what / where / backend), domain, conventions, landscape.
  Enricher   -> per-unit context: plant_contexts[uid] / wrap_contexts[uid] (deep read of the carrier).
  Camoufleur -> plant_plans[uid]      (PLANT decoy design; reads plant_contexts[uid]).
  Distinguisher -> certify_reports[uid] (PLANT indistinguishability certification).
  WrapPlanner-> wrap_plans[uid]        (WRAP wrapping plan; reads wrap_contexts[uid] + benign-fit).
  TaskAllowance -> TaskContract         (per user task; authorized entries/actions + targets/sinks — WRAP).
  Deployer   -> deploy_records         (deployed(hard) / audit_only / skipped / failed).
  Detector   -> touch_events           (commitment/access touches observed at runtime).
  Updater    -> benign_profiles / runtime_updates (online benign-fit + drift).

Persisted (Everything-is-Markdown) to `<runtime_store>/defense_memory_<env_key>.md` by
`Engine.run_env` when a runtime store is configured, so the deployed layer + touches + plans are
inspectable across runs; in-process components read the object directly.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

# Two PRIMITIVES (the per-unit method / unavoidability source) — Discussion §3, Formal §4-5:
PRIMITIVES = {"plant", "wrap"}
# PLANT placement forms (a sub-choice WITHIN plant: HOW to make the plant must-take). NOT primitives.
PLANT_PLACEMENTS = {"sweep", "exfil", "reference", "basis"}
# WRAP backends (HOW the chokepoint is placed / the deploy mechanism). audit_only = record-only fallback.
# agentdojo = a function-call runtime chokepoint (in-process tool boundary; deploy/record handled by the
# AgentDojo execution backend, not a file/MCP shim).
WRAP_BACKENDS = {"file_shim", "mcp_mediator", "rpc_proxy", "egress_proxy", "audit_only", "agentdojo"}

# unit KIND vocabulary — WHAT the unit IS.  ORTHOGONAL to wrap_backend (HOW it is wrapped): an mcp_tool
# is still a "tool"; what triggers the MCP recorder (mcp_mediator.py) is wrap_backend==mcp_mediator, not
# kind.  OBJECT kinds go to PLANT; CAPABILITY kinds go to WRAP (or PLANT if shell-reproducible).
OBJECT_KINDS = {"datum", "credential", "authorization", "record", "token"}
CAPABILITY_KINDS = {"skill", "local_tool", "mcp_tool"}


def normalize_kind(kind: str, wrap_backend: str = "file_shim") -> str:
    """Canonicalize a Surveyor-supplied kind into the clear vocabulary.  Fuzzy capability labels
    ('tool' / 'service') are disambiguated by the backend (mcp_mediator -> mcp_tool, else local_tool);
    known kinds pass through unchanged.  This does NOT couple kind to backend — it only cleans up
    ambiguous WHAT labels; the backend independently decides HOW to wrap."""
    k = (kind or "datum").strip().lower()
    if k in OBJECT_KINDS or k in CAPABILITY_KINDS:
        return k
    if k in {"tool", "service", "capability", "function"}:
        return "mcp_tool" if wrap_backend == "mcp_mediator" else "local_tool"
    return k or "datum"


@dataclass
class PerceivedUnit:
    """A unit the Surveyor perceived: coarse WHAT / WHERE / BACKEND only.

    The Surveyor fills the first block; the enriched block (real_value / real_detail / peers /
    conventions) is left to the Enricher's deep read of the carrier — the Surveyor MAY seed them but
    is not required to."""
    uid: str
    primitive: str = "plant"          # plant | wrap  (the method = unavoidability source)
    placement: str = "exfil"          # plant only: sweep|exfil|reference|basis (must-take form)
    wrap_backend: str = "file_shim"   # wrap only: file_shim|mcp_mediator|rpc_proxy|egress_proxy|audit_only
    carrier_file: str = ""            # env-relative file/dir where the unit/decoy lives (injection point)
    must_take_reason: str = ""        # WHY the attacker cannot avoid this element (unavoidability)
    harm: str = ""                    # what misuse of this unit looks like
    kind: str = "datum"               # WHAT it is (OBJECT_KINDS | CAPABILITY_KINDS); ⟂ wrap_backend (HOW)
    # ---- enriched (optional; filled by Enricher, or seeded by Surveyor) ----
    real_value: str = ""              # the genuine id/value the decoy mimics (for design)
    real_detail: str = ""             # genuine detail/role (for design)
    peers: list = field(default_factory=list)   # sibling real items, for the certify-gate
    conventions: str = ""             # id-format / naming inferred for THIS unit's carrier
    reproducible_in_shell: bool = True          # False => substrate-enforced (mcp) => wrap is sound
    hard_detect: bool = True          # True => off-scope crossing is a violation; False => audit-only
    mcp_tools: list = field(default_factory=list)   # wrap:mcp_mediator — [{name,description,params}] tool schema

    def to_dict(self) -> dict:
        return {"uid": self.uid, "primitive": self.primitive, "placement": self.placement,
                "wrap_backend": self.wrap_backend, "carrier_file": self.carrier_file,
                "must_take_reason": self.must_take_reason, "harm": self.harm, "kind": self.kind,
                "real_value": self.real_value, "real_detail": self.real_detail, "peers": self.peers,
                "conventions": self.conventions, "reproducible_in_shell": self.reproducible_in_shell,
                "hard_detect": self.hard_detect, "mcp_tools": self.mcp_tools}


@dataclass
class EnvMemory:
    """The shared blackboard: everything we know / decide / observe about one target environment."""
    env_key: str = ""
    scope_id: str = ""                # the role/workflow this env's benign-fit calibrates (WRAP hard scope)
    domain: str = ""
    conventions: str = ""             # global naming / id-format / provenance notes
    landscape: list = field(default_factory=list)   # raw inventory the Surveyor saw [{id, detail, ...}]
    units: list = field(default_factory=list)       # list[PerceivedUnit]
    # ---- per-unit context (Enricher output; the SLICE each stateless role reads) ----
    unit_contexts: dict = field(default_factory=dict)    # uid -> free-form context notes
    plant_contexts: dict = field(default_factory=dict)   # uid -> {carrier_*, peers, real_*, conventions}
    wrap_contexts: dict = field(default_factory=dict)     # uid -> {wrap_backend, entry_*, mediatable, ...}
    # ---- role decisions ----
    plant_plans: dict = field(default_factory=dict)      # uid -> Camoufleur decoy plan
    wrap_plans: dict = field(default_factory=dict)        # uid -> WrapPlanner wrapping plan
    certify_reports: dict = field(default_factory=dict)   # uid -> Distinguisher certify report
    # ---- deploy + runtime ----
    deploy_records: list = field(default_factory=list)   # [{uid, primitive, status, reason, artifacts}]
    touch_events: list = field(default_factory=list)     # [{uid, primitive, channel, timing, via, ...}]
    benign_profiles: dict = field(default_factory=dict)  # scope_id -> {benign_argv, runs, ...}
    runtime_updates: list = field(default_factory=list)  # [{event, uid, ...}] online benign-fit / drift log

    # ---- blackboard writers (roles write back here, they do not keep private state) ----
    def note_plant_context(self, uid: str, ctx: dict) -> None:
        self.plant_contexts[uid] = ctx

    def note_wrap_context(self, uid: str, ctx: dict) -> None:
        self.wrap_contexts[uid] = ctx

    def note_plant_plan(self, uid: str, plan: dict) -> None:
        self.plant_plans[uid] = plan

    def note_wrap_plan(self, uid: str, plan: dict) -> None:
        self.wrap_plans[uid] = plan

    def note_certify(self, uid: str, report: dict) -> None:
        if report:
            self.certify_reports[uid] = report

    def note_deploy(self, records) -> None:
        self.deploy_records = [r if isinstance(r, dict) else r.to_dict() for r in records]

    def note_touches(self, events) -> None:
        self.touch_events = list(events)

    def note_runtime(self, entry: dict) -> None:
        self.runtime_updates.append(entry)

    # ---- context SLICES the stateless roles read ----
    def _header(self) -> list[str]:
        return [f"Environment domain: {self.domain or '?'}.",
                f"Naming / provenance conventions: {self.conventions or '(none noted)'}"]

    def context(self) -> str:
        """The global env provenance (landscape) — the authenticity backdrop for the Distinguisher."""
        lines = self._header() + ["Known items in this environment (authentic provenance to judge against):"]
        for it in self.landscape[:40]:
            lines.append(f"- id={it.get('id', '?')} | {it.get('detail', '')}")
        return "\n".join(lines)

    def plant_context_text(self, uid: str) -> str:
        """The SLICE the Camoufleur / Distinguisher read for one PLANT unit (peers to blend among)."""
        pc = self.plant_contexts.get(uid, {})
        lines = [f"Environment domain: {self.domain or '?'}.",
                 f"Conventions: {pc.get('inferred_conventions') or self.conventions or '(none noted)'}",
                 f"Carrier: {pc.get('carrier_file', '?')} ({pc.get('carrier_format', '?')})",
                 "Authentic peer items the decoy must blend among (do not copy verbatim):"]
        for it in (pc.get("peers") or [])[:40]:
            lines.append(f"- id={it.get('id', '?')} | {it.get('detail', '')}")
        return "\n".join(lines)

    def to_dict(self) -> dict:
        return {"env_key": self.env_key, "scope_id": self.scope_id, "domain": self.domain,
                "conventions": self.conventions, "landscape": self.landscape,
                "units": [u.to_dict() for u in self.units],
                "unit_contexts": self.unit_contexts, "plant_contexts": self.plant_contexts,
                "wrap_contexts": self.wrap_contexts, "plant_plans": self.plant_plans,
                "wrap_plans": self.wrap_plans, "certify_reports": self.certify_reports,
                "deploy_records": self.deploy_records, "touch_events": self.touch_events,
                "benign_profiles": self.benign_profiles, "runtime_updates": self.runtime_updates}

    def save(self, out_dir: Path) -> Path:
        """Persist the blackboard as Markdown to `out_dir/defense_memory_<env_key>.md` (per-env keyed, so
        a sweep over many envs does not collide). Called by Engine.run_env when a runtime store is set."""
        d = Path(out_dir); d.mkdir(parents=True, exist_ok=True)
        p = d / f"defense_memory_{self.env_key or 'env'}.md"
        body = ["# Defense EnvMemory", "", f"- env: {self.env_key}", f"- scope: {self.scope_id}",
                f"- domain: {self.domain}", f"- conventions: {self.conventions}", "", "## Units", ""]
        for u in self.units:
            form = u.placement if u.primitive == "plant" else f"backend={u.wrap_backend}"
            body.append(f"- **{u.uid}** ({u.kind}) → `{u.primitive}`/{form} @ `{u.carrier_file}`; "
                        f"harm: {u.harm}")
        if self.wrap_plans:
            body += ["", "## WRAP plans", ""]
            for uid, pl in self.wrap_plans.items():
                body.append(f"- **{uid}** → backend=`{pl.get('wrap_backend')}` "
                            f"detect={pl.get('detect_mode')}; {pl.get('reason', '')}")
        if self.deploy_records:
            body += ["", "## Deploy records", ""]
            for r in self.deploy_records:
                body.append(f"- **{r.get('uid')}** ({r.get('primitive')}) → `{r.get('status')}`; "
                            f"{r.get('reason', '')}")
        if self.certify_reports:
            body += ["", "## Certify reports", "", "```json",
                     json.dumps(self.certify_reports, indent=2, ensure_ascii=False), "```"]
        body += ["", "## Landscape", "", "```json",
                 json.dumps(self.landscape, indent=2, ensure_ascii=False), "```"]
        p.write_text("\n".join(body), encoding="utf-8")
        return p

    @classmethod
    def from_units(cls, env_key: str, domain: str, conventions: str,
                   landscape: list, units: list, scope_id: str = "") -> "EnvMemory":
        return cls(env_key=env_key, scope_id=scope_id, domain=domain, conventions=conventions,
                   landscape=landscape, units=units)
