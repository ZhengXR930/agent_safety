# Method · Contract--Receipt PLANT--WRAP

## 1. Problem and unit abstraction

We defend tool-using agents against indirect prompt injection at runtime. The attack surface is not a specific string format: an attacker can place instructions or misleading claims in tool outputs, MCP resources, Skill prose, files, persisted state, or other model-visible substrate content. The defended event is an externally visible effect: a tool call, MCP method, Skill helper action, state write, message, file mutation, authorization decision, or any nested effect that leaves the model-only reasoning boundary.

The method treats every registered Tool, MCP method, and Skill export as a capability unit. A unit exposes two independent runtime facts:

- whether an invocation must be mediated before commit;
- whether a successful invocation returns an observation that may become evidence for later effects.

This unit abstraction is deliberately substrate-level. It does not assume a particular agent framework, hidden chain-of-thought access, source--sink taint graph, or prompt format. A ReAct loop implemented with an OpenAI-compatible SDK and a tool runtime is sufficient, as long as effect boundaries are mediated.

## 2. Trusted roots and threat model

Trusted roots are:

- the trusted user task received before execution;
- the operator/substrate manifest for registered units;
- runtime-context receipts issued by the adapter for already-fixed episode facts, such as workspace, account, repository, or server session;
- explicit operator approval, when an evaluation configuration enables approval.

Untrusted inputs are all runtime content visible to the target agent unless it is closed through the Contract/Receipt mechanism. This includes tool prose, MCP resource descriptions, Skill descriptions, retrieved files, webpage text, emails, benchmark attack labels, model outputs, and runtime catalogs that were not registered as trusted manifests.

The attacker may inject content into any untrusted runtime carrier and may try to convert that content into a concrete effect argument or authorization claim. The defense does not claim to stop effects that bypass all mediated units, malicious code that executes outside the registered runtime, or harmful actions that the trusted user explicitly authorized.

## 3. Trusted manifest

The manifest is the environment-level trusted root. For each registered unit action it records:

- action name and argument schema;
- required arguments and deterministic defaults;
- argument types such as `code`, `path`, `url`, `email`, `opaque`, and `natural_language`;
- whether the action is an effect boundary;
- whether a successful result is an observation;
- output schema, when the substrate can attest the returned shape;
- receipt role: `data`, `advisory`, or `control`;
- nested-effect hooks when a unit can invoke a helper, subprocess, MCP server, or tool behind the visible call.

The manifest contains no task-specific ground truth, no attack label, no evaluator answer, and no allowed runtime value. JSON Schema describes call validity and return shape only. It does not grant authority. Missing schema removes shape-based authority; it does not let the Contract or Binding agent invent fields.

For MCP, the manifest is compiled from operator-approved server registration and capability discovery. For Skills, the SkillCard/registry entry is part of the manifest: it fixes helper identity, declared exports, expected argument/return schemas, and nested effect hooks. For ordinary tools, the manifest is the registered tool schema plus the substrate's effect/observation classification.

## 4. TaskContract

Given a trusted task `T` and a manifest `M`, TaskContractor emits one small task-local program `C_T`. The Contract is a specification, not an execution trace. It says what must be learned and which effects may be committed; it does not predict runtime values, receipt paths, tool-call ids, or attack content.

The Contract has four clause types:

| Clause | Meaning |
|---|---|
| `Acquire` | The agent may obtain data from a named observation unit under trusted or already-bound arguments. |
| `Derive` | A task-required value is selected or computed from earlier clauses. |
| `Conditional` | A task-stated branch condition controls whether later clauses are active. |
| `Effect` | One mediated action is authorized, with argument constraints tied to trusted roots or prior clause outputs. |

Effect arguments are constrained by literals, trusted roots, runtime context, prior clause outputs, deterministic operators, or bounded semantic selection over enumerated candidates. The Contract may express deterministic relations such as identity, count, union, difference, argmin, and argmax when the trusted task explicitly entails them. It may not add actions, invent object paths, import benchmark ground truth, or treat untrusted runtime prose as authorization.

TaskContractor is allowed to use a model to compile the task, but deterministic validation owns the accepted language. The validator rejects unknown actions, unknown sources, invalid clause references, impossible schemas, exact-only arguments represented as free semantic claims, and unsupported nested projections. A transport-level malformed response may be retried once with the same schema; semantic repair loops are not part of the core method.

## 5. Receipts

At runtime, every successful observation is recorded as an immutable receipt. A receipt binds:

- unit/action identity;
- canonical arguments;
- canonical output digest and sidecar value;
- receipt role from the manifest;
- parent invocation when the observation came from a nested unit;
- the exact task and Contract version under which it was observed.

Receipts are append-only evidence. They may remain visible to the target agent even when they cannot be used as WRAP authority. Only receipts that close to an `Acquire`, effect-return, runtime-context, or authorized persisted-state boundary can participate in WRAP Binding. Superseded, schema-invalid, unbound, quarantined, or PLANT-only receipts are not authority.

Effect-return receipts are important: when a permitted effect returns a value that a later effect needs, that return value becomes evidence only through an explicit effect-return binding. The target agent's memory of the value is not authority by itself.

## 6. Binding closure

Before a proposed effect commits, WRAP resolves each submitted argument to trusted evidence. The implementation uses four binding families.

| Binding family | What it proves |
|---|---|
| Root/context binding | The value is exactly from the trusted task or a runtime-context receipt. |
| Receipt/effect-return binding | The value is contained in or deterministically returned by a bound observation or prior authorized effect. |
| Schema/operator binding | The value follows from deterministic canonicalization, typed constructors, defaults, or closed operators over bound receipts. |
| Semantic candidate binding | A bounded Binding Agent selects candidate ids from code-enumerated evidence; it cannot invent values, widen clauses, change support mode, or grant authority. |

Exact arguments use exact or deterministic typed equality. For example, numeric and boolean representation changes may be canonicalized by type; authority-bearing identities such as account ids, file paths, recipients, and URLs are not accepted by free semantic equivalence. For `natural_language` arguments, WRAP parses registered authority atoms such as URLs, emails, mentions, paths, account identifiers, or artifact handles, and binds those atoms rather than judging the whole prose as faithful.

A semantic Binding Agent is used only after code has enumerated candidate receipts and public Binding goals. The agent may choose among candidates or abstain. It never sees an output language that can add a source, clause, action, operator, effect, authority bit, or proposal value.

## 7. WRAP effect gate

For every concrete effect proposal `p = (action, arguments)`, the UnitBroker first enumerates the immediate and nested effect proposals induced by that invocation. Each proposal is checked independently.

WRAP allows a proposal only if:

1. exactly one active `Effect` clause authorizes the action;
2. every required argument is present or filled by a trusted deterministic default;
3. every submitted argument, including optional submitted arguments, closes to the clause's allowed sources;
4. all literals and typed canonical values match;
5. all referenced observation, effect-return, state, and runtime-context receipts are active and bound under the current Contract;
6. authority-sensitive effects have at least one valid authority source, and advisory receipts contribute zero authorization;
7. no argument remains unresolved and no conflict is found.

Equivalently, WRAP checks authority closure at the effect boundary. It does not ask whether the agent was causally influenced by a string, and it does not reconstruct hidden model state. The proposal either has sufficient trusted evidence for this action and these arguments, or it does not commit.

Rejected proposals can trigger continuation, but continuation does not weaken WRAP. The retried agent receives a sanitized Recovery Envelope containing the concrete unresolved/conflicting goals and relevant receipts, and the replacement proposal must pass the same gate.

## 8. PLANT active defense

PLANT is independent of WRAP. It creates decoy commitments that should be unavailable to a benign execution but attractive to an agent that follows injected runtime content. PLANT has three carrier classes.

| Carrier | Deployment surface | Mechanism | Hard evidence |
|---|---|---|---|
| Observation | Agent-visible untrusted content | marker rewrite or neutral decoy object | marker/object copied into final response or reaches an effect boundary |
| Dependency | decision/basis layer | decoy basis receipt or forged premise handle outside authorized sources | explicit commitment to that decoy in an effect-relevant proposal |
| Substrate | execution environment or persistent state | decoy file, resource, capability, authorization handle, tool, account, or state artifact | exact invocation or mutation of the decoy artifact |

PLANT placement is Contract-aware and benign-preserving. It should not alter the normal dependency needed to complete the trusted task. If a deployment cannot be shown to be neutral for the relevant benign consumers, PLANT abstains. Abstention is not a WRAP failure; WRAP still gates the actual effect.

Visibility and access are not hard attacks. A benign agent may read a decoy and reject it. Hard PLANT evidence requires committed adoption: copied marker, decoy object/argument at an effect boundary, explicit effect-relevant basis commitment, or actual substrate invocation.

## 9. Nested effects and UnitBroker

Some units hide effects behind helpers, subprocesses, Skill exports, MCP servers, or server-side tools. The method handles this with a UnitBroker rather than benchmark-specific patches.

Each invocation record contains only:

- `unit_id`;
- `action`;
- `arguments`;
- `parent_invocation`, when nested.

A NestedEffectResolver maps registered helper boundaries to canonical child effect proposals using the manifest's ABI decoder and hook declaration. If no nested effect occurs, the broker is inert. If a nested effect occurs, it is mediated exactly like a top-level effect. This is the same rule for Tool, MCP, and Skill units: registered inner effects cannot bypass WRAP merely because they are invoked by another unit.

## 10. Main invariants

Under a correct manifest and complete mediation of effect boundaries, every allowed effect has a Contract-closed proof from trusted roots and active receipts. Therefore, an injected runtime instruction cannot become an external effect merely by being seen, paraphrased, or placed in a tool output; it must produce an effect proposal whose arguments and authority close under WRAP.

PLANT adds detection but not the primary authorization guarantee. A hard PLANT commitment means the agent committed to a decoy that was not needed for benign task completion. Lack of PLANT deployment or lack of PLANT hit does not imply the effect is safe; WRAP remains the decisive commit gate.

## 11. Evaluation protocol

The main metrics are:

- `BU`: benign utility on clean tasks;
- `AU`: utility under attack;
- `ASR`: attack success rate, where lower is better.

All methods must run on a frozen benchmark protocol: same task set, same attack set, same target model, same judge model when the benchmark requires a judge, and the same evaluator denominator. Detection-only baselines are reported separately or explicitly marked as detect-as-defense if their detections are converted into blocked attacks.

## 12. Limits

The method depends on manifest quality. Missing schemas, wrong effect labels, wrong receipt roles, or unregistered nested helpers can cause fail-closed utility loss or unsafe allowance. The method also does not defend unmediated channels, malicious code that executes outside the registered runtime, or user-authorized harmful effects. Semantic Binding is bounded but model-assisted, so it is a utility component rather than a trusted source of new authority.

## Changelog

- 2026-08-14: Rewritten as the final Contract--Receipt PLANT--WRAP methodology. Removed implementation-history prose and centered the paper claim on manifest-backed effect mediation, four binding families, three PLANT carrier classes, continuation, and UnitBroker nested-effect mediation.
