# Skills Security Scan Report

**Date:** 2026-06-25 21:07:04
**Project:** agent_safety

## Executive Summary

| Metric | Value |
|--------|-------|
| **Overall Security Score** | **100/100** |
| Total Critical Findings | 0 |
| Total High Findings | 0 |
| Total Informational Findings | 0 |
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
| Active Defense - Experiment Skills | 82 | 0 | 0 | 0 | 🟢 |
| Project Core Skills | 3 | 0 | 0 | 0 | 🟢 |
| Registry - Other Skills | 2 | 0 | 0 | 0 | 🟢 |
| Registry - Skills | 1 | 0 | 0 | 0 | 🟢 |
| TrustLift - Experiment Skills | 47 | 0 | 0 | 0 | 🟢 |

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

