"""AgentDojo (tool unit) under the active defense.

Default is the smoke evaluation; --full runs the checkpointed full evaluation."""
from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from code.harness.dispatch import entry  # noqa: E402

if __name__ == "__main__":
    entry("AgentDojo under the active defense",
          {"smoke": "code.harness.agentdojo_ours_smoke",
           "full": "code.harness.agentdojo_ours_full"},
          flag="--mode", default="smoke")
