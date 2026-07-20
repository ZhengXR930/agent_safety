# Method · Perception-Guided PLANT–WRAP

## Minimal representation

Before any task exists, environment perception persists

$$D^{env}_t=(S_t,P_t,W_t),$$

where $S_t$ is the perceived capability/effect schema, $P_t$ is the PLANT placement, and $W_t$ is the
set of mediated capability boundaries. When a trusted task $T$ arrives, but before its execution, a
separate task contract $C_T=\operatorname{ContractSynthesis}(T,S_t)$ is generated once and persisted by
`schema version + environment fingerprint + trusted task fingerprint`. The contract is an unordered set
of independent authorization clauses

$$C_T=(T,\{c_k=(i_k,S_k,V_k,R_k,e_k)\}_{k=1}^m),\qquad e_k=(a_k,A_k),$$

where $i_k$ is one minimal instruction grounded only in trusted task $T$; $S_k$ contains perceived
observation carriers or receipts returned by independently authorized effects; $V_k$ contains clause-local
symbolic variables; $R_k\subseteq 2^{V_k}\times2^{V_k}$ records only relation input/output incidence; and
$e_k$ is one explicitly authorized mediated action with argument map $A_k$. An argument constraint is one
of `literal(v)`, `from(variable)`, `content`, or `unknown`. Relation operators, formulas, predicates,
runtime values, paths, and free-text derivations are not serialized: the relation semantics come only from
$i_k$. Clauses have no prescribed call order; an effect receipt can satisfy a later clause only after its
producer has independently passed its own clause.

The Agent executes the trusted task once. Runtime provenance records only observations actually exposed to
the Agent and proposed/executed effects:

$$r_o=(n_o,args_o,h(v_o)),\qquad p=(a,args).$$

The value $v_o$ remains in an execution sidecar. No Agent internal state or episode-wide flow graph is
reconstructed.

## Joint decision

WRAP assumes a trusted environment manifest $B_{env}$ naming complete tool/MCP entries whose invocation
may commit an externally visible effect. This manifest is fixed per environment version, contains no task,
attack, ground-truth, or allowed-argument information, and is shared across methods in evaluation. Entries
outside $B_{env}$ return observations; entries inside it are mediated before invocation and may return an
observation receipt after an allowed invocation. When the substrate exposes a deeper server-side commit
boundary, that boundary replaces whole-call mediation. An inferred $\hat B_{env}$ is an automation ablation,
not part of the core WRAP guarantee.

For a proposed write, WRAP allows it iff exactly one clause matches the action, trusted literals match,
direct variables bind to declared receipts, joint relation-derived arguments satisfy the trusted local
instruction, and no argument is unknown:

$$
\operatorname{AllowWrite}(p)=
\exists!c_k:\ a(p)=a_k\land \operatorname{LiteralOK}(p,A_k)\land
\operatorname{BindOK}(p,S_k,V_k)\land\operatorname{RelationOK}(p,i_k,R_k)\land
\neg\operatorname{Unknown}(A_k).
$$

`LiteralOK` is a task-grounded LLM judgment over `(trusted task, clause, expected, proposed)`, returning
only `equivalent`, `different`, or `uncertain`; it is not token equality or a collection of URL/date/name
normalizers. `different` routes to Auditor and `uncertain` to Approval. The clause cannot impose precision
absent from the trusted task.

`RelationOK` is one instruction-local joint judgment over only `(trusted instruction, action, proposed
relation arguments, relation input/output incidence, named receipts)`. It returns a fixed
`supported/conflict/uncertain` value per proposed argument and no rationale. Joint evaluation prevents
mixing fields from different records and covers trusted selection, formatting, aggregation, and arithmetic
without introducing an executable task program. `conflict` routes to Auditor, `uncertain` and `unknown`
route to Approval. Supported bindings record only `task` and receipt digests in the existing Evidence.

An undeclared write is always Auditor. An external read named directly by the trusted task is constrained by
its clause. Otherwise an external read may expand a source only after a source carrier declared by some
clause has actually been observed; runtime content still cannot create write authority.

This preserves control/data separation without interpreting an Agent program. The active-defense
contribution is that environment
perception jointly chooses $S_t$, $P_t$ and $W_t$ before tasks arrive; task arrival then specializes this
plan into $G_T$. Logger evidence may update
the next persisted plan but never lets attacker-controlled runtime content widen the current contract.

PLANT is independent of this receipt system. Once a source carrier is resolved, its deployer performs
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
