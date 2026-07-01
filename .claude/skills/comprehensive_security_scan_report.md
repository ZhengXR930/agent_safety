# Comprehensive Skills Security Scan Report

**Generated:** 2026-06-25  
**Tool:** secure-skill / scan_skills.py + scan_all_skills.py  
**Project root:** `/Users/bytedance/Downloads/code_zxr/agent_safety`

---

## Executive Summary

| Metric | Value |
|--------|-------|
| **Total skills scanned** | 3,486 |
| **Groups** | 8 (project-core, registry-skills, registry-other, trae, experiment-runs, scr-authblur, scr-capflow, scr-trustlift) |
| **PASS** | 2,993 (85.9%) |
| **WARN** | 38 (1.1%) |
| **FAIL** | 455 (13.0%) |

### Findings by Severity

| Severity | Count |
|----------|-------|
| **CRITICAL** | 681 |
| **HIGH** | 759 |
| **INFO** | 1,774 |

---

## Results by Group

### Core Project Skills (all PASS) ✅

| Skill | Code | Prompt | Supply | Overall |
|-------|------|--------|--------|---------|
| project-core:ai-truthfulness-enforcer | PASS | PASS | PASS | PASS |
| project-core:brainstorm (1) | PASS | PASS | PASS | PASS |
| project-core:install-permission-auditor | PASS | PASS | PASS | PASS |
| project-core:scan_reports_authblur_transition | PASS | PASS | PASS | PASS |
| project-core:secure-skill | PASS | PASS | PASS | PASS (1 INFO) |
| project-core:security-review | PASS | PASS | PASS | PASS |

### Registry Skills (all PASS) ✅

| Skill | Code | Prompt | Supply | Overall |
|-------|------|--------|--------|---------|
| registry-skills:ai-truthfulness-enforcer | PASS | PASS | PASS | PASS |
| registry-skills:install-permission-auditor | PASS | PASS | PASS | PASS |
| registry-other:security-review | PASS | PASS | PASS | PASS |
| registry-other:user-research-doc | PASS | PASS | PASS | PASS |

### .trae Skills (all PASS) ✅

| Skill | Code | Prompt | Supply | Overall |
|-------|------|--------|--------|---------|
| trae:secure-skill | PASS | PASS | PASS | PASS (1 INFO) |
| trae:skill-a-inventory-analyst | PASS | PASS | PASS | PASS |

### Experiment Runs — Failing Skills

| Skill | Code | Prompt | Supply | Details |
|-------|------|--------|--------|---------|
| experiment-runs:skill_b | FAIL | PASS | WARN | 1 CRITICAL, 1 HIGH |
| experiment-runs:contact-broadcaster | FAIL | PASS | PASS/WARN | 1 CRITICAL, 0/1 HIGH |
| experiment-runs:bulk-delete-records | FAIL | PASS | PASS | 1 CRITICAL |

### SCR-CapFlow — Failing Skills

| Skill | Code | Prompt | Supply |
|-------|------|--------|--------|
| scr-capflow:skill_b | FAIL | PASS | WARN |
| scr-capflow:contact-broadcaster | FAIL | PASS | PASS/WARN |

### SCR-TrustLift — Failing Skills (122 unique)

Benchmark skills with security issues including:
- `co_INST-*` skills: docx/pptx/xlsx task skills with code execution
- `ob_INST-*` skills: docx/pdf/pptx/python-code task skills  
- `context7`, `doc-scraper`, `pptx`, `notion-summary`, `network-conftest-generator`, `flow-nexus-platform`

---

## Finding Types Breakdown

### CRITICAL Findings (681)

| Category | Count | Examples |
|----------|-------|----------|
| **CODE-EXEC** | 391 | `__import__()` dynamic import, `compile()`, `eval()`, `exec()` |
| **NET-EXFIL** | 232 | `urllib.request.urlopen()`, `requests.post()`, socket connections |
| **DATA-EXTRACT** | 50 | Instructions to send/upload file contents externally |
| **SYSTEM-OVERRIDE** | 6 | "ignore previous instructions", "override system prompt" |
| **TYPOSQUAT** | 2 | Typosquatted package names in requirements.txt |

### HIGH Findings (759)

| Category | Count | Examples |
|----------|-------|----------|
| **TYPOSQUAT** | 598 | Imports resembling typosquatted package names |
| **FS-BOUNDARY** | 99 | File access outside skill boundary, destructive file ops |
| **INLINE-INSTALL** | 4 | `pip install` inline in scripts |
| Other | ~58 | OBFUSCATION, HIDDEN-CHARS, PRIV-ESC, HIDDEN-DIRECTIVE |

### INFO Findings (1,774)

| Category | Count |
|----------|-------|
| SUBPROCESS | 876 |
| ENV-ACCESS | 438 |
| UNPINNED | 30 |
| FILE-OPS | 20 |
| SUSPICIOUS-LANG | ~410 |

---

## Notable Patterns

| Pattern | Details |
|---------|---------|
| **Benchmark attack skills** | Most FAIL/WARN results come from intentional attack skills in SCR-TrustLift and experiment-run benchmarks. These skills are DESIGNED to be malicious (typosquatting, exfiltration, code execution). |
| **Core project skills** | All project registry skills pass with 0 findings. Only 2 INFO findings exist across secure-skill instances (subprocess.run() with list args in auto-install code). |
| **Common failing skill** | `skill_b` appears across experiment-runs and capflow groups with `__import__()`, `urllib.request.urlopen()`, and typosquat patterns. |
| **Common warning skill** | `adobesign` in experiment-runs and trustlift groups with prompt-level/warn findings. |

> **Note:** The `secure-skill` itself has 1 INFO finding per instance: `subprocess.run()` on line 441 for automated skill installation. It uses safe list args (`shell=False` default), so the risk is minimal.

---

## Reports Generated

| Report | Path |
|--------|------|
| Full scan report (markdown) | `.claude/skills/all_skills_security_scan_report.md` |
| Full scan details (JSON) | `.claude/skills/all_skills_security_scan_report.json` |
| Project core skills | `.claude/skills/all_project_skills_scan_report.md` |
| Project core skills (strict) | `.claude/skills/all_project_skills_scan_report_strict.md` |
| Registry other skills | `registry/other/registry_other_scan_report.md` |
| Registry other skills (strict) | `.trae/skills/trae_skills_scan_report_strict.md` |
