#!/usr/bin/env python3
"""Validate adaptive_attack_eval benchmark_manifest.jsonl."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from build_benchmark_manifest import PROJECT_ROOT, validate


DEFAULT_MANIFEST = PROJECT_ROOT / "experiment-stage" / "adaptive_attack_eval" / "benchmark_manifest.jsonl"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    args = parser.parse_args()

    rows = []
    with args.manifest.open("r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, start=1):
            if not line.strip():
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as exc:
                print(f"line {line_no}: {exc}", file=sys.stderr)
                raise SystemExit(1) from exc
    summary = validate(rows)
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    if not summary["valid"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
