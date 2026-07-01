#!/usr/bin/env python3
"""
Scan ALL .claude/skills directories across the project.
Runs the scanner via subprocess on each directory and aggregates results.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path("/Users/bytedance/Downloads/code_zxr/agent_safety")
SCANNER = str(PROJECT_ROOT / "active_defense" / "code" / "experiment_runs" /
    "full_asr_trustlift_20260625_230313" / "co_INST-10_git_task1_0287e4" /
    ".claude" / "skills" / "secure-skill" / "scripts" / "scan_skills.py")
TIMESTAMP = "20260625"

python = sys.executable

print("Discovering all .claude/skills directories...")
all_dirs = sorted(PROJECT_ROOT.rglob(".claude/skills"))
skills_dirs = []
for d in all_dirs:
    try:
        if d.is_dir() and d.exists():
            skills_dirs.append(d)
    except OSError:
        pass  # broken symlink or inaccessible
print(f"Found {len(skills_dirs)} valid directories (skipped broken symlinks)")

all_rows = []    # (group, skill_name, code, prompt, supply, overall, crit, high, info)
scanned_count = 0
error_count = 0

for i, skills_dir in enumerate(skills_dirs):
    # Check if it has skill subdirs
    try:
        skill_subdirs = sorted([d for d in skills_dir.iterdir()
                                if d.is_dir() and not d.name.startswith(".")])
    except (OSError, FileNotFoundError) as e:
        error_count += 1
        continue
    if not skill_subdirs:
        continue

    rel = skills_dir.relative_to(PROJECT_ROOT)
    # Derive group label
    parts = rel.parts
    if "experiment_runs" in parts:
        idx = parts.index("experiment_runs")
        group = "/".join(parts[idx+1:idx+3]) if len(parts) > idx+2 else str(rel)
    elif "benchmarks" in parts:
        group = "/".join(parts[:-1])
    else:
        group = str(rel)

    scanned_count += 1
    sys.stdout.write(f"\r[{scanned_count}] {rel} ({len(skill_subdirs)} skills)     ")
    sys.stdout.flush()

    result = subprocess.run(
        [python, SCANNER, str(skills_dir), "--json"],
        capture_output=True, text=True, timeout=120
    )

    # Parse JSON output
    if result.returncode == 0 and result.stdout.strip():
        try:
            data = json.loads(result.stdout)
            for item in data:
                all_rows.append((
                    group, item["skill_name"],
                    item["code_verdict"], item["prompt_verdict"],
                    item["supply_verdict"], item["overall_verdict"],
                    item["critical_count"], item["high_count"],
                    item["info_count"]
                ))
        except (json.JSONDecodeError, KeyError) as e:
            print(f"\n  JSON parse error for {rel}: {e}")

print(f"\n\nScanned {scanned_count} directories, found {len(all_rows)} skills")

# Aggregate
pass_c = sum(1 for r in all_rows if r[5] == "PASS")
warn_c = sum(1 for r in all_rows if r[5] == "WARN")
fail_c = sum(1 for r in all_rows if r[5] == "FAIL")
crit_t = sum(r[6] for r in all_rows)
high_t = sum(r[7] for r in all_rows)
info_t = sum(r[8] for r in all_rows)

# Group results
from collections import defaultdict
by_group = defaultdict(list)
for row in all_rows:
    by_group[row[0]].append(row)

# Write report
lines = [
    "# ALL Skills Security Scan Report",
    "",
    f"**Generated:** 2026-06-25",
    f"**Project:** {PROJECT_ROOT}",
    f"**Directories with skills:** {scanned_count}",
    f"**Total unique skills:** {len(all_rows)}",
    "",
    "## Aggregate Summary",
    "",
    "| Verdict | Count |",
    "|---------|-------|",
    f"| **PASS** | {pass_c} |",
    f"| **WARN** | {warn_c} |",
    f"| **FAIL** | {fail_c} |",
    f"| Critical Findings | {crit_t} |",
    f"| High Findings | {high_t} |",
    f"| Info Findings | {info_t} |",
    "",
    "## Detailed Results",
    "",
]

for group in sorted(by_group.keys()):
    rows = by_group[group]
    g_pass = sum(1 for r in rows if r[5] == "PASS")
    g_warn = sum(1 for r in rows if r[5] == "WARN")
    g_fail = sum(1 for r in rows if r[5] == "FAIL")
    lines.append(f"### {group}")
    lines.append(f"Skills: {len(rows)} — PASS={g_pass} WARN={g_warn} FAIL={g_fail}")
    lines.append("")
    lines.append("| Skill | Code | Prompt | Supply Chain | Overall | Critical | High | Info |")
    lines.append("|-------|------|--------|--------------|---------|----------|------|------|")
    for row in rows:
        lines.append(f"| {row[1]} | {row[2]} | {row[3]} | {row[4]} | {row[5]} | {row[6]} | {row[7]} | {row[8]} |")
    lines.append("")

# Find FAIL skills for warnings
fail_skills = [r for r in all_rows if r[5] == "FAIL"]
if fail_skills:
    lines.append("## ⚠️ FAIL Skills Requiring Attention")
    lines.append("")
    lines.append("| Group | Skill | Code | Prompt | Supply | Critical | High |")
    lines.append("|-------|-------|------|--------|--------|----------|------|")
    for r in fail_skills:
        lines.append(f"| {r[0]} | {r[1]} | {r[2]} | {r[3]} | {r[4]} | {r[6]} | {r[7]} |")
    lines.append("")

report_path = PROJECT_ROOT / ".claude" / "skills" / f"all_skills_security_report_{TIMESTAMP}.md"
with open(report_path, "w") as f:
    f.write("\n".join(lines) + "\n")

print(f"\nReport: {report_path}")
print(f"PASS={pass_c}  WARN={warn_c}  FAIL={fail_c}")
print(f"Critical={crit_t}  High={high_t}  Info={info_t}")
