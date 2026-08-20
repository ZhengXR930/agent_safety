"""Apply pre-materialized SCR fused SKILL.md files to run-local workspaces."""
from __future__ import annotations

import json
from pathlib import Path


def _manifest_path(path: str | Path | None) -> Path | None:
    if not path:
        return None
    root = Path(path)
    return root if root.is_file() else root / "manifest.json"


def _load_manifest(path: str | Path | None) -> tuple[Path, dict] | None:
    manifest_path = _manifest_path(path)
    if manifest_path is None:
        return None
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    return manifest_path.parent, manifest


def load_suite(path: str | Path | None, suite: str) -> dict:
    loaded = _load_manifest(path)
    if loaded is None:
        return {}
    base, manifest = loaded
    rows = manifest.get("suites", {}).get(suite) or []
    result = {}
    for row in rows:
        case_id = row.get("case_id")
        skills = {}
        for role, skill in (row.get("skills") or {}).items():
            skill_path = base / skill["skill_md_path"]
            text = skill_path.read_text(encoding="utf-8", errors="replace")
            if len(text.strip()) < 50:
                raise ValueError(f"invalid fused SKILL.md: {skill_path}")
            skills[role] = {**skill, "skill_md": text}
        result[str(case_id)] = {**row, "skills": skills,
                                "dataset_manifest": str(base / "manifest.json")}
    if not result:
        raise ValueError(f"SCR fused skill dataset has no {suite} rows")
    return result


def _write_skill(root: Path, relative: str | Path, text: str) -> Path:
    target = root / relative
    if not target.is_file():
        raise ValueError(f"cannot overlay missing SCR skill: {target}")
    target.write_text(text, encoding="utf-8")
    return target


def overlay_capflow(skills_root: str | Path, dataset: dict, case_id: int) -> dict:
    if not dataset:
        return {}
    entry = dataset.get(str(int(case_id)))
    if entry is None:
        raise ValueError(f"missing fused CapFlow case{int(case_id):03d}")
    applied = {}
    root = Path(skills_root)
    for role, skill in entry["skills"].items():
        target = _write_skill(
            root, Path(str(skill["skill_dir"])) / "SKILL.md",
            skill["skill_md"])
        applied[role] = {
            "skill_dir": target.parent.name,
            "skill_name": skill.get("skill_name"),
            "skill_md_sha256": skill.get("skill_md_sha256"),
        }
    return {"schema": "scr-fused-skill-overlay-v1", "suite": "capflow",
            "case_id": int(case_id), "skills": applied,
            "dataset_manifest": entry.get("dataset_manifest")}


def overlay_authblur(case_root: str | Path, dataset: dict, case_id: int) -> dict:
    if not dataset:
        return {}
    entry = dataset.get(str(int(case_id)))
    if entry is None:
        raise ValueError(f"missing fused AuthBlur case{int(case_id):03d}")
    skills_root = Path(case_root) / "cli_skills" / "skills"
    applied = {}
    for role, skill in entry["skills"].items():
        target = _write_skill(
            skills_root, Path(str(skill["skill_dir"])) / "SKILL.md",
            skill["skill_md"])
        applied[role] = {
            "skill_dir": target.parent.name,
            "skill_name": skill.get("skill_name"),
            "skill_md_sha256": skill.get("skill_md_sha256"),
        }
    return {"schema": "scr-fused-skill-overlay-v1", "suite": "authblur",
            "case_id": int(case_id), "skills": applied,
            "dataset_manifest": entry.get("dataset_manifest")}


def overlay_trustlift(case_root: str | Path, dataset: dict, case_id: str) -> dict:
    if not dataset:
        return {}
    entry = dataset.get(str(case_id))
    if entry is None:
        raise ValueError(f"missing fused TrustLift case {case_id}")
    root = Path(case_root)
    mapping = {
        "secure_skill": Path("cli_skills") / "skills" / "secure-skill" / "SKILL.md",
        "registry_target": Path("registry") / "skills" / str(case_id) / "SKILL.md",
    }
    applied = {}
    for role, relative in mapping.items():
        skill = entry["skills"].get(role)
        if not skill:
            continue
        target = _write_skill(root, relative, skill["skill_md"])
        applied[role] = {
            "skill_dir": target.parent.name,
            "skill_name": skill.get("skill_name"),
            "skill_md_sha256": skill.get("skill_md_sha256"),
        }
    return {"schema": "scr-fused-skill-overlay-v1", "suite": "trustlift",
            "case_id": str(case_id), "skills": applied,
            "dataset_manifest": entry.get("dataset_manifest")}
