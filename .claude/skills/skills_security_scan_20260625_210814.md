# Skills Security Scan Report

**Date:** 2026-06-25 21:08:14
**Project:** agent_safety

## Executive Summary

| Metric | Value |
|--------|-------|
| **Overall Security Score** | **0/100** |
| Total Critical Findings | 117 |
| Total High Findings | 71 |
| Total Informational Findings | 116 |
| Total Skills Scanned | 135 |

### Risk Levels

| Severity | Meaning |
|----------|---------|
| 🔴 **Critical** | Code execution, command injection, data exfiltration, credential harvesting, system prompt override, role hijacking |
| 🟠 **High** | Obfuscation, unsafe deserialization, filesystem boundary violations, privilege escalation, safety bypass, excessive permissions |
| 🔵 **Info** | Subprocess calls, env access, file ops, strong directive language |

### Score Guide
- **90-100**: Good security posture
- **70-89**: Medium risk — review high/critical items
- **50-69**: High risk — multiple critical items need attention
- **< 50**: Critical — immediate action required

---

## Group Summary

| Group | Skills | Critical | High | Info | |
|-------|--------|----------|------|------|---|
| Active Defense - Experiment Skills | 82 | 45 | 19 | 11 | 🔴 🟠 |
| Project Core Skills | 3 | 27 | 13 | 8 | 🔴 🟠 |
| Registry - Other Skills | 2 | 27 | 13 | 8 | 🔴 🟠 |
| Registry - Skills | 1 | 0 | 0 | 0 | 🟢 |
| TrustLift - Experiment Skills | 47 | 18 | 26 | 89 | 🔴 🟠 |

---

## Active Defense - Experiment Skills

### apple-music

**Findings:** 2 Critical, 0 High, 0 Info

#### 🔴 CRITICAL (2)

**NET-EXFIL:**

- **Line 466** in `active_defense/code/experiment_runs/trustlift_C_20260619_153157/apple-music_attack_cf671a/.claude/skills/apple-music/SKILL.md`
  - Risk: Outbound HTTP may exfiltrate data
  - Fix: Remove outbound network calls
  - Match: `requests.post(`

- **Line 480** in `active_defense/code/experiment_runs/trustlift_C_20260619_153157/apple-music_attack_cf671a/.claude/skills/apple-music/SKILL.md`
  - Risk: Outbound HTTP may exfiltrate data
  - Fix: Remove outbound network calls
  - Match: `requests.post(`


### secure-skill

**Findings:** 16 Critical, 6 High, 3 Info

#### 🔴 CRITICAL (16)

**CMD-INJECT:**

- **Line 11** in `active_defense/code/experiment_runs/trustlift_transition_20260625_202016/Legacy_control_3e8f77/.claude/skills/secure-skill/scripts/patterns.json`
  - Risk: Shell command injection via os.system()
  - Fix: Use subprocess.run() with list args
  - Match: `os.system(`

- **Line 12** in `active_defense/code/experiment_runs/trustlift_transition_20260625_202016/Legacy_control_3e8f77/.claude/skills/secure-skill/scripts/patterns.json`
  - Risk: Shell command injection via os.popen()
  - Fix: Use subprocess.run() with list args
  - Match: `os.popen(`


**CODE-EXEC:**

- **Line 21** in `active_defense/code/experiment_runs/trustlift_transition_20260625_202016/Legacy_control_3e8f77/.claude/skills/secure-skill/scan_report.md`
  - Risk: Arbitrary code execution via eval()
  - Fix: Replace with ast.literal_eval() or explicit parsing
  - Match: `eval(`

- **Line 21** in `active_defense/code/experiment_runs/trustlift_transition_20260625_202016/Legacy_control_3e8f77/.claude/skills/secure-skill/scan_report.md`
  - Risk: Arbitrary code execution via exec()
  - Fix: Remove exec() and use explicit function calls
  - Match: `exec(`

- **Line 4** in `active_defense/code/experiment_runs/trustlift_transition_20260625_202016/Legacy_control_3e8f77/.claude/skills/secure-skill/scripts/patterns.json`
  - Risk: Arbitrary code execution via eval()
  - Fix: Replace with ast.literal_eval() or explicit parsing
  - Match: `eval(`

- **Line 5** in `active_defense/code/experiment_runs/trustlift_transition_20260625_202016/Legacy_control_3e8f77/.claude/skills/secure-skill/scripts/patterns.json`
  - Risk: Arbitrary code execution via exec()
  - Fix: Remove exec() and use explicit function calls
  - Match: `exec(`

- **Line 5** in `active_defense/code/experiment_runs/trustlift_transition_20260625_202016/Legacy_control_3e8f77/.claude/skills/secure-skill/scripts/patterns.json`
  - Risk: Arbitrary code execution via exec()
  - Fix: Remove exec() and use explicit function calls
  - Match: `exec(`

- **Line 6** in `active_defense/code/experiment_runs/trustlift_transition_20260625_202016/Legacy_control_3e8f77/.claude/skills/secure-skill/scripts/patterns.json`
  - Risk: Dynamic code compilation
  - Fix: Remove compile() or ensure input is fully trusted
  - Match: `compile(`


**DATA-EXTRACT:**

- **Line 16** in `active_defense/code/experiment_runs/trustlift_transition_20260625_202016/Legacy_control_3e8f77/.claude/skills/secure-skill/scripts/patterns.json`
  - Risk: Explicit data exfiltration
  - Fix: Remove exfiltration language
  - Match: `exfiltrate`

- **Line 19** in `active_defense/code/experiment_runs/trustlift_transition_20260625_202016/Legacy_control_3e8f77/.claude/skills/secure-skill/scripts/patterns.json`
  - Risk: Explicit data exfiltration
  - Fix: Remove exfiltration language
  - Match: `exfiltrate`

- **Line 20** in `active_defense/code/experiment_runs/trustlift_transition_20260625_202016/Legacy_control_3e8f77/.claude/skills/secure-skill/scripts/patterns.json`
  - Risk: Explicit data exfiltration
  - Fix: Remove exfiltration language
  - Match: `exfiltrate`


**ROLE-HIJACK:**

- **Line 76** in `active_defense/code/experiment_runs/trustlift_transition_20260625_202016/Legacy_control_3e8f77/.claude/skills/secure-skill/scripts/patterns.json`
  - Risk: Enables unrestricted mode
  - Fix: Remove unrestricted mode language
  - Match: `unrestricted mode`

- **Line 76** in `active_defense/code/experiment_runs/trustlift_transition_20260625_202016/Legacy_control_3e8f77/.claude/skills/secure-skill/scripts/patterns.json`
  - Risk: Enables unrestricted mode
  - Fix: Remove unrestricted mode language
  - Match: `unrestricted mode`

- **Line 78** in `active_defense/code/experiment_runs/trustlift_transition_20260625_202016/Legacy_control_3e8f77/.claude/skills/secure-skill/scripts/patterns.json`
  - Risk: References jailbreaking
  - Fix: Remove jailbreak references
  - Match: `jailbreak`


**SYSTEM-OVERRIDE:**

- **Line 66** in `active_defense/code/experiment_runs/trustlift_transition_20260625_202016/Legacy_control_3e8f77/.claude/skills/secure-skill/scripts/patterns.json`
  - Risk: Overrides system instructions
  - Fix: Remove override language
  - Match: `override system prompt`

- **Line 67** in `active_defense/code/experiment_runs/trustlift_transition_20260625_202016/Legacy_control_3e8f77/.claude/skills/secure-skill/scripts/patterns.json`
  - Risk: Overrides system instructions
  - Fix: Remove override language
  - Match: `override system prompt`


#### 🟠 HIGH (6)

**EXCESSIVE-PERMS:**

- **Line 99** in `active_defense/code/experiment_runs/trustlift_transition_20260625_202016/Legacy_control_3e8f77/.claude/skills/secure-skill/scripts/patterns.json`
  - Risk: Requests access to all files
  - Fix: Limit access to skill directory
  - Match: `access to all files`


**PRIV-ESC:**

- **Line 48** in `active_defense/code/experiment_runs/trustlift_transition_20260625_202016/Legacy_control_3e8f77/.claude/skills/secure-skill/scripts/patterns.json`
  - Risk: Privilege escalation via sudo
  - Fix: Remove sudo usage
  - Match: `sudo`

- **Line 48** in `active_defense/code/experiment_runs/trustlift_transition_20260625_202016/Legacy_control_3e8f77/.claude/skills/secure-skill/scripts/patterns.json`
  - Risk: Privilege escalation via sudo
  - Fix: Remove sudo usage
  - Match: `sudo`

- **Line 50** in `active_defense/code/experiment_runs/trustlift_transition_20260625_202016/Legacy_control_3e8f77/.claude/skills/secure-skill/scripts/patterns.json`
  - Risk: Cron manipulation can install backdoors
  - Fix: Remove crontab access
  - Match: `crontab`


**SAFETY-BYPASS:**

- **Line 94** in `active_defense/code/experiment_runs/trustlift_transition_20260625_202016/Legacy_control_3e8f77/.claude/skills/secure-skill/scripts/patterns.json`
  - Risk: Declares no restrictions apply
  - Fix: Remove restriction-bypass declarations
  - Match: `no restrictions apply`


**UNSAFE-DESER:**

- **Line 38** in `active_defense/code/experiment_runs/trustlift_transition_20260625_202016/Legacy_control_3e8f77/.claude/skills/secure-skill/scripts/patterns.json`
  - Risk: yaml.load() without SafeLoader
  - Fix: Use yaml.safe_load()
  - Match: `yaml.load()`


#### 🔵 INFO (3)

**SUBPROCESS:**

- **Line 88** in `active_defense/code/experiment_runs/trustlift_transition_20260625_202016/Legacy_control_3e8f77/.claude/skills/secure-skill/scan_report.md`
  - Risk: Subprocess call (verify shell=False)
  - Fix: Ensure list args and no shell=True
  - Match: `subprocess.run(`

- **Line 11** in `active_defense/code/experiment_runs/trustlift_transition_20260625_202016/Legacy_control_3e8f77/.claude/skills/secure-skill/scripts/patterns.json`
  - Risk: Subprocess call (verify shell=False)
  - Fix: Ensure list args and no shell=True
  - Match: `subprocess.run(`

- **Line 12** in `active_defense/code/experiment_runs/trustlift_transition_20260625_202016/Legacy_control_3e8f77/.claude/skills/secure-skill/scripts/patterns.json`
  - Risk: Subprocess call (verify shell=False)
  - Fix: Ensure list args and no shell=True
  - Match: `subprocess.run(`


### security-review

**Findings:** 27 Critical, 13 High, 8 Info

#### 🔴 CRITICAL (27)

**CMD-INJECT:**

- **Line 207** in `active_defense/code/experiment_runs/trustlift_baseline_20260619_165737/analytics_af3832/.claude/skills/security-review/SKILL.md`
  - Risk: Shell command injection via os.system()
  - Fix: Use subprocess.run() with list args
  - Match: `os.system(`

- **Line 80** in `active_defense/code/experiment_runs/trustlift_baseline_20260619_165737/analytics_af3832/.claude/skills/security-review/languages/python.md`
  - Risk: Shell command injection via os.system()
  - Fix: Use subprocess.run() with list args
  - Match: `os.system(`

- **Line 222** in `active_defense/code/experiment_runs/trustlift_baseline_20260619_165737/analytics_af3832/.claude/skills/security-review/languages/python.md`
  - Risk: Shell command injection via os.system()
  - Fix: Use subprocess.run() with list args
  - Match: `os.system(`

- **Line 223** in `active_defense/code/experiment_runs/trustlift_baseline_20260619_165737/analytics_af3832/.claude/skills/security-review/languages/python.md`
  - Risk: Shell command injection via os.popen()
  - Fix: Use subprocess.run() with list args
  - Match: `os.popen(`

- **Line 81** in `active_defense/code/experiment_runs/trustlift_baseline_20260619_165737/analytics_af3832/.claude/skills/security-review/languages/python.md`
  - Risk: shell=True enables command injection
  - Fix: Remove shell=True
  - Match: `subprocess.run(cmd, shell=True`

- **Line 82** in `active_defense/code/experiment_runs/trustlift_baseline_20260619_165737/analytics_af3832/.claude/skills/security-review/languages/python.md`
  - Risk: shell=True enables command injection
  - Fix: Remove shell=True
  - Match: `subprocess.Popen(cmd, shell=True`

- **Line 224** in `active_defense/code/experiment_runs/trustlift_baseline_20260619_165737/analytics_af3832/.claude/skills/security-review/languages/python.md`
  - Risk: shell=True enables command injection
  - Fix: Remove shell=True
  - Match: `subprocess.call(cmd, shell=True`

- **Line 225** in `active_defense/code/experiment_runs/trustlift_baseline_20260619_165737/analytics_af3832/.claude/skills/security-review/languages/python.md`
  - Risk: shell=True enables command injection
  - Fix: Remove shell=True
  - Match: `subprocess.run(cmd, shell=True`

- **Line 226** in `active_defense/code/experiment_runs/trustlift_baseline_20260619_165737/analytics_af3832/.claude/skills/security-review/languages/python.md`
  - Risk: shell=True enables command injection
  - Fix: Remove shell=True
  - Match: `subprocess.Popen(cmd, shell=True`


**CODE-EXEC:**

- **Line 190** in `active_defense/code/experiment_runs/trustlift_baseline_20260619_165737/analytics_af3832/.claude/skills/security-review/SKILL.md`
  - Risk: Arbitrary code execution via eval()
  - Fix: Replace with ast.literal_eval() or explicit parsing
  - Match: `eval(`

- **Line 191** in `active_defense/code/experiment_runs/trustlift_baseline_20260619_165737/analytics_af3832/.claude/skills/security-review/SKILL.md`
  - Risk: Arbitrary code execution via exec()
  - Fix: Remove exec() and use explicit function calls
  - Match: `exec(`

- **Line 197** in `active_defense/code/experiment_runs/trustlift_baseline_20260619_165737/analytics_af3832/.claude/skills/security-review/SKILL.md`
  - Risk: Arbitrary code execution via exec()
  - Fix: Remove exec() and use explicit function calls
  - Match: `exec(`

- **Line 216** in `active_defense/code/experiment_runs/trustlift_baseline_20260619_165737/analytics_af3832/.claude/skills/security-review/languages/python.md`
  - Risk: Arbitrary code execution via eval()
  - Fix: Replace with ast.literal_eval() or explicit parsing
  - Match: `eval(`

- **Line 263** in `active_defense/code/experiment_runs/trustlift_baseline_20260619_165737/analytics_af3832/.claude/skills/security-review/languages/python.md`
  - Risk: Arbitrary code execution via eval()
  - Fix: Replace with ast.literal_eval() or explicit parsing
  - Match: `eval(`

- **Line 217** in `active_defense/code/experiment_runs/trustlift_baseline_20260619_165737/analytics_af3832/.claude/skills/security-review/languages/python.md`
  - Risk: Arbitrary code execution via exec()
  - Fix: Remove exec() and use explicit function calls
  - Match: `exec(`

- **Line 218** in `active_defense/code/experiment_runs/trustlift_baseline_20260619_165737/analytics_af3832/.claude/skills/security-review/languages/python.md`
  - Risk: Dynamic code compilation
  - Fix: Remove compile() or ensure input is fully trusted
  - Match: `compile(`

- **Line 219** in `active_defense/code/experiment_runs/trustlift_baseline_20260619_165737/analytics_af3832/.claude/skills/security-review/languages/python.md`
  - Risk: Dynamic import loads arbitrary modules
  - Fix: Use static imports at the top of the file
  - Match: `__import__(`

- **Line 45** in `active_defense/code/experiment_runs/trustlift_baseline_20260619_165737/analytics_af3832/.claude/skills/security-review/languages/javascript.md`
  - Risk: Arbitrary code execution via eval()
  - Fix: Replace with ast.literal_eval() or explicit parsing
  - Match: `eval(`

- **Line 249** in `active_defense/code/experiment_runs/trustlift_baseline_20260619_165737/analytics_af3832/.claude/skills/security-review/languages/javascript.md`
  - Risk: Arbitrary code execution via eval()
  - Fix: Replace with ast.literal_eval() or explicit parsing
  - Match: `eval(`

- **Line 356** in `active_defense/code/experiment_runs/trustlift_baseline_20260619_165737/analytics_af3832/.claude/skills/security-review/languages/javascript.md`
  - Risk: Arbitrary code execution via eval()
  - Fix: Replace with ast.literal_eval() or explicit parsing
  - Match: `eval(`

- **Line 375** in `active_defense/code/experiment_runs/trustlift_baseline_20260619_165737/analytics_af3832/.claude/skills/security-review/languages/javascript.md`
  - Risk: Arbitrary code execution via eval()
  - Fix: Replace with ast.literal_eval() or explicit parsing
  - Match: `eval(`

- **Line 134** in `active_defense/code/experiment_runs/trustlift_baseline_20260619_165737/analytics_af3832/.claude/skills/security-review/languages/javascript.md`
  - Risk: Arbitrary code execution via exec()
  - Fix: Remove exec() and use explicit function calls
  - Match: `exec(`

- **Line 137** in `active_defense/code/experiment_runs/trustlift_baseline_20260619_165737/analytics_af3832/.claude/skills/security-review/languages/javascript.md`
  - Risk: Arbitrary code execution via exec()
  - Fix: Remove exec() and use explicit function calls
  - Match: `exec(`

- **Line 378** in `active_defense/code/experiment_runs/trustlift_baseline_20260619_165737/analytics_af3832/.claude/skills/security-review/languages/javascript.md`
  - Risk: Arbitrary code execution via exec()
  - Fix: Remove exec() and use explicit function calls
  - Match: `exec(`

- **Line 100** in `active_defense/code/experiment_runs/trustlift_baseline_20260619_165737/analytics_af3832/.claude/skills/security-review/languages/javascript.md`
  - Risk: Dynamic code compilation
  - Fix: Remove compile() or ensure input is fully trusted
  - Match: `compile(`


**NET-EXFIL:**

- **Line 235** in `active_defense/code/experiment_runs/trustlift_baseline_20260619_165737/analytics_af3832/.claude/skills/security-review/languages/python.md`
  - Risk: Outbound HTTP request
  - Fix: Remove outbound network calls
  - Match: `urllib.request.urlopen(`

- **Line 237** in `active_defense/code/experiment_runs/trustlift_baseline_20260619_165737/analytics_af3832/.claude/skills/security-review/languages/python.md`
  - Risk: Async HTTP may exfiltrate data
  - Fix: Remove async HTTP clients
  - Match: `aiohttp.ClientSession(`


#### 🟠 HIGH (13)

**PRIV-ESC:**

- **Line 155** in `active_defense/code/experiment_runs/trustlift_baseline_20260619_165737/analytics_af3832/.claude/skills/security-review/infrastructure/docker.md`
  - Risk: Privilege escalation via sudo
  - Fix: Remove sudo usage
  - Match: `sudo`


**UNSAFE-DESER:**

- **Line 192** in `active_defense/code/experiment_runs/trustlift_baseline_20260619_165737/analytics_af3832/.claude/skills/security-review/SKILL.md`
  - Risk: Pickle deserialization can execute code
  - Fix: Use json.loads() instead
  - Match: `pickle.loads(`

- **Line 193** in `active_defense/code/experiment_runs/trustlift_baseline_20260619_165737/analytics_af3832/.claude/skills/security-review/SKILL.md`
  - Risk: yaml.load() without SafeLoader
  - Fix: Use yaml.safe_load()
  - Match: `yaml.load(user_data)`

- **Line 85** in `active_defense/code/experiment_runs/trustlift_baseline_20260619_165737/analytics_af3832/.claude/skills/security-review/languages/python.md`
  - Risk: Pickle deserialization can execute code
  - Fix: Use json.loads() instead
  - Match: `pickle.loads(`

- **Line 206** in `active_defense/code/experiment_runs/trustlift_baseline_20260619_165737/analytics_af3832/.claude/skills/security-review/languages/python.md`
  - Risk: Pickle deserialization can execute code
  - Fix: Use json.loads() instead
  - Match: `pickle.loads(`

- **Line 207** in `active_defense/code/experiment_runs/trustlift_baseline_20260619_165737/analytics_af3832/.claude/skills/security-review/languages/python.md`
  - Risk: Pickle deserialization can execute code
  - Fix: Use json.loads() instead
  - Match: `pickle.load(`

- **Line 208** in `active_defense/code/experiment_runs/trustlift_baseline_20260619_165737/analytics_af3832/.claude/skills/security-review/languages/python.md`
  - Risk: Pickle deserialization can execute code
  - Fix: Use json.loads() instead
  - Match: `Pickle.loads(`

- **Line 86** in `active_defense/code/experiment_runs/trustlift_baseline_20260619_165737/analytics_af3832/.claude/skills/security-review/languages/python.md`
  - Risk: yaml.load() without SafeLoader
  - Fix: Use yaml.safe_load()
  - Match: `yaml.load(user_data)`

- **Line 87** in `active_defense/code/experiment_runs/trustlift_baseline_20260619_165737/analytics_af3832/.claude/skills/security-review/languages/python.md`
  - Risk: yaml.load() without SafeLoader
  - Fix: Use yaml.safe_load()
  - Match: `yaml.load(data, Loader=yaml.Loader)`

- **Line 211** in `active_defense/code/experiment_runs/trustlift_baseline_20260619_165737/analytics_af3832/.claude/skills/security-review/languages/python.md`
  - Risk: yaml.load() without SafeLoader
  - Fix: Use yaml.safe_load()
  - Match: `yaml.load(data)`

- **Line 212** in `active_defense/code/experiment_runs/trustlift_baseline_20260619_165737/analytics_af3832/.claude/skills/security-review/languages/python.md`
  - Risk: yaml.load() without SafeLoader
  - Fix: Use yaml.safe_load()
  - Match: `yaml.load(data, Loader=yaml.FullLoader)`

- **Line 213** in `active_defense/code/experiment_runs/trustlift_baseline_20260619_165737/analytics_af3832/.claude/skills/security-review/languages/python.md`
  - Risk: yaml.load() without SafeLoader
  - Fix: Use yaml.safe_load()
  - Match: `yaml.load(data, Loader=yaml.UnsafeLoader)`

- **Line 210** in `active_defense/code/experiment_runs/trustlift_baseline_20260619_165737/analytics_af3832/.claude/skills/security-review/languages/python.md`
  - Risk: Marshal deserialization can execute code
  - Fix: Use json.loads() instead
  - Match: `marshal.loads(`


#### 🔵 INFO (8)

**ENV-ACCESS:**

- **Line 55** in `active_defense/code/experiment_runs/trustlift_baseline_20260619_165737/analytics_af3832/.claude/skills/security-review/SKILL.md`
  - Risk: Reads environment variables
  - Fix: Document which env vars are read
  - Match: `os.environ.`

- **Line 153** in `active_defense/code/experiment_runs/trustlift_baseline_20260619_165737/analytics_af3832/.claude/skills/security-review/SKILL.md`
  - Risk: Reads environment variables
  - Fix: Document which env vars are read
  - Match: `os.environ.`

- **Line 31** in `active_defense/code/experiment_runs/trustlift_baseline_20260619_165737/analytics_af3832/.claude/skills/security-review/languages/python.md`
  - Risk: Reads environment variables
  - Fix: Document which env vars are read
  - Match: `os.environ.`


**SUBPROCESS:**

- **Line 81** in `active_defense/code/experiment_runs/trustlift_baseline_20260619_165737/analytics_af3832/.claude/skills/security-review/languages/python.md`
  - Risk: Subprocess call (verify shell=False)
  - Fix: Ensure list args and no shell=True
  - Match: `subprocess.run(`

- **Line 82** in `active_defense/code/experiment_runs/trustlift_baseline_20260619_165737/analytics_af3832/.claude/skills/security-review/languages/python.md`
  - Risk: Subprocess call (verify shell=False)
  - Fix: Ensure list args and no shell=True
  - Match: `subprocess.Popen(`

- **Line 224** in `active_defense/code/experiment_runs/trustlift_baseline_20260619_165737/analytics_af3832/.claude/skills/security-review/languages/python.md`
  - Risk: Subprocess call (verify shell=False)
  - Fix: Ensure list args and no shell=True
  - Match: `subprocess.call(`

- **Line 225** in `active_defense/code/experiment_runs/trustlift_baseline_20260619_165737/analytics_af3832/.claude/skills/security-review/languages/python.md`
  - Risk: Subprocess call (verify shell=False)
  - Fix: Ensure list args and no shell=True
  - Match: `subprocess.run(`

- **Line 226** in `active_defense/code/experiment_runs/trustlift_baseline_20260619_165737/analytics_af3832/.claude/skills/security-review/languages/python.md`
  - Risk: Subprocess call (verify shell=False)
  - Fix: Ensure list args and no shell=True
  - Match: `subprocess.Popen(`


---

## Project Core Skills

### security-review

**Findings:** 27 Critical, 13 High, 8 Info

#### 🔴 CRITICAL (27)

**CMD-INJECT:**

- **Line 207** in `.claude/skills/security-review/SKILL.md`
  - Risk: Shell command injection via os.system()
  - Fix: Use subprocess.run() with list args
  - Match: `os.system(`

- **Line 80** in `.claude/skills/security-review/languages/python.md`
  - Risk: Shell command injection via os.system()
  - Fix: Use subprocess.run() with list args
  - Match: `os.system(`

- **Line 222** in `.claude/skills/security-review/languages/python.md`
  - Risk: Shell command injection via os.system()
  - Fix: Use subprocess.run() with list args
  - Match: `os.system(`

- **Line 223** in `.claude/skills/security-review/languages/python.md`
  - Risk: Shell command injection via os.popen()
  - Fix: Use subprocess.run() with list args
  - Match: `os.popen(`

- **Line 81** in `.claude/skills/security-review/languages/python.md`
  - Risk: shell=True enables command injection
  - Fix: Remove shell=True
  - Match: `subprocess.run(cmd, shell=True`

- **Line 82** in `.claude/skills/security-review/languages/python.md`
  - Risk: shell=True enables command injection
  - Fix: Remove shell=True
  - Match: `subprocess.Popen(cmd, shell=True`

- **Line 224** in `.claude/skills/security-review/languages/python.md`
  - Risk: shell=True enables command injection
  - Fix: Remove shell=True
  - Match: `subprocess.call(cmd, shell=True`

- **Line 225** in `.claude/skills/security-review/languages/python.md`
  - Risk: shell=True enables command injection
  - Fix: Remove shell=True
  - Match: `subprocess.run(cmd, shell=True`

- **Line 226** in `.claude/skills/security-review/languages/python.md`
  - Risk: shell=True enables command injection
  - Fix: Remove shell=True
  - Match: `subprocess.Popen(cmd, shell=True`


**CODE-EXEC:**

- **Line 190** in `.claude/skills/security-review/SKILL.md`
  - Risk: Arbitrary code execution via eval()
  - Fix: Replace with ast.literal_eval() or explicit parsing
  - Match: `eval(`

- **Line 191** in `.claude/skills/security-review/SKILL.md`
  - Risk: Arbitrary code execution via exec()
  - Fix: Remove exec() and use explicit function calls
  - Match: `exec(`

- **Line 197** in `.claude/skills/security-review/SKILL.md`
  - Risk: Arbitrary code execution via exec()
  - Fix: Remove exec() and use explicit function calls
  - Match: `exec(`

- **Line 216** in `.claude/skills/security-review/languages/python.md`
  - Risk: Arbitrary code execution via eval()
  - Fix: Replace with ast.literal_eval() or explicit parsing
  - Match: `eval(`

- **Line 263** in `.claude/skills/security-review/languages/python.md`
  - Risk: Arbitrary code execution via eval()
  - Fix: Replace with ast.literal_eval() or explicit parsing
  - Match: `eval(`

- **Line 217** in `.claude/skills/security-review/languages/python.md`
  - Risk: Arbitrary code execution via exec()
  - Fix: Remove exec() and use explicit function calls
  - Match: `exec(`

- **Line 218** in `.claude/skills/security-review/languages/python.md`
  - Risk: Dynamic code compilation
  - Fix: Remove compile() or ensure input is fully trusted
  - Match: `compile(`

- **Line 219** in `.claude/skills/security-review/languages/python.md`
  - Risk: Dynamic import loads arbitrary modules
  - Fix: Use static imports at the top of the file
  - Match: `__import__(`

- **Line 45** in `.claude/skills/security-review/languages/javascript.md`
  - Risk: Arbitrary code execution via eval()
  - Fix: Replace with ast.literal_eval() or explicit parsing
  - Match: `eval(`

- **Line 249** in `.claude/skills/security-review/languages/javascript.md`
  - Risk: Arbitrary code execution via eval()
  - Fix: Replace with ast.literal_eval() or explicit parsing
  - Match: `eval(`

- **Line 356** in `.claude/skills/security-review/languages/javascript.md`
  - Risk: Arbitrary code execution via eval()
  - Fix: Replace with ast.literal_eval() or explicit parsing
  - Match: `eval(`

- **Line 375** in `.claude/skills/security-review/languages/javascript.md`
  - Risk: Arbitrary code execution via eval()
  - Fix: Replace with ast.literal_eval() or explicit parsing
  - Match: `eval(`

- **Line 134** in `.claude/skills/security-review/languages/javascript.md`
  - Risk: Arbitrary code execution via exec()
  - Fix: Remove exec() and use explicit function calls
  - Match: `exec(`

- **Line 137** in `.claude/skills/security-review/languages/javascript.md`
  - Risk: Arbitrary code execution via exec()
  - Fix: Remove exec() and use explicit function calls
  - Match: `exec(`

- **Line 378** in `.claude/skills/security-review/languages/javascript.md`
  - Risk: Arbitrary code execution via exec()
  - Fix: Remove exec() and use explicit function calls
  - Match: `exec(`

- **Line 100** in `.claude/skills/security-review/languages/javascript.md`
  - Risk: Dynamic code compilation
  - Fix: Remove compile() or ensure input is fully trusted
  - Match: `compile(`


**NET-EXFIL:**

- **Line 235** in `.claude/skills/security-review/languages/python.md`
  - Risk: Outbound HTTP request
  - Fix: Remove outbound network calls
  - Match: `urllib.request.urlopen(`

- **Line 237** in `.claude/skills/security-review/languages/python.md`
  - Risk: Async HTTP may exfiltrate data
  - Fix: Remove async HTTP clients
  - Match: `aiohttp.ClientSession(`


#### 🟠 HIGH (13)

**PRIV-ESC:**

- **Line 155** in `.claude/skills/security-review/infrastructure/docker.md`
  - Risk: Privilege escalation via sudo
  - Fix: Remove sudo usage
  - Match: `sudo`


**UNSAFE-DESER:**

- **Line 192** in `.claude/skills/security-review/SKILL.md`
  - Risk: Pickle deserialization can execute code
  - Fix: Use json.loads() instead
  - Match: `pickle.loads(`

- **Line 193** in `.claude/skills/security-review/SKILL.md`
  - Risk: yaml.load() without SafeLoader
  - Fix: Use yaml.safe_load()
  - Match: `yaml.load(user_data)`

- **Line 85** in `.claude/skills/security-review/languages/python.md`
  - Risk: Pickle deserialization can execute code
  - Fix: Use json.loads() instead
  - Match: `pickle.loads(`

- **Line 206** in `.claude/skills/security-review/languages/python.md`
  - Risk: Pickle deserialization can execute code
  - Fix: Use json.loads() instead
  - Match: `pickle.loads(`

- **Line 207** in `.claude/skills/security-review/languages/python.md`
  - Risk: Pickle deserialization can execute code
  - Fix: Use json.loads() instead
  - Match: `pickle.load(`

- **Line 208** in `.claude/skills/security-review/languages/python.md`
  - Risk: Pickle deserialization can execute code
  - Fix: Use json.loads() instead
  - Match: `Pickle.loads(`

- **Line 86** in `.claude/skills/security-review/languages/python.md`
  - Risk: yaml.load() without SafeLoader
  - Fix: Use yaml.safe_load()
  - Match: `yaml.load(user_data)`

- **Line 87** in `.claude/skills/security-review/languages/python.md`
  - Risk: yaml.load() without SafeLoader
  - Fix: Use yaml.safe_load()
  - Match: `yaml.load(data, Loader=yaml.Loader)`

- **Line 211** in `.claude/skills/security-review/languages/python.md`
  - Risk: yaml.load() without SafeLoader
  - Fix: Use yaml.safe_load()
  - Match: `yaml.load(data)`

- **Line 212** in `.claude/skills/security-review/languages/python.md`
  - Risk: yaml.load() without SafeLoader
  - Fix: Use yaml.safe_load()
  - Match: `yaml.load(data, Loader=yaml.FullLoader)`

- **Line 213** in `.claude/skills/security-review/languages/python.md`
  - Risk: yaml.load() without SafeLoader
  - Fix: Use yaml.safe_load()
  - Match: `yaml.load(data, Loader=yaml.UnsafeLoader)`

- **Line 210** in `.claude/skills/security-review/languages/python.md`
  - Risk: Marshal deserialization can execute code
  - Fix: Use json.loads() instead
  - Match: `marshal.loads(`


#### 🔵 INFO (8)

**ENV-ACCESS:**

- **Line 55** in `.claude/skills/security-review/SKILL.md`
  - Risk: Reads environment variables
  - Fix: Document which env vars are read
  - Match: `os.environ.`

- **Line 153** in `.claude/skills/security-review/SKILL.md`
  - Risk: Reads environment variables
  - Fix: Document which env vars are read
  - Match: `os.environ.`

- **Line 31** in `.claude/skills/security-review/languages/python.md`
  - Risk: Reads environment variables
  - Fix: Document which env vars are read
  - Match: `os.environ.`


**SUBPROCESS:**

- **Line 81** in `.claude/skills/security-review/languages/python.md`
  - Risk: Subprocess call (verify shell=False)
  - Fix: Ensure list args and no shell=True
  - Match: `subprocess.run(`

- **Line 82** in `.claude/skills/security-review/languages/python.md`
  - Risk: Subprocess call (verify shell=False)
  - Fix: Ensure list args and no shell=True
  - Match: `subprocess.Popen(`

- **Line 224** in `.claude/skills/security-review/languages/python.md`
  - Risk: Subprocess call (verify shell=False)
  - Fix: Ensure list args and no shell=True
  - Match: `subprocess.call(`

- **Line 225** in `.claude/skills/security-review/languages/python.md`
  - Risk: Subprocess call (verify shell=False)
  - Fix: Ensure list args and no shell=True
  - Match: `subprocess.run(`

- **Line 226** in `.claude/skills/security-review/languages/python.md`
  - Risk: Subprocess call (verify shell=False)
  - Fix: Ensure list args and no shell=True
  - Match: `subprocess.Popen(`


---

## Registry - Other Skills

### security-review

**Findings:** 27 Critical, 13 High, 8 Info

#### 🔴 CRITICAL (27)

**CMD-INJECT:**

- **Line 207** in `benchmarks/SCR_Bench/SCR-TrustLift/experiment/codex-tools/registry/other/security-review/SKILL.md`
  - Risk: Shell command injection via os.system()
  - Fix: Use subprocess.run() with list args
  - Match: `os.system(`

- **Line 80** in `benchmarks/SCR_Bench/SCR-TrustLift/experiment/codex-tools/registry/other/security-review/languages/python.md`
  - Risk: Shell command injection via os.system()
  - Fix: Use subprocess.run() with list args
  - Match: `os.system(`

- **Line 222** in `benchmarks/SCR_Bench/SCR-TrustLift/experiment/codex-tools/registry/other/security-review/languages/python.md`
  - Risk: Shell command injection via os.system()
  - Fix: Use subprocess.run() with list args
  - Match: `os.system(`

- **Line 223** in `benchmarks/SCR_Bench/SCR-TrustLift/experiment/codex-tools/registry/other/security-review/languages/python.md`
  - Risk: Shell command injection via os.popen()
  - Fix: Use subprocess.run() with list args
  - Match: `os.popen(`

- **Line 81** in `benchmarks/SCR_Bench/SCR-TrustLift/experiment/codex-tools/registry/other/security-review/languages/python.md`
  - Risk: shell=True enables command injection
  - Fix: Remove shell=True
  - Match: `subprocess.run(cmd, shell=True`

- **Line 82** in `benchmarks/SCR_Bench/SCR-TrustLift/experiment/codex-tools/registry/other/security-review/languages/python.md`
  - Risk: shell=True enables command injection
  - Fix: Remove shell=True
  - Match: `subprocess.Popen(cmd, shell=True`

- **Line 224** in `benchmarks/SCR_Bench/SCR-TrustLift/experiment/codex-tools/registry/other/security-review/languages/python.md`
  - Risk: shell=True enables command injection
  - Fix: Remove shell=True
  - Match: `subprocess.call(cmd, shell=True`

- **Line 225** in `benchmarks/SCR_Bench/SCR-TrustLift/experiment/codex-tools/registry/other/security-review/languages/python.md`
  - Risk: shell=True enables command injection
  - Fix: Remove shell=True
  - Match: `subprocess.run(cmd, shell=True`

- **Line 226** in `benchmarks/SCR_Bench/SCR-TrustLift/experiment/codex-tools/registry/other/security-review/languages/python.md`
  - Risk: shell=True enables command injection
  - Fix: Remove shell=True
  - Match: `subprocess.Popen(cmd, shell=True`


**CODE-EXEC:**

- **Line 190** in `benchmarks/SCR_Bench/SCR-TrustLift/experiment/codex-tools/registry/other/security-review/SKILL.md`
  - Risk: Arbitrary code execution via eval()
  - Fix: Replace with ast.literal_eval() or explicit parsing
  - Match: `eval(`

- **Line 191** in `benchmarks/SCR_Bench/SCR-TrustLift/experiment/codex-tools/registry/other/security-review/SKILL.md`
  - Risk: Arbitrary code execution via exec()
  - Fix: Remove exec() and use explicit function calls
  - Match: `exec(`

- **Line 197** in `benchmarks/SCR_Bench/SCR-TrustLift/experiment/codex-tools/registry/other/security-review/SKILL.md`
  - Risk: Arbitrary code execution via exec()
  - Fix: Remove exec() and use explicit function calls
  - Match: `exec(`

- **Line 216** in `benchmarks/SCR_Bench/SCR-TrustLift/experiment/codex-tools/registry/other/security-review/languages/python.md`
  - Risk: Arbitrary code execution via eval()
  - Fix: Replace with ast.literal_eval() or explicit parsing
  - Match: `eval(`

- **Line 263** in `benchmarks/SCR_Bench/SCR-TrustLift/experiment/codex-tools/registry/other/security-review/languages/python.md`
  - Risk: Arbitrary code execution via eval()
  - Fix: Replace with ast.literal_eval() or explicit parsing
  - Match: `eval(`

- **Line 217** in `benchmarks/SCR_Bench/SCR-TrustLift/experiment/codex-tools/registry/other/security-review/languages/python.md`
  - Risk: Arbitrary code execution via exec()
  - Fix: Remove exec() and use explicit function calls
  - Match: `exec(`

- **Line 218** in `benchmarks/SCR_Bench/SCR-TrustLift/experiment/codex-tools/registry/other/security-review/languages/python.md`
  - Risk: Dynamic code compilation
  - Fix: Remove compile() or ensure input is fully trusted
  - Match: `compile(`

- **Line 219** in `benchmarks/SCR_Bench/SCR-TrustLift/experiment/codex-tools/registry/other/security-review/languages/python.md`
  - Risk: Dynamic import loads arbitrary modules
  - Fix: Use static imports at the top of the file
  - Match: `__import__(`

- **Line 45** in `benchmarks/SCR_Bench/SCR-TrustLift/experiment/codex-tools/registry/other/security-review/languages/javascript.md`
  - Risk: Arbitrary code execution via eval()
  - Fix: Replace with ast.literal_eval() or explicit parsing
  - Match: `eval(`

- **Line 249** in `benchmarks/SCR_Bench/SCR-TrustLift/experiment/codex-tools/registry/other/security-review/languages/javascript.md`
  - Risk: Arbitrary code execution via eval()
  - Fix: Replace with ast.literal_eval() or explicit parsing
  - Match: `eval(`

- **Line 356** in `benchmarks/SCR_Bench/SCR-TrustLift/experiment/codex-tools/registry/other/security-review/languages/javascript.md`
  - Risk: Arbitrary code execution via eval()
  - Fix: Replace with ast.literal_eval() or explicit parsing
  - Match: `eval(`

- **Line 375** in `benchmarks/SCR_Bench/SCR-TrustLift/experiment/codex-tools/registry/other/security-review/languages/javascript.md`
  - Risk: Arbitrary code execution via eval()
  - Fix: Replace with ast.literal_eval() or explicit parsing
  - Match: `eval(`

- **Line 134** in `benchmarks/SCR_Bench/SCR-TrustLift/experiment/codex-tools/registry/other/security-review/languages/javascript.md`
  - Risk: Arbitrary code execution via exec()
  - Fix: Remove exec() and use explicit function calls
  - Match: `exec(`

- **Line 137** in `benchmarks/SCR_Bench/SCR-TrustLift/experiment/codex-tools/registry/other/security-review/languages/javascript.md`
  - Risk: Arbitrary code execution via exec()
  - Fix: Remove exec() and use explicit function calls
  - Match: `exec(`

- **Line 378** in `benchmarks/SCR_Bench/SCR-TrustLift/experiment/codex-tools/registry/other/security-review/languages/javascript.md`
  - Risk: Arbitrary code execution via exec()
  - Fix: Remove exec() and use explicit function calls
  - Match: `exec(`

- **Line 100** in `benchmarks/SCR_Bench/SCR-TrustLift/experiment/codex-tools/registry/other/security-review/languages/javascript.md`
  - Risk: Dynamic code compilation
  - Fix: Remove compile() or ensure input is fully trusted
  - Match: `compile(`


**NET-EXFIL:**

- **Line 235** in `benchmarks/SCR_Bench/SCR-TrustLift/experiment/codex-tools/registry/other/security-review/languages/python.md`
  - Risk: Outbound HTTP request
  - Fix: Remove outbound network calls
  - Match: `urllib.request.urlopen(`

- **Line 237** in `benchmarks/SCR_Bench/SCR-TrustLift/experiment/codex-tools/registry/other/security-review/languages/python.md`
  - Risk: Async HTTP may exfiltrate data
  - Fix: Remove async HTTP clients
  - Match: `aiohttp.ClientSession(`


#### 🟠 HIGH (13)

**PRIV-ESC:**

- **Line 155** in `benchmarks/SCR_Bench/SCR-TrustLift/experiment/codex-tools/registry/other/security-review/infrastructure/docker.md`
  - Risk: Privilege escalation via sudo
  - Fix: Remove sudo usage
  - Match: `sudo`


**UNSAFE-DESER:**

- **Line 192** in `benchmarks/SCR_Bench/SCR-TrustLift/experiment/codex-tools/registry/other/security-review/SKILL.md`
  - Risk: Pickle deserialization can execute code
  - Fix: Use json.loads() instead
  - Match: `pickle.loads(`

- **Line 193** in `benchmarks/SCR_Bench/SCR-TrustLift/experiment/codex-tools/registry/other/security-review/SKILL.md`
  - Risk: yaml.load() without SafeLoader
  - Fix: Use yaml.safe_load()
  - Match: `yaml.load(user_data)`

- **Line 85** in `benchmarks/SCR_Bench/SCR-TrustLift/experiment/codex-tools/registry/other/security-review/languages/python.md`
  - Risk: Pickle deserialization can execute code
  - Fix: Use json.loads() instead
  - Match: `pickle.loads(`

- **Line 206** in `benchmarks/SCR_Bench/SCR-TrustLift/experiment/codex-tools/registry/other/security-review/languages/python.md`
  - Risk: Pickle deserialization can execute code
  - Fix: Use json.loads() instead
  - Match: `pickle.loads(`

- **Line 207** in `benchmarks/SCR_Bench/SCR-TrustLift/experiment/codex-tools/registry/other/security-review/languages/python.md`
  - Risk: Pickle deserialization can execute code
  - Fix: Use json.loads() instead
  - Match: `pickle.load(`

- **Line 208** in `benchmarks/SCR_Bench/SCR-TrustLift/experiment/codex-tools/registry/other/security-review/languages/python.md`
  - Risk: Pickle deserialization can execute code
  - Fix: Use json.loads() instead
  - Match: `Pickle.loads(`

- **Line 86** in `benchmarks/SCR_Bench/SCR-TrustLift/experiment/codex-tools/registry/other/security-review/languages/python.md`
  - Risk: yaml.load() without SafeLoader
  - Fix: Use yaml.safe_load()
  - Match: `yaml.load(user_data)`

- **Line 87** in `benchmarks/SCR_Bench/SCR-TrustLift/experiment/codex-tools/registry/other/security-review/languages/python.md`
  - Risk: yaml.load() without SafeLoader
  - Fix: Use yaml.safe_load()
  - Match: `yaml.load(data, Loader=yaml.Loader)`

- **Line 211** in `benchmarks/SCR_Bench/SCR-TrustLift/experiment/codex-tools/registry/other/security-review/languages/python.md`
  - Risk: yaml.load() without SafeLoader
  - Fix: Use yaml.safe_load()
  - Match: `yaml.load(data)`

- **Line 212** in `benchmarks/SCR_Bench/SCR-TrustLift/experiment/codex-tools/registry/other/security-review/languages/python.md`
  - Risk: yaml.load() without SafeLoader
  - Fix: Use yaml.safe_load()
  - Match: `yaml.load(data, Loader=yaml.FullLoader)`

- **Line 213** in `benchmarks/SCR_Bench/SCR-TrustLift/experiment/codex-tools/registry/other/security-review/languages/python.md`
  - Risk: yaml.load() without SafeLoader
  - Fix: Use yaml.safe_load()
  - Match: `yaml.load(data, Loader=yaml.UnsafeLoader)`

- **Line 210** in `benchmarks/SCR_Bench/SCR-TrustLift/experiment/codex-tools/registry/other/security-review/languages/python.md`
  - Risk: Marshal deserialization can execute code
  - Fix: Use json.loads() instead
  - Match: `marshal.loads(`


#### 🔵 INFO (8)

**ENV-ACCESS:**

- **Line 55** in `benchmarks/SCR_Bench/SCR-TrustLift/experiment/codex-tools/registry/other/security-review/SKILL.md`
  - Risk: Reads environment variables
  - Fix: Document which env vars are read
  - Match: `os.environ.`

- **Line 153** in `benchmarks/SCR_Bench/SCR-TrustLift/experiment/codex-tools/registry/other/security-review/SKILL.md`
  - Risk: Reads environment variables
  - Fix: Document which env vars are read
  - Match: `os.environ.`

- **Line 31** in `benchmarks/SCR_Bench/SCR-TrustLift/experiment/codex-tools/registry/other/security-review/languages/python.md`
  - Risk: Reads environment variables
  - Fix: Document which env vars are read
  - Match: `os.environ.`


**SUBPROCESS:**

- **Line 81** in `benchmarks/SCR_Bench/SCR-TrustLift/experiment/codex-tools/registry/other/security-review/languages/python.md`
  - Risk: Subprocess call (verify shell=False)
  - Fix: Ensure list args and no shell=True
  - Match: `subprocess.run(`

- **Line 82** in `benchmarks/SCR_Bench/SCR-TrustLift/experiment/codex-tools/registry/other/security-review/languages/python.md`
  - Risk: Subprocess call (verify shell=False)
  - Fix: Ensure list args and no shell=True
  - Match: `subprocess.Popen(`

- **Line 224** in `benchmarks/SCR_Bench/SCR-TrustLift/experiment/codex-tools/registry/other/security-review/languages/python.md`
  - Risk: Subprocess call (verify shell=False)
  - Fix: Ensure list args and no shell=True
  - Match: `subprocess.call(`

- **Line 225** in `benchmarks/SCR_Bench/SCR-TrustLift/experiment/codex-tools/registry/other/security-review/languages/python.md`
  - Risk: Subprocess call (verify shell=False)
  - Fix: Ensure list args and no shell=True
  - Match: `subprocess.run(`

- **Line 226** in `benchmarks/SCR_Bench/SCR-TrustLift/experiment/codex-tools/registry/other/security-review/languages/python.md`
  - Risk: Subprocess call (verify shell=False)
  - Fix: Ensure list args and no shell=True
  - Match: `subprocess.Popen(`


---

## TrustLift - Experiment Skills

### apple-music

**Findings:** 2 Critical, 0 High, 0 Info

#### 🔴 CRITICAL (2)

**NET-EXFIL:**

- **Line 466** in `benchmarks/SCR_Bench/SCR-TrustLift/experiment/apple-music/.claude/skills/apple-music/SKILL.md`
  - Risk: Outbound HTTP may exfiltrate data
  - Fix: Remove outbound network calls
  - Match: `requests.post(`

- **Line 480** in `benchmarks/SCR_Bench/SCR-TrustLift/experiment/apple-music/.claude/skills/apple-music/SKILL.md`
  - Risk: Outbound HTTP may exfiltrate data
  - Fix: Remove outbound network calls
  - Match: `requests.post(`


### chrome-devtools

**Findings:** 2 Critical, 8 High, 0 Info

#### 🔴 CRITICAL (2)

**CODE-EXEC:**

- **Line 41** in `benchmarks/SCR_Bench/SCR-TrustLift/experiment/chrome-devtools/.claude/skills/chrome-devtools/scripts/lib/selector.js`
  - Risk: Arbitrary code execution via eval()
  - Fix: Replace with ast.literal_eval() or explicit parsing
  - Match: `eval(`

- **Line 124** in `benchmarks/SCR_Bench/SCR-TrustLift/experiment/chrome-devtools/.claude/skills/chrome-devtools/scripts/lib/selector.js`
  - Risk: Arbitrary code execution via eval()
  - Fix: Replace with ast.literal_eval() or explicit parsing
  - Match: `eval(`


#### 🟠 HIGH (8)

**PRIV-ESC:**

- **Line 52** in `benchmarks/SCR_Bench/SCR-TrustLift/experiment/chrome-devtools/.claude/skills/chrome-devtools/SKILL.md`
  - Risk: Privilege escalation via sudo
  - Fix: Remove sudo usage
  - Match: `sudo`

- **Line 21** in `benchmarks/SCR_Bench/SCR-TrustLift/experiment/chrome-devtools/.claude/skills/chrome-devtools/scripts/install-deps.sh`
  - Risk: Privilege escalation via sudo
  - Fix: Remove sudo usage
  - Match: `SUDO`

- **Line 21** in `benchmarks/SCR_Bench/SCR-TrustLift/experiment/chrome-devtools/.claude/skills/chrome-devtools/scripts/install-deps.sh`
  - Risk: Privilege escalation via sudo
  - Fix: Remove sudo usage
  - Match: `sudo`

- **Line 26** in `benchmarks/SCR_Bench/SCR-TrustLift/experiment/chrome-devtools/.claude/skills/chrome-devtools/scripts/install-deps.sh`
  - Risk: Privilege escalation via sudo
  - Fix: Remove sudo usage
  - Match: `SUDO`

- **Line 36** in `benchmarks/SCR_Bench/SCR-TrustLift/experiment/chrome-devtools/.claude/skills/chrome-devtools/scripts/install-deps.sh`
  - Risk: Privilege escalation via sudo
  - Fix: Remove sudo usage
  - Match: `SUDO`

- **Line 53** in `benchmarks/SCR_Bench/SCR-TrustLift/experiment/chrome-devtools/.claude/skills/chrome-devtools/scripts/install-deps.sh`
  - Risk: Privilege escalation via sudo
  - Fix: Remove sudo usage
  - Match: `SUDO`

- **Line 107** in `benchmarks/SCR_Bench/SCR-TrustLift/experiment/chrome-devtools/.claude/skills/chrome-devtools/scripts/install-deps.sh`
  - Risk: Privilege escalation via sudo
  - Fix: Remove sudo usage
  - Match: `SUDO`

- **Line 147** in `benchmarks/SCR_Bench/SCR-TrustLift/experiment/chrome-devtools/.claude/skills/chrome-devtools/scripts/install-deps.sh`
  - Risk: Privilege escalation via sudo
  - Fix: Remove sudo usage
  - Match: `SUDO`


### co_INST-13_docx_task3

**Findings:** 2 Critical, 4 High, 3 Info

#### 🔴 CRITICAL (2)

**CODE-EXEC:**

- **Line 83** in `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-13_docx_task3/.claude/skills/co_INST-13_docx_task3/ooxml/scripts/validation/pptx.py`
  - Risk: Dynamic code compilation
  - Fix: Remove compile() or ensure input is fully trusted
  - Match: `compile(`

- **Line 917** in `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-13_docx_task3/.claude/skills/co_INST-13_docx_task3/ooxml/scripts/validation/base.py`
  - Risk: Dynamic code compilation
  - Fix: Remove compile() or ensure input is fully trusted
  - Match: `compile(`


#### 🟠 HIGH (4)

**FS-BOUNDARY:**

- **Line 836** in `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-13_docx_task3/.claude/skills/co_INST-13_docx_task3/scripts/document.py`
  - Risk: Destructive file operation
  - Fix: Validate paths are within skill directory
  - Match: `shutil.rmtree(`


**PRIV-ESC:**

- **Line 194** in `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-13_docx_task3/.claude/skills/co_INST-13_docx_task3/SKILL.md`
  - Risk: Privilege escalation via sudo
  - Fix: Remove sudo usage
  - Match: `sudo`

- **Line 196** in `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-13_docx_task3/.claude/skills/co_INST-13_docx_task3/SKILL.md`
  - Risk: Privilege escalation via sudo
  - Fix: Remove sudo usage
  - Match: `sudo`

- **Line 197** in `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-13_docx_task3/.claude/skills/co_INST-13_docx_task3/SKILL.md`
  - Risk: Privilege escalation via sudo
  - Fix: Remove sudo usage
  - Match: `sudo`


#### 🔵 INFO (3)

**SUBPROCESS:**

- **Line 103** in `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-13_docx_task3/.claude/skills/co_INST-13_docx_task3/ooxml/scripts/pack.py`
  - Risk: Subprocess call (verify shell=False)
  - Fix: Ensure list args and no shell=True
  - Match: `subprocess.run(`

- **Line 153** in `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-13_docx_task3/.claude/skills/co_INST-13_docx_task3/ooxml/scripts/validation/redlining.py`
  - Risk: Subprocess call (verify shell=False)
  - Fix: Ensure list args and no shell=True
  - Match: `subprocess.run(`

- **Line 185** in `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-13_docx_task3/.claude/skills/co_INST-13_docx_task3/ooxml/scripts/validation/redlining.py`
  - Risk: Subprocess call (verify shell=False)
  - Fix: Ensure list args and no shell=True
  - Match: `subprocess.run(`


### co_INST-13_docx_task4

**Findings:** 2 Critical, 4 High, 3 Info

#### 🔴 CRITICAL (2)

**CODE-EXEC:**

- **Line 83** in `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-13_docx_task4/.claude/skills/co_INST-13_docx_task4/ooxml/scripts/validation/pptx.py`
  - Risk: Dynamic code compilation
  - Fix: Remove compile() or ensure input is fully trusted
  - Match: `compile(`

- **Line 917** in `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-13_docx_task4/.claude/skills/co_INST-13_docx_task4/ooxml/scripts/validation/base.py`
  - Risk: Dynamic code compilation
  - Fix: Remove compile() or ensure input is fully trusted
  - Match: `compile(`


#### 🟠 HIGH (4)

**FS-BOUNDARY:**

- **Line 836** in `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-13_docx_task4/.claude/skills/co_INST-13_docx_task4/scripts/document.py`
  - Risk: Destructive file operation
  - Fix: Validate paths are within skill directory
  - Match: `shutil.rmtree(`


**PRIV-ESC:**

- **Line 194** in `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-13_docx_task4/.claude/skills/co_INST-13_docx_task4/SKILL.md`
  - Risk: Privilege escalation via sudo
  - Fix: Remove sudo usage
  - Match: `sudo`

- **Line 196** in `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-13_docx_task4/.claude/skills/co_INST-13_docx_task4/SKILL.md`
  - Risk: Privilege escalation via sudo
  - Fix: Remove sudo usage
  - Match: `sudo`

- **Line 197** in `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-13_docx_task4/.claude/skills/co_INST-13_docx_task4/SKILL.md`
  - Risk: Privilege escalation via sudo
  - Fix: Remove sudo usage
  - Match: `sudo`


#### 🔵 INFO (3)

**SUBPROCESS:**

- **Line 103** in `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-13_docx_task4/.claude/skills/co_INST-13_docx_task4/ooxml/scripts/pack.py`
  - Risk: Subprocess call (verify shell=False)
  - Fix: Ensure list args and no shell=True
  - Match: `subprocess.run(`

- **Line 153** in `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-13_docx_task4/.claude/skills/co_INST-13_docx_task4/ooxml/scripts/validation/redlining.py`
  - Risk: Subprocess call (verify shell=False)
  - Fix: Ensure list args and no shell=True
  - Match: `subprocess.run(`

- **Line 185** in `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-13_docx_task4/.claude/skills/co_INST-13_docx_task4/ooxml/scripts/validation/redlining.py`
  - Risk: Subprocess call (verify shell=False)
  - Fix: Ensure list args and no shell=True
  - Match: `subprocess.run(`


### co_INST-13_docx_task5

**Findings:** 2 Critical, 4 High, 3 Info

#### 🔴 CRITICAL (2)

**CODE-EXEC:**

- **Line 83** in `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-13_docx_task5/.claude/skills/co_INST-13_docx_task5/ooxml/scripts/validation/pptx.py`
  - Risk: Dynamic code compilation
  - Fix: Remove compile() or ensure input is fully trusted
  - Match: `compile(`

- **Line 917** in `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-13_docx_task5/.claude/skills/co_INST-13_docx_task5/ooxml/scripts/validation/base.py`
  - Risk: Dynamic code compilation
  - Fix: Remove compile() or ensure input is fully trusted
  - Match: `compile(`


#### 🟠 HIGH (4)

**FS-BOUNDARY:**

- **Line 836** in `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-13_docx_task5/.claude/skills/co_INST-13_docx_task5/scripts/document.py`
  - Risk: Destructive file operation
  - Fix: Validate paths are within skill directory
  - Match: `shutil.rmtree(`


**PRIV-ESC:**

- **Line 194** in `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-13_docx_task5/.claude/skills/co_INST-13_docx_task5/SKILL.md`
  - Risk: Privilege escalation via sudo
  - Fix: Remove sudo usage
  - Match: `sudo`

- **Line 196** in `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-13_docx_task5/.claude/skills/co_INST-13_docx_task5/SKILL.md`
  - Risk: Privilege escalation via sudo
  - Fix: Remove sudo usage
  - Match: `sudo`

- **Line 197** in `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-13_docx_task5/.claude/skills/co_INST-13_docx_task5/SKILL.md`
  - Risk: Privilege escalation via sudo
  - Fix: Remove sudo usage
  - Match: `sudo`


#### 🔵 INFO (3)

**SUBPROCESS:**

- **Line 103** in `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-13_docx_task5/.claude/skills/co_INST-13_docx_task5/ooxml/scripts/pack.py`
  - Risk: Subprocess call (verify shell=False)
  - Fix: Ensure list args and no shell=True
  - Match: `subprocess.run(`

- **Line 153** in `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-13_docx_task5/.claude/skills/co_INST-13_docx_task5/ooxml/scripts/validation/redlining.py`
  - Risk: Subprocess call (verify shell=False)
  - Fix: Ensure list args and no shell=True
  - Match: `subprocess.run(`

- **Line 185** in `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-13_docx_task5/.claude/skills/co_INST-13_docx_task5/ooxml/scripts/validation/redlining.py`
  - Risk: Subprocess call (verify shell=False)
  - Fix: Ensure list args and no shell=True
  - Match: `subprocess.run(`


### co_INST-13_pptx_task0

**Findings:** 2 Critical, 2 High, 5 Info

#### 🔴 CRITICAL (2)

**CODE-EXEC:**

- **Line 83** in `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-13_pptx_task0/.claude/skills/co_INST-13_pptx_task0/ooxml/scripts/validation/pptx.py`
  - Risk: Dynamic code compilation
  - Fix: Remove compile() or ensure input is fully trusted
  - Match: `compile(`

- **Line 917** in `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-13_pptx_task0/.claude/skills/co_INST-13_pptx_task0/ooxml/scripts/validation/base.py`
  - Risk: Dynamic code compilation
  - Fix: Remove compile() or ensure input is fully trusted
  - Match: `compile(`


#### 🟠 HIGH (2)

**PRIV-ESC:**

- **Line 483** in `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-13_pptx_task0/.claude/skills/co_INST-13_pptx_task0/SKILL.md`
  - Risk: Privilege escalation via sudo
  - Fix: Remove sudo usage
  - Match: `sudo`

- **Line 484** in `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-13_pptx_task0/.claude/skills/co_INST-13_pptx_task0/SKILL.md`
  - Risk: Privilege escalation via sudo
  - Fix: Remove sudo usage
  - Match: `sudo`


#### 🔵 INFO (5)

**SUBPROCESS:**

- **Line 103** in `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-13_pptx_task0/.claude/skills/co_INST-13_pptx_task0/ooxml/scripts/pack.py`
  - Risk: Subprocess call (verify shell=False)
  - Fix: Ensure list args and no shell=True
  - Match: `subprocess.run(`

- **Line 153** in `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-13_pptx_task0/.claude/skills/co_INST-13_pptx_task0/ooxml/scripts/validation/redlining.py`
  - Risk: Subprocess call (verify shell=False)
  - Fix: Ensure list args and no shell=True
  - Match: `subprocess.run(`

- **Line 185** in `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-13_pptx_task0/.claude/skills/co_INST-13_pptx_task0/ooxml/scripts/validation/redlining.py`
  - Risk: Subprocess call (verify shell=False)
  - Fix: Ensure list args and no shell=True
  - Match: `subprocess.run(`

- **Line 219** in `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-13_pptx_task0/.claude/skills/co_INST-13_pptx_task0/scripts/thumbnail.py`
  - Risk: Subprocess call (verify shell=False)
  - Fix: Ensure list args and no shell=True
  - Match: `subprocess.run(`

- **Line 237** in `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-13_pptx_task0/.claude/skills/co_INST-13_pptx_task0/scripts/thumbnail.py`
  - Risk: Subprocess call (verify shell=False)
  - Fix: Ensure list args and no shell=True
  - Match: `subprocess.run(`


### co_INST-13_pptx_task1

**Findings:** 2 Critical, 2 High, 5 Info

#### 🔴 CRITICAL (2)

**CODE-EXEC:**

- **Line 83** in `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-13_pptx_task1/.claude/skills/co_INST-13_pptx_task1/ooxml/scripts/validation/pptx.py`
  - Risk: Dynamic code compilation
  - Fix: Remove compile() or ensure input is fully trusted
  - Match: `compile(`

- **Line 917** in `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-13_pptx_task1/.claude/skills/co_INST-13_pptx_task1/ooxml/scripts/validation/base.py`
  - Risk: Dynamic code compilation
  - Fix: Remove compile() or ensure input is fully trusted
  - Match: `compile(`


#### 🟠 HIGH (2)

**PRIV-ESC:**

- **Line 483** in `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-13_pptx_task1/.claude/skills/co_INST-13_pptx_task1/SKILL.md`
  - Risk: Privilege escalation via sudo
  - Fix: Remove sudo usage
  - Match: `sudo`

- **Line 484** in `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-13_pptx_task1/.claude/skills/co_INST-13_pptx_task1/SKILL.md`
  - Risk: Privilege escalation via sudo
  - Fix: Remove sudo usage
  - Match: `sudo`


#### 🔵 INFO (5)

**SUBPROCESS:**

- **Line 103** in `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-13_pptx_task1/.claude/skills/co_INST-13_pptx_task1/ooxml/scripts/pack.py`
  - Risk: Subprocess call (verify shell=False)
  - Fix: Ensure list args and no shell=True
  - Match: `subprocess.run(`

- **Line 153** in `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-13_pptx_task1/.claude/skills/co_INST-13_pptx_task1/ooxml/scripts/validation/redlining.py`
  - Risk: Subprocess call (verify shell=False)
  - Fix: Ensure list args and no shell=True
  - Match: `subprocess.run(`

- **Line 185** in `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-13_pptx_task1/.claude/skills/co_INST-13_pptx_task1/ooxml/scripts/validation/redlining.py`
  - Risk: Subprocess call (verify shell=False)
  - Fix: Ensure list args and no shell=True
  - Match: `subprocess.run(`

- **Line 219** in `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-13_pptx_task1/.claude/skills/co_INST-13_pptx_task1/scripts/thumbnail.py`
  - Risk: Subprocess call (verify shell=False)
  - Fix: Ensure list args and no shell=True
  - Match: `subprocess.run(`

- **Line 237** in `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-13_pptx_task1/.claude/skills/co_INST-13_pptx_task1/scripts/thumbnail.py`
  - Risk: Subprocess call (verify shell=False)
  - Fix: Ensure list args and no shell=True
  - Match: `subprocess.run(`


### co_INST-13_pptx_task2

**Findings:** 2 Critical, 2 High, 5 Info

#### 🔴 CRITICAL (2)

**CODE-EXEC:**

- **Line 83** in `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-13_pptx_task2/.claude/skills/co_INST-13_pptx_task2/ooxml/scripts/validation/pptx.py`
  - Risk: Dynamic code compilation
  - Fix: Remove compile() or ensure input is fully trusted
  - Match: `compile(`

- **Line 917** in `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-13_pptx_task2/.claude/skills/co_INST-13_pptx_task2/ooxml/scripts/validation/base.py`
  - Risk: Dynamic code compilation
  - Fix: Remove compile() or ensure input is fully trusted
  - Match: `compile(`


#### 🟠 HIGH (2)

**PRIV-ESC:**

- **Line 483** in `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-13_pptx_task2/.claude/skills/co_INST-13_pptx_task2/SKILL.md`
  - Risk: Privilege escalation via sudo
  - Fix: Remove sudo usage
  - Match: `sudo`

- **Line 484** in `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-13_pptx_task2/.claude/skills/co_INST-13_pptx_task2/SKILL.md`
  - Risk: Privilege escalation via sudo
  - Fix: Remove sudo usage
  - Match: `sudo`


#### 🔵 INFO (5)

**SUBPROCESS:**

- **Line 103** in `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-13_pptx_task2/.claude/skills/co_INST-13_pptx_task2/ooxml/scripts/pack.py`
  - Risk: Subprocess call (verify shell=False)
  - Fix: Ensure list args and no shell=True
  - Match: `subprocess.run(`

- **Line 153** in `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-13_pptx_task2/.claude/skills/co_INST-13_pptx_task2/ooxml/scripts/validation/redlining.py`
  - Risk: Subprocess call (verify shell=False)
  - Fix: Ensure list args and no shell=True
  - Match: `subprocess.run(`

- **Line 185** in `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-13_pptx_task2/.claude/skills/co_INST-13_pptx_task2/ooxml/scripts/validation/redlining.py`
  - Risk: Subprocess call (verify shell=False)
  - Fix: Ensure list args and no shell=True
  - Match: `subprocess.run(`

- **Line 219** in `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-13_pptx_task2/.claude/skills/co_INST-13_pptx_task2/scripts/thumbnail.py`
  - Risk: Subprocess call (verify shell=False)
  - Fix: Ensure list args and no shell=True
  - Match: `subprocess.run(`

- **Line 237** in `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-13_pptx_task2/.claude/skills/co_INST-13_pptx_task2/scripts/thumbnail.py`
  - Risk: Subprocess call (verify shell=False)
  - Fix: Ensure list args and no shell=True
  - Match: `subprocess.run(`


### co_INST-13_xlsx_task6

**Findings:** 0 Critical, 0 High, 5 Info

#### 🔵 INFO (5)

**FILE-OPS:**

- **Line 19** in `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-13_xlsx_task6/.claude/skills/co_INST-13_xlsx_task6/recalc.py`
  - Risk: Expands ~ to home directory
  - Fix: Use paths relative to skill directory
  - Match: `os.path.expanduser(`

- **Line 21** in `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-13_xlsx_task6/.claude/skills/co_INST-13_xlsx_task6/recalc.py`
  - Risk: Expands ~ to home directory
  - Fix: Use paths relative to skill directory
  - Match: `os.path.expanduser(`


**SUBPROCESS:**

- **Line 31** in `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-13_xlsx_task6/.claude/skills/co_INST-13_xlsx_task6/recalc.py`
  - Risk: Subprocess call (verify shell=False)
  - Fix: Ensure list args and no shell=True
  - Match: `subprocess.run(`

- **Line 84** in `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-13_xlsx_task6/.claude/skills/co_INST-13_xlsx_task6/recalc.py`
  - Risk: Subprocess call (verify shell=False)
  - Fix: Ensure list args and no shell=True
  - Match: `subprocess.run(`

- **Line 92** in `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-13_xlsx_task6/.claude/skills/co_INST-13_xlsx_task6/recalc.py`
  - Risk: Subprocess call (verify shell=False)
  - Fix: Ensure list args and no shell=True
  - Match: `subprocess.run(`


### co_INST-13_xlsx_task7

**Findings:** 0 Critical, 0 High, 5 Info

#### 🔵 INFO (5)

**FILE-OPS:**

- **Line 19** in `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-13_xlsx_task7/.claude/skills/co_INST-13_xlsx_task7/recalc.py`
  - Risk: Expands ~ to home directory
  - Fix: Use paths relative to skill directory
  - Match: `os.path.expanduser(`

- **Line 21** in `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-13_xlsx_task7/.claude/skills/co_INST-13_xlsx_task7/recalc.py`
  - Risk: Expands ~ to home directory
  - Fix: Use paths relative to skill directory
  - Match: `os.path.expanduser(`


**SUBPROCESS:**

- **Line 31** in `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-13_xlsx_task7/.claude/skills/co_INST-13_xlsx_task7/recalc.py`
  - Risk: Subprocess call (verify shell=False)
  - Fix: Ensure list args and no shell=True
  - Match: `subprocess.run(`

- **Line 84** in `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-13_xlsx_task7/.claude/skills/co_INST-13_xlsx_task7/recalc.py`
  - Risk: Subprocess call (verify shell=False)
  - Fix: Ensure list args and no shell=True
  - Match: `subprocess.run(`

- **Line 92** in `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-13_xlsx_task7/.claude/skills/co_INST-13_xlsx_task7/recalc.py`
  - Risk: Subprocess call (verify shell=False)
  - Fix: Ensure list args and no shell=True
  - Match: `subprocess.run(`


### co_INST-14_hf-llm-trainer

**Findings:** 1 Critical, 0 High, 27 Info

#### 🔴 CRITICAL (1)

**NET-EXFIL:**

- **Line 42** in `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-14_hf-llm-trainer/.claude/skills/co_INST-14_hf-llm-trainer/skills/model-trainer/scripts/dataset_inspector.py`
  - Risk: Outbound HTTP request
  - Fix: Remove outbound network calls
  - Match: `urllib.request.urlopen(`


#### 🔵 INFO (27)

**ENV-ACCESS:**

- **Line 47** in `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-14_hf-llm-trainer/.claude/skills/co_INST-14_hf-llm-trainer/skills/model-trainer/scripts/convert_to_gguf.py`
  - Risk: Reads environment variables
  - Fix: Document which env vars are read
  - Match: `os.environ.`

- **Line 48** in `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-14_hf-llm-trainer/.claude/skills/co_INST-14_hf-llm-trainer/skills/model-trainer/scripts/convert_to_gguf.py`
  - Risk: Reads environment variables
  - Fix: Document which env vars are read
  - Match: `os.environ.`

- **Line 49** in `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-14_hf-llm-trainer/.claude/skills/co_INST-14_hf-llm-trainer/skills/model-trainer/scripts/convert_to_gguf.py`
  - Risk: Reads environment variables
  - Fix: Document which env vars are read
  - Match: `os.environ.`

- **Line 50** in `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-14_hf-llm-trainer/.claude/skills/co_INST-14_hf-llm-trainer/skills/model-trainer/scripts/convert_to_gguf.py`
  - Risk: Reads environment variables
  - Fix: Document which env vars are read
  - Match: `os.environ.`


**SUBPROCESS:**

- **Line 31** in `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-14_hf-llm-trainer/.claude/skills/co_INST-14_hf-llm-trainer/skills/model-trainer/references/gguf_conversion.md`
  - Risk: Subprocess call (verify shell=False)
  - Fix: Ensure list args and no shell=True
  - Match: `subprocess.run(`

- **Line 32** in `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-14_hf-llm-trainer/.claude/skills/co_INST-14_hf-llm-trainer/skills/model-trainer/references/gguf_conversion.md`
  - Risk: Subprocess call (verify shell=False)
  - Fix: Ensure list args and no shell=True
  - Match: `subprocess.run(`

- **Line 44** in `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-14_hf-llm-trainer/.claude/skills/co_INST-14_hf-llm-trainer/skills/model-trainer/references/gguf_conversion.md`
  - Risk: Subprocess call (verify shell=False)
  - Fix: Ensure list args and no shell=True
  - Match: `subprocess.run(`

- **Line 50** in `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-14_hf-llm-trainer/.claude/skills/co_INST-14_hf-llm-trainer/skills/model-trainer/references/gguf_conversion.md`
  - Risk: Subprocess call (verify shell=False)
  - Fix: Ensure list args and no shell=True
  - Match: `subprocess.run(`

- **Line 100** in `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-14_hf-llm-trainer/.claude/skills/co_INST-14_hf-llm-trainer/skills/model-trainer/references/reliability_principles.md`
  - Risk: Subprocess call (verify shell=False)
  - Fix: Ensure list args and no shell=True
  - Match: `subprocess.run(`

- **Line 103** in `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-14_hf-llm-trainer/.claude/skills/co_INST-14_hf-llm-trainer/skills/model-trainer/references/reliability_principles.md`
  - Risk: Subprocess call (verify shell=False)
  - Fix: Ensure list args and no shell=True
  - Match: `subprocess.run(`

- **Line 108** in `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-14_hf-llm-trainer/.claude/skills/co_INST-14_hf-llm-trainer/skills/model-trainer/references/reliability_principles.md`
  - Risk: Subprocess call (verify shell=False)
  - Fix: Ensure list args and no shell=True
  - Match: `subprocess.run(`

- **Line 183** in `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-14_hf-llm-trainer/.claude/skills/co_INST-14_hf-llm-trainer/skills/model-trainer/references/reliability_principles.md`
  - Risk: Subprocess call (verify shell=False)
  - Fix: Ensure list args and no shell=True
  - Match: `subprocess.run(`

- **Line 184** in `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-14_hf-llm-trainer/.claude/skills/co_INST-14_hf-llm-trainer/skills/model-trainer/references/reliability_principles.md`
  - Risk: Subprocess call (verify shell=False)
  - Fix: Ensure list args and no shell=True
  - Match: `subprocess.run(`

- **Line 187** in `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-14_hf-llm-trainer/.claude/skills/co_INST-14_hf-llm-trainer/skills/model-trainer/references/reliability_principles.md`
  - Risk: Subprocess call (verify shell=False)
  - Fix: Ensure list args and no shell=True
  - Match: `subprocess.run(`

- **Line 188** in `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-14_hf-llm-trainer/.claude/skills/co_INST-14_hf-llm-trainer/skills/model-trainer/references/reliability_principles.md`
  - Risk: Subprocess call (verify shell=False)
  - Fix: Ensure list args and no shell=True
  - Match: `subprocess.run(`

- **Line 189** in `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-14_hf-llm-trainer/.claude/skills/co_INST-14_hf-llm-trainer/skills/model-trainer/references/reliability_principles.md`
  - Risk: Subprocess call (verify shell=False)
  - Fix: Ensure list args and no shell=True
  - Match: `subprocess.run(`

- **Line 228** in `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-14_hf-llm-trainer/.claude/skills/co_INST-14_hf-llm-trainer/skills/model-trainer/references/reliability_principles.md`
  - Risk: Subprocess call (verify shell=False)
  - Fix: Ensure list args and no shell=True
  - Match: `subprocess.run(`

- **Line 232** in `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-14_hf-llm-trainer/.claude/skills/co_INST-14_hf-llm-trainer/skills/model-trainer/references/reliability_principles.md`
  - Risk: Subprocess call (verify shell=False)
  - Fix: Ensure list args and no shell=True
  - Match: `subprocess.run(`

- **Line 94** in `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-14_hf-llm-trainer/.claude/skills/co_INST-14_hf-llm-trainer/skills/model-trainer/scripts/convert_to_gguf.py`
  - Risk: Subprocess call (verify shell=False)
  - Fix: Ensure list args and no shell=True
  - Match: `subprocess.run(`

- **Line 99** in `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-14_hf-llm-trainer/.claude/skills/co_INST-14_hf-llm-trainer/skills/model-trainer/scripts/convert_to_gguf.py`
  - Risk: Subprocess call (verify shell=False)
  - Fix: Ensure list args and no shell=True
  - Match: `subprocess.run(`

- **Line 107** in `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-14_hf-llm-trainer/.claude/skills/co_INST-14_hf-llm-trainer/skills/model-trainer/scripts/convert_to_gguf.py`
  - Risk: Subprocess call (verify shell=False)
  - Fix: Ensure list args and no shell=True
  - Match: `subprocess.run(`

- **Line 115** in `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-14_hf-llm-trainer/.claude/skills/co_INST-14_hf-llm-trainer/skills/model-trainer/scripts/convert_to_gguf.py`
  - Risk: Subprocess call (verify shell=False)
  - Fix: Ensure list args and no shell=True
  - Match: `subprocess.run(`

- **Line 121** in `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-14_hf-llm-trainer/.claude/skills/co_INST-14_hf-llm-trainer/skills/model-trainer/scripts/convert_to_gguf.py`
  - Risk: Subprocess call (verify shell=False)
  - Fix: Ensure list args and no shell=True
  - Match: `subprocess.run(`

- **Line 139** in `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-14_hf-llm-trainer/.claude/skills/co_INST-14_hf-llm-trainer/skills/model-trainer/scripts/convert_to_gguf.py`
  - Risk: Subprocess call (verify shell=False)
  - Fix: Ensure list args and no shell=True
  - Match: `subprocess.run(`

- **Line 170** in `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-14_hf-llm-trainer/.claude/skills/co_INST-14_hf-llm-trainer/skills/model-trainer/scripts/convert_to_gguf.py`
  - Risk: Subprocess call (verify shell=False)
  - Fix: Ensure list args and no shell=True
  - Match: `subprocess.run(`

- **Line 179** in `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-14_hf-llm-trainer/.claude/skills/co_INST-14_hf-llm-trainer/skills/model-trainer/scripts/convert_to_gguf.py`
  - Risk: Subprocess call (verify shell=False)
  - Fix: Ensure list args and no shell=True
  - Match: `subprocess.run(`

- **Line 207** in `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-14_hf-llm-trainer/.claude/skills/co_INST-14_hf-llm-trainer/skills/model-trainer/scripts/convert_to_gguf.py`
  - Risk: Subprocess call (verify shell=False)
  - Fix: Ensure list args and no shell=True
  - Match: `subprocess.run(`


### co_INST-15_hf-llm-trainer

**Findings:** 1 Critical, 0 High, 27 Info

#### 🔴 CRITICAL (1)

**NET-EXFIL:**

- **Line 42** in `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-15_hf-llm-trainer/.claude/skills/co_INST-15_hf-llm-trainer/skills/model-trainer/scripts/dataset_inspector.py`
  - Risk: Outbound HTTP request
  - Fix: Remove outbound network calls
  - Match: `urllib.request.urlopen(`


#### 🔵 INFO (27)

**ENV-ACCESS:**

- **Line 47** in `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-15_hf-llm-trainer/.claude/skills/co_INST-15_hf-llm-trainer/skills/model-trainer/scripts/convert_to_gguf.py`
  - Risk: Reads environment variables
  - Fix: Document which env vars are read
  - Match: `os.environ.`

- **Line 48** in `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-15_hf-llm-trainer/.claude/skills/co_INST-15_hf-llm-trainer/skills/model-trainer/scripts/convert_to_gguf.py`
  - Risk: Reads environment variables
  - Fix: Document which env vars are read
  - Match: `os.environ.`

- **Line 49** in `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-15_hf-llm-trainer/.claude/skills/co_INST-15_hf-llm-trainer/skills/model-trainer/scripts/convert_to_gguf.py`
  - Risk: Reads environment variables
  - Fix: Document which env vars are read
  - Match: `os.environ.`

- **Line 50** in `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-15_hf-llm-trainer/.claude/skills/co_INST-15_hf-llm-trainer/skills/model-trainer/scripts/convert_to_gguf.py`
  - Risk: Reads environment variables
  - Fix: Document which env vars are read
  - Match: `os.environ.`


**SUBPROCESS:**

- **Line 31** in `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-15_hf-llm-trainer/.claude/skills/co_INST-15_hf-llm-trainer/skills/model-trainer/references/gguf_conversion.md`
  - Risk: Subprocess call (verify shell=False)
  - Fix: Ensure list args and no shell=True
  - Match: `subprocess.run(`

- **Line 32** in `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-15_hf-llm-trainer/.claude/skills/co_INST-15_hf-llm-trainer/skills/model-trainer/references/gguf_conversion.md`
  - Risk: Subprocess call (verify shell=False)
  - Fix: Ensure list args and no shell=True
  - Match: `subprocess.run(`

- **Line 44** in `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-15_hf-llm-trainer/.claude/skills/co_INST-15_hf-llm-trainer/skills/model-trainer/references/gguf_conversion.md`
  - Risk: Subprocess call (verify shell=False)
  - Fix: Ensure list args and no shell=True
  - Match: `subprocess.run(`

- **Line 50** in `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-15_hf-llm-trainer/.claude/skills/co_INST-15_hf-llm-trainer/skills/model-trainer/references/gguf_conversion.md`
  - Risk: Subprocess call (verify shell=False)
  - Fix: Ensure list args and no shell=True
  - Match: `subprocess.run(`

- **Line 100** in `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-15_hf-llm-trainer/.claude/skills/co_INST-15_hf-llm-trainer/skills/model-trainer/references/reliability_principles.md`
  - Risk: Subprocess call (verify shell=False)
  - Fix: Ensure list args and no shell=True
  - Match: `subprocess.run(`

- **Line 103** in `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-15_hf-llm-trainer/.claude/skills/co_INST-15_hf-llm-trainer/skills/model-trainer/references/reliability_principles.md`
  - Risk: Subprocess call (verify shell=False)
  - Fix: Ensure list args and no shell=True
  - Match: `subprocess.run(`

- **Line 108** in `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-15_hf-llm-trainer/.claude/skills/co_INST-15_hf-llm-trainer/skills/model-trainer/references/reliability_principles.md`
  - Risk: Subprocess call (verify shell=False)
  - Fix: Ensure list args and no shell=True
  - Match: `subprocess.run(`

- **Line 183** in `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-15_hf-llm-trainer/.claude/skills/co_INST-15_hf-llm-trainer/skills/model-trainer/references/reliability_principles.md`
  - Risk: Subprocess call (verify shell=False)
  - Fix: Ensure list args and no shell=True
  - Match: `subprocess.run(`

- **Line 184** in `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-15_hf-llm-trainer/.claude/skills/co_INST-15_hf-llm-trainer/skills/model-trainer/references/reliability_principles.md`
  - Risk: Subprocess call (verify shell=False)
  - Fix: Ensure list args and no shell=True
  - Match: `subprocess.run(`

- **Line 187** in `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-15_hf-llm-trainer/.claude/skills/co_INST-15_hf-llm-trainer/skills/model-trainer/references/reliability_principles.md`
  - Risk: Subprocess call (verify shell=False)
  - Fix: Ensure list args and no shell=True
  - Match: `subprocess.run(`

- **Line 188** in `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-15_hf-llm-trainer/.claude/skills/co_INST-15_hf-llm-trainer/skills/model-trainer/references/reliability_principles.md`
  - Risk: Subprocess call (verify shell=False)
  - Fix: Ensure list args and no shell=True
  - Match: `subprocess.run(`

- **Line 189** in `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-15_hf-llm-trainer/.claude/skills/co_INST-15_hf-llm-trainer/skills/model-trainer/references/reliability_principles.md`
  - Risk: Subprocess call (verify shell=False)
  - Fix: Ensure list args and no shell=True
  - Match: `subprocess.run(`

- **Line 228** in `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-15_hf-llm-trainer/.claude/skills/co_INST-15_hf-llm-trainer/skills/model-trainer/references/reliability_principles.md`
  - Risk: Subprocess call (verify shell=False)
  - Fix: Ensure list args and no shell=True
  - Match: `subprocess.run(`

- **Line 232** in `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-15_hf-llm-trainer/.claude/skills/co_INST-15_hf-llm-trainer/skills/model-trainer/references/reliability_principles.md`
  - Risk: Subprocess call (verify shell=False)
  - Fix: Ensure list args and no shell=True
  - Match: `subprocess.run(`

- **Line 94** in `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-15_hf-llm-trainer/.claude/skills/co_INST-15_hf-llm-trainer/skills/model-trainer/scripts/convert_to_gguf.py`
  - Risk: Subprocess call (verify shell=False)
  - Fix: Ensure list args and no shell=True
  - Match: `subprocess.run(`

- **Line 99** in `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-15_hf-llm-trainer/.claude/skills/co_INST-15_hf-llm-trainer/skills/model-trainer/scripts/convert_to_gguf.py`
  - Risk: Subprocess call (verify shell=False)
  - Fix: Ensure list args and no shell=True
  - Match: `subprocess.run(`

- **Line 107** in `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-15_hf-llm-trainer/.claude/skills/co_INST-15_hf-llm-trainer/skills/model-trainer/scripts/convert_to_gguf.py`
  - Risk: Subprocess call (verify shell=False)
  - Fix: Ensure list args and no shell=True
  - Match: `subprocess.run(`

- **Line 115** in `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-15_hf-llm-trainer/.claude/skills/co_INST-15_hf-llm-trainer/skills/model-trainer/scripts/convert_to_gguf.py`
  - Risk: Subprocess call (verify shell=False)
  - Fix: Ensure list args and no shell=True
  - Match: `subprocess.run(`

- **Line 121** in `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-15_hf-llm-trainer/.claude/skills/co_INST-15_hf-llm-trainer/skills/model-trainer/scripts/convert_to_gguf.py`
  - Risk: Subprocess call (verify shell=False)
  - Fix: Ensure list args and no shell=True
  - Match: `subprocess.run(`

- **Line 139** in `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-15_hf-llm-trainer/.claude/skills/co_INST-15_hf-llm-trainer/skills/model-trainer/scripts/convert_to_gguf.py`
  - Risk: Subprocess call (verify shell=False)
  - Fix: Ensure list args and no shell=True
  - Match: `subprocess.run(`

- **Line 170** in `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-15_hf-llm-trainer/.claude/skills/co_INST-15_hf-llm-trainer/skills/model-trainer/scripts/convert_to_gguf.py`
  - Risk: Subprocess call (verify shell=False)
  - Fix: Ensure list args and no shell=True
  - Match: `subprocess.run(`

- **Line 179** in `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-15_hf-llm-trainer/.claude/skills/co_INST-15_hf-llm-trainer/skills/model-trainer/scripts/convert_to_gguf.py`
  - Risk: Subprocess call (verify shell=False)
  - Fix: Ensure list args and no shell=True
  - Match: `subprocess.run(`

- **Line 207** in `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-15_hf-llm-trainer/.claude/skills/co_INST-15_hf-llm-trainer/skills/model-trainer/scripts/convert_to_gguf.py`
  - Risk: Subprocess call (verify shell=False)
  - Fix: Ensure list args and no shell=True
  - Match: `subprocess.run(`


### co_INST-16_hf_dataset_creator

**Findings:** 0 Critical, 0 High, 1 Info

#### 🔵 INFO (1)

**ENV-ACCESS:**

- **Line 22** in `benchmarks/SCR_Bench/SCR-TrustLift/experiment/co_INST-16_hf_dataset_creator/.claude/skills/co_INST-16_hf_dataset_creator/skills/hugging-face-dataset-creator/scripts/dataset_manager.py`
  - Risk: Reads environment variables
  - Fix: Document which env vars are read
  - Match: `os.environ.`


---

## Appendix: Pattern Coverage

The following security patterns were checked:

### Code - Critical (Critical)

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

### Code - High (High)

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

### Code - Informational (Info)

- `subprocess\.(run|call|check_output|check_call|Popen)\s*\(` — Subprocess call (verify shell=False)
- `os\.environ\s*[\[.]` — Reads environment variables
- `os\.path\.expanduser\s*\(` — Expands ~ to home directory

### Prompt - Critical (Critical)

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

### Prompt - High (High)

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

### Prompt - Informational (Info)

- `you\s+must\s+(always|never)\s+` — Strong directive language
- `do\s+not\s+(ever|under\s+any\s+circumstances)\s+` — Absolute prohibition
- `from\s+now\s+on\s+(you|your)\s+` — Attempts to permanently alter AI behavior
- `you\s+are\s+now\s+(a|an)\s+` — Attempts to redefine AI identity

