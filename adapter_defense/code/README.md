# Adapter Defense Code

This directory owns the reproducible code for the adapter-defense direction:
small local boundary detectors trained/evaluated around tool-use safety.

Keep code here only if it supports one of these stages:

1. benchmark / taxonomy data layer;
2. teacher labeling and calibration;
3. split export for adapter training;
4. adapter training, merge, and evaluation;
5. adaptive attack probes against the adapter or its comparison target;
6. shared utilities required by the above.

Do not put active-defense runtime implementations here. Those belong in
`../../active_defense/code/`.

## Benchmark / Taxonomy Layer

- `build_benchmark_manifest.py`
- `audit_benchmark_taxonomy.py`
- `validate_benchmark_manifest.py`
- `defense_runner_adapter.py`
- `build_adaptive_attack_manifest.py`
- `build_control_surface_manifest.py`
- `build_systematic_attack_inventory.py`

These scripts create and audit the shared benchmark view used by the adapter
experiments. The current row-level taxonomy includes:

```json
{
  "clean": "yes|no",
  "value": "yes|no",
  "authority": "yes|no",
  "policy": "yes|no",
  "rationale": "..."
}
```

## Teacher Labeling / Calibration

- `build_authority_teacher_labels.py`
- `build_boundary_teacher_labels.py`
- `build_value_*_teacher_labels.py`
- `calibrate_authority_teacher_labels.py`
- `calibrate_boundary_teacher_labels.py`
- `calibrate_value_*_teacher_labels.py`
- `adjudicate_boundary_label_quality.py`
- `internal_openai_compat.py`

These are the teacher-label pipeline. They may call configured APIs from
`../../config.txt`; never print secrets.

## Split Export

- `export_authority_teacher_splits.py`
- `export_boundary_training_splits.py`
- `export_value_*_splits.py`
- `export_value_contrastive_pairs.py`
- `export_trace_capability_adapters.py`
- `export_capability_boundary_splits.py`
- `mine_boundary_training_candidates.py`
- `build_value_structured_plus_contrastive.py`

These convert calibrated labels and mined examples into SFT-ready train/dev/test
JSONL files.

## Training / Merge / Evaluation

- `train_m2_boundary_lora.py`
- `merge_lora_adapter.py`
- `run_authority_teacher_adapter.sh`
- `run_authority_nopair_adapter.sh`
- `run_value_*_adapter.sh`
- `run_trace_capability_adapter_suite.sh`
- `eval_m2_boundary_lora.py`
- `eval_value_compact_lora.py`
- `eval_capability_lora.py`
- `eval_m2_on_pair_candidates.py`

These are the core adapter training and testing entrypoints.

## Attack Probes / Baseline Runners

- `run_pair_source_span_authority_adapter.sh`
- `run_pair_source_span_boundary_verifier.py`
- `run_pair_source_span_tsguard.py`
- `run_adaptive_three_category_attack.py`
- `run_adaptive_three_category_sanity_worker.sh`
- `run_promptguard2_baseline.py`
- `run_value_authority_boundary_verifier.py`

These evaluate whether attacks transfer to the adapter or to comparison guards.

## Shared Utilities

- `tooluse_attack_common.py`
- `download_adaptive_attack_agent_llama31.sh`
- `shims/`

Generated caches such as `__pycache__/` are not part of the maintained source
surface.
