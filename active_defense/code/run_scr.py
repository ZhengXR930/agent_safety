"""SCRBench (skill unit) under the active defense, by suite."""
from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from code.harness.dispatch import entry  # noqa: E402

if __name__ == "__main__":
    entry("SCRBench under the active defense",
          {"capflow": "code.harness.scr_capflow",
           "authblur": "code.harness.scr_authblur",
           "trustlift": "code.harness.scr_trustlift",
           "generic": "code.harness.scr_generic"},
          flag="--suite")
