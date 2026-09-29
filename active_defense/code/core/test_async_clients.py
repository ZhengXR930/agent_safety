from __future__ import annotations

import asyncio
import os
import unittest
from unittest.mock import patch

from code.core.async_compat import ensure_event_loop
from code.core.client import TOTOKENS_RESPONSES_MODELS, agent_sdk_model


class AsyncClientIsolationTests(unittest.TestCase):
    def test_totokens_judges_use_responses_api(self):
        self.assertIn("gpt-5.4", TOTOKENS_RESPONSES_MODELS)
        self.assertIn("gpt-5.6-sol", TOTOKENS_RESPONSES_MODELS)

    def test_replaces_closed_policy_loop(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.close()
        ensure_event_loop()
        replacement = asyncio.get_event_loop()
        self.assertFalse(replacement.is_closed())
        replacement.close()
        asyncio.set_event_loop(None)

    @patch.dict(os.environ, {"DEEPSEEK_API_KEY": "test-key"})
    def test_agent_models_do_not_share_async_client_across_roles(self):
        first = agent_sdk_model("deepseek-v4-flash")
        second = agent_sdk_model("deepseek-v4-flash")
        self.assertIsNot(first, second)


if __name__ == "__main__":
    unittest.main()
