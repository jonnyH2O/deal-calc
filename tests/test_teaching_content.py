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
    T5  the cap rate note names risk, location, and condition (R13) test_T5_cap_rate_note
    T6  the sample deals are the SRS's numbers (R5, R9)             test_T6_sample_deals
worked_formulas(deal, results)
    W1  each of the four formulas, with the sample deal (R8)       test_W1_sample_deal_formulas
    W2  a negative NOI keeps its minus sign through the formulas   test_W2_negative_noi
    W3  the formulas use the Number Formatter's rounding           test_W3_rounding_matches_the_results
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
    pieces = [text.PAGE_PURPOSE, text.INFO_HINT, text.CAP_RATE_NOTE, text.DELTAS_NEED_FIXING,
              *text.SECTION_PURPOSES.values()]
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
        for word in ("risk", "location", "building condition", "not always a better deal"):
            with self.subTest(word=word):
                self.assertIn(word, text.CAP_RATE_NOTE)

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


if __name__ == "__main__":
    unittest.main()
