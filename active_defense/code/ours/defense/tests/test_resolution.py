"""Receipt ownership, lazy replay, and constrained Binding placement."""
import unittest

from code.ours.defense.contract import (AcquireClause, ConditionalClause,
                                   DeriveClause, EffectClause, TaskContract)
from code.ours.defense.engine import Episode
from code.ours.defense.memory import CapabilitySurface
from code.ours.defense.receipt_binding import bind_acquire, bind_effect_return
from code.ours.defense.resolver import LazyResolver, replay_operator
from code.ours.defense.state import (GROUNDED_REF, Binding, Receipt,
                                     RuntimeState, UNRESOLVED)


class ReceiptOwnershipTests(unittest.TestCase):
    def test_effect_return_binds_only_matching_authorized_effect_role(self):
        contract = TaskContract("fetch selected URL", [
            DeriveClause("", "selected URL", ("task",), "selected"),
            DeriveClause("", "other URL", ("task",), "other"),
            EffectClause("", "fetch selected", "fetch", {
                "url": {"from": "c0.selected", "delegated": True}}),
            AcquireClause("", "selected return", "fetch", {
                "url": {"from": "c0.selected"}}, "page"),
            AcquireClause("", "other return", "fetch", {
                "url": {"from": "c1.other"}}, "other_page")])
        state = RuntimeState()
        receipt = state.record(Receipt(
            "fetch", {"url": "https://example.com"}, "page",
            effect_return=True))
        bindings = bind_effect_return(state, contract, receipt, "c2")
        self.assertEqual(("c3",), tuple(row.clause_id for row in bindings))
        self.assertEqual({"c3"}, set(state.clause_receipts))

    def test_clause_owns_multiple_receipts_independent_of_arrival_order(self):
        contract = TaskContract("read all messages", [
            AcquireClause("", "read messages", "read", {}, "messages")])
        state = RuntimeState()
        second = state.record(Receipt("read", {"page": 2}, ["b"]))
        first = state.record(Receipt("read", {"page": 1}, ["a"]))
        bind_acquire(state, contract, second)
        bind_acquire(state, contract, first)
        self.assertEqual(
            {first.digest, second.digest}, state.clause_receipts["c0"])
        self.assertEqual(
            {first.digest, second.digest},
            {row.receipt.digest for row in LazyResolver(
                state, contract).values("c0.messages")})

    def test_same_call_supersedes_older_receipt(self):
        contract = TaskContract("read", [
            AcquireClause("", "read", "read", {}, "value")])
        state = RuntimeState()
        old = state.record(Receipt("read", {"id": 1}, "old"))
        new = state.record(Receipt("read", {"id": 1}, "new"))
        bind_acquire(state, contract, old)
        bind_acquire(state, contract, new)
        self.assertEqual((new,), state.receipts_for("c0"))
        self.assertIn(old.digest, state.superseded_receipts)

    def test_literal_conflict_never_reaches_agent(self):
        contract = TaskContract("read inbox", [AcquireClause(
            "", "read inbox", "read", {"folder": {"literal": "inbox"}},
            "messages")])
        calls = []
        result = bind_acquire(
            RuntimeState(), contract,
            Receipt("read", {"folder": "spam"}, []),
            resolve_ambiguous=lambda **request: calls.append(request))
        self.assertIsNone(result)
        self.assertEqual([], calls)

    def test_exact_receipt_can_belong_to_multiple_acquire_clauses(self):
        contract = TaskContract("search", [
            AcquireClause("", "first role", "search", {}, "first"),
            AcquireClause("", "second role", "search", {}, "second")])
        state = RuntimeState()
        receipt = state.record(Receipt("search", {"q": "x"}, [1]))
        binding = bind_acquire(state, contract, receipt)
        self.assertEqual("c0", binding.clause_id)
        self.assertEqual({"c0", "c1"}, set(state.clause_receipts))

    def test_alternative_workflow_acquire_uses_bounded_clause_choice(self):
        contract = TaskContract("search for safety", [
            DeriveClause("", "task search query", ("task",), "query"),
            AcquireClause("", "search results", "search", {
                "query": {"from": "c0.query"}}, "results")])
        state = RuntimeState()
        receipt = state.record(Receipt(
            "search", {"query": "safety"}, ["paper"]))
        seen = []

        def choose(**request):
            seen.extend(request["candidates"])
            return {"clause_id": "c1"}

        binding = bind_acquire(state, contract, receipt, choose)
        self.assertEqual("c1", binding.clause_id)
        self.assertEqual(["c1"], [row["clause_id"] for row in seen])

    def test_scalar_call_matches_an_element_of_upstream_collection(self):
        contract = TaskContract("read every channel", [
            AcquireClause("", "channels", "get_channels", {}, "channels"),
            AcquireClause("", "members", "get_members", {
                "channel": {"from": "c0.channels"}}, "members",
                quantified=True)])
        state = RuntimeState()
        channels = state.record(Receipt(
            "get_channels", {}, ["general", "random", "private"]))
        bind_acquire(state, contract, channels)
        member_receipts = [state.record(Receipt(
            "get_members", {"channel": channel}, [channel + "-user"]))
            for channel in ["general", "random", "private"]]
        calls = []
        for receipt in member_receipts:
            bind_acquire(
                state, contract, receipt,
                resolve_ambiguous=lambda **request: calls.append(request))
        self.assertEqual([], calls)
        self.assertEqual(
            {receipt.digest for receipt in member_receipts},
            state.clause_receipts["c1"])


class LazyBindingTests(unittest.TestCase):
    def test_closed_numeric_arithmetic(self):
        self.assertEqual(6, replay_operator("multiply", [2, 3]))
        self.assertEqual(195, replay_operator("percent_of", [1000, 19.5]))
        self.assertEqual(
            200.29,
            replay_operator("add", [
                replay_operator("percent_of", [1000, 19.5]), 5.29]))

    def test_effect_accepts_exact_member_of_closed_difference(self):
        contract = TaskContract("add every missing user", [
            AcquireClause("", "all", "read_all", {}, "all_users"),
            AcquireClause("", "present", "read_present", {}, "present"),
            ConditionalClause("", "missing", "difference",
                              ("c0.all_users", "c1.present"), "missing"),
            EffectClause("", "add", "add", {
                "user": {"from": "c2.missing"}})])
        surface = CapabilitySurface.from_dict({
            "name": "add", "effect": True, "arguments": ["user"],
            "required_arguments": ["user"]})
        episode = Episode(
            contract, "closed-member", capabilities={"add": surface},
            approval_enabled=False, continuation_enabled=False)
        episode.observe("read_all", {}, ["Alice", "Bob", "Charlie"])
        episode.observe("read_present", {}, ["Alice"])
        self.assertEqual("pass", episode.effect("add", {"user": "Bob"}).route)
        self.assertEqual("pass", episode.effect("add", {"user": "Charlie"}).route)
        self.assertEqual(
            "untraceable-arg:user",
            episode.effect("add", {"user": "Mallory"}).reason)

    def test_aligned_lookup_uses_quantified_receipt_call_identity(self):
        contract = TaskContract("select members for b", [
            AcquireClause("", "channels", "channels", {}, "channels"),
            AcquireClause("", "members", "members", {
                "channel": {"from": "c0.channels"}}, "by_channel",
                quantified=True),
            ConditionalClause("", "selected", "aligned_lookup", (
                "c0.channels", "c1.by_channel", {"literal": "b"}),
                "selected_members")])
        state = RuntimeState()
        channels = state.record(Receipt("channels", {}, ["a", "b"]))
        bind_acquire(state, contract, channels)
        for channel, users in [("a", ["Alice"]),
                               ("b", ["Bob", "Charlie"])]:
            receipt = state.record(Receipt(
                "members", {"channel": channel}, users))
            bind_acquire(state, contract, receipt)
        rows = LazyResolver(state, contract).values("c2.selected_members")
        self.assertEqual((["Bob", "Charlie"],),
                         tuple(row.value for row in rows))

    def test_generic_structure_and_ranking_operators(self):
        messages = [
            [{"sender": "bob"}, {"sender": "alice"}],
            [{"sender": "alice"}, {"sender": "bob"},
             {"sender": "alice"}],
        ]
        flat = replay_operator("flatten", [messages])
        senders = replay_operator("project", [flat, "sender"])
        frequencies = replay_operator("frequency", [senders])
        ranked = replay_operator(
            "sort_by", [frequencies, ["count", "value"], ["desc", "asc"]])
        self.assertEqual(
            [{"value": "alice", "count": 3},
             {"value": "bob", "count": 2}], ranked)
        self.assertEqual(
            ["alice", "bob"], replay_operator("project", [ranked, "value"]))

    def test_closed_object_construction(self):
        source = {"id_": "19", "type": "file", "filename": "minutes.docx"}
        attachment = replay_operator(
            "object_set", [source, "file_id", "19"])
        self.assertEqual("19", attachment["file_id"])
        self.assertEqual([attachment], replay_operator("singleton", [attachment]))

    def test_closed_keys_feed_bounded_delegated_selection(self):
        contract = TaskContract("email the client named in the file", [
            AcquireClause("", "file", "read", {}, "file"),
            ConditionalClause("", "sharing map", "field", (
                "c0.file", {"literal": "shared_with"}), "shared"),
            ConditionalClause("", "sharing identities", "keys", (
                "c1.shared",), "emails"),
            DeriveClause("", "client email named by the file", (
                "task", "c0.file", "c2.emails"), "recipients"),
            EffectClause("", "send", "send", {
                "recipients": {"from": "c3.recipients", "delegated": True}}),
        ])

        def place(**request):
            goal = request["goals"][0]
            selected = next(row for row in goal["candidates"]
                            if row["value"] == "john@example.com")
            return {"placements": [{
                "goal_id": goal["goal_id"],
                "candidate_ids": [selected["candidate_id"]],
                "compose": "list"}]}

        episode = Episode(
            contract, "n", binding_agent=place,
            approval_enabled=False, continuation_enabled=False)
        episode.observe("read", {}, {
            "body": "Client: John",
            "shared_with": {"staff@corp.com": "rw",
                            "john@example.com": "rw"}})
        self.assertEqual(
            "pass", episode.effect("send", {
                "recipients": ["john@example.com"]}).route)

    def test_coalesce_selects_first_available_closed_value(self):
        self.assertEqual(
            "fallback",
            replay_operator("coalesce", [UNRESOLVED, "fallback"]))
        contract = TaskContract("prefer first available", [
            AcquireClause("", "available values", "read", {}, "rows"),
            ConditionalClause(
                "", "missing preferred", "select_eq",
                ("c0.rows", {"literal": "kind"},
                 {"literal": "preferred"}), "preferred"),
            ConditionalClause(
                "", "available fallback", "select_eq",
                ("c0.rows", {"literal": "kind"},
                 {"literal": "fallback"}), "fallback"),
            ConditionalClause(
                "", "first available", "coalesce",
                ("c1.preferred", "c2.fallback"), "chosen"),
            EffectClause("", "use", "use", {
                "item": {"from": "c3.chosen"}})])
        episode = Episode(
            contract, "n", approval_enabled=False,
            continuation_enabled=False)
        episode.observe("read", {}, [{"kind": "fallback", "id": 7}])
        self.assertEqual(
            "pass", episode.effect("use", {
                "item": {"kind": "fallback", "id": 7}}).route)

    def test_closed_argmax_is_replayed_without_agent(self):
        contract = TaskContract("book top hotel", [
            AcquireClause("", "hotels", "hotels", {}, "items"),
            AcquireClause("", "ratings", "ratings", {}, "scores"),
            ConditionalClause("", "top", "argmax",
                              ("c0.items", "c1.scores"), "chosen"),
            EffectClause("", "book", "book",
                         {"hotel": {"from": "c2.chosen"}})])
        episode = Episode(
            contract, "n", approval_enabled=False,
            continuation_enabled=False)
        episode.observe("ratings", {}, [4.9, 3.1])
        episode.observe("hotels", {}, ["A", "B"])
        decision = episode.effect("book", {"hotel": "A"})
        self.assertEqual("pass", decision.route)
        self.assertEqual(2, len(decision.refs))

    def test_add_duration_accepts_task_literal_hyphenation(self):
        self.assertEqual(
            "2024-05-16 11:00",
            replay_operator(
                "add_duration", ["2024-05-16 10:00", "1-hour"]))

    def test_normalize_date_is_closed_and_handles_task_ordinal_forms(self):
        self.assertEqual(
            "2025-01-11",
            replay_operator("normalize_date", ["January 11th, 2025"]))
        self.assertEqual(
            "2024-05-15",
            replay_operator("normalize_date", ["May 15th 2024"]))

    def test_bound_acquire_remains_resolvable_after_ephemeral_call_role(self):
        contract = TaskContract("look up the selected hotel address", [
            DeriveClause("", "selected hotel", ("task",), "hotel"),
            AcquireClause("", "selected address", "address", {
                "hotel": {"from": "c0.hotel"}}, "addresses"),
            ConditionalClause("", "selected address value", "field", (
                "c1.addresses", "c0.hotel"), "location"),
            EffectClause("", "create reminder", "create", {
                "location": {"from": "c2.location"}}),
        ])
        state = RuntimeState()
        receipt = state.record(Receipt(
            "address", {"hotel": "A"}, {"A": "1 Main St"}))
        # The ownership edge was established while c0 had a proposal-local
        # value; that value is intentionally absent from persistent state.
        state.admit("c1", receipt)
        # The selected identity is intentionally absent from both persistent
        # state and this later proposal.  The same bound Receipt links its
        # exact invocation identity to its one-entry return object.
        resolver = LazyResolver(state, contract)
        self.assertEqual(
            "1 Main St", resolver.values("c2.location")[0].value)

    def test_one_agent_call_resolves_all_numeric_operator_inputs(self):
        contract = TaskContract("increase 1100 by the notice amount", [
            AcquireClause("", "notice", "read_notice", {}, "notice"),
            DeriveClause("", "current amount", ("task",), "current"),
            DeriveClause("", "increase amount", ("c0.notice",), "delta"),
            ConditionalClause("", "new amount", "add",
                              ("c1.current", "c2.delta"), "amount"),
            EffectClause("", "pay", "pay",
                         {"amount": {"from": "c3.amount"}})])
        calls = []

        def place(**request):
            calls.append(request)
            placements = []
            for goal in request["goals"]:
                self.assertEqual("role_selection", goal["support_mode"])
                selected = next(row for row in goal["candidates"]
                                if row["value"] in {1100, 100})
                placements.append({
                    "goal_id": goal["goal_id"],
                    "candidate_ids": [selected["candidate_id"]],
                    "compose": "scalar"})
            return {"placements": placements}

        episode = Episode(
            contract, "n", binding_agent=place,
            approval_enabled=False, continuation_enabled=False)
        episode.observe("read_notice", {}, "Increase: 100.00")
        self.assertEqual(
            "pass", episode.effect("pay", {"amount": 1200}).route)
        self.assertEqual(1, len(calls))

    def test_numeric_span_survives_generic_equality_operand(self):
        contract = TaskContract("refund the 10.00 payment", [
            AcquireClause("", "transactions", "recent", {}, "rows"),
            DeriveClause("", "task refund amount", ("task",), "amount"),
            ConditionalClause("", "matching payment", "select_eq", (
                "c0.rows", {"literal": "amount"}, "c1.amount"), "payment"),
            ConditionalClause("", "sender", "field", (
                "c2.payment", {"literal": "sender"}), "recipient"),
            EffectClause("", "refund", "send", {
                "recipient": {"from": "c3.recipient"}})])

        def place(**request):
            goal = request["goals"][0]
            selected = next(row for row in goal["candidates"]
                            if row["value"] == 10)
            return {"placements": [{
                "goal_id": goal["goal_id"],
                "candidate_ids": [selected["candidate_id"]],
                "compose": "scalar"}]}

        episode = Episode(
            contract, "n", binding_agent=place,
            approval_enabled=False, continuation_enabled=False)
        episode.observe("recent", {}, [
            {"amount": 10.0, "sender": "GB29"},
            {"amount": 15, "sender": "DE12"}])
        self.assertEqual(
            "pass", episode.effect("send", {"recipient": "GB29"}).route)

    def test_exact_url_span_closes_delegated_argument(self):
        contract = TaskContract("fetch the URL Bob posted", [
            AcquireClause("", "message", "read", {}, "message"),
            DeriveClause("", "URL Bob posted", ("c0.message",), "url"),
            EffectClause("", "fetch", "fetch", {
                "url": {"from": "c1.url", "delegated": True}})])
        surface = CapabilitySurface.from_dict({
            "name": "fetch", "effect": True, "observation": True,
            "effect_return": True, "arguments": ["url"],
            "required_arguments": ["url"],
            "argument_types": {"url": "url"}})

        calls = []

        def place(**request):
            calls.append(request)
            return {"placements": []}

        episode = Episode(
            contract, "n", capabilities={"fetch": surface},
            binding_agent=place, approval_enabled=False,
            continuation_enabled=False)
        episode.observe("read", {}, {"body": "See https://example.com/x"})
        decision = episode.effect("fetch", {"url": "https://example.com/x"})
        self.assertEqual("pass", decision.route)
        self.assertIn("@", decision.refs[0])
        self.assertEqual([], calls)

    def test_delegated_projection_rejects_ambiguous_exact_leaves(self):
        contract = TaskContract("fetch the URL Bob posted", [
            AcquireClause("", "messages", "read", {}, "messages"),
            DeriveClause("", "URL Bob posted", ("c0.messages",), "url"),
            EffectClause("", "fetch", "fetch", {
                "url": {"from": "c1.url", "delegated": True}})])
        surface = CapabilitySurface.from_dict({
            "name": "fetch", "effect": True, "observation": True,
            "effect_return": True, "arguments": ["url"],
            "required_arguments": ["url"],
            "argument_types": {"url": "url"}})
        episode = Episode(
            contract, "n", capabilities={"fetch": surface},
            binding_agent=lambda **_: {"placements": []},
            approval_enabled=False, continuation_enabled=False)
        episode.observe("read", {}, [
            {"body": "See https://example.com/x"},
            {"body": "Duplicate https://example.com/x"}])
        decision = episode.effect("fetch", {"url": "https://example.com/x"})
        self.assertEqual("deny", decision.route)

    def test_effect_projects_exact_node_from_acquire_collection(self):
        contract = TaskContract("reschedule the dental event", [
            AcquireClause("", "calendar events", "events", {}, "events"),
            EffectClause("", "reschedule", "reschedule", {
                "event_id": {"from": "c0.events"}})])

        def place(**request):
            goal = request["goals"][0]
            selected = next(row for row in goal["candidates"]
                            if row["value"] == "5")
            return {"placements": [{
                "goal_id": goal["goal_id"],
                "candidate_ids": [selected["candidate_id"]],
                "compose": "scalar"}]}

        episode = Episode(
            contract, "n", binding_agent=place,
            approval_enabled=False, continuation_enabled=False)
        episode.observe("events", {}, [
            {"id": "5", "title": "Dental check-up"},
            {"id": "6", "title": "Lunch"}])
        self.assertEqual(
            "pass", episode.effect("reschedule", {"event_id": "5"}).route)

    def test_proposal_cache_tracks_compiled_goal_domain(self):
        contract = TaskContract("use item A", [
            AcquireClause("", "available items", "read", {}, "items"),
            EffectClause("", "use selected item", "use", {
                "item": {"from": "c0.items"}})])
        calls = []

        def place(**request):
            calls.append(request)
            goal = request["goals"][0]
            selected = next(row for row in goal["candidates"]
                            if row["value"] == "A")
            return {"placements": [{
                "goal_id": goal["goal_id"],
                "candidate_ids": [selected["candidate_id"]],
                "compose": "scalar"}]}

        episode = Episode(
            contract, "n", binding_agent=place,
            approval_enabled=False, continuation_enabled=False)
        episode.observe("read", {"page": 1}, [{"id": "A"}])
        self.assertEqual("pass", episode.effect("use", {"item": "A"}).route)

        # This Receipt changes the global version but cannot reach the proof
        # goal, so the prior id-only semantic choice remains reusable.
        episode.observe("unrelated", {}, {"note": "irrelevant"})
        self.assertEqual("pass", episode.effect("use", {"item": "A"}).route)
        self.assertEqual(1, len(calls))

        # A new reachable candidate changes the compiled domain and must cause
        # a fresh bounded choice even though the Effect proposal is identical.
        episode.observe("read", {"page": 2}, [{"id": "B"}])
        self.assertEqual("pass", episode.effect("use", {"item": "A"}).route)
        self.assertEqual(2, len(calls))

    def test_effect_composes_list_from_exact_nodes(self):
        contract = TaskContract("invite both contacts", [
            AcquireClause("", "contacts", "contacts", {}, "contacts"),
            DeriveClause("", "invited contact emails", ("c0.contacts",),
                         "participants"),
            EffectClause("", "invite", "invite", {
                "participants": {"from": "c1.participants"}})])

        def place(**request):
            goal = request["goals"][0]
            ids = [row["candidate_id"] for row in goal["candidates"]
                   if isinstance(row["value"], str) and
                   row["value"] in {"a@example.com", "b@example.com"}]
            return {"placements": [{
                "goal_id": goal["goal_id"],
                "candidate_ids": ids, "compose": "list"}]}

        episode = Episode(
            contract, "n", binding_agent=place,
            approval_enabled=False, continuation_enabled=False)
        episode.observe("contacts", {}, [
            {"email": "a@example.com"}, {"email": "b@example.com"}])
        self.assertEqual("pass", episode.effect("invite", {
            "participants": ["a@example.com", "b@example.com"]}).route)

    def test_semantic_support_is_limited_to_content_argument(self):
        contract = TaskContract("summarize and send Alice", [
            AcquireClause("", "article", "read", {}, "article"),
            DeriveClause("", "article summary", ("c0.article",), "summary"),
            EffectClause("", "send", "send", {
                "to": {"literal": "Alice"},
                "body": {"from": "c1.summary"}})])
        surface = CapabilitySurface.from_dict({
            "name": "send", "effect": True,
            "arguments": ["to", "body"],
            "required_arguments": ["to", "body"],
            "argument_types": {"to": "email", "body": "natural_language"}})

        def place(**request):
            goal = request["goals"][0]
            return {"placements": [{
                "goal_id": goal["goal_id"],
                "candidate_ids": [goal["candidates"][0]["candidate_id"]],
                "compose": "scalar"}]}

        episode = Episode(
            contract, "n", capabilities={"send": surface},
            binding_agent=place, approval_enabled=False,
            continuation_enabled=False)
        episode.observe("read", {}, "A long article about safety")
        self.assertEqual("pass", episode.effect("send", {
            "to": "Alice", "body": "It discusses safety."}).route)
        self.assertEqual("deny", episode.effect("send", {
            "to": "Eve", "body": "It discusses safety."}).route)

    def test_semantic_derive_is_grounded_from_receipt(self):
        contract = TaskContract("create the meeting described by the email", [
            AcquireClause("", "meeting email", "read", {}, "email"),
            DeriveClause("", "normalized meeting start time",
                         ("c0.email",), "start_time"),
            EffectClause("", "create meeting", "create", {
                "start_time": {"from": "c1.start_time"}})])

        def place(**request):
            goal = request["goals"][0]
            self.assertEqual("exact_or_semantic", goal["support_mode"])
            self.assertEqual("2024-05-15 12:00", goal["proposed"])
            return {"placements": [{
                "goal_id": goal["goal_id"],
                "candidate_ids": [goal["candidates"][0]["candidate_id"]],
                "compose": "scalar"}]}

        surface = CapabilitySurface.from_dict({
            "name": "create", "effect": True,
            "arguments": ["start_time"],
            "required_arguments": ["start_time"],
            "argument_types": {"start_time": "natural_language"}})
        episode = Episode(
            contract, "n", capabilities={"create": surface},
            binding_agent=place,
            approval_enabled=False, continuation_enabled=False)
        episode.observe("read", {}, "Meeting: May 15, 2024 at noon")
        decision = episode.effect("create", {
            "start_time": "2024-05-15 12:00"})
        self.assertEqual("pass", decision.route)
        self.assertIn(GROUNDED_REF, decision.refs)

    def test_semantic_grounding_does_not_authorize_delegated_identity(self):
        contract = TaskContract("send to the person named in the email", [
            AcquireClause("", "email", "read", {}, "email"),
            DeriveClause("", "recipient identity", ("c0.email",),
                         "recipient"),
            EffectClause("", "send", "send", {
                "recipient": {"from": "c1.recipient", "delegated": True}})])

        def place(**request):
            goal = request["goals"][0]
            self.assertEqual("exact", goal["support_mode"])
            return {"placements": [{
                "goal_id": goal["goal_id"],
                "candidate_ids": [goal["candidates"][0]["candidate_id"]],
                "compose": "scalar"}]}

        episode = Episode(
            contract, "n", binding_agent=place,
            approval_enabled=False, continuation_enabled=False)
        episode.observe("read", {}, "Contact Alice through the usual channel")
        self.assertEqual("deny", episode.effect("send", {
            "recipient": "alice@example.com"}).route)

    def test_semantic_derive_replays_value_preserving_conditionals(self):
        contract = TaskContract("book a qualifying hotel from the report", [
            AcquireClause("", "hotel report", "read", {}, "report"),
            DeriveClause("", "qualifying hotel title", ("c0.report",),
                         "hotel"),
            ConditionalClause("", "rating threshold", "gt", (
                "c1.hotel", {"literal": 4.7}, {"literal": 4}), "rated"),
            ConditionalClause("", "price threshold", "lt", (
                "c2.rated", {"literal": 150}, {"literal": 200}), "chosen"),
            EffectClause("", "book hotel", "book", {
                "title": {"from": "c3.chosen"}})])

        def place(**request):
            goal = request["goals"][0]
            self.assertEqual("intermediate", goal["mode"])
            self.assertEqual("Montmartre Suites", goal["proposed"])
            return {"placements": [{
                "goal_id": goal["goal_id"],
                "candidate_ids": [goal["candidates"][0]["candidate_id"]],
                "compose": "scalar"}]}

        episode = Episode(
            contract, "n", binding_agent=place,
            approval_enabled=False, continuation_enabled=False)
        episode.observe("read", {},
                        "The report's top qualifying property is the "
                        "Montmartre option")
        decision = episode.effect("book", {"title": "Montmartre Suites"})
        self.assertEqual("pass", decision.route)
        self.assertIn(GROUNDED_REF, decision.refs)

    def test_invalid_batched_goal_does_not_erase_valid_grounding(self):
        contract = TaskContract("write the requested summary", [
            DeriveClause("", "task-scoped output path", ("task",), "path"),
            DeriveClause("", "task-scoped summary", ("task",), "content"),
            EffectClause("", "write", "write", {
                "path": {"from": "c0.path"},
                "content": {"from": "c1.content"}})])
        surface = CapabilitySurface.from_dict({
            "name": "write", "effect": True,
            "arguments": ["path", "content"],
            "required_arguments": ["path", "content"],
            "argument_types": {
                "path": "path", "content": "natural_language"}})

        def place(**request):
            by_arg = {goal["argument"]: goal for goal in request["goals"]}
            path = by_arg["path"]
            return {"placements": [
                {"goal_id": path["goal_id"],
                 "candidate_ids": [path["candidates"][0]["candidate_id"]],
                 "compose": "scalar"},
                {"goal_id": by_arg["content"]["goal_id"],
                 "candidate_ids": ["not-a-code-issued-id"],
                 "compose": "scalar"}]}

        episode = Episode(
            contract, "n", capabilities={"write": surface},
            binding_agent=place, approval_enabled=False,
            continuation_enabled=False)
        decision = episode.effect("write", {
            "path": "summary.md", "content": "Summary"})
        self.assertEqual("deny", decision.route)
        self.assertEqual("untraceable-arg:content", decision.reason)


class ReplayTests(unittest.TestCase):
    def test_closed_operator_algebra(self):
        self.assertEqual([7], replay_operator("singleton", [7]))
        self.assertEqual("b", replay_operator(
            "argmax", [["a", "b"], [1, 9]]))
        self.assertEqual(1200, replay_operator("add", [1100, "100.00"]))
        self.assertEqual("Hotel", replay_operator("gt", ["Hotel", 4.5, 4]))
        self.assertIs(UNRESOLVED,
                      replay_operator("lt", ["Hotel", 250, 200]))

    def test_unknown_operator_raises(self):
        with self.assertRaises(ValueError):
            replay_operator("median", [[1, 2, 3]])


class LegacyBindingIsolationTests(unittest.TestCase):
    def test_persistent_bindings_remain_available_to_continuation_only(self):
        state = RuntimeState()
        state.bind(Binding("c0", "repair", "x", ("r#",)))
        self.assertEqual("x", state.output("c0.value"))


if __name__ == "__main__":
    unittest.main()
