import unittest
from unittest.mock import patch, MagicMock
import json
import sys
import os

# Add parent directory to path to import the main module
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import unthink_proxy


class TestProcessThinkingContent(unittest.TestCase):
    def test_empty_content(self):
        result, thinking_started, thinking_finished = unthink_proxy.process_thinking_content(
            "", False, False
        )
        self.assertEqual(result, "")
        self.assertFalse(thinking_started)
        self.assertFalse(thinking_finished)

    def test_open_tag(self):
        result, thinking_started, thinking_finished = unthink_proxy.process_thinking_content(
            "Hello <think>thinking", False, False
        )
        self.assertEqual(result, "Hello ")
        self.assertTrue(thinking_started)
        self.assertFalse(thinking_finished)

    def test_close_tag(self):
        result, thinking_started, thinking_finished = unthink_proxy.process_thinking_content(
            "thinking</think>World", True, False
        )
        self.assertEqual(result, "World")
        self.assertFalse(thinking_started)
        self.assertTrue(thinking_finished)

    def test_normal_content(self):
        result, thinking_started, thinking_finished = unthink_proxy.process_thinking_content(
            "Normal content", False, False
        )
        self.assertEqual(result, "Normal content")
        self.assertFalse(thinking_started)
        self.assertFalse(thinking_finished)

    def test_thinking_mode(self):
        result, thinking_started, thinking_finished = unthink_proxy.process_thinking_content(
            "Hidden thinking", True, False
        )
        self.assertEqual(result, "")
        self.assertTrue(thinking_started)
        self.assertFalse(thinking_finished)


if __name__ == "__main__":
    unittest.main()