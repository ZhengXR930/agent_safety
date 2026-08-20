"""Helpers for fixed SCR-CapFlow fused SKILL.md datasets."""
from __future__ import annotations

import json
import re
import shutil
from pathlib import Path


def frontmatter_value(text: str, key: str) -> str:
    match = re.search(
        rf"(?m)^{re.escape(key)}:\s*(?:\"([^\"]*)\"|'([^']*)'|([^\n]+))",
        text,
    )
    return next((part.strip() for part in match.groups() if part is not None),
                "") if match else ""


def load_capflow_skill_dataset(path: str | Path | None) -> dict[int, dict]:
    if not path:
        return {}
    root = Path(path)
    manifest_path = root if root.is_file() else root / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    base = manifest_path.parent
    entries: dict[int, dict] = {}
    for entry in manifest.get("cases") or []:
        case_id = int(entry["case_id"])
        skills = {}
        for role, row in (entry.get("skills") or {}).items():
            skill_path = base / row["skill_md_path"]
            text = skill_path.read_text(encoding="utf-8", errors="replace")
            if len(text) < 100 or not text.lstrip().startswith("---"):
                raise ValueError(f"invalid SCR fused SKILL.md: {skill_path}")
            skills[role] = {**row, "skill_md": text}
        if set(skills) != {"A", "B"}:
            raise ValueError(f"case{case_id:03d} needs fused A and B skills")
        entries[case_id] = {**entry, "skills": skills,
                            "dataset_manifest": str(manifest_path)}
    if not entries:
        raise ValueError(f"SCR fused skill dataset is empty: {manifest_path}")
    return entries


def overlay_capflow_skill_dataset(
    skills_dir: str | Path,
    dataset: dict[int, dict],
    case_id: int,
) -> dict:
    if not dataset:
        return {}
    entry = dataset.get(int(case_id))
    if not entry:
        raise ValueError(f"case{int(case_id):03d} missing from SCR skill dataset")
    root = Path(skills_dir)
    applied = {}
    for role, row in entry["skills"].items():
        skill_dir = row.get("skill_dir")
        target = root / str(skill_dir) / "SKILL.md"
        if not target.is_file():
            matches = [
                path for path in root.glob("*/SKILL.md")
                if frontmatter_value(
                    path.read_text(encoding="utf-8", errors="replace"),
                    "name") == row.get("skill_name")
            ]
            if len(matches) != 1:
                raise ValueError(
                    f"cannot resolve SCR case{case_id:03d} role {role} skill")
            target = matches[0]
        target.write_text(row["skill_md"], encoding="utf-8")
        applied[role] = {
            "skill_dir": target.parent.name,
            "skill_name": row.get("skill_name"),
            "tool": row.get("tool"),
            "skill_md_sha256": row.get("skill_md_sha256"),
        }
    return {
        "schema": "scr-capflow-fused-skill-overlay-v1",
        "dataset_manifest": entry.get("dataset_manifest"),
        "case_id": int(case_id),
        "attack_family": entry.get("attack_family"),
        "skills": applied,
        "combination_validation": entry.get("combination_validation"),
    }


def copy_capflow_skills_with_overlay(
    source: str | Path,
    destination: str | Path,
    *,
    dataset: dict[int, dict] | None = None,
    case_id: int | None = None,
) -> dict:
    destination = Path(destination)
    if destination.exists():
        shutil.rmtree(destination)
    shutil.copytree(source, destination)
    if dataset and case_id is not None:
        return overlay_capflow_skill_dataset(destination, dataset, case_id)
    return {}
