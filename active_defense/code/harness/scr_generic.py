"""Run the generic environment-discovered Skill substrate."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from code.benchmarks.scr import SkillRuntime


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--skills-dir", required=True)
    parser.add_argument("--capability-manifest", required=True,
                        help="operator-attested JSON list with explicit effect/observation facts")
    parser.add_argument("--turn", action="append", required=True,
                        help="original trusted user turn; repeat to preserve interaction boundaries")
    parser.add_argument("--model", default="gpt-5.5-2026-04-24")
    parser.add_argument("--no-plant", action="store_true")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    capability_manifest = json.loads(
        Path(args.capability_manifest).read_text(encoding="utf-8"))
    result = SkillRuntime(args.skills_dir, args.model, capability_manifest).run(
        args.turn, plant=not args.no_plant)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({"output": str(output), "turns": len(args.turn)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
