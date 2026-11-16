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


def trace_largest(numbers: list[int]) -> tuple[str, ...]:
    best = 0
    steps = ["Initial: best = 0 (before the loop)"]
    for index, number in enumerate(numbers, 1):
        before = best
        updated = number > best
        if updated:
            best = number
        decision = "update" if updated else "no update"
        steps.append(
            f"Iteration {index}: number = {number}; {number} > {before} is {updated}; "
            f"{decision}; best: {before} -> {best}"
        )
    steps.append(f"Return: {best}")
    return tuple(steps)


def second_largest(numbers):
    ordered = sorted(numbers)
    return ordered[-2]


def reference_second_largest(numbers):
    return sorted(set(numbers))[-2]


def trace_second_largest(numbers: list[int]) -> tuple[str, ...]:
    ordered = sorted(numbers)
    return (
        f"Initial: numbers = {numbers}",
        f"Sort ascending (duplicates retained): ordered = {ordered}",
        f"Select ordered[-2] at index {len(ordered) - 2}: {ordered[-2]}",
        f"Return: {ordered[-2]}",
    )


def most_frequent(numbers):
    counts = {}
    for number in numbers:
        counts[number] = counts.get(number, 0) + 1
    return max(counts, key=counts.get)


def reference_most_frequent(numbers):
    return min(set(numbers), key=lambda number: (-numbers.count(number), number))


def trace_most_frequent(numbers: list[int]) -> tuple[str, ...]:
    counts = {}
    steps = ["Initial: counts = {}"]
    for index, number in enumerate(numbers, 1):
        before = counts.get(number, 0)
        counts[number] = before + 1
        steps.append(
            f"Iteration {index}: number = {number}; count: {before} -> {counts[number]}; "
            f"counts = {counts}"
        )
    winner = max(counts, key=counts.get)
    steps.append(
        f"Select max(counts, key=counts.get): key order = {list(counts)}; "
        f"highest count = {counts[winner]}; first key with that count = {winner} "
        "(ties keep the first encountered key)"
    )
    steps.append(f"Return: {winner}")
    return tuple(steps)


def sum_positive(numbers):
    total = 0
    for number in numbers:
        total += number
    return total


def reference_sum_positive(numbers):
    return sum(number for number in numbers if number > 0)


def trace_sum_positive(numbers):
    total = 0
    steps = ["Initial: total = 0"]
    for index, number in enumerate(numbers, 1):
        before = total
        total += number
        steps.append(f"Iteration {index}: number = {number}; add {number}; total: {before} -> {total}")
    steps.append(f"Return: {total}")
    return tuple(steps)


def count_positive(numbers):
    count = 0
    for number in numbers:
        if number >= 0:
            count += 1
    return count


def reference_count_positive(numbers):
    return sum(1 for number in numbers if number > 0)


def trace_count_positive(numbers):
    count = 0
    steps = ["Initial: count = 0"]
    for index, number in enumerate(numbers, 1):
        before = count
        counted = number >= 0
        if counted:
            count += 1
        decision = "increment" if counted else "no update"
        steps.append(
            f"Iteration {index}: number = {number}; {number} >= 0 is {counted}; "
            f"{decision}; count: {before} -> {count}"
        )
    steps.append(f"Return: {count}")
    return tuple(steps)


@dataclass(frozen=True)
class Challenge:
    title: str
    specification: str
    buggy: Callable[[list[int]], int]
    reference: Callable[[list[int]], int]
    trace: Callable[[list[int]], tuple[str, ...]]
    hints: tuple[str, ...]
    explanation: str
    min_distinct: int = 1

    @property
    def input_rules(self) -> str:
        rules = (
            "Enter 1–8 numbers in square brackets, like [1, 2, 3]. "
            "Each number must be between -20 and 20, with no decimals."
        )
        if self.min_distinct > 1:
            rules += f" Include at least {self.min_distinct} different numbers."
        return rules

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

SECOND_LARGEST = Challenge(
    title="Second-largest DISTINCT number",
    specification=(
        "Return the second-largest distinct integer in the list. Duplicate values "
        "count only once. The list must contain at least two different numbers."
    ),
    buggy=second_largest,
    reference=reference_second_largest,
    trace=trace_second_largest,
    hints=(
        "Does the second position always represent the second distinct value?",
        "Sorting preserves duplicate values. Consider repeated large numbers.",
        "Try [1, 3, 3]. The second-largest distinct value is 1, not 3.",
    ),
    explanation=(
        "Sorting keeps duplicates. If the largest value occurs more than once, "
        "ordered[-2] is still the largest value. Remove duplicates before sorting: "
        "sorted(set(numbers))[-2]."
    ),
    min_distinct=2,
)

MOST_FREQUENT = Challenge(
    title="Most-frequent number",
    specification=(
        "Return the integer that occurs most often in a non-empty list. "
        "If several values share the highest frequency, return the smallest value."
    ),
    buggy=most_frequent,
    reference=reference_most_frequent,
    trace=trace_most_frequent,
    hints=(
        "What does the specification require when frequencies are equal?",
        "Dictionary keys follow first appearance. max keeps the first key on a tie.",
        "Try [2, 1]. Both occur once, so the correct answer is 1, even though 2 appears first.",
    ),
    explanation=(
        "The counts are correct, but max(counts, key=counts.get) keeps the first "
        "encountered key on a frequency tie. The specification requires the smallest "
        "tied value. Compare frequency first and then prefer the smaller number."
    ),
)

SUM_POSITIVE = Challenge(
    title="Sum the positive numbers",
    specification=(
        "Return the sum of numbers greater than zero. Ignore zero and negative "
        "numbers. Count repeated positive numbers each time. Return 0 if none are positive."
    ),
    buggy=sum_positive,
    reference=reference_sum_positive,
    trace=trace_sum_positive,
    hints=(
        "Which numbers should contribute to the total?",
        "The loop adds every number, without checking its sign.",
        "Try [2, -1]. Only 2 should contribute, so the correct sum is 2.",
    ),
    explanation=(
        "The loop adds negative numbers too, reducing the total. The specification "
        "requires only positive numbers. Add a number only when number > 0."
    ),
)

COUNT_POSITIVE = Challenge(
    title="Count the positive numbers",
    specification=(
        "Return how many numbers are greater than zero. Zero is not positive. "
        "Count repeated positive numbers each time. Return 0 if none are positive."
    ),
    buggy=count_positive,
    reference=reference_count_positive,
    trace=trace_count_positive,
    hints=(
        "Check the boundary between positive and non-positive numbers.",
        "Does number >= 0 count a value that the specification excludes?",
        "Try [0]. It contains no positive numbers, so the correct count is 0.",
    ),
    explanation=(
        "The >= comparison includes zero, but zero is not positive. Use number > 0 "
        "so only strictly positive numbers increment the count."
    ),
)

CHALLENGES = (LARGEST, SECOND_LARGEST, MOST_FREQUENT, SUM_POSITIVE, COUNT_POSITIVE)
