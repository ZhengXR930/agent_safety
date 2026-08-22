# AgentDojo DeepSeek comparison

Frozen on 2026-08-11 for AgentDojo v1.2.2 with the
`important_instructions` attack. Every row uses the same 97 clean tasks and
629 matched attack pairs. Higher BU/AU and lower ASR are better.

| Method | Benign Utility | Utility under Attack | ASR |
|---|---:|---:|---:|
| Ours | 84/97 (86.6%) | 505/629 (80.3%) | 0/629 (0.0%) |
| Undefended | 86/97 (88.7%) | 464/629 (73.8%) | 107/629 (17.0%) |
| DRIFT | 74/97 (76.3%) | 384/629 (61.0%) | 12/629 (1.9%) |
| CaMeL (local-adapted) | 74/97 (76.3%) | 471/629 (74.9%) | 7/629 (1.1%) |
| Progent | 85/97 (87.6%) | 489/629 (77.7%) | 4/629 (0.6%) |
| MELON | 50/97 (51.5%) | 245/629 (39.0%) | 4/629 (0.6%) |

Ours has the best aligned attack utility and the only zero-ASR result. Its BU
is 1 task below Progent and 2 tasks below Undefended. CaMeL is explicitly the
repository's local-adapted integration, not an unmodified upstream result.

Canonical Ours artifacts are under `Ours/DeepSeek/`: `METADATA.json`, the four
files in `contracts/`, and `results/merged_final.json`. Earlier candidates are
superseded and retained only in `Ours/DeepSeek/archive/20260811_pre_84_final/`.
