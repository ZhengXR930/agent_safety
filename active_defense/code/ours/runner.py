"""Active Defense runner; implementation is preserved in ``ours.defense``."""
from code.core.runner import BaselineRunner

RUNNER = BaselineRunner("ours")


def runner_for(method: str) -> BaselineRunner:
    if method not in {"ours", "wrap_only", "plant_only"}:
        raise ValueError(f"unknown active-defense method: {method}")
    return BaselineRunner(method)
