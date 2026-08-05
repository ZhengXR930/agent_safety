"""SkillInject baseline controls (skill unit).

There is no ours entry yet: SkillInject still needs a lean adapter under
code/benchmarks/.  See code/README.md."""
from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from code.harness.dispatch import entry  # noqa: E402

if __name__ == "__main__":
    entry("SkillInject baseline controls",
          {"guards": "code.harness.skillinject_baselines"},
          flag="--defense", default="guards")
