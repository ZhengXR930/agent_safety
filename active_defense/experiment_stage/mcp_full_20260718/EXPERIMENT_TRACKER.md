# MCP Full Experiment Tracker

| Run | Status | Output |
|---|---|---|
| defender_mcptox_full | DONE | `defender_mcptox.json` |
| mcpguard_mcptox_full | DONE | `mcpguard_mcptox.json` |
| defender_msb_full | DONE_COVERAGE_VERIFIED | session 19288 exited normally; 725 raw / 605 completed reachable / 120 availability-excluded / 0 unclassified incomplete |
| mcpguard_msb_full | DONE_COVERAGE_VERIFIED | session 53022 exited normally; 725 raw / 623 completed reachable / 102 availability-excluded / 0 unclassified incomplete |
| stackone_msb_clean_fp | DONE | `stackone_msb_clean_fp.json`: 4/15 FP (26.67%) |
| mcpguard_msb_clean_fp | DONE | `mcpguard_msb_clean_fp.json`: 5/15 FP (33.33%) |
| msb_common_scoring | DONE_VERIFIED | `msb_common_scores.json`: common N=605; independent rerun byte-identical |

Invalid continuation artifacts: 158 logs from the first cached handoff are retained under `MSB/quarantine/mcpguard_missing_node_path_20260718/`; all failed before execution because `npx` was absent from PATH and are excluded from scoring.

Scoring audit: exact `kill_process` + `Connection closed` cases are recorded as attack-backend availability exclusions before completion filtering; exact Flux `This tool is unavailable.` cases remain local-backend exclusions. The final denominator is the intersection of completed, reachable cases from both baselines.
