"""Validated two-track selection (replaces the old eps-submodular, which experiments showed was
a no-op: benign FP does NOT grow with marker count, so the global-eps budget never binds).

Experiments settled the real optimization per primitive:

  WRAP  (off-scope affordances): adaptive-robust by UNAVOIDABILITY -> the optimization is
      CUT-SET COVERAGE: instrument EVERY off-scope affordance (no selection/budget). If one
      path is left uncovered, an adaptive attacker routes through it (probe: FULL coverage
      -> 0% evasion; PARTIAL -> 25% evasion). So we KEEP ALL FP-clean wrap markers; the real
      work (completeness of the cut-set) is the Surveyor's, not a selection budget.

  PLANT (decoy objects/data): adaptive-robust by INDISTINGUISHABILITY -> the optimization is a
      CERTIFY-GATE: keep a decoy only if a Distinguisher cannot tell it from real peers (probe:
      certify detection-rate monotonically predicts adaptive robustness). Distinguishable
      decoys are rejected (regenerated upstream by the Camoufleur).

benign-fit (delta <= tau) still drops any marker that false-positives on benign, keeping I(M)=0
by construction. There is no epsilon budget and no submodular subset selection.
"""
from __future__ import annotations

from .markers import Ladder, Marker, Placement


def benign_fit(ladder: Ladder, tau: float = 0.0) -> Marker | None:
    """Tightest FP-clean rung of a unit (max coverage with benign FP delta <= tau); else None
    (the unit is withheld because even its mildest rung false-positives on benign).

    NOTE (current reality): under the validated two-track design every unit emits a SINGLE
    full-coverage rung (wrap = the one cut on its off-scope path; plant = the one certified decoy),
    so the `max coverage` argmax is the identity and this reduces to "keep the rung iff FP-clean".
    The multi-rung data model is retained as dormant generality (graduated marker strength) for a
    possible future where a unit offers a coverage/FP trade-off; today nothing populates it."""
    clean = [m for m in ladder.rungs if m.delta <= tau]
    return max(clean, key=lambda m: m.coverage) if clean else None


def select(ladders: list[Ladder], *, tau: float = 0.0, certify=None) -> Placement:
    """Keep every FP-clean marker (wrap = full cut-set coverage); for plant markers, additionally
    require certify(marker) is True (certified indistinguishable). No epsilon, no subset budget.

    certify : optional callable(marker)->bool. A plant marker failing certification is dropped
              (the Camoufleur regenerates a more indistinguishable decoy upstream).
    """
    kept: list[Marker] = []
    for lad in ladders:
        m = benign_fit(lad, tau=tau)
        if m is None:
            continue                                   # false-positives on benign -> withhold
        if m.primitive == "plant" and certify is not None and not certify(m):
            continue                                   # distinguishable decoy -> reject
        kept.append(m)
    return Placement(markers=kept)
