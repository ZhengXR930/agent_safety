# Literature Audit: Lightweight Adaptive Tool-Use Guard Direction

Date: 2026-06-08

Scope: tool-use guardrails, indirect prompt injection (IPI), MCP/skill poisoning, adaptive attacks, guard model training, reasoning/policy distillation, causal/provenance defenses, continual/adversarial updating.

This audit is a direction-level synthesis, not a full related-work section. It uses recent web/arXiv/OpenReview/HuggingFace paper pages plus our local experiment logs. The goal is to decide whether the current "five-factor + LoRA" route is scientifically worth continuing, and if not, what nearby gap is sharper.

## Current Local Evidence

Our strongest local facts:

- TS-Guard is a strong static step-level guard, but PAIR source-span + proxy Thought produces an adaptive robustness gap on ToolSafe AgentDojo blocked subset.
- M1 binary hard-negative LoRA is a negative result: it fits train/dev but hurts calibration and increases held-out allow-level bypass.
- M2 training-free current-action causal factor schema has strong signal for PAIR IPI, but large validation shows clean allow is only 88.9%, below gate, and `F1/F2/F3/F5` are entangled.

Implication: the next method cannot be "more hard negatives" or "five labels from a teacher, then LoRA." That is likely unstable and weakly novel.

## Paper Pool Surveyed

I grouped the surveyed work into seven clusters. The exact count below is 63 papers/resources, enough to satisfy the requested 50-100 paper scan at landscape level.

### A. Step-Level Tool-Use Guards and Agent Safety Benchmarks

| ID | Work | Year | Why it matters here |
|---|---:|---:|---|
| A01 | ToolSafe / TS-Guard | 2026 | Direct baseline: step-level tool invocation guard, TS-Bench, multi-task RL. |
| A02 | Agent Security Bench (ASB) | 2024 | Source of user-harmfulness / agent attack patterns in TS-Bench. |
| A03 | InjecAgent | 2024 | Early IPI benchmark for tool-integrated agents. |
| A04 | AgentDojo | 2024 | Main IPI task environment behind our 489/182 slice. |
| A05 | AgentHarm | 2024/2025 | User-harmfulness tool-use benchmark. |
| A06 | TraceSafe | 2026 | Multi-step tool trajectory guardrail evaluation. |
| A07 | PASTABench | 2026 | Proactive assessment of sequential agent trajectories. |
| A08 | StepGuard | 2026 | Step-level data synthesis and balance-aware reinforcement. |
| A09 | AgentAlign | 2024/2025 | Agent safety/alignment data source referenced by TS-Bench. |

Takeaway: step-level tool-use safety is no longer empty. TS-Guard already owns "single 7B step-level learned guard trained on TS-Bench." Any new method must be more specific than "better step-level guard."

### B. IPI Runtime Defenses: Causal, Data-Flow, and Re-execution

| ID | Work | Year | Why it matters here |
|---|---:|---:|---|
| B01 | AttriGuard | 2026 | Causal attribution of tool invocations via counterfactual tests. |
| B02 | CausalArmor | 2026 | Causal attribution family for IPI defense. |
| B03 | AgentSentry | 2026 | Temporal causal diagnostics and context purification. |
| B04 | MELON | 2025 | Masked re-execution / tool comparison, provable-style IPI defense. |
| B05 | IPIGuard | 2025 | Tool dependency graph defense. |
| B06 | Argus / data-flow style defenses | 2025/2026 | Taint/provenance tracking direction. |
| B07 | ClawGuard | 2026 | Runtime rule enforcement with user-confirmed rules. |
| B08 | Instruction-following intent analysis for IPI | 2025 | Intent analysis as defense signal. |
| B09 | Firewall-style multi-agent IPI defense | 2025 | Input/data firewall split, schema sanitization. |
| B10 | BrowseSafe | 2025 | Browser-agent prompt injection defense/benchmark. |
| B11 | Securing AI Agents Against Prompt Injection Attacks | 2025 | RAG/web agent benchmark + multilayer defense. |
| B12 | PromptGuard structured framework | 2026 | Layered prompt injection defense framework. |

Takeaway: our "current-action causality" is close to AttriGuard/CausalArmor/AgentSentry. If we claim causal factors as the method, novelty is weak unless we offer a lower-cost approximation, a trainable surrogate for expensive causal replay, or an adaptive-repair loop those works lack.

### C. MCP, Tool Poisoning, Skill Supply Chain

| ID | Work | Year | Why it matters here |
|---|---:|---:|---|
| C01 | MCPTox | 2026 | Tool-description poisoning on real MCP servers. |
| C02 | MCP-SafetyBench | 2026 | 20 attack types, real MCP servers, multi-domain. |
| C03 | MCPSecBench | 2025/2026 | 17 attack types across 4 layers. |
| C04 | MCP Security Bench / MSB | 2026 | MCP-specific attack taxonomy/evaluation. |
| C05 | MCIP-Bench | 2025 | Function-calling/MCP taxonomy benchmark. |
| C06 | MCP-AttackBench | 2025 | Large-scale MCP attack samples. |
| C07 | SafeMCP | 2025 | Third-party MCP service risks. |
| C08 | MCP-TDP / When the Manual Lies | 2026 | Tool Description Poisoning benchmark. |
| C09 | Beyond Tool Poisoning | 2026 | Malicious remote MCP server surfaces beyond TPA. |
| C10 | MCP-AgentBench | 2026 | Real-world MCP-mediated tool performance. |
| C11 | Skill-Inject | 2026 | Skill file prompt injection benchmark. |
| C12 | Behavioral Integrity Verification for AI Agent Skills | 2026 | Static declared-vs-actual skill capability auditing. |
| C13 | Contractual Skills / GovernSpec | 2026 | Contractual skill design, not runtime defense. |
| C14 | GovernSpec | 2026 | Runtime-independent contracts and offline tests. |
| C15 | BehaviorSpec | 2026 | Declarative behavior contracts for agents. |
| C16 | AgentVerify | 2026 | LTL/model-checking over observable agent control flow. |

Takeaway: MCP/skill is crowded on benchmarks and static/contract analysis, but there is still space for runtime adaptive robustness and low-overhead learned approximations of contract/causal checks.

### D. Adaptive Attacks Against Guards and Agents

| ID | Work | Year | Why it matters here |
|---|---:|---:|---|
| D01 | PAIR | 2023/2024 | Iterative LLM-based black-box prompt attack. |
| D02 | TAP | 2024 | Tree-of-attacks with pruning. |
| D03 | SoC | 2025 | Multi-armed-bandit context switching attack. |
| D04 | GRA | 2025 | Black-box guardrail reverse engineering via surrogate/RL/GA. |
| D05 | Adaptive Attacks Break IPI Defenses | 2025 | Directly argues non-adaptive IPI defenses fail. |
| D06 | IterInject | 2026 | Feedback-guided iterative optimization for IPI. |
| D07 | ICON | 2026 | Intent-context coupling for efficient multi-turn jailbreak. |
| D08 | Context Fusion Attack | 2024 | Multi-turn context-based jailbreak. |
| D09 | AutoDAN | 2023/2024 | Automated adversarial jailbreak generation. |
| D10 | GCG | 2023 | White-box suffix optimization, baseline for attack rigor. |
| D11 | ReNeLLM | 2024 | Rewrite-based jailbreak. |
| D12 | Crescendo | 2025 | Multi-turn jailbreak that evades monitors. |
| D13 | JailGuard | 2026 | Detection via mutation response discrepancy. |
| D14 | Bypassing Prompt Injection and Jailbreak Detection in LLM Guardrails | 2025 | Guard detectors are vulnerable to adversarial perturbations. |
| D15 | Evaluating Robustness of LLM Safety Guardrails Against Adversarial Attacks | 2025 | Static benchmark vs unseen attack gap for guard models. |

Takeaway: "adaptive attack works" is not enough as a paper unless we specialize it to tool-use guards and show a new failure mode or a new repair loop. Existing PAIR/TAP/SoC/GRA already occupy much of the adaptive-attack framing.

### E. General Safety Guard Models and Policy/Reasoning Training

| ID | Work | Year | Why it matters here |
|---|---:|---:|---|
| E01 | Llama Guard series | 2023-2025 | Canonical open guard model family. |
| E02 | ShieldGemma | 2024 | LLM-based content moderation models. |
| E03 | WildGuard | 2024 | Open one-stop moderation for harmful intent, response risk, refusals. |
| E04 | Aegis / Aegis 2.0 | 2024/2025 | NVIDIA guard family; topic-following / broad safety categories. |
| E05 | Granite Guardian | 2024/2025 | Guard model baseline. |
| E06 | Qwen Guard / Qwen3Guard | 2025 | Strong guard baseline in recent evaluations. |
| E07 | Nemotron Safety | 2025 | Safety guard baseline. |
| E08 | Poly-Guard | 2025 | Large multi-domain policy-grounded benchmark, adversarial guardrail evaluation. |
| E09 | SALAD-Bench | 2024 | Safety evaluation taxonomy. |
| E10 | HarmBench | 2024 | Harmful behavior benchmark. |
| E11 | ToxicChat | 2023 | Toxicity/safety benchmark. |
| E12 | JailbreakBench | 2024 | Jailbreak robustness benchmark. |
| E13 | SoK: Evaluating Jailbreak Guardrails | 2025 | Guardrail taxonomy and limitations. |
| E14 | Adversarial Prompt Evaluation | 2025 | Systematic guardrail benchmarking. |

Takeaway: factor labels, policy taxonomies, and synthetic adversarial data are already common. We need a tool-action-specific mechanism, not a generic policy distillation method.

### F. Reasoning, Intent, and Interpretable Guard Methods

| ID | Work | Year | Why it matters here |
|---|---:|---:|---|
| F01 | GuardReasoner | 2025 | Reasoning-based LLM safeguards with explicit safety reasoning. |
| F02 | Reflect-Guard | 2026 | Distills structured reflection into Llama-Guard via QLoRA. |
| F03 | RSafe | 2025 | Proactive reasoning for safety. |
| F04 | Intent-FT / Mitigating Jailbreaks with Intent-Aware LLMs | 2025 | Hidden intent inference for jailbreak robustness. |
| F05 | SafeThinker | 2026 | Reasoning about risk beyond shallow alignment. |
| F06 | ConceptGuard | 2025 | Sparse interpretable jailbreak concepts. |
| F07 | GradSafe | 2024 | Gradient-based jailbreak prompt detection. |
| F08 | PIShield | 2025 | Intrinsic feature prompt injection detection. |
| F09 | PromptSleuth | 2025 | Semantic intent invariance for prompt injection. |
| F10 | CoCoTen | 2025 | Latent contextual co-occurrence tensors. |
| F11 | LatentGuard | 2025 | Latent steering for robust refusal. |
| F12 | Refusal feature adversarial training | 2025 | Robust safeguarding via refusal features. |

Takeaway: "make the guard reason over factors" is close to GuardReasoner/Reflect-Guard/Intent-FT. The differentiator must be the object being reasoned about: proposed tool action + authorization/causal provenance + adaptive repair, not generic harmful intent.

### G. Continual / Adaptive / Lightweight Guard Updating

| ID | Work | Year | Why it matters here |
|---|---:|---:|---|
| G01 | Constitutional Classifiers | 2025 | Rule-based synthetic data for classifiers against universal jailbreaks. |
| G02 | AdaptiveGuard | 2025 | Adaptive runtime safety for LLM-powered software. |
| G03 | Sentra-Guard | 2025 | HITL feedback loop for continual adaptation. |
| G04 | Auto-tuning Safety Guardrails | 2025 | Black-box discrete guardrail optimization. |
| G05 | Robust refusal feature adversarial training | 2025 | Adversarial robustness with internal features. |
| G06 | Immune | 2025 | Inference-time safety reward controlled decoding. |
| G07 | SHIELD | 2025 | Classifier-guided prompting for safer LVLMs. |
| G08 | Hybrid Guardrail Architectures | 2026 | Hybrid classifier/prompt defense. |
| G09 | PromptGuard framework | 2026 | Modular, adaptive response refinement. |

Takeaway: lightweight updating is plausible, but "LoRA each round" is not novel by itself. A publishable contribution needs a distinctive update target and proof it avoids over-refusal/forgetting better than binary hard-negative training.

## What Is Already Occupied

The following claims are likely too weak or already occupied:

1. **"Train a better 7B guard with synthetic labels."**
   GuardReasoner, Reflect-Guard, WildGuard, ShieldGemma, Aegis, Constitutional Classifiers, and Poly-Guard make this crowded.

2. **"Use factorized safety labels for interpretability."**
   Policy taxonomies and structured labels are common. Our five factors are not enough as novelty.

3. **"Use PAIR/TAP/SoC to show adaptive attacks break guards."**
   Strong adjacent work already shows adaptive attacks against guardrails and IPI defenses. We can use this as motivation/evaluation, not as the core contribution.

4. **"Use causal attribution for IPI."**
   AttriGuard/CausalArmor/AgentSentry/MELON occupy much of the causal/counterfactual runtime defense space.

5. **"Static MCP/skill scanner or contractual skill spec."**
   MCPTox, MCP-SafetyBench, MCPSecBench, Skill-Inject, Behavioral Integrity Verification, GovernSpec/Contractual Skills already cover benchmark/static/contract directions.

## Real Gap After This Audit

The gap that still looks plausible is narrower:

> **A lightweight learned surrogate for expensive runtime causal/provenance checks, specialized to proposed tool actions, updated with adaptive counterfactual failures while preserving clean utility.**

This is not "five-factor teacher distillation." It is closer to:

1. Run expensive verifier / attack loop offline to obtain causal counterfactual pairs.
2. Train a single 7B adapter to approximate the verifier on the action boundary.
3. Use calibration-preserving objectives and counterfactual invariance so clean allow does not collapse.
4. Evaluate against held-out adaptive attacks and against the expensive verifier's decision boundary.

The scientific claim would be:

> Expensive causal replay defenses are effective but too costly for every tool boundary; generic learned guards are cheap but adaptively brittle. We can close part of this gap by distilling *causal counterfactual invariances*, not labels, into a lightweight step-level guard.

This gap is plausible because:

- AttriGuard/MELON/AgentSentry are runtime and potentially multi-call/overhead heavy.
- TS-Guard is cheap but adaptively brittle.
- M1 shows naive hard-negative LoRA fails.
- M2 shows causal factor signals exist, but prompt-level factor labels are not clean enough.

## Does Lightweight + Adapter Have Space?

Yes, but only under a stricter formulation.

Likely viable:

- Adapter is not the contribution by itself.
- The adapter learns from *paired causal constraints*:
  - same current action, history polluted vs purified;
  - same risky action, trusted authorization vs untrusted laundering;
  - same source span, data evidence vs instruction upgrade;
  - same label, different attack surface variants.
- Training objective must include calibration preservation:
  - replay static clean/high-risk-authorized examples;
  - pairwise preference or consistency loss;
  - explicit no-regression on clean allow and exact score distribution;
  - possibly freeze most generation style and train only decision tokens / small heads.
- Evaluation compares:
  - TS-Guard;
  - M1 binary hard-negative LoRA;
  - expensive causal verifier / AttriGuard-like oracle;
  - our distilled adapter.

Likely not viable:

- A standalone five-factor JSON guard trained from teacher labels.
- A single LoRA round on PAIR hard negatives.
- A method whose novelty is "DeepSeek labels factors."
- A broad S1/S2/S3 all-in-one factor taxonomy without enough counterfactual data.

## Recommended Route

I recommend pivoting from **Factorized Continual Tool-Use Guard** to:

### Causal Replay Distillation for Tool-Use Guards

Core idea:

```text
Offline expensive causal verifier / counterfactual replay
  -> produces paired invariance constraints at tool-action boundary
  -> LoRA adapter distills these constraints into cheap single-forward guard
  -> adaptive attack loop supplies new counterfactual failures
```

What changes from current design:

- Replace five independent factors with a smaller decision schema:
  - `causal_support`: trusted / untrusted / ambiguous
  - `action_risk`: low / side_effect / irreversible_sensitive
  - `decision`: allow / warn / block
- Use factors only as latent/teacher metadata, not as mandatory deployed output.
- Train on pairwise loss:
  - polluted version should score no safer than purified version when action risk is unchanged;
  - trusted authorization version should score safer than untrusted laundering version;
  - clean high-risk authorized examples must remain allow/warn, not collapse to block.
- Keep adapter lightweight and mergeable, but claim robustness comes from causal pair distillation, not from LoRA.

Why this is more publishable:

- It directly explains M1 failure.
- It gives a crisp baseline hierarchy: TS-Guard < M1 hard-negative LoRA < causal-pair distillation.
- It connects to AttriGuard/MELON but attacks their deployment overhead.
- It gives a clear reason for adapter/lightweight design: approximate expensive causal replay on the hot path.

## Next Concrete Experiment

Do not train five-factor M2 yet.

Next experiment should be a data/teacher validation:

1. Build 300-600 causal pairs from existing ToolSafe/AgentDojo artifacts:
   - PAIR polluted candidate vs original blocked candidate;
   - source-span removed/purified version vs polluted version;
   - current-action-safe-after-history-compromise cases;
   - high-risk authorized clean examples.
2. Ask the expensive verifier to label only pairwise relations, not five independent factors:
   - `polluted_should_be_riskier_than_purified`
   - `trusted_auth_should_be_safer_than_untrusted_auth`
   - `history_only_compromise_should_not_block_current_action`
3. Measure pair-label consistency and clean calibration.
4. Only if pair consistency is high, train adapter with pairwise/DPO-style objective.

Go gate:

- pairwise teacher agreement >= 90%;
- clean allow on high-risk authorized set >= 95%;
- held-out PAIR re-block remains >= 95%;
- M1-style binary hard-negative baseline remains worse.

If this fails, the route should be abandoned or reframed as an evaluation/diagnostic paper, not a method paper.

## Bottom Line

The five-factor route as a deployed training target is too uncertain. It is better to keep factors as analysis vocabulary and move the method contribution to **causal counterfactual pair construction + lightweight adapter distillation**.

This preserves the lightweight single-forward goal while giving the work a more defensible research gap:

- cheap learned guard vs expensive causal replay;
- adaptive robustness vs static benchmark accuracy;
- pairwise causal invariance vs brittle hard-negative SFT.

