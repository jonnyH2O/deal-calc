"""Input Checker: decides whether typed inputs can be used, and explains any problem.

Owner: Jonny Heinrich (Project Plan M6).
Design: SDS Section 4.2. Requirements: R1, R2, R3.

Only checked values become a Deal, so Deal Math never divides by zero.

The error and warning messages are written here, next to the limits they describe (SDS 4.2). They use only terms
that are defined on the page (R17).
"""

import math

from dealcalc.deal_math import INPUT_FIELDS, Deal, Results

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

# How each input is named in messages, and the unit its range is written in.
LABELS = {
    "price": "purchase price",
    "monthly_rent": "monthly rent",
    "vacancy_pct": "vacancy rate",
    "operating_costs": "yearly operating costs",
}
PERCENT_FIELDS = {"vacancy_pct"}


def parse_number(text: str) -> float | None:
    """Read typed text as a number.

    Removes spaces, commas, a leading "$", and a trailing "%". Returns None if the text is empty or not a number.
    "nan" and "inf" are not numbers here, even though Python's float() accepts them.
    """
    cleaned = text.replace(" ", "").replace(",", "").replace("−", "-")  # also accept the minus sign "−"
    if cleaned.endswith("%"):
        cleaned = cleaned[:-1]
    if cleaned.startswith("$"):
        cleaned = cleaned[1:]
    elif cleaned.startswith("-$"):  # "-$5" means -5
        cleaned = "-" + cleaned[2:]
    try:
        number = float(cleaned)
    except ValueError:
        return None
    return number if math.isfinite(number) else None


def valid_range(field: str) -> str:
    """The valid range of an input in words, such as "more than $0, up to $100,000,000"."""
    low, high = LIMITS[field]
    if field in PERCENT_FIELDS:
        low_text, high_text = f"{low:,}%", f"{high:,}%"
    else:
        low_text, high_text = f"${low:,}", f"${high:,}"
    if field in LOWEST_EXCLUDED:
        return f"more than {low_text}, up to {high_text}"
    return f"from {low_text} to {high_text}"


def check_inputs(raw: dict[str, str]) -> tuple[Deal | None, dict[str, str]]:
    """Check a property's four typed inputs (R1, R2).

    Returns (deal, errors). errors maps each missing, non-numeric, or out-of-range field to a message that says
    what is wrong and gives the valid range. deal is a Deal only when errors is empty, and None otherwise.
    Fields other than the four inputs are ignored.
    """
    values, errors = {}, {}
    for field in INPUT_FIELDS:
        label, allowed = LABELS[field], valid_range(field)
        text = raw.get(field)
        if text is None or str(text).strip() == "":
            errors[field] = f"Enter the {label}: {allowed}."
            continue
        number = parse_number(str(text))
        if number is None:
            errors[field] = f"The {label} must be a number: {allowed}."
            continue
        low, high = LIMITS[field]
        too_low = number <= low if field in LOWEST_EXCLUDED else number < low
        if too_low or number > high:
            errors[field] = f"Out of range: the {label} must be {allowed}."
            continue
        values[field] = number
    if errors:
        return None, errors
    return Deal(**values), {}


def find_warnings(deal: Deal, results: Results) -> dict[str, str]:
    """Warnings for unusual values and a negative NOI (R3), keyed by field name.

    A negative NOI always makes the cap rate negative, so in that case only the NOI warning is given: it explains
    the low cap rate too.
    """
    warnings = {}
    vacancy_limit = WARNING_LIMITS["vacancy_pct_above"]
    if deal.vacancy_pct > vacancy_limit:
        warnings["vacancy_pct"] = (f"A vacancy rate above {vacancy_limit}% is unusual. Check that it matches the "
                                   "listing.")
    if results.noi < 0:
        warnings["noi"] = ("NOI is negative: the yearly operating costs are more than the effective gross income. "
                           "Check the operating costs and the monthly rent.")
        return warnings
    low, high = WARNING_LIMITS["cap_rate_pct_below"], WARNING_LIMITS["cap_rate_pct_above"]
    if results.cap_rate_pct < low:
        warnings["cap_rate_pct"] = (f"A cap rate below {low}% is unusual. Check the purchase price and the other "
                                    "inputs.")
    elif results.cap_rate_pct > high:
        warnings["cap_rate_pct"] = (f"A cap rate above {high}% is unusual. Check the purchase price and the other "
                                    "inputs.")
    return warnings
