"""EnvMemory — the environment-knowledge layer (single source of truth about a target env).

Built ONCE by the Surveyor during perception, then queried by every downstream component instead of
re-deriving / re-stuffing context per call:
  * Camoufleur   — designs decoys consistent with this env's naming/provenance.
  * Distinguisher — judges a candidate decoy against THIS env's conventions (memory-backed, faithful).
  * Detection    — knows which deployed markers to look for in the produced effect state.

Persisted to <env>/sandbox/.defense_memory.md (Everything-is-Markdown), so a Session-style agent can
also read it directly; in-process components read the object.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

# Two PRIMITIVES (the per-unit method / unavoidability source) — Discussion §3, Formal §4-5:
PRIMITIVES = {"plant", "wrap"}
# PLANT placement forms (a sub-choice WITHIN plant: HOW to make the plant must-take). NOT primitives.
PLANT_PLACEMENTS = {"sweep", "exfil", "reference", "basis"}


@dataclass
class PerceivedUnit:
    """A unit the Surveyor perceived, with its autonomously-chosen PRIMITIVE (plant|wrap) and — for
    plant — the placement form that makes the decoy must-take."""
    uid: str
    kind: str                         # datum|credential|authorization|skill|tool|service|...
    harm: str = ""                    # what misuse of this unit looks like
    primitive: str = "plant"          # plant | wrap  (the method = unavoidability source)
    placement: str = "exfil"          # plant only: sweep|exfil|reference|basis (must-take form)
    carrier_file: str = ""            # env-relative file where the unit/decoy lives (injection point)
    real_value: str = ""              # the genuine id/value the decoy mimics (for design)
    real_detail: str = ""             # genuine detail/role (for design)
    peers: list = field(default_factory=list)   # sibling real items, for certify-gate
    reproducible_in_shell: bool = True          # False => substrate-enforced (mcp) => wrap is sound

    def to_dict(self) -> dict:
        return {"uid": self.uid, "kind": self.kind, "harm": self.harm, "primitive": self.primitive,
                "placement": self.placement, "carrier_file": self.carrier_file,
                "real_value": self.real_value, "real_detail": self.real_detail, "peers": self.peers,
                "reproducible_in_shell": self.reproducible_in_shell}


@dataclass
class EnvMemory:
    """Everything we know about one target environment."""
    env_key: str = ""
    domain: str = ""
    conventions: str = ""             # naming / id-format / provenance notes (for the Distinguisher)
    landscape: list = field(default_factory=list)   # raw inventory the Surveyor saw [{id, detail, ...}]
    units: list = field(default_factory=list)       # list[PerceivedUnit]

    # ---- the context the Distinguisher / Camoufleur read (memory-backed, not re-stuffed) ----
    def context(self) -> str:
        lines = [f"Environment domain: {self.domain or '?'}.",
                 f"Naming / provenance conventions: {self.conventions or '(none noted)'}",
                 "Known items in this environment (the authentic provenance to judge against):"]
        for it in self.landscape[:40]:
            lines.append(f"- id={it.get('id','?')} | {it.get('detail','')}")
        return "\n".join(lines)

    def to_dict(self) -> dict:
        return {"env_key": self.env_key, "domain": self.domain, "conventions": self.conventions,
                "landscape": self.landscape, "units": [u.to_dict() for u in self.units]}

    def save(self, env_dir: Path) -> Path:
        sb = Path(env_dir) / "sandbox"; sb.mkdir(parents=True, exist_ok=True)
        p = sb / ".defense_memory.md"
        body = ["# Defense EnvMemory", "", f"- env: {self.env_key}", f"- domain: {self.domain}",
                f"- conventions: {self.conventions}", "", "## Units", ""]
        for u in self.units:
            form = u.placement if u.primitive == "plant" else "—"
            body.append(f"- **{u.uid}** ({u.kind}) → `{u.primitive}`/{form} @ `{u.carrier_file}`; "
                        f"harm: {u.harm}")
        body += ["", "## Landscape", "", "```json", json.dumps(self.landscape, indent=2,
                                                               ensure_ascii=False), "```"]
        p.write_text("\n".join(body), encoding="utf-8")
        return p

    @classmethod
    def from_units(cls, env_key: str, domain: str, conventions: str,
                   landscape: list, units: list) -> "EnvMemory":
        return cls(env_key=env_key, domain=domain, conventions=conventions,
                   landscape=landscape, units=units)
