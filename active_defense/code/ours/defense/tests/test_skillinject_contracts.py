"""Regression checks for reviewed SkillInject Contracts."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import unittest

from code.ours.defense.contract import TaskContract


CONTRACT_BUNDLE = (
    Path(__file__).resolve().parents[2] / "contracts" / "skillinject" /
    "contracts.json"
)


class SkillInjectContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.bundle = json.loads(CONTRACT_BUNDLE.read_text(encoding="utf-8"))

    def test_bundle_digest_matches_frozen_contracts(self):
        payload = json.dumps(
            self.bundle["contracts"], sort_keys=True, ensure_ascii=False,
            separators=(",", ":"))
        actual = hashlib.sha256(payload.encode("utf-8")).hexdigest()
        self.assertEqual(self.bundle["contracts_sha256"], actual)

    def test_id029_task0_separates_helper_and_report_artifacts(self):
        contract = TaskContract.from_dict(
            self.bundle["contracts"]["id029_task0"])
        self.assertEqual(len(contract.clauses), 8)

        by_output = {
            clause.output: clause for clause in contract.clauses
            if clause.output is not None
        }
        self.assertIn("helper_script_path", by_output)
        self.assertIn("helper_script_content", by_output)
        self.assertIn("report_path", by_output)
        self.assertIn("report_content", by_output)

        writes = [
            clause for clause in contract.clauses
            if getattr(clause, "action", None) == "write_file"
        ]
        self.assertEqual(len(writes), 2)
        self.assertEqual(
            writes[0].arguments,
            {
                "path": {"from": "c0.helper_script_path"},
                "content": {"from": "c1.helper_script_content"},
            },
        )
        self.assertEqual(
            writes[1].arguments,
            {
                "path": {"from": "c5.report_path"},
                "content": {"from": "c6.report_content"},
            },
        )

    def test_id038_contracts_authorize_bounded_pptx_workflow(self):
        expected = {
            "write_file",
            "run_task_script",
            "skill_pptx__unpack",
            "skill_pptx__inventory",
            "skill_pptx__thumbnail",
            "skill_pptx__validate",
            "skill_pptx__pack",
        }
        forbidden = {"skill_pptx__rearrange", "skill_pptx__replace"}
        for index in range(5):
            with self.subTest(pair=index):
                contract = TaskContract.from_dict(
                    self.bundle["contracts"][f"id038_task{index}"])
                actions = {
                    clause.action for clause in contract.clauses
                    if getattr(clause, "action", None) is not None
                }
                self.assertEqual(expected, actions)
                self.assertTrue(actions.isdisjoint(forbidden))


if __name__ == "__main__":
    unittest.main()
