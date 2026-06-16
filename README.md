# Agent Safety Research Workspace

This repository now contains two related defense directions that share public
benchmarks and public baselines.

## Top-Level Layout

| Path | Role |
|---|---|
| `adapter_defense/` | Local adapter / boundary-detector direction. This owns adapter teacher labeling, split export, LoRA training, adapter evaluation, adaptive attack probes, and the current benchmark taxonomy manifest. |
| `active_defense/` | Active defense direction. This is a separate idea/discussion space for runtime or agent-level active defenses. Keep its implementation separate from adapter training code. |
| `benchmarks/` | Shared public benchmark checkouts and datasets used by both defense directions. Do not duplicate benchmark data under subprojects. |
| `baselines/` | Shared public baseline implementations used by both directions. |
| `config.txt` | Local API configuration. Do not print or commit secrets. |
| `MODE.md`, `AGENTS.md`, `tools/` | Repository-level research protocol and helper scripts. |

Each defense direction has its own local research anchors:

```text
adapter_defense/idea.md
adapter_defense/Discussion.md
adapter_defense/LOGS/

active_defense/idea.md
active_defense/Discussion.md
active_defense/LOGS/
```

The old root-level single-idea layout is deprecated. New experiment notes should
go into the relevant subproject unless they concern shared benchmark/baseline
maintenance.

## Shared Data Policy

- Keep benchmark source data in `benchmarks/`.
- Keep public baseline repos in `baselines/`.
- Subprojects may write derived manifests, labels, model outputs, and reports
  inside their own `experiment-stage/`, `experiment_stage/`, `code/data/`, or
  `code/results/` directories.
- If both projects need the same derived benchmark manifest, prefer a single
  generated artifact under the project that owns the current data-layer code and
  document the path instead of copying it.

## Adapter Defense

Current implementation lives in `adapter_defense/code/`.

The active code scope is intentionally narrow:

- teacher labeling and calibration;
- benchmark/taxonomy manifest construction;
- split export for adapter training;
- LoRA training / merge / evaluation;
- adaptive attack probes needed to evaluate the adapters;
- small shared utilities used by those steps.

Older one-off scripts should be archived only when they are no longer part of
the reproducible pipeline.

## Active Defense

`active_defense/` is the workspace for a separate active defense idea. Its
`code/` directory should stay independent from adapter training scripts. Add
only the runtime defense implementation, evaluation adapters, and minimal
utilities needed for that idea.

## Common Commands

Repository protocol helpers:

```bash
python3 tools/lint_protocol.py
python3 tools/new_week.py
python3 tools/new_exp.py "源意图一句话"
```

Adapter benchmark taxonomy:

```bash
python adapter_defense/code/build_benchmark_manifest.py
python adapter_defense/code/audit_benchmark_taxonomy.py
python adapter_defense/code/validate_benchmark_manifest.py
```

## Template Source

The research protocol template comes from:
<https://github.com/AngusDujw/Angus-Research-Protocol>
