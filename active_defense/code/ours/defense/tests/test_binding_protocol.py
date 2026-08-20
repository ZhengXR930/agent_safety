"""Public protocol invariants for proposal-time Binding."""
import unittest
from code.ours.defense.binding_agent import BindingAgent
from code.ours.defense.contract import (AcquireClause, ConditionalClause,
                                        DeriveClause, EffectClause,
                                        TaskContract)
from code.ours.defense.engine import Episode
from code.ours.defense.memory import CapabilitySurface


class _CaptureBindingAgent(BindingAgent):
    def __init__(self):
        super().__init__("unused")
        self.prompt = ""

    def _ask_json(self, prompt, tool_schema, validator=None):
        self.prompt = prompt
        return {"placements": []}


class BindingProtocolTests(unittest.TestCase):
    @staticmethod
    def _surface(kind):
        return CapabilitySurface.from_dict({
            "name": "write_file", "effect": True,
            "arguments": ["path"], "required_arguments": ["path"],
            "argument_types": {"path": kind},
        })

    def test_semantic_and_quantified_are_code_compiled_into_public_goal(self):
        contract = TaskContract("inspect sales records", [
            DeriveClause("", "task-scoped inspection helper path", ("task",),
                         "helper_path", True),
            EffectClause("", "write helper", "write_file", {
                "path": {"from": "c0.helper_path"}}),
        ])
        seen = []

        def place(**request):
            seen.extend(request["goals"])
            return {"placements": []}

        episode = Episode(
            contract, "n", capabilities={"write_file": self._surface("path")},
            binding_agent=place, approval_enabled=False,
            continuation_enabled=False)
        episode.effect("write_file", {"path": "inspect_sales.py"})

        self.assertEqual(1, len(seen))
        self.assertEqual("exact_or_semantic", seen[0]["support_mode"])
        self.assertIs(True, seen[0]["quantified"])

    def test_exact_only_manifest_argument_stays_exact(self):
        contract = TaskContract("use account A", [
            DeriveClause("", "task account", ("task",), "account"),
            EffectClause("", "use account", "write_file", {
                "path": {"from": "c0.account"}}),
        ])
        seen = []

        def place(**request):
            seen.extend(request["goals"])
            return {"placements": []}

        episode = Episode(
            contract, "n",
            capabilities={"write_file": self._surface("opaque")},
            binding_agent=place, approval_enabled=False,
            continuation_enabled=False)
        episode.effect("write_file", {"path": "B"})

        self.assertEqual("exact", seen[0]["support_mode"])
        self.assertIs(False, seen[0]["quantified"])

    def test_one_effect_batches_all_unresolved_arguments_once(self):
        contract = TaskContract("write the requested report", [
            DeriveClause("", "task-scoped report path", ("task",),
                         "report_path", True),
            DeriveClause("", "task-scoped report body", ("task",),
                         "report_body", True),
            EffectClause("", "write report", "write_file", {
                "path": {"from": "c0.report_path"},
                "content": {"from": "c1.report_body"},
            }),
        ])
        calls = []

        def place(**request):
            calls.append(request)
            return {"placements": []}

        surface = CapabilitySurface.from_dict({
            "name": "write_file", "effect": True,
            "arguments": ["path", "content"],
            "required_arguments": ["path", "content"],
            "argument_types": {
                "path": "path", "content": "natural_language"},
        })
        episode = Episode(
            contract, "n", capabilities={"write_file": surface},
            binding_agent=place, approval_enabled=False,
            continuation_enabled=False)
        episode.effect("write_file", {
            "path": "report.md", "content": "Quarterly report"})

        self.assertEqual(1, len(calls))
        self.assertEqual(
            {"path", "content"},
            {goal["argument"] for goal in calls[0]["goals"]})

    def test_semantic_goal_keeps_receipt_root_without_recursive_duplication(self):
        contract = TaskContract("append a summary of the report", [
            AcquireClause("", "report", "read", {}, "report"),
            DeriveClause("", "faithful report summary", ("c0.report",),
                         "summary"),
            EffectClause("", "write summary", "write_file", {
                "path": {"literal": "summary.txt"},
                "content": {"from": "c1.summary"},
            }),
        ])
        seen = []

        def place(**request):
            seen.extend(request["goals"])
            goal = request["goals"][0]
            return {"placements": [{
                "goal_id": goal["goal_id"],
                "candidate_ids": [goal["candidates"][0]["candidate_id"]],
                "compose": "scalar"}]}

        surface = CapabilitySurface.from_dict({
            "name": "write_file", "effect": True,
            "arguments": ["path", "content"],
            "required_arguments": ["path", "content"],
            "argument_types": {
                "path": "path", "content": "natural_language"},
        })
        episode = Episode(
            contract, "n", capabilities={"write_file": surface},
            binding_agent=place, approval_enabled=False,
            continuation_enabled=False)
        report = [{"section": index, "text": "x" * 1000}
                  for index in range(30)]
        episode.observe("read", {}, report)
        decision = episode.effect("write_file", {
            "path": "summary.txt", "content": "A faithful summary."})

        self.assertEqual("pass", decision.route)
        self.assertEqual(1, len(seen))
        self.assertEqual("exact_or_semantic", seen[0]["support_mode"])
        self.assertEqual([report], [row["value"]
                                    for row in seen[0]["candidates"]])

    def test_batched_delegation_prefers_closed_subset_replay_root(self):
        contract = TaskContract("append report summary to the named file", [
            AcquireClause("", "report", "read", {}, "report"),
            AcquireClause("", "drive files", "list_files", {}, "files"),
            AcquireClause("", "filename matches", "search", {}, "matches"),
            ConditionalClause("", "bounded candidate set", "coalesce", (
                "c2.matches", "c1.files"), "candidates"),
            DeriveClause("", "named file id", (
                "task", "c3.candidates"), "file_id"),
            DeriveClause("", "faithful report summary", (
                "c0.report",), "summary"),
            EffectClause("", "append", "append", {
                "file_id": {"from": "c4.file_id", "delegated": True},
                "content": {"from": "c5.summary"},
            }),
        ])
        seen = []

        def place(**request):
            seen.extend(request["goals"])
            placements = []
            for goal in request["goals"]:
                placements.append({
                    "goal_id": goal["goal_id"],
                    "candidate_ids": [goal["candidates"][0]["candidate_id"]],
                    "compose": "scalar"})
            return {"placements": placements}

        surface = CapabilitySurface.from_dict({
            "name": "append", "effect": True,
            "arguments": ["file_id", "content"],
            "required_arguments": ["file_id", "content"],
            "argument_types": {
                "file_id": "opaque", "content": "natural_language"},
        })
        episode = Episode(
            contract, "n", capabilities={"append": surface},
            binding_agent=place, approval_enabled=False,
            continuation_enabled=False)
        report = {"body": "long report " + "z" * 30_000}
        episode.observe("read", {}, report)
        episode.observe("list_files", {}, [
            {"id": "9", "body": "x" * 30_000},
            {"id": "10", "body": "y" * 30_000},
        ])
        episode.observe("search", {}, [{"id": "9", "name": "target"}])
        decision = episode.effect("append", {
            "file_id": "9", "content": "A faithful summary."})

        self.assertEqual("pass", decision.route)
        by_argument = {goal["argument"]: goal for goal in seen}
        self.assertEqual(
            [[{"id": "9", "name": "target"}]],
            [row["value"] for row in
             by_argument["file_id"]["candidates"]])
        self.assertEqual(
            [report],
            [row["value"] for row in
             by_argument["content"]["candidates"]])

    def test_agent_prompt_explains_both_code_owned_fields(self):
        agent = _CaptureBindingAgent()
        goal = {
            "goal_id": "g0", "argument": "path", "role": "helper path",
            "mode": "direct", "expected_type": "any",
            "proposed": "inspect_sales.py",
            "support_mode": "exact_or_semantic", "quantified": True,
            "allowed_compose": ["scalar"],
            "candidates": [{"candidate_id": "g0.n0",
                            "value": "inspect sales records"}],
        }
        agent.place_proposal(task="inspect sales records", action="write_file",
                             arguments={"path": "inspect_sales.py"},
                             goals=[goal])
        self.assertIn("support_mode", agent.prompt)
        self.assertIn("exact_or_semantic", agent.prompt)
        self.assertIn("quantified=true", agent.prompt)


if __name__ == "__main__":
    unittest.main()
