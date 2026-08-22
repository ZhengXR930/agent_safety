# Experiment Results Cleanup Report

Date: 2026-08-22 (Asia/Shanghai)

This cleanup keeps `experiment_results/` aligned with the result artifacts cited
by `Discussion.md`.  The repository had accumulated old fusion workspaces,
adaptive-attack prompt probes, smoke runs, stale manifests, and runtime work
directories.  Those were removed when their final metrics or merged replay files
already exist in the retained benchmark folders.

## Removed In This Pass

- `fusion_eval_20260814/` and `fusion_eval_20260818/`; the final SCR merge note
  was copied to `SCR/SkillJect-fusion/` before deletion.
- `LaunderingBench/`, which was a non-reported pilot.
- `ASB-OPI-tasknum1-pilot-20260814/` and old ASB rerun/smoke directories that
  were superseded by the final ASB-OPI results.
- AgentDojo AdapTools and AutoDojo exploratory directories.  The reported
  Tool-unit adaptive result is the ASB-OPI AutoDojoStyle T4 full-400 run.
- SkillInject SkillJect smoke, v2/v3 prompt-search, affected-case rerun, and
  non-final fusion-cache directories.
- SCR smoke/full-fusion generation caches and non-final Ours runtime `work/`
  artifacts.
- MCPTox/MSB MCP-ITP smoke, limit, and prompt-search files.  Full adaptive
  payloads, logs, and replay files were kept.
- Stale generated `INDEX.json`, `VALIDATION.json`, and `SHA256SUMS`; they no
  longer matched the cleaned tree.

## Retained Boundary

Retained artifacts are the current `Discussion.md` evidence surface:

- Original benchmark results under `AgentDojo/`, `ASB-OPI/`, `MCPTox/`, `MSB/`,
  `SCR/`, and `SkillInject/`.
- Original-benchmark WRAP/PLANT ablation results under
  `ablation_original/DeepSeek_refactor/`.
- Adaptive results for ASB-OPI AutoDojoStyle, SkillInject/SCR SkillJect-fusion,
  and MCPTox/MSB MCP-ITP.

After cleanup, all explicit `experiment_results/...` references in
`Discussion.md` resolve successfully.
