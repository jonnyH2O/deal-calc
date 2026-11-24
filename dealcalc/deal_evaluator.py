"""Deal Evaluator: produces everything the page shows for one or two properties.

Owner: Alejandro Zamorano (Project Plan M9). Skeleton: Jonny Heinrich.
Design: SDS Section 4.5. Requirements: R12 (and the self-check behind R14).

This is the one module that combines the others, so the whole calculator can be tested without a browser.

The report evaluate() returns has this shape (results and deltas are already formatted as text):

    {"A": view, "B": view or None, "deltas": dict or None, "deltas_message": str or None}
    view = {"errors": dict, "warnings": dict, "results": dict or None, "formulas": dict or None}
"""

from dealcalc import teaching_content
from dealcalc.deal_math import RESULT_FIELDS, Deal, Results, compute, deltas
from dealcalc.input_checker import check_inputs, find_warnings
from dealcalc.number_format import RATE_FIELDS, format_delta, format_money, format_percent

# What sample deal A must show (R5). self_check() compares the calculator's answers with these.
R5_ANSWERS = {"gpr": "$172,800", "egi": "$164,160", "noi": "$102,160", "cap_rate_pct": "8.51%"}


def format_results(results: Results) -> dict[str, str]:
    """Each result as the page shows it: dollars for GPR, EGI, and NOI, and a percent for the cap rate."""
    shown = {}
    for field in RESULT_FIELDS:
        value = getattr(results, field)
        shown[field] = format_percent(value) if field in RATE_FIELDS else format_money(value)
    return shown


def evaluate_property(raw: dict[str, str]) -> tuple[dict, Deal | None, Results | None]:
    """Check and work out one property. Returns (view, deal, results); deal and results are None on errors."""
    deal, errors = check_inputs(raw)
    if deal is None:
        return {"errors": errors, "warnings": {}, "results": None, "formulas": None}, None, None
    results = compute(deal)
    view = {
        "errors": {},
        "warnings": find_warnings(deal, results),
        "results": format_results(results),
        "formulas": teaching_content.worked_formulas(deal, results),
    }
    return view, deal, results


def evaluate(raw_a: dict[str, str], raw_b: dict[str, str] | None) -> dict:
    """Build the report for Property A, and for Property B in comparison mode.

    For each property: checks the inputs, then, if there are no errors, computes the results, warnings, and worked
    formulas. If raw_b is given and both properties are valid, adds the formatted deltas. Otherwise deltas is None,
    and in comparison mode deltas_message names the property to fix (R12). No side effects.
    """
    view_a, deal_a, results_a = evaluate_property(raw_a)
    report = {"A": view_a, "B": None, "deltas": None, "deltas_message": None}
    if raw_b is None:
        return report

    view_b, deal_b, results_b = evaluate_property(raw_b)
    report["B"] = view_b
    if deal_a is not None and deal_b is not None:
        differences = deltas(deal_a, results_a, deal_b, results_b)
        report["deltas"] = {field: format_delta(field, x) for field, x in differences.items()}
    else:
        to_fix = [name for name, deal in (("Property A", deal_a), ("Property B", deal_b)) if deal is None]
        report["deltas_message"] = teaching_content.DELTAS_NEED_FIXING.format(properties=" and ".join(to_fix))
    return report


def page_text() -> dict:
    """Teaching Content's purposes, definitions, cap rate note, and sample deals, for the page to show."""
    return {
        "page_purpose": teaching_content.PAGE_PURPOSE,
        "info_hint": teaching_content.INFO_HINT,
        "section_purposes": teaching_content.SECTION_PURPOSES,
        "definitions": teaching_content.DEFINITIONS,
        "cap_rate_note": teaching_content.CAP_RATE_NOTE,
        "sample_deals": teaching_content.SAMPLE_DEALS,
    }


def self_check() -> str | None:
    """Compute sample deal A and compare it with the answers in R5.

    Returns None if they match, or a description of what differs.
    """
    deal, errors = check_inputs(teaching_content.SAMPLE_DEALS["A"])
    if deal is None:
        return f"sample deal A has input errors: {'; '.join(errors.values())}"
    shown = format_results(compute(deal))
    wrong = [f"{field} is {shown[field]} but should be {expected}"
             for field, expected in R5_ANSWERS.items() if shown[field] != expected]
    return "; ".join(wrong) or None
