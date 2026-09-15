from argparse import Namespace
from pathlib import Path
import unittest

from code.benchmarks.agentdojo.execution.all import suite_command


def _args(method: str) -> Namespace:
    return Namespace(
        method=method,
        output_root=Path("results"),
        agent_model="deepseek-v4-flash",
        defense_model="deepseek-v4-flash",
        attack="important_instructions",
        resume=True,
    )


class RegistryTest(unittest.TestCase):
    def test_ours_command_uses_contract_runner(self) -> None:
        command = suite_command(_args("ours"), ["--max-pairs", "20"], "banking")
        self.assertIn("code.benchmarks.agentdojo.execution.ours", command)
        self.assertEqual(
            command[command.index("--contract-model") + 1],
            "deepseek-v4-flash",
        )
        self.assertIn("--contract-file", command)
        self.assertEqual(command[-2:], ["--max-pairs", "20"])

    def test_progent_command_uses_native_policy_runner(self) -> None:
        command = suite_command(_args("progent"), [], "banking")
        self.assertIn("code.benchmarks.agentdojo.execution.native", command)
        self.assertEqual(command[command.index("--defense") + 1], "progent")
        self.assertEqual(
            command[command.index("--policy-model") + 1],
            "deepseek-v4-flash",
        )

    def test_unrestored_integrations_fail_before_subprocess(self) -> None:
        for method in ("camel", "drift"):
            with self.subTest(method=method):
                with self.assertRaisesRegex(RuntimeError, "must be restored"):
                    suite_command(_args(method), [], "banking")


if __name__ == "__main__":
    unittest.main()
