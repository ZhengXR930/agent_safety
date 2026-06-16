# Adaptive Attack Evaluation Plan

**Date**: 2026-06-11

**Status**: authoritative planning document for the large-scale adaptive-attack evaluation. Other experiment-stage planning docs are legacy and should not be used as source of truth.

## Goal

Evaluate whether existing adaptive attack methods can bypass public tool-use / agent safety defenses across three risk surfaces:

1. **Authority**: untrusted external content or tool output attempts to authorize an action the user did not request.
2. **Value**: untrusted values flow into sensitive tool arguments, e.g. recipient, URL, account id, file id, payload, amount.
3. **Policy / user-harmfulness**: trusted user intent itself requests harmful, illegal, deceptive, privacy-invasive, or otherwise disallowed behavior.

The claim is not that one attack breaks one guard. The claim we need evidence for is:

> Existing adaptive attack methods transfer across realistic attacker-controlled fields and can bypass public agent/tool-use defenses under authority, value, and policy risk surfaces.

## Dataset / Benchmark Matrix

Use public benchmarks only for main claims. Synthetic data can be used only for debugging, not headline numbers.

| Benchmark | Public Source | Controlled Fields / Surfaces | Risk Coverage | Main Use |
|---|---|---|---|---|
| **ASB / Agent Security Bench** | `benchmarks/ASB`, https://github.com/agiresearch/ASB | direct user prompt, observation/tool output, memory DB, mixed attack fields, prompt-as-tool / tool trigger fields | authority, value, policy | Primary end-to-end rollout benchmark for DPI / OPI / Memory / PoT / Mixed. |
| **AdaptiveAttackAgent / InjecAgent** | `benchmarks/AdaptiveAttackAgent`, https://github.com/uiuc-kang-lab/AdaptiveAttackAgent | injected tool response / indirect prompt injection string | authority, value | Primary official adaptive IPI benchmark with GCG/MGCG/TGCG. Direct-harm injected tool responses are authority-primary because the attacker-controlled source is external, not trusted user intent. |
| **AgentDojo** | `benchmarks/agentdojo`, https://github.com/ethz-spylab/agentdojo | untrusted tool/web/email/file content in agent tasks | authority, value | Public agent environment for OPI and built-in public defense configs. |
| **ToolSafe / TS-Bench** | `benchmarks/ToolSafe`, TS-Guard / ToolSafe paper | step-level tool invocation traces | authority, value, policy step-risk | Public step-level guard benchmark / TS-Guard evaluation. |
| **HarmBench** | `benchmarks/HarmBench`, https://github.com/centerforaisafety/HarmBench | direct harmful behavior prompts, multimodal harmful behavior prompts | policy | Public policy / harmfulness red-team baseline suite. |
| **AdvBench / JailbreakBench-style subsets** | via PAIR/TAP/HarmBench repos | direct harmful prompts | policy | Lightweight sanity for PAIR/TAP policy setting. |
| **AdapTools benchmark** | paper only currently, https://arxiv.org/abs/2602.20720 | tool-based indirect injection, tool selection / tool relevance fields | authority, value | Candidate 2026 baseline. Use only after official code search is documented or full paper reproduction is scoped. |

## Defense Baselines

Defense baseline means an existing public method or official benchmark defense implementation. Our adapters are not baselines.

### Main Public Method Baselines

| Defense Method | Public Source | Layer | Benchmark Fit | Include |
|---|---|---|---|---|
| **TS-Guard** | ToolSafe / TS-Bench, `MurrayTom/TS-Guard` | step-level tool invocation guard | ToolSafe / AgentDojo-derived tool-step traces | Main step-level public guard baseline. |
| **PromptGuard 2 / LlamaFirewall** | https://arxiv.org/abs/2505.03574 | detector / guardrail for prompt injection and jailbreak | DPI / OPI text and extracted traces | Main public detector baseline if setup is stable. |
| **DataFilter** | https://github.com/yizhu-joy/DataFilter, https://arxiv.org/abs/2510.19207 | data purification before LLM sees untrusted content | OPI / tool-output / memory text | Main plug-in purification baseline if dependency setup is stable. |
| **StruQ** | https://github.com/Sizhe-Chen/StruQ, https://arxiv.org/abs/2402.06363 | structured prompt/data channel plus trained model | prompt-injection tasks; possible OPI adaptation | Optional heavy baseline because it changes prompt/model protocol. |
| **CaMeL** | https://arxiv.org/abs/2503.18813 | system-level control/data-flow isolation with capabilities | AgentDojo-style authority/value tasks | Optional heavy baseline because it changes agent architecture. |
| **FIDES** | cited as an IFC-style baseline in NeuroTaint / TaintBench work; no public code found in current search | information-flow-control style source/sink tracking | value / authority provenance | Required but deferred. Keep in final baseline set, but do not block Phase 1 until paper details and a reproducible implementation plan are located. |

### Benchmark-Native Defense Configs

These are useful for reproducing benchmark papers, but they should be described as **benchmark-native defense configs**, not as standalone method baselines unless the paper/method is cited separately.

| Suite | Configs | Role |
|---|---|---|
| **AgentDojo built-in configs** | `tool_filter`, `transformers_pi_detector`, `repeat_user_prompt`, `spotlighting_with_delimiting` | Reproduce AgentDojo-style defense comparisons. Some are simple configs or prompt hardening strategies; do not overclaim as independent methods. |
| **ASB official configs** | `delimiters_defense`, `instructional_prevention`, `direct_paraphrase_defense`, `dynamic_prompt_rewriting`, `ob_sandwich_defense`, `pot_paraphrase_defense`, `pot_shuffling_defense`, memory detectors | Reproduce ASB paper baselines inside ASB only. `delimiters_defense` and related entries are strategies/configs, not standalone method baselines. |
| **AdaptiveAttackAgent official configs** | `LLMDetector`, `FinetunedDetector`, `InstructionalPrevention`, `DataPromptIsolation`, `SandwichPrevention`, `Paraphrasing`, `PerplexityFiltering`, `AdvFT` where supported | Reproduce AdaptiveAttackAgent paper. Treat as official IPI defense suite, not all as independent methods. |

### Non-Baseline Targets

| Target | Role |
|---|---|
| authority adapter | Our method / ablation. |
| value adapter | Our method / ablation. |
| boundary adapter | Our method / ablation. |
| internal GPT-5.x judge/guard prompts | Evaluator or proprietary stress target, not public baseline. |
| PRAC | Not included. No stable public paper/code entry found in current search; do not reproduce unless a concrete public source is identified. |

## Attack Baselines

Attack baseline means an existing attack method or official benchmark attack suite. Attack methods are not tied to one risk category; they enter a surface when the attacker-controlled field and judge are valid.

| Attack Method | Public Source | Default Setting | Candidate Surfaces | Include |
|---|---|---|---|---|
| **PAIR** | `baselines/PAIR-official`, https://github.com/patrickrchao/JailbreakingLLMs | direct harmful prompt jailbreak | DPI, OPI, Memory, PoT/tool spec when the controlled field is text and a judge exists | Yes, cross-surface after applicability check. Existing AgentDojo/ToolSafe OPI evidence is valid. |
| **TAP** | `baselines/TAP-official`, https://github.com/RICommunity/TAP | direct harmful prompt jailbreak | DPI, OPI, Memory, PoT/tool spec when the controlled field is text and a judge exists | Yes, cross-surface after applicability check. |
| **GCG / MGCG_ST / MGCG_DT / TGCG** | `benchmarks/AdaptiveAttackAgent`, https://github.com/uiuc-kang-lab/AdaptiveAttackAgent | indirect prompt injection over InjecAgent | OPI/IPI; potentially other local-model text fields | Yes, primary adaptive IPI baseline. |
| **HarmBench official attacks** | https://github.com/centerforaisafety/HarmBench | direct harmful policy red teaming | DPI / policy; possible transfer only after controlled-field validation | Yes for policy baseline. |
| **ASB official attacks** | `benchmarks/ASB`, https://github.com/agiresearch/ASB | benchmark-native DPI/OPI/Memory/PoT/Mixed | ASB-native surfaces | Yes, first ASB baseline. |
| **AdapTools** | https://arxiv.org/abs/2602.20720 | adaptive tool-based IPI | OPI, PoT/tool spec, MCP-style tool surfaces | Candidate; no official code found yet. |

## PAIR / TAP Applicability Rule

PAIR and TAP are black-box semantic search / tree-search methods, not policy-only attacks.

For each benchmark surface, include PAIR/TAP only if all four fields are explicit:

| Required Field | Meaning |
|---|---|
| controlled field | user prompt, tool observation, memory entry, tool description/name/trigger, or other attacker-owned text |
| objective | malicious tool execution, exfiltration, unsafe step ALLOW, harmful response/action, or defense bypass |
| judge | official evaluator, rule check, model judge, rollout success, or step guard decision |
| budget | attacker model calls, target calls, rollout attempts, tree width/depth |

If any field is missing, the PAIR/TAP cell is `INVALID`, not a failed experiment.

## Core Experiment Matrix

| Track | Benchmark | Attack Baseline | Defense Baseline / Target | Risk Surface | Status |
|---|---|---|---|---|---|
| ASB-native | ASB | ASB official DPI/OPI/Memory/Mixed/PoT | ASB official configs, then public method baselines where portable | authority, value candidate, policy | sanity done; needs seeded sweep. |
| IPI-adaptive | AdaptiveAttackAgent / InjecAgent | GCG, MGCG_ST, MGCG_DT, TGCG | AdaptiveAttackAgent official defense suite | authority, value, direct-harm subset | blocked on durable model path / active worker. |
| AgentDojo-public-defense | AgentDojo | official attacks plus PAIR/TAP where valid | AgentDojo built-in configs; optional DataFilter / PromptGuard 2 | authority, value | planned. |
| Step-guard | ToolSafe / AgentDojo-derived traces | official attack outputs and existing PAIR OPI outputs | TS-Guard; our adapters as ablations | authority, value, policy step-risk | existing PAIR/TS-Guard evidence reused. |
| Policy-redteam | HarmBench / AdvBench-style | HarmBench official methods, PAIR, TAP, GCG, AutoDAN where official | HarmBench classifier / target refusal / PromptGuard 2 where applicable | policy | data layer ready; attack/defense runs pending. |
| Cross-surface PAIR/TAP | AgentDojo, ASB, HarmBench, memory/PoT subsets | PAIR, TAP | public defenses or step-level evaluator depending cell | authority, value, policy | applicability manifest needed before runs. |
| AdapTools-parity | AdapTools paper benchmark if reproducible | AdapTools | tool relevance / agent tool guards reported by paper | authority, value | candidate only. |

## Unified Benchmark Data Layer

The adapter benchmark layer is represented by
`adapter_defense/experiment-stage/adaptive_attack_eval/benchmark_manifest.jsonl`.
The scripts read shared source benchmarks from the repository-level
`benchmarks/` directory.

Builder / validator:

```bash
python adapter_defense/code/build_benchmark_manifest.py
python adapter_defense/code/validate_benchmark_manifest.py
python adapter_defense/code/audit_benchmark_taxonomy.py
```

Defense adapter dry-run:

```bash
python adapter_defense/code/defense_runner_adapter.py --defense TS-Guard --limit 5 --out adapter_defense/experiment-stage/adaptive_attack_eval/defense_adapter_tsguard_dryrun.jsonl
python adapter_defense/code/defense_runner_adapter.py --defense PromptGuard2_LlamaFirewall --limit 5 --out adapter_defense/experiment-stage/adaptive_attack_eval/defense_adapter_promptguard_dryrun.jsonl
python adapter_defense/code/defense_runner_adapter.py --defense DataFilter --limit 5 --out adapter_defense/experiment-stage/adaptive_attack_eval/defense_adapter_datafilter_dryrun.jsonl
python adapter_defense/code/defense_runner_adapter.py --defense FIDES_deferred --limit 5 --out adapter_defense/experiment-stage/adaptive_attack_eval/defense_adapter_fides_dryrun.jsonl
```

Current validated coverage:

| Field | Count |
|---|---:|
| total rows | 13068 |
| ASB | 6120 |
| AdaptiveAttackAgent / InjecAgent | 2108 |
| AgentDojo | 1247 |
| HarmBench | 510 |
| ToolSafe | 3083 |
| DPI | 2550 |
| OPI | 4175 |
| PoT | 2040 |
| Step | 4303 |
| authority risk tags | 7302 |
| value risk tags | 5925 |
| policy risk tags | 4501 |
| clean rows | 1250 |

Benchmark-by-category full-count audit:

Each row has one `primary_attack_category`, so `Authority + Value + Policy + Clean / Other` must equal `Manifest Total`.

| Benchmark | Source Components Checked | Expected Total | Manifest Total | Authority | Value | Policy | Clean / Other | Split Sum | Full Count OK |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| ASB | matched task-tool pairs=2040<br>surfaces per task-tool=3 | 6120 | 6120 | 4080 | 0 | 2040 | 0 | 6120 | yes |
| AdaptiveAttackAgent | direct_harm base=510<br>direct_harm enhanced=510<br>data_stealing base=544<br>data_stealing enhanced=544 | 2108 | 2108 | 2108 | 0 | 0 | 0 | 2108 | yes |
| AgentDojo | TS-Bench banking=87<br>TS-Bench slack=101<br>TS-Bench travel=177<br>TS-Bench workspace=855<br>static injection templates=27 | 1247 | 1247 | 379 | 0 | 0 | 868 | 1247 | yes |
| HarmBench | text all=400<br>multimodal all=110 | 510 | 510 | 0 | 0 | 510 | 0 | 510 | yes |
| ToolSafe | AgentSafetyBench released=2000<br>TS-Bench AgentHarm harmful steps=525<br>TS-Bench AgentHarm benign steps=206<br>AgentHarm public harmful=176<br>AgentHarm public benign=176 | 3083 | 3083 | 735 | 383 | 1583 | 382 | 3083 | yes |

Schema contract per row:

| Field Group | Purpose |
|---|---|
| `taxonomy_labels` | Four-tuple sample annotation: `{clean,value,authority,policy,rationale}` plus primary category and review status. |
| `text_fields` | Normalized trusted / untrusted text spans for PromptGuard 2 / LlamaFirewall and DataFilter. |
| `step_candidate` | Candidate tool name, args, and thought/context for TS-Guard-style step-level guards. |
| `provenance` | Source type, trust, sink type, target sink, and candidate value-flow metadata for FIDES-style IFC reproduction. |
| `compatible_defenses` | Defense methods/configs that can consume the row without changing the benchmark layer. |
| `attack_baselines` | Attack methods with valid or candidate controlled-field applicability for the row. |

Taxonomy audit artifacts:

| Artifact | Purpose |
|---|---|
| `adapter_defense/experiment-stage/adaptive_attack_eval/benchmark_taxonomy_audit.md` | Human-readable source-count, primary split, four-tuple count, fit, and review-status report. |
| `adapter_defense/experiment-stage/adaptive_attack_eval/benchmark_taxonomy_labels.jsonl` | Compact per-row sample label export with `{clean,value,authority,policy,rationale}`. |
| `adapter_defense/experiment-stage/adaptive_attack_eval/benchmark_taxonomy_review_samples.jsonl` | Rows whose secondary value-flow tags are usable but heuristic and need later manual review. |
| `adapter_defense/experiment-stage/adaptive_attack_eval/benchmark_taxonomy_audit_summary.json` | Machine-readable audit summary. |

Notes:

- HarmBench is included from the official local clone at `benchmarks/HarmBench`: `harmbench_behaviors_text_all.csv` has 400 behaviors and `harmbench_behaviors_multimodal_all.csv` has 110 behaviors, for 510 policy-primary rows.
- AgentDojo rows include 27 statically extracted v1 injection task `GOAL` templates plus 1220 TS-Bench AgentDojo step trajectories from `benchmarks/ToolSafe/TS-Bench/agentdojo-traj/{banking,slack,travel,workspace}.json`. The static templates avoid runtime import issues in the local checkout; the TS-Bench rows are the step-level data consumed by TS-Guard-style evaluation.
- AdaptiveAttackAgent / InjecAgent rows use full local `base` and `enhanced` DH/DS files: direct_harm base=510, direct_harm enhanced=510, data_stealing base=544, data_stealing enhanced=544.
- ToolSafe rows include AgentSafetyBench released=2000, TS-Bench AgentHarm harmful steps=525, TS-Bench AgentHarm benign steps=206, AgentHarm harmful test public=176, and AgentHarm benign test public=176 clean rows for false-block evaluation. AgentSafetyBench is split into all three attack surfaces: `fulfillable=1` rows are authority-primary tool-permission/action-boundary risks; property loss, sensitive data leak, and availability rows are value-primary when not authority-primary; misinformation, harmful code, law/ethics, and physical harm rows are policy-primary when not authority-primary. Secondary `risk_categories` preserve the official value/policy risk tags.
- ASB rows use all matched task-tool pairs from `agent_task.jsonl` and `all_attack_tools.jsonl`; `academic_search_agent` has 6 tasks, so the full ASB manifest is 2040 matched task-tool pairs x 3 surfaces = 6120 rows.
- FIDES remains `FIDES_deferred`: the adapter emits source/sink provenance payloads now, but no claim should be made until the actual FIDES reproduction is implemented.
- Benchmark-by-category tables are generated at `experiment-stage/adaptive_attack_eval/benchmark_attack_category_table.md`.

## Metrics

| Metric | Definition |
|---|---|
| ASR | attacker objective success rate. |
| Utility / original task success | benchmark-defined benign task success under no attack and under attack. |
| Step unsafe allow rate | unsafe proposed tool calls classified as ALLOW by step-level guard. |
| Clean false block rate | benign or task-authorized actions blocked by guard/defense. |
| Query / rollout budget | attacker model calls, target calls, local optimization steps, rollout attempts. |
| Transfer | attack generated against one target evaluated against another defense/guard. |
| Applicability validity | whether the attack method is valid for the controlled field and judge. |

## Execution Order

1. Build `pair_tap_applicability.md`: one row per candidate surface with controlled field, objective, judge, budget, and validity.
2. Run ASB seeded sweep with ASB-native attacks and ASB-native configs. Keep configs labeled as benchmark configs, not method baselines.
3. Add portable public method baselines where implementation is stable: TS-Guard for steps, PromptGuard 2 / LlamaFirewall for detector, DataFilter for OPI purification.
4. Re-run or reuse AgentDojo/ToolSafe PAIR OPI evidence; extend PAIR/TAP only to valid OPI/Memory/PoT cells.
5. Run HarmBench policy track with official attacks and public policy/detector baselines.
6. Resume AdaptiveAttackAgent after a durable `Llama-3.1-8B-Instruct` path is verified; do not launch full 100-case/500-step GCG without confirming GPU budget.
7. Evaluate our authority/value/boundary adapters only as our method / ablation, not as public defense baselines.

## Required Configuration

| Component | Required Config | Status / Notes |
|---|---|---|
| Internal GPT-compatible API | `config.txt` with `OPENAI_API_KEY`; internal endpoint handled by local adapters | Available. Do not print secrets. |
| DeepSeek API | `config.txt` with `DEEPSEEK_API_KEY` | Available for ASB/auxiliary sanity if needed. |
| Hugging Face token | `HF_TOKEN` env var or `~/.cache/huggingface/token` / `~/.huggingface/token` / `~/.autoresearch/secrets/huggingface_token` | Required for gated Meta models. User has accepted `meta-llama/Llama-3.1-8B-Instruct` license. |
| AdaptiveAttackAgent Llama model | local path basename must be exactly `Llama-3.1-8B-Instruct` | Download script: `code/download_adaptive_attack_agent_llama31.sh`; target path defaults to `/mnt/local/localcache00/agent_safety_models/Llama-3.1-8B-Instruct` on worker. |
| Worker for local model attacks | A800 worker preferred | `mlx worker login <worker_id> -- bash code/download_adaptive_attack_agent_llama31.sh`; full attack likely needs explicit budget confirmation. |
| PAIR/TAP | internal GPT client patch; `WANDB_MODE=disabled` unless logging is desired | Pending. |
| PromptGuard 2 / LlamaFirewall | HF model access and detector runner | Pending. |
| DataFilter | repo/model/dependencies | Pending. |
| FIDES | paper details and reproducible implementation plan | Required but deferred. |

## Existing Evidence To Reuse

| Evidence | Path | Interpretation |
|---|---|---|
| PAIR on AgentDojo/ToolSafe OPI vs TS-Guard | `code/results/pair_source_span_tsguard_182_proxy_thought_deepseek/summary.json` | Shows PAIR is not policy-only and can work on indirect PI. |
| PAIR on ASB OPI weak result | `code/results/pair_asb_opi_output_span_tsguard_50_source_only/summary.json` | Shows surface-specific design matters; not all PAIR ports are valid/effective. |
| ASB small sanity | `experiment-stage/official_repro/asb/sanity_summary.json` | Confirms runner works; full seeded sweep still needed. |
| AdaptiveAttackAgent status | `experiment-stage/official_repro/adaptive_attack_agent/repro_status.md` | Official code ready; model path / worker persistence blocker remains. |

## Stop Conditions

- Do not count benchmark configs like `delimiters_defense` as standalone defense methods.
- Do not count our adapters as public defense baselines.
- Do not treat PAIR/TAP as policy-only.
- Do not run a PAIR/TAP cell unless controlled field, objective, judge, and budget are explicit.
- Do not use synthetic-only data for headline claims.
- Do not launch AdaptiveAttackAgent full run if expected GPU time exceeds 2h without explicit confirmation.
