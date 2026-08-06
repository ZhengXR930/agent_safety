"""Receipt ownership, lazy replay, and constrained Binding placement."""
import unittest

from code.defense.contract import (AcquireClause, ConditionalClause,
                                   DeriveClause, EffectClause, TaskContract)
from code.defense.engine import Episode
from code.defense.memory import CapabilitySurface
from code.defense.receipt_binding import bind_acquire
from code.defense.resolver import LazyResolver, replay_operator
from code.defense.state import Binding, Receipt, RuntimeState, UNRESOLVED


class ReceiptOwnershipTests(unittest.TestCase):
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


class LazyBindingTests(unittest.TestCase):
    def test_closed_numeric_arithmetic(self):
        self.assertEqual(6, replay_operator("multiply", [2, 3]))
        self.assertEqual(195, replay_operator("percent_of", [1000, 19.5]))
        self.assertEqual(
            200.29,
            replay_operator("add", [
                replay_operator("percent_of", [1000, 19.5]), 5.29]))

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

        def place(**request):
            goal = request["goals"][0]
            selected = next(row for row in goal["candidates"]
                            if "example.com" in str(row["value"]))
            return {"placements": [{
                "goal_id": goal["goal_id"],
                "candidate_ids": [selected["candidate_id"]],
                "compose": "scalar"}]}

        episode = Episode(
            contract, "n", capabilities={"fetch": surface},
            binding_agent=place, approval_enabled=False,
            continuation_enabled=False)
        episode.observe("read", {}, {"body": "See https://example.com/x"})
        decision = episode.effect("fetch", {"url": "https://example.com/x"})
        self.assertEqual("pass", decision.route)
        self.assertIn("@", decision.refs[0])

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
