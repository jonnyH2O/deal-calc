# Deal Calculator

The Deal Calculator works out net operating income (NOI) and cap rate for a property listing, and explains each
number for members who are new to real estate investing. It was built for the UO Real Estate Investment Group
(UOREIG) as CS 422 Project 2 by Jonny Heinrich, Ben Horrisberger, Gabe Imbrunetti, and Alejandro Zamorano.

It runs on your own computer and shows its page in a web browser. It uses only the Python standard library, saves
nothing, and needs no internet connection or account.

## Install

You need Python 3.11 or later. Check with `python3 --version` (macOS and Linux) or `python --version` (Windows).

1. Open a terminal in this folder.
2. Create and turn on a virtual environment.

   macOS and Linux:

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

   Windows:

   ```bash
   python -m venv .venv
   .venv\Scripts\activate
   ```

3. Install the requirements. The calculator uses only the standard library, so this installs nothing, but it is
   safe to run:

   ```bash
   pip install -r requirements.txt
   ```

## Run

With the virtual environment turned on:

```bash
python -m dealcalc
```

The calculator checks itself and prints a status report. When it is ready, it prints:

```
Deal Calculator is running. Open http://127.0.0.1:8000 in a browser. Press Ctrl+C to stop.
```

Open that address in a browser. If port 8000 is busy, the calculator tries ports 8001 to 8009 and prints the one
it chose. To start from a different port, run `python -m dealcalc --port 9000`. If it cannot start, it prints the
problem and how to fix it.

### Load property reports

Instead of typing the numbers, press **Load reports**, choose a listing or property report for Property A (and one
for Property B to compare two), and press **Read reports**. The calculator reads PDF, Word (.docx), and text
files, or text you paste in. It shows where it found each number and how it worked out any it had to convert, such
as a yearly rent divided by 12. Check the numbers against the report: anything it could not find is left empty for
you to type. Encrypted PDFs and scans can't be read; copy their text and paste it instead, or type the numbers in.

To try it, use the made-up listings in `samples/`: `maple-court-listing.pdf` for Property A and
`oak-grove-listing.pdf` for Property B.

## Test

```bash
python -m unittest
```

To see which lines of each module the tests never ran:

```bash
python tests/line_coverage.py
```

## How the code is organized

See [ARCHITECTURE.md](ARCHITECTURE.md) for the modules, how they fit together, and the rules for changing them.
The full design is in the team's Software Design Specification (SDS), and the requirements (R1 to R20) are in the
Software Requirements Specification (SRS).
