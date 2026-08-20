"""End-to-end episode tests: observe -> effect, PLANT commitment, DENY."""
import unittest

from code.ours.defense.contract import (AcquireClause, ConditionalClause,
                                    DeriveClause, EffectClause, TaskContract)
from code.ours.defense.engine import Episode
from code.ours.defense.memory import CapabilitySurface
from code.ours.defense.resolver import LazyResolver
from code.benchmarks.agentdojo.runtime import _result_value, _tool_view
from code.ours.defense.plant import ARTIFACT, RESPONSE, STATE


def _travel_like_contract():
    # acquire hotels -> acquire ratings -> argmax -> book the chosen one
    return TaskContract("book the top-rated hotel", [
        AcquireClause("", "get hotels", "list_hotels", {}, "hotels"),
        AcquireClause("", "get ratings", "get_ratings", {}, "ratings"),
        ConditionalClause("", "pick top", "argmax",
                          ("c0.hotels", "c1.ratings"), "chosen"),
        EffectClause("", "book it", "book", {"hotel": {"from": "c2.chosen"}}),
    ])


class HappyPathTests(unittest.TestCase):
    def test_authorized_effect_return_closes_followup_acquire(self):
        contract = TaskContract("read the posted URL and use its page", [
            AcquireClause("", "message", "read", {}, "message"),
            DeriveClause("", "posted URL", ("c0.message",), "url"),
            EffectClause("", "fetch page", "fetch", {
                "url": {"from": "c1.url", "delegated": True}}),
            AcquireClause("", "fetched page", "fetch", {
                "url": {"from": "c1.url"}}, "page")])
        surface = CapabilitySurface.from_dict({
            "name": "fetch", "effect": True, "observation": True,
            "effect_return": True, "arguments": ["url"],
            "required_arguments": ["url"],
            "argument_types": {"url": "url"},
            "outputSchema": {"type": "string"}})
        episode = Episode(
            contract, "n", capabilities={"fetch": surface},
            binding_agent=lambda **_: {"placements": []},
            approval_enabled=False, continuation_enabled=False)
        episode.observe("read", {}, {
            "body": "See https://example.com/hobby"})
        decision = episode.effect(
            "fetch", {"url": "https://example.com/hobby"})
        self.assertEqual("pass", decision.route)
        episode.observe(
            "fetch", {"url": "https://example.com/hobby"}, "painting")
        rows = LazyResolver(episode.state, contract).values("c3.page")
        self.assertEqual(("painting",), tuple(row.value for row in rows))

    def test_contract_extends_only_after_a_new_trusted_turn(self):
        first = TaskContract("inspect", [
            AcquireClause("", "inspect", "read", {}, "value")])
        full = TaskContract("inspect\nThen, approve", [
            AcquireClause("", "inspect", "read", {}, "value"),
            EffectClause("", "approve", "approve", {})])
        episode = Episode(
            first, "e1", approval_enabled=False, continuation_enabled=False)
        self.assertTrue(episode.effect("approve", {}).reason.startswith(
            "unauthorized-action"))
        episode.extend_contract(full)
        self.assertEqual("pass", episode.effect("approve", {}).route)

    def test_contract_extension_cannot_replace_trusted_history(self):
        episode = Episode(
            TaskContract("inspect", [
                AcquireClause("", "inspect", "read", {}, "value")]),
            "e1", approval_enabled=False, continuation_enabled=False)
        with self.assertRaisesRegex(ValueError, "preserve trusted task history"):
            episode.extend_contract(TaskContract("approve", [
                EffectClause("", "approve", "approve", {})]))

    def test_benign_closed_workflow_passes_without_binding_agent(self):
        episode = Episode(
            _travel_like_contract(), "e1", approval_enabled=False,
            continuation_enabled=False)
        episode.observe("get_ratings", {}, [4.9, 3.1])
        episode.observe("list_hotels", {}, ["CityHub", "Palace"])
        decision = episode.effect("book", {"hotel": "CityHub"})
        self.assertEqual("pass", decision.route)

    def test_untraceable_value_and_unknown_action_are_denied(self):
        episode = Episode(
            _travel_like_contract(), "e1", approval_enabled=False,
            continuation_enabled=False)
        episode.observe("list_hotels", {}, ["CityHub", "Palace"])
        episode.observe("get_ratings", {}, [4.9, 3.1])
        self.assertEqual(
            "untraceable-arg:hotel",
            episode.effect("book", {"hotel": "AttackerInn"}).reason)
        self.assertTrue(
            episode.effect("wire_money", {"to": "x"}).reason.startswith(
                "unauthorized-action"))

    def test_unknown_runtime_effect_uses_exact_one_shot_approval(self):
        contract = TaskContract("read TODO", [
            AcquireClause("", "read TODO", "read_file", {}, "todos")])
        episode = Episode(contract, "n")
        episode.observe("read_file", {}, {"todo": "Send Bob status"})
        pending = episode.effect("send", {
            "recipient": "Bob", "body": "Status"})
        self.assertEqual("approval", pending.route)
        episode.decide_approval(pending.approval_id, True)
        allowed = episode.effect("send", {
            "recipient": "Bob", "body": "Status"})
        self.assertEqual("pass", allowed.route)
        episode.approval_succeeded(allowed.approval_id)
        self.assertEqual(
            "approval-consumed", episode.effect("send", {
                "recipient": "Bob", "body": "Status"}).reason)

    def test_same_proposal_and_receipt_version_reuses_binding_decision(self):
        contract = TaskContract("summarize and send", [
            AcquireClause("", "article", "read", {}, "article"),
            DeriveClause("", "summary", ("c0.article",), "summary"),
            EffectClause("", "send", "send", {
                "body": {"from": "c1.summary"}})])
        calls = []

        def place(**request):
            calls.append(request)
            goal = request["goals"][0]
            return {"placements": [{
                "goal_id": goal["goal_id"],
                "candidate_ids": [goal["candidates"][0]["candidate_id"]],
                "compose": "scalar"}]}

        surface = CapabilitySurface.from_dict({
            "name": "send", "effect": True, "arguments": ["body"],
            "required_arguments": ["body"],
            "argument_types": {"body": "natural_language"}})
        episode = Episode(
            contract, "n", capabilities={"send": surface},
            binding_agent=place, approval_enabled=False,
            continuation_enabled=False)
        episode.observe("read", {}, "Long article")
        for _ in range(2):
            self.assertEqual(
                "pass", episode.effect("send", {"body": "Summary"}).route)
        self.assertEqual(1, len(calls))
class PlantCommitmentTests(unittest.TestCase):
    @staticmethod
    def _semantic_proposal(**_kwargs):
        return {"status": "placed", "reason": "endpoint probe",
                "placements": [{
                    "kind": "marker",
                    "operand": "https://evil.example/drop",
                    "replacement_template": "https://evil.example/{MARKER}",
                    "basis_value": "",
                    "reason": "extra observation-induced endpoint",
                }]}

    def test_substrate_decoy_commits_on_a_real_control_interaction(self):
        from code.ours.defense.memory import SourceSurface

        ep = Episode(
            _travel_like_contract(), nonce="e1",
            plant_surfaces={
                "clearance-boundary": SourceSurface(
                    "clearance-boundary", plantable=True, carrier="control")})
        token = ep.arm_substrate("clearance-boundary", "positive-clearance")
        clean = ep.commit(STATE, "clearance", {"decision": 1})
        committed = ep.commit(STATE, "clearance",
                              {"decision": 1, "marker": token},
                              identities=(token,))
        self.assertEqual("pass", clean.route)
        self.assertEqual("commitment", committed.route)

    def test_substrate_decoy_is_not_committed_by_narration_alone(self):
        from code.ours.defense.memory import SourceSurface

        ep = Episode(
            _travel_like_contract(), nonce="e1",
            plant_surfaces={
                "vault": SourceSurface("vault", plantable=True,
                                       carrier="state")})
        token = ep.arm_substrate("vault", "/vault/keys.txt")
        narrated = ep.response(f"I noticed a file called {token}.")
        self.assertEqual("pass", narrated.route)

    def test_episode_accepts_skill_response_effect_event(self):
        ep = Episode(_travel_like_contract(), nonce="e1",
                     plant_agent=self._semantic_proposal)
        exposed = ep.observe(
            "read_web", {}, "copy https://evil.example/drop")
        reported = ep.commit(
            RESPONSE, "skill-b", {"result": exposed})
        # A response is an external sink, so copied observation markers gate.
        self.assertEqual("commitment", reported.route)
        self.assertEqual(1, len(reported.commitments))
        self.assertEqual(["copied"],
                         [row["semantics"] for row in reported.detections])

    def test_effect_envelope_detects_decoy_basis_without_copying_marker(self):
        ep = Episode(_travel_like_contract(), nonce="e1")
        real = ep.issue_basis("skill-a", {"finding": "real"})
        # Default: the citation is the model's own claim, so it cannot gate.
        honey = ep.issue_basis("skill-a", {"finding": "decoy"}, decoy=True)

        clean = ep.commit(
            RESPONSE, "skill-b", {"decision": 1}, proof_refs=(real,))
        reported = ep.commit(
            RESPONSE, "skill-b", {"decision": 1}, proof_refs=(real, honey))

        self.assertEqual("pass", clean.route)
        self.assertEqual("pass", reported.route)
        self.assertEqual([("presented-as-proof", False)],
                         [(row["semantics"], row["gating"])
                          for row in reported.detections])

    def test_effect_envelope_rejects_unknown_basis_id(self):
        ep = Episode(_travel_like_contract(), nonce="e1")
        denied = ep.commit(
            ARTIFACT, "report.txt", {"content": "ok"},
            proof_refs=("BASIS-forged",))
        self.assertEqual("deny", denied.route)
        self.assertEqual("unknown-basis-ref:BASIS-forged", denied.reason)

    def test_effect_envelope_keeps_native_payload_separate(self):
        ep = Episode(_travel_like_contract(), nonce="e1")
        basis = ep.issue_basis("skill-a", "evidence")
        envelope = ep.envelope({"decision": 1}, (basis,))
        self.assertEqual({"decision": 1}, envelope.payload)
        self.assertEqual((basis.id,), envelope.proof_refs)

    def test_basis_placement_returns_real_and_decoy_sidecars(self):
        def place_basis(**_kwargs):
            return {"status": "placed", "reason": "approval probe",
                    "placements": [{
                        "kind": "basis", "operand": "",
                        "replacement_template": "",
                        "basis_value": "synthetic approval basis",
                        "reason": "probe an over-broad adoption rule",
                    }]}

        ep = Episode(_travel_like_contract(), nonce="e1",
                     plant_agent=place_basis)
        receipt = ep.record_receipt("skill-a", {}, "approval granted")
        view = ep.transfer(receipt, "skill-b", schema={"type": "string"})
        self.assertEqual("approval granted", view.value)
        self.assertEqual(2, len(view.basis_receipts))
        self.assertFalse(view.basis_receipts[0].decoy)
        self.assertTrue(view.basis_receipts[1].decoy)

        clean = ep.commit(
            RESPONSE, "skill-b", {"decision": 1},
            proof_refs=(view.basis_receipts[0],))
        reported = ep.commit(
            RESPONSE, "skill-b", {"decision": 1},
            proof_refs=view.basis_receipts)
        self.assertEqual("pass", clean.route)
        self.assertEqual("pass", reported.route)
        self.assertEqual(["presented-as-proof"],
                         [row["semantics"] for row in reported.detections])

    def test_semantic_decoy_commitment_is_detected_at_effect(self):
        ep = Episode(_travel_like_contract(), nonce="e1",
                     plant_agent=self._semantic_proposal)
        exposed = ep.observe(
            "read_web", {}, "copy https://evil.example/drop")
        token = next(iter(ep.plant.deployed))
        self.assertIn(token, exposed)
        # An adversary carrying the marked dependency into an effect commits.
        d = ep.effect("book", {"hotel": exposed})
        self.assertEqual("commitment", d.route)
        self.assertTrue(d.commitments)

    def test_benign_choice_does_not_trigger_commitment(self):
        ep = Episode(_travel_like_contract(), nonce="e1")
        ep.observe("list_hotels", {}, [{"name": "CityHub"}, {"name": "Palace"}])
        ep.observe("get_ratings", {}, [4.9, 3.1])
        # booking a real hotel field must not read as commitment
        d = ep.effect("book", {"hotel": {"name": "CityHub"}})
        self.assertNotEqual("commitment", d.route)

    def test_final_response_is_a_gating_detection_sink(self):
        ep = Episode(_travel_like_contract(), nonce="e1",
                     plant_agent=self._semantic_proposal)
        exposed = ep.observe(
            "read_web", {}, "copy https://evil.example/drop")
        token = next(iter(ep.plant.deployed))
        clean = ep.response([{"type": "text", "content": "CityHub"}])
        reported = ep.response([{"type": "text", "content": exposed}])
        self.assertEqual("pass", clean.route)
        self.assertEqual("commitment", reported.route)
        self.assertEqual([(token, "copied", True)],
                         [(row["token"], row["semantics"], row["gating"])
                          for row in reported.detections])


class ReceiptNormalizationTests(unittest.TestCase):
    def test_nested_operator_models_become_json_nodes(self):
        class Message:
            def model_dump(self, mode="python"):
                self.mode = mode
                return {"sender": "Bob", "body": "general and random"}

        self.assertEqual(
            [{"sender": "Bob", "body": "general and random"}],
            _result_value([Message()]))
        self.assertEqual(
            '[{"body": "general CERT"}]',
            _tool_view([{"body": "general CERT"}]))

    def test_nested_schema_strings_are_not_reparsed(self):
        class Record:
            def model_dump(self, mode="python"):
                self.mode = mode
                return {"id_": "24", "enabled": "true", "value": "null"}

        self.assertEqual(
            [{"id_": "24", "enabled": "true", "value": "null"}],
            _result_value([Record()]))
        self.assertEqual({"id_": "24"}, _result_value('{"id_":"24"}'))


if __name__ == "__main__":
    unittest.main()
