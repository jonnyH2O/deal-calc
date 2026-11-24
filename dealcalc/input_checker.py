"""Input Checker: decides whether typed inputs can be used, and explains any problem.

Owner: Jonny Heinrich (Project Plan M6).
Design: SDS Section 4.2. Requirements: R1, R2, R3.

Only checked values become a Deal, so Deal Math never divides by zero.
"""

from dealcalc.deal_math import Deal, Results

# Valid range of each input, from SRS Section 3.1: (lowest, highest). Price must be more than its lowest
# value; every other input may equal its lowest value.
LIMITS = {
    "price": (0, 100_000_000),
    "monthly_rent": (0, 10_000_000),
    "vacancy_pct": (0, 100),
    "operating_costs": (0, 100_000_000),
}
LOWEST_EXCLUDED = {"price"}

# Unusual values that get a warning but still show results (R3). These are the SRS's initial values.
WARNING_LIMITS = {
    "vacancy_pct_above": 25,
    "cap_rate_pct_below": 2,
    "cap_rate_pct_above": 15,
}


def parse_number(text: str) -> float | None:
    """Read typed text as a number.

    Removes spaces, commas, a leading "$", and a trailing "%". Returns None if the text is empty or not a number.
    """
    raise NotImplementedError("input_checker.parse_number() is not written yet (Project Plan M6).")


def check_inputs(raw: dict[str, str]) -> tuple[Deal | None, dict[str, str]]:
    """Check a property's four typed inputs (R1, R2).

    Returns (deal, errors). errors maps each missing, non-numeric, or out-of-range field to a message that says
    what is wrong and gives the valid range. deal is a Deal only when errors is empty, and None otherwise.
    """
    raise NotImplementedError("input_checker.check_inputs() is not written yet (Project Plan M6).")


def find_warnings(deal: Deal, results: Results) -> dict[str, str]:
    """Warnings for unusual values and a negative NOI (R3), keyed by field name."""
    raise NotImplementedError("input_checker.find_warnings() is not written yet (Project Plan M6).")
