"""Number Formatter: writes numbers in the formats in SRS Section 3.1.

Owner: Jonny Heinrich (Project Plan M7).
Design: SDS Section 4.3.

Results, worked formulas, and deltas all use these functions, so they always match each other. Negative numbers
use the minus sign "−" (U+2212), as in the SRS. Numbers are rounded half away from zero, the way people round by
hand ($0.50 becomes $1), using the number as Python prints it, so 8.515 becomes 8.52% even though the float is
stored as 8.51499...
"""

from decimal import ROUND_HALF_UP, Decimal

MINUS = "−"

# Fields whose deltas are shown in percentage points instead of dollars. Every other field is in dollars.
RATE_FIELDS = {"vacancy_pct", "cap_rate_pct"}


def _rounded(x: float, places: int) -> Decimal:
    """x rounded half away from zero to the given number of decimal places."""
    return Decimal(repr(x)).quantize(Decimal(1).scaleb(-places), rounding=ROUND_HALF_UP)


def _sign(value: Decimal, plus: bool) -> str:
    """"−" for a negative value, "+" for a positive one when plus is true, and nothing otherwise.

    The value is already rounded, so a number that rounds to zero gets no sign.
    """
    if value < 0:
        return MINUS
    if value > 0 and plus:
        return "+"
    return ""


def _money(x: float, plus: bool) -> str:
    value = _rounded(x, 0)
    return f"{_sign(value, plus)}${abs(value):,.0f}"


def format_money(x: float) -> str:
    """Whole dollars with commas: 102160 → "$102,160"; −4500 → "−$4,500"."""
    return _money(x, plus=False)


def format_percent(x: float) -> str:
    """Two decimals: 8.513 → "8.51%"; −0.375 → "−0.38%"."""
    value = _rounded(x, 2)
    return f"{_sign(value, plus=False)}{abs(value):,.2f}%"


def format_delta(field: str, x: float) -> str:
    """A signed delta: dollars for amounts ("+$1,936"), percentage points for RATE_FIELDS ("−0.80 points").

    A delta that rounds to zero has no sign: "$0" or "0.00 points".
    """
    if field in RATE_FIELDS:
        value = _rounded(x, 2)
        return f"{_sign(value, plus=True)}{abs(value):,.2f} points"
    return _money(x, plus=True)
