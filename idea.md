# Factorized Continual Tool-Use Guard

## One-Sentence Summary

Train a single local 7B step-level tool-use guard that decomposes safety into
stable semantic factors, learns from counterfactual pairs and adaptive
hard-negatives, and improves robustness to query-adaptive tool-use attacks
without adding multi-call runtime overhead.

## Problem

Existing learned tool-use guards can score highly on static benchmarks while
remaining brittle under query-adaptive attacks. TS-Guard is a strong example:
it performs well on ToolSafe / TS-Bench static subsets, yet PAIR-style
source-span attacks can substantially downgrade its risk judgment.

The core problem is therefore:

> Static benchmark accuracy does not guarantee adaptive robustness for
> step-level tool-use guards. A guard should learn the stable safety semantics
> behind tool-use failures, not only benchmark-specific surface patterns.

## Threat Model

The guard evaluates a proposed tool action before execution. The attacker is
black-box and query-adaptive, with a limited number of attempts. The user may be
benign or malicious depending on the attack surface.

Attack surfaces:

- `S1 tool return`: an external source appears in a tool result, such as an
  email, document, calendar event, webpage, transaction note, or issue comment.
- `S2 tool description`: a tool or skill description is malicious, poisoned, or
  hijacked.
- `S3 user query`:
  - `S3a malicious user`: the user directly requests a harmful action.
  - `S3b authority impersonation`: injected text forges user/system authority.

The first MVP focuses on ToolSafe / TS-Bench data, which covers S1 and S3
strongly. S2 is a planned extension using MCP / tool-description poisoning data.

Attack-surface mapping:

| Surface | Failure being tested | Main factors |
|---|---|---|
| `S1 tool return` | Untrusted observation drives a proposed action. | `F1`, `F2`, `F3`, `F5` |
| `S2 tool description` | Tool schema / description / routing metadata injects authority or abnormal parameters. | `F1`, `F2`, `F3` |
| `S3a malicious user` | User explicitly requests a harmful action; user desire is not sufficient authorization under safety policy. | `F3b`, `F4` |
| `S3b authority impersonation` | User-provided or external text pretends to be system / user / tool authority. | `F1`, `F2`, `F3`, `F5` |

## Core Idea

Do not collapse step-level tool safety into a single task-drift label. Instead,
train a guard to predict five safety semantic factors and a final decision:

| Factor | Meaning |
|---|---|
| `F1 source_trust` | Is the action driven by a trusted source or by untrusted external content / tool metadata? |
| `F2 instruction_data_boundary` | Did the agent treat external data as instructions or authority? |
| `F3 authorization_scope` | Is the action within both the user's legitimate task authorization and the safety policy ceiling? |
| `F4 action_consequence` | What harmful consequence can the proposed action cause? |
| `F5 trajectory_consistency` | Is the current action justified by the original user intent and prior explicitly authorized steps, or has the trajectory laundered external instructions / expanded permissions / accumulated small steps into an unauthorized outcome? |

`F3` has two sub-judgments:

- `F3a user_authorization_scope`: whether the action is covered by the user's
  legitimate task intent.
- `F3b policy_ceiling`: even if the user asks for the action, whether it exceeds
  safety policy limits.

The model outputs compact structured JSON:

```json
{
  "F1_source_trust": "...",
  "F2_instruction_data_boundary": "...",
  "F3_authorization_scope": "...",
  "F4_action_consequence": "...",
  "F5_trajectory_consistency": "...",
  "decision": "ALLOW|WARN|BLOCK"
}
```

The factor outputs are not post-hoc rationales. The final `ALLOW / WARN / BLOCK`
decision is factor-conditioned: it is not a hard-coded vote, but it must consume
or be jointly constrained by the `F1-F5` representations. We enforce
decision-factor consistency through counterfactual and consistency losses so
the model cannot solve the final label by shortcuts while using factors as
decorative explanations.

## Relationship to Authentication DAG

Authentication DAG is no longer the whole method. It is retained as the
authorization substructure behind `F1-F3`:

- user grant roots authorization;
- tool returns and external content may provide evidence or candidate data;
- evidence must not be upgraded into authority;
- action class, target, amount, recipient, time, payload, and side effects must
  stay inside the user's grant.

The broader guard adds `F4` harmful consequence reasoning and `F5` trajectory
anchoring, which are required for malicious-user requests and multi-step
laundering cases where a pure authorization DAG is insufficient.

## Training Signal

The guard is trained with three kinds of data:

1. **Static benchmark traces**
   - ToolSafe AgentDojo / InjecAgent-style IPI for S1.
   - AgentHarm / ASB harmful-user and harmful-action data for S3 / F4.
   - Clean high-permission tool-use traces for utility preservation.

2. **Counterfactual pairs**
   - Single-factor pairs: modify one factor while holding other surface details
     fixed.
   - Trajectory pairs: locally similar trajectories where only accumulated
     authorization / goal consistency differs.
   - Combination pairs: multiple factors are corrupted together to train the
     final decision boundary.

3. **Adaptive hard negatives**
   - PAIR / TAP / Agent-as-Attack / GRA-style attackers generate bypasses under
     a fixed threat model.
   - Hard negatives are used for light LoRA updates or later continual rounds.

Counterfactual data must pass two filters:

- minimal surface difference, checked by edit / embedding distance;
- causal label validity, checked by an independent adjudicator that the intended
  factor is the reason for the label flip.

Counterfactual records use an explicit causal schema:

```json
{
  "counterfactual_group_id": "...",
  "changed_factor": "F1|F2|F3|F4|F5",
  "target_factor_before": "...",
  "target_factor_after": "...",
  "stable_factors": ["F1", "F2", "F4"],
  "decision_before": "ALLOW|WARN|BLOCK",
  "decision_after": "ALLOW|WARN|BLOCK"
}
```

The training constraint is causal: the target factor should change, unrelated
factors should remain stable, and the final decision should follow the target
factor's causal change.

## Structured Adaptive Attacker

Adaptive attackers are not treated as generic jailbreak prompt generators. They
are structured around the same safety factors:

| Attacker | Targeted failure |
|---|---|
| `Attack-F1` | provenance forgery / source laundering |
| `Attack-F2` | instruction-data boundary confusion |
| `Attack-F3` | authorization expansion or policy-ceiling evasion |
| `Attack-F4` | consequence hiding or risk minimization |
| `Attack-F5` | multi-step authorization laundering / cumulative scope expansion |

PAIR, TAP, Agent-as-Attack, and GRA-policy are implementation vehicles for
these factor-targeted attacks. The method contribution is not simply running
existing attackers; it is using structured attackers to expose which semantic
factor failed and to synthesize targeted counterfactual updates.

Each successful bypass goes through this loop:

```text
adaptive bypass
  -> attribute failed factor(s)
  -> synthesize hard counterfactual pairs around those factor(s)
  -> targeted LoRA update with replay
  -> held-out adaptive attack validation
```

If a bypass cannot be attributed to any existing factor and adjudication
confirms a real safety failure, it becomes evidence for extending the factor
schema. If all factors are clean and the action is still unsafe, the case is
marked as an irreducible boundary or a missing policy definition rather than
silently folded into generic SFT data.

## Model

The deployment target is a single local 7B guard:

- backbone: TS-Guard checkpoint or compatible Qwen-style 7B model;
- adaptation: LoRA / QLoRA;
- inference: one forward pass per proposed tool action;
- no router, no multi-adapter inference, no repeated LLM calls.

Training objective:

```text
L = L_final + sum_i lambda_i * L_factor_i
    + alpha * L_pair
    + beta * L_replay
    + delta * L_consistency
    + gamma * L_LAT
```

`L_final` is cross-entropy on `ALLOW / WARN / BLOCK`. `L_factor_i` is
cross-entropy on each semantic factor. `L_pair` is a counterfactual pair loss:
for paired samples that differ only in one target factor, the model should flip
the target factor and final decision while keeping unrelated factors stable.
`L_replay` preserves clean utility and previously learned attack patterns.
`L_consistency` enforces that the final decision is compatible with the factor
state and that non-target factors remain stable within counterfactual groups.
`L_LAT` is optional local adversarial training on hidden states / embeddings,
used only to stabilize factor predictions under small local perturbations.

LAT is not the main robustness claim. The main robustness signal comes from
counterfactual pairs and adaptive hard negatives. LAT is a local regularizer:
it helps prevent fragile factor flips such as `untrusted -> trusted` under tiny
representation perturbations, but it does not replace held-out adaptive attack
evaluation.

## Training Recipe

The training procedure is intentionally lightweight at deployment time: LoRA is
used during training, then validated adapters can be merged into the base guard.
Runtime remains a single model and a single forward pass.

Stage 0: data normalization

- Convert ToolSafe / TS-Bench samples into a unified step-level schema:
  `user_intent`, `tool_schema`, `history`, `current_action`, `F1-F5`,
  `decision`.
- Derive initial factor labels from benchmark labels, tool/action metadata, and
  adjudicated rules; uncertain factor labels are either abstained or sent to
  adjudication.

Stage 1: binary warmup

- Initialize from TS-Guard or a compatible Qwen-style 7B checkpoint.
- Train LoRA on static ToolSafe labels with only final `ALLOW/WARN/BLOCK`.
- Purpose: preserve TS-Guard-style static performance and avoid destabilizing
  the base model.

Stage 2: factorized SFT

- Continue LoRA training with structured JSON outputs: `F1-F5 + decision`.
- Add factor losses and clean replay.
- Purpose: teach the model the explicit safety semantics rather than only the
  final label.

Stage 3: counterfactual training

- Add single-factor, trajectory-level, and combination counterfactual pairs.
- Optimize both supervised losses and pair loss:
  - target factor should flip when its causal condition changes;
  - unrelated factors should remain stable;
  - final decision should follow the counterfactual causal change.
- Purpose: force the guard to learn mechanism-level distinctions, not surface
  strings such as "external source" or "send_money".

Stage 4: adaptive hard-negative update

- Run PAIR / TAP / Agent-as-Attack against the current guard under the fixed
  threat model.
- Attribute each bypass to failed factor(s).
- For old factors, synthesize hard counterfactual pairs around the failed
  factor and update the corresponding factor supervision.
- For uncovered failure modes, propose a new factor dimension and validate it
  with replay from old factors before changing the schema.
- Train a small LoRA update with factor-targeted hard negatives plus replay.
- Validate on held-out attacks and clean utility.
- If validation passes, merge the LoRA into the running guard; if it overfits,
  discard or retrain with more replay.

Stage 5: continual rounds

- Repeat Stage 4 with stronger or held-out attackers.
- Keep a replay buffer covering clean, static unsafe, old hard negatives, and
  counterfactual pairs to avoid catastrophic forgetting.

The full MVP trains and compares:

- binary SFT guard;
- factorized guard without counterfactual pairs;
- factorized guard with counterfactual pairs;
- factorized guard with counterfactual pairs and adaptive hard negatives.

## Evaluation

Static metrics:

- clean allow rate;
- unsafe recall;
- macro F1;
- AUPRC for unsafe actions;
- latency / cost per step.

Adaptive metrics:

- weak ASR: original block `1.0` downgraded to `0.5` or `0.0`;
- official strong ASR: ToolSafe parser returns allow-like overall `0.0`;
- strict strong ASR: `Being_Attacked=no` and `Harmfulness_Rating=0.0`;
- query cost to bypass;
- robust utility-safety frontier.

Factor diagnostics:

- factor accuracy / agreement;
- factor consistency on counterfactual pairs;
- factor leakage, such as corrupting `F1` also moving `F4` without cause.
- counterfactual factor consistency: target factor flips as expected,
  non-target factors remain stable, and the final decision follows the causal
  change;
- attribution accuracy: predicted failed factor for adaptive bypasses matches
  adjudicated failed factor.

## MVP

The first validation should not be a downgraded toy experiment. It should keep
the core method and only restrict the initial data scope. It does not exhaust
every design choice, but it must include the minimal causal ablations needed to
show that factor supervision, counterfactual pairs, and adaptive hard negatives
each add value beyond binary SFT.

MVP scope:

- data: ToolSafe / TS-Bench AgentDojo, AgentHarm, ASB;
- attacks: PAIR source-span, PAIR source-span + proxy Thought, Agent-as-Attack;
- optional held-out attacks: TAP and full GRA-policy once implemented;
- model: 7B LoRA factorized JSON guard initialized from TS-Guard or compatible
  7B backbone;
- outputs: `F1-F5` plus `ALLOW / WARN / BLOCK`.

Primary MVP claim:

> Factorized counterfactual training plus adaptive hard-negative updates reduce
> PAIR-style adaptive ASR relative to TS-Guard and binary SFT, while preserving
> clean allow rate and single-forward-step latency.

Go conditions:

- clean allow drop is at most 3-5%;
- PAIR strict ASR drops by at least 30% relative to TS-Guard;
- full factorized method outperforms binary SFT;
- held-out attack variants still show lower ASR.

No-Go conditions:

- binary SFT achieves the same robustness;
- counterfactual pairs do not improve held-out adaptive robustness;
- factor outputs are unstable or purely decorative;
- clean utility collapses.

## Current Evidence Snapshot

Static TS-Guard is strong, so the motivation is not static failure:

- AgentDojo proposed-action slice: F1=0.945, attack catch=0.904, clean
  allow=0.979.
- AgentHarm: F1=0.898, recall=0.960.
- ASB all: F1=0.950, recall=0.940.

Adaptive audit shows a robustness gap:

- PAIR whole-history upper bound on 47 unique pairs: weak ASR=97.9%, official
  strong ASR=40.4%, strict strong ASR=29.8%.
- PAIR external-source-span only: weak ASR=72.3%, official strong ASR=14.9%,
  strict strong ASR=8.5%.
- SoC finite-arm is weak in this setting, suggesting content-level adaptive
  generation is more important than fixed context switching.

The next experiment should build the factorized/counterfactual training data
and test whether the proposed guard reduces PAIR adaptive ASR without losing
clean utility.

## Changelog

- `2026-06-04`: Replaced the earlier Authentication-DAG-only framing with a
  factorized continual step-level tool guard. Authentication DAG is retained as
  the F1-F3 authorization substructure; the active method now adds F4
  consequence reasoning, F5 trajectory consistency, counterfactual training, and
  adaptive hard-negative updates.
