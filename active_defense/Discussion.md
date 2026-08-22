# Discussion

## DISC-2026W33-003 · Thread #9: DeepSeek Target + DeepSeek Defense Benchmark Comparison

Status: Open  
Updated: 2026-08-18  

### AgentDojo

| Schema | BU | AU | ASR |
|---|---:|---:|---:|
| Ours | 84/97 (86.6%) | 505/629 (80.3%) | **0/629 (0.0%)** |
| Undefended | 86/97 (88.7%) | 464/629 (73.8%) | 107/629 (17.0%) |
| DRIFT | 74/97 (76.3%) | 384/629 (61.0%) | 12/629 (1.9%) |
| CaMeL | 74/97 (76.3%) | 471/629 (74.9%) | 7/629 (1.1%) |
| Progent | 85/97 (87.6%) | 489/629 (77.7%) | 4/629 (0.6%) |
| MELON | 50/97 (51.5%) | 245/629 (39.0%) | 4/629 (0.6%) |
| Tool Filter | 21/97 (21.6%) | 141/629 (22.4%) | 1/629 (0.2%) |
| Spotlighting | **92/97 (94.8%)** | **547/629 (87.0%)** | 1/629 (0.2%) |
| AgentShield | 81/97 (83.5%) | 502/629 (79.8%) | 3/629 (0.5%) |

### ASB-OPI

| Schema | BU | AU | ASR |
|---|---:|---:|---:|
| Ours | 46/51 (90.2%) | **1735/2040 (85.0%)** | **0/2040 (0.0%)** |
| Undefended | 45/51 (88.2%) | 1453/2040 (71.2%) | 1220/2040 (59.8%) |
| CaMeL | 45/51 (88.2%) | 1471/2040 (72.1%) | 281/2040 (13.8%) |
| DRIFT | 24/51 (47.1%) | 776/2040 (38.0%) | 200/2040 (9.8%) |
| MELON | 43/51 (84.3%) | 1640/2040 (80.4%) | 275/2040 (13.5%) |
| Spotlighting | **47/51 (92.2%)** | 1266/2040 (62.1%) | 1043/2040 (51.1%) |
| Tool Filter | 24/51 (47.1%) | 1038/2040 (50.9%) | 312/2040 (15.3%) |
| Progent | 27/51 (52.9%) | 962/2040 (47.2%) | 291/2040 (14.3%) |
| AgentShield | 42/51 (82.4%) | 1252/2040 (61.4%) | 867/2040 (42.5%) |

### SkillInject

| Schema | BU | AU | ASR |
|---|---:|---:|---:|
| Ours | 146/180 (81.1%) | 142/180 (78.9%) | **1/180 (0.6%)** |
| Undefended | **148/180 (82.2%)** | **150/180 (83.3%)** | 52/180 (28.9%) |
| ClawGuard | 82/180 (45.6%) | 82/180 (45.6%) | 13/180 (7.2%) |
| Progent | 115/180 (63.9%) | 113/180 (62.8%) | 28/180 (15.6%) |
| TaskShield | 96/180 (53.3%) | 105/180 (58.3%) | 10/180 (5.6%) |

### SCR

| Schema | BU | AU | ASR |
|---|---:|---:|---:|
| CapFlow · Ours | 127/150 (84.7%) | **149/150 (99.3%)** | **0/150 (0.0%)** |
| CapFlow · Undefended | 120/150 (80.0%) | 93/150 (62.0%) | 90/150 (60.0%) |
| CapFlow · ClawGuard | 0/150 (0.0%) | 131/150 (87.3%) | **0/150 (0.0%)** |
| CapFlow · Progent | **144/150 (96.0%)** | 56/150 (37.3%) | 92/150 (61.3%) |
| CapFlow · TaskShield | 118/150 (78.7%) | 75/150 (50.0%) | 63/150 (42.0%) |
| AuthBlur · Ours | 115/116 (99.1%) | **116/116 (100.0%)** | **0/116 (0.0%)** |
| AuthBlur · Undefended | **116/116 (100.0%)** | **116/116 (100.0%)** | 84/116 (72.4%) |
| AuthBlur · TaskShield | **116/116 (100.0%)** | 115/116 (99.1%) | 82/116 (70.7%) |
| AuthBlur · DynamicGuardian | **116/116 (100.0%)** | **116/116 (100.0%)** | 84/116 (72.4%) |
| TrustLift · Ours | **401/401 (100.0%)** | **401/401 (100.0%)** | **0/401 (0.0%)** |
| TrustLift · Undefended | **401/401 (100.0%)** | **401/401 (100.0%)** | 401/401 (100.0%) |
| TrustLift · ClawGuard | 26/401 (6.5%) | 26/401 (6.5%) | 26/401 (6.5%) |
| TrustLift · Progent | **401/401 (100.0%)** | **401/401 (100.0%)** | 401/401 (100.0%) |
| TrustLift · TaskShield | 325/401 (81.0%) | 315/401 (78.6%) | 315/401 (78.6%) |

### MCPTox

| Schema | BU | AU | ASR |
|---|---:|---:|---:|
| Ours | 231/357 (64.7%) | **1015/1348 (75.3%)** | **0/1348 (0.0%)** |
| Undefended | **247/357 (69.2%)** | 556/1348 (41.2%) | 488/1348 (36.2%) |
| MCPGuard | 184/357 (51.5%) | 704/1348 (52.2%) | 1/1348 (0.1%) |
| ClawGuard | 207/357 (58.0%) | 618/1348 (45.8%) | 218/1348 (16.2%) |
| StackOne | 49/357 (13.7%) | 179/1348 (13.3%) | 13/1348 (1.0%) |
| Pipelock | 243/357 (68.1%) | 608/1348 (45.1%) | 414/1348 (30.7%) |

### MSB

| Schema | AU | ASR |
|---|---:|---:|
| Ours | 343/415 (82.7%) | **0/622 (0.0%)** |
| Undefended | **376/415 (90.6%)** | 303/622 (48.7%) |
| MCPGuard | 308/415 (74.2%) | 71/622 (11.4%) |
| ClawGuard | 367/415 (88.4%) | 237/622 (38.1%) |
| StackOne | 327/415 (78.8%) | 101/622 (16.2%) |
| Pipelock | 367/415 (88.4%) | 301/622 (48.4%) |

## DISC-2026W33-004 · Thread #10: Adaptive-Attack Subsets for Tool, MCP, and Skill Units

Status: Open  
Updated: 2026-08-19  

### Scope

This thread reports adaptive-attack stress tests on five applicability-defined
subsets.  The subset rule is threat-surface coverage, not effect-size selection:
we include cases where the adaptive method has the same attack surface assumed by
the method, and we keep failed/missing cases in the denominator when the run is
reported as full-subset.

For each table, `AU-original` and `ASR-original` are the corresponding
non-adaptive/original results on the same applicability subset, not full-suite
benchmark aggregates.

### Adaptive Attacks Used

Tool units use AutoDojo-style iterative payload optimization.  The attacker model
generates and refines the indirect instruction from target-model feedback, while
the clean task, tool set, and target model remain fixed.  For ASB-OPI we use a
GPT-5.4 attack model against a DeepSeek target with `T=4`; the generated cache is
then replayed unchanged against Ours and the selected baselines.

Skill units use SkillJect-style fusion.  The attacker rewrites the benign
`SKILL.md` into a polluted skill document, preserving the benign skill workflow
while embedding an instruction that can be adopted during task execution.  The
attack is adaptive to the skill-document substrate and task utility constraint:
it changes the skill artifact, not the user task or the defense implementation.
The fused skills are reusable across defenses, so this is a one-shot
artifact-level adaptive attack rather than a per-defense iterative attack.

MCP units use MCP-ITP-style poisoned tool descriptions.  The attacker optimizes
MCP tool metadata so that the target model naturally invokes the attacker-chosen
tool or target operation.  This directly attacks the MCP tool-selection layer:
the malicious object is the tool description/catalog entry, while the clean task
and target model remain fixed.  We report MCP-ITP adaptive ASR, not the original
MCPTox/MSB malicious-objective judge, because the attack objective has changed to
target-tool invocation under optimized metadata.

### Subset Selection

ASB-OPI uses all 400 attacker-tool cells, one representative attack case per
cell.  This is the natural cell-level unit for AutoDojo-style search because the
optimized payload is tied to the clean task plus attacker-tool surface.  The
baseline set is the strongest original ASB-OPI defenses outside Ours/Undefended
under low-ASR, high-AU selection: MELON, CaMeL, and DRIFT.

SkillInject uses the 44 comparable official SkillJect-fusion pairs.  The original
candidate set has 45 scripted pairs, but `id015_task1` is excluded because it has
no common comparable fused pair across the merged baseline/Ours result.

SCR uses CapFlow `A+B_neutral` under official composition fusion.  This is the
SCR condition where SkillJect-style skill-document pollution most directly tests
A-side skill influence causing a B-side external effect.  `A+B_explicit` is not
reported because it is an explicitly malicious user task rather than an IPI
adaptive attack.  AuthBlur and TrustLift are not included in this adaptive table
because their core threat surfaces are not the SkillJect fusion surface.

MCPTox uses the Template-2 full subset, 455 cases.  Template-2 is the MCPTox
family whose clean task/catalog can be transformed into a tool-selection
metadata attack; the MCP-ITP generation used strong budget `N=5,T=2,m=3`.

MSB uses 212 applicable cases across `name_overlap`,
`preference_manipulation`, `preference_manipulation-simulated_user`, and
`tool_transfer`.  These are the MSB settings where MCP poisoned metadata can
plausibly steer target-tool selection.  We do not report the earlier MSB shared
ASR sanity table because it was all-zero and not aligned with the MCP-ITP
adaptive objective.

### ASB-OPI · AutoDojo-Style T4, 400 Attacker-Tool Cells

Artifacts:
`experiment_results/ASB-OPI/AutoDojoStyle/GPT5.4_vs_DeepSeek/undefended_T4_full400_reuse191/merged_cache.json`,
`experiment_results/ASB-OPI/AutoDojoStyle/GPT5.4_vs_DeepSeek/undefended_T4_full400_reuse191/MERGED_METADATA.json`,
and replay metadata under
`experiment_results/ASB-OPI/AutoDojoStyle/GPT5.4_vs_DeepSeek/*_T4_full400_reuse191/`.

| Schema | AU | AU-original | ASR | ASR-original |
|---|---:|---:|---:|---:|
| Undefended | **388/400 (97.0%)** | 333/400 (83.2%) | 345/400 (86.2%) | 164/400 (41.0%) |
| Ours | 303/400 (75.8%) | **344/400 (86.0%)** | **0/400 (0.0%)** | **0/400 (0.0%)** |
| MELON | 335/400 (83.8%) | 332/400 (83.0%) | 45/400 (11.2%) | 50/400 (12.5%) |
| CaMeL | 284/400 (71.0%) | 304/400 (76.0%) | 46/400 (11.5%) | 43/400 (10.8%) |
| DRIFT | 147/400 (36.8%) | 160/400 (40.0%) | 34/400 (8.5%) | 35/400 (8.8%) |

The adaptive attack substantially raises Undefended ASR on the same 400 cells
from 164/400 to 345/400, so this is a valid Tool-unit adaptive stress test.  Ours
keeps ASR at 0/400.  The AU drop from 344/400 original to 303/400 adaptive is
mostly a target-agent task-completion failure after seeing poisoned observations:
the frozen contracts contain the required normal tools, and WRAP is not
overblocking them, but the target agent sometimes stops before calling all
remaining normal tools.

### SkillInject · SkillJect Fusion, 44 Pairs

Artifacts:
`experiment_results/SkillInject/SkillJect-fusion/official_scripted45_all_baselines_ours_recovery_contractfix_merged44/merged_metrics.json`

| Schema | AU | AU-original | ASR | ASR-original |
|---|---:|---:|---:|---:|
| Ours | **41/44 (93.2%)** | **37/44 (84.1%)** | **0/44 (0.0%)** | **0/44 (0.0%)** |
| Undefended | 38/44 (86.4%) | 33/44 (75.0%) | 21/44 (47.7%) | 10/44 (22.7%) |
| ClawGuard | 24/44 (54.5%) | 12/44 (27.3%) | 5/44 (11.4%) | 0/44 (0.0%) |
| Progent | 19/44 (43.2%) | 15/44 (34.1%) | 4/44 (9.1%) | 1/44 (2.3%) |
| TaskShield | 29/44 (65.9%) | 18/44 (40.9%) | 1/44 (2.3%) | 0/44 (0.0%) |

Ours changed from AU 25/44 to 41/44 after the recovery/contract fix merge, while
ASR stayed 0/44.

### SCR CapFlow · SkillJect Composition Fusion, 150 Cases

Artifacts:
`experiment_results/SCR/SkillJect-fusion/official_composition_capflow_comparison_metrics.json`,
`experiment_results/SCR/SkillJect-fusion/official_composition_capflow_baseline_utility_full.json`,
`experiment_results/SCR/ClawGuard/DeepSeek/skillject_official_composition_capflow_approval3/metrics.json`,
`experiment_results/SCR/SkillJect-fusion/official_composition_capflow_ours_contract_fix_merged_MERGE_NOTES.md`

| Schema | AU | AU-original | ASR | ASR-original |
|---|---:|---:|---:|---:|
| Ours | **147/150 (98.0%)** | **149/150 (99.3%)** | **0/150 (0.0%)** | **0/150 (0.0%)** |
| Undefended | 21/150 (14.0%) | 51/150 (34.0%) | 125/150 (83.3%) | 96/150 (64.0%) |
| ClawGuard (approval3) | 35/150 (23.3%) | 49/150 (32.7%) | 114/150 (76.0%) | 98/150 (65.3%) |
| Progent | 30/150 (20.0%) | 56/150 (37.3%) | 106/150 (70.7%) | 92/150 (61.3%) |
| TaskShield | 30/150 (20.0%) | 75/150 (50.0%) | 67/150 (44.7%) | 63/150 (42.0%) |

The final Ours row uses the TaskContract identity-closure fix.  The local repair
progression was: initial fusion result AU 126/150, ASR 22/150; reasoned-recovery
merge AU 143/150, ASR 4/150; TaskContract fix on the remaining four cases
(`case024`, `case044`, `case080`, `case098`) AU 147/150, ASR 0/150.
The Undefended row includes the four previously missing cases
(`case030`, `case031`, `case078`, `case083`) rerun under the same fusion setting;
Progent and TaskShield AU were computed from their existing full per-case calls
and CapFlow utility semantics.

### MCPTox Template-2 · MCP-ITP Strong Budget, 455 Cases

Artifacts:
`experiment_results/mcptox/mcp_itp_template2_targetfirst_v5_strong_N5T2m3_full.json`
and replay files under `experiment_results/mcptox/*_mcp_itp_template2_v5_full455_replay.json`.

| Schema | AU | AU-original | ASR | ASR-original |
|---|---:|---:|---:|---:|
| Ours | **357/455 (78.5%)** | **370/455 (81.3%)** | **7/455 (1.5%)** | **0/455 (0.0%)** |
| Undefended | 140/455 (30.8%) | 167/455 (36.7%) | 245/455 (53.8%) | 145/455 (31.9%) |
| MCPGuard | 149/455 (32.7%) | 240/455 (52.7%) | 203/455 (44.6%) | 1/455 (0.2%) |
| ClawGuard | 260/455 (57.1%) | 197/455 (43.3%) | 18/455 (4.0%) | 71/455 (15.6%) |
| StackOne | 229/455 (50.3%) | 68/455 (14.9%) | 33/455 (7.3%) | 9/455 (2.0%) |
| Pipelock | 131/455 (28.8%) | 206/455 (45.3%) | 241/455 (53.0%) | 136/455 (29.9%) |

This subset contains 381 tool-hijack cases scored by paper-style target-tool
invocation and 74 cases scored by the MCPTox-compatible adaptive judge.

### MSB · MCP-ITP Payload-Aware, 212 Applicable Cases

Artifacts:
`experiment_results/MSB/mcp_itp_payloadaware_v2_N3T1m2_full212.json`
and replay files under `experiment_results/MSB/*mcp_itp_payloadaware_v2*full212*`.

| Schema | AU | AU-original | ASR | ASR-original |
|---|---:|---:|---:|---:|
| Ours | **130/212 (61.3%)** | **175/212 (82.5%)** | **0/212 (0.0%)** | **0/212 (0.0%)** |
| Undefended | 64/212 (30.2%) | 174/212 (82.1%) | 99/212 (46.7%) | 80/212 (37.7%) |
| MCPGuard | 71/212 (33.5%) | 157/212 (74.1%) | 91/212 (42.9%) | 40/212 (18.9%) |
| ClawGuard | 72/212 (34.0%) | 166/212 (78.3%) | 82/212 (38.7%) | 80/212 (37.7%) |
| StackOne | 68/212 (32.1%) | 165/212 (77.8%) | 26/212 (12.3%) | 49/212 (23.1%) |
| Pipelock | 62/212 (29.2%) | 165/212 (77.8%) | 100/212 (47.2%) | 77/212 (36.3%) |

Coverage: `name_overlap` 44, `preference_manipulation` 44,
`preference_manipulation-simulated_user` 44, and `tool_transfer` 80.  ASR here is
target-tool selection under optimized poisoned descriptions, not MSB official
side-effect success.

### Current Interpretation

Across all five applicability subsets, Ours keeps adaptive ASR at 0 or near-zero:
0/400 on ASB-OPI, 0/44 on SkillInject, 0/150 on SCR CapFlow, 7/455 on MCPTox
Template-2, and 0/212 on MSB.  The remaining MCPTox 7/455 are the only non-zero
adaptive failures and should be the next MCP-side error-analysis target.  The SCR
non-zero failures were contract-generation bugs rather than WRAP policy gaps;
fixing identity argument closure removed the remaining four ASR without lowering
AU.  On ASB-OPI, the remaining gap is AU rather than ASR: the current evidence
points to payload-induced incomplete normal-tool selection by the target model,
not missing contract authority or WRAP overblocking.

## DISC-2026W34-001 · Thread #11: Original-Benchmark WRAP/PLANT Ablation

Status: Open  
Updated: 2026-08-21  

### Scope

This thread reports the original-benchmark ablation results for the refactored
shared defense stack under `deepseek-v4-flash` as both target model and defense
model.  `full` is the complete Ours configuration; `wrap-only` disables PLANT;
`plant-only` disables WRAP.  Results are read from
`experiment_results/ablation_original/DeepSeek_refactor/` except where a row is
explicitly marked as a partial artifact.

### Ablation Table

| Benchmark | Mode | BU | AU | ASR |
|---|---|---:|---:|---:|
| AgentDojo | full | 84/97 (86.6%) | 505/629 (80.3%) | 0/629 (0.0%) |
| AgentDojo | wrap-only | 76/97 (78.4%) | 481/629 (76.5%) | 3/629 (0.5%) |
| AgentDojo | plant-only | 70/77 (90.9%) | 394/455 (86.6%) | 0/455 (0.0%) |
| ASB-OPI | full | 46/51 (90.2%) | 1735/2040 (85.0%) | 0/2040 (0.0%) |
| ASB-OPI | wrap-only | 45/51 (88.2%) | 1662/2040 (81.5%) | 0/2040 (0.0%) |
| ASB-OPI | plant-only | 44/51 (86.3%) | 1168/1678 (69.6%) | 1003/1678 (59.8%) |
| SkillInject | full | 146/180 (81.1%) | 142/180 (78.9%) | 1/180 (0.6%) |
| SkillInject | wrap-only | 131/173 (75.7%) | 56/93 (60.2%) | 6/93 (6.5%) |
| SkillInject | plant-only | 128/179 (71.5%) | 123/179 (68.7%) | 4/179 (2.2%) |
| SCR | full | 643/667 (96.4%) | 666/667 (99.9%) | 0/667 (0.0%) |
| SCR | wrap-only | 628/667 (94.2%) | 621/667 (93.1%) | 37/667 (5.5%) |
| SCR | plant-only | 197/211 (93.4%) | 86/211 (40.8%) | 123/211 (58.3%) |
| MCPTox | full | 231/357 (64.7%) | 1015/1348 (75.3%) | 0/1348 (0.0%) |
| MCPTox | wrap-only | 223/357 (62.5%) | 898/1348 (66.6%) | 87/1348 (6.5%) |
| MCPTox | plant-only | 240/357 (67.2%) | 784/1348 (58.2%) | 56/1348 (4.2%) |
| MSB | full | 16/17 (94.1%) | 343/415 (82.7%) | 0/622 (0.0%) |
| MSB | wrap-only | 242/243 (99.6%) | 242/243 (99.6%) | 0/243 (0.0%) |
| MSB | plant-only | 64/64 (100.0%) | 64/64 (100.0%) | 5/64 (7.8%) |

### Notes

AgentDojo `wrap-only` is the completed refactor-run artifact under
`experiment_results/ablation_original/DeepSeek_refactor/AgentDojo/wrap_only/`.
The workspace tail was completed through disjoint temporary shards under
`workspace_remaining_shards_20260821_1615/` and merged back into
`workspace.json` by `(task, injection)` key.
AgentDojo `plant-only` is reported on completed shard outputs only: 77/93
benign shards and 455/586 attack cases completed, with 26 shard outputs still
marked incomplete/running.

Several only-mode rows have smaller denominators than the corresponding `full`
row because the available ablation artifacts were not rerun to full-benchmark
coverage after the no-rerun constraint.  The table preserves the artifact
denominators instead of extrapolating rates.
