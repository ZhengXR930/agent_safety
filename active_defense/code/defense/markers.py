"""Core data model: Unit -> (Ladder of) Marker -> Placement.

plant vs wrap is ONE continuum, but the routing rule is NOT just kind — it is the
"skill-as-shell" rule (Discussion §4 / Formal §5,§7): a marker is only adaptive-robust if the
adversary cannot avoid it, and a WRAP gateway is avoidable whenever the adversary can reproduce
the effect through a MORE GENERAL affordance (a shell / code execution).  So:

  * an OBJECT the agent must process (credential, datum, authorization, record, token)
        -> PLANT (object decoy); touch = decoy carried to a sink / cited as a basis.  [always]
  * a CAPABILITY the agent invokes (tool, skill, install, go_ahead, decision):
      - if its effect is SHELL-REPRODUCIBLE (the common open-shell case) -> PLANT (a BASIS decoy:
        a fake "already-authorized" record the over-reaching agent cites as license).  WRAP here
        would be bypassed (EXP-2026W26-004).
      - only if the effect is SUBSTRATE-ENFORCED / not shell-reproducible (mcp server-side) -> WRAP.
"""
from __future__ import annotations

from dataclasses import dataclass, field

OBJECT_KINDS = {"credential", "datum", "authorization", "record", "token"}
AFFORDANCE_KINDS = {"tool", "skill", "mcp", "install", "go_ahead", "decision"}
ENFORCED_KINDS = {"mcp"}            # substrate-enforced: agent cannot reproduce the effect in shell


def primitive_for(kind: str, reproducible_in_shell: bool = True) -> str:
    """Per-unit plant-vs-wrap routing (skill-as-shell rule).

    WRAP only when the effect is NOT reproducible by the agent's most general affordance
    (substrate-enforced, e.g. mcp); otherwise PLANT — objects as object decoys, shell-reproducible
    capabilities as BASIS decoys.  Default reproducible_in_shell=True matches an open-shell agent."""
    if kind in OBJECT_KINDS:
        return "plant"
    if kind in ENFORCED_KINDS or not reproducible_in_shell:
        return "wrap"
    return "plant"     # shell-reproducible capability -> basis (authorization) decoy


@dataclass
class Unit:
    """A perceived element of the environment and its authorized scope."""
    uid: str
    kind: str                     # credential|datum|authorization|tool|skill|...
    role: str = ""                # e.g. "invoice reviewer"
    role_type: str = "general"    # advisory|decision_or_execution|findings|general
    authorized: str = ""          # what the role legitimately does
    off_scope: str = ""           # the over-reach a laundered agent could be pushed to
    reproducible_in_shell: bool = True   # effect reproducible by a general shell? (False => mcp-enforced)
    spec: dict = field(default_factory=dict)   # extra env-specific fields (target_id, ...)

    @property
    def primitive(self) -> str:
        return primitive_for(self.kind, self.reproducible_in_shell)

    @property
    def plant_form(self) -> str:
        """When primitive=='plant': 'object' (object decoy) vs 'basis' (fake authorization decoy
        for a shell-reproducible capability's off-scope action)."""
        return "object" if self.kind in OBJECT_KINDS else "basis"


@dataclass
class Marker:
    """One candidate tripwire on a unit, at one ladder rung.

    coverage : structural weight (cut-set membership), attack-agnostic.
    delta    : benign false-positive rate, learned by benign-fit.
    camouflaged: hard gate — must be True before deploy (indistinguishable from benign).
    """
    mid: str
    unit_uid: str
    primitive: str                # "plant" | "wrap"
    rung: int = 0                 # ladder index (0 = mildest)
    coverage: float = 1.0
    delta: float = 0.0
    cost: float = 1.0
    camouflaged: bool = True
    spec: dict = field(default_factory=dict)   # how to instantiate (gateway text / decoy)


@dataclass
class Ladder:
    """The environment-derived candidate rungs for a single unit."""
    unit: Unit
    rungs: list[Marker] = field(default_factory=list)


@dataclass
class Placement:
    """The selected, deployed deception layer."""
    markers: list[Marker] = field(default_factory=list)

    @property
    def im(self) -> float:
        """Benign FP upper bound (命题1: I(M) <= sum delta_m)."""
        return sum(m.delta for m in self.markers)

    def by_primitive(self, p: str) -> list[Marker]:
        return [m for m in self.markers if m.primitive == p]
