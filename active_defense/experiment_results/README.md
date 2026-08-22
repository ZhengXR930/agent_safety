# Canonical Experiment Results

This directory keeps the reviewable result surface used by `Discussion.md`.
Intermediate smoke runs, prompt-search attempts, stale generated indexes, and
large runtime work directories have been removed when they were not needed to
support the reported tables.

The retained layout is benchmark-owned:

- `<benchmark>/<method>/<defense-model>/` for original benchmark results.
- `ablation_original/DeepSeek_refactor/` for Thread #11 WRAP/PLANT ablations.
- `ASB-OPI/AutoDojoStyle/GPT5.4_vs_DeepSeek/*_T4_full400_reuse191/` for the
  Tool-unit adaptive attack table.
- `SkillInject/SkillJect-fusion/official_scripted45_all_baselines*` and
  `SCR/SkillJect-fusion/official_composition_capflow_*` for SkillJect-style
  adaptive results.
- `mcptox/*mcp_itp_template2_v5_full455*` and
  `MSB/*mcp_itp_payloadaware_v2*full212*` for MCP-ITP-style adaptive results.

The target model for the reported results is DeepSeek V4 Flash.  Adaptive attack
generation artifacts use the attacker-model directory names recorded in their
paths.  `Discussion.md` is the authoritative map from reported numbers to the
retained artifacts.
