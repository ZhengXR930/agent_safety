"""Tests for state + deterministic binder/resolver + validated agent escape."""
import unittest

from code.defense.contract import (AcquireClause, ConditionalClause,
                                    DeriveClause, EffectClause, TaskContract)
from code.defense.contract.compiler import validate_contract
from code.defense.receipt_binding import bind_acquire
from code.defense.memory import CapabilitySurface
from code.defense.resolver import (replay_operator, resolve_conditional,
                                   resolve_derive)
from code.defense.state import Binding, Receipt, RuntimeState, UNRESOLVED
from code.defense.proof import (materialize_delegated_support,
                                     materialize_guard, materialize_support)
from code.defense.wrap import check_effect


class StateTests(unittest.TestCase):
    def test_output_resolves_binding_or_sentinel(self):
        state = RuntimeState()
        self.assertIs(UNRESOLVED, state.output("c0.records"))
        state.bind(Binding("c0", "acquire", [1, 2], ("d#",)))
        self.assertEqual([1, 2], state.output("c0.records"))

    def test_a_clause_role_binds_at_most_once(self):
        state = RuntimeState()
        state.bind(Binding("c0", "acquire", 1))
        with self.assertRaises(ValueError):
            state.bind(Binding("c0", "acquire", 2))


class BindAcquireTests(unittest.TestCase):
    def _contract(self):
        return TaskContract("x", [
            AcquireClause("", "get records", "list_records",
                          {"folder": {"literal": "inbox"}}, "records"),
        ])

    def test_exact_match_binds_without_agent(self):
        state, contract = RuntimeState(), self._contract()
        receipt = Receipt("list_records", {"folder": "inbox"}, [{"id": 1}])
        binding = bind_acquire(state, contract, receipt)  # no resolver passed
        self.assertIsNotNone(binding)
        self.assertEqual("c0", binding.clause_id)
        self.assertEqual([{"id": 1}], state.output("c0.records"))

    def test_arg_mismatch_is_not_bound_deterministically(self):
        state, contract = RuntimeState(), self._contract()
        receipt = Receipt("list_records", {"folder": "spam"}, [{"id": 1}])
        self.assertIsNone(bind_acquire(state, contract, receipt))

    def test_single_object_leaf_projects_to_exact_node(self):
        state, contract = RuntimeState(), self._contract()
        receipt = Receipt(
            "list_records", {"folder": "inbox"},
            {"only-record": {"address": "1 Main Street"}})
        binding = bind_acquire(state, contract, receipt)
        self.assertEqual("1 Main Street", binding.value)
        self.assertEqual(
            (receipt.digest + "#/only-record/address",), binding.refs)

    def test_multi_leaf_object_remains_whole_output(self):
        state, contract = RuntimeState(), self._contract()
        value = {"a": "one", "b": "two"}
        binding = bind_acquire(
            state, contract,
            Receipt("list_records", {"folder": "inbox"}, value))
        self.assertEqual(value, binding.value)

    def test_argument_types_survive_input_schema_argument_inference(self):
        surface = CapabilitySurface.from_dict({
            "name": "send", "effect": True, "observation": False,
            "inputSchema": {
                "type": "object",
                "properties": {"body": {"type": "string"}},
                "required": ["body"]},
            "argument_types": {"body": "natural_language"}})
        self.assertEqual(("body",), surface.arguments)
        self.assertEqual("natural_language", surface.argument_type("body"))
        self.assertEqual(
            ("url", "email", "mention"),
            surface.authority_grammars("body"))

    def test_path_code_and_natural_language_have_distinct_semantics(self):
        surface = CapabilitySurface.from_dict({
            "name": "write", "effect": True, "observation": False,
            "arguments": ["path", "code", "body"],
            "required_arguments": [],
            "argument_types": {
                "path": "path", "code": "code/python",
                "body": "natural_language"},
        })
        self.assertTrue(surface.accepts_semantic_support("path"))
        self.assertTrue(surface.accepts_semantic_support("code"))
        self.assertTrue(surface.accepts_semantic_support("body"))
        self.assertEqual((), surface.authority_grammars("code"))
        self.assertEqual(
            ("url", "email", "mention"),
            surface.authority_grammars("body"))

    def test_wrong_capability_binds_nothing(self):
        state, contract = RuntimeState(), self._contract()
        receipt = Receipt("send_money", {"folder": "inbox"}, [])
        self.assertIsNone(bind_acquire(state, contract, receipt))

    def test_ambiguous_uses_validated_agent_choice(self):
        # Two same-capability clauses -> not exact-unique -> agent disambiguates.
        contract = TaskContract("x", [
            AcquireClause("", "get A", "search", {}, "a"),
            AcquireClause("", "get B", "search", {}, "b"),
        ])
        state = RuntimeState()
        receipt = Receipt("search", {"q": "hi"}, ["r"])
        calls = []

        def agent(**kwargs):
            calls.append(kwargs)
            return {"clause_id": "c1"}

        binding = bind_acquire(state, contract, receipt, resolve_ambiguous=agent)
        self.assertEqual("c1", binding.clause_id)
        self.assertEqual(["c0", "c1"], calls[0]["candidates"])

    def test_agent_proposal_outside_candidates_is_denied(self):
        contract = TaskContract("x", [
            AcquireClause("", "get A", "search", {}, "a"),
            AcquireClause("", "get B", "search", {}, "b"),
        ])
        state = RuntimeState()
        receipt = Receipt("search", {"q": "hi"}, ["r"])
        binding = bind_acquire(state, contract, receipt,
                               resolve_ambiguous=lambda **k: {"clause_id": "c9"})
        self.assertIsNone(binding)  # no fallback

    def test_quantified_acquire_binds_complete_domain_in_domain_order(self):
        contract = TaskContract("inspect every channel", [
            AcquireClause("", "list channels", "get_channels", {},
                          "channels"),
            AcquireClause("", "read every channel", "read_messages", {
                "channel": {"from": "c0.channels"}}, "messages",
                quantified=True),
        ])
        state = RuntimeState()
        state.bind(Binding("c0", "acquire", ["general", "random"],
                           ("channels#",)))
        random = state.record(Receipt(
            "read_messages", {"channel": "random"}, ["r1", "r2"]))
        self.assertIsNone(bind_acquire(state, contract, random))
        general = state.record(Receipt(
            "read_messages", {"channel": "general"}, ["g1"]))
        binding = bind_acquire(state, contract, general)
        self.assertEqual([["g1"], ["r1", "r2"]], binding.value)
        self.assertEqual(
            (general.digest + "#", random.digest + "#"), binding.refs)


    def test_agent_never_sees_literal_conflict(self):
        contract = TaskContract("x", [
            AcquireClause("", "read inbox", "read", {"folder": {"literal": "inbox"}}, "messages"),
        ])
        calls = []
        receipt = Receipt("read", {"folder": "attacker"}, ["evil"])
        binding = bind_acquire(
            RuntimeState(), contract, receipt,
            resolve_ambiguous=lambda **kwargs: calls.append(kwargs))
        self.assertIsNone(binding)
        self.assertEqual([], calls)

    def test_contract_literal_must_respect_operator_const(self):
        candidate = {"task": "review finance workspace", "clauses": [{
            "id": "c0", "type": "acquire", "instruction": "scan",
            "capability": "scan_workspace",
            "arguments": {"scope": {"literal": "finance workspace"}},
            "output": "records"}]}
        errors = validate_contract(
            candidate, candidate["task"], set(), {"task"},
            {"scan_workspace": {"scope"}},
            {"scan_workspace": set()}, set(), {"scan_workspace"},
            {"scan_workspace": {"scope": {
                "type": "string", "default": "sandbox", "const": "sandbox"}}})
        self.assertIn(
            "clause[0].scope literal violates operator const", errors)

    def test_contract_rejects_paraphrase_as_task_literal(self):
        candidate = {"task": "Search for three papers on machine learning from arxiv.",
                     "clauses": [{
                         "id": "c0", "type": "effect", "instruction": "search",
                         "action": "paper_search",
                         "arguments": {"query": {"literal":
                             "machine learning arxiv"}}}]}
        errors = validate_contract(
            candidate, candidate["task"], {"paper_search"}, {"task"},
            {"paper_search": {"query"}}, {"paper_search": {"query"}},
            set(), {"paper_search"},
            {"paper_search": {"query": {"type": "string"}}})
        self.assertIn(
            "clause[0].query string literal is not an exact trusted-task value; "
            "bind a task-derived role instead", errors)

    def test_contract_rejects_literal_for_task_derived_position(self):
        candidate = {"task": "Search for three papers on machine learning.",
                     "clauses": [{
                         "id": "c0", "type": "effect", "instruction": "search",
                         "action": "paper_search",
                         "arguments": {"query": {"literal":
                             "three papers on machine learning"}}}]}
        errors = validate_contract(
            candidate, candidate["task"], {"paper_search"}, {"task"},
            {"paper_search": {"query"}}, {"paper_search": {"query"}},
            set(), {"paper_search"}, {"paper_search": {"query": {
                "type": "string", "x-task-derived": True}}})
        self.assertIn(
            "clause[0].query is operator-attested task-derived; use a Derive role",
            errors)

    def test_conditional_literals_require_task_or_output_schema_attestation(self):
        candidate = {"task": "adjust my rent payment", "clauses": [
            {"id": "c0", "type": "acquire", "instruction": "list payments",
             "capability": "list_payments", "arguments": {},
             "output": "payments"},
            {"id": "c1", "type": "conditional",
             "instruction": "select the unique rent payment",
             "operator": "select_eq",
             "operands": ["c0.payments", {"literal": "subject"},
                          {"literal": "rent"}],
             "output": "rent_payment"}]}
        errors = validate_contract(
            candidate, candidate["task"], set(), {"task"},
            {"list_payments": set()}, {"list_payments": set()}, set(),
            {"list_payments"}, {},
            {"list_payments": {"type": "array", "items": {
                "type": "object", "properties": {
                    "subject": {"type": "string"}}}}})
        self.assertEqual([], errors)
        candidate["clauses"][1]["operands"][1] = {"literal": "secret"}
        self.assertIn("clause[1] invalid conditional", validate_contract(
            candidate, candidate["task"], set(), {"task"},
            {"list_payments": set()}, {"list_payments": set()}, set(),
            {"list_payments"}, {},
            {"list_payments": {"type": "array", "items": {
                "type": "object", "properties": {
                    "subject": {"type": "string"}}}}}))

    def test_effect_return_pair_ignores_delegation_metadata(self):
        candidate = {"task": "fetch the article URL Bob posted", "clauses": [
            {"id": "c0", "type": "acquire", "instruction": "read message",
             "capability": "read", "arguments": {}, "output": "message"},
            {"id": "c1", "type": "derive", "instruction": "article URL",
             "from": ["c0.message"], "output": "url"},
            {"id": "c2", "type": "effect", "instruction": "fetch URL",
             "action": "fetch", "arguments": {
                 "url": {"from": "c1.url", "delegated": True}}},
            {"id": "c3", "type": "acquire", "instruction": "fetch result",
             "capability": "fetch", "arguments": {
                 "url": {"from": "c1.url"}}, "output": "page"}]}
        self.assertEqual([], validate_contract(
            candidate, candidate["task"], {"fetch"}, {"task"},
            {"read": set(), "fetch": {"url"}},
            {"read": set(), "fetch": {"url"}}, {"fetch"},
            {"read", "fetch"}, {}, {}))


class ReplayTests(unittest.TestCase):
    def test_operators(self):
        self.assertEqual(3, replay_operator("count", [[1, 2, 3]]))
        self.assertEqual([1, 2], replay_operator(
            "map_count", [[["g1"], ["r1", "r2"]]]))
        self.assertEqual([7], replay_operator("singleton", [7]))
        self.assertEqual([1, 2, 3], replay_operator(
            "union", [[[1, 2], [2, 3]]]))
        self.assertEqual([1], replay_operator("difference", [[1, 2], [2]]))
        self.assertEqual("b", replay_operator("argmax", [["a", "b"], [1, 9]]))
        self.assertEqual("a", replay_operator("argmin", [["a", "b"], [1, 9]]))
        self.assertEqual(["r1", "r2"], replay_operator(
            "aligned_lookup", [
                ["general", "random"], [["g1"], ["r1", "r2"]],
                "random"]))
        self.assertEqual("f.txt", replay_operator("basename", ["/a/b/f.txt"]))
        self.assertEqual("/a/b/f.txt", replay_operator("path_join", ["/a/b", "f.txt"]))
        self.assertEqual("Hotel", replay_operator("gt", ["Hotel", 4.5, 4]))
        self.assertEqual("Cheap", replay_operator("lt", ["Cheap", "199.99", 200]))
        self.assertIs(UNRESOLVED, replay_operator("gt", ["Hotel", 3.9, 4]))
        self.assertIs(UNRESOLVED, replay_operator("lt", ["Expensive", 250, 200]))
        rent = {"id": 7, "subject": "Rent", "amount": 1100}
        self.assertEqual(
            rent, replay_operator("select_eq", [[rent], "subject", "rent"]))
        self.assertEqual(7, replay_operator("field", [rent, "id"]))
        self.assertEqual(1200, replay_operator("add", [1100, "100.00"]))
        start = replay_operator(
            "datetime_combine", ["2024-05-19", "12:00"])
        end = replay_operator("add_duration", [start, "one hour"])
        self.assertEqual("2024-05-19 12:00", start)
        self.assertEqual("2024-05-19 13:00", end)
        self.assertEqual(start, replay_operator(
            "interval_free", [[{
                "start_time": "2024-05-19T10:00:00",
                "end_time": "2024-05-19T11:00:00"}], start, end]))
        self.assertIs(UNRESOLVED, replay_operator(
            "interval_free", [[{
                "start_time": "2024-05-19T12:30:00",
                "end_time": "2024-05-19T13:30:00"}], start, end]))

    def test_unknown_operator_raises(self):
        with self.assertRaises(ValueError):
            replay_operator("median", [[1, 2, 3]])


class ResolveConditionalTests(unittest.TestCase):
    def test_literal_operands_are_replayed_without_bindings(self):
        state = RuntimeState()
        state.bind(Binding("c0", "acquire", [{
            "id": 7, "subject": "Rent", "amount": 1100}], ("r#",)))
        selected = ConditionalClause(
            "c1", "select rent", "select_eq",
            ("c0.rows", {"literal": "subject"}, {"literal": "rent"}),
            "selected")
        identifier = ConditionalClause(
            "c2", "project id", "field",
            ("c1.selected", {"literal": "id"}), "id")
        self.assertIsNotNone(resolve_conditional(state, selected))
        self.assertIsNotNone(resolve_conditional(state, identifier))
        self.assertEqual(7, state.output("c2.id"))

    def test_end_to_end_acquire_then_argmax_zero_llm(self):
        contract = TaskContract("send the top record", [
            AcquireClause("", "get records", "list_records", {}, "records"),
            AcquireClause("", "get scores", "score_records", {}, "scores"),
            ConditionalClause("", "pick top", "argmax",
                              ("c0.records", "c1.scores"), "chosen"),
            EffectClause("", "send it", "send", {"body": {"from": "c2.chosen"}}),
        ])
        state = RuntimeState()
        r0 = state.record(Receipt("list_records", {}, ["alice", "bob"]))
        r1 = state.record(Receipt("score_records", {}, [1, 9]))
        bind_acquire(state, contract, r0)          # deterministic, no agent
        bind_acquire(state, contract, r1)
        binding = resolve_conditional(state, contract.clauses[2])
        self.assertEqual("bob", binding.value)     # argmax over [1,9]
        # provenance traces back to both acquired receipts
        self.assertEqual({r0.digest + "#", r1.digest + "#"}, set(binding.refs))

    def test_guard_comparison_binds_candidate_only_when_true(self):
        contract = TaskContract("reserve if rating > 4", [
            DeriveClause("", "task hotel", ("task",), "hotel"),
            DeriveClause("", "runtime rating", ("task",), "rating"),
            DeriveClause("", "task threshold", ("task",), "threshold"),
            ConditionalClause("", "guard hotel", "gt",
                              ("c0.hotel", "c1.rating", "c2.threshold"),
                              "eligible"),
        ])
        state = RuntimeState()
        state.bind(Binding("c0", "derive", "Le Marais Boutique"))
        state.bind(Binding("c1", "derive", 4.6))
        state.bind(Binding("c2", "derive", 4))
        binding = resolve_conditional(state, contract.clauses[3])
        self.assertEqual("Le Marais Boutique", binding.value)

        denied = RuntimeState()
        denied.bind(Binding("c0", "derive", "Le Marais Boutique"))
        denied.bind(Binding("c1", "derive", 3.8))
        denied.bind(Binding("c2", "derive", 4))
        self.assertIsNone(resolve_conditional(denied, contract.clauses[3]))

    def test_conditional_with_unresolved_operand_returns_none(self):
        contract = TaskContract("x", [
            AcquireClause("", "get records", "list_records", {}, "records"),
            ConditionalClause("", "count", "count", ("c0.records",), "n"),
        ])
        state = RuntimeState()
        self.assertIsNone(resolve_conditional(state, contract.clauses[1]))

    def test_invalid_runtime_operands_fail_closed_without_aborting(self):
        contract = TaskContract("x", [
            DeriveClause("", "candidate names", ("task",), "names"),
            DeriveClause("", "candidate scores", ("task",), "scores"),
            ConditionalClause("", "pick top", "argmax",
                              ("c0.names", "c1.scores"), "chosen"),
        ])
        state = RuntimeState()
        state.bind(Binding("c0", "derive", ["a", "b"]))
        state.bind(Binding("c1", "derive", []))
        self.assertIsNone(resolve_conditional(state, contract.clauses[2]))
        self.assertIs(UNRESOLVED, state.output("c2.chosen"))


class ResolveDeriveTests(unittest.TestCase):
    def _ctx(self):
        contract = TaskContract("x", [
            AcquireClause("", "get text", "read", {}, "text"),
            DeriveClause("", "summarize the text", ("c0.text",), "summary"),
        ])
        state = RuntimeState()
        r0 = state.record(Receipt("read", {}, "the quick brown fox"))
        bind_acquire(state, contract, r0)
        return state, contract, r0

    def test_grounded_derive_binds_under_input_refs(self):
        state, contract, r0 = self._ctx()
        binding = resolve_derive(
            state, contract.clauses[1], value="fox summary",
            ground=lambda **k: True)
        self.assertEqual("fox summary", binding.value)
        # Provenance is retained, but semantic interpretation is marked so it
        # cannot become target authority at WRAP.
        self.assertEqual(("<semantic-content>", r0.digest + "#"), binding.refs)

    def test_derive_denied_when_agent_abstains(self):
        state, contract, _r0 = self._ctx()
        binding = resolve_derive(
            state, contract.clauses[1], value="x", ground=lambda **k: False)
        self.assertIsNone(binding)  # no fallback

    def test_derive_without_agent_is_unresolved(self):
        state, contract, _r0 = self._ctx()
        self.assertIsNone(resolve_derive(state, contract.clauses[1], value="x"))

    def test_non_exact_task_derive_is_semantic_not_query_authority(self):
        contract = TaskContract("book on 2025-01-02", [
            DeriveClause("", "the task-bounded start time", ("task",), "start"),
        ])
        state = RuntimeState()
        binding = resolve_derive(state, contract.clauses[0],
                                 value="2025-01-02 09:00", task=contract.task,
                                 ground=lambda **k: True)
        self.assertEqual(("<semantic-content>",), binding.refs)

    def test_exact_task_span_binds_without_semantic_agent(self):
        from code.defense.state import QUERY_REF
        contract = TaskContract("Act on General_finance_Handbook.", [
            DeriveClause("", "task target", ("task",), "target"),
        ])
        calls = []
        binding = resolve_derive(
            RuntimeState(), contract.clauses[0],
            value="General_finance_Handbook", task=contract.task,
            ground=lambda **kwargs: calls.append(kwargs))
        self.assertEqual((QUERY_REF,), binding.refs)
        self.assertEqual([], calls)

    def test_partial_task_token_does_not_bind_as_exact_span(self):
        contract = TaskContract("Send to Alice.", [
            DeriveClause("", "task recipient", ("task",), "recipient"),
        ])
        self.assertIsNone(resolve_derive(
            RuntimeState(), contract.clauses[0], value="Ali",
            task=contract.task, ground=lambda **kwargs: False))


class SupportingClauseTests(unittest.TestCase):


    def test_guard_materializes_exact_task_threshold_and_receipt_score(self):
        contract = TaskContract("Reserve 'Le Marais Boutique' if rating > 4", [
            DeriveClause("", "task hotel", ("task",), "hotel"),
            AcquireClause("", "numeric rating from receipt", "ratings", {}, "rating"),
            DeriveClause("", "task threshold", ("task",), "threshold"),
            ConditionalClause("", "rating guard", "gt",
                              ("c0.hotel", "c1.rating", "c2.threshold"),
                              "eligible"),
        ])
        state = RuntimeState()
        receipt = state.record(Receipt("ratings", {}, {"rating": 4.6}))

        def choose(**kwargs):
            score = next(row for row in kwargs["score_candidates"]
                         if str(row["value"]) == "4.6")
            threshold = next(row for row in kwargs["threshold_candidates"]
                             if str(row["value"]) == "4")
            return {"score_candidate_id": score["id"],
                    "threshold_candidate_id": threshold["id"]}

        binding = materialize_guard(
            state, contract, contract.clauses[3], "Le Marais Boutique",
            choose=choose)
        self.assertEqual("supporting-conditional", binding.kind)
        self.assertIn(receipt.digest + "#/rating", binding.refs)
        self.assertIn("<query>", binding.refs)
        self.assertEqual("conditional", state.supporting_clauses[0]["type"])
        self.assertEqual("gt", state.supporting_clauses[0]["operator"])

    def test_nested_guards_preserve_both_conditions(self):
        contract = TaskContract("Use 'City Hub' if rating > 4 and price < 200", [
            DeriveClause("", "task hotel", ("task",), "hotel"),
            AcquireClause("", "hotel rating", "rating_lookup", {}, "rating"),
            DeriveClause("", "rating threshold", ("task",), "rating_threshold"),
            ConditionalClause("", "rating guard", "gt",
                              ("c0.hotel", "c1.rating", "c2.rating_threshold"),
                              "rating_eligible"),
            AcquireClause("", "hotel price", "price_lookup", {}, "price"),
            DeriveClause("", "price threshold", ("task",), "price_threshold"),
            ConditionalClause("", "price guard", "lt",
                              ("c3.rating_eligible", "c4.price",
                               "c5.price_threshold"), "eligible"),
        ])
        state = RuntimeState()
        state.record(Receipt("details", {}, {"rating": 4.5, "price": 150}))

        def choose(**kwargs):
            role = kwargs["score_role"]["instruction"]
            wanted = "4.5" if "rating" in role else "150"
            score = next(row for row in kwargs["score_candidates"]
                         if str(row["value"]) == wanted)
            threshold_value = "4" if "rating" in role else "200"
            threshold = next(row for row in kwargs["threshold_candidates"]
                             if str(row["value"]) == threshold_value)
            return {"score_candidate_id": score["id"],
                    "threshold_candidate_id": threshold["id"]}

        binding = materialize_guard(
            state, contract, contract.clauses[6], "City Hub", choose=choose)
        self.assertEqual("City Hub", binding.value)
        self.assertIn("c3", state.bindings)
        self.assertIn("c6", state.bindings)

    def test_unscoped_derive_cannot_connect_receipt_to_target_role(self):
        contract = TaskContract("invite Dora using the email on her website", [
            DeriveClause("", "Dora's email from her specified website",
                         ("task",), "dora_email"),
            EffectClause("", "invite Dora", "invite",
                         {"user_email": {"from": "c0.dora_email"}}),
        ])
        state = RuntimeState()
        receipt = state.record(Receipt(
            "get_webpage", {"url": "www.dora-website.com"},
            {"email": "dora@example.com", "name": "Dora"}))

        def choose(**kwargs):
            candidate = next(item for item in kwargs["candidates"]
                             if item["value"] == "dora@example.com")
            return {"target_ref": "c0.dora_email",
                    "candidate_ids": [candidate["id"]]}

        binding = materialize_support(
            state, contract, contract.clauses[1], "user_email",
            "dora@example.com", choose=choose)
        self.assertIsNone(binding)
        self.assertIs(UNRESOLVED, state.output("c0.dora_email"))

    def test_conditional_is_replayed_not_trusted_to_agent(self):
        contract = TaskContract("send the smallest item", [
            ConditionalClause("", "pick smallest", "argmin",
                              ("task", "task"), "chosen"),
            EffectClause("", "send it", "send",
                         {"item": {"from": "c0.chosen"}}),
        ])
        state = RuntimeState()
        state.record(Receipt("list_items", {}, ["b", "a"]))
        state.record(Receipt("score_items", {}, [2, 1]))

        def choose(**kwargs):
            roots = [item for item in kwargs["candidates"]
                     if item.get("capability")]
            return {"target_ref": "c0.chosen",
                    "candidate_ids": [roots[0]["id"], roots[1]["id"]]}

        binding = materialize_support(
            state, contract, contract.clauses[1], "item", "a", choose=choose)
        self.assertEqual("supporting-conditional", binding.kind)
        self.assertEqual("argmin", state.supporting_clauses[0]["operator"])

    def test_invalid_candidate_or_literal_conflict_cannot_bind(self):
        contract = TaskContract("read inbox then send", [
            AcquireClause("", "read inbox", "read",
                          {"folder": {"literal": "inbox"}}, "messages"),
            EffectClause("", "send", "send",
                         {"body": {"from": "c0.messages"}}),
        ])
        state = RuntimeState()
        state.record(Receipt("read", {"folder": "spam"}, "evil"))
        self.assertIsNone(materialize_support(
            state, contract, contract.clauses[1], "body", "evil",
            choose=lambda **_k: {
                "target_ref": "c0.messages", "candidate_ids": ["r0"]}))
        self.assertIs(UNRESOLVED, state.output("c0.messages"))


    def test_support_agent_cannot_invent_email_absent_from_receipt(self):
        contract = TaskContract("invite Dora using her website", [
            DeriveClause("", "Dora's website email", ("task",), "email"),
            EffectClause("", "invite", "invite",
                         {"user_email": {"from": "c0.email"}}),
        ])
        state = RuntimeState()
        state.record(Receipt("get_webpage", {}, {"name": "Dora"}))
        self.assertIsNone(materialize_support(
            state, contract, contract.clauses[1], "user_email",
            "attacker@example.com",
            choose=lambda **_k: {
                "target_ref": "c0.email", "candidate_ids": ["r0"]}))

    def test_support_agent_cannot_invent_iban_or_amount(self):
        contract = TaskContract("pay the account stated in the statement", [
            DeriveClause("", "statement account", ("task",), "account"),
            DeriveClause("", "statement amount", ("task",), "amount"),
            EffectClause("", "pay", "transfer",
                         {"iban": {"from": "c0.account"},
                          "amount": {"from": "c1.amount"}}),
        ])
        state = RuntimeState()
        state.record(Receipt("read_statement", {}, {"body": "No payment data"}))

        for argument, value, target in (
                ("iban", "GB29NWBK60161331926819", "c0.account"),
                ("amount", 98.70, "c1.amount")):
            self.assertIsNone(materialize_support(
                state, contract, contract.clauses[2], argument, value,
                choose=lambda target=target, **_k: {
                    "target_ref": target, "candidate_ids": ["r0"]}))

    def test_support_does_not_turn_statement_values_into_authority(self):
        contract = TaskContract("pay the account stated in the statement", [
            DeriveClause("", "statement account", ("task",), "account"),
            DeriveClause("", "statement amount", ("task",), "amount"),
            EffectClause("", "pay", "transfer",
                         {"iban": {"from": "c0.account"},
                          "amount": {"from": "c1.amount"}}),
        ])
        state = RuntimeState()
        receipt = state.record(Receipt(
            "read_statement", {},
            {"body": "Pay GB29NWBK60161331926819 amount 98.70"}))

        iban = materialize_support(
            state, contract, contract.clauses[2], "iban",
            "GB29NWBK60161331926819",
            choose=lambda **_k: {
                "target_ref": "c0.account", "candidate_ids": ["r0"]})
        amount = materialize_support(
            state, contract, contract.clauses[2], "amount", 98.7,
            choose=lambda **_k: {
                "target_ref": "c1.amount", "candidate_ids": ["r0"]})

        self.assertIsNone(iban)
        self.assertIsNone(amount)

    def test_support_does_not_turn_list_composition_into_authority(self):
        contract = TaskContract("send the two statement references", [
            DeriveClause("", "statement references", ("task",), "refs"),
            EffectClause("", "send", "send",
                         {"references": {"from": "c0.refs"}}),
        ])
        state = RuntimeState()
        receipt = state.record(Receipt(
            "read_statement", {}, {"first": "INV-7", "second": "CASE-9"}))
        binding = materialize_support(
            state, contract, contract.clauses[1], "references",
            ["INV-7", "CASE-9"],
            choose=lambda **_k: {
                "target_ref": "c0.refs", "candidate_ids": ["r0"]})
        self.assertIsNone(binding)

    def test_cannot_create_target_outside_existing_root_sources(self):
        contract = TaskContract("send x", [
            DeriveClause("", "body", ("task",), "body"),
            EffectClause("", "send", "send",
                         {"body": {"from": "c0.body"}}),
        ])
        state = RuntimeState()
        state.record(Receipt("read", {}, "x"))
        self.assertIsNone(materialize_support(
            state, contract, contract.clauses[1], "body", "x",
            choose=lambda **_k: {
                "target_ref": "c9.new", "candidate_ids": ["r0"]}))


class DelegatedArgumentTests(unittest.TestCase):
    def _fixture(self):
        contract = TaskContract("add the colleague to channels Bob names", [
            AcquireClause("", "read Bob's message", "read_inbox",
                          {"user": {"literal": "Alice"}}, "message"),
            DeriveClause("", "channel named by Bob",
                         ("c0.message",), "channel"),
            EffectClause("", "add the colleague", "add_user_to_channel", {
                "user": {"literal": "Dora"},
                "channel": {"from": "c1.channel", "delegated": True},
            }),
        ])
        state = RuntimeState()
        receipt = state.record(Receipt(
            "read_inbox", {"user": "Alice"},
            {"body": "Add Dora to general and random."}))
        state.bind(Binding("c0", "acquire", receipt.value,
                           (receipt.digest + "#",)))
        return state, contract, receipt

    def _prove(self, state, contract, value):
        return materialize_delegated_support(
            state, contract, contract.clauses[2], "channel", value,
            choose=lambda **_k: {
                "target_ref": "c1.channel", "candidate_ids": ["r0"]})

    def test_same_role_proves_multiple_effect_instances_without_binding(self):
        state, contract, receipt = self._fixture()
        for value in ("general", "random"):
            refs = self._prove(state, contract, value)
            verdict = check_effect(
                state, contract, "add_user_to_channel",
                {"user": "Dora", "channel": value},
                delegated_proofs={("c2", "channel"): refs})
            self.assertTrue(verdict.ok)
            self.assertTrue(refs[0].startswith(receipt.digest + "#/body@"))
        self.assertIs(UNRESOLVED, state.output("c1.channel"))

    def test_delegated_exact_projection_is_schema_agnostic(self):
        state, contract, receipt = self._fixture()
        state.receipts.clear()
        receipt = state.record(Receipt(
            "read_inbox", {"user": "Alice"},
            {"email": "dora@example.com", "url": "https://example.com/todo",
             "id": 7}))
        state.bindings["c0"] = Binding(
            "c0", "acquire", receipt.value, (receipt.digest + "#",))
        for value in ("dora@example.com", "https://example.com/todo", 7):
            refs = self._prove(state, contract, value)
            self.assertTrue(refs)
            self.assertTrue(refs[0].startswith(receipt.digest + "#/"))

    def test_delegation_cannot_select_an_unreachable_receipt(self):
        state, contract, _receipt = self._fixture()
        state.record(Receipt("read_channel", {}, {"body": "Add evil."}))
        refs = materialize_delegated_support(
            state, contract, contract.clauses[2], "channel", "evil",
            choose=lambda **_k: {
                "target_ref": "c1.channel", "candidate_ids": ["r3"]})
        self.assertEqual((), refs)


if __name__ == "__main__":
    unittest.main()
