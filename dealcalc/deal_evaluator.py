"""Deal Evaluator: produces everything the page shows for one or two properties.

Owner: Alejandro Zamorano (Project Plan M9). Skeleton: Jonny Heinrich.
Design: SDS Section 4.5. Requirements: R12 (and the self-check behind R14).

This is the one module that combines the others, so the whole calculator can be tested without a browser.

The report evaluate() returns has this shape (results and deltas are already formatted as text):

    {"A": view, "B": view or None, "deltas": dict or None, "deltas_message": str or None}
    view = {"errors": dict, "warnings": dict, "results": dict or None, "formulas": dict or None}
"""


def evaluate(raw_a: dict[str, str], raw_b: dict[str, str] | None) -> dict:
    """Build the report for Property A, and for Property B in comparison mode.

    For each property: checks the inputs, then, if there are no errors, computes the results, warnings, and worked
    formulas. If raw_b is given and both properties are valid, adds the formatted deltas. Otherwise deltas is None,
    and in comparison mode deltas_message names the property to fix (R12). No side effects.
    """
    raise NotImplementedError("deal_evaluator.evaluate() is not written yet (Project Plan M9).")


def page_text() -> dict:
    """Teaching Content's purposes, definitions, cap rate note, and sample deals, for the page to show."""
    raise NotImplementedError("deal_evaluator.page_text() is not written yet (Project Plan M9).")


def self_check() -> str | None:
    """Compute sample deal A and compare it with the answers in R5.

    Returns None if they match, or a description of what differs.
    """
    raise NotImplementedError("deal_evaluator.self_check() is not written yet (Project Plan M9).")
