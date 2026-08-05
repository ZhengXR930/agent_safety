"""Closed operator types constrain semantic Binding proposals."""
import unittest

from code.defense.contract import (AcquireClause, ConditionalClause,
                                   DeriveClause, TaskContract)
from code.defense.proof import materialize_intermediate_derive
from code.defense.state import Binding, Receipt, RuntimeState


class OperatorInputBindingTests(unittest.TestCase):
    def test_add_derive_selects_exact_numeric_span_not_whole_text(self):
        contract = TaskContract("increase rent by the notice amount", [
            AcquireClause("", "read notice", "read_file", {}, "notice"),
            DeriveClause("", "rent increase", ("c0.notice",), "increase"),
            ConditionalClause(
                "", "compute rent", "add", ("c1.increase", 1100), "rent"),
        ])
        state = RuntimeState()
        receipt = state.record(Receipt(
            "read_file", {}, "Your monthly rent is increased by 100.00."))
        state.bind(Binding("c0", "acquire", receipt.value,
                           (receipt.digest + "#",)))

        observed = {}

        def choose(**request):
            observed.update(request)
            candidate = next(row for row in request["candidates"]
                             if str(row["value"]) == "100.00")
            return {"candidate_ids": [candidate["id"]], "compose": "scalar"}

        binding = materialize_intermediate_derive(
            state, contract, contract.clauses[1], choose=choose)
        self.assertIsNotNone(binding)
        self.assertEqual("number", observed["expected_type"])
        self.assertTrue(all(
            str(row["value"]).strip() == "100.00"
            for row in observed["candidates"]))
        self.assertEqual("100.00", binding.value)
        self.assertIn("@", binding.refs[0])


if __name__ == "__main__":
    unittest.main()
