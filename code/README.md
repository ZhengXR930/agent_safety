# Code Layout

This directory now keeps only the active idea:

> Intent-ambiguity-space adaptive attacks against step-level tool-use guards.

## Active Scripts

- `tooluse_attack_common.py`  
  Shared ToolSafe/TS-Guard adapters, success metrics, and blocked-subset loader.

- `run_pair_tsguard_official_adapter.py`  
  PAIR official-loop adaptation to TS-Guard. The fixed tool call is preserved;
  only interaction history / untrusted context and rationale are rewritten.

- `run_tap_tsguard_official_adapter.py`  
  TAP official tree-search/pruning loop adapted to the same TS-Guard target.

- `run_soc_tsguard_paper_repro.py`  
  Paper-faithful SoC contextual-bandit reproduction. No official SoC code was
  found, so this must be reported separately from official-code baselines.

- `measure_toolsafe_operational_ambiguity.py`  
  Operational-semantics ambiguity measurement: sample reference-agent action
  plans for each benign user intent and compute action-distribution entropy.

## Active Results

- `results/toolsafe_local_guard_slice_tsguard/`  
  Source ToolSafe/TS-Guard 489 proposed-action run used to derive the blocked
  attack subset.

- `results/pair_official_adapter_tsguard_182/`  
  Current PAIR-vs-TS-Guard adaptive attack run.

- `results/toolsafe_operational_ambiguity_blocked182_pilot/`  
  Pilot operational ambiguity measurement, if present.
