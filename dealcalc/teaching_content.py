"""Teaching Content: all the words written for members, and the worked formulas.

Owner: Gabe Imbrunetti (Project Plan M8). Skeleton: Jonny Heinrich.
Design: SDS Section 4.4. Requirements: R5 to R9, R13, R17.

Every member-facing word lives here, so the wording can be reviewed and changed in one place without touching
the formulas. The text is written for members who are new to real estate investing, and every term it uses is
defined on the page (R17): each input and result has a name and definition below, and "delta" is defined in the
comparison section's purpose.
"""

from dealcalc.deal_math import Deal, Results
from dealcalc.number_format import MINUS, format_money, format_percent

# One sentence at the top of the page saying what the calculator does (R6).
PAGE_PURPOSE = ("Enter a property listing's numbers to see its net operating income (NOI) and cap rate, with every "
                "step explained.")

# Shown under the page purpose. The page puts its info button icon where {icon} is.
INFO_HINT = "Press {icon} next to any section or item to see an explanation."

# A sentence or two at the start of each section saying what it is for (R6).
SECTION_PURPOSES = {
    "inputs": ("These are the four numbers you need from a property listing. Each one says where to find it on the "
               "listing."),
    "results": ("These show how much money the property earns in a year and how that compares with its price. Each "
                "result shows its formula with your numbers, so you can follow every step."),
    "comparison": ("This puts two properties side by side, such as the meeting's listing and a similar building "
                   "nearby. A delta is Property B's number minus Property A's, so a plus sign means Property B's "
                   "number is higher."),
}

# For each input and result: the name the page shows and a one-sentence definition (R7, R8). For each input,
# also where to find the number on a listing (R7).
DEFINITIONS = {
    "price": {
        "name": "Purchase price",
        "definition": "What the buyer pays for the property.",
        "where_to_find": "Listed as the asking price or list price, usually near the top of the listing.",
    },
    "monthly_rent": {
        "name": "Monthly rent (all units)",
        "definition": "The rent collected each month if every unit is rented, added up for all units.",
        "where_to_find": ("Add up the monthly rent for every unit in the listing's rent roll (its table of units "
                          "and rents), or use the total monthly rent if the listing gives one."),
    },
    "vacancy_pct": {
        "name": "Vacancy rate",
        "definition": "The share of rent expected to be lost to empty units, as a percent.",
        "where_to_find": ("Listed as the vacancy or vacancy rate; if the listing doesn't give one, use your team's "
                          "estimate."),
    },
    "operating_costs": {
        "name": "Yearly operating costs",
        "definition": ("What it costs to run the property for a year, such as taxes, insurance, repairs, and "
                       "management, not counting loan payments."),
        "where_to_find": "Listed as the operating expenses or expenses; use the total for one year.",
    },
    "gpr": {
        "name": "Gross potential rent (GPR)",
        "definition": "The rent the property would collect in a year if every unit were rented all year.",
    },
    "egi": {
        "name": "Effective gross income (EGI)",
        "definition": ("Gross potential rent minus the rent lost to empty units, which is the rent the property is "
                       "expected to actually collect in a year."),
    },
    "noi": {
        "name": "Net operating income (NOI)",
        "definition": ("Effective gross income minus yearly operating costs, which is what the property earns in a "
                       "year before any loan payments."),
    },
    "cap_rate_pct": {
        "name": "Cap rate",
        "definition": ("NOI divided by the purchase price, as a percent, which is a rough measure of the yearly "
                       "return and partly of risk."),
    },
}

# The note shown in comparison mode (R13).
CAP_RATE_NOTE = ("Cap rates partly reflect risk, so a higher cap rate is not always a better deal. A gap between "
                 "two cap rates may come from differences in risk, location, or building condition.")

# Shown in comparison mode instead of the deltas when a property has input errors (R12). {properties} becomes
# "Property A", "Property B", or "Property A and Property B".
DELTAS_NEED_FIXING = "Fix the inputs for {properties} to see the deltas."

# The sample deals, as typed inputs (R5, R9). The numbers come from the SRS.
SAMPLE_DEALS = {
    "A": {"price": "1,200,000", "monthly_rent": "14,400", "vacancy_pct": "5", "operating_costs": "62,000"},
    "B": {"price": "1,350,000", "monthly_rent": "15,600", "vacancy_pct": "7", "operating_costs": "70,000"},
}


def worked_formulas(deal: Deal, results: Results) -> dict[str, str]:
    """Each result's formula with the member's numbers, keyed by result field (R8).

    For example: "NOI = $164,160 − $62,000 = $102,160". No side effects. Each number is rounded on its own for
    display, the same way it appears elsewhere on the page.
    """
    return {
        "gpr": f"GPR = {format_money(deal.monthly_rent)} × 12 = {format_money(results.gpr)}",
        "egi": (f"EGI = {format_money(results.gpr)} × (1 {MINUS} {format_percent(deal.vacancy_pct)}) "
                f"= {format_money(results.egi)}"),
        "noi": (f"NOI = {format_money(results.egi)} {MINUS} {format_money(deal.operating_costs)} "
                f"= {format_money(results.noi)}"),
        "cap_rate_pct": (f"Cap rate = {format_money(results.noi)} ÷ {format_money(deal.price)} "
                         f"= {format_percent(results.cap_rate_pct)}"),
    }
