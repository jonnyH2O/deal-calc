"""Page Host: starts the calculator, reports its status, and connects the page to the Deal Evaluator.

Owner: Ben Horrisberger (Project Plan M10). Skeleton: Jonny Heinrich.
Design: SDS Section 4.6. Requirements: R14, R20.

Routes (all on 127.0.0.1, so only this computer can reach them):
    GET  /, /page.css, /page.js   the Calculator Page's files
    GET  /text                    deal_evaluator.page_text() as JSON
    POST /evaluate                body {"A": raw, "B": raw or null, "seq": int}; returns evaluate(A, B) plus seq
Unknown paths get 404, and a body that is not valid JSON gets 400 with a message.

Skeleton note: while a module is still unwritten, its routes answer 501 and the start-up self-check is skipped
with a message, so the calculator still starts.
"""

import argparse
import json
import os
import socket
import sys
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from dealcalc import deal_evaluator

HOST = "127.0.0.1"
DEFAULT_PORT = 8000
PORT_TRIES = 10  # tries ports N to N+9
STATIC_DIR = Path(__file__).with_name("static")
PAGE_FILES = {
    "/": ("page.html", "text/html; charset=utf-8"),
    "/page.css": ("page.css", "text/css; charset=utf-8"),
    "/page.js": ("page.js", "text/javascript; charset=utf-8"),
}


class DealServer(ThreadingHTTPServer):
    """The HTTP server, set so that a port already in use is never shared.

    Python's HTTP server turns on address reuse. On Windows that lets a second program listen on a port that is
    already taken, so both would claim port 8000. On Windows we ask for the port exclusively instead.
    """

    allow_reuse_address = os.name != "nt"

    def server_bind(self):
        if hasattr(socket, "SO_EXCLUSIVEADDRUSE"):  # Windows only
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        super().server_bind()


class DealRequestHandler(BaseHTTPRequestHandler):
    """Answers the Calculator Page's requests."""

    def do_GET(self):
        if self.path in PAGE_FILES:
            name, content_type = PAGE_FILES[self.path]
            self._send(HTTPStatus.OK, (STATIC_DIR / name).read_bytes(), content_type)
        elif self.path == "/text":
            self._answer(deal_evaluator.page_text)
        else:
            self._send_message(HTTPStatus.NOT_FOUND, f"There is no page at {self.path}.")

    def do_POST(self):
        if self.path != "/evaluate":
            self._send_message(HTTPStatus.NOT_FOUND, f"There is no page at {self.path}.")
            return
        length = int(self.headers.get("Content-Length", 0))
        try:
            body = json.loads(self.rfile.read(length))
        except ValueError:
            self._send_message(HTTPStatus.BAD_REQUEST, "The request body is not valid JSON.")
            return
        if not (isinstance(body, dict) and isinstance(body.get("A"), dict)
                and isinstance(body.get("B"), (dict, type(None))) and isinstance(body.get("seq"), int)):
            self._send_message(HTTPStatus.BAD_REQUEST, 'The request body must be {"A": {...}, "B": {...} or null, '
                                                       '"seq": number}.')
            return
        self._answer(lambda: {**deal_evaluator.evaluate(body["A"], body["B"]), "seq": body["seq"]})

    def _answer(self, make_json):
        """Send make_json()'s result, or 501 while the module behind it is not written yet."""
        try:
            data = make_json()
        except NotImplementedError as missing:
            self._send_message(HTTPStatus.NOT_IMPLEMENTED, str(missing))
            return
        self._send(HTTPStatus.OK, json.dumps(data).encode("utf-8"), "application/json")

    def _send_message(self, status, message):
        self._send(status, json.dumps({"error": message}).encode("utf-8"), "application/json")

    def _send(self, status, body, content_type):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        pass  # keep the terminal for the status report


def check_install() -> str | None:
    """Return a problem with the installed calculator, or None if it is ready to start."""
    missing = [name for name, _ in PAGE_FILES.values() if not (STATIC_DIR / name).is_file()]
    if missing:
        return (f"the page files {', '.join(missing)} are missing from {STATIC_DIR}. "
                "Download the calculator's files again and reinstall it (see the README).")
    try:
        problem = deal_evaluator.self_check()
    except NotImplementedError:
        print("Self-check skipped: the Deal Evaluator is not written yet.")
        return None
    if problem:
        return f"the self-check on the sample deal failed: {problem}"
    return None


def open_server(first_port: int) -> DealServer | None:
    """Listen on the first free port from first_port to first_port + 9, or return None if all are taken."""
    for port in range(first_port, first_port + PORT_TRIES):
        try:
            return DealServer((HOST, port), DealRequestHandler)
        except OSError:
            continue
    return None


def main(argv: list[str]) -> int:
    """Start the calculator and serve the page until Ctrl+C. Returns the exit code: 0 after a normal stop, 1 if
    the calculator could not start (R14)."""
    parser = argparse.ArgumentParser(prog="python -m dealcalc", description="Start the Deal Calculator.")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT,
                        help=f"first port to try (default {DEFAULT_PORT}); the next {PORT_TRIES - 1} are tried too")
    args = parser.parse_args(argv)

    problem = check_install()
    if problem:
        print(f"Deal Calculator could not start: {problem}", file=sys.stderr)
        return 1
    server = open_server(args.port)
    if server is None:
        last = args.port + PORT_TRIES - 1
        print(f"Deal Calculator could not start: ports {args.port} to {last} are all in use. Close the program "
              f"using them, or start with a different port, for example: python -m dealcalc --port 9000",
              file=sys.stderr)
        return 1

    port = server.server_address[1]
    print(f"Deal Calculator is running. Open http://{HOST}:{port} in a browser. Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("Deal Calculator stopped.")
    finally:
        server.server_close()
    return 0
