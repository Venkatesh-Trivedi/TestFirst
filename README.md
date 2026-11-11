# TestFirst

A first terminal prototype of a beginner programming game. Invent a list that
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

The first challenge is **Find the largest number**. Read its specification and
buggy function, enter a JSON list such as `[2, 5, 1]`, then enter your predicted
correct output as a JSON integer, such as `5`.

Lists must contain 1 through 8 integers, each between -20 and 20 inclusive.
Booleans, floats, non-list values, and malformed JSON are rejected. Predictions
must be JSON integers; an integer outside the list's allowed range is accepted
as an incorrect prediction.

The game distinguishes invalid input, incorrect prediction, correct prediction
without exposing the bug, and success. Success displays expected and actual
outputs, the initial `best`, every loop comparison and update decision, and an
explanation. Try another list after any outcome.

At the **list prompt**, enter `hint` for the next of three optional hints,
`restart` to redisplay the challenge and reset the hint count, or `quit` to exit.
Retrying preserves the hint count. EOF or Ctrl+C exits cleanly at either prompt.
Commands are only recognized at the list prompt; the prediction prompt accepts
a JSON integer. Hints never appear automatically.

## Project layout

- `testfirst/challenges.py`: fixed trusted functions, challenge data, trace steps.
- `testfirst/engine.py`: JSON validation, evaluation, outcomes, hint state.
- `testfirst/__main__.py`: terminal input and display.
- `tests/`: engine, trace, and terminal tests using `unittest`.
- `ENGINEERING_JOURNAL.md`: decisions, actual validation, and limitations.

To add another integer-list challenge, define trusted callables and a `Challenge`
in `challenges.py`, pass it to `Game(challenge=...)`, and select it in the terminal
entry point. The current validation rules and `best`/`number` trace display suit
this first challenge; different input shapes or algorithms will need corresponding
validation and display changes. There is no dynamic code loading or plugin system.

Progress and hints live only in memory. There are no accounts, storage, scores,
AI services, or web interface. Player text is parsed with `json.loads` and is
never executed.
