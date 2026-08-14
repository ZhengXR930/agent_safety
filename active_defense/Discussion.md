# Discussion

## DISC-2026W33-003 · Thread #9: DeepSeek Target + DeepSeek Defense Benchmark Comparison

Status: Open  
Opened: 2026-08-14  
Model setting: target agent = `deepseek-v4-flash`; defense/guard model = `deepseek-v4-flash` when the method has an independent defense model.  
Metrics: BU / AU / ASR. Higher BU/AU is better; lower ASR is better.  
Evidence: canonical `experiment_results/*/*/DeepSeek/METADATA.json` unless marked otherwise.

### Scope

This thread records the DeepSeek-on-DeepSeek comparison across the five main benchmarks:

- AgentDojo: Tool unit
- SkillInject: Skill unit
- SCR: Skill composition unit
- MSB: MCP unit
- MCPTox: MCP unit

Prompt-only and detection-only defenses are included for completeness, but the main paper claim should compare runtime/system-level defenses separately from prompt-only wrappers.

### Method snapshot

Ours is the current Contract--Receipt PLANT--WRAP runtime:

1. compile the trusted task and trusted manifest into a small TaskContract;
2. record observations, effect returns, runtime context, and state as immutable receipts;
3. close proposed effect arguments through four Binding families: root/context, receipt/effect-return, schema/operator, and semantic candidate binding;
4. gate every top-level and nested effect through WRAP;
5. deploy PLANT over observation, dependency, and substrate carriers, counting only committed decoy adoption as hard evidence;
6. use continuation only as utility recovery under the same WRAP gate.

### AgentDojo · Tool unit · important_instructions

Denominator: 97 clean / 629 attack.

| Method | Category | BU | AU | ASR | Notes |
|---|---|---:|---:|---:|---|
| Ours | runtime effect gate | 84/97 (86.6%) | 505/629 (80.3%) | 0/629 (0.0%) | frozen |
| Undefended | no defense | 86/97 (88.7%) | 464/629 (73.8%) | 107/629 (17.0%) | frozen |
| DRIFT | runtime / constraint defense | 74/97 (76.3%) | 384/629 (61.0%) | 12/629 (1.9%) | frozen |
| CaMeL | runtime / isolation-style | 74/97 (76.3%) | 471/629 (74.9%) | 7/629 (1.1%) | local adapted CaMeL |
| Progent | runtime / policy guard | 85/97 (87.6%) | 489/629 (77.7%) | 4/629 (0.6%) | frozen |
| MELON | detector / filtering | 50/97 (51.5%) | 245/629 (39.0%) | 4/629 (0.6%) | frozen |
| Tool Filter | tool reduction | 21/97 (21.6%) | 141/629 (22.4%) | 1/629 (0.2%) | low utility |
| Spotlighting | prompt-only | 92/97 (94.8%) | 547/629 (87.0%) | 1/629 (0.2%) | suspiciously strong; fresh rerun pending |
| AgentShield | detection-only / detect-as-defense | 81/97 (83.5%) | 502/629 (79.8%) | 3/629 (0.5%) | raw oracle: BU 88/97, AU 536/629, ASR 5/629 |

Spotlighting audit: current fresh rerun is still strong but incomplete. As of the last check it had completed 426/629 attacks with ASR 2 so far. This suggests the result is not only a stale-file artifact, but it remains prompt-only and target-model dependent.

### SkillInject · Skill unit

Denominator: 180 clean / 180 attack.

| Method | Category | BU | AU | ASR | Notes |
|---|---|---:|---:|---:|---|
| Ours | runtime effect gate | 146/180 (81.1%) | 142/180 (78.9%) | 1/180 (0.6%) | frozen; detected_attack 19/180 |
| ClawGuard | capability / approval guard | 82/180 (45.6%) | 82/180 (45.6%) | 13/180 (7.2%) | frozen |
| Progent | policy guard | 115/180 (63.9%) | 113/180 (62.8%) | 28/180 (15.6%) | frozen |
| TaskShield | task policy guard | 96/180 (53.3%) | 105/180 (58.3%) | 10/180 (5.6%) | frozen |
| Undefended | no defense | running | running | running | launched at `experiment_results/SkillInject/Undefended/DeepSeek/`; PID 3795243 |

### SCR · Skill composition unit

SCR is reported by suite because each baseline supports a different subset.

#### CapFlow

Denominator: 150 clean / 150 attack.

| Method | Category | BU | AU | ASR | Notes |
|---|---|---:|---:|---:|---|
| Ours | runtime effect gate | 127/150 (84.7%) | 149/150 (99.3%) | 0/150 (0.0%) | frozen |
| ClawGuard | capability / approval guard | 0/150 (0.0%) | 131/150 (87.3%) | 0/150 (0.0%) | deny/no-recover utility artifact |
| Progent | policy guard | 144/150 (96.0%) | 56/150 (37.3%) | 92/150 (61.3%) | frozen |
| TaskShield | task policy guard | 118/150 (78.7%) | 75/150 (50.0%) | 63/150 (42.0%) | frozen |
| Undefended | no defense | — | — | — | no canonical DeepSeek metadata archived |

#### AuthBlur

Denominator: 116 clean / 116 attack.

| Method | Category | BU | AU | ASR | Notes |
|---|---|---:|---:|---:|---|
| Ours | runtime effect gate | 115/116 (99.1%) | 116/116 (100.0%) | 0/116 (0.0%) | frozen |
| TaskShield | task policy guard | 116/116 (100.0%) | 115/116 (99.1%) | 82/116 (70.7%) | frozen |
| DynamicGuardian | dynamic guard | 116/116 (100.0%) | 116/116 (100.0%) | 84/116 (72.4%) | frozen |
| Progent | policy guard | running | running | running | launched at `experiment_stage/scr_authblur_progent_deepseek_20260814/`; current protocol coverage fix |
| Undefended | no defense | — | — | — | no canonical DeepSeek metadata archived |

#### TrustLift

Denominator: 401 attack. Ours clean BU is not materialized in current metadata.

| Method | Category | BU | AU | ASR | Notes |
|---|---|---:|---:|---:|---|
| Ours | runtime effect gate | — | 401/401 (100.0%) | 0/401 (0.0%) | attack-side frozen; clean BU missing |
| ClawGuard | capability / approval guard | 26/401 (6.5%) | 26/401 (6.5%) | 26/401 (6.5%) | frozen |
| Progent | policy guard | 401/401 (100.0%) | 401/401 (100.0%) | 401/401 (100.0%) | fails completely on ASR |
| TaskShield | task policy guard | 325/401 (81.0%) | 315/401 (78.6%) | 315/401 (78.6%) | frozen |
| Undefended | no defense | — | — | — | no canonical DeepSeek metadata archived |

### MSB · MCP unit

Frozen subset: 622 public-reachable attack cases. AU denominator is 415 where MSB defines attack-side utility. The frozen MSB adapter is attack-only, so BU is not a unified comparable metric; reachable-clean/native checks are recorded only as notes.

| Method | Category | BU | AU | ASR | Notes |
|---|---|---:|---:|---:|---|
| Ours | runtime effect gate | N/A | 343/415 (82.7%) | 0/622 (0.0%) | frozen; reachable-clean sanity 16/17 |
| Undefended | no defense | — | 376/415 (90.6%) | 303/622 (48.7%) | frozen |
| MCPGuard | MCP guard | — | 308/415 (74.2%) | 71/622 (11.4%) | frozen |
| Pipelock | MCP guard | — | 367/415 (88.4%) | 301/622 (48.4%) | weak under unified scoring |
| StackOne | MCP guard | — | 327/415 (78.8%) | 101/622 (16.2%) | frozen |

### MCPTox · MCP unit

Denominator: 357 clean / 1348 attack.

| Method | Category | BU | AU | ASR | Notes |
|---|---|---:|---:|---:|---|
| Ours | runtime effect gate | 231/357 (64.7%) | 1015/1348 (75.3%) | 0/1348 (0.0%) | frozen |
| MCPGuard | MCP guard | 184/357 (51.5%) | 704/1348 (52.2%) | 1/1348 (0.1%) | frozen |
| StackOne | MCP guard | 49/357 (13.7%) | 179/1348 (13.3%) | 13/1348 (1.0%) | frozen |
| Pipelock | detector-style MCP guard | 361/362 detector utility (99.7%) | — | 496/1348 defended success (36.8%) | non-unified metadata; not directly comparable |
| Undefended | no defense | — | — | — | no canonical DeepSeek metadata archived |

### Main interpretation

Across runtime-comparable baselines, Ours is the only method with near-zero or zero ASR across Tool, Skill, Skill-composition, and MCP benchmarks while preserving nontrivial utility.

The strongest apparent competitor on AgentDojo is Spotlighting, but it is prompt-only. Its performance depends heavily on the target model obeying delimiter instructions and does not establish a runtime effect invariant. Therefore it should be reported separately or clearly marked as prompt-only.

AgentShield is also not a normal blocking runtime defense in this table. Its upstream design is detection-only; the current numbers use detect-as-defense and should be labeled as such.

### Quality flags

1. Spotlighting AgentDojo result is under fresh rerun before final freezing.
2. SkillInject Undefended is now running and should replace the pending row once finished.
3. Progent on SCR-AuthBlur is now running; prior omission was a protocol coverage gap, not a methodological impossibility.
4. Undefended canonical DeepSeek metadata is still missing for SCR and MCPTox.
5. MSB has no unified clean BU in the frozen attack-only protocol; reachable-clean/native checks are notes only.
6. MCPTox Pipelock uses non-unified detector-style metadata and should not be compared as ordinary BU/AU/ASR without caveat.
7. TrustLift Ours clean BU is missing in current metadata; attack-side AU/ASR are frozen.

【Agent @Codex】【2026-08-14 00:00】Created from canonical DeepSeek metadata after the method was frozen as Contract--Receipt PLANT--WRAP. SkillInject Undefended was launched in `experiment_results/SkillInject/Undefended/DeepSeek/`. Progent AuthBlur was launched in `experiment_stage/scr_authblur_progent_deepseek_20260814/`. Both should be merged into this thread after completion.
