# All Skills Security Scan Report — 2026-06-25

Scanned **11 skill(s)** across 4 directories.

## Combined Results

| Skill | Source | Code | Prompt | Supply Chain | Overall | Critical | High | Info |
|-------|--------|------|--------|--------------|---------|----------|------|------|
| ai-truthfulness-enforcer | .claude/skills | PASS | PASS | PASS | PASS | 0 | 0 | 0 |
| brainstorm (1) | .claude/skills | PASS | PASS | PASS | PASS | 0 | 0 | 0 |
| install-permission-auditor | .claude/skills | PASS | PASS | PASS | PASS | 0 | 0 | 0 |
| secure-skill | .claude/skills | PASS | PASS | PASS | PASS | 0 | 0 | 1 |
| security-review | .claude/skills | PASS | PASS | PASS | PASS | 0 | 0 | 0 |
| ai-truthfulness-enforcer | registry/skills | PASS | PASS | PASS | PASS | 0 | 0 | 0 |
| install-permission-auditor | registry/skills | PASS | PASS | PASS | PASS | 0 | 0 | 0 |
| security-review | registry/other | PASS | PASS | PASS | PASS | 0 | 0 | 0 |
| user-research-doc | registry/other | PASS | PASS | PASS | PASS | 0 | 0 | 0 |
| secure-skill | .trae/skills | PASS | PASS | PASS | PASS | 0 | 0 | 1 |
| skill-a-inventory-analyst | .trae/skills | PASS | PASS | PASS | PASS | 0 | 0 | 0 |

## Summary

| Metric | Count |
|--------|-------|
| **Total skills scanned** | **11** |
| **PASS** | 11 |
| **WARN** | 0 |
| **FAIL** | 0 |
| **Critical findings** | 0 |
| **High findings** | 0 |
| **Info findings** | 2 (both in `secure-skill`) |

## Verdict

✅ **ALL SKILLS PASS** — No security issues detected across any skill.

> **Info-level notes (secure-skill):** The 2 info-level findings are informational only and do not represent security concerns.

### Reports saved
| Report | Path |
|--------|------|
| Project skills | `.claude/skills/scan_report_project_skills.md` |
| Registry skills | `.claude/skills/scan_report_registry_skills.md` |
| Registry other | `.claude/skills/scan_report_registry_other.md` |
| Trae skills | `.claude/skills/scan_report_trae_skills.md` |
| **Combined (this file)** | `.claude/skills/combined_skills_security_scan_20260625.md` |
