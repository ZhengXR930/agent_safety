# Experiment Audit Report

**Date**: 2026-07-19  
**Auditor**: Codex  
**Independence**: unavailable (chat2api unavailable; no subagent authorized)  

## Overall Verdict: PASS WITH SCOPE CAVEAT

- Ground truth provenance: PASS for MCPTox official DeepSeek-v3 per-instance labels and MSB official environment/log scorer.
- Score normalization: PASS; all denominators and raw counts are reported.
- Result existence: PASS for both MCPTox cells and both maximal-reachable MSB cells.
- Dead code: PASS for completed metrics paths.
- Scope: PASS WITH CAVEAT; MSB covers every completed case available after the user-approved 21-server skip and exact evidenced backend failures, but is not the globally connected all-server benchmark.
- Evaluation type: MCPTox `real_gt + offline_replay`; MSB maximal-reachable subset `real_gt/end-to-end`.

## Integrity caveats

- MCP-Guard emits stage-3 `NoneType` formatting warnings when its upstream router prints a safe model result whose optional score is absent. Inspection of the source and 9,796/9,796 recorded events confirms that every call still returned an explicit `allowed` decision; the warnings and detector logs are retained as an upstream implementation caveat.
- MCPTox contains 362 parsed clean tool blocks versus 353 declared tool names.
- The original MSB scorer used Windows-only path substrings for retrieval PUA; it was changed to basename matching. Before the fix the same successful task was False, after the fix True.
- No ASR/PUA value is assigned to the 21 user-approved OAuth/firewall exclusions or to cases with proven MCP infrastructure failure. Exact `kill_process` + `Connection closed` cases are labeled attack-backend unavailable before completion filtering; exact Flux `This tool is unavailable.` cases are labeled local-backend unavailable.
- Exact duplicate detector inputs may reuse a deterministic decision within one process; every logical call still emits an event, preserving FP denominators.
- Final MSB acceptance passed: each baseline has 725 raw unique runner cases and zero unclassified incomplete cases. StackOne has 605 completed/120 availability-excluded; MCP-Guard has 623/102; scoring uses their 605-key completed-reachable intersection.
- The scorer was rerun independently after process exit and produced a byte-identical JSON file with SHA-256 `997700f8ce9e686cebe4287d81d2b9e23c552e1df810d984673e6ac99ee2a0ed`. Clean FP rows were also counted directly: StackOne 4/15 and MCP-Guard 5/15.
