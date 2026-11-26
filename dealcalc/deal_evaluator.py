"""Deal Evaluator: produces everything the page shows for one or two properties.

Owner: Alejandro Zamorano (Project Plan M9). Skeleton: Jonny Heinrich.
Design: SDS Section 4.5. Requirements: R12 (and the self-check behind R14), and reading property reports (not yet
in the SRS).

This is the one module that combines the others, so the whole calculator can be tested without a browser.

The report evaluate() returns has this shape (results and deltas are already formatted as text):

    {"A": view, "B": view or None, "deltas": dict or None, "deltas_message": str or None}
    view = {"errors": dict, "warnings": dict, "results": dict or None, "formulas": dict or None}

read_reports() returns {"A": reading or None, "B": reading or None}, with
    reading = {"name": str, "inputs": dict or None, "summary": list of str}
"""

from dealcalc import report_reader, teaching_content
from dealcalc.deal_math import RESULT_FIELDS, Deal, Results, compute, deltas
from dealcalc.input_checker import check_inputs, find_warnings
from dealcalc.number_format import RATE_FIELDS, format_delta, format_input, format_money, format_percent

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


def read_reports(reports: dict[str, tuple[str, bytes] | None]) -> dict:
    """Read the property report chosen for each property (POST /read-reports). No side effects.

    reports maps "A" and "B" to (file name, the file's bytes), or to None when no report was chosen for that
    property. Each reading's inputs hold, as typed text, the inputs the report gives; an input it does not give is
    left out. inputs is None when the file could not be read at all, so the page keeps what is typed. summary is
    what the page shows about the report, from Teaching Content.
    """
    return {side: None if report is None else read_report(*report) for side, report in reports.items()}


def read_report(name: str, data: bytes) -> dict:
    """One report's reading for the page (see read_reports). Pasted text has no file name, so it gets one."""
    name = name or teaching_content.PASTED_REPORT_NAME
    reading = report_reader.read_report(data)
    if reading.problem:
        return {"name": name, "inputs": None,
                "summary": [teaching_content.REPORT_PROBLEMS[reading.problem].format(name=name)]}
    return {
        "name": name,
        "inputs": {field: format_input(value) for field, value in reading.values.items()},
        "summary": teaching_content.report_summary(reading.values, reading.sources, reading.worked),
    }


def reports_too_large(limit_mb: int) -> str:
    """The message for reports larger than the Page Host reads (limit_mb megabytes each)."""
    return teaching_content.REPORTS_TOO_LARGE.format(limit=limit_mb)


def page_text() -> dict:
    """Teaching Content's purposes, definitions, cap rate words, sample deals, and report words, for the page.

    sample_deals is a list of {"A": raw, "B": raw} pairs, starting with the SRS sample (R5, R9).
    """
    return {
        "page_purpose": teaching_content.PAGE_PURPOSE,
        "info_hint": teaching_content.INFO_HINT,
        "section_purposes": teaching_content.SECTION_PURPOSES,
        "definitions": teaching_content.DEFINITIONS,
        "cap_rate_note": teaching_content.CAP_RATE_NOTE,
        "cap_rate_tag": teaching_content.CAP_RATE_TAG,
        # the SRS sample first, then the other examples; "try a sample deal" loads the next one each time
        "sample_deals": [teaching_content.SAMPLE_DEALS, *teaching_content.MORE_SAMPLE_DEALS],
        "reports_purpose": teaching_content.REPORTS_PURPOSE,
        "reports_choose_first": teaching_content.REPORTS_CHOOSE_FIRST,
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
