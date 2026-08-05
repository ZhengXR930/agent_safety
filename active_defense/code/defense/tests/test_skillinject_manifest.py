"""Trusted SkillInject native capability registration."""
from __future__ import annotations

import unittest

from code.manifest.skillinject import skill_registration


class SkillInjectManifestTests(unittest.TestCase):
    def test_discord_registers_structured_moderation_effect(self):
        tools, skill = skill_registration("discord")
        by_name = {tool["name"]: tool for tool in tools}
        moderation = by_name["moderate_messages"]
        self.assertTrue(moderation["effect"])
        self.assertTrue(moderation["observation"])
        self.assertTrue(moderation["effect_return"])
        self.assertEqual(
            moderation["argument_types"], {"decisions": "natural_language"})
        self.assertIn("moderate_messages", skill["tools"])


if __name__ == "__main__":
    unittest.main()
