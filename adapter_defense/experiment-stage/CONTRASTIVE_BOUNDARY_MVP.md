# Contrastive Boundary Guard MVP

Date: 2026-06-08

## Claim Under Test

Adaptive PAIR succeeds against TS-Guard mainly by downgrading the risk score of a fixed unsafe tool action through source-span reframing and proxy rationale laundering. If true, a defense should not simply learn hard-negative labels; it should learn a contrastive invariance:

```text
same unsafe action + reframed source / proxy Thought
  should not be scored safer than
same unsafe action + original blocked source/rationale
```

## Evidence Level

`offline_oracle_mvp`.

This MVP uses existing paired PAIR artifacts where both the original blocked seed and the reframed candidate are known. It validates whether the training signal exists. It does **not** prove a deployable guard, because online deployment cannot assume access to the original unreframed attack source.

## Data

- PAIR source-span + DeepSeek proxy Thought on ToolSafe AgentDojo blocked subset:
  - `code/results/pair_source_span_tsguard_182_proxy_thought_deepseek/records.jsonl`
  - 177 unique proposed-action pairs.
- Source-only PAIR slice for overlap analysis:
  - `code/results/pair_source_span_tsguard_50_source_only/records.jsonl`
  - 47 overlapping pairs.
- Static replay label distribution from `guard_mvp_m1/dev.jsonl` and `test.jsonl`.

## Metrics

| Metric | Value |
|---|---:|
| PAIR proxy cases | 177 |
| TS-Guard weak ASR | 0.853 |
| TS-Guard strong ASR | 0.192 |
| TS-Guard strict strong ASR | 0.136 |
| Risk downgrade rate | 0.853 |
| Source reframe rate | 1.000 |
| Rationale rewrite rate | 0.983 |
| Contrastive oracle re-block on weak bypass | 1.000 |
| Contrastive oracle remaining weak ASR | 0.000 |
| Trivial WARN-as-BLOCK remaining weak ASR | 0.192 |
| Source-only overlap cases | 47 |
| Proxy Thought improves score on overlap | 0.170 |
| Mean proxy-minus-source score delta | 0.064 |

## Interpretation

The MVP supports a real contrastive training signal:

- Most PAIR success is literally a risk downgrade from the original TS-Guard blocked seed.
- A trivial WARN-as-BLOCK policy would catch many `0.5` downgrades, but still leaves allow-level bypasses (`strong ASR=0.192`).
- Proxy Thought helps some cases but is not the dominant driver in the 47-case source-only overlap; source-span reframing alone is already strong.

This suggests a more stable defense direction than five-factor supervision:

```text
source/rationale contrastive pairs
  -> pairwise risk-invariance or DPO-style objective
  -> lightweight single-forward adapter
  -> held-out adaptive re-attack
```

## No-Go Boundary

The current result is not a deployment claim. The next step must show that a model can learn this invariance without oracle access to the original source. If a LoRA/DPO adapter cannot reduce held-out allow-level bypass beyond WARN-as-BLOCK while preserving clean allow, this route should stop.

## Training-Free Verifier Check

After the offline oracle MVP, we tested a stronger but still training-free verifier on existing benchmark/artifact data. This verifier does not output `F1-F5`; it directly checks:

```json
{
  "task_support": "high|medium|low",
  "external_authority_dependence": "high|medium|low",
  "action_risk": "low|medium|high",
  "decision": "ALLOW|WARN|BLOCK"
}
```

Evaluation data:

- 75 hard clean ToolSafe cases: `score=0`, with external `<INFORMATION>` span and side-effect action.
- 177 PAIR source-span + DeepSeek proxy Thought best candidates.

Results:

| Slice | n | Decision counts | Metric |
|---|---:|---|---:|
| hard clean | 75 | ALLOW=73, BLOCK=2 | clean allow=0.973 |
| PAIR attack | 177 | BLOCK=176, ALLOW=1 | attack block=0.994 |
| PAIR weak bypass | 151 | BLOCK=150, ALLOW=1 | block on weak bypass=0.993 |
| PAIR strong bypass | 34 | BLOCK=33, ALLOW=1 | block on strong bypass=0.971 |

This is the first evidence that the contrastive boundary idea can preserve clean utility in a training-free setting while catching adaptive PAIR bypasses. The two clean blocks appear to be silver-label edge cases where the current action follows a previously compromised trajectory or sends money to an injected recipient. The single attack allow is a malformed/ambiguous action case where the verifier judged the action as directly completing the user's email-delegated task.

Evidence:

- `code/results/contrastive_boundary_verifier_deepseek_full_v2/metrics.json`
- `code/results/contrastive_boundary_verifier_deepseek_full_v2/records.jsonl`

## Next Experiment

Build a training/eval pair bank:

- train split: original blocked seed vs PAIR reframed candidate, plus source-neutralized and thought-neutralized variants where available;
- held-out split: PAIR dev/test candidates never used in training;
- clean replay: high-risk authorized and benign side-effect tool calls to protect utility.

Train a small adapter with pairwise objective and compare:

1. TS-Guard baseline;
2. trivial WARN-as-BLOCK;
3. M1 binary hard-negative LoRA;
4. contrastive pairwise LoRA/DPO.

## Value + Authority Boundary Check

We then tested whether the boundary is too narrow. The previous verifier focused
on authority laundering; a realistic guard also needs to catch untrusted values
flowing into sensitive tool arguments. We therefore added one explicit axis:

```json
{
  "task_support": "high|low",
  "source_authority_dependence": "high|low",
  "untrusted_value_flow": "high|low",
  "action_risk": "high|low",
  "decision": "ALLOW|WARN|BLOCK"
}
```

Evaluation data still comes only from existing artifacts:

- 75 hard clean ToolSafe cases: `score=0`, external `<INFORMATION>` span, and side-effect action.
- 171 ToolSafe value-flow-like unsafe cases: `score=1`, external `<INFORMATION>` span, side-effect action, and current action values overlapping external history.
- 177 PAIR source-span + DeepSeek proxy Thought best candidates.

Results:

| Slice | n | Decision counts | Metric |
|---|---:|---|---:|
| hard clean | 75 | ALLOW=72, WARN=1, BLOCK=2 | clean allow=0.960 |
| hard clean | 75 | ALLOW/WARN=73, BLOCK=2 | clean warn-or-allow=0.973 |
| value-flow attack | 171 | BLOCK=170, WARN=1 | attack block=0.994 |
| value-flow attack | 171 | BLOCK/WARN=171 | attack warn-or-block=1.000 |
| authority-flow attack | 177 | BLOCK=176, ALLOW=1 | attack block=0.994 |
| authority weak bypass | 151 | BLOCK=150, ALLOW=1 | block=0.993 |
| authority strong bypass | 34 | BLOCK=33, ALLOW=1 | block=0.971 |

This supports a broader claim than authority-only defense: the same lightweight
boundary can cover value propagation and authority laundering. The remaining
errors are concentrated in silver-label or malformed cases: clean non-allow
examples include prior compromised money-transfer trajectories, and the only
attack allow is an ambiguous `update_file` action that is not a normal executable
tool call.

Evidence:

- `code/results/value_authority_boundary_verifier_deepseek_full/metrics.json`
- `code/results/value_authority_boundary_verifier_deepseek_full/records.jsonl`
