#!/usr/bin/env python3
"""
scan_all_skills.py - Comprehensive security scan of ALL skills under the project.

Scans all project & registry skills, then all benchmark skills from:
  - SCR-AuthBlur cases
  - SCR-TrustLift experiment
  - SCR-CapFlow cases
  - SCR-Transition cases
  - Experiment run _attack / _control skills

Generates a consolidated markdown report and detailed JSON.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

# Import the core scanning logic from scan_skills.py
SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPT_DIR))
from scan_skills import scan_skill, SkillScanResult, generate_markdown_report, print_summary


PROJECT_ROOT = Path("/Users/bytedance/Downloads/code_zxr/agent_safety")
SKIP_SKILLS = {
    "secure-skill", "user-research-doc", "security-review",
    "install-permission-auditor", "ai-truthfulness-enforcer",
}


def find_skill_dirs() -> dict[str, list[str]]:
    """Return dict of group_name -> list of skill_dir paths."""
    groups = {}

    # 1. Project core skills (.claude/skills)
    core_skills = [
        str(p) for p in (PROJECT_ROOT / ".claude" / "skills").iterdir()
        if p.is_dir() and not p.name.startswith(".") and p.name not in SKIP_SKILLS
    ]
    if core_skills:
        groups["project-core"] = core_skills
        print(f"  Project core: {len(core_skills)} skills")

    # 2. Registry skills
    for registry_type in ["skills", "other"]:
        reg_dir = PROJECT_ROOT / "registry" / registry_type
        if reg_dir.exists():
            skills = [str(p) for p in reg_dir.iterdir() if p.is_dir()]
            if skills:
                groups[f"registry-{registry_type}"] = skills
                print(f"  Registry {registry_type}: {len(skills)} skills")

    # 3. .trae skills
    trae_skills = [
        str(p) for p in (PROJECT_ROOT / ".trae" / "skills").iterdir()
        if p.is_dir() and not p.name.startswith(".")
    ]
    if trae_skills:
        groups["trae"] = trae_skills
        print(f"  .trae skills: {len(trae_skills)} skills")

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

    # 5. SCR-TrustLift benchmark skills
    trustlift_skills = []
    base = PROJECT_ROOT / "benchmarks" / "SCR_Bench" / "SCR-TrustLift"
    for experiment in ["experiment", "experiment-group"]:
        exp_dir = base / experiment
        if exp_dir.exists():
            for agent_dir in sorted(exp_dir.iterdir()):
                if not agent_dir.is_dir():
                    continue
                for skills_base in [
                    agent_dir / ".trae" / "skills",
                    agent_dir / ".claude" / "skills",
                    agent_dir / "registry" / "skills",
                    agent_dir / "registry" / "other",
                    agent_dir / "cli_skills" / "skills",
                ]:
                    if skills_base.exists():
                        for skill_dir in sorted(skills_base.iterdir()):
                            if skill_dir.is_dir() and skill_dir.name not in SKIP_SKILLS:
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

    # 8. Experiment run skills
    experiment_skills = []
    exp_root = PROJECT_ROOT / "active_defense" / "code" / "experiment_runs"
    if exp_root.exists():
        for exp_dir in sorted(exp_root.iterdir()):
            if not exp_dir.is_dir():
                continue
            for agent_dir in sorted(exp_dir.iterdir()):
                if not agent_dir.is_dir():
                    continue
                for skills_base in [
                    agent_dir / ".trae" / "skills",
                    agent_dir / ".claude" / "skills",
                ]:
                    if skills_base.exists():
                        for skill_dir in sorted(skills_base.iterdir()):
                            if skill_dir.is_dir() and skill_dir.name not in SKIP_SKILLS:
                                experiment_skills.append(str(skill_dir))
    if experiment_skills:
        groups["experiment-runs"] = experiment_skills
        print(f"  Experiment runs: {len(experiment_skills)} skills")

    return groups


def consolidate_like_skills(results: list[SkillScanResult]) -> list[SkillScanResult]:
    """Group results by base skill name and keep worst verdict per group."""
    # We keep the base report for detailed findings, but group summary info
    return results


def main() -> None:
    strict = "--strict" in sys.argv
    output_idx = sys.argv.index("--output") + 1 if "--output" in sys.argv else None
    output = sys.argv[output_idx] if output_idx else "all_skills_security_report.md"

    print("=" * 60)
    print("  COMPREHENSIVE SKILLS SECURITY SCAN")
    print("=" * 60)
    print()
    print("🔍 Finding all skill directories...")
    groups = find_skill_dirs()

    total_skills = sum(len(skills) for skills in groups.values())
    if not total_skills:
        print("❌ No skills found to scan.")
        sys.exit(0)

    print(f"\n📊 Found {total_skills} skills across {len(groups)} groups\n")

    # Scan each group
    all_results: list[SkillScanResult] = []
    scanned = 0
    for group_name, skill_dirs in sorted(groups.items()):
        print(f"  Scanning group '{group_name}' ({len(skill_dirs)} skills)...")
        group_results = []
        for sd in sorted(skill_dirs):
            try:
                result = scan_skill(sd, strict)
                result.skill_name = f"{group_name}:{result.skill_name}"
                group_results.append(result)
            except Exception as e:
                print(f"    ⚠️  Error scanning {sd}: {e}")
            scanned += 1
            if scanned % 100 == 0:
                print(f"    ... {scanned}/{total_skills} scanned")
        all_results.extend(group_results)

    print(f"\n✅ Total scanned: {scanned} skills")

    # Write the report
    output_path = SCRIPT_DIR.parent.parent.parent / output
    generate_markdown_report(all_results, str(output_path))
    print(f"\n📄 Report written to: {output_path}")
    print_summary(all_results)

    # Generate detailed JSON with all findings
    json_output = output_path.with_suffix(".json")
    json_results = []
    for r in all_results:
        json_results.append({
            "skill_name": r.skill_name,
            "code_verdict": r.code_verdict,
            "prompt_verdict": r.prompt_verdict,
            "supply_verdict": r.supply_verdict,
            "overall_verdict": r.overall_verdict,
            "critical_count": r.critical_count,
            "high_count": r.high_count,
            "info_count": r.info_count,
            "findings": r.findings,
        })
    with open(json_output, "w", encoding="utf-8") as f:
        json.dump(json_results, f, indent=2, ensure_ascii=False)
    print(f"📄 JSON details written to: {json_output}")

    # Summary stats
    fails = [r for r in all_results if r.overall_verdict == "FAIL"]
    warns = [r for r in all_results if r.overall_verdict == "WARN"]
    passes = [r for r in all_results if r.overall_verdict == "PASS"]
    print()
    print("=" * 60)
    print("  CONSOLIDATED RESULTS")
    print("=" * 60)
    print(f"  Total skills: {len(all_results)}")
    print(f"  ✅ PASS: {len(passes)}")
    print(f"  ⚠️  WARN: {len(warns)}")
    print(f"  ❌ FAIL: {len(fails)}")
    if fails:
        print()
        print("  Failed skills:")
        for r in fails:
            print(f"    ❌ {r.skill_name} (C:{r.code_verdict} P:{r.prompt_verdict} S:{r.supply_verdict})")
            print(f"       Critical={r.critical_count} High={r.high_count} Info={r.info_count}")
    if warns:
        print()
        print("  Warning skills:")
        for r in warns:
            print(f"    ⚠️  {r.skill_name} (C:{r.code_verdict} P:{r.prompt_verdict} S:{r.supply_verdict})")
            print(f"       Critical={r.critical_count} High={r.high_count} Info={r.info_count}")
    print()

    any_fail = bool(fails)
    sys.exit(1 if any_fail else 0)


if __name__ == "__main__":
    main()
