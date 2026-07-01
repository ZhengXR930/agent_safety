# Full Project Skills Security Scan Report

**Date:** 2026-06-25  
**Scanner:** secure-skill / `scan_skills.py`  
**Scope:** All 4 skill source directories under the project  

---

## Overall Summary

| Metric | Count |
|--------|-------|
| Total skills scanned | **11** (across 4 directories) |
| PASS | **11** |
| WARN | **0** |
| FAIL | **0** |
| Critical findings | 0 |
| High findings | 0 |
| Info findings | 1 |

**Overall verdict: ✅ ALL PASS — no security issues found.**

---

## Per-Skill Results (Deduplicated)

| # | Skill | Origin | Code | Prompt | Supply Chain | Overall | C | H | I |
|---|-------|--------|------|--------|--------------|---------|---|---|---|
| 1 | ai-truthfulness-enforcer | `.claude/skills` | PASS | PASS | PASS | PASS | 0 | 0 | 0 |
| 2 | brainstorm (1) | `.claude/skills` | PASS | PASS | PASS | PASS | 0 | 0 | 0 |
| 3 | install-permission-auditor | `.claude/skills` | PASS | PASS | PASS | PASS | 0 | 0 | 0 |
| 4 | secure-skill | `.claude/skills` | PASS | PASS | PASS | PASS | 0 | 0 | 1 |
| 5 | security-review | `.claude/skills` | PASS | PASS | PASS | PASS | 0 | 0 | 0 |
| 6 | secure-skill | `.trae/skills` | PASS | PASS | PASS | PASS | 0 | 0 | 1 |
| 7 | skill-a-inventory-analyst | `.trae/skills` | PASS | PASS | PASS | PASS | 0 | 0 | 0 |
| 8 | ai-truthfulness-enforcer | `registry/skills` | PASS | PASS | PASS | PASS | 0 | 0 | 0 |
| 9 | install-permission-auditor | `registry/skills` | PASS | PASS | PASS | PASS | 0 | 0 | 0 |
| 10 | security-review | `registry/other` | PASS | PASS | PASS | PASS | 0 | 0 | 0 |
| 11 | user-research-doc | `registry/other` | PASS | PASS | PASS | PASS | 0 | 0 | 0 |

---

## Per-Source Directory Breakdown

### 1. `.claude/skills` (Main Claude Skills)

**5 skills scanned:** ai-truthfulness-enforcer, brainstorm (1), install-permission-auditor, secure-skill, security-review

- All PASS / 0 critical / 0 high / 1 info
- The only INFO finding: `subprocess.run()` call in `secure-skill/scripts/scan_skills.py` (used for auto-install after scan — safe usage with list args, no shell=True)

### 2. `.trae/skills` (Trae Skills)

**2 skills scanned:** secure-skill, skill-a-inventory-analyst

- All PASS / 0 critical / 0 high / 1 info
- The INFO finding duplicates the same `subprocess.run()` call from the secure-skill scanner

### 3. `registry/skills` (Registry Skills)

**2 skills scanned:** ai-truthfulness-enforcer, install-permission-auditor

- All PASS / 0 findings

### 4. `registry/other` (Registry Other)

**2 skills scanned:** security-review, user-research-doc

- All PASS / 0 findings

---

## Finding Details

### INFO — SUBPROCESS (secure-skill/scripts/scan_skills.py line 441)

```
subprocess.run([sys.executable, str(install_script), str(target_root)], check=True)
```

**Risk:** Subprocess call (verify shell=False)  
**Status:** ✅ Safe — uses list args with no shell=True. This is the scanner's own post-scan auto-install mechanism.  
**Recommendation:** Acceptable as-is for a security scanning tool that needs to install skills. Could be suppressed.

---

## Conclusion

**All 11 skills across the project pass security scanning with zero critical, zero high findings.** The only INFO-level finding is the scanner's own `subprocess.run` call (safe usage), which is inherent to its design.

No code execution risks, no prompt injection patterns, and no supply chain vulnerabilities (typosquatting, unpinned deps, or inline installs) were detected in any skill.
