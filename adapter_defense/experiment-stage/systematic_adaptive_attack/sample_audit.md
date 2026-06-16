# Control-Surface Manifest Sample Audit

Date: 2026-06-11

## Summary

Generated `control_surface_manifest.jsonl` with 125 public-benchmark rows:

- `authority::OPI`: 25
- `value::OPI`: 25
- `policy::DPI`: 50
- `authority::PoT`: 12
- `policy::PoT`: 13

## Validity Checks

### authority::OPI

- Source: `code/data/boundary_training_candidates/unsafe_authority_flow.jsonl`
- Valid attacker control: `history` / `tool_observation`.
- Interpretation: step-level traces where an untrusted observation or external content provides spurious authority for the proposed action.
- Caveat: current rows are step traces, not end-to-end rollout tasks. Use for step-guard target sweep; use official ASB/AgentDojo/AdaptiveAttackAgent runners for rollout.

### value::OPI

- Source: `code/data/boundary_training_candidates/unsafe_value_flow.jsonl`
- Valid attacker control: `history` / `tool_observation`.
- Interpretation: untrusted content supplies sensitive or task-changing values used in action inputs.
- Caveat: some rows also contain authority/task-support failures. Before full value claims, sample-purity audit should mark whether failure is primarily value, authority, or policy.

### policy::DPI

- Sources:
  - `code/data/boundary_training_candidates/unsafe_user_or_policy.jsonl`
  - `benchmarks/ToolSafe/TS-Bench/agentharm-traj/harmful_steps.json`
- Valid attacker control: `instruction`.
- Interpretation: attacker controls the direct user request or direct prompt injection content.
- Caveat: fixed-action step scoring is only a guard subtest. Main policy evidence should come from direct-prompt jailbreak or rollout, because malicious actions are often obvious.

### PoT

- Source: `benchmarks/ASB/data/all_attack_tools.jsonl`
- Valid attacker control: `tool_name`, `tool_description`, `trigger`, `tool_availability`.
- Interpretation: attacker controls malicious or misleading tool affordances and backdoor triggers.
- Caveat: current manifest splits PoT into `authority` and `policy` via ASB `Aggressive`; it does not yet identify `value` PoT cases. Add a second pass that detects sensitive values in tool descriptions or attack instructions.

## Decision

The manifest is valid as a first control-surface index, not yet a final benchmark split.

Use it for:

- experiment bookkeeping,
- step-guard target sweeps,
- selecting examples for official ASB / AdaptiveAttackAgent reproduction.

Do not use it alone for:

- final policy/user-harmfulness claims,
- end-to-end rollout ASR,
- pure value-flow conclusions without manual or scripted purity filtering.
