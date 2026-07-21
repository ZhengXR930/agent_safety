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
indices, and a special free-text/content type are absent. The relation is the local map
$i_k:S_k\rightarrow o_k$ or $i_k:S_k\rightarrow A_k$ itself. Clause order records only acyclic data
dependencies, not a prescribed tool-call schedule.

Before emitting this program, Contract synthesis performs a semantics-preserving elaboration of the trusted
request's minimum information-acquisition dependencies. In particular, it distinguishes a carrier that
contains a requested fact from one that supplies a runtime reference to that fact. Only the latter produces
an explicit `selected reference -> observable capability -> requested information` chain. The capability
argument remains bound to the earlier output and is not predicted. Elaboration may expose an observation
dependency but cannot add a final effect, destination, identity, or scope; no extra Contract field is stored.

The Agent executes the trusted task once. Before execution, each clause instantiates one local WRAP gate at
the already-mediated environment capability boundary. Runtime may bind concrete receipts and materialize
clause outputs, but may only resolve or narrow these gates; it cannot add an action, source, or clause.
Runtime provenance records only observations actually exposed to the Agent, materialized clause outputs,
and proposed/executed effects:

$$r_o=(n_o,args_o,h(v_o)),\qquad p=(a,args).$$

The value $v_o$ remains in an execution sidecar. No Agent internal state or episode-wide flow graph is
reconstructed.

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
ground-truth, allowed argument, or task-flow information. When the substrate exposes a deeper server-side
commit boundary, that boundary replaces whole-call mediation. Inferred manifests are automation ablations,
not part of the core WRAP guarantee.

For MCP, the trusted manifest is compiled once at operator-approved server registration or installation,
after protocol initialization and capability discovery. The compiler may consume the complete advertised
`tools/list` JSON Schema, but persists only the compact `EnvironmentPlan` and its five
`CapabilitySurface` fields: `name`, `description`, `arguments`, `effect`, and `observation`.
`arguments` is the public call shape, not a ranking of security importance. The hash of the full
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
an authorization label. WRAP checks every argument the Agent actually submits. An omitted tool default is
left to the substrate; a submitted argument must match a task literal, runtime-context value, or receipt
within the selected Clause, even when the Contractor did not enumerate that position. The compiled result
is persisted with the environment version and is never regenerated inside an episode.

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
\operatorname{BindOK}(P(p),S_k)\land\operatorname{LocalDeriveOK}(P(p),i_k)\land
\neg\operatorname{Unknown}(A_k).
$$

The first promotion of a runtime value into a named Clause output additionally requires local semantic
entailment $\operatorname{Entails}(i_k,R_k,o_k)$ over only that Clause's named receipts. Exact containment
in a receipt proves grounding but not the Clause relation: a real channel is not thereby the least-active
channel. `supported` requires the supplied facts to be sufficient to establish the relation; a missing
source object, alternative, measurement, or intermediate result yields `uncertain`. After this one proof,
exact reuse of the authorized output is deterministic and invokes no further judge. No predicate/operator
field or task-specific relation executor is introduced.

`LiteralOK` is a task-grounded LLM judgment over `(trusted task, clause, expected, proposed)`, returning
only `equivalent`, `different`, or `uncertain`; it is not token equality or a collection of URL/date/name
normalizers. `different` routes to Auditor and `uncertain` to Approval. The clause cannot impose precision
absent from the trusted task.

`LocalDeriveOK` is scoped to one clause, one proposed output/argument, and only that clause's named receipts.
It returns `supported/conflict/uncertain` plus supporting receipt digests and no rationale. `conflict` routes
to Auditor; `uncertain` and `unknown` route to Approval. The Detector consumes only the gate verdict and an
independent PLANT commitment; it does not construct provenance or repeat semantic reasoning. A candidate
derivation becomes an immutable, downstream-consumable `cN.output` receipt only after its local gate returns
supported. A selected intermediate call remains pending until the substrate reports successful completion;
only then can its structured call arguments materialize the selected Clause output. Failed calls and
conflict/uncertain candidates never create output authority. Internally, promotion records only an
episode-local map from the promoted receipt digest to its exact `cN.output` scope. Merely appearing in an
observation or output container does not grant authority; this map is not serialized, added to provenance,
or carried across tasks.

A selected structured object remains one Clause output even when it supplies several final arguments. The
Contract may bind `recipient`, `amount`, and `subject` directly to `c0.bill` without predicting the returned
record's field names or inserting field-extraction Clauses. Runtime first asks the local judge to select an
exact existing node reference from the source receipt; code verifies that digest and structural path, then
each final argument closes to a leaf of that same immutable object. The judge cannot synthesize a record or
refer to a nonexistent node.

An undeclared write is held for Approval because no clause can prove its control authority; a definite
argument contradiction is Auditor. At runtime, only a capability in $B_{env}\cap O_{env}$ may satisfy a
named clause source: its call arguments must themselves be grounded in that clause's existing receipts, and
the local instruction must confirm the read is needed. A successful observation becomes a receipt available
to that clause. Argument provenance alone cannot turn a write in $B_{env}\setminus O_{env}$ into an
intermediate read, and runtime content cannot create action authority.

This preserves control/data separation without interpreting an Agent program. The active-defense
contribution is that environment
perception jointly chooses $S_t$, $P_t$ and $W_t$ before tasks arrive; task arrival then specializes this
plan into $G_T$. Logger evidence may update
the next persisted plan but never lets attacker-controlled runtime content widen the current contract.

PLANT is independent of this receipt system. Once an observation source is resolved, its deployer performs
`resolve -> plant -> expose -> record`; its detector fires only on marker commitment/outcome. Known sources are
planted before their first read, while runtime-derived sources are planted by a source-exposure hook before
their content is returned. WRAP can operate without PLANT and PLANT without WRAP; a final aggregator maps
either hard signal to Auditor, incomplete WRAP evidence to Approval, and otherwise to Pass.

For an observation $x$, the same task contract $C_T$, and fresh nonce $\nu$, the PLANT designer may return a shape-preserving rewrite
$(x',\tau)$. Deployment is accepted only when collection cardinality/order, keys, and all non-text leaves
are unchanged; task-authorized objects are preserved, while one or more existing text leaves may replace
an additional control target outside $C_T$ by a syntactically same-kind honey identity $\tau$ containing
$\nu$. No added record or field is allowed. The outcome signal is

$$\operatorname{PlantCommit}(a,\tau)=\mathbb{1}[\exists z\in\operatorname{Leaves}(args(a)):z=\tau],$$

so quoting or summarizing a sentence that merely contains $\tau$ is not a commitment.

## Changelog

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
