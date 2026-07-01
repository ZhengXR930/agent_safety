#!/usr/bin/env python3
"""
Comprehensive scan: walks ALL .claude/skills directories in the project,
scans each skill subdirectory, and produces an aggregated security report.
Uses direct imports from the scanner module.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

# Add scanner script directory to path
SCANNER_DIR = Path(
    "/Users/bytedance/Downloads/code_zxr/agent_safety/active_defense/code/experiment_runs/"
    "full_asr_trustlift_20260625_230313/co_INST-10_git_task1_0287e4/.claude/skills/"
    "secure-skill/scripts"
).resolve()
sys.path.insert(0, str(SCANNER_DIR))

# Import scanner functions
import importlib.util
spec = importlib.util.spec_from_file_location("scanner", SCANNER_DIR / "scan_skills.py")
scanner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(scanner)

PROJECT_ROOT = Path("/Users/bytedance/Downloads/code_zxr/agent_safety")
TIMESTAMP = "20260625"

ALL_SKILLS_DIRS = sorted(PROJECT_ROOT.rglob(".claude/skills"))

all_results = []
scanned_dirs = 0

for skills_dir in ALL_SKILLS_DIRS:
    skill_subdirs = sorted([
        d for d in skills_dir.iterdir()
        if d.is_dir() and not d.name.startswith(".")
    ])
    if not skill_subdirs:
        continue

    rel = skills_dir.relative_to(PROJECT_ROOT)
    scanned_dirs += 1
    for sd in skill_subdirs:
        try:
            result = scanner.scan_skill(str(sd), strict=False)
            all_results.append((str(rel), result))
        except Exception as e:
            print(f"  Error scanning {sd}: {e}", file=sys.stderr)

# Aggregate
summary = {}  # (group_name, skill_name) -> (overall, cv, pv, sv, crit, high, info)
for rel_path, r in all_results:
    # Derive group name from parent hierarchy
    parts = rel_path.split("/")
    # Use the first 2-3 meaningful parts
    if "experiment_runs" in parts:
        idx = parts.index("experiment_runs")
        group = "/".join(parts[idx:idx+2]) if len(parts) > idx+1 else rel_path
    elif "benchmarks" in parts:
        idx = parts.index("benchmarks")
        group = "/".join(parts[idx:idx+3]) if len(parts) > idx+2 else rel_path
    else:
        group = rel_path
    key = (group, r.skill_name, r.code_verdict, r.prompt_verdict, r.supply_verdict)
    summary[key] = (r.overall_verdict, r.critical_count, r.high_count, r.info_count)

grouped = {}
for (group, skill, cv, pv, sv), (ov, cc, hc, ic) in summary.items():
    if group not in grouped:
        grouped[group] = {}
    grouped[group][skill] = (cv, pv, sv, ov, cc, hc, ic)

# Write report
report = [f"# ALL Skills Security Scan Report", "",
          f"**Generated:** 2026-06-25", f"**Project:** {PROJECT_ROOT}",
          f"**Directories with skills scanned:** {scanned_dirs}",
          f"**Total unique skills found:** {len(summary)}", ""]

# Aggregate counts
pass_count = sum(1 for v in summary.values() if v[0] == "PASS")
warn_count = sum(1 for v in summary.values() if v[0] == "WARN")
fail_count = sum(1 for v in summary.values() if v[0] == "FAIL")
crit_total = sum(v[1] for v in summary.values())
high_total = sum(v[2] for v in summary.values())
info_total = sum(v[3] for v in summary.values())

report.append("## Aggregate Summary\n")
report.append("| Verdict | Count |")
report.append("|---------|-------|")
report.append(f"| **PASS** | {pass_count} |")
report.append(f"| **WARN** | {warn_count} |")
report.append(f"| **FAIL** | {fail_count} |")
report.append(f"| Critical | {crit_total} |")
report.append(f"| High | {high_total} |")
report.append(f"| Info | {info_total} |")
report.append("")

report.append("## Detailed Results by Group\n")
for group in sorted(grouped.keys()):
    skills = grouped[group]
    g_pass = sum(1 for v in skills.values() if v[3] == "PASS")
    g_warn = sum(1 for v in skills.values() if v[3] == "WARN")
    g_fail = sum(1 for v in skills.values() if v[3] == "FAIL")
    report.append(f"### {group}")
    report.append(f"Skills in group: {len(skills)} — PASS={g_pass} WARN={g_warn} FAIL={g_fail}\n")
    report.append("| Skill | Code | Prompt | Supply Chain | Overall | Critical | High | Info |")
    report.append("|-------|------|--------|--------------|---------|----------|------|------|")
    for skill_name in sorted(skills.keys()):
        cv, pv, sv, ov, cc, hc, ic = skills[skill_name]
        report.append(f"| {skill_name} | {cv} | {pv} | {sv} | {ov} | {cc} | {hc} | {ic} |")
    report.append("")

report_path = PROJECT_ROOT / ".claude" / "skills" / f"all_skills_security_report_{TIMESTAMP}.md"
with open(report_path, "w") as f:
    f.write("\n".join(report) + "\n")

print(f"Report: {report_path}")
print(f"\nSummary: {len(summary)} skills across {scanned_dirs} directories")
print(f"  PASS={pass_count}  WARN={warn_count}  FAIL={fail_count}")
print(f"  Critical={crit_total}  High={high_total}  Info={info_total}")
