"""Checks that the package matches the interfaces in the SDS.

Run with: python -m unittest
Each module has its own white-box test file (test_deal_math.py, test_page_host.py, and so on).
"""

import dataclasses
import unittest

from dealcalc import (deal_evaluator, deal_math, input_checker, number_format, page_host, pdf_text, report_reader,
                     teaching_content)


class TestInterfaces(unittest.TestCase):
    """Every module has the services listed in SDS Section 4, and the property report services (not yet in the
    SDS; see "Property reports" in ARCHITECTURE.md)."""

    def test_modules_have_their_services(self):
        expected = {
            deal_math: ["Deal", "Results", "compute", "deltas", "monthly_from_yearly", "yearly_from_monthly",
                        "total_from_average", "vacancy_from_occupancy"],
            input_checker: ["LIMITS", "WARNING_LIMITS", "parse_number", "check_inputs", "find_warnings"],
            number_format: ["format_money", "format_percent", "format_delta", "format_input"],
            teaching_content: ["PAGE_PURPOSE", "SECTION_PURPOSES", "DEFINITIONS", "CAP_RATE_NOTE", "SAMPLE_DEALS",
                               "worked_formulas", "CAP_RATE_TAG", "REPORTS_PURPOSE", "REPORT_PROBLEMS",
                               "report_summary"],
            deal_evaluator: ["evaluate", "page_text", "self_check", "read_reports"],
            page_host: ["main", "DealRequestHandler", "DEFAULT_PORT", "reports_from"],
            report_reader: ["Reading", "read_report", "read_text"],
            pdf_text: ["PdfError", "extract_text"],
        }
        for module, names in expected.items():
            for name in names:
                with self.subTest(module=module.__name__, name=name):
                    self.assertTrue(hasattr(module, name))

    def test_deal_and_results_fields(self):
        self.assertEqual(tuple(f.name for f in dataclasses.fields(deal_math.Deal)), deal_math.INPUT_FIELDS)
        self.assertEqual(tuple(f.name for f in dataclasses.fields(deal_math.Results)), deal_math.RESULT_FIELDS)

    def test_every_input_has_limits_definitions_and_sample_values(self):
        for field in deal_math.INPUT_FIELDS:
            with self.subTest(field=field):
                self.assertIn(field, input_checker.LIMITS)
                self.assertIn(field, teaching_content.DEFINITIONS)
                self.assertIn(field, teaching_content.SAMPLE_DEALS["A"])
                self.assertIn(field, teaching_content.SAMPLE_DEALS["B"])


if __name__ == "__main__":
    unittest.main()
