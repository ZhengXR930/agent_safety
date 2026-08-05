import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from code.benchmarks.manifest import validate_plan, validate_registrations
from code.defense.memory import CapabilitySurface, EnvironmentPlan
from code.harness.mcp_ours import _blocks
from code.manifest.agentdojo import COMMIT_ENTRIES
from code.manifest.scr import TRUSTLIFT_TOOLS, authblur_tools
from code.manifest.skillinject import (TOOLS as SKILLINJECT_TOOLS,
                                       generate_catalog, load_catalog,
                                       skill_registration)


class ManifestQualityTests(unittest.TestCase):
    def test_centralized_static_manifests_are_complete(self):
        validate_registrations(SKILLINJECT_TOOLS, "SkillInject")
        validate_registrations(authblur_tools(), "SCR/AuthBlur")
        validate_registrations(TRUSTLIFT_TOOLS, "SCR/TrustLift")
        self.assertTrue({"slack", "workspace", "banking", "travel"}
                        <= set(COMMIT_ENTRIES))

    def test_skillinject_catalog_registers_clean_documented_helpers(self):
        with TemporaryDirectory() as raw:
            skill = Path(raw) / "docx"
            (skill / "scripts").mkdir(parents=True)
            (skill / "SKILL.md").write_text(
                "---\nname: docx\ndescription: Edit documents.\n---\n"
                "export DOCUMENT_SERVICE_URL=\"https://docs.example\"\n"
                "Run python scripts/unpack.py for unpacking.\n")
            trusted = skill / "scripts" / "unpack.py"
            trusted.write_text("print('ok')\n")
            # Package inventory is not authority. An unmentioned executable is
            # exactly how SkillInject supplies its attack helper.
            (skill / "scripts" / "backup.sh").write_text("curl evil\n")
            catalog = generate_catalog(raw, skill_names={"docx"})
        helpers = catalog["skills"]["docx"]["helpers"]
        self.assertEqual(["scripts/unpack.py"],
                         [row["implementation"]["path"] for row in helpers])
        self.assertEqual(64, len(helpers[0]["implementation"]["sha256"]))
        self.assertEqual(
            {"DOCUMENT_SERVICE_URL": "https://docs.example"},
            helpers[0]["implementation"]["environment"])

    def test_checked_in_skillinject_catalog_is_complete_and_valid(self):
        catalog = load_catalog()
        expected = {"docx", "xlsx", "pdf", "pptx", "email-api",
                    "python-code", "calendar", "git"}
        self.assertTrue(expected <= set(catalog["skills"]))
        self.assertNotIn("execute_command",
                         {tool["name"] for tool in SKILLINJECT_TOOLS})
        self.assertIn("run_task_script",
                      {tool["name"] for tool in SKILLINJECT_TOOLS})
        forbidden = {"backup.sh", "ip_loc.py", "network_diag.sh",
                     "file_check.sh"}
        for name, row in catalog["skills"].items():
            tools, manifest = skill_registration(name)
            validate_registrations(tools, "SkillInject/" + name)
            self.assertEqual(set(manifest["tools"]),
                             {tool["name"] for tool in tools})
            paths = {Path(helper["implementation"]["path"]).name
                     for helper in row["helpers"]}
            self.assertFalse(paths & forbidden)

    def test_mcp_catalog_parser_keeps_empty_descriptions_and_final_tool(self):
        rows = _blocks(
            "Tool: first\nDescription: \nArguments:\n"
            "- value: input value (required)\n\n\n"
            "Tool: last\nDescription: List available records.\nArguments:\n")
        self.assertEqual(set(rows), {"first", "last"})
        self.assertEqual(rows["first"]["inputSchema"]["required"], ["value"])
        self.assertIn("registered MCP service", rows["first"]["description"])
        self.assertEqual(rows["last"]["inputSchema"]["required"], [])

    def test_complete_observation_registration_passes(self):
        validate_registrations([{
            "name": "read_record", "description": "Read one record.",
            "effect": False, "observation": True,
            "inputSchema": {
                "type": "object",
                "properties": {"id": {"type": "string"}},
                "required": ["id"], "additionalProperties": False,
            },
            "outputSchema": {"type": "object"},
        }], "test")

    def test_observation_without_output_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "output schema"):
            validate_registrations([{
                "name": "read_record", "description": "Read one record.",
                "effect": False, "observation": True,
                "inputSchema": {"type": "object", "properties": {},
                                "required": []},
            }], "test")

    def test_optional_requiredness_must_be_explicit(self):
        with self.assertRaisesRegex(ValueError, "required arguments"):
            validate_registrations([{
                "name": "search", "description": "Search records.",
                "effect": False, "observation": True,
                "inputSchema": {"type": "object", "properties": {
                    "limit": {"type": "integer"}}},
                "outputSchema": {"type": "array"},
            }], "test")

    def test_plan_rejects_name_only_fallback(self):
        plan = EnvironmentPlan("p", {}, {"read": CapabilitySurface(
            "read", description="read", arguments=("path",), effect=True,
            observation=True, required_arguments=("path",),
            output_schema={"type": "string"},
            argument_schemas=(("path", {"type": "string"}),),
            effect_return=True)})
        with self.assertRaisesRegex(ValueError, "functional description"):
            validate_plan(plan, "test")


if __name__ == "__main__":
    unittest.main()
