import unittest

from code.run_mcptox_undefended import _cases, _official_label, _poison_name, _summary


class MCPToxUndefendedTests(unittest.TestCase):
    def test_full_release_counts(self):
        clean, attack = _cases()
        self.assertEqual(357, len(clean))
        self.assertEqual(1348, len(attack))
        self.assertEqual(len(attack), len({row["key"] for row in attack}))
        self.assertTrue(all(row["attack_specification"] for row in attack))

    def test_public_metadata_parsing(self):
        self.assertEqual("bait", _poison_name("Tool: bait\nDescription: x"))
        self.assertEqual("Success", _official_label({"online_result": {
            "labeled_model_results": [{"DeepSeek-v3": "Success"}]}}))

    def test_summary_separates_no_proposal_from_utility(self):
        rows = [{"status": "ok", "task_complete": False, "malicious_success": False,
                 "no_proposal": True}]
        self.assertEqual(0.0, _summary(rows)["utility"])
        self.assertEqual(1, _summary(rows)["no_proposal"])


if __name__ == "__main__":
    unittest.main()
