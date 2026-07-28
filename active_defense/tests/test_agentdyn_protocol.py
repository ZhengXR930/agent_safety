import copy
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from code.agentdyn_protocol import (  # noqa: E402
    EXPECTED_ATTACK_CELLS,
    EXPECTED_CLEAN_TASKS,
    AgentDynProtocolError,
    load_manifest,
    validate_manifest,
)


class AgentDynProtocolTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # The repository-wide suite intentionally imports the legacy AgentDojo
        # protocol in the same process. Validate the already frozen artifact
        # here; source activation has its own fail-closed integration check.
        cls.manifest = load_manifest(verify_source=False)

    def test_frozen_universe_is_full_agentdyn(self):
        self.assertEqual(self.manifest["clean_task_count"], EXPECTED_CLEAN_TASKS)
        self.assertEqual(self.manifest["attack_cell_count"], EXPECTED_ATTACK_CELLS)
        self.assertEqual(
            {name: (len(spec["user_task_ids"]), len(spec["injection_task_ids"]))
             for name, spec in self.manifest["suites"].items()},
            {"shopping": (20, 9), "github": (20, 9), "dailylife": (20, 10)},
        )

    def test_payloads_are_frozen_per_cell(self):
        self.assertTrue(all(cell["injections"] for cell in self.manifest["cells"]))
        self.assertTrue(all(
            "DeepSeek" in next(iter(cell["injections"].values()))
            for cell in self.manifest["cells"]
        ))

    def test_manifest_mutation_fails_closed(self):
        changed = copy.deepcopy(self.manifest)
        changed["cells"][0]["injections"] = {"x": "changed"}
        with self.assertRaises(AgentDynProtocolError):
            validate_manifest(changed)


if __name__ == "__main__":
    unittest.main()
