# Active Defense for AI Agents

## Current Thesis

The current scheme is a lean Contract--Receipt--PLANT--WRAP runtime for agent
capability safety. A trusted user task is compiled once into a small
`TaskContract`; runtime observations become immutable receipts; proposal-time
binding can select only code-enumerated evidence; and every externally visible
effect passes a deterministic WRAP gate. PLANT runs independently as a
commitment sensor over model-visible carriers, dependency premises, and
substrate artifacts.

The claim is narrow and operational: authority for a concrete effect must close
to the trusted task, registered substrate manifest, and runtime receipts.
Untrusted runtime content can provide evidence only through explicit, task-local
roles and cannot create a new action, source, relation, argument role, or
authority edge.

## Core Objects

- `EnvironmentPlan`: task-independent trusted manifest compiled from operator or
  substrate facts. It records capability names, effect/observation booleans,
  argument schemas, required arguments, content types, output schema, receipt
  role, Skill membership, and plantable source surfaces.
- `TaskContract`: task-specific clause program with `Acquire`, `Derive`,
  `Conditional`, and `Effect` clauses. It is generated before target execution
  and accepted only after deterministic validation.
- `Receipt`: immutable runtime observation of an actual capability call and its
  arguments, return value, effect-return bit, and receipt role.
- `ClauseReceiptBinding`: ownership edge from a Contract clause to a receipt.
  It records reachability but does not choose a semantic value.
- `BindingProof`: proposal-local evidence produced by deterministic replay plus
  an optional constrained Binding Agent. The agent can select only opaque
  candidate ids from a code-built domain.
- `WRAP`: deterministic effect gate. A call passes only when one matching
  `Effect` clause closes every supplied argument and no unauthorized
  authority-like content atom is present.
- `PLANT`: independent commitment detector. It instruments observation,
  dependency, and substrate planes and gates only when a certified decoy reaches
  a real commit boundary.

## Runtime Flow

1. The trusted environment is registered into an `EnvironmentPlan`. Runtime tool
   descriptions, benchmark labels, attack metadata, and agent-visible prose do
   not extend this plan.
2. A trusted task is compiled into one `TaskContract`. Transport failures may be
   retried under the same schema; validation failures fail closed.
3. The target agent executes. Observations are recorded as receipts and may be
   exposed through PLANT-decorated carrier views.
4. Receipt ownership is reconciled monotonically against `Acquire` clauses.
   Deterministic `Conditional` operators replay closed relations such as
   `argmax`, `count`, `union`, `select_eq`, arithmetic, and time operations.
5. When the agent proposes an effect, unresolved argument roles are compiled
   into Binding goals. A Binding Agent, if used, selects from candidate ids only;
   code projects the final values and refs.
6. WRAP gates the effect. It allows exactly one matching `Effect` clause whose
   action, required arguments, optional submitted arguments, literals,
   from-bindings, delegated proofs, content atoms, defaults, and authority
   receipts all validate.
7. PLANT checks the same boundary independently. Observation marker/object
   adoption, substrate artifact invocation, and copied final responses can gate;
   dependency-basis presentation is audit evidence and does not authorize.
8. Approval and continuation are safe-by-default compatibility paths. Approval
   is exact, one-shot, and user-scoped. Continuation can repair or replan only
   from sanitized runtime context and must revalidate through the same WRAP
   gate.

## Contribution Boundary

The system is not a general content-safety classifier, full information-flow
control system, or universal prevention layer. It assumes a mediated substrate
for effectful actions and a trustworthy registration boundary for capability
manifests. If an agent can reproduce the same real-world effect through an
unmediated shell, network, credential, or side channel, WRAP cannot claim a hard
boundary for that effect. PLANT may still provide commitment evidence when a
certified decoy is actually used, but it does not prove coverage of every
unmediated path.

## Evaluation Boundary

Evaluation uses the unified frozen protocol under `code/`: one adapter and one
frozen dataset per benchmark, shared by every method. The stable entry point is
`python3 -m code.run`; data integrity and result coverage are checked through
`protocol.json` and `experiment_results/METADATA.json` rather than inferred from
historical logs.

Current result files are not all complete main-table artifacts. The validator
may report missing methods or denominator mismatches even when the method under
inspection has passing coverage for a subset. Treat `experiment_results/` as the
canonical surface only after `python3 -m code.run --verify-only --verify-results
experiment_results` passes for the intended comparison set.
