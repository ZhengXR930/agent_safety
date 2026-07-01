# Complete Skills Security Scan Report

**Date:** 2026-06-25
**Total Skills Scanned:** 3496 (from `.claude/skills`, `registry/skills`, experiment runs, and SCR benchmarks)

---

## Executive Summary

| Verdict | Count |
|---------|-------|
| ✅ **PASS** | 3001 |
| ⚠️ **WARN** | 38 |
| ❌ **FAIL** | 457 |

| Severity | Count |
|----------|-------|
| 🔴 CRITICAL | 685 |
| 🟠 HIGH | 764 |
| 🔵 INFO | 1797 |

---

## Finding Categories (Summary)

| Category | Count | Description |
|----------|-------|-------------|
| SUBPROCESS | 1094 | Subprocess calls (verify shell=False) |
| TYPOSQUAT | 614 | Potential package typosquatting |
| ENV-ACCESS | 487 | Environment variable reads |
| CODE-EXEC | 395 | Dynamic code execution (eval, exec, compile) |
| NET-EXFIL | 232 | Outbound network requests |
| FILE-OPS | 136 | File path expansion operations |
| FS-BOUNDARY | 100 | File access outside skill boundary |
| UNPINNED | 80 | Dependencies not pinned to exact version |
| DATA-EXTRACT | 50 | Data exfiltration instructions in markdown |
| INLINE-INSTALL | 32 | Inline pip install in code |
| HIDDEN-CHARS | 18 | Zero-width characters in markdown |
| SYSTEM-OVERRIDE | 6 | System prompt override language |
| OBFUSCATION | 2 | Obfuscated payload detection |

---

## 1. Main Project Skills (`.claude/skills`) — ALL PASS ✅

| Skill | Code | Prompt | Supply Chain | Overall | Findings |
|-------|------|--------|--------------|---------|----------|
| ai-truthfulness-enforcer | PASS | PASS | PASS | PASS | None |
| brainstorm (1) | PASS | PASS | PASS | PASS | None |
| install-permission-auditor | PASS | PASS | PASS | PASS | None |
| scan_reports_authblur_transition | PASS | PASS | PASS | PASS | None |
| secure-skill | PASS | PASS | PASS | PASS | 1 INFO |
| security-review | PASS | PASS | PASS | PASS | None |

**Status:** All 6 core project skills are clean with no critical or high findings.

---

## 2. Registry Skills (`registry/skills`) — ALL PASS ✅

| Skill | Code | Prompt | Supply Chain | Overall |
|-------|------|--------|--------------|---------|
| ai-truthfulness-enforcer | PASS | PASS | PASS | PASS |
| install-permission-auditor | PASS | PASS | PASS | PASS |

**Status:** Both registry skills are clean.

---

## 3. Experiment Runs Skills — FAILURES FOUND ❌

### 3a. Code FAIL (CRITICAL) — Network Exfiltration

**Root cause:** `urllib.request.urlopen()` outbound HTTP calls to dynamically configured `MOCK_SERVER_HOST`/`MOCK_SERVER_PORT`.

| Skill Name | Code | Prompt | Supply | Critical | High | Info |
|------------|------|--------|--------|----------|------|------|
| skill_b | FAIL | PASS | WARN | 1 | 1 | 2 |
| contact-broadcaster | FAIL | PASS | WARN | 1 | 1 | 2 |
| bulk-delete-records | FAIL | PASS | PASS | 1 | 0 | 0 |

**Example finding:**
```
[CRITICAL] NET-EXFIL: urllib.request.urlopen(req, timeout=5).read()
    Fix: Remove outbound network calls
[INFO] ENV-ACCESS: MOCK_SERVER_HOST / MOCK_SERVER_PORT
```

### 3b. Prompt FAIL — System Override / Hidden Directives

| Skill Name | Code | Prompt | Supply | Critical | High | Info |
|------------|------|--------|--------|----------|------|------|
| flow-nexus-platform | PASS | FAIL | PASS | 1 | 0 | 0 |
| flow-nexus-platform (2) | PASS | FAIL | PASS | 1 | 0 | 0 |
| ob_INST-10_docx_task3 | FAIL | FAIL | WARN | 3 | 3 | 3 |
| ob_INST-11_docx_task3 | FAIL | FAIL | WARN | 3 | 3 | 3 |
| co_INST-22_calendar_task0 | PASS | FAIL | PASS | 1 | 0 | 0 |

### 3c. SCR-TrustLift Benchmark: Combined Code + Supply Failures

Multiple SCR benchmark skills show a pattern of CODE-EXEC critical findings (eval/exec) combined with supply chain warnings (TYPOSQUAT, UNPINNED, INLINE-INSTALL). These are primarily in the SCR-TrustLift experiment group's test skills.

---

## 4. SCR-TrustLift Benchmark Skills — WARN Findings ⚠️

| Skill Name | Code | Prompt | Supply | Overall | High |
|------------|------|--------|--------|---------|------|
| co_INST-18_hf-paper-publisher | PASS | PASS | WARN | WARN | 1 |
| co_INST-19_hf-paper-publisher | PASS | PASS | WARN | WARN | 1 |
| co_INST-20_hf_model_evaluation | PASS | PASS | WARN | WARN | 5 |
| co_INST-21_hf_model_evaluation | PASS | PASS | WARN | WARN | 5 |
| co_INST-27_fhir-developer-skill_task* | PASS | PASS | WARN | WARN | 1 |
| import-notion | PASS | PASS | WARN | WARN | 1 |
| gemini-image (1) | WARN | PASS | WARN | WARN | 3 |
| adobesign | PASS | WARN | PASS | WARN | 1 |

---

## 5. Detailed Analysis of Top Risks

### 🔴 CODE-EXEC (395 findings)
- **eval() / exec() / compile() — Arbitrary code execution**
- Found in SCR benchmark test skills that are designed to test AI agent safety
- These may be intentional test cases rather than production code

### 🔴 NET-EXFIL (232 findings)
- **urllib.request.urlopen() — Outbound HTTP requests**
- Found in experiment run `skill_b` and `contact-broadcaster`
- These skills make POST requests to `MOCK_SERVER_HOST:MOCK_SERVER_PORT`
- Risk: if environment variables point to an attacker-controlled server, data could be exfiltrated

### 🟠 TYPOSQUAT (614 findings)
- Package names with Levenshtein distance ≤ 2 from popular packages
- High count is due to repeated instances of the same import patterns across many case directories

### 🟠 SUBPROCESS (1094 findings)
- `subprocess.run()` / `subprocess.Popen()` calls
- High count reflects many skills using subprocess for tool execution
- Need to verify `shell=False` is maintained

---

## 6. Recommendations

1. **For experiment run skills** (`skill_b`, `contact-broadcaster`, `bulk-delete-records`):
   - Replace `urllib.request.urlopen()` with sandboxed local file operations
   - Remove or document environment variable usage (`MOCK_SERVER_HOST`, `MOCK_SERVER_PORT`)
   - Add path validation before outbound operations

2. **For project main skills** (no action needed — all PASS):
   - All 6 core skills and 2 registry skills show no security issues

3. **For SCR benchmark skills** with prompt injection (SYSTEM-OVERRIDE):
   - Review whether system override language in SKILL.md is intentional (benchmark test)
   - If so, document as an approved test pattern

4. **General:**
   - Pin all dependencies in `requirements.txt` to exact versions
   - Remove inline `pip install` commands in favor of dependency files
   - Ensure all skills have `shell=False` in subprocess calls
   - Review zero-width characters in markdown files (18 instances)
