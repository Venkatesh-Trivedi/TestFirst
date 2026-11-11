"use strict";

const $ = (id) => document.getElementById(id);
let state;
let pending = false;
let traceIndex = 0;
let showAll = false;

function element(tag, text, className) {
  const node = document.createElement(tag);
  node.textContent = text;
  if (className) node.className = className;
  return node;
}

function actionButton(text, action, extra = {}) {
  const button = element("button", text);
  button.addEventListener("click", () => act(action, extra));
  return button;
}

function showCode(source) {
  $("source").replaceChildren();
  // Styling only: these tokens never participate in challenge evaluation.
  for (const token of source.split(/(\b(?:def|for|in|if|return)\b|\b\d+\b)/g)) {
    const style = /^(def|for|in|if|return)$/.test(token) ? "keyword" : /^\d+$/.test(token) ? "literal" : "";
    $("source").append(element("span", token, style));
  }
}

function renderTrace() {
  const steps = state.result.trace;
  $("trace-steps").replaceChildren();
  const visible = showAll ? steps : [steps[traceIndex]];
  visible.forEach((step) => $("trace-steps").append(element("li", step)));
  $("trace-steps").start = showAll ? 1 : traceIndex + 1;
  $("step-count").textContent = showAll ? `All ${steps.length} steps` : `Step ${traceIndex + 1} of ${steps.length}`;
  $("previous").disabled = !showAll && traceIndex === 0;
  $("step-next").disabled = !showAll && traceIndex === steps.length - 1;
  $("show-all").textContent = showAll ? "Show one step" : "Show all";
  $("show-all").setAttribute("aria-pressed", String(showAll));
}

function render() {
  const completed = state.challenges.filter((challenge) => challenge.completed).length;
  $("progress").textContent = `${completed} of ${state.challenges.length} completed`;
  $("navigation").replaceChildren();
  $("challenge-list").replaceChildren();
  for (const challenge of state.challenges) {
    const status = challenge.completed ? "Complete" : "Not completed";
    const nav = actionButton(`${challenge.id + 1}. ${challenge.title} · ${status}`, "select", { challenge: challenge.id });
    if (state.view === "challenge" && state.selected === challenge.id) nav.setAttribute("aria-current", "page");
    $("navigation").append(nav);
    const row = element("div", "", "challenge-row");
    const description = element("div", "");
    description.append(element("h2", challenge.title), element("p", challenge.specification), element("span", status, "muted"));
    row.append(description, actionButton(challenge.completed ? "Open again" : "Start challenge", "select", { challenge: challenge.id }));
    $("challenge-list").append(row);
  }
  $("menu").hidden = state.view !== "menu";
  $("practice").hidden = state.view !== "challenge";
  $("summary").hidden = state.view !== "summary";
  if (state.view === "summary") {
    $("summary-count").textContent = `You completed ${completed} of ${state.challenges.length} challenges this session.`;
    $("summary-list").replaceChildren();
    for (const challenge of state.challenges) {
      const row = element("div", "", "summary-row");
      row.append(element("h2", challenge.title), element("p", challenge.completed ? "Complete" : "Not completed"), element("p", `Hints used: ${challenge.hints_used}/${challenge.hint_total}`, "muted"));
      $("summary-list").append(row);
    }
    return;
  }
  if (state.view !== "challenge") return;
  const challenge = state.challenges[state.selected];
  $("position").textContent = `Challenge ${state.selected + 1} of ${state.challenges.length}`;
  $("challenge-title").textContent = challenge.title;
  $("specification").textContent = challenge.specification;
  $("constraints").textContent = challenge.input_rules;
  showCode(challenge.source);
  $("hint-count").textContent = `${challenge.hints_used} of ${challenge.hint_total} hints used · always optional`;
  $("hints").replaceChildren(...challenge.hints.map((hint) => element("li", hint)));
  $("hint").disabled = challenge.hints_used === challenge.hint_total;
  const result = state.result;
  const success = result?.outcome === "success";
  $("success").hidden = !success;
  $("attempt-form").hidden = success;
  $("hint").disabled ||= success;
  $("feedback").dataset.outcome = result?.outcome || "empty";
  const titles = {
    invalid_input: "Invalid input",
    incorrect_prediction: "Incorrect prediction",
    no_bug: "Correct prediction. Bug still hidden.",
    success: "Challenge complete.",
  };
  $("feedback-title").textContent = result ? titles[result.outcome] : "What will your test reveal?";
  $("feedback-message").textContent = result ? result.message : "Enter a list and your prediction to compare the specification with the program. Hints are here if you want them.";
  if (success) {
    $("expected").textContent = result.expected;
    $("actual").textContent = result.actual;
    $("explanation").textContent = result.explanation;
    $("next-challenge").textContent = state.selected === state.challenges.length - 1 ? "Session summary" : "Next challenge";
    renderTrace();
  } else {
    // Remove prior answers from the document, including hidden content.
    for (const id of ["expected", "actual", "explanation", "trace-steps"]) $(id).replaceChildren();
  }
}

async function act(action, extra = {}) {
  if (pending) return;
  pending = true;
  $("notice").textContent = "Working…";
  $("main").setAttribute("aria-busy", "true");
  document.querySelectorAll("button").forEach((button) => { button.disabled = true; });
  try {
    const response = await fetch("/api/action", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action, ...extra }),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Could not complete that action.");
    state = data;
    if (["select", "next", "replay", "restart", "menu"].includes(action)) $("attempt-form").reset();
    if (action !== "hint") { traceIndex = 0; showAll = false; }
    $("notice").textContent = action === "hint" ? state.challenges[state.selected].hints.at(-1) || "All hints used." : action === "replay" || action === "restart" ? "Restarted. Hints reset; completed challenges stay marked." : "";
    document.querySelectorAll("button").forEach((button) => { button.disabled = false; });
    render();
    if (action === "submit") {
      // The live region carries the outcome; focus makes the next action easy to find.
      $("notice").textContent = `${$("feedback-title").textContent} ${state.result.message}`;
      $("feedback").focus();
    } else if (action === "hint") {
      $($("hint").disabled ? "hint-title" : "hint").focus();
    } else {
      $(state.view === "menu" ? "menu-title" : state.view === "summary" ? "summary-title" : "challenge-title").focus();
    }
  } catch (error) {
    $("notice").textContent = `Connection or request error: ${error.message} Your entered values are still here. Try the action again.`;
    document.querySelectorAll("button").forEach((button) => { button.disabled = false; });
    if (state) render();
  } finally {
    pending = false;
    $("main").removeAttribute("aria-busy");
  }
}

$("attempt-form").addEventListener("submit", (event) => {
  event.preventDefault();
  act("submit", { numbers: $("numbers").value, prediction: $("prediction").value });
});
for (const id of ["back-menu", "success-menu", "summary-menu"]) $(id).addEventListener("click", () => act("menu"));
$("first-challenge").addEventListener("click", () => act("select", { challenge: 0 }));
for (const action of ["hint", "restart", "replay"]) $(action).addEventListener("click", () => act(action));
$("next-challenge").addEventListener("click", () => act("next"));
$("previous").addEventListener("click", () => { showAll = false; traceIndex = Math.max(0, traceIndex - 1); renderTrace(); });
$("step-next").addEventListener("click", () => { showAll = false; traceIndex = Math.min(state.result.trace.length - 1, traceIndex + 1); renderTrace(); });
$("show-all").addEventListener("click", () => { showAll = !showAll; renderTrace(); });

async function start() {
  try {
    const response = await fetch("/api/state");
    if (!response.ok) throw new Error("The session could not be loaded.");
    state = await response.json();
    render();
    $("notice").textContent = "";
  } catch (error) {
    $("notice").textContent = `Unable to load challenges. ${error.message} Reload the page to try again.`;
  }
}
start();
