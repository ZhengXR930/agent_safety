"""MSB (MCP unit) under the active defense.

Shares the ours MCP path with run_mcptox.py: one pass covers the paired sample."""
from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from code.harness.dispatch import entry  # noqa: E402

if __name__ == "__main__":
    entry("MSB under the active defense",
          {"ours": "code.harness.mcp_ours"}, flag="--mode", default="ours")
