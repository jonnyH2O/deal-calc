"""Deal Math: a property's checked inputs and results, and all the math in the SRS.

Owner: Alejandro Zamorano (Project Plan M5). Skeleton: Jonny Heinrich.
Design: SDS Section 4.1. Requirements: R4, R5, R12.

This is the only module with formulas. It uses no other module.
"""

from dataclasses import dataclass

# The four inputs and four results, in the order the page shows them.
INPUT_FIELDS = ("price", "monthly_rent", "vacancy_pct", "operating_costs")
RESULT_FIELDS = ("gpr", "egi", "noi", "cap_rate_pct")


@dataclass(frozen=True)
class Deal:
    """A property's inputs after they pass the Input Checker."""

    price: float            # purchase price, US dollars (always more than 0)
    monthly_rent: float     # rent each month for all units, US dollars
    vacancy_pct: float      # vacancy rate, percent (5 means 5%)
    operating_costs: float  # yearly operating costs, US dollars


@dataclass(frozen=True)
class Results:
    """A property's results, not rounded. The Number Formatter rounds them for display."""

    gpr: float           # gross potential rent, US dollars per year
    egi: float           # effective gross income, US dollars per year
    noi: float           # net operating income, US dollars per year (may be negative)
    cap_rate_pct: float  # cap rate, percent (may be negative)


def compute(deal: Deal) -> Results:
    """Work out a property's results (R4).

    GPR = monthly_rent × 12
    EGI = GPR × (1 − vacancy_pct ÷ 100)
    NOI = EGI − operating_costs
    cap_rate_pct = NOI ÷ price × 100

    No side effects. Expects price > 0, which the Input Checker guarantees.
    """
    raise NotImplementedError("deal_math.compute() is not written yet (Project Plan M5).")


def deltas(deal_a: Deal, results_a: Results, deal_b: Deal, results_b: Results) -> dict[str, float]:
    """Property B minus Property A for each of the 8 inputs and results, keyed by field name (R12).

    No side effects.
    """
    raise NotImplementedError("deal_math.deltas() is not written yet (Project Plan M5).")
