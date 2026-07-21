import unittest

from code.run_mcptox_ours_full import _summary


class MCPToxOursFullTests(unittest.TestCase):
    def test_summary_uses_committed_semantic_outcomes(self):
        rows = [{"status": "ok", "task_complete": True, "malicious_success": False,
                 "route": "pass", "no_proposal": False, "plants_deployed": 1,
                 "plant_commitments": 1}]
        summary = _summary(rows)
        self.assertEqual(1.0, summary["utility"])
        self.assertEqual(0.0, summary["asr"])
        self.assertEqual(1, summary["plant_commitments"])


if __name__ == "__main__":
    unittest.main()
