"""Number Formatter: writes numbers in the formats in SRS Section 3.1.

Owner: Jonny Heinrich (Project Plan M7).
Design: SDS Section 4.3.

Results, worked formulas, and deltas all use these functions, so they always match each other. Negative numbers
use the minus sign "−" (U+2212), as in the SRS.
"""

# Fields whose deltas are shown in percentage points instead of dollars.
RATE_FIELDS = {"vacancy_pct", "cap_rate_pct"}


def format_money(x: float) -> str:
    """Whole dollars with commas: 102160 → "$102,160"; −4500 → "−$4,500"."""
    raise NotImplementedError("number_format.format_money() is not written yet (Project Plan M7).")


def format_percent(x: float) -> str:
    """Two decimals: 8.513 → "8.51%"."""
    raise NotImplementedError("number_format.format_percent() is not written yet (Project Plan M7).")


def format_delta(field: str, x: float) -> str:
    """A signed delta: dollars for amounts ("+$1,936"), percentage points for RATE_FIELDS ("−0.80 points")."""
    raise NotImplementedError("number_format.format_delta() is not written yet (Project Plan M7).")
