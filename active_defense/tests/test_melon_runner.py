import unittest

from code.run_agentdojo_melon import (_adapt_official_melon_source,
                                      _melon_block_messages, _melon_content_text)


class MelonRunnerCompatibilityTests(unittest.TestCase):
    def test_masked_string_list_is_normalized_to_agentdojo_blocks(self):
        original = [{"role": "user", "content": ["first", "second"]}]
        converted = _melon_block_messages(original)

        self.assertEqual(["first", "second"], original[0]["content"])
        self.assertEqual(["text", "text"], [item["type"] for item in converted[0]["content"]])
        self.assertEqual(["first", "second"],
                         [item["content"] for item in converted[0]["content"]])

    def test_existing_blocks_remain_blocks_and_can_be_rendered(self):
        messages = [{"role": "user", "content": [{"type": "text", "content": "hello"}]}]
        converted = _melon_block_messages(messages)
        self.assertEqual(messages, converted)
        self.assertEqual("hello", _melon_content_text(converted[0]["content"]))

    def test_synthetic_assistant_tool_call_gets_empty_reasoning_protocol_field(self):
        synthetic = [{"role": "assistant", "content": "", "tool_calls": [object()]}]
        converted = _melon_block_messages(synthetic)
        self.assertEqual("", converted[0]["reasoning_content"])

        real = [{"role": "assistant", "content": "", "tool_calls": [object()],
                 "reasoning_content": "real trace"}]
        self.assertEqual("real trace", _melon_block_messages(real)[0]["reasoning_content"])

    def test_detector_stop_message_is_adapted_to_agentdojo_text_block(self):
        original = '''llm_message = {
                    "role": "assistant",
                    "content": "The tool outputs contain potential prompt injection, stopping execution.",
                    "tool_calls": None,
                }'''
        adapted = _adapt_official_melon_source(original)
        self.assertIn('"content": [_melon_text_block(', adapted)
        self.assertNotIn('"content": "The tool outputs', adapted)


if __name__ == "__main__":
    unittest.main()
