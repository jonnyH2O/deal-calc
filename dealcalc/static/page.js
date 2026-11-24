// Calculator Page: shows the calculator and sends every input change to the Page Host.
// Owner: Ben Horrisberger (Project Plan M11, M12). Skeleton: Jonny Heinrich.
// Design: SDS Section 4.7 and the state machine in Figure 3. Requirements: R6 to R13, R15, R16.
//
// This file does no math and holds almost no wording: the Python side sends every number already worked out and
// formatted, and every explanation comes from GET /text. The only words here are labels and the message shown
// when the page cannot reach the calculator at all (it cannot ask the calculator for that message).

"use strict";

// The field names shared with the Python side (deal_math.INPUT_FIELDS and RESULT_FIELDS), in display order.
const INPUT_FIELDS = ["price", "monthly_rent", "vacancy_pct", "operating_costs"];
const RESULT_FIELDS = ["gpr", "egi", "noi", "cap_rate_pct"];
const PROPERTIES = ["A", "B"];
const NOT_YET = "—"; // "—", shown where a number cannot be worked out yet
const CANNOT_REACH = "This page can't reach the calculator. Start it with python -m dealcalc, then reload this page.";

const state = {
  mode: "single",            // "single" or "comparison" (R11)
  explanationsShown: true,   // explanations are shown when the page first opens (R10)
  inputs: { A: {}, B: {} },  // typed text, keyed by field name
  latestSeq: 0,              // number of the newest POST /evaluate sent
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
  for (const section of ["inputs", "results", "comparison"]) {
    byId(`${section}-purpose`).textContent = pageText.section_purposes[section];
  }
  byId("cap-rate-note").textContent = pageText.cap_rate_note;
  buildRows();
  connectControls();
  requestEvaluation();  // shows a hint under each empty input
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

// The left-hand cell: the item's name, its definition, and, for inputs, where to find it on a listing.
function labelRow(field, isInput) {
  const entry = pageText.definitions[field];
  const row = document.createElement("tr");
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
  byId("toggle-explanations").addEventListener("click", toggleExplanations);
  byId("sample-deal").addEventListener("click", fillSample);
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
    delta.className = report.deltas ? "delta" : "";
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

// Hide or show all explanations. Errors and warnings stay visible (R10).
function toggleExplanations() {
  state.explanationsShown = !state.explanationsShown;
  document.body.classList.toggle("explanations-hidden", !state.explanationsShown);
  const button = byId("toggle-explanations");
  button.textContent = state.explanationsShown ? "Hide explanations" : "Show explanations";
  button.setAttribute("aria-pressed", String(!state.explanationsShown));
}

// Replace the inputs with SAMPLE_DEALS (A, and B in comparison mode), then call requestEvaluation() (R9).
function fillSample() {
  const properties = state.mode === "comparison" ? PROPERTIES : ["A"];
  for (const property of properties) {
    for (const field of INPUT_FIELDS) {
      const text = pageText.sample_deals[property][field];
      state.inputs[property][field] = text;
      byId(`input-${property}-${field}`).value = text;
    }
  }
  requestEvaluation();
}

loadText();
