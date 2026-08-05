"""SCRBench baseline controls (skill unit)."""
from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from code.harness.dispatch import entry  # noqa: E402

if __name__ == "__main__":
    entry("SCRBench baseline controls",
          {"baselines": "code.harness.scr_baselines",
           "clawguard": "code.harness.scr_clawguard",
           "guardian": "code.harness.scr_guardian"})
