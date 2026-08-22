# Ablation Original DeepSeek Refactor Summary

- target model: `deepseek-v4-flash`
- defense model: `deepseek-v4-flash`
- scope: original-benchmark ablation artifacts currently available under `DeepSeek_refactor`. Some inherited only-mode artifacts have smaller denominators than the full benchmark because they were not rerun per the no-rerun constraint; AgentDojo plant-only is partial due to provider `402 Insufficient Balance`.

## Available Benchmark Results

| Benchmark | Method | BU | AU | ASR |
|---|---|---:|---:|---:|
| ASB-OPI | ours | 46/51 (90.2%) | 1735/2040 (85.0%) | 0/2040 (0.0%) |
| ASB-OPI | wrap_only | 45/51 (88.2%) | 1662/2040 (81.5%) | 0/2040 (0.0%) |
| ASB-OPI | plant_only | 44/51 (86.3%) | 1168/1678 (69.6%) | 1003/1678 (59.8%) |
| MCPTox | ours | 231/357 (64.7%) | 1015/1348 (75.3%) | 0/1348 (0.0%) |
| MCPTox | wrap_only | 223/357 (62.5%) | 898/1348 (66.6%) | 87/1348 (6.5%) |
| MCPTox | plant_only | 240/357 (67.2%) | 784/1348 (58.2%) | 56/1348 (4.2%) |
| MSB | ours | 16/17 (94.1%) | 343/415 (82.7%) | 0/622 (0.0%) |
| MSB | wrap_only | 242/243 (99.6%) | 242/243 (99.6%) | 0/243 (0.0%) |
| MSB | plant_only | 64/64 (100.0%) | 64/64 (100.0%) | 5/64 (7.8%) |
| SkillInject | ours | 146/180 (81.1%) | 142/180 (78.9%) | 1/180 (0.6%) |
| SkillInject | wrap_only | 131/173 (75.7%) | 56/93 (60.2%) | 6/93 (6.5%) |
| SkillInject | plant_only | 128/179 (71.5%) | 123/179 (68.7%) | 4/179 (2.2%) |
| SCR | ours | 643/667 (96.4%) | 666/667 (99.9%) | 0/667 (0.0%) |
| SCR | wrap_only | 628/667 (94.2%) | 621/667 (93.1%) | 37/667 (5.5%) |
| SCR | plant_only | 197/211 (93.4%) | 86/211 (40.8%) | 123/211 (58.3%) |

## PLANT-Only Deployment/Commit Rates

| Benchmark | Attack n | Deploy rate | Commit rate |
|---|---:|---:|---:|
| ASB-OPI | 1678 | 720/1678 (42.9%) | 7/1678 (0.4%) |
| MCPTox | 1348 | 1219/1348 (90.4%) | 208/1348 (15.4%) |
| MSB | 64 | 62/64 (96.9%) | 46/64 (71.9%) |
| SkillInject | 179 | 179/179 (100.0%) | 16/179 (8.9%) |
| SCR | 211 | 76/211 (36.0%) | 20/211 (9.5%) |

## AgentDojo Status

AgentDojo plant-only is partial: 498/629 attack cases completed. Current AU is 427/498 (85.7%); current ASR is 0/498 (0.0%). Remaining execution is blocked by `402 Insufficient Balance` from the model provider.
Current partial plant-only deploy rate is 471/498 (94.6%); commit rate is 80/498 (16.1%).

Coverage caveat: ASB-OPI plant-only, SkillInject wrap-only, SCR plant-only, and MSB wrap/plant-only use the existing available denominators in their source artifacts rather than newly rerun full denominators.

## Sources

- ASB-OPI ours: `experiment_results/ablation_original/DeepSeek_refactor/ASB-OPI/ours/METADATA.json`
- ASB-OPI wrap_only: `experiment_results/ablation_original/DeepSeek_refactor/ASB-OPI/wrap_only/summary.json`
- ASB-OPI plant_only: `experiment_results/ablation_original/DeepSeek_refactor/ASB-OPI/plant_only/summary.json`
- MCPTox ours: `experiment_results/ablation_original/DeepSeek_refactor/MCPTox/ours/METADATA.json`
- MCPTox wrap_only: `experiment_results/ablation_original/DeepSeek_refactor/MCPTox/wrap_only/summary.json`
- MCPTox plant_only: `experiment_results/ablation_original/DeepSeek_refactor/MCPTox/plant_only/summary.json`
- MSB ours: `experiment_results/ablation_original/DeepSeek_refactor/MSB/ours/METADATA.json`
- MSB wrap_only: `experiment_results/ablation_original/DeepSeek_refactor/MSB/wrap_only/summary.json`
- MSB plant_only: `experiment_results/ablation_original/DeepSeek_refactor/MSB/plant_only/summary.json`
- SkillInject ours: `experiment_results/ablation_original/DeepSeek_refactor/SkillInject/ours/METADATA.json`
- SkillInject wrap_only: `experiment_results/ablation_original/DeepSeek_refactor/SkillInject/wrap_only/summary.json`
- SkillInject plant_only: `experiment_results/ablation_original/DeepSeek_refactor/SkillInject/plant_only/summary.json`
- SCR ours: `experiment_results/ablation_original/DeepSeek_refactor/SCR/ours/METADATA.json`
- SCR wrap_only: `experiment_results/ablation_original/DeepSeek_refactor/SCR/wrap_only/summary.json`
- SCR plant_only: `experiment_results/ablation_original/DeepSeek_refactor/SCR/plant_only/summary.json`
