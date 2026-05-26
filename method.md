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

- 2026-05-25: Added the public-benchmark validator approximation and empirical
  boundary from ToolSafe AgentDojo / AgentHarm validation. Linked experiment:
  `LOGS/2026-W21.md#EXP-2026W21-002`.
