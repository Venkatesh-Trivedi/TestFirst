"""Input validation and game state, independent of terminal I/O."""

from dataclasses import dataclass
from enum import Enum
import json

from .challenges import Challenge, LARGEST


class Outcome(Enum):
    INVALID_INPUT = "invalid_input"
    INCORRECT_PREDICTION = "incorrect_prediction"
    NO_BUG = "no_bug"
    SUCCESS = "success"


@dataclass(frozen=True)
class Attempt:
    outcome: Outcome
    message: str
    expected: int | None = None
    actual: int | None = None
    trace: tuple[str, ...] = ()


def parse_numbers(input_text: str, challenge: Challenge = LARGEST) -> list[int]:
    try:
        numbers = json.loads(input_text)
    except (ValueError, RecursionError) as error:
        raise ValueError("Use valid JSON for the list.") from error
    if type(numbers) is not list or not 1 <= len(numbers) <= 8:
        raise ValueError("Enter a JSON list containing between 1 and 8 integers.")
    if any(type(number) is not int or not -20 <= number <= 20 for number in numbers):
        raise ValueError("Every list item must be an integer between -20 and 20; no booleans or floats.")
    if len(set(numbers)) < challenge.min_distinct:
        raise ValueError(f"Include at least {challenge.min_distinct} distinct integers.")
    return numbers


def parse_attempt(
    input_text: str, prediction_text: str, challenge: Challenge = LARGEST,
) -> tuple[list[int], int]:
    numbers = parse_numbers(input_text, challenge)
    try:
        prediction = json.loads(prediction_text)
    except (ValueError, RecursionError) as error:
        raise ValueError("Use a valid JSON integer for the prediction.") from error
    if type(prediction) is not int:
        raise ValueError("The predicted output must be a JSON integer; no booleans or floats.")
    return numbers, prediction


@dataclass
class Game:
    challenge: Challenge = LARGEST
    hints_used: int = 0
    completed: bool = False

    def next_hint(self) -> str | None:
        if self.hints_used == len(self.challenge.hints):
            return None
        hint = self.challenge.hints[self.hints_used]
        self.hints_used += 1
        return hint

    def restart(self) -> None:
        self.hints_used = 0

    def evaluate(self, input_text: str, prediction_text: str) -> Attempt:
        try:
            numbers, prediction = parse_attempt(input_text, prediction_text, self.challenge)
        except ValueError as error:
            return Attempt(Outcome.INVALID_INPUT, str(error))
        expected = self.challenge.reference(numbers)
        actual = self.challenge.buggy(numbers)
        if prediction != expected:
            return Attempt(
                Outcome.INCORRECT_PREDICTION,
                "Incorrect prediction: reconsider what the specification asks for.",
                expected, actual,
            )
        if actual == expected:
            return Attempt(
                Outcome.NO_BUG,
                "Correct prediction, but this input does not expose the bug. Try another list.",
                expected, actual,
            )
        self.completed = True
        return Attempt(
            Outcome.SUCCESS, "Success! Your input exposes the bug.",
            expected, actual, self.challenge.trace(numbers),
        )
