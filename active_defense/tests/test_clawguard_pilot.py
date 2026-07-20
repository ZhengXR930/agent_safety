import importlib.util
from pathlib import Path
import sys
import unittest


MODULE_PATH = Path(__file__).resolve().parents[1] / "code" / "run_clawguard_pilot.py"
sys.path.insert(0, str(MODULE_PATH.parent))
SPEC = importlib.util.spec_from_file_location("run_clawguard_pilot", MODULE_PATH)
pilot = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(pilot)


class ClawGuardPilotTests(unittest.TestCase):
    def test_task_scope_allows_requested_path_and_denies_ssh_key(self):
        scope = {
            "task_description": "read report",
            "file_read": ["/data/project/documents/report.txt"],
            "file_write": [],
            "commands": [],
            "network": [],
            "disabled_tools": [],
        }
        engine = pilot.upstream_engine(scope)
        self.assertEqual(pilot.check_action(engine, "read_file", {"path": "/data/project/documents/report.txt"})[0], "allow")
        self.assertEqual(pilot.check_action(engine, "read_file", {"path": "~/.ssh/id_rsa"})[0], "deny")

    def test_move_requires_both_source_and_destination_authority(self):
        scope = {
            "task_description": "move file",
            "file_read": ["/tmp/a"],
            "file_write": ["/tmp/b"],
            "commands": [],
            "network": [],
            "disabled_tools": [],
        }
        engine = pilot.upstream_engine(scope)
        self.assertEqual(pilot.check_action(engine, "move_file", {"source": "/tmp/a", "destination": "/tmp/b"})[0], "allow")
        self.assertEqual(pilot.check_action(engine, "move_file", {"source": "~/.ssh/id_rsa", "destination": "/tmp/b"})[0], "deny")

    def test_unknown_mcp_tool_is_not_silently_allowed(self):
        engine = pilot.upstream_engine({
            "task_description": "x", "file_read": [], "file_write": [],
            "commands": [], "network": [], "disabled_tools": [],
        })
        self.assertEqual(pilot.check_action(engine, "office_magic", {})[0], "unsupported")


if __name__ == "__main__":
    unittest.main()
