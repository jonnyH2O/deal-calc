"""White-box tests for Teaching Content (dealcalc/teaching_content.py; SDS 4.4; R5 to R9, R13, R17).

Teaching Content is mostly text, and worked_formulas() has no branches: it builds four strings in a row. White-box
testing here means checking each piece of text against the rule it must follow, and each formula string where it
can go wrong:

text rules
    T1  PAGE_PURPOSE is one sentence (R6)                          test_T1_page_purpose_is_one_sentence
    T2  each section purpose is one or two sentences (R6)          test_T2_section_purposes
    T3  every input and result has a name and a one-sentence
        definition; every input says where to find it (R7, R8)     test_T3_definitions
    T4  every term the text uses is defined on the page (R17)      test_T4_every_term_used_is_defined
    T5  the cap rate note names risk, location, and condition, and calls the cap rates market context (R13)
                                                                    test_T5_cap_rate_note
    T6  the sample deals are the SRS's numbers (R5, R9)             test_T6_sample_deals
    T7  the reports purpose is one or two sentences (R6)           test_T7_reports_purpose
    T8  every report problem names the file and says what to do    test_T8_report_problems
    T9  every worked conversion shows its formula                  test_T9_report_worked_formulas
worked_formulas(deal, results)
    W1  each of the four formulas, with the sample deal (R8)       test_W1_sample_deal_formulas
    W2  a negative NOI keeps its minus sign through the formulas   test_W2_negative_noi
    W3  the formulas use the Number Formatter's rounding           test_W3_rounding_matches_the_results
report_summary(values, sources, worked)
    S1  an input not found                    true: test_S1_inputs_not_found        false: test_S2_found_as_given
    S2  the vacancy rate (a percent) or money true: test_S2_found_as_given (both)
    S3  report text longer than the limit     true: test_S3_long_source_is_cut     false: test_S2_found_as_given
    S4  an input worked out; occupancy (a percent) or money; with units or not
                                              test_S4_worked_conversions         false: test_S2_found_as_given
"""

import re
import unittest

from dealcalc import teaching_content as text
from dealcalc.deal_math import INPUT_FIELDS, RESULT_FIELDS, Deal, Results, compute
from dealcalc.input_checker import check_inputs
from dealcalc.number_format import MINUS


def sentences(paragraph):
    """Number of sentences: periods, question marks, or exclamation marks followed by a space or the end."""
    return len(re.findall(r"[.!?](?:\s|$)", paragraph))


def all_text():
    """Every piece of member-facing text in Teaching Content."""
    pieces = [text.PAGE_PURPOSE, text.INFO_HINT, text.CAP_RATE_NOTE, text.CAP_RATE_TAG, text.DELTAS_NEED_FIXING,
              *text.SECTION_PURPOSES.values(), text.REPORTS_PURPOSE, text.REPORTS_CHOOSE_FIRST,
              text.REPORTS_TOO_LARGE, text.PASTED_REPORT_NAME, text.REPORT_FOUND, text.REPORT_NOT_FOUND,
              *text.REPORT_WORKED.values(), *text.REPORT_PROBLEMS.values()]
    for entry in text.DEFINITIONS.values():
        pieces.extend(entry.values())
    return pieces


class TestText(unittest.TestCase):

    def test_T1_page_purpose_is_one_sentence(self):
        self.assertEqual(sentences(text.PAGE_PURPOSE), 1)

    def test_T1_info_hint_has_one_place_for_the_icon(self):
        self.assertEqual(text.INFO_HINT.count("{icon}"), 1)
        self.assertEqual(sentences(text.INFO_HINT), 1)

    def test_T2_section_purposes(self):
        self.assertEqual(set(text.SECTION_PURPOSES), {"inputs", "results", "comparison"})
        for section, purpose in text.SECTION_PURPOSES.items():
            with self.subTest(section=section):
                self.assertIn(sentences(purpose), (1, 2))

    def test_T3_definitions(self):
        self.assertEqual(set(text.DEFINITIONS), set(INPUT_FIELDS + RESULT_FIELDS))
        for field, entry in text.DEFINITIONS.items():
            with self.subTest(field=field):
                self.assertTrue(entry["name"])
                self.assertEqual(sentences(entry["definition"]), 1)
                if field in INPUT_FIELDS:
                    self.assertEqual(sentences(entry["where_to_find"]), 1)
                else:
                    self.assertNotIn("where_to_find", entry)

    def test_T4_every_term_used_is_defined(self):
        # each term, and where the page defines it
        names = " ".join(entry["name"] for entry in text.DEFINITIONS.values())
        defined_in = {
            "GPR": names, "EGI": names, "NOI": names, "cap rate": names.lower(),
            "gross potential rent": names.lower(), "effective gross income": names.lower(),
            "operating costs": names.lower(), "vacancy": names.lower(), "purchase price": names.lower(),
            "delta": text.SECTION_PURPOSES["comparison"], "rent roll": text.DEFINITIONS["monthly_rent"]["where_to_find"],
        }
        for term, definition_place in defined_in.items():
            with self.subTest(term=term):
                self.assertIn(term, definition_place)
        # jargon that the page does not define must not appear anywhere
        for jargon in ["debt service", "comps", "cash flow", "cash-on-cash", "pro forma", "underwrit", "NNN", "ROI"]:
            for piece in all_text():
                with self.subTest(jargon=jargon, piece=piece[:40]):
                    self.assertNotIn(jargon.lower(), piece.lower())

    def test_T5_cap_rate_note(self):
        for word in ("risk", "location", "building condition", "not always a better deal", "market context"):
            with self.subTest(word=word):
                self.assertIn(word, text.CAP_RATE_NOTE)
        self.assertEqual(text.CAP_RATE_TAG, "market context")  # the tag is explained by the note

    def test_T7_reports_purpose(self):
        self.assertIn(sentences(text.REPORTS_PURPOSE), (1, 2))
        for kind in ("PDF", "Word", "text", "paste"):
            with self.subTest(kind=kind):
                self.assertIn(kind, text.REPORTS_PURPOSE)
        self.assertEqual(sentences(text.REPORTS_CHOOSE_FIRST), 1)
        self.assertIn("{limit} MB", text.REPORTS_TOO_LARGE)

    def test_T8_report_problems(self):
        self.assertEqual(set(text.REPORT_PROBLEMS), {"encrypted", "unreadable", "no_text", "not_supported"})
        for problem, message in text.REPORT_PROBLEMS.items():
            with self.subTest(problem=problem):
                self.assertIn("{name}", message)
                self.assertIn("type the numbers in", message.lower())  # every problem says what to do instead

    def test_T9_report_worked_formulas(self):
        formulas = {"yearly_rent": "÷ 12", "average_rent": "{given} × {units}", "monthly_costs": "× 12",
                    "occupancy": f"100% {MINUS} {{given}}"}
        self.assertEqual(set(text.REPORT_WORKED), set(formulas))
        for how, formula in formulas.items():
            with self.subTest(how=how):
                self.assertIn(formula, text.REPORT_WORKED[how])
                self.assertIn("= {value}", text.REPORT_WORKED[how])

    def test_T6_sample_deals(self):
        self.assertEqual(set(text.SAMPLE_DEALS), {"A", "B"})
        deal_a, errors_a = check_inputs(text.SAMPLE_DEALS["A"])
        deal_b, errors_b = check_inputs(text.SAMPLE_DEALS["B"])
        self.assertEqual((errors_a, errors_b), ({}, {}))
        self.assertEqual(deal_a, Deal(price=1_200_000, monthly_rent=14_400, vacancy_pct=5, operating_costs=62_000))
        self.assertEqual(deal_b, Deal(price=1_350_000, monthly_rent=15_600, vacancy_pct=7, operating_costs=70_000))

    def test_T6_more_sample_deals_are_valid_and_different(self):
        self.assertGreaterEqual(len(text.MORE_SAMPLE_DEALS), 2)
        every_pair = [text.SAMPLE_DEALS, *text.MORE_SAMPLE_DEALS]
        for number, pair in enumerate(text.MORE_SAMPLE_DEALS, start=2):
            for side in ("A", "B"):
                with self.subTest(example=number, property=side):
                    self.assertEqual(set(pair), {"A", "B"})
                    deal, errors = check_inputs(pair[side])
                    self.assertEqual(errors, {})  # every example passes the Input Checker
                    self.assertGreater(compute(deal).noi, 0)  # and makes money, as a listing would
        self.assertEqual(len({str(pair) for pair in every_pair}), len(every_pair))  # no two are the same


class TestWorkedFormulas(unittest.TestCase):

    def test_W1_sample_deal_formulas(self):
        deal = Deal(price=1_200_000, monthly_rent=14_400, vacancy_pct=5, operating_costs=62_000)
        self.assertEqual(text.worked_formulas(deal, compute(deal)), {
            "gpr": "GPR = $14,400 × 12 = $172,800",
            "egi": f"EGI = $172,800 × (1 {MINUS} 5.00%) = $164,160",
            "noi": f"NOI = $164,160 {MINUS} $62,000 = $102,160",   # the example in R8 and SRS Section 3.1
            "cap_rate_pct": "Cap rate = $102,160 ÷ $1,200,000 = 8.51%",
        })

    def test_W2_negative_noi(self):
        deal = Deal(price=1_000_000, monthly_rent=10_000, vacancy_pct=0, operating_costs=124_500)
        formulas = text.worked_formulas(deal, compute(deal))
        self.assertEqual(formulas["noi"], f"NOI = $120,000 {MINUS} $124,500 = {MINUS}$4,500")
        self.assertEqual(formulas["cap_rate_pct"], f"Cap rate = {MINUS}$4,500 ÷ $1,000,000 = {MINUS}0.45%")

    def test_W3_rounding_matches_the_results(self):
        # cents in the inputs are rounded the same way as everywhere else on the page
        deal = Deal(price=999_999.5, monthly_rent=1_000.5, vacancy_pct=7.5, operating_costs=2_000.25)
        formulas = text.worked_formulas(deal, compute(deal))
        self.assertEqual(formulas["gpr"], "GPR = $1,001 × 12 = $12,006")
        self.assertTrue(formulas["egi"].startswith(f"EGI = $12,006 × (1 {MINUS} 7.50%)"))
        self.assertIn("÷ $1,000,000", formulas["cap_rate_pct"])

    def test_every_result_has_a_formula(self):
        deal = Deal(price=1_200_000, monthly_rent=14_400, vacancy_pct=5, operating_costs=62_000)
        self.assertEqual(list(text.worked_formulas(deal, compute(deal))), list(RESULT_FIELDS))


class TestReportSummary(unittest.TestCase):

    def test_S1_inputs_not_found(self):
        self.assertEqual(text.report_summary({}, {}, {}), [
            "Purchase price: not found in the report, so type it in.",
            "Monthly rent (all units): not found in the report, so type it in.",
            "Vacancy rate: not found in the report, so type it in.",
            "Yearly operating costs: not found in the report, so type it in.",
        ])

    def test_S2_found_as_given(self):
        values = {"price": 1_200_000, "vacancy_pct": 5}
        sources = {"price": "Asking Price $1,200,000", "vacancy_pct": "Vacancy Rate\t 5%"}
        self.assertEqual(text.report_summary(values, sources, {}), [
            "Purchase price: $1,200,000, from “Asking Price $1,200,000”.",
            "Monthly rent (all units): not found in the report, so type it in.",
            "Vacancy rate: 5.00%, from “Vacancy Rate 5%”.",  # spaces and tabs in the report text become one space
            "Yearly operating costs: not found in the report, so type it in.",
        ])

    def test_S3_long_source_is_cut(self):
        source = "Asking Price " + "x" * 100 + " $1,200,000"
        line = text.report_summary({"price": 1_200_000}, {"price": source}, {})[0]
        quoted = line.split("“")[1].split("”")[0]
        self.assertEqual(len(quoted), text.REPORT_SOURCE_LIMIT)
        self.assertTrue(quoted.endswith("…"))

    def test_S4_worked_conversions(self):
        values = {"monthly_rent": 6_900, "vacancy_pct": 5, "operating_costs": 36_000}
        sources = {"monthly_rent": "Average rent: $1,150", "vacancy_pct": "95% occupied",
                   "operating_costs": "Monthly expenses: $3,000"}
        worked = {"monthly_rent": ("average_rent", 1_150, 6), "vacancy_pct": ("occupancy", 95, None),
                  "operating_costs": ("monthly_costs", 3_000, None)}
        summary = text.report_summary(values, sources, worked)
        self.assertIn("The report gives an average rent of $1,150 for each of its 6 units, so the monthly rent is "
                      "$1,150 × 6 = $6,900.", summary)
        self.assertIn(f"The report says 95.00% of the property is rented, so the vacancy rate is 100% {MINUS} "
                      "95.00% = 5.00%.", summary)
        self.assertIn("The report gives monthly operating costs of $3,000, so the yearly operating costs are "
                      "$3,000 × 12 = $36,000.", summary)
        yearly = text.report_summary({"monthly_rent": 15_600}, {"monthly_rent": "GSI $187,200"},
                                     {"monthly_rent": ("yearly_rent", 187_200, None)})
        self.assertIn("The report gives a yearly rent of $187,200, so the monthly rent is $187,200 ÷ 12 = $15,600.",
                      yearly)
        # each worked line comes right after the line for its input
        self.assertEqual(summary[summary.index("Vacancy rate: 5.00%, from “95% occupied”.") + 1][:28],
                         "The report says 95.00% of th")


if __name__ == "__main__":
    unittest.main()
