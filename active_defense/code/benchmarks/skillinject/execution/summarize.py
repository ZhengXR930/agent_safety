"""Validate and summarize one complete SkillInject result directory."""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def _load(directory: Path, condition: str) -> list[tuple[Path, dict]]:
    records = []
    for path in sorted(directory.glob(f"*_{condition}.json")):
        record = json.loads(path.read_text(encoding="utf-8"))
        if record.get("condition") != condition:
            raise ValueError(f"{path}: condition does not match filename")
        records.append((path, record))
    return records


def _configuration(record: dict) -> dict:
    audit = record.get("audit") or {}
    return audit.get("configuration") or audit.get("ablation") or {}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("directory")
    parser.add_argument("--expected", type=int, default=180)
    parser.add_argument("--wrap-enabled", choices=("true", "false"),
                        required=True)
    parser.add_argument("--plant-enabled", choices=("true", "false"),
                        required=True)
    args = parser.parse_args()

    directory = Path(args.directory)
    clean = _load(directory, "clean")
    attack = _load(directory, "attack")
    if len(clean) != args.expected or len(attack) != args.expected:
        raise ValueError(
            f"incomplete coverage: clean={len(clean)}, attack={len(attack)}, "
            f"expected={args.expected}")

    expected_configuration = {
        "wrap_enabled": args.wrap_enabled == "true",
        "plant_enabled": args.plant_enabled == "true",
    }
    technical = []
    for path, record in clean + attack:
        if _configuration(record) != expected_configuration:
            raise ValueError(f"{path}: unexpected ablation configuration")
        if not isinstance(record.get("utility"), bool):
            technical.append(str(path))
        if record.get("condition") == "attack" and not isinstance(
                record.get("attack_effect"), bool):
            technical.append(str(path))
    if technical:
        raise ValueError("non-boolean result(s): " + ", ".join(technical))

    bu = sum(record["utility"] for _path, record in clean)
    au = sum(record["utility"] for _path, record in attack)
    asr = sum(record["attack_effect"] for _path, record in attack)
    total = args.expected
    summary = {
        "schema": "ablation-summary-v1",
        "benchmark": "skillinject",
        "input": str(directory),
        "metrics": {
            "BU": {"successes": bu, "n": total, "rate": bu / total},
            "AU": {"successes": au, "n": total, "rate": au / total},
            "ASR": {"successes": asr, "n": total, "rate": asr / total},
        },
        "technical_failures": 0,
        "coverage": {"clean": len(clean), "attack": len(attack)},
    }
    target = directory / "summary.json"
    pending = target.with_suffix(".json.tmp")
    pending.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    pending.replace(target)
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    main()
