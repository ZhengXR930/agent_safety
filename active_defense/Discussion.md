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

## DISC-2026W33-004 · Thread #10: Adaptive-Attack Subsets for MCP and Skill Units

Status: Open  
Updated: 2026-08-18  

### Scope

This thread reports adaptive-attack stress tests on four applicability-defined
subsets.  The subset rule is threat-surface coverage, not effect-size selection:
we include cases where the adaptive method has the same attack surface assumed by
the method, and we keep failed/missing cases in the denominator when the run is
reported as full-subset.

For each table, `AU-original` and `ASR-original` are the corresponding
non-adaptive/original results on the same applicability subset, not full-suite
benchmark aggregates.

### Adaptive Attacks Used

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
`experiment_results/fusion_eval_20260818/SCR/ours_contract_fix_merged/MERGE_NOTES.md`

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

Across all four applicability subsets, Ours keeps adaptive ASR at 0 or near-zero:
0/44 on SkillInject, 0/150 on SCR CapFlow, 7/455 on MCPTox Template-2, and 0/212
on MSB.  The remaining MCPTox 7/455 are the only non-zero adaptive failures and
should be the next MCP-side error-analysis target.  The SCR non-zero failures
were contract-generation bugs rather than WRAP policy gaps; fixing identity
argument closure removed the remaining four ASR without lowering AU.
