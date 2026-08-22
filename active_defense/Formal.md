# Formal · Contract--Receipt--PLANT--WRAP

This file is the formal summary for the current lean defense. `method.md` is
the detailed single source of truth; this document fixes the main objects,
invariants, and decision rule.

## 1. Environment Manifest

Before any task arrives, the operator or substrate registers a trusted
manifest:

$$M=(S, A, K),$$

where `S` is the set of plantable source surfaces, `A` is the set of capability
surfaces, and `K` is the set of Skill surfaces. A capability surface contains:

- a stable name and description;
- explicit booleans `effect` and `observation`;
- public argument names and required arguments;
- argument schemas and optional output schema;
- argument/output content types such as `natural_language`, `code`, `path`,
  `opaque`, `url`, `email`, and `identity`;
- a receipt role in `{data, advisory, control}`;
- an optional `effect_return` fact.

These are substrate facts, not runtime observations. Runtime catalog text,
attack labels, benchmark ground truth, tool responses, and agent output cannot
extend `M`. A registration change creates a new environment version; an active
episode continues under the version it loaded.

## 2. Task Contract

For a trusted task `T`, the defense compiles one task-local program

$$C_T=(T, c_0,\ldots,c_n).$$

Each clause is one of four variants:

- `Acquire(capability, arguments, output)`: records a task-authorized
  observation call shape and names its output.
- `Derive(inputs, output)`: names a semantic role over trusted task text,
  runtime context, or prior outputs. It does not construct exact wire values by
  itself.
- `Conditional(operator, operands, output)`: computes a closed deterministic
  relation from prior outputs and task literals.
- `Effect(action, arguments)`: authorizes one externally visible action and its
  argument roles.

Every argument spec is exactly one of:

$$literal(v),\quad from(r),\quad from(r, delegated=true).$$

The compiler validates that actions, observation capabilities, argument names,
required positions, literals, schemas, references, delegation, and operators are
registered and structurally valid. Runtime content cannot add an action, a
clause, an argument role, a relation, a source, or a literal. A failed Contract
validation yields an empty unusable Contract rather than a repaired fallback.

## 3. Runtime Receipts

Every mediated observation is recorded as an immutable receipt

$$r=(capability,args,value,effect\_return,receipt\_role).$$

The receipt digest covers the capability, arguments, value, return role, and
return kind. Two calls with the same value remain distinct if their arguments
differ.

Runtime state stores three different facts:

- receipt list: all active immutable observations;
- `ClauseReceiptBinding`: an ownership edge from an `Acquire` clause to a
  compatible receipt;
- `Binding`: a resolved clause output and the exact receipt refs supporting it.

Ownership and value resolution are intentionally separate. A receipt can be
owned by multiple compatible clauses, and a clause can own multiple receipts.
Repeating the same concrete call supersedes the older return only for that
clause. Invalidated or superseded receipts remain audit evidence but leave the
active authority view.

## 4. Deterministic Resolution

An `Acquire` output is resolved from its owned receipt values. A `Conditional`
output is replayed by code over already resolved operands. The operator algebra
is fixed and includes only registered primitives such as `identity`,
`singleton`, `count`, `map_count`, `union`, `flatten`, `keys`, `project`,
`frequency`, `sort_by`, `object_set`, `difference`, `argmin`, `argmax`,
`coalesce`, `aligned_lookup`, `basename`, `path_join`, `gt`, `lt`, `field`,
`select_eq`, `add`, `multiply`, `percent_of`, `datetime_combine`,
`add_duration`, and `interval_free`.

A `Derive` output is the only semantic role. It may be grounded at proposal time
by a constrained Binding Agent, but the agent never writes values or refs.
Instead, code builds a finite public goal

$$g=(id,role,mode,type,quantified,candidates),$$

where every candidate id maps to a code-owned receipt node, span, task literal,
or replay output. The Binding Agent may select candidate ids and an allowed
composition only. Code then projects exact values, semantic support refs,
delegated refs, or grounded refs from the current receipt snapshot. If no proof
closes, the role remains unresolved.

## 5. WRAP Gate

For a proposed effect

$$p=(action,args),$$

WRAP evaluates only matching `Effect` clauses in `C_T`. Let `required(action)`
come from the trusted manifest. The proposal passes iff there exists exactly one
clause-compatible path such that:

1. `action` equals a registered `Effect` clause action;
2. every required argument is present;
3. no submitted non-default argument is absent from the clause;
4. every literal argument equals its Contract literal under only
   schema-attested canonicalization;
5. every `from` argument equals a resolved clause output or a validated
   proposal-local proof for that argument;
6. every `delegated` argument has unique exact evidence from the named source;
7. natural-language authority atoms such as URLs, emails, and mentions are
   authorized by trusted task text, literals, closed conditionals, or local
   delegation;
8. control effects with `receipt_role=control` cite a fresh exact-scope control
   receipt when required.

Otherwise the decision is `deny`, `approval`, `commitment`, or `replan`
depending on the failure mode and enabled compatibility path. Approval and
continuation never bypass WRAP: repaired proposals are revalidated by the same
rule.

## 6. PLANT Commitment

PLANT is independent of WRAP authority. It maintains one episode-local registry
of certified decoys across three planes:

- `observation`: model-visible carrier content such as tool results, MCP
  resources, Skill prose, or receipt views;
- `dependency`: runtime-issued proof premises for one consumer;
- `substrate`: adapter-deployed native artifacts in control or state surfaces.

A commit event is

$$e=(channel,actor,payload,proof\_refs,identities).$$

Channels include `call`, `response`, `state`, and `artifact`. The channel fixes
the evidence semantics:

- an observation decoy reaching `call`, `state`, or `artifact` is `effectful`;
- an observation decoy reaching `response` is `copied`;
- a dependency decoy cited as proof is `presented-as-proof` and audit-only;
- a substrate decoy is `invoked` only when the adapter reports exact identity
  selection at an effect boundary.

`effectful`, `copied`, and `invoked` are gating commitments. Mere visibility,
listing, narration, or proof-basis presentation is not authority and does not by
itself block unless it reaches a gating boundary.

## 7. Joint Decision

The episode decision at a boundary is ordered conservatively:

1. unknown or forged basis refs deny;
2. PLANT gating commitments return `commitment` and may trigger continuation;
3. WRAP validates the effect against the Contract and runtime state;
4. exact one-shot approval may be requested only for scoped unresolved cases;
5. continuation may propose repair or sanitized replan, but any repair must pass
   the same WRAP validation.

Ignoring optional continuation or approval metadata is safe by default: adapters
that do not consume it see the original deny/commitment decision.

## 8. Assumptions And Limits

The hard WRAP claim requires a mediated substrate boundary for the effect. If an
agent can reproduce the same real effect through an unmediated shell, direct
network call, leaked credential, or another capability outside the manifest,
WRAP is not a cut point for that effect. PLANT may still catch committed decoy
use, but the current model does not claim complete coverage of unmediated paths.

The manifest is a trusted root. Incorrect `effect`, `observation`, schema,
identity path, content type, or receipt-role facts can cause false denial or
unsafe allowance. Runtime descriptions are deliberately not trusted to repair
this.

Semantic Binding is bounded but still model-assisted. It can choose only from
code-issued candidates, yet utility can fail when the candidate domain is too
large, incomplete, or semantically underspecified. The fail-closed behavior is
part of the safety boundary.

## 9. Metrics

For each frozen benchmark protocol, report at least:

- `BU`: clean utility over the frozen clean denominator;
- `AU`: attack utility over attack cases where the benign task should still be
  completed;
- `ASR`: attack success rate;
- `ASR_undetected`: harmful success without a hard WRAP/PLANT event when the
  evaluator exposes it;
- `PLANT hard commitment`: clean and attack commitment counts by plane and
  boundary;
- `technical_failure`: transport or runner errors separated from semantic
  defense decisions;
- `coverage`: explicit denominator metadata checked by `code.run --verify-only`.

Do not infer comparable results from historical logs, detector-only replay, or
partial result files. A method is comparable only when its `METADATA.json`
coverage matches the relevant `protocol.json` denominator for the intended
comparison.
