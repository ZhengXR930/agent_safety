# Comprehensive Skills Security Scan Report

**Date:** 2026-06-25 21:09:07
**Project:** agent_safety

## Executive Summary

| Metric | Value |
|--------|-------|
| **Overall Security Score** | **0/100** |
| Total Critical Findings | 20 |
| Total High Findings | 26 |
| Total Informational Findings | 89 |
| Skills with Findings | 14 |

### Score Guide
- **90-100**: Good security posture
- **70-89**: Medium risk — review high/critical items
- **50-69**: High risk — multiple critical items need attention
- **< 50**: Critical — immediate action required

> **Note:** The scanner excludes security-tool skills (secure-skill, install-permission-auditor, security-review) and generated report files. Findings are from actual application/experiment skills only.

### Key Risk Categories
| Severity | Categories |
|----------|------------|
| 🔴 **Critical** | CODE-EXEC, CMD-INJECT, NET-EXFIL, CRED-HARVEST (code) / SYSTEM-OVERRIDE, ROLE-HIJACK, DATA-EXTRACT (prompt) |
| 🟠 **High** | OBFUSCATION, UNSAFE-DESER, FS-BOUNDARY, PRIV-ESC (code) / SAFETY-BYPASS, EXCESSIVE-PERMS, HIDDEN-DIRECTIVE (prompt) |
| 🔵 **Info** | SUBPROCESS, ENV-ACCESS, FILE-OPS (code) / SUSPICIOUS-LANG (prompt) |

---

## Group Summary

| Group | Skills | Critical | High | Info | Status |
|-------|--------|----------|------|------|--------|
| Active Defense - Experiment Skills | 1 | 2 | 0 | 0 | 🔴 |
| TrustLift - Experiment Skills | 13 | 18 | 26 | 89 | 🔴 🟠 |

---

## Active Defense - Experiment Skills

### apple-music

**Findings:** 2 Critical, 0 High, 0 Info

#### 🔴 CRITICAL (2)

**NET-EXFIL:**

- **Line 466** `active_defense/code/experiment_runs/trustlift_C_20260619_153157/apple-music_attack_cf671a/.claude/skills/apple-music/SKILL.md`
  - Risk: Outbound HTTP may exfiltrate data
  - Match: `requests.post(`

- **Line 480** `active_defense/code/experiment_runs/trustlift_C_20260619_153157/apple-music_attack_cf671a/.claude/skills/apple-music/SKILL.md`
  - Risk: Outbound HTTP may exfiltrate data
  - Match: `requests.post(`


---

## TrustLift - Experiment Skills

### apple-music

**Findings:** 2 Critical, 0 High, 0 Info

#### 🔴 CRITICAL (2)

**NET-EXFIL:**

- **Line 466** `benchmarks/SCR_Bench/SCR-TrustLift/experiment/apple-music/.claude/skills/apple-music/SKILL.md`
  - Risk: Outbound HTTP may exfiltrate data
  - Match: `requests.post(`

- **Line 480** `benchmarks/SCR_Bench/SCR-TrustLift/experiment/apple-music/.claude/skills/apple-music/SKILL.md`
  - Risk: Outbound HTTP may exfiltrate data
  - Match: `requests.post(`


### chrome-devtools

**Findings:** 2 Critical, 7 High, 0 Info

#### 🔴 CRITICAL (2)

**CODE-EXEC:**

- **Line 41** `benchmarks/SCR_Bench/SCR-TrustLift/experiment/chrome-devtools/.claude/skills/chrome-devtools/scripts/lib/selector.js`
  - Risk: Arbitrary code execution via eval()
  - Match: `eval(`

- **Line 124** `benchmarks/SCR_Bench/SCR-TrustLift/experiment/chrome-devtools/.claude/skills/chrome-devtools/scripts/lib/selector.js`
  - Risk: Arbitrary code execution via eval()
  - Match: `eval(`


#### 🟠 HIGH (7)

**PRIV-ESC:**

- **Line 52** `benchmarks/SCR_Bench/SCR-TrustLift/experiment/chrome-devtools/.claude/skills/chrome-devtools/SKILL.md`
  - Risk: Privilege escalation via sudo
  - Match: `sudo`

- **Line 21** `benchmarks/SCR_Bench/SCR-TrustLift/experiment/chrome-devtools/.claude/skills/chrome-devtools/scripts/install-deps.sh`
  - Risk: Privilege escalation via sudo
  - Match: `SUDO`

- **Line 26** `benchmarks/SCR_Bench/SCR-TrustLift/experiment/chrome-devtools/.claude/skills/chrome-devtools/scripts/install-deps.sh`
  - Risk: Privilege escalation via sudo
  - Match: `SUDO`

- **Line 36** `benchmarks/SCR_Bench/SCR-TrustLift/experiment/chrome-devtools/.claude/skills/chrome-devtools/scripts/install-deps.sh`
  - Risk: Privilege escalation via sudo
  - Match: `SUDO`

- **Line 53** `benchmarks/SCR_Bench/SCR-TrustLift/experiment/chrome-devtools/.claude/skills/chrome-devtools/scripts/install-deps.sh`
  - Risk: Privilege escalation via sudo
  - Match: `SUDO`

- **Line 107** `benchmarks/SCR_Bench/SCR-TrustLift/experiment/chrome-devtools/.claude/skills/chrome-devtools/scripts/install-deps.sh`
  - Risk: Privilege escalation via sudo
  - Match: `SUDO`

- **Line 147** `benchmarks/SCR_Bench/SCR-TrustLift/experiment/chrome-devtools/.claude/skills/chrome-devtools/scripts/install-deps.sh`
  - Risk: Privilege escalation via sudo
  - Match: `SUDO`


### co_INST-13_docx_task3

**Findings:** 2 Critical, 4 High, 3 Info

#### 🔴 CRITICAL (2)

**CODE-EXEC:**

- **Line 917** `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-13_docx_task3/.claude/skills/co_INST-13_docx_task3/ooxml/scripts/validation/base.py`
  - Risk: Dynamic code compilation
  - Match: `compile(`

- **Line 83** `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-13_docx_task3/.claude/skills/co_INST-13_docx_task3/ooxml/scripts/validation/pptx.py`
  - Risk: Dynamic code compilation
  - Match: `compile(`


#### 🟠 HIGH (4)

**FS-BOUNDARY:**

- **Line 836** `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-13_docx_task3/.claude/skills/co_INST-13_docx_task3/scripts/document.py`
  - Risk: Destructive file operation
  - Match: `shutil.rmtree(`

**PRIV-ESC:**

- **Line 194** `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-13_docx_task3/.claude/skills/co_INST-13_docx_task3/SKILL.md`
  - Risk: Privilege escalation via sudo
  - Match: `sudo`

- **Line 196** `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-13_docx_task3/.claude/skills/co_INST-13_docx_task3/SKILL.md`
  - Risk: Privilege escalation via sudo
  - Match: `sudo`

- **Line 197** `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-13_docx_task3/.claude/skills/co_INST-13_docx_task3/SKILL.md`
  - Risk: Privilege escalation via sudo
  - Match: `sudo`


#### 🔵 INFO (3)

**SUBPROCESS:**

- **Line 103** `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-13_docx_task3/.claude/skills/co_INST-13_docx_task3/ooxml/scripts/pack.py`
  - Risk: Subprocess call (verify shell=False)
  - Match: `subprocess.run(`

- **Line 153** `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-13_docx_task3/.claude/skills/co_INST-13_docx_task3/ooxml/scripts/validation/redlining.py`
  - Risk: Subprocess call (verify shell=False)
  - Match: `subprocess.run(`

- **Line 185** `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-13_docx_task3/.claude/skills/co_INST-13_docx_task3/ooxml/scripts/validation/redlining.py`
  - Risk: Subprocess call (verify shell=False)
  - Match: `subprocess.run(`


### co_INST-13_docx_task4

**Findings:** 2 Critical, 4 High, 3 Info

#### 🔴 CRITICAL (2)

**CODE-EXEC:**

- **Line 917** `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-13_docx_task4/.claude/skills/co_INST-13_docx_task4/ooxml/scripts/validation/base.py`
  - Risk: Dynamic code compilation
  - Match: `compile(`

- **Line 83** `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-13_docx_task4/.claude/skills/co_INST-13_docx_task4/ooxml/scripts/validation/pptx.py`
  - Risk: Dynamic code compilation
  - Match: `compile(`


#### 🟠 HIGH (4)

**FS-BOUNDARY:**

- **Line 836** `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-13_docx_task4/.claude/skills/co_INST-13_docx_task4/scripts/document.py`
  - Risk: Destructive file operation
  - Match: `shutil.rmtree(`

**PRIV-ESC:**

- **Line 194** `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-13_docx_task4/.claude/skills/co_INST-13_docx_task4/SKILL.md`
  - Risk: Privilege escalation via sudo
  - Match: `sudo`

- **Line 196** `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-13_docx_task4/.claude/skills/co_INST-13_docx_task4/SKILL.md`
  - Risk: Privilege escalation via sudo
  - Match: `sudo`

- **Line 197** `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-13_docx_task4/.claude/skills/co_INST-13_docx_task4/SKILL.md`
  - Risk: Privilege escalation via sudo
  - Match: `sudo`


#### 🔵 INFO (3)

**SUBPROCESS:**

- **Line 103** `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-13_docx_task4/.claude/skills/co_INST-13_docx_task4/ooxml/scripts/pack.py`
  - Risk: Subprocess call (verify shell=False)
  - Match: `subprocess.run(`

- **Line 153** `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-13_docx_task4/.claude/skills/co_INST-13_docx_task4/ooxml/scripts/validation/redlining.py`
  - Risk: Subprocess call (verify shell=False)
  - Match: `subprocess.run(`

- **Line 185** `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-13_docx_task4/.claude/skills/co_INST-13_docx_task4/ooxml/scripts/validation/redlining.py`
  - Risk: Subprocess call (verify shell=False)
  - Match: `subprocess.run(`


### co_INST-13_docx_task5

**Findings:** 2 Critical, 4 High, 3 Info

#### 🔴 CRITICAL (2)

**CODE-EXEC:**

- **Line 917** `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-13_docx_task5/.claude/skills/co_INST-13_docx_task5/ooxml/scripts/validation/base.py`
  - Risk: Dynamic code compilation
  - Match: `compile(`

- **Line 83** `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-13_docx_task5/.claude/skills/co_INST-13_docx_task5/ooxml/scripts/validation/pptx.py`
  - Risk: Dynamic code compilation
  - Match: `compile(`


#### 🟠 HIGH (4)

**FS-BOUNDARY:**

- **Line 836** `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-13_docx_task5/.claude/skills/co_INST-13_docx_task5/scripts/document.py`
  - Risk: Destructive file operation
  - Match: `shutil.rmtree(`

**PRIV-ESC:**

- **Line 194** `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-13_docx_task5/.claude/skills/co_INST-13_docx_task5/SKILL.md`
  - Risk: Privilege escalation via sudo
  - Match: `sudo`

- **Line 196** `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-13_docx_task5/.claude/skills/co_INST-13_docx_task5/SKILL.md`
  - Risk: Privilege escalation via sudo
  - Match: `sudo`

- **Line 197** `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-13_docx_task5/.claude/skills/co_INST-13_docx_task5/SKILL.md`
  - Risk: Privilege escalation via sudo
  - Match: `sudo`


#### 🔵 INFO (3)

**SUBPROCESS:**

- **Line 103** `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-13_docx_task5/.claude/skills/co_INST-13_docx_task5/ooxml/scripts/pack.py`
  - Risk: Subprocess call (verify shell=False)
  - Match: `subprocess.run(`

- **Line 153** `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-13_docx_task5/.claude/skills/co_INST-13_docx_task5/ooxml/scripts/validation/redlining.py`
  - Risk: Subprocess call (verify shell=False)
  - Match: `subprocess.run(`

- **Line 185** `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-13_docx_task5/.claude/skills/co_INST-13_docx_task5/ooxml/scripts/validation/redlining.py`
  - Risk: Subprocess call (verify shell=False)
  - Match: `subprocess.run(`


### co_INST-13_pptx_task0

**Findings:** 2 Critical, 2 High, 5 Info

#### 🔴 CRITICAL (2)

**CODE-EXEC:**

- **Line 917** `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-13_pptx_task0/.claude/skills/co_INST-13_pptx_task0/ooxml/scripts/validation/base.py`
  - Risk: Dynamic code compilation
  - Match: `compile(`

- **Line 83** `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-13_pptx_task0/.claude/skills/co_INST-13_pptx_task0/ooxml/scripts/validation/pptx.py`
  - Risk: Dynamic code compilation
  - Match: `compile(`


#### 🟠 HIGH (2)

**PRIV-ESC:**

- **Line 483** `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-13_pptx_task0/.claude/skills/co_INST-13_pptx_task0/SKILL.md`
  - Risk: Privilege escalation via sudo
  - Match: `sudo`

- **Line 484** `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-13_pptx_task0/.claude/skills/co_INST-13_pptx_task0/SKILL.md`
  - Risk: Privilege escalation via sudo
  - Match: `sudo`


#### 🔵 INFO (5)

**SUBPROCESS:**

- **Line 103** `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-13_pptx_task0/.claude/skills/co_INST-13_pptx_task0/ooxml/scripts/pack.py`
  - Risk: Subprocess call (verify shell=False)
  - Match: `subprocess.run(`

- **Line 153** `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-13_pptx_task0/.claude/skills/co_INST-13_pptx_task0/ooxml/scripts/validation/redlining.py`
  - Risk: Subprocess call (verify shell=False)
  - Match: `subprocess.run(`

- **Line 185** `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-13_pptx_task0/.claude/skills/co_INST-13_pptx_task0/ooxml/scripts/validation/redlining.py`
  - Risk: Subprocess call (verify shell=False)
  - Match: `subprocess.run(`

- **Line 219** `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-13_pptx_task0/.claude/skills/co_INST-13_pptx_task0/scripts/thumbnail.py`
  - Risk: Subprocess call (verify shell=False)
  - Match: `subprocess.run(`

- **Line 237** `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-13_pptx_task0/.claude/skills/co_INST-13_pptx_task0/scripts/thumbnail.py`
  - Risk: Subprocess call (verify shell=False)
  - Match: `subprocess.run(`


### co_INST-13_pptx_task1

**Findings:** 2 Critical, 2 High, 5 Info

#### 🔴 CRITICAL (2)

**CODE-EXEC:**

- **Line 917** `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-13_pptx_task1/.claude/skills/co_INST-13_pptx_task1/ooxml/scripts/validation/base.py`
  - Risk: Dynamic code compilation
  - Match: `compile(`

- **Line 83** `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-13_pptx_task1/.claude/skills/co_INST-13_pptx_task1/ooxml/scripts/validation/pptx.py`
  - Risk: Dynamic code compilation
  - Match: `compile(`


#### 🟠 HIGH (2)

**PRIV-ESC:**

- **Line 483** `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-13_pptx_task1/.claude/skills/co_INST-13_pptx_task1/SKILL.md`
  - Risk: Privilege escalation via sudo
  - Match: `sudo`

- **Line 484** `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-13_pptx_task1/.claude/skills/co_INST-13_pptx_task1/SKILL.md`
  - Risk: Privilege escalation via sudo
  - Match: `sudo`


#### 🔵 INFO (5)

**SUBPROCESS:**

- **Line 103** `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-13_pptx_task1/.claude/skills/co_INST-13_pptx_task1/ooxml/scripts/pack.py`
  - Risk: Subprocess call (verify shell=False)
  - Match: `subprocess.run(`

- **Line 153** `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-13_pptx_task1/.claude/skills/co_INST-13_pptx_task1/ooxml/scripts/validation/redlining.py`
  - Risk: Subprocess call (verify shell=False)
  - Match: `subprocess.run(`

- **Line 185** `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-13_pptx_task1/.claude/skills/co_INST-13_pptx_task1/ooxml/scripts/validation/redlining.py`
  - Risk: Subprocess call (verify shell=False)
  - Match: `subprocess.run(`

- **Line 219** `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-13_pptx_task1/.claude/skills/co_INST-13_pptx_task1/scripts/thumbnail.py`
  - Risk: Subprocess call (verify shell=False)
  - Match: `subprocess.run(`

- **Line 237** `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-13_pptx_task1/.claude/skills/co_INST-13_pptx_task1/scripts/thumbnail.py`
  - Risk: Subprocess call (verify shell=False)
  - Match: `subprocess.run(`


### co_INST-13_pptx_task2

**Findings:** 2 Critical, 2 High, 5 Info

#### 🔴 CRITICAL (2)

**CODE-EXEC:**

- **Line 917** `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-13_pptx_task2/.claude/skills/co_INST-13_pptx_task2/ooxml/scripts/validation/base.py`
  - Risk: Dynamic code compilation
  - Match: `compile(`

- **Line 83** `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-13_pptx_task2/.claude/skills/co_INST-13_pptx_task2/ooxml/scripts/validation/pptx.py`
  - Risk: Dynamic code compilation
  - Match: `compile(`


#### 🟠 HIGH (2)

**PRIV-ESC:**

- **Line 483** `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-13_pptx_task2/.claude/skills/co_INST-13_pptx_task2/SKILL.md`
  - Risk: Privilege escalation via sudo
  - Match: `sudo`

- **Line 484** `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-13_pptx_task2/.claude/skills/co_INST-13_pptx_task2/SKILL.md`
  - Risk: Privilege escalation via sudo
  - Match: `sudo`


#### 🔵 INFO (5)

**SUBPROCESS:**

- **Line 103** `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-13_pptx_task2/.claude/skills/co_INST-13_pptx_task2/ooxml/scripts/pack.py`
  - Risk: Subprocess call (verify shell=False)
  - Match: `subprocess.run(`

- **Line 153** `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-13_pptx_task2/.claude/skills/co_INST-13_pptx_task2/ooxml/scripts/validation/redlining.py`
  - Risk: Subprocess call (verify shell=False)
  - Match: `subprocess.run(`

- **Line 185** `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-13_pptx_task2/.claude/skills/co_INST-13_pptx_task2/ooxml/scripts/validation/redlining.py`
  - Risk: Subprocess call (verify shell=False)
  - Match: `subprocess.run(`

- **Line 219** `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-13_pptx_task2/.claude/skills/co_INST-13_pptx_task2/scripts/thumbnail.py`
  - Risk: Subprocess call (verify shell=False)
  - Match: `subprocess.run(`

- **Line 237** `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-13_pptx_task2/.claude/skills/co_INST-13_pptx_task2/scripts/thumbnail.py`
  - Risk: Subprocess call (verify shell=False)
  - Match: `subprocess.run(`


### co_INST-13_xlsx_task6

**Findings:** 0 Critical, 0 High, 5 Info

#### 🔵 INFO (5)

**FILE-OPS:**

- **Line 19** `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-13_xlsx_task6/.claude/skills/co_INST-13_xlsx_task6/recalc.py`
  - Risk: Expands ~ to home directory
  - Match: `os.path.expanduser(`

- **Line 21** `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-13_xlsx_task6/.claude/skills/co_INST-13_xlsx_task6/recalc.py`
  - Risk: Expands ~ to home directory
  - Match: `os.path.expanduser(`

**SUBPROCESS:**

- **Line 31** `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-13_xlsx_task6/.claude/skills/co_INST-13_xlsx_task6/recalc.py`
  - Risk: Subprocess call (verify shell=False)
  - Match: `subprocess.run(`

- **Line 84** `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-13_xlsx_task6/.claude/skills/co_INST-13_xlsx_task6/recalc.py`
  - Risk: Subprocess call (verify shell=False)
  - Match: `subprocess.run(`

- **Line 92** `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-13_xlsx_task6/.claude/skills/co_INST-13_xlsx_task6/recalc.py`
  - Risk: Subprocess call (verify shell=False)
  - Match: `subprocess.run(`


### co_INST-13_xlsx_task7

**Findings:** 0 Critical, 0 High, 5 Info

#### 🔵 INFO (5)

**FILE-OPS:**

- **Line 19** `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-13_xlsx_task7/.claude/skills/co_INST-13_xlsx_task7/recalc.py`
  - Risk: Expands ~ to home directory
  - Match: `os.path.expanduser(`

- **Line 21** `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-13_xlsx_task7/.claude/skills/co_INST-13_xlsx_task7/recalc.py`
  - Risk: Expands ~ to home directory
  - Match: `os.path.expanduser(`

**SUBPROCESS:**

- **Line 31** `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-13_xlsx_task7/.claude/skills/co_INST-13_xlsx_task7/recalc.py`
  - Risk: Subprocess call (verify shell=False)
  - Match: `subprocess.run(`

- **Line 84** `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-13_xlsx_task7/.claude/skills/co_INST-13_xlsx_task7/recalc.py`
  - Risk: Subprocess call (verify shell=False)
  - Match: `subprocess.run(`

- **Line 92** `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-13_xlsx_task7/.claude/skills/co_INST-13_xlsx_task7/recalc.py`
  - Risk: Subprocess call (verify shell=False)
  - Match: `subprocess.run(`


### co_INST-14_hf-llm-trainer

**Findings:** 1 Critical, 0 High, 27 Info

#### 🔴 CRITICAL (1)

**NET-EXFIL:**

- **Line 42** `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-14_hf-llm-trainer/.claude/skills/co_INST-14_hf-llm-trainer/skills/model-trainer/scripts/dataset_inspector.py`
  - Risk: Outbound HTTP request
  - Match: `urllib.request.urlopen(`


#### 🔵 INFO (27)

**ENV-ACCESS:**

- **Line 47** `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-14_hf-llm-trainer/.claude/skills/co_INST-14_hf-llm-trainer/skills/model-trainer/scripts/convert_to_gguf.py`
  - Risk: Reads environment variables
  - Match: `os.environ.`

- **Line 48** `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-14_hf-llm-trainer/.claude/skills/co_INST-14_hf-llm-trainer/skills/model-trainer/scripts/convert_to_gguf.py`
  - Risk: Reads environment variables
  - Match: `os.environ.`

- **Line 49** `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-14_hf-llm-trainer/.claude/skills/co_INST-14_hf-llm-trainer/skills/model-trainer/scripts/convert_to_gguf.py`
  - Risk: Reads environment variables
  - Match: `os.environ.`

- **Line 50** `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-14_hf-llm-trainer/.claude/skills/co_INST-14_hf-llm-trainer/skills/model-trainer/scripts/convert_to_gguf.py`
  - Risk: Reads environment variables
  - Match: `os.environ.`

**SUBPROCESS:**

- **Line 31** `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-14_hf-llm-trainer/.claude/skills/co_INST-14_hf-llm-trainer/skills/model-trainer/references/gguf_conversion.md`
  - Risk: Subprocess call (verify shell=False)
  - Match: `subprocess.run(`

- **Line 32** `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-14_hf-llm-trainer/.claude/skills/co_INST-14_hf-llm-trainer/skills/model-trainer/references/gguf_conversion.md`
  - Risk: Subprocess call (verify shell=False)
  - Match: `subprocess.run(`

- **Line 44** `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-14_hf-llm-trainer/.claude/skills/co_INST-14_hf-llm-trainer/skills/model-trainer/references/gguf_conversion.md`
  - Risk: Subprocess call (verify shell=False)
  - Match: `subprocess.run(`

- **Line 50** `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-14_hf-llm-trainer/.claude/skills/co_INST-14_hf-llm-trainer/skills/model-trainer/references/gguf_conversion.md`
  - Risk: Subprocess call (verify shell=False)
  - Match: `subprocess.run(`

- **Line 100** `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-14_hf-llm-trainer/.claude/skills/co_INST-14_hf-llm-trainer/skills/model-trainer/references/reliability_principles.md`
  - Risk: Subprocess call (verify shell=False)
  - Match: `subprocess.run(`

- **Line 103** `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-14_hf-llm-trainer/.claude/skills/co_INST-14_hf-llm-trainer/skills/model-trainer/references/reliability_principles.md`
  - Risk: Subprocess call (verify shell=False)
  - Match: `subprocess.run(`

- **Line 108** `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-14_hf-llm-trainer/.claude/skills/co_INST-14_hf-llm-trainer/skills/model-trainer/references/reliability_principles.md`
  - Risk: Subprocess call (verify shell=False)
  - Match: `subprocess.run(`

- **Line 183** `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-14_hf-llm-trainer/.claude/skills/co_INST-14_hf-llm-trainer/skills/model-trainer/references/reliability_principles.md`
  - Risk: Subprocess call (verify shell=False)
  - Match: `subprocess.run(`

- **Line 184** `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-14_hf-llm-trainer/.claude/skills/co_INST-14_hf-llm-trainer/skills/model-trainer/references/reliability_principles.md`
  - Risk: Subprocess call (verify shell=False)
  - Match: `subprocess.run(`

- **Line 187** `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-14_hf-llm-trainer/.claude/skills/co_INST-14_hf-llm-trainer/skills/model-trainer/references/reliability_principles.md`
  - Risk: Subprocess call (verify shell=False)
  - Match: `subprocess.run(`

- **Line 188** `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-14_hf-llm-trainer/.claude/skills/co_INST-14_hf-llm-trainer/skills/model-trainer/references/reliability_principles.md`
  - Risk: Subprocess call (verify shell=False)
  - Match: `subprocess.run(`

- **Line 189** `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-14_hf-llm-trainer/.claude/skills/co_INST-14_hf-llm-trainer/skills/model-trainer/references/reliability_principles.md`
  - Risk: Subprocess call (verify shell=False)
  - Match: `subprocess.run(`

- **Line 228** `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-14_hf-llm-trainer/.claude/skills/co_INST-14_hf-llm-trainer/skills/model-trainer/references/reliability_principles.md`
  - Risk: Subprocess call (verify shell=False)
  - Match: `subprocess.run(`

- **Line 232** `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-14_hf-llm-trainer/.claude/skills/co_INST-14_hf-llm-trainer/skills/model-trainer/references/reliability_principles.md`
  - Risk: Subprocess call (verify shell=False)
  - Match: `subprocess.run(`

- **Line 94** `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-14_hf-llm-trainer/.claude/skills/co_INST-14_hf-llm-trainer/skills/model-trainer/scripts/convert_to_gguf.py`
  - Risk: Subprocess call (verify shell=False)
  - Match: `subprocess.run(`

- **Line 99** `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-14_hf-llm-trainer/.claude/skills/co_INST-14_hf-llm-trainer/skills/model-trainer/scripts/convert_to_gguf.py`
  - Risk: Subprocess call (verify shell=False)
  - Match: `subprocess.run(`

- **Line 107** `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-14_hf-llm-trainer/.claude/skills/co_INST-14_hf-llm-trainer/skills/model-trainer/scripts/convert_to_gguf.py`
  - Risk: Subprocess call (verify shell=False)
  - Match: `subprocess.run(`

- **Line 115** `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-14_hf-llm-trainer/.claude/skills/co_INST-14_hf-llm-trainer/skills/model-trainer/scripts/convert_to_gguf.py`
  - Risk: Subprocess call (verify shell=False)
  - Match: `subprocess.run(`

- **Line 121** `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-14_hf-llm-trainer/.claude/skills/co_INST-14_hf-llm-trainer/skills/model-trainer/scripts/convert_to_gguf.py`
  - Risk: Subprocess call (verify shell=False)
  - Match: `subprocess.run(`

- **Line 139** `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-14_hf-llm-trainer/.claude/skills/co_INST-14_hf-llm-trainer/skills/model-trainer/scripts/convert_to_gguf.py`
  - Risk: Subprocess call (verify shell=False)
  - Match: `subprocess.run(`

- **Line 170** `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-14_hf-llm-trainer/.claude/skills/co_INST-14_hf-llm-trainer/skills/model-trainer/scripts/convert_to_gguf.py`
  - Risk: Subprocess call (verify shell=False)
  - Match: `subprocess.run(`

- **Line 179** `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-14_hf-llm-trainer/.claude/skills/co_INST-14_hf-llm-trainer/skills/model-trainer/scripts/convert_to_gguf.py`
  - Risk: Subprocess call (verify shell=False)
  - Match: `subprocess.run(`

- **Line 207** `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-14_hf-llm-trainer/.claude/skills/co_INST-14_hf-llm-trainer/skills/model-trainer/scripts/convert_to_gguf.py`
  - Risk: Subprocess call (verify shell=False)
  - Match: `subprocess.run(`


### co_INST-15_hf-llm-trainer

**Findings:** 1 Critical, 0 High, 27 Info

#### 🔴 CRITICAL (1)

**NET-EXFIL:**

- **Line 42** `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-15_hf-llm-trainer/.claude/skills/co_INST-15_hf-llm-trainer/skills/model-trainer/scripts/dataset_inspector.py`
  - Risk: Outbound HTTP request
  - Match: `urllib.request.urlopen(`


#### 🔵 INFO (27)

**ENV-ACCESS:**

- **Line 47** `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-15_hf-llm-trainer/.claude/skills/co_INST-15_hf-llm-trainer/skills/model-trainer/scripts/convert_to_gguf.py`
  - Risk: Reads environment variables
  - Match: `os.environ.`

- **Line 48** `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-15_hf-llm-trainer/.claude/skills/co_INST-15_hf-llm-trainer/skills/model-trainer/scripts/convert_to_gguf.py`
  - Risk: Reads environment variables
  - Match: `os.environ.`

- **Line 49** `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-15_hf-llm-trainer/.claude/skills/co_INST-15_hf-llm-trainer/skills/model-trainer/scripts/convert_to_gguf.py`
  - Risk: Reads environment variables
  - Match: `os.environ.`

- **Line 50** `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-15_hf-llm-trainer/.claude/skills/co_INST-15_hf-llm-trainer/skills/model-trainer/scripts/convert_to_gguf.py`
  - Risk: Reads environment variables
  - Match: `os.environ.`

**SUBPROCESS:**

- **Line 31** `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-15_hf-llm-trainer/.claude/skills/co_INST-15_hf-llm-trainer/skills/model-trainer/references/gguf_conversion.md`
  - Risk: Subprocess call (verify shell=False)
  - Match: `subprocess.run(`

- **Line 32** `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-15_hf-llm-trainer/.claude/skills/co_INST-15_hf-llm-trainer/skills/model-trainer/references/gguf_conversion.md`
  - Risk: Subprocess call (verify shell=False)
  - Match: `subprocess.run(`

- **Line 44** `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-15_hf-llm-trainer/.claude/skills/co_INST-15_hf-llm-trainer/skills/model-trainer/references/gguf_conversion.md`
  - Risk: Subprocess call (verify shell=False)
  - Match: `subprocess.run(`

- **Line 50** `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-15_hf-llm-trainer/.claude/skills/co_INST-15_hf-llm-trainer/skills/model-trainer/references/gguf_conversion.md`
  - Risk: Subprocess call (verify shell=False)
  - Match: `subprocess.run(`

- **Line 100** `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-15_hf-llm-trainer/.claude/skills/co_INST-15_hf-llm-trainer/skills/model-trainer/references/reliability_principles.md`
  - Risk: Subprocess call (verify shell=False)
  - Match: `subprocess.run(`

- **Line 103** `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-15_hf-llm-trainer/.claude/skills/co_INST-15_hf-llm-trainer/skills/model-trainer/references/reliability_principles.md`
  - Risk: Subprocess call (verify shell=False)
  - Match: `subprocess.run(`

- **Line 108** `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-15_hf-llm-trainer/.claude/skills/co_INST-15_hf-llm-trainer/skills/model-trainer/references/reliability_principles.md`
  - Risk: Subprocess call (verify shell=False)
  - Match: `subprocess.run(`

- **Line 183** `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-15_hf-llm-trainer/.claude/skills/co_INST-15_hf-llm-trainer/skills/model-trainer/references/reliability_principles.md`
  - Risk: Subprocess call (verify shell=False)
  - Match: `subprocess.run(`

- **Line 184** `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-15_hf-llm-trainer/.claude/skills/co_INST-15_hf-llm-trainer/skills/model-trainer/references/reliability_principles.md`
  - Risk: Subprocess call (verify shell=False)
  - Match: `subprocess.run(`

- **Line 187** `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-15_hf-llm-trainer/.claude/skills/co_INST-15_hf-llm-trainer/skills/model-trainer/references/reliability_principles.md`
  - Risk: Subprocess call (verify shell=False)
  - Match: `subprocess.run(`

- **Line 188** `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-15_hf-llm-trainer/.claude/skills/co_INST-15_hf-llm-trainer/skills/model-trainer/references/reliability_principles.md`
  - Risk: Subprocess call (verify shell=False)
  - Match: `subprocess.run(`

- **Line 189** `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-15_hf-llm-trainer/.claude/skills/co_INST-15_hf-llm-trainer/skills/model-trainer/references/reliability_principles.md`
  - Risk: Subprocess call (verify shell=False)
  - Match: `subprocess.run(`

- **Line 228** `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-15_hf-llm-trainer/.claude/skills/co_INST-15_hf-llm-trainer/skills/model-trainer/references/reliability_principles.md`
  - Risk: Subprocess call (verify shell=False)
  - Match: `subprocess.run(`

- **Line 232** `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-15_hf-llm-trainer/.claude/skills/co_INST-15_hf-llm-trainer/skills/model-trainer/references/reliability_principles.md`
  - Risk: Subprocess call (verify shell=False)
  - Match: `subprocess.run(`

- **Line 94** `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-15_hf-llm-trainer/.claude/skills/co_INST-15_hf-llm-trainer/skills/model-trainer/scripts/convert_to_gguf.py`
  - Risk: Subprocess call (verify shell=False)
  - Match: `subprocess.run(`

- **Line 99** `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-15_hf-llm-trainer/.claude/skills/co_INST-15_hf-llm-trainer/skills/model-trainer/scripts/convert_to_gguf.py`
  - Risk: Subprocess call (verify shell=False)
  - Match: `subprocess.run(`

- **Line 107** `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-15_hf-llm-trainer/.claude/skills/co_INST-15_hf-llm-trainer/skills/model-trainer/scripts/convert_to_gguf.py`
  - Risk: Subprocess call (verify shell=False)
  - Match: `subprocess.run(`

- **Line 115** `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-15_hf-llm-trainer/.claude/skills/co_INST-15_hf-llm-trainer/skills/model-trainer/scripts/convert_to_gguf.py`
  - Risk: Subprocess call (verify shell=False)
  - Match: `subprocess.run(`

- **Line 121** `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-15_hf-llm-trainer/.claude/skills/co_INST-15_hf-llm-trainer/skills/model-trainer/scripts/convert_to_gguf.py`
  - Risk: Subprocess call (verify shell=False)
  - Match: `subprocess.run(`

- **Line 139** `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-15_hf-llm-trainer/.claude/skills/co_INST-15_hf-llm-trainer/skills/model-trainer/scripts/convert_to_gguf.py`
  - Risk: Subprocess call (verify shell=False)
  - Match: `subprocess.run(`

- **Line 170** `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-15_hf-llm-trainer/.claude/skills/co_INST-15_hf-llm-trainer/skills/model-trainer/scripts/convert_to_gguf.py`
  - Risk: Subprocess call (verify shell=False)
  - Match: `subprocess.run(`

- **Line 179** `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-15_hf-llm-trainer/.claude/skills/co_INST-15_hf-llm-trainer/skills/model-trainer/scripts/convert_to_gguf.py`
  - Risk: Subprocess call (verify shell=False)
  - Match: `subprocess.run(`

- **Line 207** `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-15_hf-llm-trainer/.claude/skills/co_INST-15_hf-llm-trainer/skills/model-trainer/scripts/convert_to_gguf.py`
  - Risk: Subprocess call (verify shell=False)
  - Match: `subprocess.run(`


### co_INST-16_hf_dataset_creator

**Findings:** 0 Critical, 0 High, 1 Info

#### 🔵 INFO (1)

**ENV-ACCESS:**

- **Line 22** `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-16_hf_dataset_creator/.claude/skills/co_INST-16_hf_dataset_creator/skills/hugging-face-dataset-creator/scripts/dataset_manager.py`
  - Risk: Reads environment variables
  - Match: `os.environ.`


---

## Top Risk Items Requiring Immediate Attention

The following findings are the most severe (critical severity):

- 🔴 `NET-EXFIL` in **apple-music** `active_defense/code/experiment_runs/trustlift_C_20260619_153157/apple-music_attack_cf671a/.claude/skills/apple-music/SKILL.md` L466
  - Outbound HTTP may exfiltrate data
- 🔴 `NET-EXFIL` in **apple-music** `active_defense/code/experiment_runs/trustlift_C_20260619_153157/apple-music_attack_cf671a/.claude/skills/apple-music/SKILL.md` L480
  - Outbound HTTP may exfiltrate data
- 🔴 `CODE-EXEC` in **co_INST-13_pptx_task2** `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-13_pptx_task2/.claude/skills/co_INST-13_pptx_task2/ooxml/scripts/validation/base.py` L917
  - Dynamic code compilation
- 🔴 `CODE-EXEC` in **co_INST-13_pptx_task2** `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-13_pptx_task2/.claude/skills/co_INST-13_pptx_task2/ooxml/scripts/validation/pptx.py` L83
  - Dynamic code compilation
- 🔴 `NET-EXFIL` in **apple-music** `benchmarks/SCR_Bench/SCR-TrustLift/experiment/apple-music/.claude/skills/apple-music/SKILL.md` L466
  - Outbound HTTP may exfiltrate data
- 🔴 `NET-EXFIL` in **apple-music** `benchmarks/SCR_Bench/SCR-TrustLift/experiment/apple-music/.claude/skills/apple-music/SKILL.md` L480
  - Outbound HTTP may exfiltrate data
- 🔴 `CODE-EXEC` in **chrome-devtools** `benchmarks/SCR_Bench/SCR-TrustLift/experiment/chrome-devtools/.claude/skills/chrome-devtools/scripts/lib/selector.js` L41
  - Arbitrary code execution via eval()
- 🔴 `CODE-EXEC` in **chrome-devtools** `benchmarks/SCR_Bench/SCR-TrustLift/experiment/chrome-devtools/.claude/skills/chrome-devtools/scripts/lib/selector.js` L124
  - Arbitrary code execution via eval()
- 🔴 `CODE-EXEC` in **co_INST-13_pptx_task1** `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-13_pptx_task1/.claude/skills/co_INST-13_pptx_task1/ooxml/scripts/validation/base.py` L917
  - Dynamic code compilation
- 🔴 `CODE-EXEC` in **co_INST-13_pptx_task1** `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-13_pptx_task1/.claude/skills/co_INST-13_pptx_task1/ooxml/scripts/validation/pptx.py` L83
  - Dynamic code compilation
- 🔴 `CODE-EXEC` in **co_INST-13_pptx_task0** `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-13_pptx_task0/.claude/skills/co_INST-13_pptx_task0/ooxml/scripts/validation/base.py` L917
  - Dynamic code compilation
- 🔴 `CODE-EXEC` in **co_INST-13_pptx_task0** `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-13_pptx_task0/.claude/skills/co_INST-13_pptx_task0/ooxml/scripts/validation/pptx.py` L83
  - Dynamic code compilation
- 🔴 `NET-EXFIL` in **co_INST-15_hf-llm-trainer** `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-15_hf-llm-trainer/.claude/skills/co_INST-15_hf-llm-trainer/skills/model-trainer/scripts/dataset_inspector.py` L42
  - Outbound HTTP request
- 🔴 `CODE-EXEC` in **co_INST-13_docx_task5** `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-13_docx_task5/.claude/skills/co_INST-13_docx_task5/ooxml/scripts/validation/base.py` L917
  - Dynamic code compilation
- 🔴 `CODE-EXEC` in **co_INST-13_docx_task5** `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-13_docx_task5/.claude/skills/co_INST-13_docx_task5/ooxml/scripts/validation/pptx.py` L83
  - Dynamic code compilation
- 🔴 `CODE-EXEC` in **co_INST-13_docx_task4** `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-13_docx_task4/.claude/skills/co_INST-13_docx_task4/ooxml/scripts/validation/base.py` L917
  - Dynamic code compilation
- 🔴 `CODE-EXEC` in **co_INST-13_docx_task4** `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-13_docx_task4/.claude/skills/co_INST-13_docx_task4/ooxml/scripts/validation/pptx.py` L83
  - Dynamic code compilation
- 🔴 `CODE-EXEC` in **co_INST-13_docx_task3** `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-13_docx_task3/.claude/skills/co_INST-13_docx_task3/ooxml/scripts/validation/base.py` L917
  - Dynamic code compilation
- 🔴 `CODE-EXEC` in **co_INST-13_docx_task3** `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-13_docx_task3/.claude/skills/co_INST-13_docx_task3/ooxml/scripts/validation/pptx.py` L83
  - Dynamic code compilation
- 🔴 `NET-EXFIL` in **co_INST-14_hf-llm-trainer** `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-14_hf-llm-trainer/.claude/skills/co_INST-14_hf-llm-trainer/skills/model-trainer/scripts/dataset_inspector.py` L42
  - Outbound HTTP request

---

## Appendix: Pattern Coverage

### Code - Critical (CRITICAL)

- `\beval\s*\(` — Arbitrary code execution via eval()
- `\bexec\s*\(` — Arbitrary code execution via exec()
- `\bcompile\s*\(` — Dynamic code compilation
- `__import__\s*\(` — Dynamic import loads arbitrary modules
- `importlib\.import_module\s*\(` — Dynamic import loads arbitrary modules
- `os\.system\s*\(` — Shell command injection via os.system()
- `os\.popen\s*\(` — Shell command injection via os.popen()
- `subprocess\.\w+\(.*shell\s*=\s*True` — shell=True enables command injection
- `requests\.(post|put)\s*\(` — Outbound HTTP may exfiltrate data
- `urllib\.request\.urlopen\s*\(` — Outbound HTTP request
- `httpx\.(post|put)\s*\(` — Outbound HTTP via httpx
- `socket\.connect\s*\(` — Raw socket may exfiltrate data
- `aiohttp\.ClientSession\s*\(` — Async HTTP may exfiltrate data
- `['"]~/\.ssh` — Reads SSH keys
- `['"]~/\.aws` — Reads AWS credentials
- `['"]~/\.gnupg` — Reads GPG keys
- `open\s*\(.*\.(pem|key|p12)` — Opens a private key file

### Code - High (HIGH)

- `base64\.b64decode\s*\(` — Base64 decoding may hide payloads
- `codecs\.decode\s*\(` — Codecs decode may obscure strings
- `bytes\.fromhex\s*\(` — Hex decoding may hide payloads
- `chr\s*\(\s*\d+\s*\)\s*\+\s*chr\s*\(` — chr() chain hides intent
- `pickle\.loads?\s*\(` — Pickle deserialization can execute code
- `yaml\.load\s*\([^)]*\)` — yaml.load() without SafeLoader
- `marshal\.loads?\s*\(` — Marshal deserialization can execute code
- `open\s*\(.*((/etc/|/usr/|/var/|/tmp/))` — File access outside skill boundary
- `open\s*\(.*~/\.(bashrc|profile|zshrc)` — Modifies shell config files
- `os\.symlink\s*\(` — Symlinks can redirect to sensitive locations
- `shutil\.(rmtree|move)\s*\(` — Destructive file operation
- `\bsudo\b` — Privilege escalation via sudo
- `chmod\s+777` — World-writable permissions
- `\bcrontab\b` — Cron manipulation can install backdoors

### Code - Informational (INFO)

- `subprocess\.(run|call|check_output|check_call|Popen)\s*\(` — Subprocess call (verify shell=False)
- `os\.environ\s*[\[.]` — Reads environment variables
- `os\.path\.expanduser\s*\(` — Expands ~ to home directory

### Prompt - Critical (CRITICAL)

- `ignore\s+(all\s+)?previous\s+instructions` — Attempts to override system prompt
- `ignore\s+(all\s+)?prior\s+instructions` — Attempts to override system prompt
- `disregard\s+(all\s+)?(previous|prior|above)` — Disregard existing instructions
- `new\s+system\s+prompt` — Injects a replacement system prompt
- `override\s+(the\s+)?system\s+(prompt|instructions)` — Overrides system instructions
- `act\s+as\s+(root|admin|administrator|superuser)` — Escalates to privileged role
- `pretend\s+you\s+(have\s+no|don'?t\s+have)\s+restrictions` — Removes safety restrictions
- `you\s+have\s+no\s+limitations` — Declares AI has no limitations
- `unrestricted\s+mode` — Enables unrestricted mode
- `developer\s+mode\s+enabled` — Activates developer mode bypass
- `\bjailbreak\b` — References jailbreaking
- `send\s+(the\s+)?contents?\s+(of|from)\s+` — Sends file contents externally
- `upload\s+(the\s+)?file\s+to\s+` — Uploads files externally
- `POST\s+to\s+https?://` — POSTs to external URL
- `\bexfiltrate\b` — Explicit data exfiltration
- `transmit\s+(all\s+)?data\s+to\s+` — Transmits data externally

### Prompt - High (HIGH)

- `skip\s+(all\s+)?safety\s+checks?` — Skips safety checks
- `disable\s+(the\s+)?content\s+filter` — Disables content filtering
- `bypass\s+(the\s+)?security` — Bypasses security mechanisms
- `remove\s+(all\s+)?guardrails` — Removes safety guardrails
- `no\s+restrictions?\s+appl(y|ies)` — Declares no restrictions apply
- `(run|execute)\s+any\s+command` — Requests unrestricted command execution
- `full\s+(file\s*system|filesystem)\s+access` — Requests unrestricted filesystem access
- `access\s+to\s+all\s+files` — Requests access to all files
- `root\s+access\s+required` — Claims root access is required
- `<!--\s*(system|instruction|command|execute|override|ignore)` — HTML comment contains hidden directive

### Prompt - Informational (INFO)

- `you\s+must\s+(always|never)\s+` — Strong directive language
- `do\s+not\s+(ever|under\s+any\s+circumstances)\s+` — Absolute prohibition
- `from\s+now\s+on\s+(you|your)\s+` — Attempts to permanently alter AI behavior
- `you\s+are\s+now\s+(a|an)\s+` — Attempts to redefine AI identity

