"""White-box tests for the Deal Evaluator (dealcalc/deal_evaluator.py; SDS 4.5; R12, and the self-check behind R14).

The tests are written from the code: each branch below is taken both ways by at least one test, named in the
right-hand column. python tests/line_coverage.py confirms that every line runs.

Teaching Content's worked_formulas() is replaced by a stand-in here, so these tests check only the Evaluator.
Its real text is tested in tests/test_teaching_content.py.

format_results(results)
    F1  field is a rate field               true: test_F1_cap_rate_as_percent_others_in_dollars (cap rate)
                                            false: the same test (GPR, EGI, NOI)
evaluate_property(raw)
    E1  the inputs have errors              true: test_E1_property_with_errors    false: test_E1_valid_property
evaluate(raw_a, raw_b)
    E2  raw_b is None (single mode)         true: test_E2_single_property_mode    false: test_E3_both_valid
    E3  both properties are valid           true: test_E3_both_valid
                                            false: test_E4_which_property_to_fix (all three cases)
    E4  each property in the "to fix" list  A only, B only, and both: test_E4_which_property_to_fix
self_check()
    S1  sample deal A has input errors      true: test_S1_sample_with_input_errors
                                            false: test_S3_sample_matches_r5
    S2  a result differs from R5            true: test_S2_results_that_differ_from_r5
                                            false: test_S3_sample_matches_r5
    S3  nothing differs (returns None)      true: test_S3_sample_matches_r5
                                            false: test_S2_results_that_differ_from_r5
read_reports(reports) and read_report(name, data)
    P1  no report for a property            true: test_P1_no_report_for_b         false: test_P3_report_read
    P2  pasted text, with no file name      true: test_P2_pasted_text             false: test_P3_report_read
    P3  the report could not be read        true: test_P3_report_not_read         false: test_P3_report_read
reports_too_large(limit_mb)  (no branches)  test_reports_too_large
"""

import json
import unittest
from pathlib import Path
from unittest import mock

from dealcalc import deal_evaluator, teaching_content
from dealcalc.deal_evaluator import evaluate, format_results, page_text, read_reports, self_check
from dealcalc.deal_math import Results
from dealcalc.number_format import MINUS

SAMPLE_A = teaching_content.SAMPLE_DEALS["A"]
SAMPLE_B = teaching_content.SAMPLE_DEALS["B"]
BAD = {**SAMPLE_A, "price": ""}


def fake_formulas(deal, results):
    """Stands in for Teaching Content's worked_formulas() until M8 is written."""
    return {"noi": f"NOI for price {deal.price:.0f}"}


class EvaluatorTest(unittest.TestCase):

    def setUp(self):
        patcher = mock.patch.object(teaching_content, "worked_formulas", side_effect=fake_formulas)
        self.worked_formulas = patcher.start()
        self.addCleanup(patcher.stop)


class TestFormatResults(EvaluatorTest):

    def test_F1_cap_rate_as_percent_others_in_dollars(self):
        shown = format_results(Results(gpr=172_800, egi=164_160, noi=-4_500, cap_rate_pct=8.5133))
        self.assertEqual(shown, {"gpr": "$172,800", "egi": "$164,160", "noi": f"{MINUS}$4,500",
                                 "cap_rate_pct": "8.51%"})


class TestEvaluateProperty(EvaluatorTest):

    def test_E1_valid_property(self):
        report = evaluate(SAMPLE_A, None)
        self.assertEqual(report["A"], {
            "errors": {},
            "warnings": {},
            "results": {"gpr": "$172,800", "egi": "$164,160", "noi": "$102,160", "cap_rate_pct": "8.51%"},
            "formulas": {"noi": "NOI for price 1200000"},
        })

    def test_E1_property_with_errors(self):
        report = evaluate(BAD, None)
        self.assertEqual(set(report["A"]["errors"]), {"price"})
        self.assertEqual(report["A"]["warnings"], {})
        self.assertIsNone(report["A"]["results"])
        self.assertIsNone(report["A"]["formulas"])
        self.worked_formulas.assert_not_called()  # no formulas are written from inputs with errors

    def test_E1_warnings_come_through(self):
        report = evaluate({**SAMPLE_A, "vacancy_pct": "40"}, None)
        self.assertEqual(set(report["A"]["warnings"]), {"vacancy_pct"})
        self.assertIsNotNone(report["A"]["results"])


class TestEvaluate(EvaluatorTest):

    def test_E2_single_property_mode(self):
        report = evaluate(SAMPLE_A, None)
        self.assertIsNone(report["B"])
        self.assertIsNone(report["deltas"])
        self.assertIsNone(report["deltas_message"])

    def test_E3_both_valid(self):
        report = evaluate(SAMPLE_A, SAMPLE_B)
        self.assertEqual(report["B"]["results"]["noi"], "$104,096")
        self.assertEqual(report["deltas"], {
            "price": "+$150,000", "monthly_rent": "+$1,200", "vacancy_pct": "+2.00 points",
            "operating_costs": "+$8,000", "gpr": "+$14,400", "egi": "+$9,936", "noi": "+$1,936",
            "cap_rate_pct": f"{MINUS}0.80 points",
        })
        self.assertIsNone(report["deltas_message"])

    def test_E4_which_property_to_fix(self):
        cases = [(BAD, SAMPLE_B, "Property A"), (SAMPLE_A, BAD, "Property B"),
                 (BAD, BAD, "Property A and Property B")]
        for raw_a, raw_b, names in cases:
            with self.subTest(names=names):
                report = evaluate(raw_a, raw_b)
                self.assertIsNone(report["deltas"])
                self.assertEqual(report["deltas_message"], f"Fix the inputs for {names} to see the deltas.")
                self.assertIsNotNone(report["B"])  # B's errors are still shown

    def test_report_can_be_sent_as_json(self):
        for raw_b in (None, SAMPLE_B, BAD):
            with self.subTest(raw_b=raw_b):
                json.dumps(evaluate(SAMPLE_A, raw_b))  # raises if anything in the report is not JSON

    def test_evaluate_does_not_change_its_inputs(self):
        raw_a, raw_b = dict(SAMPLE_A), dict(SAMPLE_B)
        evaluate(raw_a, raw_b)
        self.assertEqual((raw_a, raw_b), (SAMPLE_A, SAMPLE_B))


class TestPageText(unittest.TestCase):

    def test_page_text_is_teaching_content(self):
        text = page_text()
        self.assertEqual(text["page_purpose"], teaching_content.PAGE_PURPOSE)
        self.assertEqual(text["info_hint"], teaching_content.INFO_HINT)
        self.assertEqual(text["section_purposes"], teaching_content.SECTION_PURPOSES)
        self.assertEqual(text["definitions"], teaching_content.DEFINITIONS)
        self.assertEqual(text["cap_rate_note"], teaching_content.CAP_RATE_NOTE)
        self.assertEqual(text["cap_rate_tag"], teaching_content.CAP_RATE_TAG)
        self.assertEqual(text["reports_purpose"], teaching_content.REPORTS_PURPOSE)
        self.assertEqual(text["reports_choose_first"], teaching_content.REPORTS_CHOOSE_FIRST)
        self.assertEqual(text["sample_deals"], [teaching_content.SAMPLE_DEALS, *teaching_content.MORE_SAMPLE_DEALS])
        self.assertEqual(text["sample_deals"][0], teaching_content.SAMPLE_DEALS)  # the first press gives R5's
        json.dumps(text)


class TestSelfCheck(unittest.TestCase):

    def test_S3_sample_matches_r5(self):
        self.assertIsNone(self_check())

    def test_S1_sample_with_input_errors(self):
        broken = {"A": {**SAMPLE_A, "price": "abc"}, "B": SAMPLE_B}
        with mock.patch.object(teaching_content, "SAMPLE_DEALS", broken):
            problem = self_check()
        self.assertTrue(problem.startswith("sample deal A has input errors: The purchase price must be a number"))

    def test_S2_results_that_differ_from_r5(self):
        wrong_rent = {"A": {**SAMPLE_A, "monthly_rent": "14,000"}, "B": SAMPLE_B}
        with mock.patch.object(teaching_content, "SAMPLE_DEALS", wrong_rent):
            problem = self_check()
        self.assertIn("gpr is $168,000 but should be $172,800", problem)
        self.assertIn("cap_rate_pct is", problem)

    def test_S2_r5_answers_are_the_srs_numbers(self):
        self.assertEqual(deal_evaluator.R5_ANSWERS,
                         {"gpr": "$172,800", "egi": "$164,160", "noi": "$102,160", "cap_rate_pct": "8.51%"})


class TestReadReports(unittest.TestCase):

    def test_P3_report_read(self):
        report = b"Asking Price: $1.35M\nGross Scheduled Income (annual): $175,000\nVacancy: 7%"
        answer = read_reports({"A": ("oak.txt", report), "B": None})
        self.assertIsNone(answer["B"])
        reading = answer["A"]
        self.assertEqual(reading["name"], "oak.txt")
        # typed text for the page's inputs: the rent worked out to the cent, and no costs (the report has none)
        self.assertEqual(reading["inputs"], {"price": "1,350,000", "monthly_rent": "14,583.33", "vacancy_pct": "7"})
        self.assertEqual(reading["summary"][1],
                         "Monthly rent (all units): $14,583, from “Gross Scheduled Income (annual): $175,000”.")
        self.assertEqual(reading["summary"][-1], "Yearly operating costs: not found in the report, so type it in.")
        json.dumps(answer)  # raises if anything in the answer is not JSON

    def test_P2_pasted_text(self):
        reading = read_reports({"A": None, "B": ("", b"Vacancy: 5%")})["B"]
        self.assertEqual(reading["name"], teaching_content.PASTED_REPORT_NAME)
        self.assertEqual(reading["inputs"], {"vacancy_pct": "5"})

    def test_P3_report_not_read(self):
        reading = read_reports({"A": ("photo.png", b"\x89PNG\r\n\x1a\n\x00\x00"), "B": None})["A"]
        self.assertEqual(reading, {"name": "photo.png", "inputs": None, "summary": [
            teaching_content.REPORT_PROBLEMS["not_supported"].format(name="photo.png")]})

    def test_P1_no_report_for_b(self):
        self.assertEqual(read_reports({"A": None, "B": None}), {"A": None, "B": None})

    def test_sample_listing_gives_sample_deal_a(self):
        data = (Path(__file__).resolve().parent.parent / "samples" / "maple-court-listing.pdf").read_bytes()
        reading = read_reports({"A": ("maple-court-listing.pdf", data), "B": None})["A"]
        self.assertEqual(reading["inputs"], teaching_content.SAMPLE_DEALS["A"])
        # and what the page then shows for them is R5's answers
        self.assertEqual(evaluate(reading["inputs"], None)["A"]["results"], deal_evaluator.R5_ANSWERS)

    def test_reports_too_large(self):
        self.assertEqual(deal_evaluator.reports_too_large(18),
                         "The reports are too large to read. Choose files under 18 MB each, or paste their text "
                         "instead.")


if __name__ == "__main__":
    unittest.main()
