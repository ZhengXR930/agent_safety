"""Thin orchestration: bind -> resolve -> gate, with independent PLANT.

One Episode owns one RuntimeState.  Reads are bound to Acquire roles and used
to resolve Conditional outputs deterministically; effects are traced by WRAP
and, independently, screened by PLANT for commitment.  The engine holds no
budgets; it owns the task/observation-keyed PLANT proposal cache shared by its
Episodes.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import re

from code.defense.contract import (AcquireClause, ConditionalClause,
                                    DeriveClause, EffectClause)
from code.defense.continuation import (ABORT, REPAIR, REPLAN,
                                       ContinuationController)
from code.defense.receipt_binding import bind_acquire
from code.defense.plant import CALL, RESPONSE, CommitEvent, Plant
from code.defense.resolver import resolve_conditional, resolve_derive
from code.defense.memory import argument_values_equal
from code.defense.state import (QUERY_REF, SEMANTIC_REF, Receipt, RuntimeState,
                                UNRESOLVED, digest)
from code.defense.proof import (materialize_delegated_support,
                                     materialize_guard,
                                     materialize_intermediate_derive,
                                     materialize_support)
from code.defense.wrap import authority_atoms, check_effect


@dataclass(frozen=True)
class Decision:
    route: str  # pass | deny | approval | commitment | replan
    reason: str = ""
    refs: tuple = field(default_factory=tuple)
    # Gating commitment tokens: these witness an action and set the route.
    commitments: tuple = field(default_factory=tuple)
    # Every PLANT detection at this boundary, gating or not, so a report-only
    # propagation stays measurable without being counted as an action.
    detections: tuple = field(default_factory=tuple)
    # Present only for an exact, task-local one-shot approval flow.
    approval_id: str = ""
    approval: dict = field(default_factory=dict)
    # Safe-by-default compatibility: an adapter that ignores these fields still
    # sees the original refusal. Only continue_decision() may consume the plan.
    continuation_id: str = ""
    continuation: dict = field(default_factory=dict)
    authorized_arguments: dict = field(default_factory=dict)


@dataclass(frozen=True)
class AuthorityScope:
    """The exact Effect region covered by one trusted authority receipt."""
    action: str
    arguments: tuple[tuple[str, object], ...] = ()

    @classmethod
    def for_effect(cls, action: str, arguments=None):
        return cls(str(action), tuple(sorted(
            (str(name), value) for name, value in
            dict(arguments or {}).items())))

    def to_dict(self) -> dict:
        return {"action": self.action, "arguments": dict(self.arguments)}


@dataclass(frozen=True)
class BasisReceipt:
    """Runtime-issued premise with a conservative source role.

    Ordinary exports are ``authority=False``.  An authority receipt must name
    an exact Effect scope; it is never inferred from prose or from an Agent.
    """
    id: str
    source: str
    value: object
    receipt_role: str = "advisory"
    authority: bool = False
    scope: AuthorityScope | None = None
    decoy: bool = False
    # Present only for an automatically mediated cross-unit transfer. These
    # fields bind the opaque handle to the exact runtime fact and intended
    # consumer; they never grant authority.
    receipt_digest: str = ""
    consumer: str = ""


@dataclass(frozen=True)
class BasisAccessReceipt:
    """Runtime witness that one actor dereferenced one issued handle."""
    id: str
    basis_id: str
    actor: str


@dataclass(frozen=True)
class CarrierView:
    """Native carrier value plus defense-only basis sidecars."""
    value: object
    basis_receipts: tuple[BasisReceipt, ...] = ()
    proposal: dict = field(default_factory=dict)

    @property
    def artifact_ids(self) -> tuple[str, ...]:
        return tuple(dict.fromkeys(
            str(item.get("operand"))
            for item in self.proposal.get("placements", ())
            if isinstance(item, dict) and item.get("kind") == "artifact" and
            item.get("operand")))


@dataclass(frozen=True)
class EffectEnvelope:
    """Defense-only metadata carried beside an unchanged native payload."""
    payload: object
    proof_refs: tuple[str, ...] = ()


def _redact_marker(value, paths, operands):
    """Remove exact marked operands from selected JSON leaves only."""
    paths = frozenset(map(str, paths or ()))
    operands = tuple(str(item) for item in operands if isinstance(item, str) and item)

    def walk(node, path=""):
        if isinstance(node, dict):
            return {key: walk(child, path + "/" + str(key).replace(
                "~", "~0").replace("/", "~1"))
                    for key, child in node.items()}
        if isinstance(node, (list, tuple)):
            return [walk(child, path + "/" + str(index))
                    for index, child in enumerate(node)]
        if path in paths and isinstance(node, str):
            for operand in operands:
                node = node.replace(operand, "[invalidated]")
        return node

    return walk(value)


class Episode:
    """Run one trusted task under the lean defense.

    Optional agents handle only acquire disambiguation and semantic Derive or
    supporting-role grounding. Each is called at most once per genuinely
    ambiguous decision, and deterministic code owns all values and refs.
    """

    def __init__(self, contract, nonce: str, *, capabilities=None,
                 skills=None,
                 acquire_agent=None, derive_agent=None, support_agent=None,
                 guard_agent=None, intermediate_agent=None,
                 plant_agent=None, plant_cache=None, plant_surfaces=None,
                 approval_enabled: bool = True,
                 continuation_enabled: bool = True,
                 max_replans: int = 1):
        self.contract = contract
        self.nonce = str(nonce)
        self.state = RuntimeState()
        self.plant = Plant(contract, nonce, placement_agent=plant_agent,
                           cache=plant_cache, surfaces=plant_surfaces)
        self.capabilities = capabilities or {}
        self.skills = skills or {}
        self.acquire_agent = acquire_agent
        self.derive_agent = derive_agent
        self.support_agent = support_agent
        self.guard_agent = guard_agent
        self.intermediate_agent = intermediate_agent
        self.approval_enabled = bool(approval_enabled)
        self.continuation = (ContinuationController(
            contract, max_replans=max_replans)
            if continuation_enabled else None)
        self._plant_scopes: dict[str, dict] = {}
        self._acquire_cache: dict[tuple, object] = {}
        self._derive_attempts: set[tuple] = set()
        self._semantic_attempts: dict[tuple, tuple[str, ...] | None] = {}
        self._support_attempts: set[tuple] = set()
        self._intermediate_attempts: set[tuple] = set()
        self._delegated_attempts: dict[tuple, tuple[str, ...]] = {}
        self._basis_receipts: dict[str, BasisReceipt] = {}
        self._basis_accesses: dict[str, BasisAccessReceipt] = {}
        self._proof_presentations: list[dict] = []
        self._dependency_transfers: dict[tuple[str, str], CarrierView] = {}
        self._approval_requests: dict[str, dict] = {}
        self._approval_grants: set[str] = set()
        self._approval_denied: set[str] = set()
        self._approval_consumed: set[str] = set()

    # -- observation --------------------------------------------------------
    def record_receipt(self, capability: str, arguments: dict, value) -> Receipt:
        """Record one mediated runtime fact without exposing it as input.

        This is the boundary for structured Agent outputs such as a control
        decision.  Recording provenance never grants authority; an adapter must
        separately present a scoped authority receipt before an Effect.
        """
        surface = self.capabilities.get(str(capability))
        receipt = self.state.record(
            Receipt(str(capability), dict(arguments or {}), value,
                    bool(surface is not None and surface.committed_return),
                    getattr(surface, "receipt_role", "data")))
        self._reconcile()
        return receipt

    def observe(self, capability: str, arguments: dict, value, *,
                consumer: str | None = None, placement_schema=None,
                return_view: bool = False):
        """Record a read and expose it at its actual runtime boundary.

        ``consumer`` is an execution identity, not a semantic label. When a
        mediated Receipt crosses into another Tool/MCP/Skill/Agent unit, the
        Runtime automatically creates the dependency carrier. Adapters may
        report the real consumer but cannot opt a value into or out of the
        dependency plane.
        """
        receipt = self.record_receipt(str(capability), arguments, value)
        if consumer is not None:
            view = self.transfer(receipt, consumer, schema=placement_schema)
            return view if return_view else view.value
        if return_view:
            view = self.place_carrier(
                str(capability), value, modes=("marker",),
                schema=placement_schema)
            self._index_plant_scopes(str(capability), view.value, receipt)
            return view
        exposed = self.plant.decorate(str(capability), value)
        self._index_plant_scopes(str(capability), exposed, receipt)
        return exposed

    # -- substrate PLANT carriers ------------------------------------------
    def arm_substrate(self, carrier: str, sample) -> str:
        """Return the token a trusted control/state adapter must embed.

        The adapter owns the native artifact — a honey file or record, a
        permission entry, a test account, an authorization handle, or a decoy
        tool/resource — and only a real interaction with it commits.
        """
        decoy = self.plant.arm_substrate(carrier, sample)
        self._plant_scopes[decoy.token] = {
            "mechanism": decoy.mechanism,
            "source": decoy.source,
            "refs": (),
            "source_refs": ("source:" + decoy.source,),
            "identities": decoy.identities or (decoy.token,),
            "operand": decoy.element,
            "paths": (),
        }
        return decoy.token

    def place_substrate(self, carrier: str, state, *, schema=None) -> str | None:
        """Ask the shared placement role whether to arm a state/control slot.

        Registration establishes that the adapter can deploy and monitor the
        carrier.  The Agent proposes only whether this episode benefits from an
        artifact; deterministic code creates the token and the adapter embeds
        it in native state.
        """
        decoy = self.plant.place_substrate(str(carrier), state, schema=schema)
        if decoy is None:
            return None
        self._plant_scopes[decoy.token] = {
            "mechanism": decoy.mechanism,
            "source": decoy.source,
            "refs": (),
            "source_refs": ("source:" + decoy.source,),
            "identities": decoy.identities or (decoy.token,),
            "operand": decoy.element,
            "paths": (),
        }
        return decoy.token

    def expose(self, source: str, value):
        """Instrument registered non-tool model input without a Receipt.

        This is the seam for skill narrative and MCP resource content: material
        the agent reads that is not a Contract-bound acquisition.
        """
        exposed = self.plant.decorate(str(source), value)
        self._index_plant_scopes(str(source), exposed)
        return exposed

    def _index_plant_scopes(self, source: str, exposed,
                            receipt: Receipt | None = None) -> None:
        """Tie deployed identities to the exact runtime carrier that held them."""
        for row in self.plant.placements:
            if str(row.get("source")) != str(source):
                continue
            token = str(row.get("token", ""))
            decoy = self.plant.deployed.get(token)
            if decoy is None or not decoy.recognizes((), exposed):
                continue
            paths = tuple(map(str, row.get("occurrences", ()) or ()))
            refs = (() if receipt is None else tuple(
                receipt.digest + "#" + path for path in paths))
            previous = self._plant_scopes.get(token, {})
            self._plant_scopes[token] = {
                "mechanism": decoy.mechanism,
                "source": decoy.source,
                "refs": tuple(dict.fromkeys((*previous.get("refs", ()), *refs))),
                "source_refs": (() if receipt is not None else
                                ("source:" + decoy.source,)),
                "identities": decoy.identities or (decoy.token,),
                "operand": decoy.element,
                "paths": tuple(dict.fromkeys(
                    (*previous.get("paths", ()), *paths))),
            }

    def issue_basis(self, source: str, value, *, receipt_role: str | None = None,
                    authority: bool | None = None,
                    scope: AuthorityScope | None = None,
                    decoy: bool = False, receipt_digest: str = "",
                    consumer: str = "") -> BasisReceipt:
        """Issue one episode-local premise; only explicit trusted scope grants."""
        source = str(source)
        surface = self.capabilities.get(source)
        role = str(receipt_role or getattr(surface, "receipt_role", "advisory"))
        if role not in {"data", "advisory", "control"}:
            raise ValueError(f"unknown receipt role {role!r}")
        authorized = (role == "control" if authority is None else bool(authority))
        if decoy and authorized:
            raise ValueError("a dependency decoy cannot carry authority")
        if authorized and role != "control":
            raise ValueError("untrusted source role cannot introduce authority")
        if authorized and not isinstance(scope, AuthorityScope):
            raise ValueError("authority basis requires an exact Effect scope")
        if decoy:
            basis_id = self.plant.arm_basis(source, value).token
        else:
            basis_id = "BASIS-" + digest({
                "nonce": self.nonce, "source": source, "value": value,
                "role": role, "authority": authorized,
                "scope": None if scope is None else scope.to_dict(),
            })[:16]
        receipt = BasisReceipt(
            basis_id, source, value, role, authorized, scope, bool(decoy),
            str(receipt_digest), str(consumer))
        self._basis_receipts[basis_id] = receipt
        return receipt

    def resolve_basis(self, basis_id: str, *, actor: str) -> object:
        """Return a premise through the controlled carrier and attest access."""
        basis_id, actor = str(basis_id), str(actor)
        receipt = self._basis_receipts.get(basis_id)
        if receipt is None:
            raise ValueError("unknown basis handle")
        if receipt.consumer and receipt.consumer != actor:
            raise ValueError("basis handle is scoped to another consumer")
        access_id = "ACCESS-" + digest({
            "nonce": self.nonce, "basis": basis_id, "actor": actor,
        })[:16]
        self._basis_accesses.setdefault(
            access_id, BasisAccessReceipt(access_id, basis_id, actor))
        return receipt.value

    def place_carrier(self, source: str, value, *, modes=("marker",),
                      schema=None, surface_cards=()) -> CarrierView:
        """Place on a carrier that is not a cross-unit Receipt flow.

        Dependency placement is deliberately unavailable here: it is created
        only by :meth:`transfer`, after Runtime observes an actual producer to
        consumer flow.
        """
        modes = tuple(dict.fromkeys(map(str, modes or ())))
        if "basis" in modes:
            raise ValueError("dependency basis requires transfer(receipt, consumer)")
        return self._place_carrier(
            str(source), value, modes=modes, schema=schema,
            surface_cards=surface_cards)

    def _place_carrier(self, source: str, value, *, modes,
                       schema=None, surface_cards=(),
                       receipt: Receipt | None = None,
                       consumer: str = "") -> CarrierView:
        """Shared placement primitive; only ``transfer`` may request basis."""
        self.plant.exposed += 1
        modes = tuple(dict.fromkeys(map(str, modes or ())))
        proposal = self.plant.propose(
            str(source), value, modes=modes, schema=schema,
            surface_cards=surface_cards)
        placements = proposal.get("placements", ())
        placed, _marker_count = self.plant.apply_markers(
            str(source), value,
            (item for item in placements if item.get("kind") == "marker"))
        receipts = ()
        if "basis" in modes:
            if receipt is None or not consumer:
                raise ValueError("dependency basis requires an exact Receipt flow")
            # Cross-unit data never acquires authority merely by being passed.
            # Both real and decoy handles retain the Receipt role and audience.
            real = self.issue_basis(
                str(source), placed, receipt_role=receipt.receipt_role,
                authority=False, receipt_digest=receipt.digest,
                consumer=consumer)
            receipts = (real,)
            basis = next((item for item in placements
                          if item.get("kind") == "basis"), None)
            if basis is not None:
                decoy = self.issue_basis(
                    str(source), basis.get("basis_value", ""),
                    receipt_role=receipt.receipt_role, authority=False,
                    decoy=True, receipt_digest=receipt.digest,
                    consumer=consumer)
                receipts += (decoy,)
        view = CarrierView(placed, receipts, dict(proposal))
        self._index_plant_scopes(str(source), view.value)
        return view

    def transfer(self, receipt: Receipt, consumer: str, *, schema=None,
                 surface_cards=()) -> CarrierView:
        """Expose one recorded Receipt to another execution unit.

        This is the sole dependency-carrier constructor. The decision is
        structural: an active Receipt is crossing to a named consumer. It
        does not depend on benchmark roles, task semantics, or attack labels.
        Repeated delivery of the same fact to the same consumer reuses the
        episode-local carrier and therefore causes no additional Agent call.
        """
        if not any(item is receipt for item in self.state.receipts):
            raise ValueError("dependency transfer requires an active Receipt")
        consumer = str(consumer).strip()
        if not consumer:
            raise ValueError("dependency transfer requires a consumer identity")
        key = (receipt.digest, consumer)
        if key not in self._dependency_transfers:
            surface = self.capabilities.get(receipt.capability)
            inferred_schema = (schema if schema is not None else
                               getattr(surface, "output_schema", None))
            self._dependency_transfers[key] = self._place_carrier(
                receipt.capability, receipt.value,
                modes=("marker", "basis"), schema=inferred_schema,
                surface_cards=surface_cards, receipt=receipt,
                consumer=consumer)
        view = self._dependency_transfers[key]
        self._index_plant_scopes(receipt.capability, view.value, receipt)
        return view

    @staticmethod
    def envelope(payload, proof_refs=()) -> EffectEnvelope:
        """Build defense metadata without modifying the native payload."""
        refs = tuple(
            item.id if isinstance(item, BasisReceipt) else str(item)
            for item in (proof_refs or ()))
        return EffectEnvelope(payload, tuple(dict.fromkeys(refs)))

    def commit(self, channel: str, actor: str, value, *, proof_refs=(),
               identities=()) -> Decision:
        """Report one observable boundary and run all three PLANT sensors.

        ``channel`` is ``call``, ``response``, ``state`` or ``artifact`` — the
        boundary, which fixes the evidence semantics.  A certified observation
        identity in either an effect argument or the final response routes to
        ``commitment``; the former is ``effectful`` and the latter ``copied``.
        A really-invoked artifact gates. Dependency proof presentation is
        recorded but never authorizes or blocks by itself.

        Every adapter — tool, MCP or skill — reports its boundaries here.
        """
        envelope = (value if isinstance(value, EffectEnvelope)
                    else self.envelope(value, proof_refs))
        selected = frozenset(map(str, (*tuple(identities or ()), actor)))
        if (self.continuation is not None and
                selected & self.continuation.denied_resources):
            return Decision("deny", "continuation-denied-resource",
                            refs=tuple(sorted(
                                selected & self.continuation.denied_resources)))
        unknown = tuple(ref for ref in envelope.proof_refs
                        if ref not in self._basis_receipts)
        if unknown:
            return Decision("deny", "unknown-basis-ref:" + unknown[0],
                            refs=unknown)
        if envelope.proof_refs:
            self._proof_presentations.append({
                "actor": str(actor), "boundary": str(channel),
                "proof_refs": list(envelope.proof_refs),
            })
        events = self.plant.commit(CommitEvent(
            str(channel), str(actor), envelope.payload, envelope.proof_refs,
            tuple(identities or ())))
        detections = tuple(event.to_dict() for event in events)
        gating = tuple(event for event in events if event.gating)
        if gating:
            decision = Decision(
                "commitment", "PLANT commitment",
                refs=tuple(event.semantics for event in gating),
                commitments=tuple(event.token for event in gating),
                detections=detections)
            if self.continuation is None:
                return decision
            arguments = (dict(envelope.payload)
                         if isinstance(envelope.payload, dict)
                         else {"value": envelope.payload})
            plan = self.continuation.propose(
                self.state, action=str(actor), arguments=arguments,
                reason=decision.reason, refs=decision.refs,
                events=tuple(event.to_dict() for event in gating),
                plant_scopes=self._plant_scopes,
                proof_refs=envelope.proof_refs)
            return self._with_continuation(decision, plan)
        return Decision("pass", "clean commitment channel",
                        detections=detections)

    @staticmethod
    def _with_continuation(decision: Decision, plan, *, context=None,
                           authorized_arguments=None) -> Decision:
        value = plan.to_dict()
        if context is not None:
            value["state"] = context
        return Decision(
            decision.route, decision.reason, decision.refs,
            decision.commitments, decision.detections,
            decision.approval_id, dict(decision.approval),
            plan.id, value, dict(authorized_arguments or {}))

    def _resolve_acquire_once(self, **request):
        """Cache one semantic choice for an identical observation mapping."""
        key = (str(request.get("capability", "")),
               digest(request.get("arguments", {})),
               tuple(request.get("candidates", ())))
        if key not in self._acquire_cache:
            self._acquire_cache[key] = self.acquire_agent(**request)
        return self._acquire_cache[key]

    def _resolve_conditionals(self) -> None:
        pending = True
        while pending:
            pending = False
            for clause in self.contract.clauses:
                if (isinstance(clause, ConditionalClause) and
                        clause.id not in self.state.bindings and
                        resolve_conditional(self.state, clause) is not None):
                    pending = True

    def _reconcile(self, *, materialize: bool = False) -> None:
        """Monotonically close ClauseBindings against all current Receipts."""
        clauses_by_ref = {
            clause.output_ref: clause for clause in self.contract.clauses
            if clause.output_ref
        }
        # Only closed operators need an upstream Derive before a concrete
        # consumer exists.  Acquisition arguments are instead grounded from
        # the call that actually occurs below.  Eagerly materializing them
        # from an observation can collapse a semantic field (for example one
        # URL) into its containing message and poison every later proof.
        intermediate_refs = set()
        for clause in self.contract.clauses:
            if isinstance(clause, ConditionalClause):
                intermediate_refs.update(clause.operand_refs)

        resolver = (self._resolve_acquire_once
                    if self.acquire_agent is not None else None)
        while True:
            before = len(self.state.bindings)

            # An actual consumer argument proposes the exact upstream role it
            # consumes. The semantic agent validates the declared Derive only;
            # provenance remains the inputs' existing refs.
            for receipt in self.state.receipts:
                for acquire in self.contract.clauses:
                    if (not isinstance(acquire, AcquireClause) or
                            acquire.capability != receipt.capability):
                        continue
                    for name, spec in acquire.call_arguments.items():
                        if (name not in receipt.arguments or
                                not isinstance(spec, dict) or
                                set(spec) != {"from"}):
                            continue
                        raw = spec["from"]
                        sources = ([raw] if isinstance(raw, str)
                                   else list(raw or ()))
                        if len(sources) != 1:
                            continue
                        source = str(sources[0])
                        target = clauses_by_ref.get(source)
                        if (not isinstance(target, DeriveClause) or
                                self.state.output(source) is not UNRESOLVED):
                            continue
                        proposed = receipt.arguments[name]
                        key = (target.id, digest(proposed),
                               tuple(r.digest for r in self.state.receipts))
                        if key in self._derive_attempts:
                            continue
                        self._derive_attempts.add(key)
                        resolve_derive(
                            self.state, target, proposed,
                            task=self.contract.task, ground=self.derive_agent)

            # A Receipt may predate the role used in its arguments. Retry every
            # still-unowned Receipt after newly proven bindings.
            for receipt in self.state.receipts:
                root = receipt.digest + "#"
                owned = any(
                    binding.kind == "acquire" and
                    any(str(ref).startswith(root) for ref in binding.refs)
                    for binding in self.state.bindings.values())
                if not owned:
                    bind_acquire(self.state, self.contract, receipt, resolver)

            self._resolve_conditionals()

            if materialize and self.intermediate_agent is not None:
                version = tuple(receipt.digest for receipt in self.state.receipts)
                for clause in self.contract.clauses:
                    if (not isinstance(clause, DeriveClause) or
                            clause.output_ref not in intermediate_refs or
                            clause.id in self.state.bindings):
                        continue
                    key = (clause.id, version)
                    if key in self._intermediate_attempts:
                        continue
                    ready = all(
                        ref in {"task", "runtime-context"} or
                        self.state.output(ref) is not UNRESOLVED
                        for ref in clause.input_refs)
                    if not ready:
                        continue
                    self._intermediate_attempts.add(key)
                    materialize_intermediate_derive(
                        self.state, self.contract, clause,
                        choose=self.intermediate_agent)
                self._resolve_conditionals()

            if len(self.state.bindings) == before:
                return

    def _resolve_effect_derives(self, action: str, arguments: dict) -> dict:
        """Ground stable Derives and return proposal-local task semantic proofs."""
        surface = self.capabilities.get(str(action))
        skill_context = [
            skill.to_dict() for skill in self.skills.values()
            if action in skill.tools]
        evidence = [{
            "id": "r" + str(index),
            "capability": receipt.capability,
            "arguments": receipt.arguments,
            "value": receipt.value,
        } for index, receipt in enumerate(self.state.receipts)]
        evidence_refs = {
            "r" + str(index): receipt.digest + "#"
            for index, receipt in enumerate(self.state.receipts)}

        clause_by_ref = {
            item.output_ref: item for item in self.contract.clauses
            if item.output_ref}

        def exact_task_value(value) -> bool:
            """Whether a scalar is an exact, bounded token of the task."""
            if not isinstance(value, str) or not value:
                return False
            return re.search(
                r"(?<![\w])" + re.escape(value) + r"(?![\w])",
                self.contract.task) is not None

        def schema_attests_empty(argument: str, value) -> bool:
            """Whether the Tool schema accepts this empty collection exactly.

            Empty argv/options collections carry no runtime-selected entity or
            authority.  When their complete Contract ancestry is the trusted
            task, requiring a semantic Agent to rediscover that fact adds only
            variance.  Non-empty collections and schemas with a positive lower
            bound continue through the ordinary Binding path.
            """
            if surface is None:
                return False
            schema = surface.argument_schema(argument)
            if not isinstance(schema, dict):
                return False
            if isinstance(value, list) and not value:
                declared = schema.get("type")
                minimum = schema.get("minItems", 0)
                return (declared == "array" and
                        type(minimum) is int and minimum == 0 and
                        ("enum" not in schema or value in schema["enum"]))
            if isinstance(value, dict) and not value:
                declared = schema.get("type")
                minimum = schema.get("minProperties", 0)
                return (declared == "object" and
                        type(minimum) is int and minimum == 0 and
                        not schema.get("required") and
                        ("enum" not in schema or value in schema["enum"]))
            return False

        def task_rooted(source: str, seen=frozenset()) -> bool:
            """Whether a role's complete authority ancestry is the task root.

            This is structural, not semantic: the Contract already fixed the
            Derive/Conditional path.  The Binding Agent may instantiate that
            declared role, but no Receipt or runtime text may enter the path.
            """
            if source == "task":
                return True
            if source in seen or source == "runtime-context":
                return False
            target = clause_by_ref.get(source)
            if isinstance(target, DeriveClause):
                return bool(target.input_refs) and all(
                    task_rooted(str(ref), seen | {source})
                    for ref in target.input_refs)
            if isinstance(target, ConditionalClause):
                return bool(target.operand_refs) and all(
                    task_rooted(str(ref), seen | {source})
                    for ref in target.operand_refs)
            return False

        def evidence_for(target: DeriveClause) -> list[dict]:
            """Only Receipts already reachable through this Derive's inputs."""
            roots = set()
            for input_ref in target.input_refs:
                binding = self.state.bindings.get(
                    str(input_ref).partition(".")[0])
                for ref in (() if binding is None else binding.refs):
                    if "#" in str(ref):
                        roots.add(str(ref).split("#", 1)[0] + "#")
            return [row for row in evidence
                    if evidence_refs[row["id"]] in roots]

        def ground_source(source: str, proposed, seen=frozenset()):
            if source in seen or self.state.output(source) is not UNRESOLVED:
                return
            target = clause_by_ref.get(source)
            if isinstance(target, DeriveClause):
                ready = all(
                    ref in {"task", "runtime-context"} or
                    self.state.output(ref) is not UNRESOLVED
                    for ref in target.input_refs)
                key = (target.id, digest(proposed),
                       tuple(r.digest for r in self.state.receipts))
                if ready and key not in self._derive_attempts:
                    self._derive_attempts.add(key)
                    resolve_derive(
                        self.state, target, proposed,
                        task=self.contract.task, ground=None)
                return
            if isinstance(target, ConditionalClause):
                inverse = None
                if target.operator == "identity" and len(target.operand_refs) == 1:
                    inverse = proposed
                elif (target.operator == "singleton" and
                      len(target.operand_refs) == 1 and
                      isinstance(proposed, (list, tuple)) and len(proposed) == 1):
                    inverse = proposed[0]
                if inverse is not None:
                    ground_source(target.operand_refs[0], inverse,
                                  seen | {source})
                    resolve_conditional(self.state, target)

        proofs = {}
        for clause in self.contract.clauses:
            if not (isinstance(clause, EffectClause) and clause.action == action):
                continue
            for name, spec in clause.effect_arguments.items():
                if not (isinstance(spec, dict) and set(spec) == {"from"} and
                        name in arguments):
                    continue
                sources = spec["from"]
                sources = ([sources] if isinstance(sources, str)
                           else list(sources or ()))
                for src in sources:
                    source = str(src)
                    target = clause_by_ref.get(source)
                    if (isinstance(target, DeriveClause) and
                            self.derive_agent is not None):
                        closed_inputs = [ref for ref in target.input_refs
                                         if ref not in {"task",
                                                        "runtime-context"}]
                        if target.quantified and len(closed_inputs) == 1:
                            parent_ref = closed_inputs[0]
                            parent = clause_by_ref.get(parent_ref)
                            collection = self.state.output(parent_ref)
                            if (isinstance(parent, ConditionalClause) and
                                    isinstance(collection, (list, tuple)) and
                                    any(argument_values_equal(
                                        surface, name, item, arguments[name])
                                        for item in collection)):
                                binding = self.state.bindings.get(
                                    parent_ref.partition(".")[0])
                                if binding is not None:
                                    proofs[(clause.id, name)] = binding.refs
                                    continue
                        # Exact task text already has a deterministic trusted
                        # witness.  The semantic Agent is needed only for a
                        # genuine representation change (for example
                        # ``first page`` -> ``1`` or prose -> source code).
                        if exact_task_value(arguments[name]):
                            proofs[(clause.id, name)] = (QUERY_REF,)
                            continue
                        if (task_rooted(source) and
                                schema_attests_empty(name, arguments[name])):
                            proofs[(clause.id, name)] = (QUERY_REF,)
                            continue
                        target_evidence = evidence_for(target)
                        target_ids = {row["id"] for row in target_evidence}
                        key = (target.id, digest(arguments[name]),
                               tuple(evidence_refs[row["id"]]
                                     for row in target_evidence))
                        if key not in self._semantic_attempts:
                            result = self.derive_agent(
                                task=self.contract.task,
                                instruction=target.instruction,
                                inputs={ref: ref for ref in target.input_refs},
                                value=arguments[name],
                                skill_context=skill_context,
                                evidence_candidates=target_evidence)
                            grounded = (
                                result is True or
                                (isinstance(result, dict) and
                                 result.get("grounded") is True))
                            ids = (result.get("candidate_ids", [])
                                   if isinstance(result, dict) else [])
                            valid_ids = (
                                isinstance(ids, list) and
                                len(set(map(str, ids))) == len(ids) and
                                all(str(item) in target_ids for item in ids))
                            content_position = (
                                surface is not None and
                                surface.accepts_semantic_support(name))
                            if grounded and valid_ids and content_position:
                                # Semantic support is accepted only at an
                                # operator-attested content position. It never
                                # becomes task or target authority.
                                proof = tuple(dict.fromkeys((
                                    SEMANTIC_REF,
                                    *(evidence_refs[str(item)]
                                      for item in ids))))
                            elif (grounded and not ids and
                                  task_rooted(source)):
                                # The trusted task introduced this argument's
                                # authority, and every declared ancestor stays
                                # inside that root. The Agent resolves only the
                                # semantic value (for example first -> 1); it
                                # cannot add a Receipt or widen the Effect.
                                proof = (QUERY_REF,)
                            else:
                                proof = None
                            self._semantic_attempts[key] = proof
                        proof = self._semantic_attempts[key]
                        if proof:
                            proofs[(clause.id, name)] = proof
                        continue
                    ground_source(source, arguments[name])
        return proofs

    def _resolve_effect_supports(self, action: str, arguments: dict,
                                 surface) -> None:
        """Materialize one task-local non-Effect path to an existing Root role."""
        if self.support_agent is None and self.guard_agent is None:
            return
        receipt_version = tuple(receipt.digest for receipt in self.state.receipts)
        for clause in self.contract.clauses:
            if not (isinstance(clause, EffectClause) and clause.action == action):
                continue
            for name, spec in clause.effect_arguments.items():
                if name not in arguments or not (
                        isinstance(spec, dict) and set(spec) == {"from"}):
                    continue
                sources = spec["from"]
                sources = [sources] if isinstance(sources, str) else list(sources or ())
                if not any(self.state.output(source) is UNRESOLVED
                           for source in sources):
                    continue
                key = (clause.id, name, digest(arguments[name]), receipt_version)
                if key in self._support_attempts:
                    continue
                self._support_attempts.add(key)
                clause_by_ref = {
                    item.output_ref: item for item in self.contract.clauses
                    if item.output_ref}
                for source in sources:
                    target = clause_by_ref.get(source)
                    if (self.state.output(source) is UNRESOLVED and
                            isinstance(target, ConditionalClause) and
                            target.operator in {"gt", "lt"} and
                            self.guard_agent is not None):
                        materialize_guard(
                            self.state, self.contract, target, arguments[name],
                            choose=self.guard_agent,
                            equal=lambda left, right: argument_values_equal(
                                surface, name, left, right))
                if (self.support_agent is not None and
                        any(self.state.output(source) is UNRESOLVED
                            for source in sources)):
                    materialize_support(
                        self.state, self.contract, clause, name, arguments[name],
                        choose=self.support_agent,
                        equal=lambda left, right: argument_values_equal(
                            surface, name, left, right),
                        allow_semantic=(surface is not None and
                                        surface.accepts_semantic_support(name)))

    def _resolve_delegated_supports(
            self, action: str, arguments: dict) -> dict[tuple[str, str], tuple]:
        """Build proposal-local proofs for explicitly delegated arguments."""
        if self.support_agent is None:
            return {}
        receipt_version = tuple(receipt.digest for receipt in self.state.receipts)
        proofs = {}
        for clause in self.contract.clauses:
            if not (isinstance(clause, EffectClause) and clause.action == action):
                continue
            for name, spec in clause.effect_arguments.items():
                if (name not in arguments or not isinstance(spec, dict) or
                        set(spec) != {"from", "delegated"} or
                        spec.get("delegated") is not True):
                    continue
                key = (clause.id, name, digest(arguments[name]), receipt_version)
                if key not in self._delegated_attempts:
                    self._delegated_attempts[key] = materialize_delegated_support(
                        self.state, self.contract, clause, name, arguments[name],
                        choose=self.support_agent)
                refs = self._delegated_attempts[key]
                if refs:
                    proofs[(clause.id, name)] = refs
        return proofs

    # -- effect -------------------------------------------------------------
    def _authority_proofs(self, proof_refs, action: str, arguments: dict,
                          surface) -> tuple[BasisReceipt, ...]:
        """Validate fresh, trusted, scope-matched authority receipts."""
        cited = (self._basis_receipts.get(
            item.id if isinstance(item, BasisReceipt) else str(item))
            for item in (proof_refs or ()))
        valid = []
        for receipt in cited:
            if (receipt is None or not receipt.authority or
                    receipt.scope is None or receipt.scope.action != str(action)):
                continue
            if all(name in arguments and argument_values_equal(
                    surface, name, expected, arguments[name])
                   for name, expected in receipt.scope.arguments):
                valid.append(receipt)
        return tuple(valid)

    def _validate_repair(self, action: str, arguments: dict, *, proof_refs=()):
        """Recheck a mechanically reconstructed proposal without any Agent."""
        action, arguments = str(action), dict(arguments or {})
        surface = self.capabilities.get(action)
        if (surface is not None and surface.requires_authority_proof and
                not self._authority_proofs(
                    proof_refs, action, arguments, surface)):
            return False, ()
        events = self.plant.commit(CommitEvent(CALL, action, arguments))
        if any(event.gating for event in events):
            return False, ()
        required = frozenset(getattr(surface, "required", ()) or ())
        content = frozenset(
            name for name in (getattr(surface, "arguments", ()) or ())
            if surface is not None and surface.accepts_semantic_support(name))
        atoms = {
            name: authority_atoms(
                arguments.get(name), surface.authority_grammars(name))
            for name in content if name in arguments}
        verdict = check_effect(
            self.state, self.contract, action, arguments,
            required=required, content=content, content_atoms=atoms,
            equal=lambda name, left, right: argument_values_equal(
                surface, name, left, right))
        return verdict.ok, verdict.refs

    def _apply_invalidation(self, plan) -> None:
        """Invalidate the smallest runtime region represented by PLANT refs."""
        by_receipt: dict[str, dict] = {}
        for token in plan.denied_resources:
            scope = self._plant_scopes.get(str(token), {})
            if scope.get("mechanism") != "marker":
                continue
            for ref in scope.get("refs", ()):
                receipt_digest = str(ref).split("#", 1)[0]
                row = by_receipt.setdefault(
                    receipt_digest, {"paths": set(), "operands": set()})
                row["paths"].update(scope.get("paths", ()))
                operand = scope.get("operand")
                if isinstance(operand, str) and operand:
                    row["operands"].add(operand)

        replaced = set()
        for receipt_digest, row in by_receipt.items():
            receipt = next((item for item in self.state.receipts
                            if item.digest == receipt_digest), None)
            if receipt is None:
                continue
            sanitized = _redact_marker(
                receipt.value, row["paths"], row["operands"])
            if sanitized == receipt.value:
                self.state.invalidate_receipts((receipt_digest,))
            else:
                self.state.replace_receipt(receipt_digest, sanitized)
            replaced.add(receipt_digest)

        # If the adapter could identify only a receipt root, conservatively
        # invalidate it. Source-only Skill/MCP narrative is omitted from the
        # continuation context and remains audit evidence, not active proof.
        remaining = {
            str(ref).split("#", 1)[0]
            for ref in plan.invalidated_refs if "#" in str(ref)
        } - replaced
        self.state.invalidate_receipts(remaining)
        self._reconcile()

    def sanitized_source(self, source: str, value):
        """Replay one non-Receipt carrier with committed marker operands removed."""
        paths, operands = set(), set()
        denied = (() if self.continuation is None else
                  self.continuation.denied_resources)
        for token in denied:
            scope = self._plant_scopes.get(str(token), {})
            if (scope.get("mechanism") == "marker" and
                    scope.get("source") == str(source)):
                paths.update(scope.get("paths", ()))
                operand = scope.get("operand")
                if isinstance(operand, str) and operand:
                    operands.add(operand)
        return _redact_marker(value, paths, operands)

    def continue_decision(self, decision: Decision) -> Decision:
        """Consume one attached plan; unchanged adapters remain fail-closed."""
        if self.continuation is None or not decision.continuation_id:
            return decision
        plan = self.continuation.consume(decision.continuation_id)
        if plan.mode == REPAIR:
            ok, refs = self._validate_repair(
                plan.action, plan.candidate_arguments or {},
                proof_refs=plan.proof_refs)
            if not ok:
                return Decision(
                    "deny", "repair-revalidation-failed",
                    detections=decision.detections,
                    continuation_id=plan.id,
                    continuation=plan.to_dict())
            repaired = Decision(
                "pass", "verified-repair", refs,
                detections=decision.detections)
            return self._with_continuation(
                repaired, plan,
                authorized_arguments=plan.candidate_arguments)
        if plan.mode == REPLAN:
            self._apply_invalidation(plan)
            context = self.continuation.context(self.state, plan)
            replanned = Decision(
                "replan", "sanitized-replan", decision.refs,
                decision.commitments, decision.detections)
            return self._with_continuation(replanned, plan, context=context)
        return self._with_continuation(
            Decision("deny", "safe-abort", decision.refs,
                     decision.commitments, decision.detections), plan)

    def effect_succeeded(self, action: str, arguments: dict) -> None:
        """Record a native success for a later sanitized replan context."""
        if self.continuation is not None:
            self.continuation.record_effect(action, arguments)

    def _approval_scope(self, action: str, arguments: dict, required,
                        surface) -> str:
        """Classify only proposals that an exact user approval can recover.

        A missing Root Effect is eligible only after runtime evidence exists.
        For an existing Root Effect, approval may close unresolved ``from``
        roles, but never an extra argument, a missing required argument, or a
        conflict with a trusted literal.
        """
        roots = [clause for clause in self.contract.clauses
                 if isinstance(clause, EffectClause) and
                 clause.action == action]
        if (self.capabilities and
                (surface is None or not getattr(surface, "effect", False))):
            return ""
        if not roots:
            return "unknown-effect" if self.state.receipts else ""
        producers = {clause.output_ref: clause for clause in self.contract.clauses
                     if clause.output_ref}
        for clause in roots:
            specs = clause.effect_arguments
            if any(name not in specs for name in arguments):
                continue
            if any(name not in arguments for name in required):
                continue
            compatible = True
            for name, spec in specs.items():
                if name not in arguments:
                    continue
                if isinstance(spec, dict) and set(spec) == {"literal"}:
                    compatible = argument_values_equal(
                        surface, name, spec["literal"], arguments[name])
                    if not compatible:
                        break
                elif (isinstance(spec, dict) and
                      set(spec) in ({"from"}, {"from", "delegated"})):
                    sources = spec.get("from")
                    sources = ([sources] if isinstance(sources, str)
                               else list(sources or ()))
                    # Approval may fill an unresolved semantic role; it may not
                    # override an already replayed BindingProof with a
                    # conflicting proposal value.
                    if (sources and all(self.state.output(source) is not UNRESOLVED
                                        for source in sources) and
                            not all(isinstance(producers.get(source), DeriveClause)
                                    for source in sources)):
                        compatible = False
                        break
            if compatible:
                return "unresolved-binding"
        return ""

    def _approval_decision(self, action: str, arguments: dict, reason: str,
                           scope: str, detections=()) -> Decision:
        receipt_refs = tuple(receipt.digest + "#"
                             for receipt in self.state.receipts)
        approval_id = "APPROVAL-" + digest({
            "nonce": self.nonce,
            "task": self.contract.task,
            "action": action,
            "arguments": arguments,
            "receipts": receipt_refs,
        })[:20]
        if approval_id in self._approval_consumed:
            return Decision("deny", "approval-consumed", detections=detections)
        if approval_id in self._approval_denied:
            return Decision("deny", "approval-denied", detections=detections)
        request = {
            "id": approval_id,
            "scope": scope,
            "task": self.contract.task,
            "action": action,
            "arguments": dict(arguments),
            "receipt_refs": list(receipt_refs),
            "evidence": [
                {"ref": receipt.digest + "#",
                 "capability": receipt.capability,
                 "arguments": dict(receipt.arguments),
                 "value": receipt.value}
                for receipt in self.state.receipts
            ],
            "trigger": reason,
        }
        self._approval_requests.setdefault(approval_id, request)
        if approval_id in self._approval_grants:
            return Decision(
                "pass", "one-shot-approval", receipt_refs,
                detections=detections, approval_id=approval_id)
        return Decision(
            "approval", scope, receipt_refs, detections=detections,
            approval_id=approval_id, approval=request)

    def decide_approval(self, approval_id: str, approved: bool) -> None:
        """Record a trusted user's decision for one exact pending proposal."""
        approval_id = str(approval_id)
        if approval_id not in self._approval_requests:
            raise ValueError("unknown approval request")
        if approval_id in self._approval_consumed:
            raise ValueError("approval already consumed")
        if approved:
            self._approval_denied.discard(approval_id)
            self._approval_grants.add(approval_id)
        else:
            self._approval_grants.discard(approval_id)
            self._approval_denied.add(approval_id)

    def approval_succeeded(self, approval_id: str) -> None:
        """Consume a one-shot grant only after the native effect succeeds."""
        approval_id = str(approval_id)
        if approval_id not in self._approval_grants:
            raise ValueError("approval is not granted")
        self._approval_grants.remove(approval_id)
        self._approval_consumed.add(approval_id)

    def effect(self, action: str, arguments: dict, *, proof_refs=()) -> Decision:
        """Gate one effect; advisory premises never contribute authority."""
        arguments = dict(arguments or {})
        commitment = self.commit(
            CALL, str(action), arguments, proof_refs=proof_refs)
        if commitment.route != "pass":
            return commitment
        # A non-gating detection still happened here; carry it through every
        # later verdict so a measurable signal is never lost to the route.
        seen = commitment.detections
        surface = self.capabilities.get(str(action))
        authority_required = bool(
            surface is not None and surface.requires_authority_proof)
        authority = (self._authority_proofs(
            proof_refs, str(action), arguments, surface)
                     if authority_required else ())
        if authority_required and not authority:
            return Decision(
                "deny", "insufficient-authority-proof", detections=seen)
        self._reconcile(materialize=True)
        semantic_proofs = self._resolve_effect_derives(
            str(action), arguments)
        if authority:
            # A trusted adapter may declare that this Root Effect is conferred
            # by cited, runtime-issued granting premises. Those receipts—not a
            # semantic model—then close its unresolved ordinary roles. Literal
            # conflicts and undeclared arguments remain impossible in WRAP.
            authority_refs = tuple(receipt.id for receipt in authority)
            for clause in self.contract.clauses:
                if not (isinstance(clause, EffectClause) and
                        clause.action == str(action)):
                    continue
                for name, spec in clause.effect_arguments.items():
                    if (name in arguments and isinstance(spec, dict) and
                            set(spec) == {"from"}):
                        semantic_proofs.setdefault(
                            (clause.id, name), authority_refs)
        self._resolve_effect_supports(str(action), arguments, surface)
        # Semantic support may close an upstream Derive used by one or more
        # deterministic Conditionals. Replay that now-complete suffix before
        # WRAP compares the Effect proposal; this adds no Agent call.
        self._reconcile(materialize=False)
        delegated_proofs = self._resolve_delegated_supports(
            str(action), arguments)
        required = frozenset(getattr(surface, "required", ()) or ())
        content = frozenset(
            name for name in (getattr(surface, "arguments", ()) or ())
            if surface is not None and surface.accepts_semantic_support(name))
        atoms = {
            name: authority_atoms(
                arguments.get(name), surface.authority_grammars(name))
            for name in content if name in arguments}
        verdict = check_effect(
            self.state, self.contract, str(action), arguments,
            required=required, content=content,
            content_atoms=atoms, delegated_proofs=delegated_proofs,
            semantic_proofs=semantic_proofs,
            equal=lambda name, left, right: argument_values_equal(
                surface, name, left, right))
        if verdict.ok:
            return Decision("pass", verdict.reason, verdict.refs,
                            detections=seen)
        failed = Decision(
            "deny", verdict.reason, verdict.refs, detections=seen)
        plan = None
        if self.continuation is not None:
            plan = self.continuation.propose(
                self.state, action=str(action), arguments=arguments,
                reason=verdict.reason, refs=verdict.refs,
                required=required,
                equal=lambda name, left, right: argument_values_equal(
                    surface, name, left, right),
                validate=lambda candidate: self._validate_repair(
                    str(action), candidate, proof_refs=proof_refs),
                proof_refs=proof_refs)
            if plan.mode == REPAIR:
                return self._with_continuation(failed, plan)
        if self.approval_enabled:
            scope = self._approval_scope(
                str(action), arguments, required, surface)
            if scope:
                return self._approval_decision(
                    str(action), arguments, verdict.reason, scope, seen)
        return (self._with_continuation(failed, plan)
                if plan is not None else failed)

    def response(self, value, *, proof_refs=()) -> Decision:
        """Detect PLANT commitment at the final outbound response sink."""
        return self.commit(RESPONSE, "$response", value, proof_refs=proof_refs)

    def close(self) -> dict:
        basis = [{"id": receipt.id, "source": receipt.source,
                  "receipt_role": receipt.receipt_role,
                  "authority": receipt.authority,
                  "scope": (None if receipt.scope is None
                            else receipt.scope.to_dict()),
                  "decoy": receipt.decoy,
                  "receipt_digest": receipt.receipt_digest,
                  "consumer": receipt.consumer}
                 for receipt in self._basis_receipts.values()]
        accesses = [vars(receipt)
                    for receipt in self._basis_accesses.values()]
        presentations = list(self._proof_presentations)
        approvals = {
            "requested": len(self._approval_requests),
            "granted": len(self._approval_grants) + len(self._approval_consumed),
            "consumed": len(self._approval_consumed),
            "denied": len(self._approval_denied),
            "requests": list(self._approval_requests.values()),
        }
        self._approval_requests.clear()
        self._approval_grants.clear()
        self._approval_denied.clear()
        self._approval_consumed.clear()
        self._basis_receipts.clear()
        self._basis_accesses.clear()
        self._proof_presentations.clear()
        transfers = [
            {"receipt_digest": receipt_digest, "consumer": consumer,
             "basis_ids": [item.id for item in view.basis_receipts]}
            for (receipt_digest, consumer), view in
            self._dependency_transfers.items()
        ]
        self._dependency_transfers.clear()
        continuation = (self.continuation.close()
                        if self.continuation is not None else {})
        return {"wrap": self.state.close(), "plant": self.plant.close(),
                "basis_receipts": basis, "basis_accesses": accesses,
                "dependency_transfers": transfers,
                "proof_presentations": presentations,
                "approvals": approvals,
                "continuation": continuation}

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()
        return False


class Engine:
    """Perceive the environment once, compile one contract per trusted task, and
    start deterministic Episodes.  The only model calls live here (contract
    compile, cached) and in the optional per-Episode binding agents."""

    def __init__(self, model: str | None = None, *,
                 acquire_agent=None, derive_agent=None, support_agent=None,
                 guard_agent=None, intermediate_agent=None, plant_agent=None,
                 approval_enabled: bool = True,
                 continuation_enabled: bool = True,
                 max_replans: int = 1):
        self.model = str(model) if model else ""
        self.approval_enabled = bool(approval_enabled)
        self.continuation_enabled = bool(continuation_enabled)
        self.max_replans = max(0, int(max_replans))
        # The single validated binding agent handles genuine ambiguity that the
        # deterministic pipeline cannot; it can only narrow authority.
        if self.model and any(agent is None for agent in (
                acquire_agent, derive_agent, support_agent, guard_agent,
                intermediate_agent)):
            from code.defense.binding_agent import BindingAgent
            agent = BindingAgent(self.model)
            acquire_agent = acquire_agent or agent.disambiguate_acquire
            derive_agent = derive_agent or agent.ground_derive
            support_agent = support_agent or agent.materialize_support
            guard_agent = guard_agent or agent.materialize_guard
            intermediate_agent = (intermediate_agent or
                                  agent.materialize_intermediate)
        self.acquire_agent = acquire_agent
        self.derive_agent = derive_agent
        self.support_agent = support_agent
        self.guard_agent = guard_agent
        self.intermediate_agent = intermediate_agent
        if self.model and plant_agent is None:
            from code.defense.plant_agent import PlantPlacementAgent
            plant_agent = PlantPlacementAgent(self.model).place
        self.plant_agent = plant_agent
        self._plant_cache: dict = {}
        self.plan = None
        self._contracts: dict = {}
        self._traces: dict = {}

    def perceive(self, tool_schemas, source_carriers=(), skill_manifests=()):
        from code.defense.surveyor import Surveyor
        tool_schemas = list(tool_schemas or ())
        Surveyor.validate_boundary_manifest(tool_schemas)
        self.plan = Surveyor(self.model or None).perceive(
            tool_schemas, list(source_carriers or ()),
            list(skill_manifests or ()))
        return self.plan

    def perceive_skills(self, skill_files, capability_manifest,
                        plant_carriers=(), skill_manifests=()):
        """Register Tool-local boundaries from one or more installed Skills."""
        from code.defense.surveyor import Surveyor
        self.plan = Surveyor(self.model or None).perceive_skills(
            skill_files, capability_manifest, plant_carriers,
            skill_manifests)
        return self.plan

    def _key(self, task, effect_entries):
        return (str(task), tuple(sorted(map(str, effect_entries or ()))))

    def contract(self, task, effect_entries=None):
        from code.defense.taskcontractor import TaskContractor
        if self.plan is None:
            raise RuntimeError("perceive() must run before contract synthesis")
        key = self._key(task, effect_entries)
        if key not in self._contracts:
            if not self.model:
                raise RuntimeError("contract synthesis requires a defense model")
            contract, trace = TaskContractor(self.model).extract_with_trace(
                    str(task), self.plan, effect_entries=key[1] or None)
            self._contracts[key], self._traces[key] = contract, trace
        return self._contracts[key]

    def contract_trace(self, task, effect_entries=None):
        self.contract(task, effect_entries)
        return self._traces.get(self._key(task, effect_entries))

    def start(self, contract, task_id: str | None = None) -> Episode:
        return Episode(
            contract, str(task_id or digest(contract.to_dict())),
            capabilities=getattr(self.plan, "capabilities", {}),
            skills=getattr(self.plan, "skills", {}),
            acquire_agent=self.acquire_agent, derive_agent=self.derive_agent,
            support_agent=self.support_agent,
            guard_agent=self.guard_agent,
            intermediate_agent=self.intermediate_agent,
            plant_agent=self.plant_agent, plant_cache=self._plant_cache,
            plant_surfaces=getattr(self.plan, "sources", {}),
            approval_enabled=self.approval_enabled,
            continuation_enabled=self.continuation_enabled,
            max_replans=self.max_replans)
