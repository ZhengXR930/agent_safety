#!/usr/bin/env python3
"""
Scan ALL .claude/skills directories across the project.
Uses direct Python calls to the scanner's core functions.
"""
from __future__ import annotations

import json
import os
import sys
import traceback
from pathlib import Path
from collections import defaultdict

PROJECT_ROOT = Path("/Users/bytedance/Downloads/code_zxr/agent_safety")

# ── Directly embed the scanner logic ──────────────────────────────
# We inline the needed functions from scan_skills.py to avoid module
# import issues and the auto-install side effect at end of main().

import re
from dataclasses import dataclass, field, asdict

@dataclass
class Finding:
    severity: str
    category: str
    file: str
    line: int
    detail: str
    fix: str

@dataclass
class SkillScanResult:
    skill_name: str
    code_verdict: str
    prompt_verdict: str
    supply_verdict: str
    overall_verdict: str
    critical_count: int
    high_count: int
    info_count: int
    findings: list = field(default_factory=list)

# Load patterns
patterns_path = PROJECT_ROOT / "active_defense" / "code" / "experiment_runs" / "full_asr_trustlift_20260625_230313" / "co_INST-10_git_task1_0287e4" / ".claude" / "skills" / "secure-skill" / "scripts" / "patterns.json"
with open(str(patterns_path), "r", encoding="utf-8") as fh:
    _PATTERNS = json.load(fh)

CODE_CRITICAL = _PATTERNS["code_critical"]
CODE_HIGH = _PATTERNS["code_high"]
CODE_INFO = _PATTERNS["code_info"]
PROMPT_CRITICAL = _PATTERNS["prompt_critical"]
PROMPT_HIGH = _PATTERNS["prompt_high"]
PROMPT_INFO = _PATTERNS["prompt_info"]

ZERO_WIDTH_CHARS = {
    "​": "zero-width space (U+200B)",
    "‌": "zero-width non-joiner (U+200C)",
    "‍": "zero-width joiner (U+200D)",
    "﻿": "byte order mark (U+FEFF)",
    "⁠": "word joiner (U+2060)",
    "⁢": "invisible times (U+2062)",
    "⁣": "invisible separator (U+2063)",
}

SCANNABLE_EXTENSIONS = {".md", ".txt", ".yaml", ".yml", ".rst", ".adoc"}

POPULAR_PACKAGES = [
    "requests", "urllib3", "boto3", "botocore", "setuptools", "pip",
    "certifi", "charset-normalizer", "idna", "numpy", "typing-extensions",
    "packaging", "six", "python-dateutil", "pyyaml", "s3transfer",
    "cryptography", "cffi", "jmespath", "pyasn1", "attrs", "click",
    "importlib-metadata", "pycparser", "tomli", "platformdirs", "wheel",
    "filelock", "colorama", "markupsafe", "jinja2", "zipp", "pyparsing",
    "pytz", "pillow", "pandas", "aiohttp", "grpcio", "scipy",
    "protobuf", "wrapt", "flask", "django", "sqlalchemy", "psycopg2",
    "redis", "celery", "pytest", "coverage", "tox", "flake8",
    "black", "mypy", "isort", "pylint", "httpx", "fastapi", "uvicorn",
    "pydantic", "starlette", "gunicorn", "paramiko", "fabric",
    "beautifulsoup4", "lxml", "scrapy", "selenium", "playwright",
    "matplotlib", "scikit-learn", "tensorflow", "torch", "transformers",
    "openai", "langchain", "anthropic", "docker", "kubernetes",
    "google-cloud-storage", "azure-storage-blob", "aws-cdk-lib",
    "pygments", "rich", "typer", "argparse", "pathlib", "dataclasses",
]

KNOWN_TYPOSQUATS = {
    "reqeusts": "requests", "requets": "requests", "reqests": "requests",
    "request": "requests", "requestes": "requests", "colourma": "colorama",
    "colourama": "colorama", "numppy": "numpy", "numpay": "numpy",
    "pandsa": "pandas", "pandaas": "pandas", "flassk": "flask",
    "flaask": "flask", "djano": "django", "djnago": "django",
    "scikitlearn": "scikit-learn", "beautifulsoup": "beautifulsoup4",
    "python-opencv": "opencv-python", "python3-dateutil": "python-dateutil",
    "pipsqlalchemy": "sqlalchemy", "httx": "httpx", "fasttapi": "fastapi",
    "pyaml": "pyyaml", "pycryptography": "cryptography",
}

def _levenshtein(s1, s2):
    if len(s1) < len(s2):
        return _levenshtein(s2, s1)
    if len(s2) == 0:
        return len(s1)
    prev = list(range(len(s2) + 1))
    for i, c1 in enumerate(s1):
        curr = [i + 1]
        for j, c2 in enumerate(s2):
            curr.append(min(prev[j + 1] + 1, curr[j] + 1, prev[j] + (c1 != c2)))
        prev = curr
    return prev[-1]

def _normalize_pkg(name):
    return re.sub(r"[-_.]+", "-", name).lower()

def _scan_code_file(filepath):
    findings = []
    try:
        with open(filepath, "r", encoding="utf-8", errors="replace") as fh:
            lines = fh.readlines()
    except OSError:
        return findings
    for line_num, line in enumerate(lines, start=1):
        if line.strip().startswith("#"):
            continue
        for category, patterns in CODE_CRITICAL.items():
            for pat in patterns:
                if re.search(pat["regex"], line):
                    findings.append(Finding("CRITICAL", category, filepath,
                        line_num, line.strip()[:80], pat["fix"]))
        for category, patterns in CODE_HIGH.items():
            for pat in patterns:
                if re.search(pat["regex"], line):
                    findings.append(Finding("HIGH", category, filepath,
                        line_num, line.strip()[:80], pat["fix"]))
        for category, patterns in CODE_INFO.items():
            for pat in patterns:
                if re.search(pat["regex"], line):
                    findings.append(Finding("INFO", category, filepath,
                        line_num, line.strip()[:80], pat["fix"]))
    return findings

def scan_code(skill_dir, strict=False):
    findings = []
    for p in sorted(Path(skill_dir).rglob("*.py")):
        findings.extend(_scan_code_file(str(p)))
    critical = sum(1 for f in findings if f.severity == "CRITICAL")
    high = sum(1 for f in findings if f.severity == "HIGH")
    info = sum(1 for f in findings if f.severity == "INFO")
    if critical > 0:
        verdict = "FAIL"
    elif high > 0:
        verdict = "FAIL" if strict else "WARN"
    else:
        verdict = "PASS"
    return verdict, critical, high, info, findings

def _in_code_block(lines, target_line):
    in_block = False
    for i in range(target_line):
        if lines[i].strip().startswith("```"):
            in_block = not in_block
    return in_block

def _scan_prompt_file(filepath):
    findings = []
    try:
        with open(filepath, "r", encoding="utf-8", errors="replace") as fh:
            content = fh.read()
            lines = content.splitlines()
    except OSError:
        return findings
    for char, desc in ZERO_WIDTH_CHARS.items():
        pos = content.find(char)
        if pos != -1:
            line_num = content[:pos].count("\n") + 1
            findings.append(Finding("HIGH", "HIDDEN-CHARS", filepath, line_num,
                f"[{desc}]", "Remove all zero-width characters"))
    for line_num, line in enumerate(lines, start=1):
        if _in_code_block(lines, line_num - 1):
            continue
        ll = line.lower()
        for category, patterns in PROMPT_CRITICAL.items():
            for pat in patterns:
                m = re.search(pat["regex"], ll)
                if m:
                    findings.append(Finding("CRITICAL", category, filepath,
                        line_num, m.group(0)[:70], pat["fix"]))
        for category, patterns in PROMPT_HIGH.items():
            for pat in patterns:
                m = re.search(pat["regex"], ll)
                if m:
                    findings.append(Finding("HIGH", category, filepath,
                        line_num, m.group(0)[:70], pat["fix"]))
        for category, patterns in PROMPT_INFO.items():
            for pat in patterns:
                m = re.search(pat["regex"], ll)
                if m:
                    findings.append(Finding("INFO", category, filepath,
                        line_num, m.group(0)[:70], pat["fix"]))
    return findings

def scan_prompt(skill_dir, strict=False):
    findings = []
    for p in sorted(Path(skill_dir).rglob("*")):
        if p.is_file() and p.suffix in SCANNABLE_EXTENSIONS:
            findings.extend(_scan_prompt_file(str(p)))
    critical = sum(1 for f in findings if f.severity == "CRITICAL")
    high = sum(1 for f in findings if f.severity == "HIGH")
    info = sum(1 for f in findings if f.severity == "INFO")
    if critical > 0:
        verdict = "FAIL"
    elif high > 0:
        verdict = "FAIL" if strict else "WARN"
    else:
        verdict = "PASS"
    return verdict, critical, high, info, findings

def _check_typosquat(pkg):
    norm = _normalize_pkg(pkg)
    if norm in KNOWN_TYPOSQUATS:
        return True, KNOWN_TYPOSQUATS[norm]
    for popular in POPULAR_PACKAGES:
        pop_norm = _normalize_pkg(popular)
        if norm == pop_norm:
            return False, ""
        dist = _levenshtein(norm, pop_norm)
        if len(norm) >= 4 and 1 <= dist <= 2:
            return True, popular
    return False, ""

def _extract_imports(filepath):
    results = []
    try:
        with open(filepath, "r", encoding="utf-8", errors="replace") as fh:
            for line_num, line in enumerate(fh, start=1):
                s = line.strip()
                if s.startswith("#"):
                    continue
                m = re.match(r"^import\s+([\w.]+)", s)
                if m:
                    results.append((line_num, m.group(1).split(".")[0]))
                m = re.match(r"^from\s+([\w.]+)\s+import", s)
                if m:
                    results.append((line_num, m.group(1).split(".")[0]))
    except OSError:
        pass
    return results

def _extract_requirements(filepath):
    results = []
    try:
        with open(filepath, "r", encoding="utf-8", errors="replace") as fh:
            for line_num, line in enumerate(fh, start=1):
                s = line.strip()
                if not s or s.startswith("#") or s.startswith("-"):
                    continue
                m = re.match(r"^([A-Za-z0-9_.-]+)\s*(==|>=|<=|~=|!=|>|<|;|\[|$)", s)
                if m:
                    results.append((line_num, m.group(1), m.group(2) == "=="))
    except OSError:
        pass
    return results

def _scan_pip_inline(filepath):
    results = []
    try:
        with open(filepath, "r", encoding="utf-8", errors="replace") as fh:
            for line_num, line in enumerate(fh, start=1):
                if re.search(r"(pip3?|python3?\s+-m\s+pip)\s+install\b", line):
                    results.append((line_num, line.strip()))
    except OSError:
        pass
    return results

def scan_supply(skill_dir, strict=False):
    findings = []
    checked = set()
    skill_path = Path(skill_dir)
    for p in sorted(skill_path.rglob("*.py")):
        for line_num, pkg in _extract_imports(str(p)):
            if pkg in checked:
                continue
            checked.add(pkg)
            is_typo, real = _check_typosquat(pkg)
            if is_typo:
                findings.append(Finding("HIGH", "TYPOSQUAT", str(p), line_num,
                    f"'{pkg}' looks like a typosquat of '{real}'",
                    f"Verify package name. Did you mean '{real}'?"))
        for line_num, line_text in _scan_pip_inline(str(p)):
            findings.append(Finding("HIGH", "INLINE-INSTALL", str(p), line_num,
                f"Inline install: {line_text[:60]}",
                "Move dependencies to requirements.txt"))
    for req_name in ("requirements.txt", "requirements-dev.txt"):
        for p in sorted(skill_path.rglob(req_name)):
            for line_num, pkg, pinned in _extract_requirements(str(p)):
                if pkg not in checked:
                    checked.add(pkg)
                    is_typo, real = _check_typosquat(pkg)
                    if is_typo:
                        findings.append(Finding("CRITICAL", "TYPOSQUAT", str(p), line_num,
                            f"'{pkg}' looks like a typosquat of '{real}'",
                            f"Replace with correct name: '{real}'"))
                if not pinned:
                    findings.append(Finding("INFO", "UNPINNED", str(p), line_num,
                        f"'{pkg}' is not pinned to an exact version",
                        f"Pin to specific version: {pkg}==<version>"))
    critical = sum(1 for f in findings if f.severity == "CRITICAL")
    high = sum(1 for f in findings if f.severity == "HIGH")
    info = sum(1 for f in findings if f.severity == "INFO")
    if critical > 0:
        verdict = "FAIL"
    elif high > 0:
        verdict = "FAIL" if strict else "WARN"
    else:
        verdict = "PASS"
    return verdict, critical, high, info, findings

def _worst_verdict(verdicts):
    if "FAIL" in verdicts:
        return "FAIL"
    if "WARN" in verdicts:
        return "WARN"
    return "PASS"

def scan_skill(skill_dir, strict=False):
    name = Path(skill_dir).name
    cv, cc, ch, ci, cf = scan_code(skill_dir, strict)
    pv, pc, ph, pi, pf = scan_prompt(skill_dir, strict)
    sv, sc, sh, si, sf = scan_supply(skill_dir, strict)
    overall = _worst_verdict([cv, pv, sv])
    total_c = cc + pc + sc
    total_h = ch + ph + sh
    total_i = ci + pi + si
    return SkillScanResult(
        skill_name=name,
        code_verdict=cv,
        prompt_verdict=pv,
        supply_verdict=sv,
        overall_verdict=overall,
        critical_count=total_c,
        high_count=total_h,
        info_count=total_i,
    )

# ── Main scan logic ───────────────────────────────────────────────

TIMESTAMP = "20260625"

print("Discovering all .claude/skills directories...")
all_dirs = sorted(PROJECT_ROOT.rglob(".claude/skills"))
skills_dirs = []
errors = []
for d in all_dirs:
    try:
        if d.is_dir() and d.exists():
            skills_dirs.append(d)
    except OSError:
        errors.append(str(d))
print(f"Found {len(skills_dirs)} valid directories ({len(errors)} broken)")
if errors:
    for e in errors[:5]:
        print(f"  ⚠️  Broken: {e}")

all_rows = []    # (group, skill_name, code, prompt, supply, overall, crit, high, info)
scanned_count = 0
skip_no_skills = 0
scan_errors = 0

for i, skills_dir in enumerate(skills_dirs):
    # Check if it has skill subdirs
    try:
        skill_subdirs = sorted([
            d for d in skills_dir.iterdir()
            if d.is_dir() and not d.name.startswith(".")
        ])
    except (OSError, FileNotFoundError):
        scan_errors += 1
        continue

    if not skill_subdirs:
        skip_no_skills += 1
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
    sys.stdout.write(f"\r[{scanned_count}] {group} ({len(skill_subdirs)} skills)     ")
    sys.stdout.flush()

    for sd in skill_subdirs:
        try:
            result = scan_skill(str(sd), strict=False)
            all_rows.append((
                group, result.skill_name,
                result.code_verdict, result.prompt_verdict,
                result.supply_verdict, result.overall_verdict,
                result.critical_count, result.high_count,
                result.info_count
            ))
        except Exception as e:
            print(f"\n  Error scanning {sd}: {e}")

print(f"\n\nScanned {scanned_count} directories, found {len(all_rows)} skills")

# Aggregate
pass_c = sum(1 for r in all_rows if r[5] == "PASS")
warn_c = sum(1 for r in all_rows if r[5] == "WARN")
fail_c = sum(1 for r in all_rows if r[5] == "FAIL")
crit_t = sum(r[6] for r in all_rows)
high_t = sum(r[7] for r in all_rows)
info_t = sum(r[8] for r in all_rows)

by_group = defaultdict(list)
for row in all_rows:
    by_group[row[0]].append(row)

lines = [
    "# ALL Skills Security Scan Report",
    "",
    f"**Generated:** 2026-06-25",
    f"**Project:** {PROJECT_ROOT}",
    f"**Directories with skills scanned:** {scanned_count}",
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
