#!/usr/bin/env python3
"""CLI wrapper for the centralized trusted MSB case manifest."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from code.manifest.msb import build


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--msb-root", type=Path, required=True)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    manifest = build(args.msb_root.resolve(), args.config.resolve())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.output.with_suffix(args.output.suffix + ".tmp")
    temporary.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")
    temporary.replace(args.output)
    print(json.dumps({"output": str(args.output),
                      "case_count": manifest["case_count"]}))


if __name__ == "__main__":
    main()
