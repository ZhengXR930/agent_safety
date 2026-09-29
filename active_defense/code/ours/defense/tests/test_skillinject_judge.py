"""Regression tests for replayable SkillInject utility judging."""
from __future__ import annotations

import unittest
from unittest.mock import patch

from code.benchmarks.skillinject.execution import baselines


class SkillInjectUtilityJudgeTests(unittest.TestCase):
    @patch.object(baselines, "client_for_model", return_value=object())
    @patch.object(
        baselines, "chat",
        side_effect=[TimeoutError("gateway timeout"),
                     '{"verdict":"task_success","reason":"artifact present"}'])
    def test_transient_failure_retries_same_judge(self, chat, client):
        utility, reason = baselines.judge_utility_evidence(
            "make artifact", "FILE result.txt:\ndone", "judge-model",
            attempts=3)
        self.assertTrue(utility)
        self.assertEqual("task_success: artifact present", reason)
        self.assertEqual(2, chat.call_count)
        self.assertEqual(2, client.call_count)
        prompts = [call.args[2] for call in chat.call_args_list]
        self.assertEqual(prompts[0], prompts[1])

    @patch.object(baselines, "client_for_model", return_value=object())
    @patch.object(baselines, "chat", side_effect=TimeoutError("offline"))
    def test_exhausted_retries_remain_technical(self, chat, client):
        utility, reason = baselines.judge_utility_evidence(
            "make artifact", "no evidence", "judge-model", attempts=3)
        self.assertIsNone(utility)
        self.assertIn("after retries", reason)
        self.assertIn("attempt 3/3", reason)
        self.assertEqual(3, chat.call_count)
        self.assertEqual(3, client.call_count)

    @patch.object(baselines, "client_for_model", return_value=object())
    @patch.object(
        baselines, "chat",
        return_value='{"verdict":"technical","reason":"corrupt evidence"}')
    def test_valid_technical_verdict_is_not_retried(self, chat, client):
        utility, reason = baselines.judge_utility_evidence(
            "make artifact", "evidence", "judge-model", attempts=3)
        self.assertIsNone(utility)
        self.assertEqual("technical: corrupt evidence", reason)
        self.assertEqual(1, chat.call_count)
        self.assertEqual(1, client.call_count)

    def test_metadata_binds_model_prompt_and_exact_evidence(self):
        first = baselines.utility_judge_metadata("evidence-a", "judge-model")
        second = baselines.utility_judge_metadata("evidence-b", "judge-model")
        self.assertEqual("judge-model", first["model"])
        self.assertEqual(
            baselines.UTILITY_JUDGE_PROMPT_VERSION,
            first["prompt_version"])
        self.assertNotEqual(first["evidence_sha256"], second["evidence_sha256"])


if __name__ == "__main__":
    unittest.main()
