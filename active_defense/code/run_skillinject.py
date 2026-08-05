"""SkillInject (skill unit, open shell) under the active defense."""
from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from code.harness.dispatch import entry  # noqa: E402

if __name__ == "__main__":
    entry("SkillInject under the active defense",
          {"ours": "code.harness.skillinject_ours"},
          flag="--mode", default="ours")
