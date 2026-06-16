# Capability-Targeted Boundary Adapter MVP

## Claim

A mixed M2 LoRA conflates clean value flow, authority laundering, and task support. A TRACE-inspired capability decomposition should improve diagnosis and may improve robustness/utility by training separate adapters:

- `value` adapter: preserve clean value-flow utility while blocking unauthorized value flow.
- `authority` adapter: block PAIR source-span / proxy-Thought authority laundering while preserving clean side-effect/tool-use utility.

## Anti-Claims

- If the value adapter cannot recover `clean_value_flow` allow while preserving `unsafe_value_flow` block, the value-flow schema/teacher labels are insufficient.
- If the authority adapter cannot improve held-out PAIR re-block over mixed M2, PAIR failures require stronger counterfactual/routing training rather than single-capability SFT.
- If either adapter only improves its target slice while badly hurting clean replay, capability splitting alone is not enough.

## Data

Source artifacts are existing benchmark-derived records only:

- GPT teacher calibrated labels: `code/data/boundary_teacher_gpt_cleaned_1k_calibrated/teacher_labels_calibrated.jsonl`.
- PAIR source-span + DeepSeek proxy Thought records: `code/results/pair_source_span_tsguard_182_proxy_thought_deepseek/records.jsonl`.
- Split map: `code/data/guard_mvp_m1/splits.json`.

Exported splits:

- `code/data/boundary_m2_capability_splits/value/{train,dev,test}.jsonl`.
- `code/data/boundary_m2_capability_splits/authority/{train,dev,test}.jsonl`.

## Metrics

Value adapter:

- `clean_value_flow.allow_rate` on dev/test.
- `unsafe_value_flow.warn_or_block_rate` and `block_rate` on dev/test.
- broad/side-effect clean allow as utility guardrail.

Authority adapter:

- static `unsafe_authority_flow.warn_or_block_rate` and clean allow on dev/test.
- held-out PAIR test split `m2_reblock_warn_or_block` and `m2_reblock_block`.
- compare against mixed M2 result `EXP-2026W24-013`.

## Run Order

1. Sanity-train value adapter with same 4-bit attention-only LoRA recipe.
2. Evaluate value dev/test.
3. Sanity-train authority adapter with same recipe.
4. Evaluate authority dev/test and held-out PAIR test.
5. Decide whether routing/merge is worth testing.
