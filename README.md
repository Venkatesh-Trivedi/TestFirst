# TestFirst

A terminal prototype of a beginner programming game. Invent a list that
exposes a bug, predict the correct output, then inspect what the buggy program did.
No learning outcomes or user testing have been measured.

Requires Python 3.10 or newer. Uses only the Python standard library; no install
or dependency setup is required. Run these commands from the repository root:

```powershell
python -m testfirst
```

Run the tests:

```powershell
python -m unittest discover -s tests -v
```

## Playing

Choose a challenge from the numbered menu:

| Choice | Challenge | Specification |
| --- | --- | --- |
| 1 | Find the largest number | Return the largest integer in a non-empty list. |
| 2 | Second-largest DISTINCT number | Return the second-largest unique value, ignoring duplicates. Requires at least two distinct integers. |
| 3 | Most-frequent number | Return the most frequent integer; among equally frequent values, return the smallest. |

Read the specification and buggy function, enter a JSON list such as `[2, 5, 1]`,
then enter your predicted correct output as a JSON integer. For this list, the
predictions for choices 1, 2, and 3 would be `5`, `2`, and `1`, respectively.

Lists must contain 1 through 8 integers, each between -20 and 20 inclusive.
Booleans, floats, non-list values, and malformed JSON are rejected. Predictions
must be JSON integers; an integer outside the list's allowed range is accepted
as an incorrect prediction. The list is validated before you are asked for a
prediction; invalid lists return directly to the list prompt. For choice 2,
lists with fewer than two distinct values are also rejected.

The game distinguishes invalid input, incorrect prediction, correct prediction
without exposing the bug, and success. Success announces **Challenge complete.**,
then displays expected and actual outputs, an execution trace, and an explanation.
The largest-number trace shows the initial `best` and every comparison/update;
second-largest shows the sorted list and selected position; most-frequent shows
count updates, dictionary key order, and the tie-selection rule. All traces end
with the actual return value. Unsuccessful attempts let you try another list.
Success opens a dedicated completion menu, never directly another list prompt:

```text
[next / menu / replay / quit]
```

- `next`: open the next challenge in menu order. After the last challenge, show
  a session summary of completed/not-completed challenges and current hint counts,
  then exit. Skipped challenges are not marked complete.
- `menu`: return to numbered challenge selection.
- `replay`: explicitly restart the current challenge and reset its hints.
- `quit`: exit.

Invalid completion choices stay at this menu. Completed challenges are marked
`[complete]` in the main menu. Completion means you have solved the challenge at
least once in this session; replay/restart and later unsuccessful attempts do
not remove the mark. Repeated successes count once. Choosing a challenge from
the main menu opens it for attempts, preserving its existing hints and mark.

At the **list prompt**, enter `hint` for the next of three optional hints,
`restart` to redisplay the challenge and reset its hint count, `menu` to choose
another challenge, or `quit` to exit. Each challenge has its own three hints.
Retrying and switching away/back preserve that challenge's hint count; restart
only resets the selected challenge. EOF or Ctrl+C exits cleanly at any prompt.
The prediction prompt accepts a JSON integer; use the commands shown at the
list, selection, or completion prompt. Hints never appear automatically.

## Project layout

- `testfirst/challenges.py`: fixed trusted functions, challenge data, trace steps.
- `testfirst/engine.py`: JSON validation, evaluation, outcomes, hint state.
- `testfirst/__main__.py`: terminal input and display.
- `tests/`: engine, trace, and terminal tests using `unittest`.
- `ENGINEERING_JOURNAL.md`: decisions, actual validation, and limitations.

To add another integer-list challenge, define trusted callables and a `Challenge`
in `challenges.py` and add it to the `CHALLENGES` tuple. The menu uses that tuple.
Each trace is a tuple of explanatory text steps displayed by the same UI loop;
there is no algorithm-specific rendering in the terminal. `min_distinct` adds
the distinct-value requirement to shared validation and displayed input rules.
Different input shapes will still need validation changes. There is no dynamic
code loading or plugin system. The separate tracers must stay aligned with their
trusted functions; tests check intermediate steps and return values.

Completion marks and hints live only in memory and reset when you exit.
Summary hint counts reflect the current count after any replay/reset, not a
lifetime total. There are no accounts, storage, scores,
AI services, or web interface. Player text is parsed with `json.loads` and is
never executed.
