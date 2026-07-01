# Project-Wide All Skills Security Scan Report

**Date:** 2026/06/25  
**Scanner:** `secure-skill` (code + prompt injection + supply chain analysis)  
**Scope:** All 4 skill directories across the entire project

> **Verdict: ✅ ALL 11 SKILLS PASS — Zero security issues detected.**

---

## Combined Results

| Skill | Directory | Code | Prompt | Supply | Overall | Crit | High | Info |
|-------|-----------|------|--------|--------|---------|------|------|------|
| ai-truthfulness-enforcer | `.claude/skills/` | PASS | PASS | PASS | **PASS** | 0 | 0 | 0 |
| ai-truthfulness-enforcer | `registry/skills/` | PASS | PASS | PASS | **PASS** | 0 | 0 | 0 |
| brainstorm (1) | `.claude/skills/` | PASS | PASS | PASS | **PASS** | 0 | 0 | 0 |
| install-permission-auditor | `.claude/skills/` | PASS | PASS | PASS | **PASS** | 0 | 0 | 0 |
| install-permission-auditor | `registry/skills/` | PASS | PASS | PASS | **PASS** | 0 | 0 | 0 |
| secure-skill | `.claude/skills/` | PASS | PASS | PASS | **PASS** | 0 | 0 | 1 |
| secure-skill | `.trae/skills/` | PASS | PASS | PASS | **PASS** | 0 | 0 | 1 |
| security-review | `.claude/skills/` | PASS | PASS | PASS | **PASS** | 0 | 0 | 0 |
| security-review | `registry/other/` | PASS | PASS | PASS | **PASS** | 0 | 0 | 0 |
| skill-a-inventory-analyst | `.trae/skills/` | PASS | PASS | PASS | **PASS** | 0 | 0 | 0 |
| user-research-doc | `registry/other/` | PASS | PASS | PASS | **PASS** | 0 | 0 | 0 |

---

## Source Reports

| Directory | Skills | Report |
|-----------|--------|--------|
| `.claude/skills/` | 5 | `claude_skills_security_report.md` |
| `.trae/skills/` | 2 | `trae_skills_security_report.md` |
| `registry/skills/` | 2 | `registry_skills_security_report.md` |
| `registry/other/` | 2 | `registry_other_security_report.md` |

---

## Findings Detail

### `secure-skill` (INFO — 1 finding in each copy)
- **Category:** SUPPLY CHAIN / UNPINNED DEPENDENCY
- **Detail:** One or more package references are not pinned to exact versions
- **Severity:** INFO (advisory only)
- **Fix:** Pin to specific version (e.g., `package==X.Y.Z`)
- **Note:** No actual typosquatting or vulnerability detected — this is a minor advisory

---

## Summary Statistics

| Metric | Count |
|--------|-------|
| Total skills scanned | 11 (7 unique) |
| PASS | 11 |
| WARN | 0 |
| FAIL | 0 |
| CRITICAL findings | 0 |
| HIGH findings | 0 |
| INFO findings | 2 |
