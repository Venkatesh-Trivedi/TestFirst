from itertools import product
import json
import unittest
from unittest.mock import Mock
from dataclasses import replace

from testfirst.challenges import LARGEST, TraceStep, largest, trace_largest
from testfirst.engine import Game, Outcome


class EvaluationTests(unittest.TestCase):
    def test_valid_attempts(self):
        cases = [
            ([1, 8, 3], 8, Outcome.NO_BUG),
            ([-8, -2, -5], -2, Outcome.SUCCESS),
            ([-20], -20, Outcome.SUCCESS),
            ([20], 20, Outcome.NO_BUG),
            ([0], 0, Outcome.NO_BUG),
            ([-3, 0, -1], 0, Outcome.NO_BUG),
            ([-20, 5, 20, -1], 20, Outcome.NO_BUG),
            ([-20] * 8, -20, Outcome.SUCCESS),
            ([20] * 8, 20, Outcome.NO_BUG),
            ([1, 4], 1, Outcome.INCORRECT_PREDICTION),
            ([-8, -2], 0, Outcome.INCORRECT_PREDICTION),
            ([0], 100, Outcome.INCORRECT_PREDICTION),
        ]
        for numbers, prediction, outcome in cases:
            with self.subTest(numbers=numbers, prediction=prediction):
                result = Game().evaluate(json.dumps(numbers), str(prediction))
                self.assertEqual(result.outcome, outcome)
                self.assertEqual(result.expected, max(numbers))
                self.assertEqual(result.actual, largest(numbers))
                self.assertEqual(bool(result.trace), outcome is Outcome.SUCCESS)

    def test_invalid_lists(self):
        cases = [
            "", "[", "[1,]", "[1] trailing", "[]", "[1,2,3,4,5,6,7,8,9]",
            "null", "true", "2", '"[1]"', '{"n": 1}',
            "[true]", "[false]", "[1.0]", "[1e0]", '["1"]', "[[1]]",
            "[null]", "[-21]", "[21]", "[NaN]", "[Infinity]", "[-Infinity]",
            "[1, false]", "[" * 2000 + "]" * 2000,
        ]
        buggy = Mock(side_effect=AssertionError("Invalid input must not execute the challenge"))
        game = Game(replace(LARGEST, buggy=buggy))
        for text in cases:
            with self.subTest(text=text[:60]):
                result = game.evaluate(text, "0")
                self.assertEqual(result.outcome, Outcome.INVALID_INPUT)
                self.assertIsNone(result.expected)
                self.assertEqual(result.trace, ())
        buggy.assert_not_called()

    def test_invalid_predictions(self):
        for prediction in ("", "x", "true", "false", "1.0", "1e0", "null", "[]", "{}", '"1"', "NaN", "1 2"):
            with self.subTest(prediction=prediction):
                self.assertEqual(Game().evaluate("[1]", prediction).outcome, Outcome.INVALID_INPUT)

    def test_oversized_integer_is_invalid(self):
        self.assertEqual(Game().evaluate("[" + "9" * 10000 + "]", "0").outcome, Outcome.INVALID_INPUT)

    def test_whitespace_is_valid(self):
        self.assertEqual(Game().evaluate("  [ -2, -1 ] \n", " -1 ").outcome, Outcome.SUCCESS)

    def test_hints_are_optional_limited_and_reset_on_restart(self):
        game = Game()
        game.evaluate("[-1]", "-1")
        self.assertEqual(game.hints_used, 0)
        for index, hint in enumerate(LARGEST.hints, 1):
            self.assertEqual(game.next_hint(), hint)
            self.assertEqual(game.hints_used, index)
        self.assertIsNone(game.next_hint())
        self.assertEqual(game.hints_used, 3)
        game.evaluate("[1]", "1")
        self.assertEqual(game.hints_used, 3)
        game.restart()
        self.assertEqual(game.hints_used, 0)
        self.assertEqual(game.next_hint(), LARGEST.hints[0])


class TraceTests(unittest.TestCase):
    def test_all_negative_trace(self):
        self.assertEqual(trace_largest([-5, -2]), (
            TraceStep(None, 0, 0, False),
            TraceStep(-5, 0, 0, False),
            TraceStep(-2, 0, 0, False),
        ))

    def test_updates_equal_values_and_no_updates(self):
        self.assertEqual(trace_largest([-2, 0, 3, 3, 2, 5]), (
            TraceStep(None, 0, 0, False),
            TraceStep(-2, 0, 0, False),
            TraceStep(0, 0, 0, False),
            TraceStep(3, 0, 3, True),
            TraceStep(3, 3, 3, False),
            TraceStep(2, 3, 3, False),
            TraceStep(5, 3, 5, True),
        ))

    def test_trace_matches_trusted_function_for_all_short_lists(self):
        for length in range(1, 4):
            for values in product(range(-20, 21), repeat=length):
                steps = trace_largest(list(values))
                self.assertEqual(len(steps), length + 1)
                self.assertEqual(steps[0], TraceStep(None, 0, 0, False))
                for previous, step, number in zip(steps, steps[1:], values):
                    self.assertEqual(step.number, number)
                    self.assertEqual(step.best_before, previous.best_after)
                    self.assertEqual(step.updated, number > step.best_before)
                    self.assertEqual(step.best_after, number if step.updated else step.best_before)
                self.assertEqual(steps[-1].best_after, largest(values))


if __name__ == "__main__":
    unittest.main()
