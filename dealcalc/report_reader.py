"""Report Reader: finds a property's four inputs in a listing or property report.

Owner: Gabe Imbrunetti. Design: not yet in the SDS (see "Property reports" in ARCHITECTURE.md).

read_report() takes the bytes of a report file: a PDF (its text comes from PDF Text), a Word file (.docx), or plain
text, such as text a member pasted. It splits the text into lines, and each line into cells at tabs or at runs of
two or more spaces. For each input it looks for the labels that listings use, most specific first, and takes the
number that belongs to the label:

- in the same cell, after the label: "List Price: $1.35M";
- at the start of the next cell: "Asking Price | $1,200,000";
- or at the start of the cell under the label, as in a row of labels over a row of numbers ("Units" over "12"),
  unless the line after that has a number there too: then the label heads a column of a longer table, such as a
  rent roll, and no one number belongs to it.

A percent may also come just before its label: "95% occupied". Only a few words may come between a label and its
number, and none that make it a different number, so "Price per Unit", "Average Rent", and "Effective Gross Income"
are not taken for the price or the monthly rent.

Some inputs are often given in another form, so they are worked out with Deal Math: a yearly rent (divided by 12),
an average rent per unit (times the number of units), monthly operating costs (times 12), or an occupancy rate
(100 minus it). Each is recorded so the page can show how it was worked out. This module writes no words for
members (Teaching Content does) and has no formulas of its own.
"""

import io
import re
import zipfile
import zlib
from dataclasses import dataclass, field
from decimal import Decimal
from itertools import islice
from xml.etree import ElementTree

from dealcalc import deal_math, pdf_text

MAX_GAP_CHARACTERS = 40           # a label's number must start within this many characters of the label
MAX_GAP_WORDS = {"money": 3, "percent": 3, "count": 0}  # and with at most this many words in between
MAX_UNITS = 10_000                # the most units a property can have
MAX_WORD_FILE_BYTES = 20_000_000  # the most of a Word file's text that is read


@dataclass(frozen=True)
class Reading:
    """What read_report() found in one report."""

    values: dict = field(default_factory=dict)   # field name → the input's value, in the input's own unit
    sources: dict = field(default_factory=dict)  # field name → the report text the value was read from
    worked: dict = field(default_factory=dict)   # field name → (how, the report's number, the number of units or
                                                 # None), for an input worked out from another number
    problem: str | None = None                   # why the file could not be read at all, or None:
                                                 # "encrypted", "unreadable", "no_text", or "not_supported"


def read_report(data: bytes) -> Reading:
    """Find the four inputs in a report file: a PDF, a Word file, or plain text. No side effects."""
    if b"%PDF-" in data[:1024]:
        try:
            text = pdf_text.extract_text(data)
        except pdf_text.PdfError as problem:
            return Reading(problem=str(problem))
    elif data.startswith(b"PK\x03\x04"):  # a zip file, which is what a Word file is
        try:
            text = _word_text(data)
        except (zipfile.BadZipFile, EOFError, zlib.error, ElementTree.ParseError):
            return Reading(problem="unreadable")
        if text is None:
            return Reading(problem="not_supported")
    elif b"\x00" in data[:4096] and not data.startswith((b"\xff\xfe", b"\xfe\xff")):  # a picture or other binary
        return Reading(problem="not_supported")
    else:
        text = _plain_text(data)
    if not text.strip():
        return Reading(problem="no_text")
    return read_text(text)


# ---------------------------------------------------------------- getting the text

_WORD = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


def _word_text(data: bytes) -> str | None:
    """A Word file's text, with each table row on one line and a tab between its cells. None if data is a zip file
    but not a Word file (such as an Excel file)."""
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        if "word/document.xml" not in archive.namelist():
            return None
        with archive.open("word/document.xml") as part:
            document = ElementTree.fromstring(part.read(MAX_WORD_FILE_BYTES))
    lines = []
    _word_lines(document, lines)
    return "\n".join(lines)


def _word_lines(element: ElementTree.Element, lines: list[str]) -> None:
    """Add each paragraph under element as a line, and each table row as a line of cells."""
    for child in element:
        if child.tag == _WORD + "p":
            lines.append(_word_paragraph(child))
        elif child.tag == _WORD + "tr":
            cells = [cell for cell in child if cell.tag == _WORD + "tc"]
            lines.append("\t".join(" ".join(map(_word_paragraph, cell.iter(_WORD + "p"))) for cell in cells))
        else:  # the body, a table, or another container: look inside it
            _word_lines(child, lines)


def _word_paragraph(paragraph: ElementTree.Element) -> str:
    """A paragraph's text, keeping its tabs and line breaks."""
    parts = []
    for node in paragraph.iter():
        if node.tag == _WORD + "t":
            parts.append(node.text or "")
        elif node.tag == _WORD + "tab":
            parts.append("\t")
        elif node.tag in (_WORD + "br", _WORD + "cr"):
            parts.append("\n")
    return "".join(parts)


def _plain_text(data: bytes) -> str:
    """Text from a text file: UTF-16 with a byte order mark, UTF-8, or, if it is not UTF-8, Windows-1252."""
    if data.startswith((b"\xff\xfe", b"\xfe\xff")):
        return data.decode("utf-16", errors="replace")
    try:
        return data.decode("utf-8-sig")
    except UnicodeDecodeError:
        return data.decode("cp1252", errors="replace")


# ---------------------------------------------------------------- finding the inputs

def _label(pattern: str) -> re.Pattern:
    return re.compile(pattern, re.I)


_RENT_WORDS = r"(?:rents?|rental\s+income|income)"

# Each search is (field, label, the kind of number, how the input comes from that number, words that must not come
# just before the label). The searches run in this order, and the first one that finds a number sets its input.
#   how: "input" is the input itself; "yearly_rent" is ÷ 12; "average_rent" is × the number of units;
#   "occupancy" is 100 minus it. Operating costs given for a month become "monthly_costs" (× 12).
_SEARCHES = [
    ("price",
     _label(r"\b(?:asking|list(?:ing)?|offer(?:ing)?|sales?|purchase)\s+price\b|\boffered\s+at\b|\bprice\b"),
     "money", "input", _label(r"\b(?:last|sold|previous|prior|original)\W*$")),
    ("monthly_rent",
     _label(rf"\b(?:(?:total|gross)\s+)*monthly\s+(?:gross\s+)?{_RENT_WORDS}|\b{_RENT_WORDS}\s+per\s+month\b"),
     "money", "input", _label(r"\b(?:effective|average|avg|net|market)\W*$")),
    ("monthly_rent",
     _label(rf"\b(?:gross\s+)?(?:potential|scheduled)\s+(?:gross\s+)?{_RENT_WORDS}"
            rf"|\b(?:total\s+)?(?:annual|yearly)\s+(?:gross\s+)?{_RENT_WORDS}"
            rf"|\bgross\s+(?:annual\s+|yearly\s+)?{_RENT_WORDS}"),
     "money", "yearly_rent", _label(r"\b(?:effective|average|avg|net|market)\W*$")),
    ("monthly_rent",
     _label(r"\b(?:average|avg\.?)\s+(?:monthly\s+)?rents?(?:\s+per\s+unit)?|\brents?\s+per\s+unit\b"),
     "money", "average_rent", None),
    ("vacancy_pct", _label(r"\bvacan(?:cy|t)\b"), "percent", "input", None),
    ("vacancy_pct", _label(r"\b(?:occupancy|occupied|leased)\b"), "percent", "occupancy", None),
    ("operating_costs",
     _label(r"\b(?:total\s+)?(?:(?:annual|yearly|monthly)\s+)?(?:operating\s+)?expenses\b"
            r"|\b(?:total\s+)?(?:(?:annual|yearly|monthly)\s+)?operating\s+costs\b|\bopex\b"),
     "money", "input", _label(r"\b(?:capital|closing|one-time|renovation)\W*$")),
]
_UNITS_LABEL = _label(r"\b(?:(?:number|#|no\.?)\s*of\s+|total\s+)?units\b|\bunit\s+count\b")
_UNITS_PHRASE = _label(r"\b(\d{1,5})[-\s]?units?\b")  # "12-unit building", "12 units"

# A number: "$1,200,000", "1,200,000", "$1.35M", "$850K", "2.5 million", "5%", "(7%)", "($62,000)", "-$4,500".
_NUMBER = re.compile(r"""
    \(?\s*-?\s*(?P<dollar>\$)?\s*-?\s*
    (?P<digits>\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?|\.\d+)
    (?:\s*(?P<word>million|thousand)\b|(?P<letter>mm|m|k)\b)?
    (?P<percent>\s*(?:%|percent\b))?
""", re.I | re.X)
_MULTIPLIERS = {"million": 1_000_000, "mm": 1_000_000, "m": 1_000_000, "thousand": 1_000, "k": 1_000}
_PERCENT_BEFORE = re.compile(r"(?P<digits>\d+(?:\.\d+)?)\s*(?:%|percent)\s*$", re.I)

# Words between a label and its number that make it a different number than the input.
_WRONG_NUMBER = _label(r"\bper\s+(?:unit|door|bed(?:room)?|room|sf|sq|square|foot|ft)\b"
                       r"|/\s*(?:unit|door|bed|room|sf|sq|ft)\b"
                       r"|\b(?:reduc|chang|increas|decreas|drop|differen|ratio|projected)\w*|\bcut\b|\brange\b"
                       r"|\bpro\s*-?\s*forma\b")
_GAP_WORD = re.compile(r"[A-Za-z]{2,}")
_LETTER = re.compile(r"[A-Za-z]")
_MONTHLY = _label(r"\bmonthly\b|\bper\s+month\b|/\s*mo(?:nth)?\b|\ba\s+month\b")
_PERIOD_AFTER = _label(r"\s*(?:/\s*(?:mo|month|yr|year)\b|(?:per|a)\s+(?:month|year)\b|monthly\b|yearly\b|annually\b)")
_CELL_BREAK = re.compile(r"\t| {2,}")
_TIDY = str.maketrans({" ": " ", " ": " ", " ": " ", " ": " ", "−": "-", "–": "-",
                       "—": "-", "＄": "$", "％": "%"})


@dataclass(frozen=True)
class _Found:
    number: float  # the number, in the report's own form (such as a yearly rent)
    source: str    # the report text it was read from
    context: str   # the label and the number, with words like "monthly" or "/mo" just after the number


def read_text(text: str) -> Reading:
    """Find the four inputs in a report's text (see the module docstring). No side effects."""
    rows = _rows(text)
    values, sources, worked = {}, {}, {}
    for field_name, label, want, how, blocked in _SEARCHES:
        if field_name in values:
            continue
        found = _find(rows, label, want, blocked)
        if found is None:
            continue
        how = _period(field_name, how, found.context)
        units = _unit_count(rows) if how == "average_rent" else None
        if how == "average_rent" and units is None:
            continue  # an average rent is no use without the number of units
        values[field_name] = _CONVERSIONS[how](found.number, units)
        sources[field_name] = found.source
        if how != "input":
            worked[field_name] = (how, found.number, units)
    return Reading(values, sources, worked)


# How each input is worked out from the number found (Deal Math has the formulas).
_CONVERSIONS = {
    "input": lambda number, units: number,
    "yearly_rent": lambda number, units: deal_math.monthly_from_yearly(number),
    "average_rent": deal_math.total_from_average,
    "occupancy": lambda number, units: deal_math.vacancy_from_occupancy(number),
    "monthly_costs": lambda number, units: deal_math.yearly_from_monthly(number),
}


def _period(field_name: str, how: str, context: str) -> str:
    """how, changed when the report gives the amount for a month: a "gross income" that is monthly is the monthly
    rent itself, and monthly operating costs are worked out for the year."""
    if field_name == "monthly_rent" and how == "yearly_rent" and _MONTHLY.search(context):
        return "input"
    if field_name == "operating_costs" and _MONTHLY.search(context):
        return "monthly_costs"
    return how


def _rows(text: str) -> list[list[str]]:
    """The text's lines as lists of cells, leaving out empty lines and cells."""
    rows = []
    for line in text.translate(_TIDY).splitlines():
        cells = [cell.strip() for cell in _CELL_BREAK.split(line) if cell.strip()]
        if cells:
            rows.append(cells)
    return rows


def _find(rows: list[list[str]], label: re.Pattern, want: str, blocked: re.Pattern | None) -> _Found | None:
    """The first number of the kind want ("money", "percent", or "count") that belongs to label."""
    for i, cells in enumerate(rows):
        for j, cell in enumerate(cells):
            for match in label.finditer(cell):
                if blocked is not None and blocked.search(cell, 0, match.start()):
                    continue
                found = _number_for(rows, i, j, match, want)
                if found is not None:
                    return found
    return None


def _number_for(rows: list[list[str]], i: int, j: int, match: re.Match, want: str) -> _Found | None:
    """The number for one label: just before it (a percent only), after it in its cell, in the next cell, or under
    it. None if it has none."""
    cells, cell = rows[i], rows[i][j]
    before = _PERCENT_BEFORE.search(cell, 0, match.start()) if want == "percent" else None
    if before:
        return _Found(float(before["digits"]), cell, cell)
    after = _number_after(cell, match.end(), want)
    if after is not None:
        value, end = after
        return _Found(value, cell, cell[match.start():end] + _period_after(cell, end))
    if not _short_gap(_NUMBER.sub(" ", cell[match.end():]), want):
        return None
    neighbors = cells[j + 1:j + 2]
    if _heads_one_value(rows, i, j, want):
        neighbors.append(rows[i + 1][j])
    for other in neighbors:
        starting = _number_starting(other, want)
        if starting is not None:
            value, end = starting
            return _Found(value, f"{cell} {other}", f"{cell[match.start():]} {other[:end]}{_period_after(other, end)}")
    return None


def _number_after(cell: str, label_end: int, want: str) -> tuple[float, int] | None:
    """(value, where it ends) for the number after a label in its cell. One number of another kind may come first,
    as in "Total Expenses (35%) $62,000" or "Vacancy $13,104 (7%)"."""
    numbers = list(islice(_NUMBER.finditer(cell, label_end), 2))
    if not numbers or not _short_gap(cell[label_end:numbers[0].start()], want):
        return None
    for k, number in enumerate(numbers):
        if k == 1 and _LETTER.search(cell, numbers[0].end(), number.start()):
            break  # words between the two numbers: the second one is about something else
        value = _value(number, want)
        if value is not None:
            return value, number.end()
    return None


def _number_starting(cell: str, want: str) -> tuple[float, int] | None:
    """(value, where it ends) for a number of the kind want at the very start of a cell."""
    number = _NUMBER.match(cell)
    value = _value(number, want) if number else None
    return None if value is None else (value, number.end())


def _heads_one_value(rows: list[list[str]], i: int, j: int, want: str) -> bool:
    """Whether the cell under rows[i][j] holds its value: the next row has as many cells, and the row after that
    does not carry on the column with another number, as a table of several rows would."""
    width = len(rows[i])
    if i + 1 >= len(rows) or len(rows[i + 1]) != width:
        return False
    return not (i + 2 < len(rows) and len(rows[i + 2]) == width and _number_starting(rows[i + 2][j], want))


def _short_gap(gap: str, want: str) -> bool:
    """Whether the text between a label and its number is short and does not make it a different number."""
    return (len(gap) <= MAX_GAP_CHARACTERS and len(_GAP_WORD.findall(gap)) <= MAX_GAP_WORDS[want]
            and not _WRONG_NUMBER.search(gap))


def _period_after(text: str, end: int) -> str:
    """Words such as "/mo" or "per year" just after a number."""
    period = _PERIOD_AFTER.match(text, end)
    return period.group() if period else ""


def _value(number: re.Match, want: str) -> float | None:
    """The number a _NUMBER match stands for, if it is of the kind want, or None.

    A percent needs "%" or "percent". Money needs a "$", a thousands comma, a word such as "million", or at least
    four digits, so "12 parking spaces" is not taken for a price; "M" and "K" multiply only after a "$". A count is
    a whole number from 1 to MAX_UNITS with no "$".
    """
    digits = number["digits"].replace(",", "")
    if number["percent"] or want == "percent":
        return float(digits) if number["percent"] and want == "percent" else None
    if want == "count":
        whole = "." not in digits and not number["dollar"] and 1 <= int(digits) <= MAX_UNITS
        return float(digits) if whole else None
    suffix = (number["word"] or (number["letter"] if number["dollar"] else None) or "").lower()
    if not (number["dollar"] or "," in number["digits"] or suffix or len(digits.split(".")[0]) >= 4):
        return None
    return float(Decimal(digits) * _MULTIPLIERS.get(suffix, 1))


def _unit_count(rows: list[list[str]]) -> float | None:
    """The number of units: from a label such as "Number of Units", or else a phrase such as "12-unit"."""
    found = _find(rows, _UNITS_LABEL, "count", None)
    if found is not None:
        return found.number
    for cells in rows:
        for cell in cells:
            phrase = _UNITS_PHRASE.search(cell)
            if phrase and 1 <= int(phrase[1]) <= MAX_UNITS:
                return float(phrase[1])
    return None
