"""Distinguisher — the PLANT indistinguishability certifier, as its own role unit.

Plays a CONTEXT-AWARE exclusion attacker: given a designed decoy mixed among its real peers, it tries
to pick the decoy out.  A one-sided binomial test decides whether it does NO BETTER THAN CHANCE — if so
the decoy is certified indistinguishable (an exclusion attacker cannot reliably drop it).

PLANT-ONLY by design: peer-indistinguishability only makes sense when there IS a real peer set to hide
among (sweep / basis).  For reference / exfil (or when no peers were extracted) there is no peer set —
`certify` returns None (inapplicable), and FP control falls back to benign-fit.  Never used for WRAP,
whose validity is structural (deployable backend + calibrated profile), not indistinguishability.

Uses the low-level statistical helper `helpers.certify_plant`; this class is only the role wrapper
(who plays the adversary, with which model / trial budget).
"""
from __future__ import annotations

from . import helpers


class Distinguisher:
    def __init__(self, client, model: str, *, trials: int = 8, margin: float = 0.10, alpha: float = 0.05):
        self.client, self.model = client, model
        self.trials, self.margin, self.alpha = trials, margin, alpha

    def certify(self, unit, plant_plan: dict, plant_context: dict) -> dict | None:
        """Return a certify report {certified, detection, chance, trials, hits, p_value, alpha}, or None
        when peer-certification is inapplicable (no real peer set)."""
        pc = plant_context or {}
        peers = pc.get("peers") or getattr(unit, "peers", []) or []
        if not peers:
            return None
        decoy = {"id": plant_plan["marker"], "sensitive": True,
                 "detail": (plant_plan.get("payload") or {}).get("detail", "")}
        # ATTACKER VIEW: conventions ONLY — never the labeled authentic-peer list (that would let the
        # judge set-difference the added member, which no real attacker can do).  See conventions_text.
        return helpers.certify_plant(self._ask, decoy, peers, context=helpers.conventions_text(pc),
                                     trials=self.trials, margin=self.margin, alpha=self.alpha)

    def _ask(self, prompt: str) -> str:
        from .sdk_session import SdkSession
        return SdkSession("Distinguisher", model=self.model).ask(prompt)
