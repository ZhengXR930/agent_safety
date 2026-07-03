"""Runtime Updater: keep the deployed deception layer correct as the environment and usage drift —
WITHOUT a full re-plan.  Operates on the new Engine's `Decoy` model (duck-typed: needs `.uid`).

Runtime is meant to be light: a Logger (the recording shim / snapshot side-effect) and this Updater.
The deploy-time Engine (perceive -> design -> calibrate) produces the initial deployed set; the Updater
then maintains it online:

  1. ONLINE BENIGN-FIT (self-correcting FP): the Logger reports which decoys were touched during normal
     (benign) operation. If a deployed decoy STARTS false-positiving as usage drifts (live benign touch
     rate > tau over >= min_obs runs), it is withheld so I(M)=0 keeps holding — without re-running the
     whole pipeline.
  2. DRIFT ADAPTATION: when the env is re-perceived, new units bring new candidate decoys (added if
     FP-clean); vanished units' decoys are removed.
  3. RE-SELECT after any change: the cheap keep-all-FP-clean selection over the current candidates.

reconcile() takes the CURRENT candidate decoys and returns (kept, added, removed) for the Deployer.
Engine.runtime_observe() / Engine.runtime_drift() drive it (see engine.py).
"""
from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Updater:
    tau: float = 0.0                                    # allowed benign touch rate (0 => any FP withholds)
    min_obs: int = 3                                    # min benign runs before trusting the live rate
    scope_id: str = "default"                          # the role/workflow this baseline belongs to
    benign_runs: int = 0
    benign_touch: Counter = field(default_factory=Counter)   # uid -> benign touch count
    benign_argv: dict = field(default_factory=dict)         # uid -> set(normalized argv tokens) = WRAP envelope
    noisy: set = field(default_factory=set)                  # uids withheld for live false-positiving
    deployed: dict = field(default_factory=dict)             # uid -> Decoy currently deployed (transient)

    def set_deployed(self, decoys) -> None:
        self.deployed = {d.uid: d for d in decoys}

    # ---- Logger feedback ----
    def observe_benign(self, touched_uids, argv_by_uid: dict | None = None) -> None:
        """Record one benign episode: which deployed decoys it touched (should be none) and the WRAP argv
        it legitimately used (extends the in-scope envelope)."""
        self.benign_runs += 1
        for uid in touched_uids:
            self.benign_touch[uid] += 1
        for uid, toks in (argv_by_uid or {}).items():
            self.benign_argv.setdefault(uid, set()).update(toks)

    def live_delta(self, uid: str) -> float:
        return (self.benign_touch[uid] / self.benign_runs) if self.benign_runs else 0.0

    # ---- persistence (survive process restarts; keyed by scope_id) ----
    def to_state(self) -> dict:
        return {"scope_id": self.scope_id, "benign_runs": self.benign_runs,
                "benign_touch": dict(self.benign_touch),
                "benign_argv": {u: sorted(t) for u, t in self.benign_argv.items()},
                "noisy": sorted(self.noisy)}

    def load_state(self, d: dict) -> None:
        self.scope_id = d.get("scope_id", self.scope_id)
        self.benign_runs = d.get("benign_runs", 0)
        self.benign_touch = Counter(d.get("benign_touch", {}))
        self.benign_argv = {u: set(t) for u, t in d.get("benign_argv", {}).items()}
        self.noisy = set(d.get("noisy", []))

    @staticmethod
    def _path(store_dir, scope_id) -> Path:
        return Path(store_dir) / f"benignfit_{scope_id}.json"

    def save(self, store_dir) -> None:
        p = self._path(store_dir, self.scope_id); p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(self.to_state(), ensure_ascii=False, indent=2), encoding="utf-8")

    @classmethod
    def load(cls, store_dir, scope_id: str, **kw) -> "Updater":
        up = cls(scope_id=scope_id, **kw)
        p = cls._path(store_dir, scope_id)
        if p.exists():
            try:
                up.load_state(json.loads(p.read_text(encoding="utf-8")))
            except (json.JSONDecodeError, OSError):
                pass
        return up

    def has_profile(self) -> bool:
        """True iff this scope has a calibrated benign baseline -> WRAP hard verdict is valid (else audit-only)."""
        return self.benign_runs >= self.min_obs

    # ---- incremental re-selection ----
    def reconcile(self, candidates) -> tuple[list, list, list]:
        """Keep every candidate that is FP-clean under LIVE benign observation; withhold any whose live
        benign touch rate exceeds tau (online benign-fit). Returns (kept, added, removed) vs deployed."""
        keep = {}
        for d in candidates:
            if self.benign_runs >= self.min_obs and self.live_delta(d.uid) > self.tau:
                self.noisy.add(d.uid)                   # record: withheld for live false-positiving
                continue                                # (holds I(M)=0 as usage drifts)
            keep[d.uid] = d
        kept = list(keep.values())
        added = [d for uid, d in keep.items() if uid not in self.deployed]
        removed = [d for uid, d in self.deployed.items() if uid not in keep]
        self.set_deployed(kept)
        return kept, added, removed


if __name__ == "__main__":
    # offline self-test: the deployed set self-corrects under FP and adapts to drift (Decoy-shaped stub).
    from dataclasses import dataclass as _dc

    @_dc
    class _D:
        uid: str

    def decoys(uids):
        return [_D(u) for u in uids]

    up = Updater(tau=0.0, min_obs=3)
    kept, added, removed = up.reconcile(decoys(["a", "b", "c"]))          # initial deploy
    assert {d.uid for d in kept} == {"a", "b", "c"} and len(added) == 3
    print("deploy:", [d.uid for d in kept])

    for _ in range(4):                                                     # 'b' starts false-positiving
        up.observe_benign(["b"])
    kept, added, removed = up.reconcile(decoys(["a", "b", "c"]))
    assert "b" not in {d.uid for d in kept} and "b" in {d.uid for d in removed}
    print("after b FP:", [d.uid for d in kept], "| removed", [d.uid for d in removed])

    kept, added, removed = up.reconcile(decoys(["a", "c", "d"]))          # drift: 'd' appears, 'b' gone
    assert "d" in {d.uid for d in kept} and "d" in {d.uid for d in added}
    print("after drift +d:", [d.uid for d in kept], "| added", [d.uid for d in added])
    print("\nUpdater self-test passed: online benign-fit withholds FP, adapts to drift, holds I(M)=0.")
