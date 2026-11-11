# Engineering journal

## 2026-11-11 — first prototype

### Scope and decisions

The provided GitHub repository was empty and was cloned into `D:\TestFirst`.
There were no existing callers, fixtures, configuration, or exports to preserve.
The implementation reaches challenge definitions, engine state/evaluation,
terminal presentation, tests, run instructions, and this journal.

- Standard-library Python only, with no packaging or dependency installation.
  Python 3.10+ syntax is used; validation was performed on Python 3.13.0.
- `challenges.py` holds the fixed buggy function, reference callable (`max`),
  explanation, three hints, and trace model. Displayed source is read from the
  trusted function with `inspect.getsource`, so it matches the executed code.
- `engine.py` has no terminal I/O. `Game` accepts a `Challenge` directly, making
  another trusted integer-list challenge possible without registration machinery.
  A result enum distinguishes invalid input, incorrect prediction, a correct
  prediction that does not expose the bug, and success. Prediction correctness
  is checked before reporting whether the buggy function disagrees.
- Player input is parsed using `json.loads`. Exact integer type checks reject
  booleans (which are Python integer subclasses), floats, and nested structures.
  Lists enforce both length and inclusive element bounds. Invalid JSON,
  excessive nesting, and Python integer parsing limits yield invalid input.
  Predictions accept any JSON integer; a wrong integer is an incorrect prediction.
- Only fixed trusted callables execute. There is no evaluation or execution of
  player-provided source. Invalid attempts never call the challenge function.
- Trace steps record initialization and each comparison's before/after values
  and update flag. The tracer separately mirrors the tiny buggy loop; explicit
  and exhaustive short-list tests guard against divergence.
- Hints advance only on request and stop after three. Retries preserve the hint
  count; restart resets it. After success the game explains the fault and allows
  more attempts. Commands are recognized at the list prompt. EOF/Ctrl+C exits
  cleanly from either prompt.

### Validation actually run

Ran `python -m unittest discover -s tests -v` twice during implementation.
The final run passed **12 tests** in **0.461 seconds** on Python 3.13.0.
Coverage includes positive, all-negative, zero, mixed-sign, single-element,
eight-element, -20/20 boundary inputs; incorrect predictions (including the
buggy answer); malformed JSON; invalid types; out-of-range values; excessive
nesting and oversized integers; optional hints and restart; terminal retries,
all outcome messages, and EOF/Ctrl+C handling at both prompts.

Trace tests check initialization, strict comparisons, equality/no update,
updates, ordering, and final output. They exhaustively cover all 70,643 lists
of lengths 1–3 using every integer from -20 through 20, comparing each trace
with the trusted buggy function. They do not exhaustively enumerate lengths 4–8.

Also launched the actual entry point with piped input using
`python -m testfirst`: requested one hint, submitted `[-5, -2]` with `-2`,
observed expected `-2` versus actual `0` and both non-updating iterations,
restarted, submitted `[0, 20, -20]` with `20`, observed the no-bug result,
and quit with zero hints after the reset. This was an automated smoke check,
not a session with a learner.

### Limitations and deferred work

- One challenge, terminal only, in-memory hint state. No accounts, database,
  AI API, scoring, web UI, or persistence were added.
- Shared validation currently assumes bounded integer lists. The terminal trace
  renderer assumes `best` and `number`. New input types or algorithms will need
  explicit validation and display changes.
- The trace and buggy loop must be updated together when changing the challenge.
  Source display assumes the project's Python source files remain available.
- The terminal reads an entire line before validation; there is no input-byte
  cap. This local prototype is not designed as an untrusted network service.
- Other Python versions, operating systems, and interactive terminal accessibility
  have not been tested. There has been no learner/user testing, and no claims
  are made about learning effectiveness.

### Work performed by Codex

Codex inspected and cloned the empty repository, designed and wrote all project
code, tests, `.gitignore`, README, and this journal, ran the tests and terminal
smoke check, and reviewed their output. The user subsequently requested publishing
the prototype to the provided GitHub repository; Codex prepared the initial commit
and push. Publication status is reported in the chat and Git history.
