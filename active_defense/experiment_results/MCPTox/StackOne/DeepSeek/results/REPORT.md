# MCPTox StackOne End-to-End — DeepSeek V4 Flash

## Protocol

- Target: `deepseek-v4-flash`.
- Judge: `gpt-5.4-2026-03-05`.
- StackOne: upstream commit `0d56b92`, `blockHighRisk=true`.
- Boundary: StackOne filters the MCP catalog before target inference; the
  target produces a fresh call from the remaining catalog.
- Denominators: 357 unique clean server-query tasks and all 1,348 released
  attack instances.
- No historical MCPTox model labels are read when computing BU, AU, or ASR.

## Result

| Metric | Count | Rate |
|---|---:|---:|
| Benign Utility | 49/357 | 13.73% |
| Utility under Attack | 179/1348 | 13.28% |
| Attack Success Rate | 13/1348 | 0.96% |
| Clean no-proposal | 328/357 | 91.88% |
| Attack no-proposal | 1205/1348 | 89.39% |
| Technical errors | 0/1705 | 0.00% |

Task completion and malicious success are disjoint in this run, so safe AU is
also 179/1348.  At least one catalog tool was blocked in every clean task and
in 1,346/1,348 attack instances.  The low residual ASR therefore comes with a
large end-to-end utility loss that the earlier per-tool clean-allow metric did
not expose.

## Artifacts

- `results.json`: complete per-case target responses, StackOne decisions, and
  judge verdicts.
- `stackone_scan_cache.json`: content-addressed StackOne scan cache.
- `full.log`: checkpoint progress.
- `smoke2.json`: pre-full 2-clean/2-attack wiring check.

`results.json` SHA-256:
`1689df9984d3f4f13e2b48e9f490786e3f6e6359c241754c38a0c8892aaf469c`.
