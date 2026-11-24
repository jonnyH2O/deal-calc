"""Run the tests and report which lines of each dealcalc module never ran (white-box testing).

    python tests/line_coverage.py

Uses only the standard library (trace), so there is nothing to install. Lines in the page server's request
handler run on a server thread, so tracing is turned on for threads too. A module at 100% has had every line run
by at least one test; the branch tables in each test file show which test covers which branch.
"""

import ast
import sys
import threading
import trace
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PACKAGE = ROOT / "dealcalc"
sys.path.insert(0, str(ROOT))


def executable_lines(path: Path) -> set[int]:
    """Line numbers that hold code Python can run, from the compiled code objects (docstrings excluded)."""
    lines = set()

    def walk(code):
        for _, _, line in code.co_lines():
            if line is not None:
                lines.add(line)
        for const in code.co_consts:
            if hasattr(const, "co_lines"):
                walk(const)

    source = path.read_text(encoding="utf-8")
    walk(compile(source, str(path), "exec"))
    # docstrings show up as code lines in some Python versions; they are text, not code, so leave them out
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
            lines -= set(range(node.lineno, node.end_lineno + 1))
    lines.discard(0)  # Python's marker for "start of module", not a real line
    return lines


def run_tests():
    """Find and run every test. Importing happens in here so that import-time lines are traced too."""
    suite = unittest.defaultTestLoader.discover(str(ROOT / "tests"), top_level_dir=str(ROOT))
    return unittest.TextTestRunner(verbosity=0).run(suite)


def main() -> int:
    tracer = trace.Trace(count=1, trace=0, ignoredirs=[sys.prefix, sys.exec_prefix])
    threading.settrace(tracer.globaltrace)
    result = tracer.runfunc(run_tests)
    threading.settrace(None)

    ran = {}
    for (filename, line), _count in tracer.results().counts.items():
        ran.setdefault(Path(filename).resolve(), set()).add(line)

    print("\nLine coverage of dealcalc (lines that never ran are listed):")
    for path in sorted(PACKAGE.glob("*.py")):
        code_lines = executable_lines(path)
        missed = sorted(code_lines - ran.get(path.resolve(), set()))
        percent = 100 * (len(code_lines) - len(missed)) / len(code_lines) if code_lines else 100
        detail = f"  missed lines: {', '.join(map(str, missed))}" if missed else ""
        print(f"  {path.name:<22} {percent:5.1f}% of {len(code_lines):>3} lines{detail}")
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())
