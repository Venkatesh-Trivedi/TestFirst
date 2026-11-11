"""Trusted challenge functions and their presentation data."""

from dataclasses import dataclass
from inspect import getsource
from typing import Callable


def largest(numbers):
    best = 0
    for number in numbers:
        if number > best:
            best = number
    return best


@dataclass(frozen=True)
class TraceStep:
    number: int | None
    best_before: int
    best_after: int
    updated: bool


def trace_largest(numbers: list[int]) -> tuple[TraceStep, ...]:
    best = 0
    steps = [TraceStep(None, best, best, False)]
    for number in numbers:
        before = best
        updated = number > best
        if updated:
            best = number
        steps.append(TraceStep(number, before, best, updated))
    return tuple(steps)


@dataclass(frozen=True)
class Challenge:
    title: str
    specification: str
    buggy: Callable[[list[int]], int]
    reference: Callable[[list[int]], int]
    trace: Callable[[list[int]], tuple[TraceStep, ...]]
    hints: tuple[str, ...]
    explanation: str

    @property
    def source(self) -> str:
        return getsource(self.buggy).strip()


LARGEST = Challenge(
    title="Find the largest number",
    specification="Return the largest integer in a non-empty list.",
    buggy=largest,
    reference=max,
    trace=trace_largest,
    hints=(
        "Look closely at the value of best before the loop starts.",
        "What happens when no number in the list is greater than zero?",
        "Try a list containing only negative integers. Its largest value is negative.",
    ),
    explanation=(
        "best starts at 0. With only negative numbers, number > best is always "
        "false, so best stays 0 even though 0 is not in the list. Initialize best "
        "from the first list element, or use max(numbers)."
    ),
)
