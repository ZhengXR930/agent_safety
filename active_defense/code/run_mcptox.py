"""MCPTox (MCP unit) under the active defense.

The ours MCP path evaluates the paired MCPTox and MSB sample in one pass, so
this entry and run_msb.py drive the same evaluation."""
from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from code.harness.dispatch import entry  # noqa: E402

if __name__ == "__main__":
    entry("MCPTox under the active defense",
          {"ours": "code.harness.mcp_ours"}, flag="--mode", default="ours")
