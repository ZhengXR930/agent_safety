"""Runtime Updater: keep the deployed deception layer correct as the environment and usage
drift — WITHOUT a full re-plan.

Runtime is meant to be light: a Logger (the recorder side-effect) and this Updater.  The
deploy-time Harness produces the initial Placement; the Updater then maintains it online:

  1. ONLINE BENIGN-FIT (self-correcting FP): the Logger reports touches during normal
     (benign) operation.  If a deployed marker starts false-positiving (observed benign rate
     > tau), it is withheld so I(M)=0 keeps holding as usage drifts — without re-running the
     whole pipeline.
  2. DRIFT ADAPTATION: when the env is re-surveyed, new units bring new candidate ladders
     (added if FP-clean); vanished units' markers are removed. New off-scope affordances
     extend the wrap cut-set; new sensitive items get certify-gated plant decoys.
  3. RE-SELECT after any change (incremental: re-runs the cheap keep-all-FP-clean selection
     over current candidates; perception/calibration touch only changed units).

reconcile() takes the CURRENT candidate ladders (from re-perceiving the possibly-drifted env,
each rung carrying its calibrated delta) and returns the new Placement plus the (added,
removed) diff for the Deployer to apply.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field

from .markers import Ladder, Marker, Placement
from .optimizer import select


@dataclass
class Updater:
    tau: float = 0.0
    min_obs: int = 5                                  # min benign runs before trusting live delta
    benign_runs: int = 0
    benign_touch: Counter = field(default_factory=Counter)   # marker.mid -> benign touch count
    deployed: dict[str, Marker] = field(default_factory=dict)  # mid -> currently deployed marker

    def set_placement(self, placement: Placement) -> None:
        self.deployed = {m.mid: m for m in placement.markers}

    # ---- Logger feedback ----
    def observe_benign(self, touched_mids) -> None:
        """Record one benign episode and which deployed markers it touched (should be none)."""
        self.benign_runs += 1
        for mid in touched_mids:
            self.benign_touch[mid] += 1

    def live_delta(self, mid: str) -> float:
        return (self.benign_touch[mid] / self.benign_runs) if self.benign_runs else 0.0

    # ---- incremental re-optimization ----
    def reconcile(self, ladders: list[Ladder]) -> tuple[Placement, list[Marker], list[Marker]]:
        """Fold live benign observations into each candidate's delta, then re-select (keep all
        FP-clean).  Returns (new_placement, added, removed)."""
        if self.benign_runs >= self.min_obs:
            for lad in ladders:
                for m in lad.rungs:
                    if m.mid in self.benign_touch:           # online benign-fit overrides calib
                        m.delta = max(m.delta, self.live_delta(m.mid))
        new = select(ladders, tau=self.tau)
        new_ids = {m.mid for m in new.markers}
        added = [m for m in new.markers if m.mid not in self.deployed]
        removed = [m for mid, m in self.deployed.items() if mid not in new_ids]
        self.set_placement(new)
        return new, added, removed


if __name__ == "__main__":
    # offline self-test: the placement self-corrects under FP, and adapts to drift.
    def ladders(unit_ids):
        return [Ladder(unit=None, rungs=[Marker(mid=u, unit_uid=u, primitive="wrap",
                                                coverage=1.0, delta=0.0)]) for u in unit_ids]

    up = Updater(tau=0.0, min_obs=3)
    # initial deploy: markers a, b, c all FP-clean
    p, added, removed = up.reconcile(ladders(["a", "b", "c"]))
    print("deploy:", [m.mid for m in p.markers], "| added", [m.mid for m in added])
    assert {m.mid for m in p.markers} == {"a", "b", "c"}

    # 'b' starts false-positiving during benign use -> Updater must withhold it
    for _ in range(4):
        up.observe_benign(["b"])
    p, added, removed = up.reconcile(ladders(["a", "b", "c"]))
    print("after b FP:", [m.mid for m in p.markers], "| removed", [m.mid for m in removed])
    assert "b" not in {m.mid for m in p.markers} and "b" in {m.mid for m in removed}

    # env drift: a new unit 'd' appears -> Updater adds it (FP-clean)
    p, added, removed = up.reconcile(ladders(["a", "c", "d"]))
    print("after drift +d -b:", [m.mid for m in p.markers], "| added", [m.mid for m in added])
    assert "d" in {m.mid for m in p.markers} and "d" in {m.mid for m in added}
    print("\nUpdater self-test passed: self-corrects FP, adapts to drift, holds I(M)=0.")
