"""MCPTox baseline controls (MCP unit)."""
from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from code.harness.dispatch import entry  # noqa: E402

if __name__ == "__main__":
    entry("MCPTox baseline controls",
          {"mcpguard": "code.harness.mcptox_mcpguard",
           "mcpguard-probe": "code.harness.mcptox_mcpguard_probe",
           "pipelock": "code.harness.mcptox_pipelock",
           "stackone-e2e": "code.harness.mcptox_stackone_e2e"})
