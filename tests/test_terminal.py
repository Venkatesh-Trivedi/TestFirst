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
        output = self.run_game(["1", "[-5, -2]", "-2", "[4]", "4", "quit"])
        self.assertIn(LARGEST.source, output)
        self.assertIn("Expected output: -2", output)
        self.assertEqual(output.count("Challenge complete."), 1)
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
            "1", "hint", "hint", "hint", "hint", "[true]",
            "[-1]", "0", "restart", "[-1]", "-1", "quit",
        ])
        self.assertIn("All hints have been used.", output)
        self.assertIn("Invalid input:", output)
        self.assertIn("Incorrect prediction:", output)
        self.assertIn("Restarted. Hints used: 0", output)
        self.assertIn("Success!", output)
        self.assertTrue(output.rstrip().endswith("Goodbye! Hints used: 0/3"))

    def test_eof_and_interrupt_exit_cleanly_at_all_prompts(self):
        for error in (EOFError, KeyboardInterrupt):
            for inputs in ([error], ["1", error], ["1", "[1]", error], ["1", "menu", error]):
                with self.subTest(error=error, inputs=inputs):
                    self.assertIn("Goodbye!", self.run_game(inputs))

    def test_invalid_lists_never_prompt_for_prediction(self):
        with patch("builtins.input", side_effect=["2", "", "what now?", "[1]", "[2,2]", "[true]", "[1,2]", "1", "quit"]) as read:
            with redirect_stdout(StringIO()) as output:
                main()
        self.assertEqual(sum("Predicted" in call.args[0] for call in read.call_args_list), 1)
        self.assertEqual(output.getvalue().count("Invalid input:"), 5)

    def test_menu_switches_preserve_hints_and_restart_only_selected_game(self):
        output = self.run_game([
            "", "4", "x", "1", "hint", "menu", "2", "hint",
            "[1,3,3]", "1", "restart", "menu", "1", "hint",
            "menu", "2", "hint", "menu", "3", "[2,1]", "1", "menu", "quit",
        ])
        self.assertEqual(output.count("Invalid choice."), 3)
        self.assertEqual(output.count("Challenge complete."), 2)
        self.assertIn("Sort ascending (duplicates retained): ordered = [1, 3, 3]", output)
        self.assertIn("key order = [2, 1]", output)
        self.assertIn("Hints used: 2/3", output)
        self.assertEqual(output.count("Does the second position always represent the second distinct value?"), 2)

    def test_quit_from_initial_menu(self):
        self.assertTrue(self.run_game(["quit"]).rstrip().endswith("Goodbye!"))


if __name__ == "__main__":
    unittest.main()
