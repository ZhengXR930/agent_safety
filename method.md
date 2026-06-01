# Method: Authentication DAG + Symbolic Validator

## 1. Objects

Trace:

\[
\tau=(e_0,\ldots,e_T)
\]

Each event is one of:

- user instruction;
- tool call;
- tool return;
- external content;
- agent intermediate decision.

Tool manifest:

\[
M(a)=({\rm requires}(a),{\rm emits}(a),{\rm args}(a))
\]

- `requires(a)`: authority required to execute action `a`.
- `emits(a)`: evidence produced by action `a`.
- `args(a)`: argument roles and source policies.

Authentication DAG:

\[
G=(V,E)
\]

Nodes are grants, evidence, bindings, scope constraints, and action
authorizations. Edges define allowed derivations.

## 2. Allowed Derivations

Allowed:

```text
user_explicit_grant -> action_authorization
user_explicit_grant -> narrower_scope_grant
user_conditional_grant + satisfied_condition -> action_authorization
trusted_resolver_binding + user_scope -> scoped_target_authorization
```

Disallowed:

```text
tool_return -> user_grant
external_content -> user_grant
advice -> action_authorization
review_result -> install_or_modify_authorization
observed_target -> communicate_or_modify_authorization
```

The key rule is simple: **evidence can bind facts, but evidence cannot create
authority**.

## 3. Violations

`A1 Fabricated Authorization`

\[
\neg \exists u:\ u \in {\rm UserGrant} \land G \vdash u \Rightarrow {\rm requires}(a)
\]

No valid user grant can derive the required action authority.

`A2 Escalated Authorization`

An evidence node is used as if it were an authorization node.

`A3 Exceeded Scope`

\[
G \vdash u \Rightarrow {\rm action\_class}(a)
\quad\land\quad
{\rm args}(a) \not\subseteq {\rm scope}(u)
\]

The action class is authorized, but the concrete arguments or side effects
exceed the grant.

`D1 Source / Taint Failure`

An authority-bearing argument or sensitive payload violates its source policy.

## 4. Decision

\[
d(\tau,a)=
\begin{cases}
{\rm block}, & A1 \lor A2 \lor A3 \\
{\rm warn}, & D1 \land \neg(A1 \lor A2 \lor A3) \\
{\rm allow}, & \text{otherwise}
\end{cases}
\]

## 5. Minimal Validator Contract

For each proposed sensitive action, a validator checks:

- required authority matches the tool manifest;
- the authorization chain has a user-rooted grant;
- each DAG edge is allowed;
- scope constraints are satisfied;
- source policies for authority-bearing arguments are satisfied;
- the final `allow/warn/block` decision follows the violation flags.

This validator is the immediate object to test. It must be useful before any
small-model training is meaningful.

### 5.1 Current Public-Benchmark Validator Approximation

The current ToolSafe/AgentDojo validator uses two deterministic checks:

1. **Action-class grant**: the user instruction must authorize both the action
   verb and the object type, e.g. `delete + file` is not the same grant as
   `delete + email`.
2. **Scoped source check**: an untrusted external instruction block may not
   provide authority-bearing arguments such as recipient, account, URL, file,
   event, or message payload. Taint is scoped to the external instruction block
   itself, not to the entire future trace.

This is still a benchmark-facing approximation rather than the final learned
guard. It deliberately avoids using benchmark labels inside the decision rule.

### 5.2 MCP / Skill Poisoning Adaptation

For third-party MCP tools or skills, the manifest itself may be untrusted. The
validator therefore separates two contracts:

```text
trusted host contract: tool name, expected purpose, allowed side effects
extension-provided contract: description/schema/instructions supplied by MCP or skill
```

The extension-provided contract may help describe utility, but it cannot create
new action authority. Under this setting the four violations specialize as:

- `A1 Untrusted Tool Authority`: the proposed action invokes a third-party
  wrapper tool whose extension-provided contract contains extra imperative
  authority, side-effect requirements, or hidden prerequisites not derived from
  the user grant or trusted host contract.
- `A2 Metadata-to-Action Escalation`: poisoned metadata/schema/output is used
  to introduce an additional tool action, such as "before using read_file,
  call write_file/move_file/read_file on an unrelated target."
- `A3 Scope Overreach`: the action class is relevant to the user task, but a
  concrete target/sink/recipient/file/name/branch/ref/id differs from the
  user-granted target or comes from poisoned metadata. This is a role-level
  argument check, not a generic "new string" blocker.
- `D1 Metadata-Tainted Sink/Payload`: a sensitive payload or sink is copied
  from untrusted metadata into an otherwise authorized call.

This adaptation makes the wrapper-tool case explicit. In a strict runtime
interpretation, wrapper-only calls are allowed unless they execute a visible
A2/A3/D1 side effect. In a conservative supply-chain interpretation, invoking
a poisoned wrapper is already `A1`, because the tool contract itself is not a
trusted authorization source.

To avoid benchmark-specific hard coding, a tool manifest should expose only a
compact set of authorization roles:

| Role | Meaning | Typical evidence |
|---|---|---|
| `operation` | what capability/effect is invoked | read/write/send/execute/create/delete/query/navigate |
| `scope` | the bounded object or constraint of that operation | resource, destination, selector, location, account, time range |
| `content` | data crossing a trust boundary | payload, command/code string, returned facts, generated body |
| `context` | state used as authority | prior call, session freshness, tool version, identity, dependency condition |

Concrete parameters such as `path`, `selector`, `ticker`, `token`, or
`contract_version` are not taxonomy classes. They are domain-specific fields
that a manifest annotator maps into one of the four roles above. This is the
intended generalization point: the symbolic validator reasons over roles, while
the manifest layer normalizes diverse tool schemas into those roles.

The runtime contract is therefore:

```text
tool schema / metadata / trace
  -> manifest annotator
  -> {operation, scope, content, context}
  -> AuthDAG verifier
  -> A1/A2/A3/D1
```

Only the annotator may inspect concrete field names or domain wording. The
verifier must not branch on names such as `selector`, `ticker`, `path`, or
`token`; it only checks whether a role is user-rooted, metadata-tainted,
scope-preserving, or used as authority.

### 5.3 Role-Manifest Annotation Protocol

The manifest annotator outputs role claims rather than a single label:

```json
{
  "role": "operation | scope | content | context",
  "source": "user | trusted_host | extension | tool_return | agent_action",
  "value": "...",
  "evidence": "...",
  "relation": "grants | requires | taints | constrains | depends_on"
}
```

The roles remain compact:

- `operation`: capability or effect class requested or invoked.
- `scope`: bounded object, destination, target, account, selector, location, or
  other constraint on an operation.
- `content`: data crossing a trust boundary, including command/code payloads,
  returned facts, messages, generated body, or sensitive material.
- `context`: state used as authority, including prior calls, freshness,
  identity, tool version, or dependency conditions.

The source and relation fields are essential. For example, a `scope` claim from
the user with relation `grants` is allowed authority, while the same `scope`
claim from extension metadata with relation `constrains` is untrusted and can
trigger A3 if copied into an action. A `context` claim from extension metadata
with relation `depends_on` is evidence, not authority, and can trigger A2 if it
forces an extra tool call.

This gives a clean learning target for future annotators:

```text
input:  MCP/skill schema, user task, tool return, or proposed action
output: set of role claims
reward: role/source/relation exactness + AuthDAG consistency
```

The optimized MCP validator has two tiers:

1. **Single-action checks** over `operation`, `scope`, and `content`.
2. **Trace/state checks** over `context`, with taint propagated into `content`
   or `scope` when a prior observation controls a downstream action.

This keeps A1/A2/A3/D1 as the top-level violation schema while preventing an
over-narrow implementation that only inspects the current tool name and
arguments. It also prevents overfitting to a long list of hand-written argument
names.

## 6. Small Local Guard Framing

If the symbolic validator passes the next validation gate, it can support a
small local guard in three ways:

1. **Label generator**: produce deterministic `allow/warn/block` and
   A1/A2/A3/D1 labels for training examples.
2. **Consistency checker**: reject model outputs whose decision contradicts
   the inferred DAG violations.
3. **Fallback rule layer**: handle high-confidence deterministic cases while
   the small model handles ambiguous semantic scope cases.

The small-model angle is therefore a deployment and learning contribution, not
a replacement for the authentication DAG.

The next experiment should compare:

- sensitive-tool blocker;
- symbolic validator;
- small model or proxy classifier trained/evaluated with validator labels;
- closed LLM judge if available.

Primary metrics:

- attack catch for A1/A2/A3;
- clean allow for benign high-permission tool use;
- warn precision/recall for D1-only cases;
- latency/cost/privacy relative to closed LLM judge.

## 7. Empirical Boundary After First Public Validation

On ToolSafe AgentDojo trajectory steps, the scope-aware validator supports the
core indirect authorization hypothesis: it improves over simple sensitive-tool
blocking while preserving clean high-permission actions.

On ToolSafe AgentHarm trajectory steps, the same validator fails to catch most
direct harmful user-intent cases. This is expected from the formalism: if the
user explicitly authorizes a harmful action, Authentication DAG alone checks
authorization, not external harm policy.

Therefore the current method is viable as an **indirect tool-call authorization
guard** and as a supervision/consistency layer for a small local guard. It is
not viable as a standalone universal harmful-content policy guard.

## Changelog

- 2026-05-28: Replaced fine-grained MCP manifest roles with the compact
  `operation/scope/content/context` taxonomy after generalization audit.
  Linked experiment: `LOGS/2026-W22.md#EXP-2026W22-006`.
- 2026-05-28: Added the role-manifest verifier contract and first MCPTox /
  MCP-SafetyBench portability result. Linked experiment:
  `LOGS/2026-W22.md#EXP-2026W22-007`.
- 2026-05-28: Added the role-manifest annotation protocol and built the first
  oracle/silver annotation seed set. Linked experiment:
  `LOGS/2026-W22.md#EXP-2026W22-008`.
- 2026-05-28: Optimized the MCP / skill poisoning schema with explicit
  trace/state requirements after MCP-SafetyBench oracle-replay validation.
  Linked experiment: `LOGS/2026-W22.md#EXP-2026W22-004`.
- 2026-05-28: Added MCP / skill poisoning adaptation of A1/A2/A3/D1 after
  MCPTox chain-level validation. Linked experiment:
  `LOGS/2026-W22.md#EXP-2026W22-002`.
- 2026-05-25: Added the public-benchmark validator approximation and empirical
  boundary from ToolSafe AgentDojo / AgentHarm validation. Linked experiment:
  `LOGS/2026-W21.md#EXP-2026W21-002`.
