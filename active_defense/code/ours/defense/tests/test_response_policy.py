import unittest

from code.ours.defense.response_policy import (
    NON_ECHO_POLICY, append_non_echo_policy)


class ResponsePolicyTests(unittest.TestCase):
    def test_policy_is_idempotent(self):
        once = append_non_echo_policy("trusted system prompt")
        twice = append_non_echo_policy(once)
        self.assertEqual(once, twice)
        self.assertEqual(1, once.count(NON_ECHO_POLICY))

    def test_policy_is_source_and_task_general(self):
        policy = NON_ECHO_POLICY.lower()
        self.assertIn("tool, mcp, skill", policy)
        self.assertIn("entity introduced solely by it", policy)
        self.assertIn("independently needed", policy)
        self.assertNotIn("riverside", policy)
        self.assertNotIn("hotel", policy)


if __name__ == "__main__":
    unittest.main()
