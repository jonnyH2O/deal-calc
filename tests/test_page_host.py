"""White-box tests for the Page Host (dealcalc/page_host.py; SDS 4.6; R14, R20) and dealcalc/__main__.py.

The tests are written from the code: each branch below is taken both ways by at least one test, named in the
right-hand column. python tests/line_coverage.py confirms that every line runs.

DealServer.server_bind()
    H1  the system has SO_EXCLUSIVEADDRUSE      true on Windows, false on macOS and Linux. This depends on the
                                                system running the tests, so each side is taken on its own system
                                                by test_O1_port_in_use_moves_to_the_next_port.
DealRequestHandler.do_GET()
    G1  path is a page file                     true: test_G1_page_files          false: test_G2_text
    G2  path is /text                           true: test_G2_text                false: test_G3_unknown_get
DealRequestHandler.do_POST()
    P1  path is not /evaluate or /read-reports  true: test_P1_unknown_post        false: test_P4_evaluate
    P2  Content-Length or body not readable     true: test_P2_not_json, test_P2_content_length_not_a_number
                                                false: test_P4_evaluate
    P2b Content-Length over MAX_BODY_BYTES      true: test_P2_body_too_large      false: test_P4_evaluate
    P5  path is /read-reports                   true: test_P5_read_reports        false: test_P4_evaluate
    P6  its body has the wrong shape            true: test_P6_read_reports_wrong_shape
                                                false: test_P5_read_reports
    P3  body has the wrong shape                true: test_P3_wrong_shape         false: test_P4_evaluate
DealRequestHandler._answer()
    A1  the Deal Evaluator fails unexpectedly   true: test_A1_unexpected_failure_gets_500
                                                false: test_P4_evaluate
reports_from(body)
    B1  body is not a dictionary                true: test_B_reports_from         false: the same test
    B2  a property has no report (null or left out)   true/false: test_B_reports_from
    B3  a report has the wrong shape            true/false: test_B_reports_from
    B4  a report's data is not base64           true/false: test_B_reports_from
check_install()
    C1  page files are missing                  true: test_C1_missing_page_files  false: test_C3_ready
    C2  the self-check finds a problem          true: test_C2_self_check_fails    false: test_C3_ready
open_server(first_port)
    O1  a port is in use (OSError)              true: test_O1_port_in_use_moves_to_the_next_port
                                                false: test_M3_runs_until_ctrl_c
    O2  every port is in use                    true: test_O2_every_port_in_use  false: test_O1_port_in_use...
main(argv)
    M1  check_install() finds a problem         true: test_M1_install_problem    false: test_M3_runs_until_ctrl_c
    M2  no free port                            true: test_M2_no_free_port       false: test_M3_runs_until_ctrl_c
    M3  stopped with Ctrl+C                     true: test_M3_runs_until_ctrl_c
__main__.py
    V1  Python is older than 3.11               true: test_V1_old_python         false: test_V1_runs_main
"""

import base64
import contextlib
import http.client
import io
import json
import runpy
import sys
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request
from pathlib import Path
from unittest import mock

from dealcalc import deal_evaluator, page_host, teaching_content


class ServerTest(unittest.TestCase):
    """Runs a real Page Host on a free port for the whole class."""

    @classmethod
    def setUpClass(cls):
        cls.server = page_host.DealServer((page_host.HOST, 0), page_host.DealRequestHandler)
        cls.port = cls.server.server_address[1]
        cls.url = f"http://{page_host.HOST}:{cls.port}"
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

    def post_json(self, data):
        return self.request("/evaluate", json.dumps(data).encode("utf-8"))


class TestGet(ServerTest):

    def test_G1_page_files(self):
        for path, content_type in [("/", "text/html"), ("/page.css", "text/css"), ("/page.js", "text/javascript")]:
            with self.subTest(path=path):
                with urllib.request.urlopen(self.url + path, timeout=5) as response:
                    self.assertEqual(response.status, 200)
                    self.assertTrue(response.headers["Content-Type"].startswith(content_type))
                    self.assertTrue(response.read())

    def test_G1_page_loads_in_under_2_seconds(self):
        # R20: after the calculator starts, its page loads in less than 2 seconds
        start = time.perf_counter()
        for path in ("/", "/page.css", "/page.js", "/text"):
            self.request(path)
        self.assertLess(time.perf_counter() - start, 2)

    def test_G2_text(self):
        status, body = self.request("/text")
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body), json.loads(json.dumps(deal_evaluator.page_text())))

    def test_G3_unknown_get(self):
        status, body = self.request("/nothing-here")
        self.assertEqual(status, 404)
        self.assertEqual(json.loads(body), {"error": "There is no page at /nothing-here."})


class TestPost(ServerTest):

    def test_P1_unknown_post(self):
        status, body = self.request("/somewhere", b"{}")
        self.assertEqual(status, 404)
        self.assertIn("error", json.loads(body))

    def test_P2_not_json(self):
        status, body = self.request("/evaluate", b"not json")
        self.assertEqual((status, json.loads(body)), (400, {"error": "The request body is not valid JSON."}))

    def test_P2_content_length_not_a_number(self):
        connection = http.client.HTTPConnection(page_host.HOST, self.port, timeout=5)
        connection.putrequest("POST", "/evaluate")
        connection.putheader("Content-Length", "abc")
        connection.endheaders()
        response = connection.getresponse()
        self.assertEqual(response.status, 400)
        connection.close()

    def test_P3_wrong_shape(self):
        sample = teaching_content.SAMPLE_DEALS["A"]
        bad_bodies = [[], {"A": "1", "B": None, "seq": 1}, {"A": sample, "B": "x", "seq": 1},
                      {"A": sample, "B": None, "seq": "1"}, {"A": sample, "B": None}]
        for body in bad_bodies:
            with self.subTest(body=body):
                status, answer = self.post_json(body)
                self.assertEqual(status, 400)
                self.assertIn('"seq": number', json.loads(answer)["error"])

    def test_P4_evaluate(self):
        samples = teaching_content.SAMPLE_DEALS
        status, body = self.post_json({"A": samples["A"], "B": samples["B"], "seq": 42})
        report = json.loads(body)
        self.assertEqual(status, 200)
        self.assertEqual(report["seq"], 42)  # the same seq comes back, so the page can ignore old answers
        self.assertEqual(report["A"]["results"]["noi"], "$102,160")
        self.assertEqual(report["deltas"]["noi"], "+$1,936")

    def test_P2_body_too_large(self):
        # refused from its Content-Length alone, before the body is read
        connection = http.client.HTTPConnection(page_host.HOST, self.port, timeout=5)
        connection.putrequest("POST", "/read-reports")
        connection.putheader("Content-Length", str(page_host.MAX_BODY_BYTES + 1))
        connection.endheaders()
        response = connection.getresponse()
        self.assertEqual(response.status, 413)
        self.assertEqual(json.loads(response.read()), {"error": deal_evaluator.reports_too_large(page_host.MAX_REPORT_MB)})
        connection.close()

    def test_P5_read_reports(self):
        report = base64.b64encode(b"Asking Price: $1,200,000\nVacancy Rate: 5%").decode()
        status, body = self.request("/read-reports", json.dumps({"A": {"name": "maple.txt", "data": report},
                                                                 "B": None}).encode())
        answer = json.loads(body)
        self.assertEqual(status, 200)
        self.assertIsNone(answer["B"])
        self.assertEqual(answer["A"]["name"], "maple.txt")
        self.assertEqual(answer["A"]["inputs"], {"price": "1,200,000", "vacancy_pct": "5"})

    def test_P6_read_reports_wrong_shape(self):
        status, body = self.request("/read-reports", json.dumps({"A": {"name": "x.pdf"}}).encode())
        self.assertEqual(status, 400)
        self.assertIn('"data": base64', json.loads(body)["error"])

    def test_A1_unexpected_failure_gets_500(self):
        with mock.patch.object(deal_evaluator, "evaluate", side_effect=RuntimeError("a bug")), \
                contextlib.redirect_stderr(io.StringIO()) as terminal:
            status, body = self.post_json({"A": {}, "B": None, "seq": 1})
        self.assertEqual(status, 500)
        self.assertIn("details are in the terminal", json.loads(body)["error"])
        self.assertIn("RuntimeError: a bug", terminal.getvalue())  # the details are printed for a maintainer


class TestReportsFrom(unittest.TestCase):

    def test_B_reports_from(self):
        data = base64.b64encode(b"report").decode()
        cases = [
            ([], None),                                                              # not a dictionary
            ({}, {"A": None, "B": None}),                                            # both left out
            ({"A": {"name": "a.pdf", "data": data}, "B": None}, {"A": ("a.pdf", b"report"), "B": None}),
            ({"A": None, "B": {"name": "", "data": data}}, {"A": None, "B": ("", b"report")}),
            ({"A": "a.pdf"}, None),                                                  # not a dictionary
            ({"A": {"name": 5, "data": data}}, None),                                # the name is not text
            ({"A": {"name": "a.pdf", "data": None}}, None),                          # no data
            ({"A": {"name": "a.pdf", "data": "not base64!"}}, None),                 # data not base64
        ]
        for body, reports in cases:
            with self.subTest(body=body):
                self.assertEqual(page_host.reports_from(body), reports)


class TestCheckInstall(unittest.TestCase):

    def test_C3_ready(self):
        self.assertIsNone(page_host.check_install())

    def test_C1_missing_page_files(self):
        with tempfile.TemporaryDirectory() as empty, mock.patch.object(page_host, "STATIC_DIR", Path(empty)):
            problem = page_host.check_install()
        self.assertIn("page.html, page.css, page.js are missing", problem)
        self.assertIn("see the README", problem)

    def test_C2_self_check_fails(self):
        with mock.patch.object(deal_evaluator, "self_check", return_value="gpr is $1 but should be $172,800"):
            problem = page_host.check_install()
        self.assertEqual(problem, "the self-check on the sample deal failed: gpr is $1 but should be $172,800")


class TestOpenServer(unittest.TestCase):

    def test_O1_port_in_use_moves_to_the_next_port(self):
        first = page_host.DealServer((page_host.HOST, 0), page_host.DealRequestHandler)
        taken = first.server_address[1]
        second = page_host.open_server(taken)
        try:
            self.assertIsNotNone(second)
            self.assertNotEqual(second.server_address[1], taken)
        finally:
            first.server_close()
            if second:
                second.server_close()

    def test_O2_every_port_in_use(self):
        with mock.patch.object(page_host, "DealServer", side_effect=OSError("in use")) as server:
            self.assertIsNone(page_host.open_server(9000))
        tried = [call.args[0][1] for call in server.call_args_list]
        self.assertEqual(tried, list(range(9000, 9010)))


class TestMain(unittest.TestCase):

    def run_main(self, argv):
        """Run main() and return (exit code, what it printed, what it printed as errors)."""
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = page_host.main(argv)
        return code, out.getvalue(), err.getvalue()

    def test_M1_install_problem(self):
        with mock.patch.object(page_host, "check_install", return_value="the page files are missing"):
            code, out, err = self.run_main([])
        self.assertEqual(code, 1)
        self.assertEqual(err.strip(), "Deal Calculator could not start: the page files are missing")

    def test_M2_no_free_port(self):
        with mock.patch.object(page_host, "open_server", return_value=None):
            code, out, err = self.run_main(["--port", "9000"])
        self.assertEqual(code, 1)
        self.assertIn("ports 9000 to 9009 are all in use", err)
        self.assertIn("python -m dealcalc --port", err)  # says how to fix it (R14)

    def test_M3_runs_until_ctrl_c(self):
        with mock.patch.object(page_host.DealServer, "serve_forever", side_effect=KeyboardInterrupt):
            code, out, err = self.run_main(["--port", "0"])  # port 0 lets the system pick a free port
        self.assertEqual(code, 0)
        self.assertRegex(out, r"Deal Calculator is running\. Open http://127\.0\.0\.1:\d+ in a browser\. "
                              r"Press Ctrl\+C to stop\.")
        self.assertIn("Deal Calculator stopped.", out)
        self.assertEqual(err, "")


class TestDunderMain(unittest.TestCase):
    """dealcalc/__main__.py, run the way `python -m dealcalc` runs it."""

    def test_V1_runs_main(self):
        with mock.patch.object(page_host, "main", return_value=0) as main, \
                mock.patch.object(sys, "argv", ["dealcalc", "--port", "9000"]):
            with self.assertRaises(SystemExit) as exit_:
                runpy.run_module("dealcalc", run_name="__main__")
        main.assert_called_once_with(["--port", "9000"])
        self.assertEqual(exit_.exception.code, 0)

    def test_V1_old_python(self):
        with mock.patch.object(sys, "version_info", (3, 10, 0)), \
                mock.patch.object(page_host, "main") as main, contextlib.redirect_stderr(io.StringIO()) as err:
            with self.assertRaises(SystemExit) as exit_:
                runpy.run_module("dealcalc", run_name="__main__")
        self.assertEqual(exit_.exception.code, 1)
        self.assertIn("needs Python 3.11 or later", err.getvalue())
        main.assert_not_called()


if __name__ == "__main__":
    unittest.main()
