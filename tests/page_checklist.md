# Calculator Page Checklist

Python cannot run the page's JavaScript, so the page is checked by hand with this list. It is white-box: it takes
every state and transition in the page's state machine (SDS Figure 3) at least once, and checks the page
requirements along the way. Run it after any change to `dealcalc/static/`, and before each release.

**Set-up:** start the calculator with `python -m dealcalc`, open the address it prints, and set the browser
window to 1280 × 720 for check 9.

## Loading (Figure 3: Loading page text)

| # | Do this | Check that | Covers |
|---|---|---|---|
| 1 | Open the page. | The top says what the calculator does in one sentence. Single property is selected, explanations are shown, and each input has a grey hint saying what to enter. | R6, R10, Loading → Ready |
| 2 | Read the Inputs and Results sections. | Each starts with a sentence or two on what it is for. Each input has a definition and "Where to find it". | R6, R7 |

## Report (Figure 3: Report up to date ⇄ Waiting for report)

| # | Do this | Check that | Covers |
|---|---|---|---|
| 3 | Press **Try a sample deal**. | Property A shows $1,200,000, 14,400, 5, and 62,000. Results show GPR $172,800, EGI $164,160, NOI $102,160, and cap rate 8.51%, each with its worked formula. | R4, R5, R8, R9, fillSample() |
| 4 | Change the vacancy rate to 8, one key at a time. | NOI and cap rate change after every key, with no Calculate button. | R4, R15, input change → Waiting → render |
| 5 | Type 40 for the vacancy rate. | An amber warning appears under it, and the results still show. | R3 |
| 6 | Type `abc` for the purchase price. | A red message under it says it must be a number and gives the valid range. Every result shows "—". | R2 |
| 7 | Fix the price (1,200,000). | The red message goes away and the results come back. | R2 |

## Mode (Figure 3: Single-property mode ⇄ Comparison mode)

| # | Do this | Check that | Covers |
|---|---|---|---|
| 8 | Press **Compare two**. | Property A keeps its numbers. Property B and Delta columns appear, with the Comparison section's purpose and the cap rate note. The note above the table says to fix the inputs for Property B. | R6, R11, R12, R13, switchMode("comparison") |
| 9 | Press **Try a sample deal**, then **Hide explanations**. | Property B is $1,350,000 / 15,600 / 7 / 70,000. Deltas include NOI +$1,936 and cap rate −0.80 points. With explanations hidden, everything fits in the 1280 × 720 window without scrolling. | R9, R12, R16 |
| 10 | Type `abc` for Property B's price. | The deltas change to "—", and the note says to fix Property B. The table does not change width. | R12 |
| 11 | Press **Single property**, then **Compare two** again. | Property A's numbers were kept both ways. | R11, switchMode("single") |

## Explanations (Figure 3: Explanations shown ⇄ Explanations hidden)

| # | Do this | Check that | Covers |
|---|---|---|---|
| 12 | With explanations hidden and a red or amber message showing, look at the messages. | Errors and warnings still show. | R10 |
| 13 | Press **Show explanations**. | Definitions, "Where to find it", section purposes, and formulas come back. The numbers did not change. | R10, toggleExplanations() |

## Cannot reach calculator (Figure 3)

| # | Do this | Check that | Covers |
|---|---|---|---|
| 14 | Stop the calculator (Ctrl+C in its terminal), then type in any input. | A red message says the page can't reach the calculator and how to start it. | loadText() / requestEvaluation() failure |
| 15 | Start the calculator again and reload the page. | The page works again. | Cannot reach → Loading |
