"""Starts the Deal Calculator: `python -m dealcalc [--port N]`.

Checks the Python version first, so an installer with an old Python gets a clear message instead of an error
from deep inside the code. Everything else is done by the Page Host.
"""

import sys

if sys.version_info < (3, 11):
    print(f"Deal Calculator needs Python 3.11 or later, but this is Python {sys.version.split()[0]}. "
          "Install a newer Python, then create the virtual environment again (see the README).", file=sys.stderr)
    sys.exit(1)

from dealcalc import page_host  # noqa: E402  (imported after the version check on purpose)

sys.exit(page_host.main(sys.argv[1:]))
