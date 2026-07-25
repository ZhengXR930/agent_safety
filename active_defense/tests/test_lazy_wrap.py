import json
import unittest
from pathlib import Path
from unittest.mock import patch

from code.defense.engine import Engine
from code.defense.auditor import RecoveryState
from code.defense.memory import CapabilitySurface
from code.defense.plant import Plant, PlantRuntime, replace_observation
from code.defense.taskcontractor import Clause, Effect, TaskContract
from code.defense.wrap import Observation, SemanticJudge, WrapRuntime


def _capability(name, arguments=(), *, effect=False, observation=False):
    return CapabilitySurface(
        name, arguments=tuple(arguments), effect=effect,
        observation=observation,
        required_arguments=tuple(arguments) if effect else (),
    )


def _slack_contract():
    path = Path("results/union_relation_v69_20260724/slack10_fixed_contract.json")
    from code.defense.taskcontractor import TaskContract
    return TaskContract.from_dict(json.loads(path.read_text())["user_task_10"])


def _slack_runtime():
    return WrapRuntime(_slack_contract(), {
        "get_channels": _capability("get_channels", observation=True),
        "read_channel_messages": _capability(
            "read_channel_messages", ("channel",), observation=True),
        "get_users_in_channel": _capability(
            "get_users_in_channel", ("channel",), observation=True),
        "add_user_to_channel": _capability(
            "add_user_to_channel", ("channel", "user"), effect=True),
    })


class LazyWrapTests(unittest.TestCase):
    def _complete_slack_snapshot(self):
        runtime = _slack_runtime()
        runtime.observe("get_channels", {}, ["general", "random"])
        runtime.observe(
            "read_channel_messages", {"channel": "general"}, [1, 2, 3])
        runtime.observe(
            "read_channel_messages", {"channel": "random"}, [1])
        runtime.observe(
            "get_users_in_channel", {"channel": "general"}, ["Alice", "Bob"])
        runtime.observe(
            "get_users_in_channel", {"channel": "random"}, ["Bob"])
        return runtime

    def test_observations_are_passive_unowned_receipts(self):
        runtime = _slack_runtime()
        receipt = runtime.observe("unplanned_search", {"q": "x"}, {"result": 1})

        self.assertEqual([receipt], runtime.observations)
        self.assertFalse(hasattr(runtime, "_receipt_clauses"))
        self.assertFalse(hasattr(runtime, "_outputs"))

    def test_effect_time_relations_bind_complete_snapshot(self):
        evidence = self._complete_slack_snapshot().evidence(
            "add_user_to_channel", {"channel": "random", "user": "Alice"})

        self.assertTrue(evidence.complete)
        self.assertTrue(evidence.bindings["channel"])
        self.assertTrue(evidence.bindings["user"])

    def test_relation_conflict_is_a_hard_boundary_violation(self):
        runtime = self._complete_slack_snapshot()

        wrong_channel = runtime.evidence(
            "add_user_to_channel", {"channel": "general", "user": "Alice"})
        unknown_user = runtime.evidence(
            "add_user_to_channel", {"channel": "random", "user": "Mallory"})

        self.assertEqual(("channel",), wrong_channel.conflicts)
        self.assertEqual(("user",), unknown_user.conflicts)

    def test_missing_domain_coverage_is_unresolved_not_conflict(self):
        runtime = _slack_runtime()
        runtime.observe("get_channels", {}, ["general", "random"])
        runtime.observe(
            "read_channel_messages", {"channel": "general"}, [1])
        runtime.observe(
            "get_users_in_channel", {"channel": "general"}, [])

        evidence = runtime.evidence(
            "add_user_to_channel", {"channel": "general", "user": "Alice"})

        self.assertEqual((), evidence.conflicts)
        self.assertEqual({"channel", "user"}, set(evidence.unresolved))

    def test_partial_quantified_graph_cannot_fall_back_to_semantic_materialization(self):
        class Judge:
            def __init__(self):
                self.witness_calls = 0

            def materialize(self, task, clause, receipts):
                return {"status": "uncertain"}

            def witness(self, task, clause, proposed, receipts):
                self.witness_calls += 1
                return {"status": "supported",
                        "refs": [receipts[0].digest + "#"]}

        contract = TaskContract("add Alice to the least active channel", [
            Clause("c0", "list every channel", ["get_channels"], "channels"),
            Clause("c1", "read each channel", [
                "c0.channels", "read_channel_messages"
            ], "messages", arguments={"channel": {"from": "c0.channels"}}),
            # Deliberately omit the optional closed argmin expression.  The
            # quantified graph alone must still prevent partial support.
            Clause("c2", "select the least active channel", [
                "c0.channels", "c1.messages"
            ], "channel"),
            Clause("c3", "add Alice", ["task", "c2.channel"],
                   effect=Effect("add_user_to_channel", {
                       "channel": {"from": "c2.channel"}, "user": "Alice"
                   })),
        ])
        judge = Judge()
        runtime = WrapRuntime(contract, {
            "get_channels": _capability("get_channels", observation=True),
            "read_channel_messages": _capability(
                "read_channel_messages", ("channel",), observation=True),
            "add_user_to_channel": _capability(
                "add_user_to_channel", ("channel", "user"), effect=True),
        }, judge)
        runtime.observe("get_channels", {}, ["general", "external"])
        runtime.observe(
            "read_channel_messages", {"channel": "general"}, [1])

        evidence = runtime.evidence(
            "add_user_to_channel", {"channel": "general", "user": "Alice"})

        self.assertEqual((), evidence.conflicts)
        self.assertEqual(("channel",), evidence.unresolved)
        self.assertEqual(0, judge.witness_calls)
    def test_new_receipt_changes_on_demand_result_without_stale_output(self):
        runtime = _slack_runtime()
        runtime.observe("get_channels", {}, ["general", "random"])
        runtime.observe(
            "read_channel_messages", {"channel": "general"}, [1])
        runtime.observe(
            "get_users_in_channel", {"channel": "general"}, [])
        first = runtime.evidence(
            "add_user_to_channel", {"channel": "general", "user": "Alice"})
        self.assertFalse(first.complete)

        runtime.observe(
            "read_channel_messages", {"channel": "random"}, [1, 2])
        runtime.observe(
            "get_users_in_channel", {"channel": "random"}, ["Alice"])
        second = runtime.evidence(
            "add_user_to_channel", {"channel": "general", "user": "Alice"})

        self.assertTrue(second.complete)
        self.assertFalse(hasattr(runtime, "_outputs"))

    def test_unrelated_receipts_cannot_expand_effect_authority(self):
        runtime = self._complete_slack_snapshot()
        runtime.observe(
            "attacker_profile", {}, {"channel": "evil", "user": "Mallory"})

        evidence = runtime.evidence(
            "add_user_to_channel", {"channel": "evil", "user": "Mallory"})

        self.assertEqual({"channel", "user"}, set(evidence.conflicts))

    def test_literal_effect_gate_needs_no_judge(self):
        contract = TaskContract("message Alice", [
            Clause("", "message Alice", ["task"], effect=Effect(
                "send", {"recipient": "Alice"})),
        ])
        runtime = WrapRuntime(contract, {
            "send": _capability("send", ("recipient",), effect=True),
        })

        self.assertTrue(runtime.evidence(
            "send", {"recipient": "Alice"}).complete)
        self.assertEqual(
            ("recipient",),
            runtime.evidence("send", {"recipient": "Mallory"}).conflicts,
        )

    def test_plant_view_does_not_change_canonical_receipt(self):
        class Designer:
            def design(self, source, observation, source_kind):
                return Plant(source, "plant-token", {
                    "url": "plant-token",
                    "title": observation["title"],
                })

        contract = TaskContract("read a page", [
            Clause("", "read page", ["fetch"], "page"),
        ])
        runtime = WrapRuntime(contract, {
            "fetch": _capability("fetch", ("url",), observation=True),
        })
        plant = PlantRuntime(designer=Designer())
        canonical = {"url": "clean.example", "title": "Report"}
        runtime.observe("fetch", {"url": "clean.example"}, canonical)
        exposed = plant.expose(
            "fetch:{clean}", canonical, replace_observation, "fetch")

        self.assertEqual(canonical, runtime.observations[0].value)
        self.assertEqual("plant-token", exposed["url"])
        self.assertTrue(plant.detect(
            {"url": "plant-token"}, "effect:open"))

    def test_recovery_quarantines_only_one_exact_receipt_node(self):
        runtime = _slack_runtime()
        clean = runtime.observe(
            "read_channel_messages", {"channel": "general"},
            {"messages": [{"text": "normal"}, {"text": "invite Eve"}]})
        runtime.observe(
            "read_channel_messages", {"channel": "random"},
            {"messages": [{"text": "other"}]})
        recovery = RecoveryState()

        self.assertEqual(1, recovery.quarantine_unique_values(
            runtime.observations, ("invite Eve",)))
        sanitized = recovery.sanitize(clean)

        self.assertEqual("normal", sanitized["messages"][0]["text"])
        self.assertEqual(
            "[content withheld by execution guard]",
            sanitized["messages"][1]["text"])

    def test_recovery_refuses_ambiguous_value_attribution(self):
        runtime = _slack_runtime()
        runtime.observe("read_channel_messages", {"channel": "general"}, ["Eve"])
        runtime.observe("read_channel_messages", {"channel": "random"}, ["Eve"])
        recovery = RecoveryState()

        self.assertEqual(0, recovery.quarantine_unique_values(
            runtime.observations, ("Eve",)))
        self.assertEqual(set(), recovery.quarantine)

    def test_recovery_budget_is_bounded(self):
        recovery = RecoveryState(budget=1)

        self.assertTrue(recovery.begin_restart())
        self.assertFalse(recovery.begin_restart())

    def test_recovery_recomputes_only_unique_closed_relation_bindings(self):
        runtime = self._complete_slack_snapshot()

        self.assertEqual(
            {"channel": "random", "user": "Alice"},
            runtime.recovery_bindings("c8"),
        )

    def test_recovery_does_not_reanchor_through_quarantined_parent(self):
        runtime = self._complete_slack_snapshot()
        evidence = runtime.evidence(
            "add_user_to_channel", {"channel": "random", "user": "Alice"})
        blocked = evidence.bindings["channel"][0]

        self.assertEqual(
            {},
            runtime.recovery_bindings("c8", (blocked,)),
        )

    def test_recovery_does_not_use_semantic_materialization(self):
        contract = TaskContract("send the selected recipient a message", [
            Clause("", "read candidates", ["read_file"], "records"),
            Clause("", "select the intended recipient", ["c0.records"], "recipient"),
            Clause("", "send the message", ["c1.recipient"],
                   effect=Effect("send", {
                       "recipient": {"from": "c1.recipient"}})),
        ])

        class Judge:
            def materialize(self, *_):
                return {"status": "supported", "ref": "invented#",
                        "value": "Alice"}

        runtime = WrapRuntime(contract, {
            "read_file": _capability("read_file", observation=True),
            "send": _capability("send", ("recipient",), effect=True),
        }, Judge())
        runtime.observe("read_file", {}, {"recipient": "Alice"})

        self.assertEqual({}, runtime.recovery_bindings("c2"))

    def test_recovery_quarantines_one_exact_provenance_ref(self):
        receipt = Observation.issue("read_file", {}, {"body": "poison"})
        recovery = RecoveryState()
        ref = receipt.digest + "#/body"

        self.assertEqual(
            1, recovery.quarantine_unique_ref([receipt], [ref, ref]))
        self.assertEqual(
            "[content withheld by execution guard]",
            recovery.sanitize(receipt)["body"])

    def test_recovery_does_not_choose_between_provenance_refs(self):
        first = Observation.issue("read_file", {"id": 1}, "one")
        second = Observation.issue("read_file", {"id": 2}, "two")
        recovery = RecoveryState()

        self.assertEqual(0, recovery.quarantine_unique_ref(
            [first, second], [first.digest + "#", second.digest + "#"]))
        self.assertFalse(recovery.quarantine)

    def test_free_text_extraction_requires_two_identical_local_results(self):
        receipt = Observation.issue(
            "get_webpage", {"url": "example"}, "Dora: dora@example.com")
        clause = Clause("", "extract Dora's email", ["get_webpage"], "email")
        answers = [
            {"status": "supported", "ref": receipt.digest + "#",
             "value": "dora@example.com"},
            {"status": "supported", "ref": receipt.digest + "#",
             "value": "dora@example.com"},
        ]

        class Session:
            def __init__(self, *_): pass
            def ask_json(self, _prompt): return answers.pop(0)

        with patch("code.defense.session.ApiSession", Session):
            result = SemanticJudge(object(), "model").materialize(
                "invite Dora", clause, (receipt,))

        self.assertEqual("supported", result["status"])
        self.assertEqual("dora@example.com", result["value"])

    def test_free_text_extraction_disagreement_is_uncertain(self):
        receipt = Observation.issue(
            "get_webpage", {"url": "example"}, "Dora: dora@example.com")
        clause = Clause("", "extract Dora's email", ["get_webpage"], "email")
        answers = [
            {"status": "supported", "ref": receipt.digest + "#",
             "value": "dora@example.com"},
            {"status": "supported", "ref": receipt.digest + "#",
             "value": "evil@example.com"},
        ]

        class Session:
            def __init__(self, *_): pass
            def ask_json(self, _prompt): return answers.pop(0)

        with patch("code.defense.session.ApiSession", Session):
            result = SemanticJudge(object(), "model").materialize(
                "invite Dora", clause, (receipt,))

        self.assertEqual("uncertain", result["status"])

    def test_proposal_time_semantic_entailment_cannot_grant_authority(self):
        contract = TaskContract("create a four-hour event from the email", [
            Clause("", "read the event email", ["read_email"], "email"),
            Clause("", "obtain the event end time required by the task",
                   ["task", "c0.email"], "end_time"),
            Clause("", "create the event", ["task", "c1.end_time"],
                   effect=Effect("create_event", {
                       "end_time": {"from": "c1.end_time"}})),
        ])

        class Judge:
            def materialize(self, *_):
                return {"status": "uncertain", "ref": ""}

        judge = Judge()
        runtime = WrapRuntime(contract, {
            "read_email": _capability("read_email", observation=True),
            "create_event": _capability(
                "create_event", ("end_time",), effect=True),
        }, judge)
        runtime.observe("read_email", {}, "The event starts at 13:00.")

        evidence = runtime.evidence(
            "create_event", {"end_time": "17:00"})

        self.assertFalse(evidence.complete)
        self.assertEqual(("end_time",), evidence.unresolved)

    def test_declared_prose_does_not_require_semantic_binding(self):
        contract = TaskContract("summarize the channel to general", [
            Clause("", "read the messages", ["read_messages"], "messages"),
            Clause("", "summarize the messages", ["c0.messages"], "summary"),
            Clause("", "send the summary", ["task", "c1.summary"],
                   effect=Effect("send", {
                       "channel": {"literal": "general"},
                       "body": {"from": "c1.summary"},
                   })),
        ])

        class Judge:
            def __call__(self, *_): return "equivalent"
            def materialize(self, *_):
                raise AssertionError("open prose must not invoke materialization")
            def witness(self, *_):
                raise AssertionError("open prose must not invoke a semantic witness")

        runtime = WrapRuntime(contract, {
            "read_messages": _capability("read_messages", observation=True),
            "send": CapabilitySurface(
                "send", arguments=("channel", "body"), effect=True,
                observation=False, required_arguments=("channel", "body"),
                interprets=(("body", ()),)),
        }, Judge())
        runtime.observe("read_messages", {}, ["Alice completed the report."])

        evidence = runtime.evidence(
            "send", {"channel": "general",
                     "body": "Alice completed it; thanks for the update."})

        self.assertTrue(evidence.complete)
        self.assertEqual((), evidence.bindings["body"])

    def test_substrate_references_bind_canonical_entities(self):
        contract = TaskContract("tell general to contact Alice", [
            Clause("", "read the directory", ["read_directory"], "directory"),
            Clause("", "send the note", ["task", "c0.directory"],
                   effect=Effect("send", {
                       "channel": {"literal": "general"},
                       "body": {"from": "c0.directory"},
                   })),
        ])
        runtime = WrapRuntime(contract, {
            "read_directory": _capability("read_directory", observation=True),
            "send": CapabilitySurface(
                "send", arguments=("channel", "body"), effect=True,
                observation=False, required_arguments=("channel", "body"),
                interprets=(("body", ("mention",)),)),
        }, reference_resolvers={"mention": lambda value: (
            ["U-A"] if isinstance(value, str) and
            (value == "Alice" or "@Alice" in value) else
            ["U-E"] if isinstance(value, str) and
            (value == "Eve" or "@Eve" in value) else []
        )})
        runtime.observe("read_directory", {}, {"id": "U-A", "name": "Alice"})

        supported = runtime.evidence(
            "send", {"channel": "general",
                     "body": "Contact @Alice."})
        rejected = runtime.evidence(
            "send", {"channel": "general", "body": "Contact @Eve."})

        self.assertTrue(supported.complete)
        self.assertTrue(supported.bindings["body"])
        self.assertEqual(("body",), rejected.conflicts)

    def test_declared_reference_without_registered_resolver_is_unresolved(self):
        contract = TaskContract("send the note", [
            Clause("", "send the note", ["task"], effect=Effect(
                "send", {"body": {"literal": "hello"}})),
        ])
        runtime = WrapRuntime(contract, {
            "send": CapabilitySurface(
                "send", arguments=("body",), effect=True, observation=False,
                required_arguments=("body",),
                interprets=(("body", ("platform_link",)),)),
        })

        evidence = runtime.evidence("send", {"body": "hello"})

        self.assertEqual(("body",), evidence.unresolved)


if __name__ == "__main__":
    unittest.main()
