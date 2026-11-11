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

## 2026-11-11 — three-challenge terminal update

### Changes and decisions

- Split list parsing into `parse_numbers`, shared by the terminal and engine.
  The UI validates before requesting a prediction, while `Game.evaluate` still
  independently validates both fields for callers outside the terminal.
- Added the exact completion message `Challenge complete.` after success.
  Retrying, requesting hints, restarting, and quitting remain available.
- Added a startup menu and `menu` command, backed by a fixed `CHALLENGES` tuple.
  One in-memory `Game` per challenge preserves its hint count across switches.
  Restart resets only the selected game's hints. Invalid menu choices retry;
  quit, EOF, and Ctrl+C work from the menu as well as the game prompts.
- Added second-largest DISTINCT: the buggy function sorts without deduplicating
  and returns the penultimate element; the reference sorts a set. Validation
  requires at least two distinct integers, preventing undefined second-largest
  results and unsafe indexing. Its trace shows the input, sorted list retaining
  duplicates, chosen index/value, and return.
- Added most-frequent: the buggy function counts correctly but selects the first
  encountered key on ties; the reference selects the smallest tied value. Its
  trace shows initial counts, every increment and count snapshot, key order,
  maximum frequency, the first-key tie rule, and return.
- Each challenge has an explicit specification, three optional progressive hints,
  and an explanation. All share the existing 1–8 integers in [-20, 20] rules and
  strict JSON/type validation; only second-largest adds a distinctness constraint.
- Replaced the original `TraceStep` model with `tuple[str, ...]` trace steps.
  The UI simply prints each step. This changes the internal trace API and tests
  together, preserving the original largest-number details and adding an explicit
  return step. No plugin framework or dependencies were introduced.
- Reviewed all original trace, parsing, and game callers before editing. Updated
  challenge definitions, engine, terminal, existing tests, and README; added
  `tests/test_challenges.py`. No stored data exists to migrate or destroy.

### Validation actually run

Ran `python -m unittest discover -s tests -v` twice for this update; both runs
passed all **22 tests**. The final run took **1.433 seconds** on Python 3.13.0.
Ran `git diff --check` successfully (Git also reported normal Windows line-ending
conversion warnings).

The original 70,643 short-list trace checks remain. New tests cover all four
outcomes for each new challenge, duplicate maxima, duplicates below the maximum,
negative and mixed-sign values, zero, singleton most-frequent lists, boundary
values, eight-element lists, tied and unique modes, incorrect predictions,
invalid predictions, and challenge-specific validation. Mocked callables verify
invalid attempts do not execute either trusted implementation.

Exact trace assertions cover duplicate sorting/selection and every count update
in a tied-frequency example. Exhaustive new-challenge checks enumerate all 3,905
lists of lengths 1–5 over [-2, 2], skipping second-largest lists with fewer than
two distinct values. They verify references against independent expected results,
trace returns against buggy functions, count snapshots, outcomes, and that inputs
are not mutated. This is not exhaustive coverage of the full allowed domain.

Terminal tests verify invalid lists never prompt for predictions; all three menu
selections; invalid menu choices; menu exit; hint preservation across switches;
restart isolation; completion text; generic traces; retry; and EOF/Ctrl+C at
startup menu, return menu, list, and prediction prompts.

Also ran the real `python -m testfirst` entry point with piped inputs: selected
challenge 1, rejected an empty line before prediction, completed `[-2,-3,-4]`
with `-2`, switched to challenge 2, rejected `[2,2]` before prediction, completed
`[1,3,3]` with `1`, switched to challenge 3, completed `[2,1]` with `1`, restarted,
and quit. All three completion messages, outputs, and traces were observed.

### Current limitations and Codex work

The initial entry above is a historical record; its one-challenge and fixed
best/number renderer limitations are superseded by this update. State still
exists only for the current process. Prediction prompts still accept JSON
integers only; commands belong to list/menu prompts. Tracers are hand-maintained
alongside trusted functions and must be kept synchronized. New non-list inputs
would require explicit validation changes. Source display still requires source
files, and terminal lines have no byte cap.

Codex performed all implementation, test and documentation edits, test runs,
smoke checks, and output review for this update, and prepared the commit/push
under the user's earlier publication request. No learner testing was conducted
by Codex and no learning-effectiveness claims are made. The user's earlier
terminal transcript supplied usability feedback. Other Python versions and
operating systems were not checked; no web UI, persistence, scoring, accounts,
AI services, or plugin system were added.

## 2026-11-11 — dedicated completion menu

### Changes and decisions

The user's screenshot showed that the post-success list prompt was confusing.
This update replaces that flow with `Completion menu [next / menu / replay / quit]`
after the success explanation and trace. It supersedes the earlier documented
behavior of automatically returning to another list attempt after success.

- `next` opens the next challenge in the fixed menu order. From the last
  challenge it prints a session summary and exits. The summary reports each
  challenge's completion status and current hint count; skipped challenges stay
  incomplete. There is no score or requirement to complete earlier challenges.
- `menu` returns to challenge selection. Completed entries show `[complete]`.
- `replay` calls the existing restart method to reset only the current game's
  hints before displaying its specification/function and requesting another list.
- `quit` exits. Empty input, list text, and unsupported commands at completion
  produce an invalid-choice message and keep the completion menu open.
- `Game.completed` is set only on a successful evaluation. It records having
  solved that challenge at least once; replay, restart, and later failures retain
  it. Repeated successes cannot inflate the summary count. New process/game
  instances start incomplete. Selection from the main menu still opens a
  challenge for attempts with its current hints, including completed entries.

Reviewed the terminal selection and attempt loop, engine state, and their tests
before editing. Changes reach `engine.py`, `__main__.py`, both existing engine
and terminal test files, README, and this journal. Existing specifications,
validation, trusted functions, traces, and the four attempt outcomes are
unchanged. No dependencies, storage, or general navigation framework were added.

### Validation actually run

Ran `python -m unittest discover -s tests -v`: **30 tests passed** in **1.802
seconds** on Python 3.13.0. This includes all previous algorithm/trace checks.
New tests verify success-only completion state, persistence through replay and
failed attempts, completion-menu invalid choices, no automatic list prompt,
next through all challenges, summary after last, skipped challenges, completion
markers, per-game hint reset/isolation, repeated success counted once, new
session reset, and clean EOF/Ctrl+C handling at completion and the prompts reached
by menu/replay/next. Updated prior success/retry tests to request replay explicitly.

Ran the actual `python -m testfirst` entry point with piped input: selected the
first challenge, requested one hint, succeeded, entered an invalid completion
choice, replayed with hints reset, succeeded again, returned to the main menu
and observed its completion mark, selected challenge two, completed it, used next
to open challenge three, completed it, and used next to print the 3/3 summary and
exit. No direct list prompt appeared after success without an explicit replay
or challenge selection/navigation action. Ran `git diff --check` successfully;
Git reported only the usual Windows line-ending conversion warnings.

### Limitations and Codex work

Completion marks and hints are process-local. Summary hint counts reflect resets,
not lifetime usage. After the last challenge, next ends the session after showing
the summary; use menu instead to continue exploring. No new user study or learning
evaluation was conducted. Other Python versions and operating systems were not
tested; prior source-file/line-size and hand-maintained-trace limitations remain.

Codex implemented the changes, updated tests/docs, ran the full suite and terminal
smoke check, reviewed results, and prepared the commit and push under the user's
existing publication request.
