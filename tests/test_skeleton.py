"""Checks that the package matches the interfaces in the SDS and that the Page Host answers requests.

Run with: python -m unittest
Each module's owner adds a test file for their module (test_deal_math.py, test_input_checker.py, and so on).
"""

import dataclasses
import json
import threading
import unittest
import urllib.error
import urllib.request

from dealcalc import deal_evaluator, deal_math, input_checker, number_format, page_host, teaching_content


class TestInterfaces(unittest.TestCase):
    """Every module has the services listed in SDS Section 4."""

    def test_modules_have_their_services(self):
        expected = {
            deal_math: ["Deal", "Results", "compute", "deltas"],
            input_checker: ["LIMITS", "WARNING_LIMITS", "parse_number", "check_inputs", "find_warnings"],
            number_format: ["format_money", "format_percent", "format_delta"],
            teaching_content: ["PAGE_PURPOSE", "SECTION_PURPOSES", "DEFINITIONS", "CAP_RATE_NOTE", "SAMPLE_DEALS",
                               "worked_formulas"],
            deal_evaluator: ["evaluate", "page_text", "self_check"],
            page_host: ["main", "DealRequestHandler", "DEFAULT_PORT"],
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


class TestPageHost(unittest.TestCase):
    """The Page Host serves the page and answers bad requests with clear errors."""

    @classmethod
    def setUpClass(cls):
        cls.server = page_host.DealServer((page_host.HOST, 0), page_host.DealRequestHandler)
        cls.url = f"http://{page_host.HOST}:{cls.server.server_address[1]}"
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def request(self, path, body=None):
        """Return (status, body bytes) for a GET, or a POST when body is given."""
        req = urllib.request.Request(self.url + path, data=body, method="POST" if body is not None else "GET")
        try:
            with urllib.request.urlopen(req, timeout=5) as response:
                return response.status, response.read()
        except urllib.error.HTTPError as error:
            return error.code, error.read()

    def test_page_files_are_served(self):
        for path in ("/", "/page.css", "/page.js"):
            with self.subTest(path=path):
                status, body = self.request(path)
                self.assertEqual(status, 200)
                self.assertTrue(body)

    def test_unknown_path_gets_404(self):
        self.assertEqual(self.request("/nothing-here")[0], 404)

    def test_body_that_is_not_json_gets_400(self):
        status, body = self.request("/evaluate", b"not json")
        self.assertEqual(status, 400)
        self.assertIn("error", json.loads(body))

    def test_body_with_wrong_shape_gets_400(self):
        self.assertEqual(self.request("/evaluate", json.dumps({"A": "1"}).encode())[0], 400)

    def test_install_check_passes(self):
        self.assertIsNone(page_host.check_install())

    def test_port_in_use_moves_to_the_next_port(self):
        taken = self.server.server_address[1]
        second = page_host.open_server(taken)
        self.assertIsNotNone(second)
        try:
            self.assertNotEqual(second.server_address[1], taken)
        finally:
            second.server_close()


if __name__ == "__main__":
    unittest.main()
