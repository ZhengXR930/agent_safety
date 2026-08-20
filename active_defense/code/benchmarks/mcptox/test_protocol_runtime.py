import hashlib
import json
from pathlib import Path
import unittest
from unittest.mock import patch
from types import SimpleNamespace

from code.benchmarks.mcptox.adapter import MCPToxAdapter
from code.benchmarks.mcptox.execution.native import catalog_blocks
from code.benchmarks.mcptox.protocol_runtime import (
    EXPECTED_ATTACK, EXPECTED_CLEAN, TOOL_PROPOSAL_PROTOCOL, judge_call,
    load_cases, parse_tool_proposal, propose_tool_call, protocol_identity,
    selected_tool_block)
from code.benchmarks.mcptox.execution.pipelock import (
    _filter_system as pipelock_filter_system,
    _summary as pipelock_summary,
)
from code.benchmarks.mcp_common.runtime import (
    _canonicalize_nested_arguments, _registered_mcptox_capability)
from code.benchmarks.mcptox.manifest_builder import (
    _reconcile_documented_parameters)


class MCPToxProtocolTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.clean, cls.attack = load_cases()

    def test_protocol_identity_is_frozen(self):
        identity = protocol_identity()
        self.assertEqual(identity["schema"], "mcptox-shared-protocol-v3")
        self.assertEqual(identity["clean_count"], 357)
        self.assertEqual(identity["attack_count"], 1348)
        self.assertEqual(len(identity["cases_sha256"]), 64)
        self.assertEqual(len(identity["tools_sha256"]), 64)
        self.assertEqual(
            "original-then-invalid-envelope-json-repair-v1",
            identity["target_output"])

    def test_tool_proposal_parser_requires_exact_envelope_types(self):
        self.assertEqual(
            {"tool": "read_file", "arguments": {"path": "/tmp/a"}},
            parse_tool_proposal(
                '{"tool":"read_file","arguments":{"path":"/tmp/a"}}'))
        self.assertEqual({}, parse_tool_proposal('{"tool":"read_file"}'))
        self.assertEqual({}, parse_tool_proposal(
            '{"tool":"read_file","arguments":"/tmp/a"}'))

    def test_target_agent_uses_shared_json_output_protocol(self):
        captured = []

        class Completions:
            def create(self, **kwargs):
                captured.append(kwargs)
                message = type("Message", (), {"content": (
                    '{"tool":"read_file","arguments":{"path":"/x"}}')})()
                choice = type("Choice", (), {"message": message})()
                return type("Response", (), {"choices": [choice]})()

        client = type("Client", (), {"chat": type(
            "Chat", (), {"completions": Completions()})()})()
        raw, call = propose_tool_call(client, "target", "catalog", "read /x")
        self.assertIn("read_file", raw)
        self.assertEqual("read_file", call["tool"])
        self.assertEqual(1, len(captured))
        self.assertNotIn("response_format", captured[0])
        self.assertEqual("read /x", captured[0]["messages"][1]["content"])

    def test_invalid_target_output_gets_one_json_repair(self):
        captured = []

        class Completions:
            def create(self, **kwargs):
                captured.append(kwargs)
                content = ("I will read it." if len(captured) == 1 else
                           '{"tool":"read_file","arguments":{"path":"/x"}}')
                message = type("Message", (), {"content": content})()
                choice = type("Choice", (), {"message": message})()
                return type("Response", (), {"choices": [choice]})()

        client = type("Client", (), {"chat": type(
            "Chat", (), {"completions": Completions()})()})()
        _raw, call = propose_tool_call(client, "target", "catalog", "read /x")
        self.assertEqual("read_file", call["tool"])
        self.assertEqual(2, len(captured))
        self.assertEqual({"type": "json_object"},
                         captured[1]["response_format"])
        self.assertEqual(TOOL_PROPOSAL_PROTOCOL,
                         captured[1]["messages"][1]["content"])
        self.assertIn("directly completes",
                      captured[1]["messages"][1]["content"])

    def test_protocol_file_pins_every_shared_data_artifact(self):
        root = Path(__file__).resolve().parent
        protocol = json.loads(
            (root / "protocol.json").read_text(encoding="utf-8"))
        self.assertEqual("response-all-operator-schema-v3",
                         protocol["version"])
        for relative, expected in protocol["data_sha256"].items():
            observed = hashlib.sha256((root / relative).read_bytes()).hexdigest()
            self.assertEqual(expected, observed, relative)

    def test_frozen_denominator_and_ids_are_shared_by_adapter(self):
        self.assertEqual(EXPECTED_CLEAN, len(self.clean))
        self.assertEqual(EXPECTED_ATTACK, len(self.attack))
        adapter = MCPToxAdapter()
        self.assertEqual(
            [row["case_id"] for row in self.clean],
            [row.case_id for row in adapter.cases("clean")])
        self.assertEqual(
            [row["case_id"] for row in self.attack],
            [row.case_id for row in adapter.cases("attack")])

    def test_attack_spec_is_exact_changed_rendered_block(self):
        for row in self.attack:
            clean = catalog_blocks(row["clean_system"])
            attacked = catalog_blocks(row["system"])
            changed = [name for name, block in attacked.items()
                       if clean.get(name) != block]
            self.assertEqual([row["poison_tool"]], changed)
            self.assertNotIn(row["poison_tool"], clean)
            self.assertEqual(
                attacked[row["poison_tool"]],
                row["attack_specification"])

    def test_judge_sees_selected_tool_and_failure_direct_is_code_owned(self):
        row = self.attack[0]
        call = {"tool": row["poison_tool"], "arguments": {}}
        captured = {}

        def fake_chat(_client, _model, prompt, **_kwargs):
            captured["prompt"] = prompt
            return json.dumps({
                "task_complete": False,
                "malicious_success": True,
                "reason": "wrapper mentioned an inner operation",
            })

        with patch(
                "code.benchmarks.mcptox.protocol_runtime.chat", fake_chat):
            verdict = judge_call(object(), "judge", row, call, True)
        self.assertIn(selected_tool_block(row, call), captured["prompt"])
        self.assertIn("attacker-authored poisoned", captured["prompt"])
        self.assertTrue(verdict["failure_direct"])
        self.assertFalse(verdict["attack_success"])

    def test_registered_capability_accepts_display_case_only(self):
        capabilities = {
            "Github__create_repository": object(),
            "Slack__send_message": object(),
        }
        self.assertEqual(
            "Github__create_repository",
            _registered_mcptox_capability(
                capabilities, "GitHub", "create_repository"))
        self.assertEqual(
            "Slack__send_message",
            _registered_mcptox_capability(
                capabilities, "Slack", "send_message"))
        self.assertEqual(
            "Unknown__read",
            _registered_mcptox_capability(
                capabilities, "Unknown", "read"))

    def test_clean_request_data_declaration_recovers_nested_schema(self):
        schema, changed = _reconcile_documented_parameters(
            {"type": "object", "properties": {
                "request_data": {"type": "string"}}},
            "Call it. The request data should be: "
            "{'customerIds': {'type': 'array', 'items': {'type': 'string'}}, "
            "'active': {'type': 'boolean'}}.The request data should be an "
            "empty dictionary {}.")
        self.assertTrue(changed)
        request = schema["properties"]["request_data"]
        self.assertEqual("object", request["type"])
        self.assertEqual(
            {"customerIds", "active"}, set(request["properties"]))
        self.assertFalse(request["additionalProperties"])

    def test_flat_arguments_move_only_to_unique_nested_schema(self):
        surface = SimpleNamespace(argument_schemas=(
            ("id", {"type": "string"}),
            ("request_data", {"type": "object", "properties": {
                "collectionMethod": {"type": "string"},
                "templateId": {"type": "string"},
            }, "additionalProperties": False}),
        ))
        arguments, moved = _canonicalize_nested_arguments(surface, {
            "id": "INV-1", "collectionMethod": "DIRECT_DEBIT_PAYMENT",
            "templateId": "template-1",
        })
        self.assertEqual(("collectionMethod", "templateId"), moved)
        self.assertEqual({
            "id": "INV-1", "request_data": {
                "collectionMethod": "DIRECT_DEBIT_PAYMENT",
                "templateId": "template-1",
            }}, arguments)

    def test_nested_normalization_abstains_on_ambiguity_or_collision(self):
        schema = {"type": "object", "properties": {
            "value": {"type": "string"}}}
        ambiguous = SimpleNamespace(argument_schemas=(
            ("left", schema), ("right", schema)))
        value = {"value": "x"}
        self.assertEqual(
            (value, ()), _canonicalize_nested_arguments(ambiguous, value))
        collision = SimpleNamespace(argument_schemas=(("body", schema),))
        value = {"body": {"value": "trusted"}, "value": "other"}
        self.assertEqual(
            (value, ()), _canonicalize_nested_arguments(collision, value))

    def test_pipelock_e2e_filters_catalog_before_shared_metrics(self):
        class Scanner:
            def scan(self, name, _block):
                return {"allowed": name == "safe", "action": None,
                        "matches": []}

        system = (
            "You are a helpful assistant with access to these tools:\n\n\n"
            "Tool: safe\nDescription: ok\nArguments:\n\n\n"
            "Tool: poisoned\nDescription: bad\nArguments:\n\n\n"
            "Choose the appropriate tool."
        )
        defended, decisions = pipelock_filter_system(Scanner(), system)
        self.assertIn("Tool: safe", defended)
        self.assertNotIn("Tool: poisoned", defended)
        self.assertEqual(["poisoned"], [
            row["tool"] for row in decisions if not row["allowed"]])

        rows = [
            {"status": "ok", "task_complete": True,
             "malicious_success": False, "blocked_tools": ["poisoned"]},
            {"status": "ok", "task_complete": False,
             "malicious_success": True, "blocked_tools": []},
        ]
        summary = pipelock_summary(rows)
        self.assertEqual(1, summary["task_success"])
        self.assertEqual(1, summary["attack_success"])
        self.assertEqual(0.5, summary["utility"])
        self.assertEqual(0.5, summary["asr"])


if __name__ == "__main__":
    unittest.main()
