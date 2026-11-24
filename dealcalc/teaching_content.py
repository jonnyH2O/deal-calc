"""Teaching Content: all the words written for members, and the worked formulas.

Owner: Gabe Imbrunetti (Project Plan M8). Skeleton: Jonny Heinrich.
Design: SDS Section 4.4. Requirements: R5 to R9, R13, R17.

Every member-facing word lives here, so the wording can be reviewed and changed in one place without touching
the formulas. Every term used in this text must be defined on the page (R17).
"""

from dealcalc.deal_math import Deal, Results

# One sentence at the top of the page saying what the calculator does (R6). To be written (M8).
PAGE_PURPOSE = ""

# A sentence or two at the start of each section saying what it is for (R6). To be written (M8).
SECTION_PURPOSES = {
    "inputs": "",
    "results": "",
    "comparison": "",
}

# For each input: a one-sentence definition and where to find the number on a listing (R7).
# For each result: a one-sentence definition (R8). To be written (M8).
DEFINITIONS = {
    "price": {"definition": "", "where_to_find": ""},
    "monthly_rent": {"definition": "", "where_to_find": ""},
    "vacancy_pct": {"definition": "", "where_to_find": ""},
    "operating_costs": {"definition": "", "where_to_find": ""},
    "gpr": {"definition": ""},
    "egi": {"definition": ""},
    "noi": {"definition": ""},
    "cap_rate_pct": {"definition": ""},
}

# The note shown in comparison mode (R13). To be written (M8).
CAP_RATE_NOTE = ""

# The sample deals, as typed inputs (R5, R9). The numbers come from the SRS.
SAMPLE_DEALS = {
    "A": {"price": "1,200,000", "monthly_rent": "14,400", "vacancy_pct": "5", "operating_costs": "62,000"},
    "B": {"price": "1,350,000", "monthly_rent": "15,600", "vacancy_pct": "7", "operating_costs": "70,000"},
}


def worked_formulas(deal: Deal, results: Results) -> dict[str, str]:
    """Each result's formula with the member's numbers, keyed by result field (R8).

    For example: "NOI = $164,160 − $62,000 = $102,160". No side effects.
    """
    raise NotImplementedError("teaching_content.worked_formulas() is not written yet (Project Plan M8).")
