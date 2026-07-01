#!/usr/bin/env python3
"""
Comprehensive deduplicated skills security scan.
Scans each UNIQUE skill name across the project once.
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from dataclasses import asdict
from pathlib import Path

SCRIPTS_DIR = Path("/Users/bytedance/Downloads/code_zxr/agent_safety/.trae/skills/secure-skill/scripts")
sys.path.insert(0, str(SCRIPTS_DIR))
from scan_skills import scan_skill, SkillScanResult

PROJECT_ROOT = Path("/Users/bytedance/Downloads/code_zxr/agent_safety")

def find_all_skill_instances():
    """Find all skill instances grouped by skill name across the project."""
    skill_map = defaultdict(list)  # skill_name -> [ (path, relative_source) ]
    seen_paths = set()

    # 1. Core directories
    core_dirs = [
        PROJECT_ROOT / ".claude" / "skills",
        PROJECT_ROOT / ".trae" / "skills",
        PROJECT_ROOT / "registry" / "skills",
        PROJECT_ROOT / "registry" / "other",
    ]
    for d in core_dirs:
        if d.exists():
            for p in d.iterdir():
                if p.is_dir() and not p.name.startswith("."):
                    rel = p.relative_to(PROJECT_ROOT)
                    skill_map[p.name].append((p, str(rel)))
                    seen_paths.add(p)

    # 2. Experiment runs
    expruns = PROJECT_ROOT / "active_defense" / "code" / "experiment_runs"
    if expruns.exists():
        for run_dir in sorted(expruns.iterdir()):
            if not run_dir.is_dir():
                continue
            for skills_dir in run_dir.rglob("skills"):
                if not skills_dir.is_dir() or skills_dir.parent.name not in (".claude", ".trae"):
                    continue
                for p in skills_dir.iterdir():
                    if p.is_dir() and not p.name.startswith("."):
                        if p not in seen_paths:
                            rel = p.relative_to(PROJECT_ROOT)
                            skill_map[p.name].append((p, str(rel)))
                            seen_paths.add(p)

    return skill_map

def main():
    print("Finding all unique skills across the project...")
    skill_map = find_all_skill_instances()
    unique_names = sorted(skill_map.keys())
    total_instances = sum(len(v) for v in skill_map.values())

    print(f"Found {len(unique_names)} unique skill names in {total_instances} total instances.\n")

    results = []
    for name in sorted(unique_names):
        instances = skill_map[name]
        best_path, best_src = instances[0]
        n_instances = len(instances)

        # Scan the first instance (all instances with the same name should be identical)
        try:
            result = scan_skill(str(best_path), strict=False)
            result.skill_name = name
        except Exception as e:
            print(f"  ERROR scanning {name}: {e}")
            from dataclasses import field
            result = SkillScanResult(
                skill_name=name,
                code_verdict="ERROR",
                prompt_verdict="ERROR",
                supply_verdict="ERROR",
                overall_verdict="ERROR",
                critical_count=0,
                high_count=0,
                info_count=0,
                findings=[],
            )

        # Determine first and last instance directories for the "range" source
        instance_srcs = sorted(s for _, s in instances)
        if n_instances == 1:
            source_display = instance_srcs[0]
        else:
            source_display = f"{instance_srcs[0]} (+{n_instances-1} more)"

        setattr(result, "instances", n_instances)
        setattr(result, "source", str(best_path))

        verdict = result.overall_verdict
        c = result.critical_count
        h = result.high_count
        i = result.info_count
        detail = ""
        if c or h:
            detail = f" [C={c} H={h} I={i}]"
        print(f"  {verdict:5}  {name:45s} ({n_instances:3d} instances){detail}")

        results.append(result)

    # Sort by severity then name
    verdict_rank = {"FAIL": 0, "WARN": 1, "PASS": 2, "ERROR": 3}
    results.sort(key=lambda r: (verdict_rank.get(r.overall_verdict, 9), r.skill_name))

    # Generate report
    output_dir = PROJECT_ROOT / ".claude" / "skills"
    output_path = output_dir / "full_project_skills_scan_report.md"
    json_path = output_dir / "full_project_skills_scan_report.json"

    lines = [
        "# Project-Wide Skills Security Scan Report\n",
        f"**Generated:** 2026-06-25 23:15",
        f"**Unique skill names found:** {len(results)}",
        f"**Total skill instances across project:** {total_instances}",
        f"**Skills directories scanned:** {len(set(s[0].parent for v in skill_map.values() for s in v))}\n",
        "## Results Table\n",
        "| Skill | Code | Prompt | Supply Chain | Overall | Critical | High | Info | Instances |",
        "|-------|------|--------|--------------|---------|----------|------|------|-----------|",
    ]

    for r in results:
        n = getattr(r, "instances", 1)
        lines.append(
            f"| {r.skill_name} | {r.code_verdict} | {r.prompt_verdict} | "
            f"{r.supply_verdict} | {r.overall_verdict} | "
            f"{r.critical_count} | {r.high_count} | {r.info_count} | {n} |"
        )

    passes = sum(1 for r in results if r.overall_verdict == "PASS")
    warns = sum(1 for r in results if r.overall_verdict == "WARN")
    fails = sum(1 for r in results if r.overall_verdict == "FAIL")
    errors = sum(1 for r in results if r.overall_verdict == "ERROR")

    lines.append(f"\n## Summary\n")
    lines.append(f"- **Unique skills:** {len(results)}")
    lines.append(f"- **Total instances:** {total_instances}")
    lines.append(f"- **PASS:** {passes}")
    lines.append(f"- **WARN:** {warns}")
    lines.append(f"- **FAIL:** {fails}")
    if errors:
        lines.append(f"- **ERROR:** {errors}")

    # Detail findings
    has_issues = [r for r in results if r.critical_count > 0 or r.high_count > 0 or r.overall_verdict == "FAIL"]
    if has_issues:
        lines.append(f"\n## Skills with Findings (CRITICAL/HIGH/FAIL)\n")
        for r in has_issues:
            lines.append(f"### {r.skill_name}")
            lines.append(f"- Instances: {getattr(r, 'instances', 1)}")
            lines.append(f"- Overall: {r.overall_verdict}")
            lines.append(f"- Critical: {r.critical_count}, High: {r.high_count}, Info: {r.info_count}")
            lines.append(f"- Source: {getattr(r, 'source', 'unknown')}")
            lines.append("")
            for f in r.findings:
                lines.append(f"  - [{f['severity']}] {f['category']}: {f['detail'][:100]}")
            lines.append("")

    lines.append("\n## All Scanned Skill Names\n")
    lines.append("| # | Skill Name | Instances | Verdict |")
    lines.append("|---|------------|-----------|---------|")
    for i, r in enumerate(sorted(results, key=lambda x: x.skill_name), 1):
        lines.append(f"| {i} | {r.skill_name} | {getattr(r, 'instances', 1)} | {r.overall_verdict} |")

    report = "\n".join(lines) + "\n"
    with open(str(output_path), "w", encoding="utf-8") as fh:
        fh.write(report)

    json_results = []
    for r in results:
        d = asdict(r)
        d["instances"] = getattr(r, "instances", 1)
        d["source"] = getattr(r, "source", "unknown")
        json_results.append(d)
    with open(str(json_path), "w", encoding="utf-8") as fh:
        json.dump(json_results, fh, indent=2)

    print(f"\n{'='*60}")
    print(f"Report:  {output_path}")
    print(f"JSON:    {json_path}")
    print(f"Summary: {passes} PASS, {warns} WARN, {fails} FAIL out of {len(results)} unique skills ({total_instances} total instances)")

    return 1 if fails > 0 else 0

if __name__ == "__main__":
    sys.exit(main())
