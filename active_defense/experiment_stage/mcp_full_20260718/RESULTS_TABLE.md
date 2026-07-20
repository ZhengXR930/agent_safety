# MCP Baseline Results

## Completed full cells: MCPTox

| Baseline | N attack | Undefended success / ASR | Defended success / ASR | Attack detection | Clean N | FP / FPR | Detector utility |
|---|---:|---:|---:|---:|---:|---:|---:|
| MCP-Guard | 1,348 | 757 / 56.16% | 0 / 0.00% | 100.00% | 362 | 288 / 79.56% | 20.44% |
| StackOne Defender | 1,348 | 757 / 56.16% | 123 / 9.12% | 81.53% | 362 | 133 / 36.74% | 63.26% |

MCPTox ASR is an offline residual-ASR replay over the benchmark's official per-instance `DeepSeek-v3` labels. Clean N is the 362 tool blocks actually present in `clean_system_promot`; the separate declared `tool_names` lists contain 353 names, a source-data inconsistency retained for audit.

## Completed maximal-reachable MSB cells

| Baseline | Common reachable N | Attack success / micro ASR | Official macro ASR | Utility N | Task success / micro utility | Official macro utility | Clean N | FP / FPR | Detector utility |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| StackOne Defender | 605 | 100 / 16.53% | 12.08% | 411 | 301 / 73.24% | 77.34% | 15 | 4 / 26.67% | 73.33% |
| MCP-Guard | 605 | 63 / 10.41% | 7.84% | 411 | 241 / 58.64% | 56.85% | 15 | 5 / 33.33% | 66.67% |

Both baselines generated 725 unique raw cases and zero unclassified incomplete cases. StackOne completed 605 reachable cases and excluded 120 availability failures (102 exact `kill_process` + `Connection closed`; 18 exact Flux `This tool is unavailable.`). MCP-Guard completed 623 and excluded the 102 attack-backend failures. The headline comparison uses the exact 605-key completed-reachable intersection; no value is imputed for excluded cases.

ASR is the official single/mixed attack-success score. Utility is the official user-task-success score on the 411 eligible common cases (excluding false-error and simulated-user families as specified by the benchmark scorer). FP is clean metadata rejected by the detector, so detector utility is `1-FPR`. Coverage and all per-attack-type values are retained in `msb_common_scores.json`.
