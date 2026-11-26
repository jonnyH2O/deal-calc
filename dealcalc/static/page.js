// Calculator Page: shows the calculator and sends every input change to the Page Host.
// Owner: Ben Horrisberger (Project Plan M11, M12). Skeleton: Jonny Heinrich.
// Design: SDS Section 4.7 and the state machine in Figure 3. Requirements: R6 to R13, R15, R16.
//
// This file does no math and holds almost no wording: the Python side sends every number already worked out and
// formatted, and every explanation comes from GET /text. The only words here are labels and the message shown
// when the page cannot reach the calculator at all (it cannot ask the calculator for that message).
//
// The "Load reports" window (not yet in the SDS) sends one or two property reports to POST /read-reports, which
// finds their inputs; the page fills them in and asks for an evaluation as if they had been typed.

"use strict";

// The field names shared with the Python side (deal_math.INPUT_FIELDS and RESULT_FIELDS), in display order.
const INPUT_FIELDS = ["price", "monthly_rent", "vacancy_pct", "operating_costs"];
const RESULT_FIELDS = ["gpr", "egi", "noi", "cap_rate_pct"];
const PROPERTIES = ["A", "B"];
// Results whose side-by-side values are market context rather than a score, so their delta is shown plainly (R13).
const CONTEXT_FIELDS = ["cap_rate_pct"];
const NOT_YET = "—"; // "—", shown where a number cannot be worked out yet
const CANNOT_REACH = "This page can't reach the calculator. Start it with python -m dealcalc, then reload this page.";

const state = {
  mode: "single",            // "single" or "comparison" (R11)
  inputs: { A: {}, B: {} },  // typed text, keyed by field name
  latestSeq: 0,              // number of the newest POST /evaluate sent
  nextSample: 0,             // which sample deal "try a sample deal" loads next; the first is the SRS sample (R5)
};
let pageText = null;         // the answer to GET /text

const byId = (id) => document.getElementById(id);

// ---------------------------------------------------------------- loading (Figure 3: "Loading page text")

// At page load, get GET /text and fill in the purposes, definitions, and cap rate note. If the request fails,
// show a message to start the calculator and then reload the page.
async function loadText() {
  try {
    const response = await fetch("/text");
    if (!response.ok) {
      throw new Error(`GET /text answered ${response.status}`);
    }
    pageText = await response.json();
  } catch (problem) {
    showProblem(CANNOT_REACH);  // Figure 3: "Cannot reach calculator"
    return;
  }
  byId("page-purpose").textContent = pageText.page_purpose;
  showInfoHint(pageText.info_hint);
  for (const section of ["inputs", "results", "comparison"]) {
    byId(`${section}-purpose`).textContent = pageText.section_purposes[section];
  }
  byId("cap-rate-note").textContent = pageText.cap_rate_note;
  byId("reports-purpose").textContent = pageText.reports_purpose;
  buildRows();
  connectControls();
  requestEvaluation();  // shows a hint under each empty input
}

// "Press {icon} next to any ..." with a picture of the info button where {icon} is.
function showInfoHint(hint) {
  const [before, after] = hint.split("{icon}");
  const icon = document.createElement("span");
  icon.className = "info-icon";
  icon.textContent = "i";
  icon.setAttribute("role", "img");
  icon.setAttribute("aria-label", "the info button");
  byId("info-hint").replaceChildren(before, icon, after);
}

// One row per input and per result, with a cell for each property and one for the delta.
function buildRows() {
  for (const field of INPUT_FIELDS) {
    const row = labelRow(field, true);
    for (const property of PROPERTIES) {
      const cell = document.createElement("td");
      cell.className = property === "B" ? "comparison-only" : "";
      const input = document.createElement("input");
      input.type = "text";
      input.inputMode = "decimal";
      input.autocomplete = "off";
      input.id = `input-${property}-${field}`;
      input.setAttribute("aria-label", `${pageText.definitions[field].name}, Property ${property}`);
      input.setAttribute("aria-describedby", `message-${property}-${field}`);
      input.addEventListener("input", () => {
        state.inputs[property][field] = input.value;
        requestEvaluation();
      });
      cell.append(input, messageSlot(`message-${property}-${field}`));
      row.append(cell);
    }
    row.append(deltaCell(field));
    byId("inputs").append(row);
  }
  for (const field of RESULT_FIELDS) {
    const row = labelRow(field, false);
    for (const property of PROPERTIES) {
      const cell = document.createElement("td");
      cell.className = property === "B" ? "value comparison-only" : "value";
      const value = document.createElement("span");
      value.className = "result";
      value.id = `result-${property}-${field}`;
      value.textContent = NOT_YET;
      const formula = document.createElement("span");
      formula.className = "formula explanation";
      formula.id = `formula-${property}-${field}`;
      cell.append(value, formula, messageSlot(`message-${property}-${field}`));
      row.append(cell);
    }
    row.append(deltaCell(field));
    byId("results").append(row);
  }
}

// The left-hand cell: the item's name and info button, its definition, and, for inputs, where to find it on a
// listing. The row is what the info button opens, so for results it also shows the worked formulas.
function labelRow(field, isInput) {
  const entry = pageText.definitions[field];
  const row = document.createElement("tr");
  row.className = "explainable";
  const label = document.createElement("th");
  label.scope = "row";
  const name = document.createElement("span");
  name.className = "item-name";
  name.textContent = entry.name;
  if (isInput) {
    const forInput = document.createElement("label");
    forInput.htmlFor = `input-A-${field}`;
    forInput.append(name);
    label.append(forInput);
  } else {
    label.append(name);
  }
  label.append(infoButton(row, entry.name));
  if (CONTEXT_FIELDS.includes(field)) {
    const tag = document.createElement("span");
    tag.className = "tag comparison-only";
    tag.textContent = pageText.cap_rate_tag;
    label.append(tag);
  }
  label.append(explanation(entry.definition));
  if (isInput) {
    label.append(explanation(`Where to find it: ${entry.where_to_find}`));
  }
  row.append(label);
  return row;
}

function explanation(text) {
  const paragraph = document.createElement("p");
  paragraph.className = "explanation";
  paragraph.textContent = text;
  return paragraph;
}

function messageSlot(id) {
  const slot = document.createElement("p");
  slot.className = "message";
  slot.id = id;
  slot.setAttribute("aria-live", "polite");
  return slot;
}

function deltaCell(field) {
  const cell = document.createElement("td");
  cell.className = "value comparison-only";
  const delta = document.createElement("span");
  delta.id = `delta-${field}`;
  delta.textContent = NOT_YET;
  cell.append(delta);
  return cell;
}

function connectControls() {
  byId("mode-single").addEventListener("click", () => switchMode("single"));
  byId("mode-comparison").addEventListener("click", () => switchMode("comparison"));
  byId("sample-deal").addEventListener("click", fillSample);
  byId("load-reports").addEventListener("click", openReports);
  byId("read-reports").addEventListener("click", readReports);
  byId("close-reports").addEventListener("click", () => byId("report-dialog").close());
  // a property's report is a file or pasted text, whichever was chosen last, so what shows is what will be read
  for (const property of PROPERTIES) {
    const file = byId(`report-file-${property}`);
    const text = byId(`report-text-${property}`);
    file.addEventListener("change", () => { text.value = ""; });
    text.addEventListener("input", () => { file.value = ""; });
  }
  // the section info buttons are in page.html; each names the element it explains in data-explains
  for (const button of document.querySelectorAll(".info[data-explains]")) {
    const explainable = byId(button.dataset.explains);
    button.addEventListener("click", () => toggleExplanation(button, explainable));
  }
}

// ---------------------------------------------------------------- the report (Figure 3: the "Report" region)

// After every input change, send POST /evaluate with the next seq number.
async function requestEvaluation() {
  state.latestSeq += 1;
  const seq = state.latestSeq;
  const body = { A: state.inputs.A, B: state.mode === "comparison" ? state.inputs.B : null, seq };
  try {
    const response = await fetch("/evaluate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    const answer = await response.json();
    if (!response.ok) {
      if (seq === state.latestSeq) {
        showProblem(answer.error);
      }
      return;
    }
    render(answer);
  } catch (problem) {
    if (seq === state.latestSeq) {
      showProblem(CANNOT_REACH);
    }
  }
}

// Show the report only if its seq is the latest one sent, so a slow older answer never replaces a newer one.
function render(report) {
  if (report.seq !== state.latestSeq) {
    return;  // Figure 3: "report [older seq] / ignore it"
  }
  hideProblem();
  const shown = state.mode === "comparison" ? PROPERTIES : ["A"];
  for (const property of shown) {
    const view = report[property];
    for (const field of INPUT_FIELDS) {
      showInputMessage(property, field, view);
    }
    for (const field of RESULT_FIELDS) {
      byId(`result-${property}-${field}`).textContent = view.results ? view.results[field] : NOT_YET;
      byId(`formula-${property}-${field}`).textContent = view.formulas ? view.formulas[field] : "";
      setMessage(`message-${property}-${field}`, view.warnings[field] || "", "warning");
    }
  }
  for (const field of [...INPUT_FIELDS, ...RESULT_FIELDS]) {
    const delta = byId(`delta-${field}`);
    const text = report.deltas ? report.deltas[field] : NOT_YET;
    delta.textContent = text;
    delta.className = report.deltas ? (CONTEXT_FIELDS.includes(field) ? "delta context" : "delta") : "";
  }
  const deltasMessage = byId("deltas-message");
  deltasMessage.textContent = report.deltas_message || "";
  deltasMessage.hidden = !report.deltas_message;
}

// An error under an input is red, except for an input the member has not filled in yet, where the same message is
// a gentle hint saying what to enter. Warnings (R3) still show the results.
function showInputMessage(property, field, view) {
  const input = byId(`input-${property}-${field}`);
  const error = view.errors[field];
  if (error) {
    const isEmpty = input.value.trim() === "";
    setMessage(`message-${property}-${field}`, error, isEmpty ? "hint" : "error");
    input.setAttribute("aria-invalid", String(!isEmpty));
  } else {
    setMessage(`message-${property}-${field}`, view.warnings[field] || "", "warning");
    input.setAttribute("aria-invalid", "false");
  }
}

function setMessage(id, text, kind) {
  const slot = byId(id);
  slot.textContent = text;
  slot.className = `message ${kind}`;
}

function showProblem(text) {
  const problem = byId("connection-problem");
  problem.textContent = text;
  problem.hidden = false;
}

function hideProblem() {
  byId("connection-problem").hidden = true;
}

// ---------------------------------------------------------------- controls (Figure 3: "Mode" and "Explanations")

// Switch between "single" and "comparison". The first property's inputs are kept as Property A (R11).
function switchMode(mode) {
  state.mode = mode;
  document.body.classList.toggle("comparison", mode === "comparison");
  byId("mode-single").setAttribute("aria-pressed", String(mode === "single"));
  byId("mode-comparison").setAttribute("aria-pressed", String(mode === "comparison"));
  requestEvaluation();
}

// Show or hide one section's or item's explanation. The button turns yellow while its explanation shows. Errors
// and warnings are not explanations, so they always stay visible.
function toggleExplanation(button, explainable) {
  const open = explainable.classList.toggle("open");
  button.setAttribute("aria-expanded", String(open));
}

// A round "i" button that shows and hides the explanations inside `explainable`.
function infoButton(explainable, what) {
  const button = document.createElement("button");
  button.type = "button";
  button.className = "info";
  button.textContent = "i";
  button.setAttribute("aria-expanded", "false");
  button.setAttribute("aria-label", `Explain ${what}`);
  button.addEventListener("click", () => toggleExplanation(button, explainable));
  return button;
}

// Replace the inputs with the next sample deal (A, and B in comparison mode), then call requestEvaluation() (R9).
// The samples take turns: the SRS sample first, then each other example, then back to the first.
function fillSample() {
  const sample = pageText.sample_deals[state.nextSample];
  state.nextSample = (state.nextSample + 1) % pageText.sample_deals.length;
  const properties = state.mode === "comparison" ? PROPERTIES : ["A"];
  for (const property of properties) {
    for (const field of INPUT_FIELDS) {
      const text = sample[property][field];
      state.inputs[property][field] = text;
      byId(`input-${property}-${field}`).value = text;
    }
    showSource(property, "");  // these numbers no longer come from a report
  }
  requestEvaluation();
}

// ---------------------------------------------------------------- property reports (not yet in SDS Figure 3)

// Open the "Load reports" window. It keeps the last reports chosen and what was found in them.
function openReports() {
  byId("report-dialog").showModal();
}

// Send the report chosen for each property to POST /read-reports, then fill in what it found. The button is off
// while the calculator reads, so a second press cannot send the reports twice.
async function readReports() {
  const button = byId("read-reports");
  button.disabled = true;
  byId("report-problem").hidden = true;
  try {
    const body = { A: await reportFor("A"), B: await reportFor("B") };
    if (!body.A && !body.B) {
      showReportProblem(pageText.reports_choose_first);
      return;
    }
    const response = await fetch("/read-reports", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    const answer = await response.json();
    if (!response.ok) {
      showReportProblem(answer.error);
      return;
    }
    applyReports(answer);
  } catch (problem) {
    showReportProblem(CANNOT_REACH);
  } finally {
    button.disabled = false;
  }
}

// One property's report as {name, data}, with the file's bytes in base64, or null if none was chosen. A chosen
// file comes before pasted text. Pasted text has no name; the calculator gives it one.
async function reportFor(property) {
  const file = byId(`report-file-${property}`).files[0];
  if (file) {
    return { name: file.name, data: await base64Of(file) };
  }
  const text = byId(`report-text-${property}`).value;
  return text.trim() ? { name: "", data: await base64Of(new Blob([text])) } : null;
}

// A file's bytes as base64 text, so JSON can carry them.
function base64Of(blob) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result.split(",")[1]);  // the result is "data:<type>;base64,<bytes>"
    reader.onerror = () => reject(reader.error);
    reader.readAsDataURL(blob);
  });
}

// For each property whose report was read: show what the report gave, clear its file and text (so reading the
// other property's report later does not read this one again over the member's changes), and fill in its inputs.
// An input the report lacks is left empty, with its hint saying what to enter. Switch to comparison mode when
// Property B was read, so the deltas show.
function applyReports(answer) {
  for (const property of PROPERTIES) {
    const reading = answer[property];
    if (!reading) {
      continue;  // no report chosen for this property this time: leave it as it is
    }
    byId(`report-summary-${property}`).replaceChildren(...reading.summary.map(listItem));
    byId(`report-file-${property}`).value = "";
    byId(`report-text-${property}`).value = "";
    if (!reading.inputs) {
      continue;  // the report could not be read: keep what is typed
    }
    for (const field of INPUT_FIELDS) {
      const text = reading.inputs[field] || "";
      state.inputs[property][field] = text;
      byId(`input-${property}-${field}`).value = text;
    }
    showSource(property, reading.name);
  }
  if (answer.B && answer.B.inputs) {
    switchMode("comparison");  // also asks for the evaluation
  } else {
    requestEvaluation();
  }
}

// Show, beside a property's column heading, the name of the report its numbers came from ("" for none).
function showSource(property, name) {
  const source = byId(`source-${property}`);
  source.textContent = name;
  source.title = name;
}

function listItem(text) {
  const item = document.createElement("li");
  item.textContent = text;
  return item;
}

function showReportProblem(text) {
  const problem = byId("report-problem");
  problem.textContent = text;
  problem.hidden = false;
}

loadText();
