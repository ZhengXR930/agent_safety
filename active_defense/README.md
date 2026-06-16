# Active Defense Workspace

This subproject is reserved for the active-defense idea. It is separate from
`../adapter_defense/`, which owns adapter teacher labeling, LoRA training, and
adapter evaluation.

## Local Anchors

| Path | Role |
|---|---|
| `idea.md` | Active-defense research problem, objective, and experiment picture. |
| `Discussion.md` | Active-defense discussion thread. |
| `LOGS/` | Active-defense experiment logs. |
| `code/` | Runtime active-defense implementation and evaluation glue only. |
| `experiment_stage/` | Active-defense outputs and reports. |
| `ref/` | Active-defense paper notes and references. |
| `session_memory/` | Handoff notes for this subproject. |

## Code Boundary

Keep `code/` focused on active defense:

- runtime defense logic;
- agent-level or tool-level enforcement wrappers;
- evaluation adapters needed for this active-defense idea;
- minimal utilities that are not already owned by shared baselines/benchmarks.

Do not copy adapter teacher labeling, adapter training, or adapter-specific
attack scripts into this directory. Reuse `../adapter_defense/code/` outputs
through documented paths when needed.

Shared public assets stay at the repository root:

```text
../benchmarks/
../baselines/
```
