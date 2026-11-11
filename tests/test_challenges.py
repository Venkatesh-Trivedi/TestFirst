from dataclasses import replace
from itertools import product
import json
import unittest
from unittest.mock import Mock

from testfirst.challenges import CHALLENGES, SECOND_LARGEST, MOST_FREQUENT
from testfirst.engine import Game, Outcome, parse_numbers


class NewChallengeTests(unittest.TestCase):
    def test_second_largest_outcomes(self):
        cases = [
            ([1, 3, 3], 1, Outcome.SUCCESS, 3),
            ([-2, -2, -5], -5, Outcome.SUCCESS, -2),
            ([-20, 20, 20], -20, Outcome.SUCCESS, 20),
            ([1, 2], 1, Outcome.NO_BUG, 1),
            ([1, 1, 3], 1, Outcome.NO_BUG, 1),
            ([0, -1, 2], 0, Outcome.NO_BUG, 0),
            ([-20] * 6 + [20, 20], -20, Outcome.SUCCESS, 20),
            ([1, 3, 3], 3, Outcome.INCORRECT_PREDICTION, 3),
        ]
        for numbers, prediction, outcome, actual in cases:
            with self.subTest(numbers=numbers, prediction=prediction):
                result = Game(SECOND_LARGEST).evaluate(json.dumps(numbers), str(prediction))
                self.assertEqual(result.outcome, outcome)
                self.assertEqual(result.actual, actual)
                self.assertEqual(result.expected, sorted(set(numbers), reverse=True)[1])

    def test_most_frequent_outcomes(self):
        cases = [
            ([2, 1], 1, Outcome.SUCCESS, 2),
            ([3, 1, 3, 1], 1, Outcome.SUCCESS, 3),
            ([-1, -2], -2, Outcome.SUCCESS, -1),
            ([20, -20] * 4, -20, Outcome.SUCCESS, 20),
            ([1, 2], 1, Outcome.NO_BUG, 1),
            ([3, 1, 1], 1, Outcome.NO_BUG, 1),
            ([0], 0, Outcome.NO_BUG, 0),
            ([20] * 8, 20, Outcome.NO_BUG, 20),
            ([0, -1, 0, -1], -1, Outcome.SUCCESS, 0),
            ([2, 1], 2, Outcome.INCORRECT_PREDICTION, 2),
        ]
        for numbers, prediction, outcome, actual in cases:
            with self.subTest(numbers=numbers, prediction=prediction):
                result = Game(MOST_FREQUENT).evaluate(json.dumps(numbers), str(prediction))
                self.assertEqual(result.outcome, outcome)
                self.assertEqual(result.actual, actual)
                highest = max(numbers.count(n) for n in numbers)
                self.assertEqual(result.expected, min(n for n in numbers if numbers.count(n) == highest))

    def test_each_challenge_validation_prevents_execution(self):
        invalid = ["[]", "[true]", "[1.0]", "[21,1]", "[-21,1]", "[1,2,3,4,5,6,7,8,9]", "bad", "null"]
        for challenge in CHALLENGES:
            buggy = Mock(side_effect=AssertionError("Must not run"))
            reference = Mock(side_effect=AssertionError("Must not run"))
            game = Game(replace(challenge, buggy=buggy, reference=reference))
            texts = invalid + (["[1]", "[2,2]", "[0,0,0]"] if challenge is SECOND_LARGEST else [])
            for text in texts:
                with self.subTest(challenge=challenge.title, text=text):
                    with self.assertRaises(ValueError):
                        parse_numbers(text, challenge)
                    self.assertEqual(game.evaluate(text, "0").outcome, Outcome.INVALID_INPUT)
            for prediction in ("true", "1.0", "bad", "[]"):
                self.assertEqual(game.evaluate("[1,2]", prediction).outcome, Outcome.INVALID_INPUT)
            buggy.assert_not_called()
            reference.assert_not_called()

    def test_all_challenges_have_three_independent_optional_hints(self):
        games = [Game(c) for c in CHALLENGES]
        for game in games:
            self.assertEqual(len(game.challenge.hints), 3)
            self.assertEqual(game.hints_used, 0)
            self.assertEqual([game.next_hint() for _ in range(3)], list(game.challenge.hints))
            self.assertIsNone(game.next_hint())
            self.assertEqual(game.hints_used, 3)
            game.restart()
            self.assertEqual(game.hints_used, 0)

    def test_second_largest_exact_trace(self):
        self.assertEqual(SECOND_LARGEST.trace([3, 1, 3]), (
            "Initial: numbers = [3, 1, 3]",
            "Sort ascending (duplicates retained): ordered = [1, 3, 3]",
            "Select ordered[-2] at index 1: 3",
            "Return: 3",
        ))

    def test_most_frequent_exact_trace(self):
        self.assertEqual(MOST_FREQUENT.trace([2, 1, 1, 2]), (
            "Initial: counts = {}",
            "Iteration 1: number = 2; count: 0 -> 1; counts = {2: 1}",
            "Iteration 2: number = 1; count: 0 -> 1; counts = {2: 1, 1: 1}",
            "Iteration 3: number = 1; count: 1 -> 2; counts = {2: 1, 1: 2}",
            "Iteration 4: number = 2; count: 1 -> 2; counts = {2: 2, 1: 2}",
            "Select max(counts, key=counts.get): key order = [2, 1]; highest count = 2; "
            "first key with that count = 2 (ties keep the first encountered key)",
            "Return: 2",
        ))

    def test_new_challenges_small_domain_exhaustive(self):
        for length in range(1, 6):
            for values in product(range(-2, 3), repeat=length):
                numbers = list(values)
                for challenge in (SECOND_LARGEST, MOST_FREQUENT):
                    if len(set(numbers)) < challenge.min_distinct:
                        continue
                    before = numbers.copy()
                    if challenge is SECOND_LARGEST:
                        expected = sorted(set(numbers), reverse=True)[1]
                    else:
                        highest = max(numbers.count(n) for n in numbers)
                        expected = min(n for n in numbers if numbers.count(n) == highest)
                    self.assertEqual(challenge.reference(numbers), expected)
                    actual = challenge.buggy(numbers)
                    trace = challenge.trace(numbers)
                    self.assertEqual(trace[-1], f"Return: {actual}")
                    if challenge is MOST_FREQUENT:
                        for index, number in enumerate(numbers, 1):
                            counts = {n: numbers[:index].count(n) for n in numbers[:index]}
                            self.assertEqual(trace[index], (
                                f"Iteration {index}: number = {number}; count: "
                                f"{numbers[:index - 1].count(number)} -> {counts[number]}; counts = {counts}"
                            ))
                    self.assertEqual(numbers, before)
                    result = Game(challenge).evaluate(json.dumps(numbers), str(expected))
                    self.assertEqual(result.outcome, Outcome.SUCCESS if actual != expected else Outcome.NO_BUG)
