# TestFirst

A browser and terminal prototype of a beginner programming game. Invent a list that
exposes a bug, predict the correct output, then inspect what the buggy program did.
No learning outcomes or user testing have been measured.

Requires Python 3.10 or newer. Uses only the Python standard library; no install
or dependency setup is required. Run these commands from the repository root.

Launch the browser version:

```powershell
python -m testfirst.web
```

Open [TestFirst locally](http://127.0.0.1:8000). The server binds only to
`127.0.0.1:8000`; stop it with Ctrl+C in its terminal. Use that exact address
(rather than `localhost`). Port 8000 must be available. No build step, package
manager, network assets, or internet connection is needed.

The terminal version remains available:

```powershell
python -m testfirst
```

Run the tests:

```powershell
python -m unittest discover -s tests -v
```

The API tests start a real loopback HTTP server on an ephemeral port. Sandboxed
environments must allow local socket connections; they are not skipped silently.

## Playing in the browser

Choose one of the three challenges. Read its specification and the fixed Python
program, enter a JSON list and predicted correct integer in the separate fields,
then select **Test my prediction**. The visible constraints come from the Python
challenge definition. All validation/evaluation runs in the same engine used by
the terminal; JavaScript only displays state and formats code.

The example `[1, 2, 3]` demonstrates input syntax without exposing any of the
three bugs. Feedback distinguishes invalid input, incorrect prediction, a
correct prediction that leaves the bug hidden, and a successful counterexample.
Invalid entries stay in the fields. Incorrect predictions reveal neither the
correct answer nor the program's result, trace, or explanation in the API or UI.

Hints are optional, revealed one at a time, and limited to three per challenge.
**Restart** clears the fields, current feedback, and current hints. Success
announces **Challenge complete.**, hides the attempt form, and shows expected
versus actual output, the explanation, and the execution trace. **Previous** and
**Next** move one step at a time; **Show all** toggles the complete trace.

After success, choose **Next challenge**, **Replay**, or **Challenge menu**.
On the last challenge, **Session summary** takes the place of Next challenge and
lists completed and skipped challenges with their current hint counts. Replay
resets current hints and fields, retaining the historical completion mark.
Navigation also marks each challenge Complete or Not completed. The summary
offers a return to the menu, so you can complete skipped challenges.

Keyboard controls use normal Tab, Shift+Tab, and Enter behavior. Fields have
labels and help text, focus is visible, outcome/hint messages are announced by
a live status region, and code can scroll independently on narrow screens.

Browser progress uses an independent **signed cookie per browser profile**.
Refresh restores selection, hints, completion, feedback, and successful traces.
Different browsers/private profiles are isolated; tabs in the same profile share
the cookie and do not synchronize live. Unsaved field values survive validation
and hint requests but not reload/navigation. Terminal and browser sessions remain
separate.

Cookies expire after 24 hours of inactivity. Clear the site's cookies to reset
all browser progress. Without configuration, local development generates an
ephemeral `TESTFIRST_SESSION_SECRET` in the process environment; restarting the
process invalidates old local cookies. To retain local progress across restarts,
set that variable to the same private random value before the launch command.
No `.env` loader or secret file is needed.

## Vercel deployment

The repository uses Vercel's [file-based Python handler](https://vercel.com/docs/functions/runtimes/python/api-directory),
with `api/index.py` delegating to the same HTTP handler/engine as local development.
No framework or package dependencies are required. `.python-version` pins Python
3.13 using Vercel's [supported version setting](https://vercel.com/docs/functions/runtimes/python/python-version).

Import this GitHub repository as a Vercel project with these settings:

| Setting | Value |
| --- | --- |
| Framework Preset | Other |
| Root Directory | Repository root (`.`) |
| Build Command | Leave unset; no frontend build is needed |
| Install Command | Leave unset; no third-party Python dependencies |
| Output Directory | `testfirst/static` (already set in `vercel.json`) |
| Production Branch | `main` |

Before deploying, configure these environment variables in **Project Settings →
Environment Variables**. Do not put secret values in Git or `vercel.json`:

| Variable | Configuration |
| --- | --- |
| `TESTFIRST_SESSION_SECRET` | Required for Production and Preview. Use a private, randomly generated value with at least 32 bytes; all instances within the same environment must use the same value. Use different values for Production and Preview. Missing/short values cause API requests to return 503; production never generates a fallback secret. |
| `TESTFIRST_ALLOWED_ORIGINS` | Set the exact Production HTTPS origin, for example `https://your-project.vercel.app`. Add custom domains as comma-separated HTTPS origins, e.g. `https://your-project.vercel.app,https://practice.example.com`. No paths or trailing slashes. Configure stable preview aliases here in Preview if needed. |
| `VERCEL_URL` | Supplied by Vercel, not a manually committed value. Its generated HTTPS deployment origin is allowed automatically, including Preview deployments. Enable automatic system environment variables in Vercel. |

To generate a secret privately on your machine:

```powershell
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Paste the output directly into Vercel's environment-variable UI; do not paste it
into issues, chat, the journal, or tracked files. Redeploy after environment changes.
`.env`, `.env.*`, and `.vercel/` are ignored as a precaution; no real secret is
included in this repository. Setting the environment variable is also supported
for local development. The terminal game needs no secret.

`vercel.json` serves the existing frontend directory statically and rewrites
`/api/state` and `/api/action` to the Python function, with explicit route markers.
Frontend URLs and JavaScript are unchanged. Python source and tests are outside
the static output directory. Response headers disable caching and restrict content
to the same origin. The handler accepts both original and rewritten API paths.

On Vercel the cookie is `Secure`, `HttpOnly`, `SameSite=Strict`, host-only, and
scoped to `/`. Its value is capped at 2,048 characters (the full header remains
below the usual 4 KiB cookie budget), HMAC-SHA256 signed, versioned, and time-limited.
Only selection/view, three hint counts, three completion flags, compact feedback,
and the last successful input are stored. Hint text, reference answers,
explanations, predictions, and traces are absent; Python reconstructs successful
details after validating the signature, expiry, schema, and input. Cookies are
signed **not encrypted**: their own submitted successful input/progress is readable
by the browser owner. Missing, tampered, expired, or invalid cookies start a fresh
session. Secret rotation invalidates existing cookies.

API requests validate Host against the configured origins and compare Origin
to that exact host over HTTPS; mutation requests require Origin. Cross-origin
fetch metadata is rejected. The handler does not trust arbitrary forwarded-host
or forwarded-protocol headers. Local development retains its exact loopback
Host/Origin checks and uses HTTP cookies without Secure.

Limits: clearing cookies loses progress; copying a valid cookie copies that
session, and old signed cookies can be replayed until expiry. Concurrent tabs
can overwrite each other's latest state, so use one tab per profile. Cookies
are not accounts or an anti-cheat system; no database, centralized revocation,
or cross-device synchronization is implemented. No actual Vercel deployment or
cloud build has been run as part of this preparation. After deploying, check
the menu, API requests, secure cookies, and completion flow on the real HTTPS URL.

## Playing in the terminal

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
- `testfirst/web.py`: shared HTTP handler, per-request browser state/navigation, local server.
- `testfirst/cookies.py`: bounded session signing, expiry, and cookie handling.
- `api/index.py`: Vercel handler and rewrite adaptation; `vercel.json`: static/API routing.
- `testfirst/static/`: HTML, CSS, and JavaScript, served from an explicit file allowlist.
- `tests/`: engine, trace, terminal, and HTTP API tests using `unittest`.
- `ENGINEERING_JOURNAL.md`: decisions, actual validation, and limitations.

To add another integer-list challenge, define trusted callables and a `Challenge`
in `challenges.py` and add it to the `CHALLENGES` tuple. The menu uses that tuple.
Each trace is a tuple of explanatory text steps displayed by the same UI loop;
there is no algorithm-specific rendering in the terminal. `min_distinct` adds
the distinct-value requirement to shared validation and displayed input rules.
Different input shapes will still need validation changes. There is no dynamic
code loading or plugin system. The separate tracers must stay aligned with their
trusted functions; tests check intermediate steps and return values.

Terminal completion marks and hints live only in memory and reset on exit.
Browser progress lives in the signed cookie and survives fresh backend instances
when they share the configured signing secret.
Summary hint counts reflect the current count after any replay/reset, not a
lifetime total. There are no accounts, storage, scores, or AI services.
Player text is parsed with `json.loads` and is
never executed.
