"""AgentDojo baseline controls (tool unit)."""
from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from code.harness.dispatch import entry  # noqa: E402

if __name__ == "__main__":
    entry("AgentDojo baseline controls",
          {"undefended": "code.harness.agentdojo_undefended",
           "melon": "code.harness.agentdojo_melon",
           "native": "code.harness.agentdojo_native",
           "matrix": "code.harness.agentdojo_matrix"})
