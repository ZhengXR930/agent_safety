import json
from pathlib import Path
import tempfile
import unittest

from code.ours.defense.skill_surface import SkillSurfaceCompiler


class SkillSurfaceCompilerTests(unittest.TestCase):
    def test_compiles_only_explicit_file_references(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            skill = root / "skills" / "secure-skill"
            (skill / "scripts").mkdir(parents=True)
            (root / "registry").mkdir()
            (skill / "SKILL.md").write_text(
                "---\nname: secure-skill\n---\n"
                "Run `scripts/scan.py`; installs use `registry.json`.\n")
            (skill / "scripts" / "scan.py").write_text("print('scan')\n")
            (skill / "scripts" / "hidden.py").write_text("print('hidden')\n")
            (root / "registry" / "registry.json").write_text(json.dumps([
                {"name": "a", "path": "skills/a"},
            ]))

            layout = SkillSurfaceCompiler().compile(
                skill / "SKILL.md", environment_root=root)

            self.assertEqual("secure-skill", layout.name)
            self.assertEqual(2, len(layout.cards))
            self.assertEqual({"helper", "state"},
                             {card.kind for card in layout.cards})
            self.assertFalse(any("hidden.py" in card.path
                                 for card in layout.cards))
            state = next(card for card in layout.cards if card.kind == "state")
            self.assertIn("fields name, path", state.summary)
            prompt = layout.placement_cards(artifact_ids=[state.id])
            self.assertEqual(["artifact"],
                             next(row for row in prompt
                                  if row["id"] == state.id)["modes"])

    def test_ambiguous_basename_is_not_guessed(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            skill = root / "skill"
            skill.mkdir()
            (skill / "SKILL.md").write_text(
                "---\nname: demo\n---\nRead registry.json.\n")
            for branch in ("a", "b"):
                directory = root / branch
                directory.mkdir()
                (directory / "registry.json").write_text("[]")
            layout = SkillSurfaceCompiler().compile(
                skill / "SKILL.md", environment_root=root)
            self.assertEqual((), layout.cards)

    def test_compilation_is_cached_for_the_installed_package(self):
        with tempfile.TemporaryDirectory() as raw:
            skill = Path(raw)
            (skill / "SKILL.md").write_text(
                "---\nname: demo\n---\nNo files.\n")
            compiler = SkillSurfaceCompiler()
            first = compiler.compile(skill / "SKILL.md")
            second = compiler.compile(skill / "SKILL.md")
            self.assertIs(first, second)


if __name__ == "__main__":
    unittest.main()
