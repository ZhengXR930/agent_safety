#!/usr/bin/env python3
"""
Comprehensive wrapper: scan ALL skills across every .claude/skills directory
in the project and produce a single aggregated report.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path("/Users/bytedance/Downloads/code_zxr/agent_safety")
SCANNER = PROJECT_ROOT / "active_defense" / "code" / "experiment_runs" / "full_asr_trustlift_20260625_230313" / "co_INST-10_git_task1_0287e4" / ".claude" / "skills" / "secure-skill" / "scripts" / "scan_skills.py"
OUTPUT_DIR = PROJECT_ROOT / ".claude" / "skills"
TIMESTAMP = "20260625"

# Ensure scanner exists
if not SCANNER.exists():
    print(f"ERROR: scanner not found at {SCANNER}", file=sys.stderr)
    sys.exit(1)

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Discovery phase: find all .claude/skills directories
print("Discovering all .claude/skills directories...")
all_skills_dirs = sorted(PROJECT_ROOT.rglob(".claude/skills"))
# Remove symlinks or broken ones
skills_dirs = [d for d in all_skills_dirs if d.is_dir()]
print(f"Found {len(skills_dirs)} skills directories.")

# For each .claude/skills directory, check if it has subdirectories (actual skills)
groups = {}
for sd in skills_dirs:
    subdirs = [d for d in sd.iterdir() if d.is_dir() and not d.name.startswith(".")]
    if subdirs:
        # Derive a group name from the parent experiment path
        rel = sd.relative_to(PROJECT_ROOT)
        name_parts = []
        for part in rel.parts:
            if part == ".claude":
                break
            name_parts.append(part)
        group_name = "_".join(name_parts[-3:]) if len(name_parts) >= 3 else "_".join(name_parts)
        groups.setdefault(group_name, []).append(sd)

report_files = []

# Scan each group
for group_name, dirs in sorted(groups.items()):
    print(f"\n{'='*60}")
    print(f"Scanning group: {group_name} ({len(dirs)} dirs)")
    print(f"{'='*60}")

    for skills_dir in dirs:
        rel = skills_dir.relative_to(PROJECT_ROOT)
        dir_name = str(rel).replace("/", "_").replace(".", "_")
        output_file = OUTPUT_DIR / f"scan_{dir_name}_{TIMESTAMP}.md"

        # Check how many skill subdirectories
        skill_subdirs = [d for d in skills_dir.iterdir() if d.is_dir() and not d.name.startswith(".")]
        if not skill_subdirs:
            continue

        print(f"  Scanning {rel} ({len(skill_subdirs)} skills)...")

        result = subprocess.run(
            [sys.executable, str(SCANNER), str(skills_dir),
             "--output", str(output_file)],
            capture_output=True, text=True, timeout=120
        )

        if result.returncode != 0:
            print(f"    ⚠️  Scan had fail/warn (exit {result.returncode})")

        # Read and store the summary lines
        for line in result.stdout.splitlines():
            if line.strip():
                print(f"    {line.strip()}")

        if result.stderr and "Fail install" in result.stderr:
            print(f"    ⚠️  Install note: {result.stderr.strip()}")

        report_files.append((str(rel), str(output_file)))

# Generate master summary
print(f"\n{'='*60}")
print(f"SCAN COMPLETE")
print(f"{'='*60}")
print(f"Total skills dirs scanned: {len(report_files)}")

# Collect all individual reports and aggregate into a master report
all_results = []
all_pass = 0
all_warn = 0
all_fail = 0
all_unknown = 0

for rel_path, report_file in report_files:
    if not Path(report_file).exists():
        continue
    with open(report_file) as f:
        content = f.read()

    # Parse the table rows from the report
    for line in content.splitlines():
        if line.startswith("| ") and not line.startswith("| Skill |") and not line.startswith("|---"):
            parts = [p.strip() for p in line.split("|")[1:-1]]
            if len(parts) >= 8:
                skill_name = parts[0]
                overall = parts[4]
                if overall == "PASS":
                    all_pass += 1
                elif overall == "WARN":
                    all_warn += 1
                elif overall == "FAIL":
                    all_fail += 1
                else:
                    all_unknown += 1
                all_results.append((rel_path, skill_name, parts[1], parts[2], parts[3], overall, parts[5], parts[6], parts[7]))

# Write master report
master_report_path = OUTPUT_DIR / f"all_skills_security_report_{TIMESTAMP}.md"
with open(master_report_path, "w") as f:
    f.write(f"# ALL Skills Security Scan Report\n")
    f.write(f"\n**Generated:** 2026-06-25\n")
    f.write(f"**Project:** {PROJECT_ROOT}\n")
    f.write(f"**Skills directories scanned:** {len(report_files)}\n")
    f.write(f"**Total skills found:** {len(all_results)}\n")
    f.write(f"\n## Aggregate Summary\n\n")
    f.write(f"| Verdict | Count |\n")
    f.write(f"|---------|-------|\n")
    f.write(f"| **PASS** | {all_pass} |\n")
    f.write(f"| **WARN** | {all_warn} |\n")
    f.write(f"| **FAIL** | {all_fail} |\n")
    f.write(f"\n## Full Results\n\n")
    f.write(f"| Group | Skill | Code | Prompt | Supply Chain | Overall | Critical | High | Info |\n")
    f.write(f"|-------|-------|------|--------|--------------|---------|----------|------|------|\n")
    for rel_path, skill_name, cv, pv, sv, ov, cc, hc, ic in all_results:
        f.write(f"| {rel_path} | {skill_name} | {cv} | {pv} | {sv} | {ov} | {cc} | {hc} | {ic} |\n")

print(f"\nMaster report written to: {master_report_path}")
print(f"\nAggregate: PASS={all_pass}  WARN={all_warn}  FAIL={all_fail}  UNKNOWN={all_unknown}")

# Output summary per group
print(f"\n--- Per-Group Summary ---")
for group_name, dirs in sorted(groups.items()):
    group_pass = sum(1 for r in all_results if r[0].startswith(dirs[0].name.split("/")[-1]) and r[5] == "PASS")
    group_fail = sum(1 for r in all_results if r[0].startswith(dirs[0].name.split("/")[-1]) and r[5] == "FAIL")
    group_warn = sum(1 for r in all_results if r[0].startswith(dirs[0].name.split("/")[-1]) and r[5] == "WARN")
    print(f"  {group_name}: {len(dirs)} dirs, PASS={group_pass}  WARN={group_warn}  FAIL={group_fail}")

sys.exit(0 if all_fail == 0 else 1)
