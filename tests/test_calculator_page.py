"""Checks the Calculator Page's files from Python (dealcalc/static/; SDS 4.7).

Python cannot run the page's JavaScript, so its behavior is checked by hand with tests/page_checklist.md, which
walks every state and transition in SDS Figure 3. These tests catch the mistakes that break the page silently:
an element ID that page.js looks for but page.html does not have, a missing SDS function, or field names that no
longer match the Python side.
"""

import re
import unittest
from pathlib import Path

from dealcalc import deal_math
from dealcalc.page_host import STATIC_DIR

HTML = (STATIC_DIR / "page.html").read_text(encoding="utf-8")
JS = (STATIC_DIR / "page.js").read_text(encoding="utf-8")


def js_list(name):
    """The strings in a JavaScript array constant, such as INPUT_FIELDS."""
    match = re.search(rf"const {name} = \[([^\]]*)\]", JS)
    return re.findall(r'"([^"]+)"', match.group(1))


class TestCalculatorPage(unittest.TestCase):

    def test_every_fixed_id_used_in_page_js_is_in_page_html(self):
        used = set(re.findall(r'byId\("([^"]+)"\)', JS))
        self.assertTrue(used)
        for element_id in used:
            with self.subTest(id=element_id):
                self.assertIn(f'id="{element_id}"', HTML)

    def test_every_section_info_button_explains_an_element_on_the_page(self):
        targets = re.findall(r'data-explains="([^"]+)"', HTML)
        self.assertEqual(sorted(targets), ["comparison", "inputs-section", "results-section"])
        for target in targets:
            with self.subTest(target=target):
                self.assertIn(f'id="{target}"', HTML)

    def test_every_section_purpose_has_a_place(self):
        for section in ("inputs", "results", "comparison"):
            with self.subTest(section=section):
                self.assertIn(f'id="{section}-purpose"', HTML)

    def test_page_js_has_the_sds_functions(self):
        for name in ("loadText", "requestEvaluation", "render", "switchMode", "toggleExplanation", "fillSample"):
            with self.subTest(function=name):
                self.assertRegex(JS, rf"(async )?function {name}\(")

    def test_page_js_has_the_report_functions(self):
        # the "Load reports" window, not yet in the SDS
        for name in ("openReports", "readReports", "reportFor", "applyReports"):
            with self.subTest(function=name):
                self.assertRegex(JS, rf"(async )?function {name}\(")
        self.assertIn('fetch("/read-reports"', JS)

    def test_every_property_has_its_report_elements(self):
        # page.js builds these IDs from the property's letter, so the check above cannot see them
        for prefix in ("report-file", "report-text", "report-summary", "source"):
            self.assertIn(f"byId(`{prefix}-${{property}}`)", JS)
            for side in ("A", "B"):
                with self.subTest(element=f"{prefix}-{side}"):
                    self.assertIn(f'id="{prefix}-{side}"', HTML)

    def test_context_fields_are_results(self):
        # the cap rate is shown as market context (R13); the constant must name a real result field
        self.assertTrue(set(js_list("CONTEXT_FIELDS")) <= set(deal_math.RESULT_FIELDS))
        self.assertEqual(js_list("CONTEXT_FIELDS"), ["cap_rate_pct"])

    def test_field_names_match_the_python_side(self):
        self.assertEqual(tuple(js_list("INPUT_FIELDS")), deal_math.INPUT_FIELDS)
        self.assertEqual(tuple(js_list("RESULT_FIELDS")), deal_math.RESULT_FIELDS)

    def test_page_js_does_no_math_on_results(self):
        # the page only shows numbers the Python side worked out: no parsing of numbers, no rounding
        for forbidden in ("parseFloat", "parseInt", "Number(", "toFixed", "Math."):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, JS)

    def test_page_loads_its_own_files_only(self):
        # nothing from the internet, so the calculator works with no internet connection
        for url in re.findall(r'(?:src|href)="([^"]+)"', HTML):
            with self.subTest(url=url):
                self.assertTrue(url.startswith("/"), url)


if __name__ == "__main__":
    unittest.main()
