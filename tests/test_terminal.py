from contextlib import redirect_stdout
from io import StringIO
import unittest
from unittest.mock import patch

from testfirst.__main__ import main
from testfirst.challenges import LARGEST


class TerminalTests(unittest.TestCase):
    def run_game(self, inputs):
        output = StringIO()
        with patch("builtins.input", side_effect=inputs), redirect_stdout(output):
            main()
        return output.getvalue()

    def test_success_trace_and_retry(self):
        output = self.run_game(["[-5, -2]", "-2", "[4]", "4", "quit"])
        self.assertIn(LARGEST.source, output)
        self.assertIn("Expected output: -2", output)
        self.assertIn("Actual buggy output: 0", output)
        self.assertIn("Initial: best = 0", output)
        self.assertIn("number = -5; -5 > 0 is False; no update; best: 0 -> 0", output)
        self.assertIn("number = -2; -2 > 0 is False; no update; best: 0 -> 0", output)
        self.assertIn("does not expose the bug", output)
        self.assertIn("Hints used: 0/3", output)
        for hint in LARGEST.hints:
            self.assertNotIn(hint, output)

    def test_all_outcomes_and_hint_restart(self):
        output = self.run_game([
            "hint", "hint", "hint", "hint", "[true]", "1",
            "[-1]", "0", "restart", "[-1]", "-1", "quit",
        ])
        self.assertIn("All hints have been used.", output)
        self.assertIn("Invalid input:", output)
        self.assertIn("Incorrect prediction:", output)
        self.assertIn("Restarted. Hints used: 0", output)
        self.assertIn("Success!", output)
        self.assertTrue(output.rstrip().endswith("Goodbye! Hints used: 0/3"))

    def test_eof_and_interrupt_exit_cleanly_at_both_prompts(self):
        for error in (EOFError, KeyboardInterrupt):
            for inputs in ([error], ["[1]", error]):
                with self.subTest(error=error, inputs=inputs):
                    self.assertIn("Goodbye!", self.run_game(inputs))


if __name__ == "__main__":
    unittest.main()
