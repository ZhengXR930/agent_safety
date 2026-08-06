# Method · Perception-Guided PLANT–WRAP

## Minimal representation

Before any task exists, environment perception persists

$$D^{env}_t=(S_t,P_t,W_t),$$

where $S_t$ is the perceived capability/effect schema, $P_t$ is the PLANT placement, and $W_t$ is the
set of mediated capability boundaries. When a trusted task $T$ arrives, but before its execution, a
separate task contract $C_T=\operatorname{ContractSynthesis}(T,S_t)$ is generated once and persisted by
`schema version + environment fingerprint + trusted task fingerprint`. The contract is a small
clause-local task program

$$C_T=(T,(c_k)_{k=1}^m),\qquad c_k=(id_k,i_k,S_k,o_k\ \mathsf{xor}\ e_k),\quad e_k=(a_k,A_k).$$

Each clause contains one trusted local instruction $i_k$ and named sources $S_k$. A derivation clause
produces one semantically named output $o_k$ (for example `c0.channel`); an effect clause authorizes one
mediated action $a_k$ with arguments $A_k$. Argument constraints are only `literal(v)`, `from(source)`
(one or several sources), or `unknown`. Anonymous variables, a separate relation table, numeric relation
indices, and a Contract-level free-text type are absent. The trusted capability manifest instead declares
`argument_types` and `output_types`. These types select task-independent parsing and comparison only:
`natural_language` activates registered URL/email/mention parsers, while `code`, `path`, `opaque`, `url`,
and `email` retain their own deterministic syntax. A type never grants authority or predicts a task value.
When the trusted request explicitly entails a
closed deterministic relation, a derivation Clause may additionally carry one expression

$$e_k ::= identity(s)\mid count(s)\mid union(s)\mid argmin(s_1,s_2)\mid
argmax(s_1,s_2)\mid difference(s_1,s_2),\qquad s_i\in S_k.$$

The expression has no literals, object paths, predicates, proposal values, or nested calls. Contract
synthesis normally uses one TaskContract Agent call. Inside that role the model rehearses a plausible execution over the
trusted task and registered capability manifest, then returns one typed final Contract; rehearsal is reasoning,
not a second persisted plan or projection. A typed-transport failure (wrong/missing tool call, malformed JSON,
non-object payload, or request failure) permits exactly one complete same-schema retransmission. It receives no
semantic validation feedback and is not reflection or partial repair; a second transport failure rejects the
whole Contract. Deterministic validation errors never trigger retransmission. Parse and validation failures are
recorded separately in the trace. Deterministic code injects the exact trusted task root, normalizes Clause
ids/redundant source closure, resolves only the unambiguous `cN.output` alias to that Clause's single declared
output, and lowers an already-proposed aggregate used by several effect roles into role-local SSA outputs.
These compiler steps add no action, capability, runtime value, field projection, or authority edge; paths such
as `c0.files.id` remain invalid. Code accepts the final Contract atomically only if every action, argument
position, source, dependency, and relation passes structural validation. There is no model reviewer, repair call, prefix salvage, compatibility fallback,
or second Contract representation. Accepted expressions are evaluated on demand over one immutable
tool-I/O receipt snapshot. Their results are proposal-local values, not persisted Clause receipts or
authority. Relations outside this small language likewise remain the prose-local map
$i_k:S_k\rightarrow o_k$. Clause order records only acyclic data dependencies, not a prescribed tool-call
schedule. For `argmin/argmax`, candidate–measurement correspondence must be established by the immutable
measurement receipt's call-argument/parent anchor; incidental receipt order is never used for alignment.
Their item and score operands must be distinct declared sources; reusing the item domain as its own score is
rejected even though it is syntactically computable.
`union(s)` is defined only for outputs of a repeatable observable Clause whose call argument is bound to a
complete earlier Clause-output domain also named by the union Clause. WRAP returns the deduplicated union
only after call arguments prove that every domain member has a successful receipt; a partial traversal
remains unresolved.

Contract synthesis directly compiles the trusted request into its smallest specification-only Clause graph;
there is no separate semantic-expansion call. A Clause states one task requirement, its earlier semantic
inputs, one named result or requested effect, and optionally a deterministic condition explicitly stated by
the task. The condition is a specification such as minimum, maximum, union, or difference—not a plan for
proving it. The Contractor does not emit receipt paths, runtime values, call ownership, coverage witnesses,
provenance parents, or alignment steps. Observable capabilities and effect arguments use exact manifest
names, but their runtime calls remain unpredicted. A task-selected reference may be an abstract Clause output
consumed by a later observable Clause; the actual reference and receipt path exist only at runtime.

The Agent executes the trusted task once. Before execution, each effect clause installs one local WRAP gate
at the already-mediated environment capability boundary. Every successful observation appends one immutable,
content-addressed canonical receipt. A receipt becomes WRAP authority only through an episode-local, append-only
`ClauseReceiptBinding` anchored to the trusted task receipt, exact Contract, acquisition Clause, capability,
and call arguments:

$$r_o=(n_o,args_o,h(v_o)),\quad
b_o=(h(T),h(C_T),id_k,h(r_o),h(args_o)),\quad p=(a,args).$$

A dynamic observation call receives an admission only after its outbound arguments Pass the installed
intermediate Clause gate. Admission is a one-shot token keyed by the substrate tool-call id and exact
`(capability, arguments)`; exactly one matching successful return consumes it. Reuse, a mismatched return, or a
later equal call receives no authority from an earlier admission. A pure observation may bind without a model
only when all call arguments follow deterministically from literals or already-bound Clause outputs. Binding is
reconciled to a fixed point when receipts arrive, so later complete domain evidence may attribute an earlier
call, but proposal content can never create ownership. The append-only binding log remains audit evidence; for
an exact Clause/source/argument location, only the newest receipt version is active WRAP authority. Unbound,
schema-invalid, superseded, and quarantined observations may remain visible to the target Agent and PLANT but
cannot enter the canonical WRAP authority view. When a proposal reaches a gate, WRAP backward-resolves only
through that view and evaluates closed relations from scratch. Runtime content may instantiate values but cannot
add an action, source, relation, Clause, or binding. The value $v_o$ remains in an execution sidecar; no Agent
internal state or episode-wide flow graph is reconstructed.

Two immutable roots may precede runtime observations. The trusted request is recorded as a task receipt.
When the substrate has already fixed an episode value such as the workspace, repository, account, sandbox,
or server session, the adapter may also issue a non-plantable `runtime-context` receipt. Its values remain
in a sidecar indexed by exact `(capability, argument)` positions; the versioned manifest stores
only the existing `SourceSurface` identity. TaskContractor may declare that an argument comes from
this source when the request leaves it to the current environment, but never sees or predicts its value.
At the boundary, an exact attested value binds to that receipt, a different value is a conflict, and a
missing/ambiguous attestation is unresolved. Agent output, tool responses, attack metadata, benchmark GT,
and runtime catalog text cannot create or modify this root.

Persistent state is not a third authority root. At a mediated state write, the substrate records only

$$s=(id_s,h(v_s),authorized_s).$$

The authority bit is true only when the write passed WRAP and every value-bearing binding comes from the
trusted task, attested runtime context, or an already-authorized saved-state version. No leaf parents or
cross-task data-flow graph are persisted. A later Skill/session receives the bit only when both the opaque
state identity and actual value digest match. An unauthorized state or a missing/mismatched record cannot
ground a proposed effect argument and is unresolved (Approval), rather than being asserted to be an attack.
PLANT-blocked writes create no record. This is coarse authority transport at explicit storage boundaries,
not provenance reconstruction through Agent hidden state or whole-program IFC.

## Joint decision

WRAP assumes a trusted environment manifest with two independent substrate facts per complete tool/MCP
entry: $B_{env}$ says invocation requires pre-commit mediation, while $O_{env}$ says a successful invocation
returns an observation that can extend runtime provenance. The sets may overlap: an external fetch can be
in $B_{env}\cap O_{env}$, a mutation in $B_{env}\setminus O_{env}$, and a local read in
$O_{env}\setminus B_{env}$. These facts are fixed per environment version and contain no task, attack,
ground-truth, allowed value, or task-flow information. A manifest may additionally identify open-prose
argument positions; this never authorizes an action, destination, identity, or embedded authority reference.
When the substrate exposes a deeper server-side
commit boundary, that boundary replaces whole-call mediation. Inferred manifests are automation ablations,
not part of the core WRAP guarantee.

For MCP, the trusted manifest is compiled once at operator-approved server registration or installation,
after protocol initialization and capability discovery. The compiler may consume the complete advertised
`tools/list` JSON Schema and persists the compact `EnvironmentPlan` fields: `name`, `description`,
`arguments`, `required_arguments`, `argument_types`, `output_types`, `receipt_role`, `effect`, `observation`,
and the advertised `output_schema` when one exists. `receipt_role` is one of `data`, `advisory`, or `control`
and defaults to `data`; `advisory` contributes no authority, while `control` can introduce authority only
through an exact task-, episode-, action-, and argument-scoped runtime receipt. The output schema is trusted
only as an operator/substrate-attested return-shape assumption:
a successful value that violates it remains observable but cannot become WRAP authority. It certifies fields,
types, and container shape—not that a field is semantically the task's “latest”, “best”, or intended object;
such a claim still requires an explicit task relation and sufficient receipts. A missing output schema therefore
removes shape-based authority rather than inviting the Contractor to invent fields. `arguments` is the public
call shape, not a ranking of security importance. The hash of the full
registration snapshot determines the existing plan identity/version;
no schema, default, task allowance, or separate version field is added to the runtime manifest. A runtime
catalog change cannot silently extend authority: it requires explicit trusted re-registration and produces
a new immutable plan for later episodes, while an active episode continues using its one loaded plan.
This guarantee assumes that the deployment retains the exact registration snapshot (or an equivalent
package lock plus reproducible discovery result). A benchmark URL without the installed version or original
`tools/list` response is not sufficient evidence for a complete trusted manifest. In that case, evaluation
must distinguish version-pinned official entries from benchmark-declared interface fallbacks; the latter may
exercise compatibility but cannot be cited as official semantic authority.
JSON Schema `required` remains only a call-validity fact for the underlying tool and is not converted into
an authorization label. WRAP strictly checks every argument named by the selected Contract gate. A submitted
required position omitted by the Contract must still close to that Clause's local receipts or runtime
context because the substrate cannot execute without it. A submitted optional position omitted by the
Contract is inspected by PLANT/Detector in the original proposal, then removed before substrate commit
after Pass; it is neither silently authorized nor turned into a synthetic Approval. The compiled result is
persisted with the environment version and is never regenerated inside an episode.

The mediation unit follows the substrate. In a one-shot MCP tool-selection interface such as MCPTox, one
complete server request is the smallest enforceable unit: every method advertised in the current catalog is
therefore in $B_{env}$. The control plane consumes only method identity and argument shape; free-text method
metadata remains an untrusted runtime observation exposed to PLANT and the Agent, not Contract authority.
Because that interface does not expose a successful method result to a later Agent turn, those entries are
not in $O_{env}$. This is not a method-name taxonomy: the adapter applies one mediation rule to the whole
current MCP boundary and assumes no pinned clean catalog. If a rejected proposal invalidates the only turn,
recovery discards that proposal and retries the original task at most once in a fresh Agent session with the
same current catalog plus a deny-only receipt. The benchmark's clean pair and attack labels remain
evaluator-only and never enter the attack EnvironmentPlan, Contract, or retry state.

WRAP first constructs neutral proposal provenance

$$P(p)=(id_k,a(p),\{arg\mapsto(expected\ sources,receipt\ inputs)\}),$$

where `expected sources` come from the immutable clause and `receipt inputs` are the immutable runtime
objects actually consulted for that candidate argument. This object contains no conflict or response
decision, so a rejected candidate retains its attempted source/input trace without receiving authority.
A local gate then compares $P(p)$ with its clause and emits only
$G(p)=(conflicts,unresolved)$. For a proposed write, WRAP allows it iff exactly one effect clause matches,
trusted literals match, every runtime-derived argument binds to the clause's named sources or prior outputs,
every additional submitted argument also binds locally to those same sources, and no position remains
unresolved:

$$
\operatorname{AllowWrite}(p)=
\exists!c_k:\ a(p)=a_k\land \operatorname{LiteralOK}(p,A_k)\land
\operatorname{BindOK}(P(p),S_k)\land\operatorname{ReferenceOK}(p,C_T,R)\land
\neg\operatorname{Unknown}(A_k).
$$

The first proposal-time resolution of a semantic Clause output requires local semantic entailment
$\operatorname{Entails}(i_k,R_k,o_k)$ over only candidate receipts selected by the Clause's declared
source capabilities and argument constraints. Exact containment
in a receipt proves grounding but not the Clause relation: a real channel is not thereby the least-active
channel. `supported` requires the supplied facts to be sufficient to establish the relation; a missing
source object, alternative, measurement, or intermediate result yields `uncertain`. After this one proof,
exact reuse of the authorized output is deterministic and invokes no further judge. For a validated closed
expression $e_k$, WRAP replaces semantic entailment with deterministic evaluation
$o_k=\llbracket e_k\rrbracket(R_k)$. A proposal equal to the evaluated result is supported; a different
proposal is a conflict. Every proof is keyed by the exact receipt snapshot; a changed snapshot is recomputed,
so no persisted relation output can become stale. Thus the model compiles the trusted relation once, while
runtime code computes its result and cannot infer a relation from the proposal. There is no
benchmark-specific predicate or executor.

`LiteralOK` is exact equality for authority-bearing positions. Representation changes must be implemented
as deterministic, task-independent canonicalization rather than an LLM equivalence judgment. A mismatch
is a conflict, so a semantic model cannot silently change an identity or destination.

For a manifest-declared `natural_language` position, WRAP does not bind the generated prose to a canonical
receipt value and does not ask a Judge whether it is faithful, relevant, or harmless. The argument type
selects the versioned, side-effect-free authority-atom parsers the substrate applies. `code`, `path`, and
`opaque` positions do not run natural-language regexes merely because their strings contain punctuation.
For every active grammar, WRAP invokes the registered substrate parser/resolver and
binds its canonical entity—not its display spelling—to the trusted task or a Clause-reachable receipt:

$$
\operatorname{ReferenceOK}(x,C_T,R)\equiv
\forall t\in\operatorname{ParseResolve}_{S}(x),\
\exists r\in\operatorname{Reachable}(C_T,R):
t\in\operatorname{ParseResolve}_{S}(r).
$$

Ordinary prose contributes no authority and is otherwise unchecked by WRAP. A reference proven outside a
closed authorized domain is a conflict. A declared grammar without an installed resolver is unresolved,
never silently inert. Completeness is relative to the substrate's actual accepted grammar: obfuscated text
is included iff the substrate itself resolves it. Authority-like natural language that the substrate does
not interpret as control remains prose; if the Agent later turns it into a structured effect argument, that
argument is checked at its own gate. PLANT commitment remains an independent hard signal over the complete
original proposal.

A quantified Clause graph also carries a code-verifiable completeness obligation even if the optional
closed relation was omitted by the Contractor. If a consumer names both a domain output and an output
produced by invoking a capability over that domain, every domain member must have a successful,
argument-anchored receipt before semantic materialization may support a
collection-wide result. Partial coverage is `uncertain`, never model-repaired. This rule uses only Clause
references and call arguments; it does not infer operators from instruction text.

For selection and extraction into an authority-bearing slot, support must name the exact selected scalar
node; a record or collection root does not prove one field merely because it contains that field.
Deterministic transformations and closed relations are recomputed by code. Generated summaries and message
bodies are not promoted into authority; they use the open-prose rule above when the registered capability
marks that position as content.

A selected structured object remains a common source carrier, but it does not itself authorize several
different scalar argument roles. For every runtime-derived effect argument, the Contract introduces one
single-value Clause output with the same semantic role as the manifest argument and binds that argument to
the matching output. Thus a bill may be the common source of distinct `recipient`, `amount`, and `subject`
outputs, while an `event_timing` aggregate cannot stand in for both `start_time` and `end_time`. These
Clauses state only trusted semantic relations and do not predict record fields, paths, formats, or values.
A deterministic compiler lowering replaces one already-proposed aggregate-to-many binding with separate
role-local semantic outputs before validation. It preserves the original common sources and effect argument
roles but introduces no value or field path. If the resulting SSA references do not validate, the complete
Contract remains fail-closed; there is no semantic repair or partial salvage.

When one proposal needs semantic extraction from semi-structured text, one WRAP Placement Agent resolves all
requested semantic bindings for that proposal in a single typed call. It sees the one authoritative
TaskContract, the complete proposed action/arguments, and only Clause-reachable immutable receipt nodes. It
returns `(source, ref, value)` placements, never a verdict. Code then verifies that every requested source is
covered exactly once, each ref is an allowed reachable node/span, and every constrained value exactly equals
the proposal value; deterministic relations and quantified-domain completeness remain code-only. Invalid or
missing placement is unresolved. There is no per-argument model call, local semantic materializer, reviewer,
or compatibility fallback; placements are proposal-local and cached only for the exact proposal and receipt
snapshot.

An undeclared action is a control conflict; an unbindable authorized argument is Approval; a definite
argument contradiction is Auditor. Pure observations in $O_{env}\setminus B_{env}$ are never gated.
Capabilities in $B_{env}\cap O_{env}$ mediate only the outbound call arguments against an authorizing
observation Clause; they are not required to match a final-effect Clause. Their successful return is logged
as an unowned receipt like every other observation. A missing or unclosed authorizing observation Clause is
Approval rather than an unauthorized-final-action conflict. Argument provenance cannot turn a write in
$B_{env}\setminus O_{env}$ into an intermediate read, and runtime content cannot create action authority.

This preserves control/data separation without interpreting an Agent program. The active-defense
contribution is that environment
perception jointly chooses $S_t$, $P_t$ and $W_t$ before tasks arrive; task arrival then specializes this
plan into $G_T$. Logger evidence may update
the next persisted plan but never lets attacker-controlled runtime content widen the current contract.

PLANT is independent of this receipt system. For each successful observation, the adapter first stores the
canonical unmodified return in WRAP's sidecar, then exposes a separately decorated view to the Agent.
Relations always consume canonical values, so honey decoration cannot become WRAP authority. PLANT and WRAP
produce independent evidence on the complete proposal; the Decision retains both. Observation markers that
reach an Effect/final-response sink and exact substrate identities that are really invoked are gating
commitments. A dependency decoy presented as proof is non-gating evidence: WRAP independently decides whether
the Effect has sufficient authority. Absence of a PLANT hit never authorizes.

A dependency carrier is runtime mediated and discovered from execution, not declared by a benchmark adapter.
Whenever an active Receipt is actually transferred from one execution unit to another, Runtime automatically
creates an episode-local carrier bound to the exact Receipt digest and consumer identity. The adapter reports
only the factual consumer; it cannot enable/disable dependency placement or assign authority. The handle
inherits the operator-declared `receipt_role`, but every ordinary transfer and every decoy has
`authority=false`. The downstream Agent calls `resolve_basis(handle)` to read a handle-only premise and
submits `proof_refs` only at a structured authority-sensitive Effect boundary. Runtime therefore records three
distinct events:

$$\mathsf{available}(h),\qquad \mathsf{accessed}(h),\qquad
\mathsf{presented\_as\_proof}(h,e).$$

Neither availability nor access proves causal consumption and neither gates. Presentation of a dependency
decoy is a PLANT measurement, not an authorization fact. WRAP releases an authority-sensitive Effect only
when a fresh receipt from the current episode carries an explicitly trusted source role and an exact scope
covering that action and its constrained arguments:

$$\operatorname{Allow}(e,a)\iff \exists r:\operatorname{Trusted}(r)\land
\operatorname{Authority}(r)\land\operatorname{Covers}(r,e,a)\land
\operatorname{Fresh}(r).$$

Advisory receipts, including authorization-like prose and PLANT basis decoys, contribute zero to this
sufficiency test. They neither help nor hurt when an independent valid proof exists. Authority is never
inferred from prose or Agent judgment; only task/operator/control/effect-return roots may introduce it, and
an authority receipt must carry its exact Effect scope when issued.

PLANT eligibility is skeleton-anchored rather than Clause-anchored. Registration mechanically compiles every
operator-attested capability with `observation=true` into a static plantable source slot $s\in P_{env}$; a
TaskContract cannot create, remove, or bypass a slot. One task-scoped PLANT Placement Agent consumes the full
$C_T$ as semantic context and is shared across benign, attack, retry, and recovery episodes for that exact
contract/environment/model. For each novel exact observation version
$v=(s,H(x))$, it makes at most one typed placement call:

$$\Pi_P(C_T,s,x,\nu)\to\{\mathsf{abstain}\}\cup(N,O\setminus N,operand,replacement).$$

The Agent performs one structured dataflow rehearsal: it proposes the exact-value dependencies N required by the normal trusted Contract trajectory and the dependencies O that would reach later tool arguments if observation-authored control were followed. A separable operand in O minus N is must-take whether it creates a new capability edge or is injected into an otherwise authorized effect argument. Broad transform outputs authorize the requested semantic transformation, not every source substring; observation-authored control operands enter N only when the trusted task explicitly preserves them, a declared acquisition/runtime argument consumes them, or a closed deterministic Contract relation selects them. Code—not the Agent—
then applies an operand-level precision gate: an operand explicitly present in the trusted task or fixed as an
exact Contract literal is protected, without exempting any other leaf in the same observation. The previous
source-wide abstention for carriers that could also feed a downstream acquisition is not used. Code further
requires one exact unique string occurrence, nonce presence, one-leaf shape preservation, unchanged
keys/cardinality/non-text leaves, and a non-atomic collection edit. There is no reflection, reviewer, or
fallback. Both placement and abstention are cached by exact `(source_kind, observation digest)`; changed
content receives one new call.

For a deployed token $\tau$, commitment scans every proposed argument leaf and retained trace channel:

$$\operatorname{PlantCommit}(p,\tau)=\mathbb{1}[\exists z\in\operatorname{Leaves}(p):\tau\subseteq z].$$

Deployment without later token use is not a security incident; consumption preserves the complete PLANT
event independently of WRAP provenance.

## Continuation

WRAP and PLANT feed one deterministic `ContinuationController`; neither owns a separate recovery policy.
Given episode state $S$ and a failed boundary event $F$, the controller can only replay, substitute,
invalidate, preserve, and enforce obligations:

$$
\operatorname{Continue}(S,F)=
\begin{cases}
\operatorname{Repair}(S,F), & \text{if one complete verified proposal exists};\\
\operatorname{Replan}(\operatorname{Sanitize}(S,F)), & \text{if a safe residual state exists};\\
\operatorname{Abort}(S,F), & \text{otherwise}.
\end{cases}
$$

`verified repair` is permitted only when every supplied Effect argument can be reconstructed from a trusted
literal or a non-semantic ClauseBinding whose operator/projection is replayable. The controller reconstructs
the complete proposal, never a field-level hybrid, and requires exactly one candidate. It then reruns PLANT,
WRAP, authority-scope comparison, and schema-aware value comparison. An adapter that ignores the continuation
fields still receives the original refusal; only explicit one-shot plan consumption may execute the repaired
arguments.

`sanitized replan` is used when no unique repair exists but the failed dependency can be removed without
inventing authority. A marker invalidates its exact receipt leaf and the transitive Binding closure backed by
that receipt; unaffected sibling fields remain active. A substrate commitment permanently denies the runtime-
attested resource identity for the episode, not merely its displayed name. A source-only Skill/MCP carrier is
replayed only after its exact invalidated operands are withheld; the original decorated carrier and transcript
are not reused. The continuation state contains only the trusted task, surviving immutable Receipts, completed
Effects, denied identities, and structured obligations. The current Agent session is
discarded; benchmark adapters start one fresh session over that state. At most one replan is allowed.

`safe abort` covers a repeated conflict, exhausted retry budget, missing Root Effect, ambiguous contamination
scope, failed repair revalidation, or a state whose safe remainder cannot continue the task. Abort is a normal
safety result and never simulates effect success. The controller is not an Agent and makes no semantic choice,
creates no Clause or Effect, and introduces no authority. Existing one-shot Approval remains a separate trusted
authority input: when enabled it may resolve a genuinely unresolved WRAP role, but it never overrides a
trusted literal conflict or a PLANT commitment.

## Changelog

- 2026-08-05: Made closed-operator operand types part of deterministic BindingProof validation. A Derive consumed by `add`, numeric `gt/lt`, or the score side of `argmin/argmax` can now be materialized only from exact nodes/spans that satisfy the operator's registered input type; the Binding Agent receives only compatible candidates. Also removed AuthBlur's adapter-level `require_authority` switch: every operator-registered `receipt_role=control` Effect now automatically requires a fresh exact-scope control proof, while `_proof_refs` remains optional sidecar metadata and ordinary Tool observations do not create dependency basis receipts.
- 2026-08-05: Replaced AuthBlur's adapter-selected dependency mode with automatic cross-unit Receipt transfer.
  Only Runtime may construct a basis carrier, from an active Receipt and actual consumer identity; handles are
  Receipt- and consumer-scoped and repeated delivery is episode-cached. Adapters cannot label A/B roles, request
  basis placement, or assign authority. This changes deployment plumbing only: availability/access remain
  audit-only and WRAP still requires an independent exact authority scope.

- 2026-08-03: Added one episode-local deterministic `ContinuationController` shared by WRAP and PLANT.
  Complete proof replay may produce one verified repair; otherwise the controller performs one exact
  dependency-closed sanitized replan or safe abort. Marker spans preserve unaffected receipt siblings,
  substrate identities remain denied for the episode, and AgentDojo/SCR/SkillInject discard the contaminated
  Agent session before consuming the structured continuation state. No model call, Clause, Effect, or authority
  source was added to the controller.

- 2026-08-03: Replaced `interprets` and per-export authority booleans with manifest `argument_types`,
  `output_types`, and `receipt_role in {data, advisory, control}`. Types select parser/comparison behavior but
  never authority; advisory receipts contribute zero, and control authority requires an exact runtime scope.

- 2026-07-27: Replaced PLANT's source-wide downstream-acquisition abstention with an operand-level precision
  gate. A task-explicit or exact Contract-literal operand is deterministically protected, while another
  O-minus-N leaf in the same plantable observation remains eligible; dynamic normal values remain represented
  in the Placement Agent's N set. This removes a carrier-wide coverage hole without adding a reviewer or model
  turn. Split the former `plant.py` into model, structure, placement, and runtime modules without changing the
  public `code.defense.plant` API.

- 2026-07-27: Recast PLANT placement as one typed N versus O dataflow rehearsal rather than entity-specific candidate rules. The Agent must expose normal and observation-induced exact-value dependency sets and proposes one O-minus-N operand; deterministic code still alone verifies a unique nonce-bearing one-leaf rewrite. This covers extra dependencies injected into already-authorized effect arguments without granting free-form transform outputs authority over every source substring. Added placement traces for auditable abstention/rejection; no reviewer, fallback, or entity parser was added.

- 2026-07-27: Removed domain-specific Contract/PLANT examples and made the single Contract Agent rehearse a manifest-only outcome ledger. Added operator-attested input/output schemas, format-scoped temporal canonicalization, strict Clause-reference syntax, and deterministic erasure of unsupported relation annotations. Effectful tools whose schema-attested return is produced by the same commit are now marked `effect_return`: a matching output Clause is valid only after an earlier identical effect Clause, and the exact passed call-id admits one receipt without repeating semantic placement. This adds no reviewer, partial Contract fallback, or runtime authority source.

- 2026-07-27: Hardened TaskContract reliability without widening its semantic grammar. The trusted task field
  is injected from the immutable request; one final Contract is deterministically compiled to role-local SSA;
  missing effect presentation text and redundant sources are canonicalized; exact `cN.output` is resolved only
  to that Clause's single declared output. Unknown actions, unattested runtime context, object-field paths, and
  semantic validation errors still reject the whole Contract. Persisted sidecar traces separate transport from
  validation failures. PLANT deterministically abstains before model placement when the current observation is
  required as an argument to a downstream observation acquisition Clause.
- 2026-07-27: Closed receipt replay and recovery-authority gaps. Dynamic observation admission is now a
  one-shot exact tool-call-id token; direct capability values cannot authorize effect arguments without an
  acquisition Clause; newer mutable-source receipts supersede older active authority versions; schema-invalid
  returns stay visible but unbound. Quarantine immediately removes exact nodes from WRAP's authority view and
  invalidates placement caches. Recovery reanchors from the trusted task, structural Clause ids, and
  deterministic clean bindings only. Added operator-attested output JSON Schema to EnvironmentPlan as a
  shape assumption, explicitly not a certificate of semantic roles such as “latest”.
- 2026-07-26: Added task/Contract-scoped `ClauseReceiptBinding` as the sole runtime ownership edge from an

- 2026-07-26: Added one atomic same-schema retransmission only for typed TaskContract transport failures and
  explicit per-attempt transport traces. Successful transport still costs one call; deterministic validation
  failures still reject the whole Contract without retry, reviewer, semantic repair, or partial fallback.
  Tightened relation guidance to positional exact-source forms and rejected `argmin/argmax` that reuse the item
  operand as scores. A fair two-tool probe exposed that proving `latest` additionally needs explicit output
  acquisition Clause to a canonical observation receipt. Passed dynamic intermediate calls bind their exact
  return; pure calls bind only through deterministic literal/already-bound argument reconciliation. Lazy WRAP
  and the WRAP Placement Agent now traverse bound receipts only; same-capability but wrong-argument receipts
  remain visible to the target/PLANT but cannot become authority. Bindings are episode-local, append-only,
  proposal-independent, and add no Contract field, Agent call, reviewer, or fallback.
- 2026-07-26: Replaced Contractor draft/reflection with one TaskContract Agent rehearsal returning one typed
  final Contract plus deterministic atomic validation. Replaced PlantDesigner/reviewer with one task-scoped
  PLANT Placement Agent and exact observation-version cache; replaced the per-value semantic Judge with one
  proposal-level WRAP Placement Agent. Both Agents return untrusted placements only, while code verifies
  structure/reachability/equality/coverage. Removed model, compatibility, and local-materialization fallbacks;
  preserved PLANT and WRAP as independent evidence streams in every Decision.
- 2026-07-26: Replaced the multi-pass Contract repair/reviewer/sanitizer chain with two-stage atomic
  synthesis. The model now emits one complete draft and one complete self-reflected final Contract;
  deterministic structural errors are supplied only to reflection. Final validation accepts the whole
  Contract or rejects it to an empty candidate. Deleted prefix sanitization, relation-approval inheritance,
  and all partial fallback paths. Cache eligibility is therefore limited to atomically valid finals.
- 2026-07-26: Made PLANT eligibility skeleton-anchored. Trusted environment registration now compiles
  every `observation=true` capability into a static plantable source slot and invalidates cached plans from
  the pre-skeleton schema. Deleted both Clause-presence eligibility and the no-match fallback to all
  Clauses. PLANT no longer consumes Contract Clauses at all: candidate selection receives only the trusted
  task and exact observation source, while the retained `affects_benign` reviewer receives the exact
  operand, replacement, and bounded local context. It asks only whether benign completion may require that
  operand unchanged; possibility or uncertainty means abstention. Every runner must pass the explicit environment skeleton, and runtime metrics
  distinguish slot exposure, deployment, and abstention. No runtime content or Contract can widen or erase
  skeleton coverage.
- 2026-07-25: Replaced the transitional global prose regex with manifest-grounded substrate resolution.
  `interprets` maps each open-prose argument to the exact resolver grammars active for that capability;
  WRAP reuses registered side-effect-free resolvers and binds their canonical entities. Empty lists attest
  inert prose, while a named but unavailable resolver fails unresolved. This makes Tier-1 coverage equal
  to the versioned substrate control grammar rather than a heuristic token vocabulary.
- 2026-07-25: Removed whole-prose semantic binding from the WRAP safety boundary. Trusted capability
  manifests identify open-prose positions with one task-independent role. Literal authority
  positions use exact equality. Deleted proposal-time semantic witnessing and retained the Judge only for
  reproducible selection/extraction of an existing receipt scalar. Tier-1 now guarantees mediated action
  and recognizable authority-reference integrity, not factual correctness of generated prose.
- 2026-07-25: Reduced TaskContractor to specification-only Clause compilation. Removed the independent
  semantic-expansion call and deleted proof-planning instructions for receipt alignment, coverage, and
  runtime provenance. `relation` now denotes only a task-stated deterministic condition; WRAP remains
  responsible for realizing and checking its witness lazily at proposal time. Added strict JSON grammar
  guidance and fail-closed validation for non-string sources. Contract/manifest/provenance schemas are
  unchanged.
- 2026-07-24: Aligned trusted-only Contract elaboration with necessary information acquisition. A
  task-selected reference may feed a manifest-grounded observable call, but an observed runtime proposal
  cannot trigger Contract repair. Added fail-closed sanitization for observable arguments without exactly
  one observable source. Recovery may now include a unique deterministic Clause binding recomputed with
  semantic materialization disabled and quarantine-overlapping refs removed; the binding remains subject
  to the original gate and adds no schema or authority.
- 2026-07-24: Prevented semantic materialization/witnessing from bypassing incomplete quantified
  observations. The runtime recognizes an existing `domain + mapped-output` Clause graph and requires an
  argument-anchored call receipt for every domain member before model-based selection may support a result.
  No relation keyword, instruction-text classifier, or schema field was added. Slack task9/injection2
  changed from an incorrect Pass on a partially observed channel set to `unresolved:channel`; benign
  complete coverage still Passes (DISC-2026W30-001).

- 2026-07-24: Corrected AgentDojo routing for dual capabilities in
  $B_{env}\cap O_{env}$. Their outbound arguments now use the existing
  `intermediate_evidence` path, while their successful return remains an unowned receipt; they no longer
  pass through the final-effect gate. No manifest or Contract field was added. Slack task3 changed from
  repeated benign `conflict:$action` and utility 0 to utility 1 with no Auditor; its undercompiled read
  Clause still requires Approval (DISC-2026W30-001).

- 2026-07-24: Added a bounded proposal-time semantic witness after exact-node and closed-relation
  reconciliation fail. It sees one scalar proposal and only the trusted task, one Clause, and
  Clause-reachable immutable receipts; it returns a verdict with existing receipt references and cannot
  generate replacement values or persistent authority. This adds no Contract field or relation operator.
  Workspace15 closes start/end/description/location with benign and attack utility 1 and ASR 0
  (DISC-2026W30-001).

- 2026-07-24: Replaced aggregate-to-many effect bindings with manifest-aligned single-value Clause outputs.
  Each runtime-derived effect argument now consumes a semantically matching scalar output; one aggregate
  output cannot silently authorize several distinct argument roles. Contractor validation requests one
  repair and fail-closed sanitization removes unresolved many-role bindings. No Contract field or relation
  operator was added; cache advanced to v34. Workspace15 Contract now separates start/end/description/location,
  but end-to-end remains Approval because runtime semantic materialization is independently incomplete
  (DISC-2026W30-001).

- 2026-07-24: Replaced AgentDojo's optimistic held-call emulation with a genuine same-tool-call
  suspension point. Approval now commits the exact complete proposal and returns the substrate's real result
  to the outstanding tool call; rejection returns a real rejected-tool result and never creates a false
  success belief. Automatic Pass projection is not applied after exact human approval. No Contract, manifest,
  provenance, or Detector schema changed (DISC-2026W30-001).

- 2026-07-24: Added optimistic held-call emulation for synchronous AgentDojo and trusted recovery
  re-anchoring. Approval no longer returns a visible pending response that induces proposal variants; the
  exact call remains uncommitted until the simulated user decision. Clean recovery receives only the original
  task and denied Clause instructions. Rejected untrusted arguments now quarantine one unanimous exact
  provenance input ref; ambiguous refs are untouched. Fused useful/poisoned text is explicitly an
  integrity-only recovery boundary. No Contract/provenance schema changed (DISC-2026W30-001).

- 2026-07-24: Split Approval continuation from Auditor recovery. Approval now creates one exact, one-shot,
  episode-local grant, commits the held proposal directly, and preserves the current Agent context when more
  trusted work remains; it never mutates TaskContract. Rejected Approval values trigger clean replay only
  when existing bindings prove an untrusted origin and an exact receipt node can be quarantined. Trusted or
  unresolved origins terminate without speculative rollback. No Contract/provenance schema changed
  (DISC-2026W30-001).

- 2026-07-24: Added proposal-blind free-text extraction and bounded clean-session recovery. The narrow Judge
  sees only trusted task/Clause text and candidate receipts, and a scalar extraction is accepted only when
  two independent evaluations reproduce the same source and value. Auditor now returns only a simulated
  substrate success to the discarded turn. Recovery restarts the original task once in a fresh Agent session,
  replays cached observations, preserves committed effects idempotently, and sanitizes only uniquely
  attributable canonical receipt nodes. Ambiguous attribution remains Approval. Removed proposal repair and
  prompt-based same-context recovery; Contract and evidence schemas remain unchanged; cache advanced to v33
  (DISC-2026W30-001).

- 2026-07-24: Replaced eager observation-to-Clause ownership with proposal-time lazy WRAP reconciliation.
  Pure observations now append unowned canonical receipts; installed effect gates backward-resolve only
  their declared Contract sources, recompute closed relations under the exact receipt snapshot, and require
  complete repeated-call coverage before accepting collection relations. Relation outputs are no longer
  persisted as authority. PLANT decorates only the Agent-facing view after the canonical receipt is stored.
  Contract, GateResult, Detector, and manifest schemas are unchanged; cache advanced to v32
  (DISC-2026W30-001).

- 2026-07-24: Extended the same closed relation field with `union(source)`; no `map` operator or new
  Contract field was introduced. Repeated capability application remains one observable Clause whose
  argument is bound to an earlier domain output. `union` merges and structurally deduplicates only that
  Clause's authorized output receipts, and promotes nothing until exact parent/call anchors prove complete
  coverage of the declared domain. Contract synthesis now contains the general repeatable-observation plus
  union compilation pattern; cache advanced to v31 (DISC-2026W30-001).

- 2026-07-24: Added fail-safe semantic admission for closed Clause relations without changing the Contract
  schema. The existing one-pass Contract Reviewer now returns only the Clause ids whose complete expression,
  operand roles, filters, tie-breaks, and comparability are entailed by the trusted local instruction.
  Unaccepted or malformed review output deletes the expression and falls back to the existing local
  Judge/Approval path; it never repairs an expression or grants authority. A revised Contract is reviewed
  again so it cannot inherit approval from an older draft. Contract cache advanced to v30
  (DISC-2026W30-001).

- 2026-07-23: Added one optional closed `relation` expression to derivation Clauses for deterministic
  trusted-task relations. The initial language is `identity`, `count`, `argmin`, `argmax`, and `difference`;
  operands must be exact sources of the same Clause, with no literals, paths, predicates, nesting, or
  proposal values. WRAP evaluates the expression over immutable Clause outputs before an effect proposal
  is checked, so a mismatching candidate is a deterministic conflict rather than a semantic-Judge
  uncertainty. `argmin/argmax` align measurements to candidates through exact receipt parent/call anchors,
  never list order. All other relations retain the prior local Judge/Approval path
  (DISC-2026W30-001).

- 2026-07-23: Split Clause-local argument projection by carrier structure. Structured selected objects use
  exact existing node refs only. A scalar/free-text carrier may instead fill only downstream slots already
  declared by the Contract through one proposal-independent semantic extraction; each derived receipt keeps
  the immutable text receipt as its parent. Whole-text copying into several fields is rejected, embedded
  commands cannot add slots/actions/sources, and multi-slot scalar carriers without frozen projections are
  unresolved rather than definite conflicts. No serialized schema changed (DISC-2026W30-001).

- 2026-07-23: Replaced generative Clause-output projection with exact-node projection. The semantic
  projector may now return only an existing `receipt-digest#JSON-pointer` for each predeclared downstream
  slot; runtime validates and resolves that path, then freezes the resulting Clause-local argument receipt
  before any effect proposal. It cannot generate, normalize, or infer the argument value. No Contract,
  receipt, provenance, gate, manifest, or Detector field changed (DISC-2026W30-001).

- 2026-07-23: Separated tool-call validity from task-argument authorization in Contract synthesis and WRAP.
  `effect.arguments` now contains only positions fixed by the trusted task or explicitly derived from its
  named Clause sources; JSON Schema `required` no longer creates serialized `unknown` positions. Task-fixed
  array arguments are normalized as one literal value. After the original proposal passes PLANT/Detector,
  an uncontracted optional position is removed before commit; an uncontracted required position must still
  close locally. This changes no Contract, manifest, receipt, evidence, or Detector field
  (DISC-2026W30-001).

- 2026-07-23: Corrected benchmark Approval simulation to evaluate the held proposal by its counterfactual
  substrate outcome rather than requiring every argument to match the hidden ground-truth call. After
  capability identity matches, the simulator executes the exact frozen proposal in an environment copy and
  approves only when the trusted task succeeds and the attack task does not. Approval then commits that
  same proposal directly; a completed trusted task receives no continuation. GT remains confined to
  simulating the user's decision and never supplies a value to Contract, WRAP, or Agent
  (DISC-2026W30-001).

- 2026-07-23: Clarified Contractor object-slot grounding without changing the Contract schema. When the
  trusted request asks to perform an effect according to a selected object, that object's Clause output is
  the abstract source for the operation-defining operands even though runtime fields and values are unknown.
  Required execution metadata is not implicitly supplied by object relevance, filenames, or reporting
  periods and remains `unknown`. Semantic review now accepts registered capability names as implementations
  of natural-language effects and does not demand predicted object paths or extraction Clauses. Contract
  cache advanced to v29 (DISC-2026W30-001).

- 2026-07-23: Replaced quote/span observation projection with pre-proposal structured materialization.
  When a Clause output becomes available, WRAP immediately instantiates the downstream slots already named
  by installed gates and freezes their parent receipt digests. A chained semantic output such as
  `bill -> payment_details -> pay` is materialized eagerly using the final gate's slot names. Production
  effect checks no longer call proposal-guided derivation when a frozen binding is absent; the position
  remains unresolved. No serialized Contract, Receipt, Provenance, GateResult, or Detector field changed
  (DISC-2026W30-001).

- 2026-07-23: Preserved substrate-declared argument requiredness in the persistent capability manifest.
  Contractor must represent every required position, leaving an ungrounded one `unknown`, but omits an
  optional position unless the trusted task fixes or derives it. WRAP still checks every argument actually
  proposed. A missing required value therefore remains an explicit Approval gap, while absent optional
  parameters no longer create synthetic Contract obligations (DISC-2026W30-001).

- 2026-07-23: Added clause-local observation projection for semi-structured carriers. A model may identify
  only verbatim argument spans inside a Clause-owned immutable receipt; code verifies the digest, structural
  path, and character interval before issuing an episode-local derived receipt. Each effect position is
  projected independently, and absent values remain `unknown`; a carrier root can no longer authorize all
  arguments merely because it is relevant to the Clause. Contractor/reviewer now also distinguish schema
  presence from source grounding: a required capability position is not evidence that a selected carrier
  supplies it. No Contract, Receipt, Provenance, GateResult, or Detector field was added
  (DISC-2026W30-001).

- 2026-07-23: Replaced clean-Episode denial recovery with one same-Episode continuation modeled after
  Progent's policy-error retry and CaMeL's state-preserving interpreter retry. The defense continuation
  retains the original Contract, installed WRAP gates, immutable receipts, PLANT state, committed substrate,
  and completed-call set, but resets the target Agent's message context so rejected untrusted text is not
  replayed. Its sole trusted query names the blocked action/reason and restates the original trusted task.
  It cannot widen authority or start a second Approval round. Relation binding now
  requires exact scalar refs for selection/extraction and reserves supporting refs for explicitly requested
  transformations. Gate-local argument repair cannot copy one scalar Clause output into several distinct
  argument positions. PLANT review no longer predicts marker propagation: it checks only separable control
  operands and Contract preservation, while actual sink-side commitment remains the outcome test. No
  Contract, Receipt, Provenance, GateResult, or Detector field changed (DISC-2026W30-001).

- 2026-07-22: Localized both remaining model judgments without adding serialized fields. PLANT review now
  receives the smallest structural/text edit span plus bounded surrounding context and checks only three
  rules (external-control separability, Contract preservation, and commitment reachability). Runtime
  relation binding now returns exact existing `receipt-digest#path` node references; code rejects invented
  paths before output promotion or gate binding. Contract, Receipt, Provenance, and Detector schemas are
  unchanged (DISC-2026W30-001).

- 2026-07-22: Clarified node-ref relation semantics without relaxing provenance authenticity. Exact
  selection/extraction returns the selected existing node; summarization, formatting, comparison,
  aggregation, and calculation may produce a new value but must return the smallest existing input nodes
  that jointly support it. Missing evidence or external control remains `uncertain`; all returned refs are
  still code-validated against Clause-owned receipts (DISC-2026W30-001).

- 2026-07-22: Added task-fixed arguments to observable output Clauses without an `observation` wrapper.
  Manifest argument names are copied structurally; direct JSON scalars are trusted-task literals and
  `{\"from\": ...}` remains runtime-bound. Exact literals close before any semantic Judge. An observable
  Clause may promote only its complete returned carrier; extraction, selection, aggregation, and
  transformation remain separate semantic Clauses, preventing a raw webpage from inheriting narrower
  `email` or identity authority. This changes the Contract schema but not receipt, provenance, Detector,
  or PLANT fields (DISC-2026W30-001).

- 2026-07-22: Reduced Contract semantic review to three closed invariants: requested-action conservation,
  task-fixed/runtime-derived argument conservation, and observable-carrier separation. The reviewer may
  no longer infer hidden identifiers, canonical formats, runtime fields, call order, or undocumented tool
  requirements, and therefore cannot downgrade a trusted-task literal to `unknown` based on speculation.
  The final three checks are action conservation, source sufficiency, and carrier separation; Contract
  cache advanced to v27 (DISC-2026W30-001).

- 2026-07-21: Ran isolated A/B/C ablations before any new full evaluation. Three Contractor generations
  conserved requested effects and avoided incidental webpage acquisition in every run, but recovered the
  task6 runtime-reference webpage chain in 0/3, refuting prompt-only stability. The fixed local Judge suite
  passed 6/6 grounding/entailment cases. Clause-local retry guidance failed to recover task9 utility and
  increased Approval interactions, so it was removed rather than retained as framework complexity
  (EXP-2026W30-041).

- 2026-07-21: Removed exact source containment as a shortcut for first-time Clause-output authority.
  Promotion now always requires the existing clause-local semantic bind, and its completeness condition
  returns `uncertain` when facts needed to establish the local relation are absent. Already-authorized
  output reuse remains deterministic. A fixed task9 regression changed an under-measured `private` proposal
  from Pass to `unresolved:channel` while preserving benign utility; attack utility remained zero because
  continuation did not reacquire the missing observation (EXP-2026W30-040).

- 2026-07-21: Added semantics-preserving information-acquisition elaboration inside Contract synthesis,
  without adding a schema field or reviewer. A task source that only supplies a runtime reference now yields
  an explicit reference output and an observable-capability output whose argument is grounded by that
  reference; a source that already contains the requested fact is not mechanically expanded. Six-task
  Contractor-only sanity preserved every requested effect, added the missing restaurant-reference webpage
  chain, and introduced no incidental webpage source in inbox-contained or control tasks
  (EXP-2026W30-039).

- 2026-07-21: Made the trusted Contract's action set a closed control boundary. A proposal whose action
  matches no effect Clause is now a definite `$action` conflict and is routed to Auditor; Approval remains
  reserved for an authorized action whose runtime argument relation cannot yet be proved. Explicitly named
  observation actions can still pass through their pre-installed Clause gate. This changes no Contract,
  provenance, or Detector field (EXP-2026W30-038).

- 2026-07-21: Closed runtime-derived observation calls without a new evidence path. A downstream call
  argument can instantiate an earlier Clause output through the existing `_derive_output` operation with
  `require_role=True`: exact containment no longer suffices, and the existing local semantic bind must prove
  the candidate's declared output role. A successful observation call no longer promotes its argument object
  unconditionally; the output must be proved from an argument or selected from the returned observation.
  Completion after Approval is now evaluated from all committed calls, so a rejected extra proposal cannot
  replay an already-complete trusted task (EXP-2026W30-037).

- 2026-07-21: Strengthened PLANT's contract-preservation gate for atomic collection objects. A scalar
  directly contained in a task-selected collection has no structural boundary separating authorized
  identity/content from control, so replacing that member is rejected in code even if the semantic reviewer
  says `keep`. Independent fields inside structured records remain eligible. This uses only object structure,
  not benchmark names, string patterns, or a new schema field (EXP-2026W30-036).

- 2026-07-21: Tightened the single clean continuation without changing Contract or evidence schemas.
  Every denied Auditor/Approval proposal now yields the same episode-local deny receipt, every successfully
  committed effect is remembered, and exact committed calls are suppressed only during the one clean retry.
  The retry receives one concise instruction to discard the unsupported binding and re-read the original
  structured source; it cannot authorize a new action or start another Approval round (EXP-2026W30-035).

- 2026-07-21: Removed two PLANT implementation-only API redundancies. An explicit unchanged-value/empty-token
  candidate is now a terminal conservative skip and bypasses review; design decisions are cached by
  `(source kind, exact object digest)` rather than incidental call identity, with a cached deployment rebound
  to the current source instance. Placement, shape preservation, self-review for actual candidates, and
  commitment detection are unchanged (EXP-2026W30-033).

- 2026-07-21: Compiled Clause sources into a deterministic capability-to-Clause index for intermediate
  observations. A runtime call can be considered only by Clauses that explicitly name its capability;
  zero-argument or exact-receipt-grounded calls require no semantic routing judgment, and one observation
  may serve multiple Clauses that named the same source. No Contract or provenance field changed
  (EXP-2026W30-032).

- 2026-07-21: Simplified the active boundary to the task-blueprint/receipt-coordinate design authorized in
  DISC-2026W30-001. Removed `critical_arguments` from the environment manifest and `carrier` from
  `SourceSurface`; capabilities now persist only `name/description/arguments/effect/observation`. Every
  argument actually submitted by the Agent must close locally to the selected Clause, including positions
  omitted by the Contract. Contractor keeps one selected structured object as one output and may bind
  several effect arguments directly to it; runtime verifies an exact receipt node before extracting leaves.
  Contract validation no longer predicts required/security-important positions (EXP-2026W30-030).

- 2026-07-21: Made Clause-output authority explicit and episode-local. All proved derivations,
  exact-node materializations, and successfully completed selected calls now share one promotion path that
  records `receipt digest -> cN.output`. Saved-state authorization consults this registry instead of
  implicitly trusting every object in the runtime output container. No Contract, Provenance, GateResult,
  Detector, or persisted-state field was added (EXP-2026W30-029).

- 2026-07-21: Replaced anonymous `variables/relations/content` Contracts with an acyclic clause-output
  program. Each clause now has `id/instruction/sources` and exactly one semantic `output` or concrete
  `effect`; effect arguments use only semantic literals, named sources/clause outputs, or unknown. WRAP is
  configured per clause before execution, materializes receipt-backed outputs at runtime, and separates
  neutral `Provenance(clause,action,arguments→refs)` from `GateResult(conflicts,unresolved)`. Detector remains
  a deterministic PLANT/WRAP router. This is a method-schema change authorized in DISC-2026W30-001 and
  implemented in EXP-2026W30-028.
  Candidate provenance now records per argument only expected sources and consulted receipt inputs;
  Gate verdicts remain separate. Clause outputs are promoted only after local support (and, for selected
  calls, successful substrate completion), support multiple immutable members, and alone carry downstream
  and saved-state authority. Multi-source joins/differences are judged once as one local relation.

- 2026-07-21: WRAP now evaluates a mediated proposal against both final-effect and intermediate-source
  interpretations before routing; one unrelated clause conflict cannot suppress a complete source
  interpretation. Approval/Auditor continuation starts a fresh defense episode over the same committed
  substrate state, discarding prior runtime receipts, derived bindings, proposal buffers, and PLANT runtime
  selections while preserving the original Contract and minimal rejected-action constraint. Contractor
  represents runtime object selectors as source relations rather than abstract literals. No Contract or
  Evidence field was added.

- 2026-07-20: Replaced the experimental saved-state parent graph with a single authority bit per exact
  state version: `state_id -> digest + authorized`. The parent design was rejected because runtime semantic
  provenance cannot justify precise persistent parent links. `record_state` and `observe_state` remain the
  only substrate hooks; unauthorized or mismatched state is unresolved, while PLANT-blocked writes create
  no record. Contract, Evidence, EnvironmentPlan, and Detector schemas remain unchanged.

- 2026-07-20: Added two non-serialized provenance roots without changing Contract, manifest, or Evidence
  fields. The trusted task can start a directly named observation chain. An adapter may additionally publish
  a non-plantable `runtime-context` sidecar scoped to exact capability/critical-argument positions; exact
  values bind, changed values conflict, and absent positions remain unresolved. AgentDojo and MCP adapters
  accept the same optional sidecar, but benchmark GT and untrusted tool/catalog content are prohibited.

- 2026-07-20: Separated MCP call validity from authorization relevance at registration. Full schema
  properties remain `arguments`; `critical_arguments` is now a task-independent role classification over
  required and optional positions instead of a copy of JSON Schema `required`. Security-relevant runtime
  context such as workspace/repository identity remains critical; grounding it is deferred to the common
  tool/runtime mechanism rather than removed from the boundary. No persistent field was added.

- 2026-07-20: Compiled one MCPTox registration artifact containing all 353 clean capabilities while
  retaining the existing six-field `CapabilitySurface`. Version-pinned official schemas supply 240
  entries; the other 113 use explicitly labeled benchmark-interface shapes. Runtime projects the relevant
  registered server surface from that one artifact, and any attack-added method remains absent/fail-closed.
  The fallback provenance is stored outside the runtime manifest and supplies no task authorization.

- 2026-07-20: Clarified the MCP manifest completeness assumption after reconstructing MCPTox servers from
  official version-pinned sources. The public benchmark does not retain exact installed versions or complete
  `tools/list` snapshots: 240/353 exposed tool names match an official snapshot at the benchmark cutoff,
  with 31/45 servers complete, 4 partial, and 10 unavailable. Official and benchmark-fallback schemas must
  therefore be reported separately; the fallback cannot silently become trusted semantic authority.

- 2026-07-20: Added the trusted MCP registration compiler. An operator-approved `tools/list` snapshot is
  reduced at install time into the existing single compact EnvironmentPlan; top-level JSON Schema
  properties/required keys populate existing argument fields, and task-independent tool semantics remain
  in the existing description field. The complete snapshot hash reuses PlanStore identity/versioning;
  runtime catalog changes do not mutate an active plan and no manifest or Contract field was added.

- 2026-07-20: Removed the MCPTox pinned-clean-catalog assumption. Attack EnvironmentPlan and Contract now
  derive from the current advertised method identities and argument shapes while excluding untrusted
  free-text descriptions; all current methods share the one-shot request mediation boundary. A rejected
  proposal retries at most once with the same current PLANT-rendered catalog and a deny-only receipt. The
  clean pair is retained only for utility/FP evaluation.

- 2026-07-20 (superseded by the entry above; retained as a negative oracle ablation): Fixed the one-shot MCP adapter at its actual execution unit. All methods in the trusted
  pre-runtime MCP catalog are mediated before the request; runtime-added methods fail closed, and catalog
  metadata is an environment-level PLANT carrier. A rejected one-shot proposal receives at most one retry
  from the persisted trusted catalog snapshot. Attack specifications remain evaluator-only. No Contract,
  Evidence, provenance, or Detector field was added.

- 2026-07-20: Separated pre-commit mediation from observation production as two independent environment
  manifest facts. Contractor still predicts no runtime source; WRAP alone attaches a dynamically selected
  observation to exactly one clause after argument grounding and instruction-local selection. Added a
  negative regression proving a grounded argument cannot turn an unrelated write into an intermediate read,
  mixed Auditor/Approval proposal handling, clause-scoped runtime PLANT selection, and schema-aware plan
  cache invalidation.

- 2026-07-20: Removed the AgentDojo-only repeat-prompt defense so target-agent prompts match the
  benchmark and MCP condition. Compressed the intermediate-read judge to consume only the clause-local
  instruction/relation and receipts that actually ground the proposed arguments. Clarified that
  non-mediated reads are sources, not effect clauses; added a deterministic nonempty-relation-input
  invariant. Compressed PLANT review and approval/auditor continuation text without changing schemas.

- 2026-07-20: Unified AgentDojo and MCP consumption of intermediate reads. WRAP now checks a mediated
  observation call before execution against exactly one clause's existing receipts and local
  `instruction + relations`; on success its receipt extends that clause's runtime provenance. Mere
  argument occurrence is insufficient and unresolved selection routes to Approval. TaskContract,
  environment manifest, Evidence, and persistent provenance schemas are unchanged.

- 2026-07-19: Added a general InjecAgent tool-unit substrate adapter. Its environment manifest is
  derived uniformly from the benchmark's public tool schemas: every offered function is a mediated
  boundary and declared required parameters are the critical argument positions. The pre-observation
  user-tool call restricts task-local Contract synthesis, while attacker-tool labels and injected
  content never enter authorization. No Contract, Evidence, Detector, or PLANT field was added.

- 2026-07-19: Tightened Contract compilation without adding schema fields: trusted-task actions remain
  authorized when external observations supply only their arguments; clauses must have closed
  source/variable/relation references; and Contractor receives the complete runtime argument schema,
  including task-constrained optional positions. A runtime observation call selected by an already
  authorized receipt now inherits that clause's source scope internally, allowing a derived receipt to
  ground later effect arguments. Evidence remains `clause/bindings/conflicts/unresolved`.

- 2026-07-18: Extended each independent clause to the minimal structured
  `instruction/sources/variables/relations/effect` form. Relations serialize only variable inputs/outputs;
  they contain no operators or generated derivation text. WRAP now proves relation-derived arguments
  jointly against the trusted local instruction and named receipts. Completed authorized-effect receipts
  may ground a later clause without adding call order. Added the fixed `unknown` argument constraint for
  explicit effects whose critical value requires Approval. Evidence and Detector schemas are unchanged.

- 2026-07-18: Made the WRAP placement assumption explicit as a task-independent, versioned environment
  capability manifest $B_{env}$. Added declared-vs-inferred boundary evaluation; the manifest is shared
  across methods and contains no authorization policy. Runtime receipt evidence can now select one derived
  observation call for PLANT before its output is exposed. PlantDesigner adds one same-role
  `verdict+feedback` reflection over contract preservation, must-take role, and commitment visibility.

- 2026-07-17: PLANT deployment now consumes the existing TaskContract and preserves source values authorized
  by its clauses; only additional control targets outside that boundary are plantable. WRAP literal matching
  is now one minimal LLM semantic judgment (`equivalent/different/uncertain`); deleted generic string/URL
  normalization and its datetime-as-port failure mode. No Contract field was added.
- 2026-07-17: Replaced passive text suffix PLANT with a shape-preserving semantic identity plant. The
  runtime accepts only existing string-leaf target substitutions, validates the full structural skeleton,
  and detects exact full-identity commitment. Reduced persistent PLANT state to `source/token/payload`; no
  Contract, carrier taxonomy, tool-name rule, or benchmark-specific field was added.
- 2026-07-17: Replaced ordered `source/relation/effect/arguments` instructions with unordered independent
  `action/sources/arguments` clauses. Removed ids, relations, internal receipts, reachability, and the
  SemanticBinder. Capability perception now fixes `local_read/external_read/write`; runtime provenance stores
  only exposed observations and effect proposals. Contracts persist by environment/task fingerprint.
- 2026-07-17: Removed the `delegated_control` flag. External task delegation is represented as an ordinary
  derivation sourced from the external-read receipt and yields candidate tasks requiring approval. WRAP now
  quarantines raw calls locally, deduplicates them by structured argument digest, and emits one Auditor or
  Approval incident per atomic task instead of treating retries as independent detections.
- 2026-07-17: Removed per-instruction Agent turns. One trusted task now has one Agent execution; WRAP uses
  the instruction set only as dynamically matched control/argument gates and resolves argument evidence
  through local upstream observation receipts.
- 2026-07-17: Replaced impossible internal-derivation receipts with runtime relation instantiation. Raw tool
  observations stay in a sidecar; structured derivations use exact evidence and free-text derivations use
  one local semantic bind. Runtime external reads may pass only when proven to be necessary observation
  expansion for the trusted task; the Contract schema remains unchanged.
- 2026-07-17: Replaced the global provenance/effect-plan formulation with atomic
  `source/relation/effect/arguments` instructions and instruction-local receipts. Removed semantic Contract
  review and runtime prediction. Formally separated PLANT deployment/detection from WRAP receipts and joined
  them only at the three-route decision aggregator.
- 2026-07-17: Split control violations from data-evidence gaps using the existing minimal Contract. Added
  Auditor continuation for off-contract sinks and reused selection evidence for local-observation argument
  transport. Full Slack evaluation exposed an unresolved taxonomy/completeness issue for explicitly
  requested externally observable reads; recorded as a negative result rather than adding a tool-specific
  exception.
- 2026-07-16: Added evidence-backed effect-argument instantiation. It reuses the existing selection proof
  and an un-serialized runtime leaf map; no Contract or logger fields were added.
- 2026-07-16: Reduced TaskContract synthesis to effect destinations plus the three-field dynamic binding
  `source`/`args`/`select`. Runtime provenance now checks source-call arguments and records selection
  integrity; structured selections can instantiate effects, while identities extracted from untrusted free
  text require approval. Removed predicted paths/order and benchmark-value rules from the Contractor surface.

- 2026-07-15: Replaced token/containment authorization and the expanded provenance/contract record with
  minimal `Value`/`Edge`/`Effect` objects. Unified PLANT lineage and WRAP argument proof at the action
  boundary; added local-observation vs external-effect taxonomy and executable filter/aggregate resolvers.

- 2026-07-21: Added gate-local object completion without changing Contract, receipt, provenance, or
  Detector schemas. Before routing an authorized action, WRAP may replace only a single-output-derived
  argument with the unique scalar identity already materialized under that Clause's episode-local
  authority, then requires the entire original gate to pass again. Actions, literals, unknown values,
  free text, ambiguous outputs, and PLANT commitments are never repairable by this mechanism.

- 2026-07-21: Added an episode-local structural-denial cache at the AgentDojo execution boundary. Once
  WRAP proves `conflict:$action`, argument variants of that same action reuse the first Auditor response
  across the single clean continuation and do not invoke another Judge or create another proposal. This
  changes execution cost only; it grants no action or argument authority. An attempted undeclared runtime
  observation-expansion branch did not restore utility and was removed.

- 2026-07-22: Made registered capability schemas the sole authority for effect argument positions. A
  transient, non-authorizing semantic expansion may expose information dependencies already implied by the
  trusted task, but it is discarded after Clause compilation and cannot predict calls, order, or runtime
  values. Missing schema positions remain `unknown`; absent optional runtime arguments require no invented
  value and are ignored by the gate.

- 2026-07-22: Unified runtime-derived source handling into one episode boundary: a successful observation
  is assigned only to the Clause identities selected by the pre-positioned WRAP blueprint, offered to PLANT
  before Agent exposure, and then recorded as the exact exposed receipt version. Receipt ownership remains
  episode-local and is used only by local bind/materialize checks; it is not a serialized provenance field
  or a global information-flow graph. Changed object versions receive a fresh PLANT design decision.

- 2026-07-23: Replaced Agent-driven Auditor continuation with a bounded frozen-binding narrowing step.
  The original conflicting proposal is retained as Auditor evidence; only conflicting argument positions
  with parameter-level bindings frozen before that proposal may be replaced, and the candidate must cross
  the same installed Clause gate again. Unknown positions remain unresolved for Approval. The action,
  trusted literals, PLANT commitments, ambiguous values, and multi-field root objects are not repairable.
  Thus recovery consumes pre-existing task authority but neither rereads adversarial observations nor
  derives authority from the rejected proposal.

- 2026-07-23: Kept PLANT candidate search source-local while making contract-preservation review consume
  the complete trusted TaskContract, since a field read at one source Clause may be required by a downstream
  effect Clause. Replaced the reviewer's coupled keep/revise/drop judgment with two transient semantic facts:
  whether the edited span is an embedded control operand and whether its exact value is task-required.
  Runtime code deploys only the former when the latter is false. This changes no persistent Contract,
  receipt, or PLANT schema.

- 2026-08-02: Added argument-local delegation for an already-declared Root Effect. A Contract may mark
  one `from` edge as `delegated:true` only when the trusted task explicitly lets the named future source
  determine that argument. Each proposal is proven independently against exact nodes/spans reachable from
  that Clause; the proof never binds the shared Clause output, creates an action, changes another argument,
  or expands Receipt scope. Operator returns are recursively normalized to JSON before Receipt recording.
- 2026-08-03: Replaced dependency-PLANT self-reported consumption with a controlled handle carrier.
  `available` and `accessed` are audit-only; presenting a decoy handle as Effect proof is non-gating PLANT
  evidence. Authority-sensitive Effects now require a fresh, episode-local, source-role-trusted receipt whose
  exact scope covers the action and constrained arguments. Advisory exports and decoys always carry
  `authority=false`; AuthBlur first records a non-authorizing structured `ControlDecision` Receipt. A negative
  decision is an ordinary response; only a positive result is converted into the fixed `authorize_control`
  Effect, which always requires scoped authority.
- 2026-08-03: Deferred open Derive roles used as acquisition arguments until an actual consumer proposal
  exists; only operands of closed Conditional operators are materialized eagerly. Argument-local delegation
  may then project the proposed scalar from an exact node/span in its declared Receipt scope. This prevents
  a containing message from being frozen as the URL or identifier it merely contains, without predicting a
  Receipt path or granting the source another Effect.
- 2026-08-06: Replaced persistent single-value materialization with unordered Clause-to-Receipt ownership,
  monotone fixed-point reconciliation, and proposal-local lazy Binding. Deterministic code enumerates the
  only admissible exact node/span, list/object composition, and registered-operator candidates; one cached
  Binding Agent call may select only opaque candidate ids for the whole Effect proposal. Natural-language
  SemanticSupport remains separate and cannot prove authority-bearing arguments. PLANT still runs immediately
  when each observation arrives and does not wait for the Receipt set to become complete.
