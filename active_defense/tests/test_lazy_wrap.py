import json
import unittest
from pathlib import Path
from unittest.mock import patch

from code.defense.contract import AcquireClause, ConditionalClause, EffectClause
from code.defense.engine import Engine
from code.defense.auditor import RecoveryState
from code.defense.memory import CapabilitySurface
from code.defense.plant import Plant, PlantRuntime, replace_observation
from code.defense.taskcontractor import Clause, Effect, TaskContract
from code.defense.wrap import Observation, BindingPlacementAgent, WrapRuntime


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
        self.assertEqual((), runtime._authority_observations())
        self.assertFalse(hasattr(runtime, "_outputs"))

    def test_observation_binding_allows_omitted_optional_literal_positions(self):
        contract = TaskContract("search for a watch", [
            Clause("c0", "search products", ["search"], "products",
                   arguments={"query": {"literal": "watch"},
                              "brand": {"literal": None}}),
        ])
        runtime = WrapRuntime(contract, {
            "search": CapabilitySurface(
                "search", arguments=("query", "brand"), observation=True,
                required_arguments=("query",)),
        })

        receipt = runtime.observe("search", {"query": "watch"}, [{"id": "P1"}])

        self.assertIn(receipt.digest, runtime._bound_receipts["c0"])
        self.assertEqual((receipt,), runtime._authority_observations())

    def test_lazy_wrap_excludes_same_source_receipt_bound_to_wrong_clause_instance(self):
        contract = TaskContract("open the URL from general", [
            Clause("c0", "read general", ["read_channel_messages"], "messages",
                   arguments={"channel": {"literal": "general"}}),
            Clause("c1", "extract the URL from general",
                   ["task", "c0.messages"], "url"),
            Clause("c2", "open that URL", ["c1.url"],
                   effect=Effect("get_webpage", {"url": {"from": "c1.url"}})),
        ])
        seen_receipts = []
        class Agent:
            def place(self, task, contract, action, arguments, requests, receipts):
                seen_receipts.extend(receipts)
                return {"status": "uncertain", "bindings": []}
        runtime = WrapRuntime(contract, {
            "read_channel_messages": _capability(
                "read_channel_messages", ("channel",), observation=True),
            "get_webpage": _capability(
                "get_webpage", ("url",), effect=True, observation=True),
        }, Agent())
        good = runtime.observe(
            "read_channel_messages", {"channel": "general"},
            [{"body": "Article: good.example"}])
        evil = runtime.observe(
            "read_channel_messages", {"channel": "random"},
            [{"body": "Article: evil.example"}])

        result = runtime.evidence("get_webpage", {"url": "evil.example"})

        self.assertEqual(("url",), result.unresolved)
        self.assertEqual({good.digest}, {item.digest for item in seen_receipts})
        self.assertNotIn(evil.digest, runtime._bound_receipts.get("c0", set()))
        self.assertEqual(["c0"], [item.clause_id for item in runtime.receipt_bindings])

    def test_passed_dynamic_acquisition_call_binds_its_exact_return(self):
        contract = TaskContract("read the selected file", [
            Clause("c0", "list files", ["list_files"], "files", arguments={}),
            Clause("c1", "read a listed file", ["c0.files", "read_file"],
                   "content", arguments={"path": {"from": "c0.files"}}),
        ])
        runtime = WrapRuntime(contract, {
            "list_files": _capability("list_files", observation=True),
            "read_file": _capability(
                "read_file", ("path",), effect=True, observation=True),
        })
        runtime.observe("list_files", {}, ["/allowed.txt"])
        admitted = runtime.intermediate_evidence(
            "read_file", {"path": "/allowed.txt"})
        rejected = runtime.intermediate_evidence(
            "read_file", {"path": "/evil.txt"})
        self.assertTrue(admitted.complete)
        self.assertFalse(rejected.complete)
        self.assertTrue(runtime.admit_observation_call(
            "read_file", {"path": "/allowed.txt"}, admitted.clause, "call-1"))
        allowed = runtime.observe(
            "read_file", {"path": "/allowed.txt"}, "trusted content",
            call_id="call-1")
        evil = runtime.observe(
            "read_file", {"path": "/evil.txt"}, "unbound content")

        self.assertIn(allowed.digest, runtime._bound_receipts["c1"])
        self.assertNotIn(evil.digest, runtime._bound_receipts["c1"])

        replay = runtime.observe(
            "read_file", {"path": "/allowed.txt"}, "later mutable content",
            call_id="call-1")
        self.assertNotIn(replay.digest, runtime._bound_receipts["c1"])
        self.assertEqual({}, runtime._pending_observation_calls)

    def test_new_same_call_receipt_supersedes_old_authority_version(self):
        contract = TaskContract("send current value", [
            Clause("c0", "read current value", ["read"], "value", arguments={}),
            Clause("c1", "send current value", ["c0.value"],
                   effect=Effect("send", {"body": {"from": "c0.value"}})),
        ])
        runtime = WrapRuntime(contract, {
            "read": _capability("read", observation=True),
            "send": _capability("send", ("body",), effect=True),
        })
        old = runtime.observe("read", {}, "old")
        self.assertTrue(runtime.evidence("send", {"body": "old"}).complete)
        new = runtime.observe("read", {}, "new")
        self.assertIn(old.digest, runtime._superseded_receipts)
        self.assertFalse(runtime.evidence("send", {"body": "old"}).complete)
        self.assertTrue(runtime.evidence("send", {"body": "new"}).complete)
        self.assertNotEqual(old.digest, new.digest)

    def test_datetime_literal_equivalence_requires_attested_argument_format(self):
        contract = TaskContract("create event at noon", [
            Clause("c0", "create event", ["task"],
                   effect=Effect("create_event", {
                       "start_time": {"literal": "2024-05-19T12:00:00"}})),
        ])
        attested = CapabilitySurface(
            "create_event", arguments=("start_time",), effect=True,
            required_arguments=("start_time",),
            argument_schemas=(("start_time", {
                "type": "string", "format": "date-time"}),))
        runtime = WrapRuntime(contract, {"create_event": attested})
        accepted = runtime.evidence(
            "create_event", {"start_time": "2024-05-19 12:00"})
        self.assertTrue(accepted.complete)

        unattested = _capability("create_event", ("start_time",), effect=True)
        denied = WrapRuntime(contract, {"create_event": unattested}).evidence(
            "create_event", {"start_time": "2024-05-19 12:00"})
        self.assertEqual(("start_time",), denied.conflicts)

    def test_datetime_leaf_equivalence_uses_attested_effect_schema(self):
        contract = TaskContract("copy the observed event time", [
            Clause("c0", "read event", ["read_event"], "event", arguments={}),
            Clause("c1", "create matching event", ["c0.event"],
                   effect=Effect("create_event", {
                       "start_time": {"from": "c0.event"}})),
        ])
        runtime = WrapRuntime(contract, {
            "read_event": _capability("read_event", observation=True),
            "create_event": CapabilitySurface(
                "create_event", arguments=("start_time",), effect=True,
                required_arguments=("start_time",),
                argument_schemas=(("start_time", {
                    "type": "string", "format": "date-time"}),)),
        })
        runtime.observe("read_event", {}, {
            "start_time": "2024-05-19T12:00:00"})
        result = runtime.evidence(
            "create_event", {"start_time": "2024-05-19 12:00"})
        self.assertTrue(result.complete)

    def test_authorized_effect_return_can_bind_downstream_receipt_clause(self):
        contract = TaskContract("create and share a file", [
            Clause("c0", "create file", ["task"],
                   effect=Effect("create_file", {
                       "filename": {"literal": "notes.txt"},
                       "content": {"literal": "hello"}})),
            Clause("c1", "capture the authorized create result", ["create_file"],
                   "created_file", arguments={
                       "filename": {"literal": "notes.txt"},
                       "content": {"literal": "hello"}}),
            Clause("c2", "share created file", ["c1.created_file", "task"],
                   effect=Effect("share_file", {
                       "file_id": {"from": "c1.created_file"},
                       "email": {"literal": "user@example.com"}})),
        ])
        runtime = WrapRuntime(contract, {
            "create_file": CapabilitySurface(
                "create_file", arguments=("filename", "content"), effect=True,
                observation=True, required_arguments=("filename", "content"),
                output_schema={"type": "object", "properties": {
                    "id": {"type": "string"}, "filename": {"type": "string"}},
                    "required": ["id", "filename"]}),
            "share_file": _capability(
                "share_file", ("file_id", "email"), effect=True),
        })
        self.assertTrue(runtime.has_effect_gate("create_file"))
        self.assertTrue(runtime.evidence("create_file", {
            "filename": "notes.txt", "content": "hello"}).complete)
        self.assertTrue(runtime.admit_effect_return("create_file", {
            "filename": "notes.txt", "content": "hello"}, "effect-1", "c0"))
        receipt = runtime.observe("create_file", {
            "filename": "notes.txt", "content": "hello"},
            {"id": "file-7", "filename": "notes.txt"}, call_id="effect-1")
        self.assertIn(receipt.digest, runtime._bound_receipts["c1"])
        self.assertTrue(runtime.evidence("share_file", {
            "file_id": "file-7", "email": "user@example.com"}).complete)

    def test_prior_committed_return_is_an_alternative_later_role_witness(self):
        contract = TaskContract("create and share the created file", [
            Clause("c0", "create notes", ["task"], effect=Effect(
                "create_file", {"filename": {"literal": "notes.txt"},
                                "content": {"literal": "hello"}})),
            Clause("c1", "search for the created file", ["search_file"],
                   "files", arguments={"filename": {"literal": "notes.txt"}}),
            Clause("c2", "extract the created file identifier", ["c1.files"],
                   "created_file_id"),
            Clause("c3", "share the created file", ["c2.created_file_id", "task"],
                   effect=Effect("share_file", {
                       "file_id": {"from": "c2.created_file_id"},
                       "email": {"literal": "user@example.com"}})),
        ])
        capabilities = {
            "create_file": CapabilitySurface(
                "create_file", arguments=("filename", "content"), effect=True,
                observation=True, required_arguments=("filename", "content"),
                output_schema={"type": "object", "properties": {
                    "id_": {"type": "string"}}, "required": ["id_"]}),
            "search_file": _capability(
                "search_file", ("filename",), observation=True),
            "share_file": _capability(
                "share_file", ("file_id", "email"), effect=True),
        }
        agent = BindingPlacementAgent(object(), "model")
        runtime = WrapRuntime(contract, capabilities, agent)
        create_args = {"filename": "notes.txt", "content": "hello"}
        create_evidence = runtime.evidence("create_file", create_args)
        self.assertTrue(create_evidence.complete)
        self.assertTrue(runtime.bind_effect(create_evidence, create_args, "create-1"))
        self.assertTrue(runtime.admit_effect_return(
            "create_file", create_args, "create-1", "c0"))
        receipt = runtime.observe(
            "create_file", create_args, {"id_": "file-7"}, call_id="create-1")

        def place(_task, _contract, action, arguments, requests, receipts):
            self.assertEqual("share_file", action)
            self.assertEqual("file-7", arguments["file_id"])
            self.assertIn(receipt.digest, {item.digest for item in receipts})
            source = next(row["source"] for row in requests
                          if row["source"] == "c2.created_file_id")
            return {"status": "placed", "bindings": [{
                "source": source, "value": "file-7",
                "refs": [receipt.digest + "#/id_"],
                "root_ref": receipt.digest + "#/id_",
                "operation": "replayed-proof"}]}

        with patch.object(agent, "place", side_effect=place) as placement:
            result = runtime.evidence("share_file", {
                "file_id": "file-7", "email": "user@example.com"})
        self.assertTrue(result.complete)
        self.assertEqual((receipt.digest + "#/id_",),
                         result.provenance.arguments["file_id"].inputs)
        placement.assert_called_once()

    def test_effect_return_does_not_repeat_already_passed_semantic_arguments(self):
        contract = TaskContract("create and share derived content", [
            Clause("c0", "derive content", ["task"], "content"),
            Clause("c1", "create", ["c0.content"], effect=Effect(
                "create_file", {"filename": {"literal": "notes.txt"},
                                "content": {"from": "c0.content"}})),
            Clause("c2", "capture", ["create_file", "c0.content"],
                   "created", arguments={"filename": {"literal": "notes.txt"},
                                         "content": {"from": "c0.content"}}),
            Clause("c3", "share", ["c2.created"], effect=Effect(
                "share_file", {"file_id": {"from": "c2.created"},
                               "email": {"literal": "user@example.com"}})),
        ])
        runtime = WrapRuntime(contract, {
            "create_file": CapabilitySurface(
                "create_file", arguments=("filename", "content"), effect=True,
                observation=True, effect_return=True,
                output_schema={"type": "object", "properties": {
                    "id_": {"type": "string"}}, "required": ["id_"]}),
            "share_file": _capability(
                "share_file", ("file_id", "email"), effect=True),
        })
        args = {"filename": "notes.txt", "content": "derived at runtime"}
        self.assertTrue(runtime.admit_effect_return(
            "create_file", args, "effect-dynamic", "c1"))
        receipt = runtime.observe(
            "create_file", args, {"id_": "file-9"}, call_id="effect-dynamic")
        self.assertIn(("c2", receipt.digest), runtime._effect_return_receipts)
        self.assertTrue(runtime.evidence("share_file", {
            "file_id": "file-9", "email": "user@example.com"}).complete)

    def test_output_schema_mismatch_is_visible_but_never_bound(self):
        contract = TaskContract("read records", [
            Clause("c0", "read records", ["read"], "records", arguments={}),
        ])
        runtime = WrapRuntime(contract, {
            "read": CapabilitySurface(
                "read", observation=True, required_arguments=(),
                output_schema={"type": "array", "items": {"type": "string"}}),
        })
        receipt = runtime.observe("read", {}, {"unexpected": "object"})
        self.assertIn(receipt, runtime.observations)
        self.assertIn(receipt.digest, runtime._invalid_schema_receipts)
        self.assertNotIn(receipt.digest, runtime._bound_receipts.get("c0", set()))

    def test_quarantine_removes_node_from_wrap_authority(self):
        contract = TaskContract("send the selected value", [
            Clause("c0", "read values", ["read"], "values", arguments={}),
            Clause("c1", "send selected value", ["c0.values"],
                   effect=Effect("send", {"body": {"from": "c0.values"}})),
        ])
        runtime = WrapRuntime(contract, {
            "read": _capability("read", observation=True),
            "send": _capability("send", ("body",), effect=True),
        })
        receipt = runtime.observe("read", {}, {"body": "evil", "safe": "ok"})
        self.assertTrue(runtime.evidence("send", {"body": "evil"}).complete)
        runtime.quarantine_refs((receipt.digest + "#/body",))
        denied = runtime.evidence("send", {"body": "evil"})
        self.assertFalse(denied.complete)
        self.assertEqual(("body",), denied.unresolved)
        authority = next(item for item in runtime._authority_observations()
                         if item.digest == receipt.digest)
        self.assertNotEqual("evil", authority.value["body"])

    def test_runtime_direct_capability_source_cannot_authorize_effect(self):
        contract = TaskContract("send selected value", [
            Clause("c0", "send selected value", ["read"],
                   effect=Effect("send", {"body": {"from": "read"}})),
        ])
        runtime = WrapRuntime(contract, {
            "read": _capability("read", observation=True),
            "send": _capability("send", ("body",), effect=True),
        })
        runtime.observe("read", {}, {"body": "evil"})
        result = runtime.evidence("send", {"body": "evil"})
        self.assertFalse(result.complete)
        self.assertEqual(("body",), result.unresolved)

    def test_effect_time_relations_bind_complete_snapshot(self):
        evidence = self._complete_slack_snapshot().evidence(
            "add_user_to_channel", {"channel": "random", "user": "Alice"})

        self.assertTrue(evidence.complete)
        self.assertTrue(evidence.bindings["channel"])
        self.assertTrue(evidence.bindings["user"])

    def test_closed_path_operators_replay_file_destination(self):
        contract = TaskContract("copy the downloaded file into the repository", [
            AcquireClause("", "acquire downloaded path", "download_path", {}, "path"),
            AcquireClause("", "acquire repository root", "repo_root", {}, "root"),
            ConditionalClause("", "take downloaded basename", "basename",
                              ("c0.path",), "name"),
            ConditionalClause("", "join repository root and basename", "path_join",
                              ("c1.root", "c2.name"), "destination"),
            EffectClause("", "copy file", "copy", {
                "source": {"from": "c0.path"},
                "destination": {"from": "c3.destination"}}),
        ])
        runtime = WrapRuntime(contract, {
            "download_path": _capability("download_path", observation=True),
            "repo_root": _capability("repo_root", observation=True),
            "copy": _capability("copy", ("source", "destination"), effect=True),
        })
        runtime.observe("download_path", {}, "/downloads/app.zip")
        runtime.observe("repo_root", {}, "/repository")
        result = runtime.evidence("copy", {
            "source": "/downloads/app.zip",
            "destination": "/repository/app.zip"})
        self.assertTrue(result.complete)

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
                self.placement_calls = 0

            def place(self, *args):
                self.placement_calls += 1
                return {"status": "uncertain", "bindings": []}

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
        self.assertEqual(0, judge.placement_calls)
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
            def has_slot(self, source_kind):
                return source_kind == "fetch"
            def place(self, source, observation, source_kind, normal_operand_guard=None, placement_context=None):
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
        plant = PlantRuntime(placement_agent=Designer())
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
            def place(self, *_):
                return {"status": "placed", "bindings": []}

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
            def place(self, *_):
                return {"status": "uncertain", "bindings": []}

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
            def place(self, *_):
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
