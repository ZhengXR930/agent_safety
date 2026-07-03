# Important Artifacts

This directory contains many historical scratch outputs.  For the current active-defense framework,
use the files below as the small working set.

## Current Core Results

- `engine_agentdojo_<suite>_gpt-4o-mini-2024-07-18.json`  (suite ∈ banking / slack / travel / workspace)
  - AgentDojo run through the **generic Engine** — the real role chain (Surveyor → Enricher →
    Camoufleur/Distinguisher → WrapPlanner → TaskAllowance → Detector), driven by deepseek; AgentDojo's
    OWN gpt-4o-mini pipeline is the benchmark agent (defense and benchmark-agent are separated).
  - ONE deployment per suite reused across every (user_task × injection_task) — the attack-agnostic claim.
  - **Supersedes** the removed bespoke `run_agentdojo_ours.py` (which reimplemented detection outside the
    Engine).  Head-to-head vs Progent / undefended baseline: see `LOGS/2026-W27.md` EXP-2026W27-008.

- `mcptox_wrap_deepseek-chat.json`
  - MCP WRAP validation on MCPTox.
  - Shows off-scope MCP tool calls are caught when harm actually crosses the mediated MCP boundary.

- `msb_wrap_deepseek-chat.json`
  - MCP WRAP validation on MSB.
  - Shows response-injection-induced off-scope sink calls are caught by the MCP mediator.

- `mcpguard_baseline_mcptox.json`
  - MCPGuard baseline comparison on MCPTox.
  - Keep as the main baseline artifact for MCP-side discussion.

- `mcpguard_msb.json`
  - MCPGuard baseline comparison on MSB.
  - Keep as the main baseline artifact for MSB-side discussion.

- `mcpitp_vs_mcpguard.json`
  - Comparison artifact for MCP ITP vs MCPGuard.
  - Keep if discussing external MCP baselines.

- `progent_vs_wrap_mcptox_deepseek-chat.json`
  - Progent-style least-privilege baseline vs WRAP-on-MCP.
  - Useful for explaining prevention/utility-loss tradeoffs versus our detection framing.

## Current Generic Engine Smoke Results

Keep only the latest representative generic-engine outputs unless a specific old run is cited in
`LOGS/`.

- `engine_capflow_deepseek-chat_20260629_235424.json`
- `engine_skillinject_deepseek-chat_20260630_150522.json`
- `engine_agentdojo_banking_gpt-4o-mini-2024-07-18.json` (and slack / travel / workspace — see Core Results)

## Historical / Scratch Outputs

The remaining files are mostly intermediate probes, old phase outputs, or raw debugging artifacts:

- `agentdojo_ours_*.json` — bespoke pre-Engine AgentDojo runner outputs (runner removed; kept only because
  `LOGS/` EXP-2026W27-006/007 cite them as history — do NOT use as current evidence)
- `phase2_*`
- `full_asr_*`
- `defense_*`
- `*_probe.json`
- `*_feasibility*.json`
- `mediation_batch.json`
- `wrap_mediation_e2e.json`
- old `tsbench_*`

Do not use these as the primary evidence for the current refactored framework unless a LOG entry or
paper section explicitly cites them.  They can be archived after confirming no active `LOGS/` or
`Discussion.md` reference needs live access.
