// Calculator Page: shows the calculator and sends every input change to the Page Host.
// Owner: Ben Horrisberger (Project Plan M11, M12). Skeleton: Jonny Heinrich.
// Design: SDS Section 4.7 and the state machine in Figure 3. This file does no math.

"use strict";

const state = {
  mode: "single",            // "single" or "comparison" (R11)
  explanationsShown: true,   // explanations are shown when the page first opens (R10)
  inputs: { A: {}, B: {} },  // typed text, keyed by field name: price, monthly_rent, vacancy_pct, operating_costs
  latestSeq: 0,              // number of the newest POST /evaluate sent
};

// At page load, get GET /text and fill in the purposes, definitions, and cap rate note. If the request fails,
// show a message to start the calculator and then reload the page.
async function loadText() {
  // To be written (M11).
}

// After every input change, send POST /evaluate with the next seq number.
async function requestEvaluation() {
  // To be written (M11).
}

// Show the report only if its seq is the latest one sent, so a slow older answer never replaces a newer one.
function render(report) {
  // To be written (M11, M12).
}

// Switch between "single" and "comparison". The first property's inputs are kept as Property A (R11).
function switchMode(mode) {
  // To be written (M12).
}

// Hide or show all explanations. Errors and warnings stay visible (R10).
function toggleExplanations() {
  // To be written (M11).
}

// Replace the inputs with SAMPLE_DEALS (A, and B in comparison mode), then call requestEvaluation() (R9).
function fillSample() {
  // To be written (M11).
}

loadText();
