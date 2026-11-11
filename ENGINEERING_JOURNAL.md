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

## 2026-11-11 — localhost browser prototype

### Inspection, scope, and design

Read the existing engine, all three challenge definitions, terminal navigation,
README, and journal before implementation. Checked the existing tests and
callers. `challenges.py`, `engine.py`, and `__main__.py` remain unchanged: the
same fixed trusted functions, reference implementations, validation, hints,
traces, four outcomes, and historical completion marks power both interfaces.
All 30 pre-existing tests still pass.

Used the requested Ponytail skill for focused implementation/cleanup and Hallmark
in prototype/app-screen mode for the new UI. Selected its Console graphite
palette: restrained amber actions, blue Python keywords, system font fallbacks,
monospace code, a top challenge navigation, and specification/code alongside
the test form. Actual challenge content is the material; there are no fabricated
metrics, testimonials, photos, or claims. Design metadata is in `.hallmark/`;
its generated local salt is ignored.

### Implementation decisions

- Added `web.py` using `HTTPServer` and `BaseHTTPRequestHandler`, bound only to
  `127.0.0.1:8000`. Launch command: `python -m testfirst.web`. No dependencies,
  build step, deployment, accounts, database, AI service, or external assets.
- One `BrowserSession` holds three existing `Game` instances. `GET /api/state`
  returns public challenge data/progress; `POST /api/action` handles selection,
  submit, hint, restart, replay, next, and menu transitions. Evaluation delegates
  directly to `Game.evaluate`. Browser JavaScript contains no reference or buggy
  algorithm implementation, and never executes submitted text as code.
- The API serializes only outcome/message for unsuccessful attempts. Expected
  output, actual output, trace, and explanation are returned only after success.
  Unrequested hints are not sent. Replay clears the active result and hints,
  retaining the existing historical completion flag. Last-challenge next shows
  a summary; skipped challenges remain incomplete. Unlike terminal exit after
  summary, the browser summary offers a return to the challenge menu.
- HTTP boundaries enforce JSON object/action/field types, fixed challenge IDs,
  a 16 KiB request limit, and a five-second connection timeout. Only an explicit
  static-file allowlist is served. Host/Origin checks restrict browser requests
  to the documented address; responses disable caching and include a same-origin
  content policy, frame protection, and MIME sniffing protection. This is a local
  prototype, not a production HTTP service.
- Added plain HTML/CSS/JavaScript in `testfirst/static/`. The interface has labelled
  inputs, visible constraints, four text-labelled outcomes, optional hints,
  restart, completion navigation, expected/actual comparison, explanation, and
  Previous/Next/Show all trace controls. Input values survive validation and hint
  requests. Syntax coloring only wraps known Python keywords/numbers in text
  nodes; all dynamic text uses DOM text APIs rather than HTML interpolation.
- Keyboard submission, visible focus, a skip link, help associations, live status
  announcements, deliberate post-action focus, and responsive stacking are
  implemented. Hint requests restore keyboard focus. Narrow code panels scroll
  independently rather than forcing the page wider.
- Ponytail cleanup removed unused scaffold photo/gradient rules, unused type and
  layout helpers, and unused theme tokens. Reused engine state/reset methods
  instead of introducing duplicate validation, evaluation, or a framework.

### Tests and failures actually observed

Ran `python -m unittest discover -s tests -v` on the original suite after adding
the UI/server: all **30 existing tests passed**. The first run with HTTP tests
failed because the sandbox prohibited outgoing loopback socket connections
(`WinError 10013`); API tests were not silently skipped. Re-running with approved
local socket access passed **39 tests**. Added a neutral-example regression test;
the final full run passed **40 tests in 3.272 seconds** on Python 3.13.0.

The ten new HTTP tests use a real ephemeral loopback server and cover initial
state/exactly three challenges; trusted source/specification reuse; all four
outcomes; answer/trace redaction; per-challenge validation; progressive/limited
hints; replay reset and completion retention; invalid action/type/state rejection;
next progression; summaries with skipped challenges; repeated success; new-server
reset; a neutral example for all challenges; static file boundaries; malformed
JSON/UTF-8/nesting; oversized bodies; content types; and Host/Origin restrictions.

`node --check testfirst/static/app.js` passed. Static design lint initially found
three copy issues (a title dash and two button arrows); those were fixed and the
final check reported **0 failures, 0 reflex findings, 0 warnings**. Its automated
render tier could not run because `puppeteer-core` was unavailable; no dependency
was installed solely for it. Direct browser verification below was used instead.
`git diff --check` passed, with only normal Windows line-ending notices.

Ran `python -m testfirst` with a piped `quit`: the three-challenge terminal menu
opened and exited cleanly. The complete existing terminal regression tests also
passed. README now documents both launch commands, exact localhost address,
browser controls, API test socket requirements, and session limitations.

### Actual browser verification

Used the in-app browser against the running local server. The initial sandboxed
preview timed out; restarting it with approved loopback access resolved this.
Checked visible flows for:

- Initial menu, readable Python/specification, constraints, and empty test form.
- `[true]` rejected while both entered values remained in place.
- `[-1]` / prediction `0` producing incorrect-prediction feedback, with expected
  output and trace absent from both the displayed page and hidden result nodes.
- `[2,5,1]` / `5` producing correct-prediction/bug-hidden feedback.
- Optional hint disclosure and hint focus restoration; `[-2,-1]` / `-1` success;
  expected `-1` versus actual `0`; Previous, Next, and Show all trace controls.
- Replay clearing hints and inputs while retaining the completion mark; Restart
  clearing a newly requested hint without altering completion history.
- Skipping challenge two and completing challenge three, producing a correct
  2/3 summary with second-largest explicitly Not completed.
- Returning to the menu, using Next challenge to reach second-largest, rejecting
  `[2,2]`, succeeding with `[1,3,3]` / `1`, advancing to most-frequent, succeeding
  with `[2,1]` / `1`, and showing the final 3/3 summary.
- Tab moving from prediction to submit with a solid visible focus outline, and
  Enter submitting successfully. Checked narrow layouts at 375px and 320px;
  document width did not exceed the viewport, and long code scrolled internally.

A transient browser locator error immediately after resizing was resolved by
refreshing the observed UI and targeting the visible summary-menu control.
Full-page screenshot capture was unavailable, and one oversized viewport capture
was clipped by the browser surface; the final saved screenshot uses the normal
narrow browser surface. Temporary viewport overrides were reset. Restarted the
preview after testing so the left-open session has no completed challenges or
used hints. This was Codex-driven functional verification, not learner testing.

During review, changed the displayed example from `[2,5,1]` to `[1,2,3]`: the
former accidentally exposes the most-frequent tie bug. The new API regression
test confirms the example leaves every challenge's bug hidden.

### Current limitations and contribution

One shared session exists per server process. Multiple tabs share progress but
do not synchronize live; use one tab. Reload retains server progress/hints but
discards unsaved form values. Server restart clears the session. Browser and
terminal progress are separate. Request handling is sequential; this prototype
is for one local learner, not concurrent users or public hosting. Port 8000 must
be free. The existing source-file requirement and hand-maintained traces remain.
Other browsers, Python versions, assistive technologies, and operating systems
were not tested. No learning-effectiveness study or new human user test occurred.

Codex inspected the repository, designed/implemented the browser/API, performed
the focused cleanup, wrote HTTP tests, corrected the example and lint findings,
ran the stated tests and browser checks, updated documentation, and prepared the
requested commit/push. No account, AI API, persistence, scoring, extra challenge,
or deployment work was added.

## 2026-11-11 — explanatory challenge-menu hero

Consolidated the menu's two introductory blocks into one hero using the existing
counterexample heading and the supplied game description: invent an input,
predict the correct output, and learn why the program fails. Added the exact
`Try your first challenge` CTA and the three requested steps: Read the promise,
Design a test, and Discover the bug. Retained the neutral example once below
the steps and kept the existing challenge list below it.

The CTA calls `act("select", { challenge: 0 })`, the same selection flow as the
challenge navigation/list. No duplicate state logic or automatic restart was
added. Everything lives inside the existing menu section, which is hidden on
active challenges and summaries. Steps use a semantic ordered list, three
columns on wide screens, and a single column below 36rem. Buttons reuse existing
colors, dimensions, focus styles, pending handling, and keyboard behavior.

Inspected the current HTML, JavaScript selection/rendering, CSS, and latest
journal before editing. Changed only `static/index.html`, `static/app.js`,
`static/style.css`, and this journal. Removed obsolete introductory styles.
Python challenges, engine, server/API, and terminal behavior are unchanged.

Validation actually performed:

- Ran `python -m unittest discover -s tests -v` with loopback access enabled:
  **all 40 existing tests passed in 2.192 seconds** on Python 3.13.0.
- `node --check testfirst/static/app.js` and `git diff --check` passed. Static
  design lint reported **0 failures, 0 reflex findings, 0 warnings**.
- In the running browser, opened the menu and verified the hero, three steps,
  single neutral example, and existing challenge list. Tab reached the CTA from
  the menu heading with a solid visible focus outline. Enter activated it and
  opened challenge 1, focused its heading, and hid the menu/hero. The existing
  completion mark and three used hints remained intact, confirming selection
  did not silently restart the challenge.
- Returned to the menu. At 375px the steps stacked vertically, the challenge
  list followed them, and document width remained within the viewport. At
  1280px all three steps shared one row, without page overflow. Restored the
  normal browser viewport and saved a narrow-screen preview showing the hero,
  CTA focus, and beginning of the steps.

Codex performed the focused implementation, browser checks, test run, and journal
update, and prepared the requested commit/push. No additional feature or
dependency was introduced. No new human user study was conducted; assistive
technologies, other browsers, and operating systems were not tested. Existing
in-memory session limitations remain.
