"""MSB baseline controls and scoring (MCP unit)."""
from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from code.harness.dispatch import entry  # noqa: E402

if __name__ == "__main__":
    entry("MSB baseline controls and scoring",
          {"clean-runtime": "code.harness.msb_clean_runtime",
           "clean-fp": "code.harness.msb_clean_fp",
           "score": "code.harness.msb_score"})
