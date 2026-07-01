#!/usr/bin/env python3
"""
Comprehensive scan of ALL skills across the entire project.
Scans main directories + all experiment run skills dirs.
Generates one consolidated report.
"""
from __future__ import annotations

import json
import os
import sys
import re
from dataclasses import dataclass, field, asdict
from pathlib import Path

# Add the secure-skill scripts dir to path for importing scan modules
SCRIPTS_DIR = Path("/Users/bytedance/Downloads/code_zxr/agent_safety/.trae/skills/secure-skill/scripts")
sys.path.insert(0, str(SCRIPTS_DIR))

# Import scan functions from the existing scanner
from scan_skills import scan_skill, generate_markdown_report, print_summary, SkillScanResult

PROJECT_ROOT = Path("/Users/bytedance/Downloads/code_zxr/agent_safety")

# Core skills directories
CORE_DIRS = [
    PROJECT_ROOT / ".claude" / "skills",
    PROJECT_ROOT / ".trae" / "skills",
    PROJECT_ROOT / "registry" / "skills",
    PROJECT_ROOT / "registry" / "other",
]

# Experiment runs
EXPERIMENT_RUNS = PROJECT_ROOT / "active_defense" / "code" / "experiment_runs"

def find_skills_dirs():
    """Find all 'skills' directories under the project."""
    found = []
    for d in CORE_DIRS:
        if d.exists():
            found.append(d)
    # Find experiment run skills dirs
    if EXPERIMENT_RUNS.exists():
        for d in sorted(EXPERIMENT_RUNS.iterdir()):
            if d.is_dir():
                # Find .claude/skills and .trae/skills in each experiment run
                for skills_dir in d.rglob("skills"):
                    if skills_dir.is_dir() and skills_dir.parent.name in (".claude", ".trae"):
                        found.append(skills_dir)
    return found

def main():
    output_dir = PROJECT_ROOT / ".claude" / "skills"
    output_path = output_dir / "full_project_skills_scan_report.md"
    json_output = output_dir / "full_project_skills_scan_report.json"

    all_skills_dirs = find_skills_dirs()
    print(f"Found {len(all_skills_dirs)} skills directories to scan.")

    all_results = []
    seen_skills = {}  # skill_name -> (result, source_dir)

    for sd in all_skills_dirs:
        source = sd.relative_to(PROJECT_ROOT) if PROJECT_ROOT in sd.parents else sd
        print(f"\n{'='*60}")
        print(f"Scanning: {source}")

        # Get all skill subdirectories (excluding dotfiles and files)
        skill_subdirs = sorted(
            str(p) for p in Path(sd).iterdir()
            if p.is_dir() and not p.name.startswith(".")
        )

        if not skill_subdirs:
            print(f"  (no skill subdirectories)")
            continue

        for skill_path in skill_subdirs:
            skill_name = Path(skill_path).name
            result = scan_skill(skill_path, strict=False)

            # Track results - for duplicate skill names across runs, keep the first seen
            # or the worst verdict
            if skill_name in seen_skills:
                prev = seen_skills[skill_name]
                # Keep the worst verdict
                verdict_rank = {"PASS": 0, "WARN": 1, "FAIL": 2}
                if verdict_rank.get(result.overall_verdict, 0) > verdict_rank.get(prev.overall_verdict, 0):
                    seen_skills[skill_name] = result
                    # Also add source info
                    result.skill_name = f"{skill_name}"
                    setattr(result, "source", str(source))
            else:
                seen_skills[skill_name] = result
                setattr(result, "source", str(source))

            verdict_str = result.overall_verdict
            c = result.critical_count
            h = result.high_count
            i = result.info_count
            detail = ""
            if c or h:
                detail = f" (C={c} H={h} I={i})"
            print(f"  {verdict_str:4}  {skill_name:40s} {detail}")

    # Consolidate unique skills
    print(f"\n{'='*60}")
    print(f"Total unique skills scanned: {len(seen_skills)}")

    results = list(seen_skills.values())
    results.sort(key=lambda r: ({"FAIL": 0, "WARN": 1, "PASS": 2}.get(r.overall_verdict, 3), r.skill_name))

    # Generate report
    lines = [
        "# Full Project Skills Security Scan Report\n",
        f"Generated: 2026-06-25 23:15",
        f"Skills directories scanned: {len(all_skills_dirs)}",
        f"Unique skills found: {len(results)}\n",
        "| Skill | Code | Prompt | Supply Chain | Overall | Critical | High | Info | Source |",
        "|-------|------|--------|--------------|---------|----------|------|------|--------|",
    ]

    for r in results:
        src = getattr(r, "source", "unknown")
        lines.append(
            f"| {r.skill_name} | {r.code_verdict} | {r.prompt_verdict} | "
            f"{r.supply_verdict} | {r.overall_verdict} | "
            f"{r.critical_count} | {r.high_count} | {r.info_count} | {src} |"
        )

    # Summary table
    passes = sum(1 for r in results if r.overall_verdict == "PASS")
    warns = sum(1 for r in results if r.overall_verdict == "WARN")
    fails = sum(1 for r in results if r.overall_verdict == "FAIL")

    lines.append(f"\n## Summary\n")
    lines.append(f"- **Total unique skills:** {len(results)}")
    lines.append(f"- **PASS:** {passes}")
    lines.append(f"- **WARN:** {warns}")
    lines.append(f"- **FAIL:** {fails}")

    # Detailed findings section
    has_findings = [r for r in results if r.critical_count > 0 or r.high_count > 0]
    if has_findings:
        lines.append(f"\n## Detailed Findings (skills with CRITICAL/HIGH issues)\n")
        for r in has_findings:
            lines.append(f"### {r.skill_name}")
            lines.append(f"- Source: {getattr(r, 'source', 'unknown')}")
            lines.append(f"- Overall: {r.overall_verdict}")
            lines.append(f"- Critical: {r.critical_count}, High: {r.high_count}, Info: {r.info_count}")
            lines.append("")

    report_content = "\n".join(lines) + "\n"

    with open(str(output_path), "w", encoding="utf-8") as fh:
        fh.write(report_content)

    # JSON output
    json_results = []
    for r in results:
        d = asdict(r)
        d["source"] = getattr(r, "source", "unknown")
        json_results.append(d)

    with open(str(json_output), "w", encoding="utf-8") as fh:
        json.dump(json_results, fh, indent=2)

    print(f"\nReport written to: {output_path}")
    print(f"JSON written to: {json_output}")
    print(f"\nSummary: {passes} PASS, {warns} WARN, {fails} FAIL out of {len(results)} unique skills")

    return 1 if fails > 0 else 0

if __name__ == "__main__":
    sys.exit(main())
