"""Teaching Content: all the words written for members, and the worked formulas.

Owner: Gabe Imbrunetti (Project Plan M8). Skeleton: Jonny Heinrich.
Design: SDS Section 4.4. Requirements: R5 to R9, R13, R17, and the property report words below (not yet in the
SRS).

Every member-facing word lives here, so the wording can be reviewed and changed in one place without touching
the formulas. The text is written for members who are new to real estate investing, and every term it uses is
defined on the page (R17): each input and result has a name and definition below, and "delta" is defined in the
comparison section's purpose.
"""

from dealcalc.deal_math import INPUT_FIELDS, Deal, Results
from dealcalc.number_format import MINUS, format_input, format_money, format_percent

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
CAP_RATE_NOTE = ("Cap rates partly reflect risk, so a higher cap rate is not always a better deal. Read two cap "
                 "rates side by side as market context: a gap between them may come from differences in risk, "
                 "location, or building condition.")

# Shown next to the cap rate's name in comparison mode, so its delta is not read as a score like the others (R13).
CAP_RATE_TAG = "market context"

# Shown in comparison mode instead of the deltas when a property has input errors (R12). {properties} becomes
# "Property A", "Property B", or "Property A and Property B".
DELTAS_NEED_FIXING = "Fix the inputs for {properties} to see the deltas."

# The sample deals, as typed inputs (R5, R9). The numbers come from the SRS.
SAMPLE_DEALS = {
    "A": {"price": "1,200,000", "monthly_rent": "14,400", "vacancy_pct": "5", "operating_costs": "62,000"},
    "B": {"price": "1,350,000", "monthly_rent": "15,600", "vacancy_pct": "7", "operating_costs": "70,000"},
}

# More made-up examples for "try a sample deal". Each press loads the next one, starting with SAMPLE_DEALS, so
# members see different listings. In each pair, B is a similar building to compare with A. They are realistic
# but not real listings, and the fourth has a high vacancy rate so members can see a warning.
MORE_SAMPLE_DEALS = [
    {"A": {"price": "850,000", "monthly_rent": "9,600", "vacancy_pct": "4", "operating_costs": "41,000"},
     "B": {"price": "920,000", "monthly_rent": "10,400", "vacancy_pct": "6", "operating_costs": "46,500"}},
    {"A": {"price": "2,400,000", "monthly_rent": "26,400", "vacancy_pct": "6", "operating_costs": "118,000"},
     "B": {"price": "2,150,000", "monthly_rent": "24,000", "vacancy_pct": "9", "operating_costs": "112,000"}},
    {"A": {"price": "640,000", "monthly_rent": "8,800", "vacancy_pct": "28", "operating_costs": "39,000"},
     "B": {"price": "700,000", "monthly_rent": "8,800", "vacancy_pct": "8", "operating_costs": "44,000"}},
    {"A": {"price": "3,100,000", "monthly_rent": "30,000", "vacancy_pct": "5", "operating_costs": "155,000"},
     "B": {"price": "2,900,000", "monthly_rent": "29,500", "vacancy_pct": "5", "operating_costs": "162,000"}},
]


# ---------------------------------------------------------------- property reports (not yet in the SRS)

# At the top of the "Load reports" window, one or two sentences like the section purposes (R6).
REPORTS_PURPOSE = ("Choose a listing or property report for Property A, and one for Property B to compare the two. "
                   "The calculator reads PDF, Word, and text files, or you can paste a report's text.")

# Shown in the window when Read reports is pressed with no file chosen and no text pasted.
REPORTS_CHOOSE_FIRST = "Choose a report file or paste a report's text first."

# Shown when the reports are larger than the calculator reads. {limit} is the most megabytes for each file.
REPORTS_TOO_LARGE = ("The reports are too large to read. Choose files under {limit} MB each, or paste their text "
                     "instead.")

# The name shown for a report that was pasted instead of chosen as a file.
PASTED_REPORT_NAME = "Pasted text"

# What the window says about each input after reading a report. {name} is the input's name from DEFINITIONS, and
# {source} is the report text the number was read from.
REPORT_FOUND = "{name}: {value}, from “{source}”."
REPORT_NOT_FOUND = "{name}: not found in the report, so type it in."

# How an input was worked out from another number in the report, like the worked formulas (R8).
REPORT_WORKED = {
    "yearly_rent": "The report gives a yearly rent of {given}, so the monthly rent is {given} ÷ 12 = {value}.",
    "average_rent": ("The report gives an average rent of {given} for each of its {units} units, so the monthly "
                     "rent is {given} × {units} = {value}."),
    "monthly_costs": ("The report gives monthly operating costs of {given}, so the yearly operating costs are "
                      "{given} × 12 = {value}."),
    "occupancy": (f"The report says {{given}} of the property is rented, so the vacancy rate is 100% {MINUS} "
                  "{given} = {value}."),
}

# Why a report could not be read at all, and what to do instead. {name} is the file's name.
REPORT_PROBLEMS = {
    "encrypted": ("{name} is locked (encrypted), so the calculator can't read it. Copy its text and paste it "
                  "instead, or type the numbers in."),
    "unreadable": "The calculator couldn't read {name}. Copy its text and paste it instead, or type the numbers in.",
    "no_text": ("{name} has no text the calculator can read, so it may be a scan or a picture. Type the numbers "
                "in from it."),
    "not_supported": ("{name} isn't a PDF, Word, or text file. Copy its text and paste it instead, or type the "
                      "numbers in."),
}

REPORT_SOURCE_LIMIT = 80  # a longer piece of report text is cut short, with "…", in the window


def report_summary(values: dict[str, float], sources: dict[str, str], worked: dict[str, tuple]) -> list[str]:
    """What the "Load reports" window says about one report: for each input, the number found and the report text
    it came from, how it was worked out if it was, or that it was not found. No side effects.

    values, sources, and worked are a Report Reader Reading's fields.
    """
    lines = []
    for field in INPUT_FIELDS:
        name = DEFINITIONS[field]["name"]
        if field not in values:
            lines.append(REPORT_NOT_FOUND.format(name=name))
            continue
        show = format_percent if field == "vacancy_pct" else format_money
        source = " ".join(sources[field].split())
        if len(source) > REPORT_SOURCE_LIMIT:
            source = source[:REPORT_SOURCE_LIMIT - 1].rstrip() + "…"
        lines.append(REPORT_FOUND.format(name=name, value=show(values[field]), source=source))
        if field in worked:
            how, given, units = worked[field]
            given = format_percent(given) if how == "occupancy" else format_money(given)
            units = format_input(units) if units is not None else ""
            lines.append(REPORT_WORKED[how].format(given=given, units=units, value=show(values[field])))
    return lines


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
