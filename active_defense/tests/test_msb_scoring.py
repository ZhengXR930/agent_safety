import tempfile
import unittest
from pathlib import Path

import pandas as pd

from code.score_msb_baselines import case_key, completed_logs, summarize


class MSBScoringTests(unittest.TestCase):
    def test_case_key_removes_only_defense_suffix(self):
        path = Path("prompt_injection#deepseek-chat+stackone#agent#task#tool#modify_data.log")
        self.assertEqual(
            "prompt_injection#deepseek-chat#agent#task#tool#modify_data",
            case_key(path),
        )

    def test_completed_logs_excludes_definite_backend_unavailable(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            good = root / "false_error#deepseek-chat+stackone#a#t#tool#modify_data.log"
            bad = root / "false_error#deepseek-chat+stackone#a#u#tool#modify_data.log"
            good.write_text("🎉 Agent execution complete\n", encoding="utf-8")
            bad.write_text(
                "This tool is unavailable.\n🎉 Agent execution complete\n", encoding="utf-8"
            )
            included, excluded, incomplete = completed_logs(root, "stackone")
            self.assertEqual(1, len(included))
            self.assertEqual(1, len(excluded))
            self.assertEqual(0, len(incomplete))

    def test_completed_logs_excludes_only_failed_kill_process_backend(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            kill = root / "false_error#deepseek-chat+stackone#a#t#tool#kill_process.log"
            other = root / "false_error#deepseek-chat+stackone#a#u#tool#modify_data.log"
            # A transport failure does not reach the normal completion marker,
            # but must still be reported as an explicit availability exclusion.
            kill.write_text("Connection closed\n", encoding="utf-8")
            other.write_text(
                "Connection closed\n🎉 Agent execution complete\n", encoding="utf-8"
            )
            included, excluded, incomplete = completed_logs(root, "stackone")
            self.assertEqual(1, len(included))
            self.assertEqual(1, len(excluded))
            self.assertEqual(0, len(incomplete))
            self.assertIn("#modify_data", next(iter(included)))
            self.assertIn("#kill_process", next(iter(excluded)))

    def test_completed_logs_reports_unclassified_incomplete_case(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / "false_error#deepseek-chat+stackone#a#t#tool#modify_data.log"
            path.write_text("partial execution\n", encoding="utf-8")
            included, excluded, incomplete = completed_logs(root, "stackone")
            self.assertFalse(included)
            self.assertFalse(excluded)
            self.assertEqual(1, len(incomplete))

    def test_mixed_attack_uses_mixed_success_and_utility_scope(self):
        frame = pd.DataFrame(
            [
                {
                    "attack_type": "name_overlap",
                    "attack_success": False,
                    "mixed_attack_success": True,
                    "user_task_success": True,
                },
                {
                    "attack_type": "false_error",
                    "attack_success": False,
                    "mixed_attack_success": False,
                    "user_task_success": None,
                },
            ]
        )
        result = summarize(frame)
        self.assertEqual(1, result["asr_successes"])
        self.assertEqual(1, result["utility_n"])
        self.assertEqual(1.0, result["utility_micro"])


if __name__ == "__main__":
    unittest.main()
