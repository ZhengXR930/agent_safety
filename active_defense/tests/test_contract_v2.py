import unittest

from code.defense.contract import (
    AcquireBinding, AcquireClause, ConditionalBinding, ConditionalClause,
    DeriveBinding, DeriveClause, EffectBinding, EffectClause, TaskContract,
)
from code.defense.detector import Detector, ProposalBuffer
from code.defense.engine import Episode
from code.defense.memory import CapabilitySurface, EnvironmentPlan
from code.defense.plant import PlantRuntime
from code.defense.taskcontractor import TaskContractor
from code.defense.wrap import WrapRuntime


class ExplicitContractTests(unittest.TestCase):
    def test_four_clause_json_is_explicit_and_round_trips(self):
        contract = TaskContract("summarize and send", [
            AcquireClause("", "read requested records", "read_records", {}, "records"),
            DeriveClause("", "summarize acquired records", ("c0.records",), "summary"),
            ConditionalClause("", "count acquired records", "count",
                              ("c0.records",), "total"),
            EffectClause("", "send requested summary", "send", {
                "body": {"from": "c1.summary"},
                "total": {"from": "c2.total"},
            }),
        ])
        encoded = contract.to_dict()
        self.assertEqual(
            ["acquire", "derive", "conditional", "effect"],
            [row["type"] for row in encoded["clauses"]])
        self.assertNotIn("sources", repr(encoded))
        self.assertNotIn('"effect":', repr(encoded))
        decoded = TaskContract.from_dict(encoded)
        self.assertEqual(encoded, decoded.to_dict())

    def test_taskcontract_agent_transport_emits_only_explicit_variants(self):
        payload = {"task": "read and send", "clauses": [
            {"id": "c0", "type": "acquire", "instruction": "read records",
             "capability": "read_records", "arguments": {}, "output": "records"},
            {"id": "c1", "type": "effect", "instruction": "send records",
             "action": "send", "arguments": {
                 "body": {"from": "c0.records"}}},
        ]}
        calls = []
        def runner(**kwargs):
            calls.append(kwargs)
            return payload, [{"attempt": 1, "ok": True,
                              "transport": "openai-agents-sdk"}]

        plan = EnvironmentPlan(capabilities={
            "read_records": CapabilitySurface(
                "read_records", observation=True),
            "send": CapabilitySurface(
                "send", arguments=("body",), required_arguments=("body",),
                effect=True),
        })
        contract = TaskContractor(object(), "test-model", runner).extract(
            "read and send", plan)
        self.assertIsInstance(contract.clauses[0], AcquireClause)
        self.assertIsInstance(contract.clauses[1], EffectClause)
        emitted_schema = calls[0]["tool_schema"]["function"]["parameters"]
        variants = emitted_schema["properties"]["clauses"]["items"]["oneOf"]
        self.assertEqual(4, len(variants))
        self.assertEqual(
            {"acquire", "derive", "conditional", "effect"},
            {variant["properties"]["type"]["enum"][0] for variant in variants})
        conditional = next(
            variant for variant in variants
            if variant["properties"]["type"]["enum"] == ["conditional"])
        self.assertIn("singleton",
                      conditional["properties"]["operator"]["enum"])

    def test_explicit_validator_rejects_wrong_variant_fields(self):
        raw = {"task": "read", "clauses": [{
            "id": "c0", "type": "acquire", "instruction": "read",
            "capability": "read_records", "arguments": {}, "output": "records",
            "from": ["task"],
        }]}
        errors = TaskContractor._validate(
            raw, "read", set(), {"task", "read_records"},
            {"read_records": set()}, {"read_records": set()}, set(),
            {"read_records"})
        self.assertIn("clause[0] fields mismatch", errors)

    def test_malformed_explicit_payload_never_downgrades_to_legacy(self):
        payload = {"task": "read", "clauses": [
            {"id": "c0", "type": "acquire", "instruction": "read",
             "capability": "read_records", "arguments": {}, "output": "records"},
            {"id": "c1", "instruction": "malformed mixed row",
             "sources": ["c0.records"], "output": "value"},
        ]}
        contract = TaskContract.from_dict(payload)
        self.assertEqual([], contract.to_dict()["clauses"])

    def test_legacy_decoder_immediately_produces_explicit_variants(self):
        legacy = {"task": "read and send", "clauses": [
            {"id": "c0", "instruction": "read", "sources": ["read_records"],
             "arguments": {}, "output": "records"},
            {"id": "c1", "instruction": "send", "sources": ["c0.records"],
             "effect": {"action": "send", "arguments": {
                 "body": {"from": "c0.records"}}}},
        ]}
        contract = TaskContract.from_dict(legacy)
        self.assertIsInstance(contract.clauses[0], AcquireClause)
        self.assertIsInstance(contract.clauses[1], EffectClause)
        self.assertEqual(["acquire", "effect"], [
            row["type"] for row in contract.to_dict()["clauses"]])


class FourBindingRuntimeTests(unittest.TestCase):
    @staticmethod
    def _contract():
        return TaskContract("summarize, count, and send the records", [
            AcquireClause("", "read requested records", "read_records", {}, "records"),
            DeriveClause("", "derive requested summary", ("c0.records",), "summary"),
            ConditionalClause("", "count all acquired records", "count",
                              ("c0.records",), "total"),
            EffectClause("", "send requested result", "send", {
                "body": {"from": "c1.summary"},
                "total": {"from": "c2.total"},
            }),
        ])

    def test_argmax_accepts_complete_parallel_collections(self):
        class Projector:
            def place(self, task, contract, action, arguments, requests, receipts):
                receipt = receipts[0]
                values = {
                    "c1.items": [{"id": "r1"}, {"id": "r2"}],
                    "c2.scores": [1, 9],
                }
                paths = {"c1.items": "/items", "c2.scores": "/scores"}
                return {"status": "placed", "bindings": [
                    {"source": row["source"], "value": values[row["source"]],
                     "refs": [receipt.digest + "#" + paths[row["source"]]],
                     "root_ref": receipt.digest + "#" + paths[row["source"]],
                     "operation": "replayed-proof"}
                    for row in requests]}

        contract = TaskContract("archive max score", [
            AcquireClause("", "list records", "list_records", {}, "listing"),
            DeriveClause("", "extract items", ("c0.listing",), "items"),
            DeriveClause("", "extract scores", ("c0.listing",), "scores"),
            ConditionalClause("", "select maximum", "argmax",
                              ("c1.items", "c2.scores"), "selected"),
            EffectClause("", "archive selected", "archive_record", {
                "record": {"from": "c3.selected"}}),
        ])
        capabilities = {
            "list_records": CapabilitySurface("list_records", observation=True),
            "archive_record": CapabilitySurface(
                "archive_record", arguments=("record",), effect=True,
                required_arguments=("record",)),
        }
        runtime = WrapRuntime(
            contract, capabilities, placement_agent=Projector(),
            task_id="parallel-argmax")
        runtime.observe("list_records", {}, {
            "items": [{"id": "r1"}, {"id": "r2"}], "scores": [1, 9]})
        episode = Episode(
            contract, runtime, PlantRuntime(), Detector(), ProposalBuffer())
        decision = episode.propose(
            "archive_record", {"record": {"id": "r2"}}, "archive-call")
        self.assertEqual("pass", decision.route)
        self.assertTrue(any(
            isinstance(item, ConditionalBinding) and item.domain_complete
            for item in runtime.clause_bindings))

    def test_singleton_conditionally_wraps_one_derived_scalar_for_array_sink(self):
        class Projector:
            def place(self, task, contract, action, arguments, requests, receipts):
                receipt = receipts[0]
                return {"status": "placed", "bindings": [{
                    "source": "c1.product_id", "value": "P007",
                    "refs": [receipt.digest + "#/products/0/id"],
                    "root_ref": receipt.digest + "#/products/0/id",
                    "operation": "replayed-proof",
                }]}

        contract = TaskContract("checkout the requested product", [
            AcquireClause("", "search requested product", "search_products",
                          {"query": {"literal": "requested product"}}, "results"),
            DeriveClause("", "derive the requested product identifier",
                         ("c0.results",), "product_id"),
            ConditionalClause("", "construct the checkout item array",
                              "singleton", ("c1.product_id",), "product_ids"),
            EffectClause("", "checkout the requested product", "checkout", {
                "product_ids": {"from": "c2.product_ids"}}),
        ])
        capabilities = {
            "search_products": CapabilitySurface(
                "search_products", arguments=("query",), observation=True,
                required_arguments=("query",)),
            "checkout": CapabilitySurface(
                "checkout", arguments=("product_ids",), effect=True,
                required_arguments=("product_ids",), argument_schemas=((
                    "product_ids", {"type": "array",
                                    "items": {"type": "string"}}),)),
        }
        runtime = WrapRuntime(
            contract, capabilities, placement_agent=Projector(),
            task_id="singleton-checkout")
        runtime.observe("search_products", {"query": "requested product"},
                        {"products": [{"id": "P007"}]})
        episode = Episode(
            contract, runtime, PlantRuntime(), Detector(), ProposalBuffer())
        decision = episode.propose(
            "checkout", {"product_ids": ["P007"]}, "checkout-call")
        self.assertEqual("pass", decision.route)
        binding = next(item for item in runtime.clause_bindings
                       if isinstance(item, ConditionalBinding))
        self.assertEqual("singleton", binding.operator)
        self.assertTrue(binding.domain_complete)
        self.assertTrue(any(isinstance(item, EffectBinding)
                            for item in runtime.clause_bindings))

    def test_runtime_materializes_all_four_binding_variants(self):
        class Projector:
            def place(self, task, contract, action, arguments, requests, receipts):
                receipt = receipts[0]
                return {"status": "placed", "bindings": [{
                    "source": "c1.summary", "value": "hello",
                    "refs": [receipt.digest + "#/0"],
                    "root_ref": receipt.digest + "#/0",
                    "operation": "replayed-proof",
                }]}

        capabilities = {
            "read_records": CapabilitySurface(
                "read_records", observation=True),
            "send": CapabilitySurface(
                "send", arguments=("body", "total"), effect=True,
                required_arguments=("body", "total")),
        }
        runtime = WrapRuntime(
            self._contract(), capabilities, placement_agent=Projector(),
            task_id="task-run")
        runtime.observe("read_records", {}, ["hello", "world"])
        episode = Episode(
            runtime.contract, runtime, PlantRuntime(), Detector(), ProposalBuffer())
        decision = episode.propose(
            "send", {"body": "hello", "total": 2}, "send-call")
        self.assertEqual("pass", decision.route)

        bindings = runtime.clause_bindings
        self.assertEqual(4, len(bindings))
        self.assertIsInstance(bindings[0], AcquireBinding)
        self.assertTrue(any(isinstance(item, DeriveBinding) for item in bindings))
        self.assertTrue(any(isinstance(item, ConditionalBinding) for item in bindings))
        self.assertTrue(any(isinstance(item, EffectBinding) for item in bindings))
        self.assertEqual({"c0", "c1", "c2", "c3"},
                         {item.clause_id for item in bindings})

        audit = runtime.close()
        self.assertEqual([], runtime.clause_bindings)
        self.assertEqual(
            {"acquire", "derive", "conditional", "effect"},
            {row["type"] for row in audit["clause_bindings"]})


if __name__ == "__main__":
    unittest.main()
