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
        output = self.run_game(["1", "[-5, -2]", "-2", "replay", "[4]", "4", "quit"])
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
            "[1,3,3]", "1", "replay", "menu", "1", "hint",
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

    def test_success_waits_in_completion_menu_until_valid_choice(self):
        inputs = ["1", "[-1]", "-1", "", "[1]", "hint", "restart", "wrong", "quit"]
        with patch("builtins.input", side_effect=inputs) as read, redirect_stdout(StringIO()) as output:
            main()
        prompts = [call.args[0] for call in read.call_args_list]
        self.assertEqual(sum(prompt.startswith("\nList") for prompt in prompts), 1)
        self.assertTrue(all("Completion menu" in prompt for prompt in prompts[3:]))
        self.assertEqual(output.getvalue().count("Invalid choice."), 5)
        self.assertNotIn("Try another list", output.getvalue())

    def test_next_visits_each_challenge_then_shows_summary(self):
        output = self.run_game([
            "1", "[-1]", "-1", "next", "[1,3,3]", "1", "next",
            "[2,1]", "1", "next",
        ])
        self.assertEqual(output.count("Challenge complete."), 3)
        self.assertIn("Session summary: 3/3 challenges completed.", output)
        self.assertEqual(output.count(": complete; hints used: 0/3"), 3)
        self.assertNotIn("not completed", output)

    def test_next_after_last_does_not_claim_skipped_challenges_complete(self):
        output = self.run_game(["3", "hint", "[2,1]", "1", "next"])
        self.assertIn("Session summary: 1/3 challenges completed.", output)
        self.assertIn("Find the largest number: not completed", output)
        self.assertIn("Second-largest DISTINCT number: not completed", output)
        self.assertIn("Most-frequent number: complete; hints used: 1/3", output)

    def test_completion_menu_marks_solved_challenges(self):
        output = self.run_game(["2", "[1,3,3]", "1", "menu", "quit"])
        self.assertIn("2. Second-largest DISTINCT number [complete]", output)
        self.assertNotIn("1. Find the largest number [complete]", output)
        self.assertNotIn("3. Most-frequent number [complete]", output)

    def test_replay_resets_only_current_hints_and_keeps_completion(self):
        output = self.run_game([
            "2", "hint", "menu", "1", "hint", "hint", "[-1]", "-1",
            "replay", "hint", "menu", "2", "hint", "menu", "quit",
        ])
        self.assertIn("Replaying. Hints used: 0", output)
        self.assertEqual(output.count(LARGEST.hints[0]), 2)
        self.assertIn("1. Find the largest number [complete]", output)
        self.assertIn("Hints used: 2/3", output)
        self.assertEqual(output.count("What happens when no number in the list is greater than zero?"), 1)

    def test_repeated_success_counts_once_and_session_state_resets(self):
        output = self.run_game([
            "3", "[2,1]", "1", "replay", "[3,1]", "1", "next",
        ])
        self.assertIn("Session summary: 1/3 challenges completed.", output)
        self.assertNotIn("[complete]", self.run_game(["quit"]))

    def test_eof_and_interrupt_at_completion_and_following_selection(self):
        for error in (EOFError, KeyboardInterrupt):
            for tail in ([error], ["menu", error], ["replay", error], ["next", error]):
                with self.subTest(error=error, tail=tail):
                    output = self.run_game(["1", "[-1]", "-1", *tail])
                    self.assertIn("Goodbye!", output)


if __name__ == "__main__":
    unittest.main()
