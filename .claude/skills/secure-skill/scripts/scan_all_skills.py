#!/usr/bin/env python3
"""
scan_all_skills.py - Comprehensive security scan of ALL skills under the project.

Scans all project & registry skills, then all benchmark skills from:
  - SCR-AuthBlur cases
  - SCR-TrustLift experiment
  - SCR-CapFlow cases
  - Experiment run _attack / _control skills
  - SCR-Transition

Generates a consolidated markdown report.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

# Import the core scanning logic from scan_skills.py
sys.path.insert(0, str(Path(__file__).parent))
from scan_skills import scan_skill, SkillScanResult, generate_markdown_report, print_summary


PROJECT_ROOT = Path("/Users/bytedance/Downloads/code_zxr/agent_safety")


def find_skill_dirs() -> dict[str, list[str]]:
    """Return dict of group_name -> list of skill_dir paths."""
    groups = {}

    # 1. Project core skills
    core_skills = [
        str(p) for p in (PROJECT_ROOT / ".claude" / "skills").iterdir()
        if p.is_dir() and not p.name.startswith(".") and p.name != "secure-skill"
    ]
    if core_skills:
        groups["project-core"] = core_skills

    # 2. Registry skills
    for registry_type in ["skills", "other"]:
        reg_dir = PROJECT_ROOT / "registry" / registry_type
        if reg_dir.exists():
            skills = [str(p) for p in reg_dir.iterdir() if p.is_dir()]
            if skills:
                groups[f"registry-{registry_type}"] = skills

    # 3. .trae skills
    trae_skills = [
        str(p) for p in (PROJECT_ROOT / ".trae" / "skills").iterdir()
        if p.is_dir() and not p.name.startswith(".")
    ]
    if trae_skills:
        groups["trae"] = trae_skills

    # 4. SCR-AuthBlur benchmark skills
    authblur_skills = []
    base = PROJECT_ROOT / "benchmarks" / "SCR_Bench" / "SCR-AuthBlur" / "cases"
    if base.exists():
        for case_dir in sorted(base.iterdir()):
            skills_dir = case_dir / "cli_skills" / "skills"
            if skills_dir.exists():
                for skill_dir in sorted(skills_dir.iterdir()):
                    if skill_dir.is_dir() and not skill_dir.name.startswith("."):
                        authblur_skills.append(str(skill_dir))
    if authblur_skills:
        groups["scr-authblur"] = authblur_skills
        print(f"  AuthBlur: {len(authblur_skills)} skills")

    # 5. SCR-TrustLift benchmark skills (from experiment group)
    trustlift_skills = []
    base = PROJECT_ROOT / "benchmarks" / "SCR_Bench" / "SCR-TrustLift"
    for experiment in ["experiment", "experiment-group"]:
        exp_dir = base / experiment
        if exp_dir.exists():
            for agent_dir in sorted(exp_dir.iterdir()):
                if not agent_dir.is_dir():
                    continue
                # Check .trae/skills, .claude/skills, registry/skills
                for skills_base in [
                    agent_dir / ".trae" / "skills",
                    agent_dir / ".claude" / "skills",
                    agent_dir / "registry" / "skills",
                    agent_dir / "registry" / "other",
                    agent_dir / "cli_skills" / "skills",
                ]:
                    if skills_base.exists():
                        for skill_dir in sorted(skills_base.iterdir()):
                            if skill_dir.is_dir():
                                name = skill_dir.name
                                if name not in ("secure-skill", "user-research-doc",
                                                "security-review", "install-permission-auditor",
                                                "ai-truthfulness-enforcer"):
                                    trustlift_skills.append(str(skill_dir))
    if trustlift_skills:
        groups["scr-trustlift"] = trustlift_skills
        print(f"  TrustLift: {len(trustlift_skills)} skills")

    # 6. SCR-CapFlow benchmark skills
    capflow_skills = []
    base = PROJECT_ROOT / "benchmarks" / "SCR_Bench" / "SCR-CapFlow" / "cases-env"
    if base.exists():
        for case_dir in sorted(base.iterdir()):
            skills_dir = case_dir / "cli_skills" / "skills"
            if skills_dir.exists():
                for skill_dir in sorted(skills_dir.iterdir()):
                    if skill_dir.is_dir() and not skill_dir.name.startswith("."):
                        capflow_skills.append(str(skill_dir))
    if capflow_skills:
        groups["scr-capflow"] = capflow_skills
        print(f"  CapFlow: {len(capflow_skills)} skills")

    # 7. SCR-Transition benchmark skills
    transition_skills = []
    base = PROJECT_ROOT / "benchmarks" / "SCR_Bench" / "SCR-Transition" / "cases"
    if base.exists():
        for case_dir in sorted(base.iterdir()):
            skills_dir = case_dir / "cli_skills" / "skills"
            if skills_dir.exists():
                for skill_dir in sorted(skills_dir.iterdir()):
                    if skill_dir.is_dir() and not skill_dir.name.startswith("."):
                        transition_skills.append(str(skill_dir))
    if transition_skills:
        groups["scr-transition"] = transition_skills
        print(f"  Transition: {len(transition_skills)} skills")

    # 8. Experiment run skills (from active_defense/code/experiment_runs)
    # Only include non-standard skills (not secure-skill, etc.)
    experiment_skills = []
    exp_root = PROJECT_ROOT / "active_defense" / "code" / "experiment_runs"
    if exp_root.exists():
        for exp_dir in sorted(exp_root.iterdir()):
            if not exp_dir.is_dir():
                continue
            for agent_dir in sorted(exp_dir.iterdir()):
                if not agent_dir.is_dir():
                    continue
                # Check .trae/skills and .claude/skills
                for skills_base in [
                    agent_dir / ".trae" / "skills",
                    agent_dir / ".claude" / "skills",
                    agent_dir / "registry" / "skills",
                ]:
                    if skills_base.exists():
                        for skill_dir in sorted(skills_base.iterdir()):
                            if skill_dir.is_dir() and skill_dir.name not in (
                                "secure-skill", "user-research-doc",
                                "security-review", "install-permission-auditor",
                                "ai-truthfulness-enforcer"
                            ):
                                case_name = f"{agent_dir.name}_{skills_base.parent.parent.name}"
                                experiment_skills.append(str(skill_dir))
    if experiment_skills:
        groups["experiment-runs"] = experiment_skills
        print(f"  Experiment runs: {len(experiment_skills)} skills")

    return groups


def main() -> None:
    strict = "--strict" in sys.argv
    output = sys.argv[sys.argv.index("--output") + 1] if "--output" in sys.argv else "all_skills_security_report.md"

    print("🔍 Finding all skill directories...")
    groups = find_skill_dirs()

    all_results: list[SkillScanResult] = []
    total_skills = sum(len(skills) for skills in groups.values())
    print(f"\n📊 Found {total_skills} skills across {len(groups)} groups\n")

    # Scan each group
    scanned = 0
    for group_name, skill_dirs in sorted(groups.items()):
        print(f"  Scanning group '{group_name}' ({len(skill_dirs)} skills)...")
        for sd in sorted(skill_dirs):
            result = scan_skill(sd, strict)
            # Prefix skill name with group
            result.skill_name = f"{group_name}:{result.skill_name}"
            all_results.append(result)
            scanned += 1
            if scanned % 50 == 0:
                print(f"    ... {scanned}/{total_skills} scanned")

    # Generate full report
    generate_markdown_report(all_results, output)
    print(f"\n📄 Report written to: {output}")
    print_summary(all_results)

    # Generate detailed JSON
    json_output = output.replace(".md", ".json")
    json_results = []
    for r in all_results:
        d = {
            "skill_name": r.skill_name,
            "code_verdict": r.code_verdict,
            "prompt_verdict": r.prompt_verdict,
            "supply_verdict": r.supply_verdict,
            "overall_verdict": r.overall_verdict,
            "critical_count": r.critical_count,
            "high_count": r.high_count,
            "info_count": r.info_count,
            "findings": r.findings,
        }
        json_results.append(d)
    with open(json_output, "w", encoding="utf-8") as f:
        json.dump(json_results, f, indent=2, ensure_ascii=False)
    print(f"📄 JSON details written to: {json_output}")

    any_fail = any(r.overall_verdict == "FAIL" for r in all_results)
    sys.exit(1 if any_fail else 0)


if __name__ == "__main__":
    main()
