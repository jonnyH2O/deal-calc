"""PDF Text: gets the text out of a PDF file, using only the standard library.

Owner: Gabe Imbrunetti. Design: not yet in the SDS (see "Property reports" in ARCHITECTURE.md).

A PDF stores text as drawing instructions: choose a font and a size, move to a spot, draw these character codes.
extract_text() follows those instructions on each page, turns the codes into characters with the font's ToUnicode
map or its encoding, and rebuilds the lines from where the characters are drawn. Text on one line with a wide gap,
such as a label and its value in a table, is split by a tab, so the Report Reader can tell the cells apart.

It reads what listings are usually saved as: streams compressed with Flate, ASCII-hex, or ASCII-85; objects packed
in object streams; simple, TrueType, Type 3, and CID fonts; and text inside form XObjects. It raises
PdfError("encrypted") for an encrypted PDF and PdfError("unreadable") for a file it cannot make sense of. A PDF
whose pages are only pictures, such as a scan, has no text, so it gives "".

None of the arithmetic here is a deal formula: it only works out where characters are drawn on the page.
"""

import math
import re
import zlib
from base64 import a85decode
from dataclasses import dataclass, field, replace

MAX_STREAM_BYTES = 20_000_000  # a stream that inflates to more than this is cut off there (guards against zip bombs)
MAX_DEPTH = 32                 # nesting deeper than this (arrays, page trees, forms) is not followed
SAME_LINE = 0.5                # baselines closer than this many font sizes are on the same line
SPACE_GAP = 0.15               # a gap wider than this many font sizes between two pieces of text is a space
TAB_GAP = 1.0                  # and a gap wider than this many font sizes is a tab: the start of a new cell


class PdfError(ValueError):
    """The PDF cannot be read. str(error) says why: "encrypted" or "unreadable"."""


class Name(str):
    """A PDF name, such as /Font, without its slash."""


@dataclass(frozen=True)
class Ref:
    """A reference to another object, such as "12 0 R"."""

    num: int


@dataclass
class Stream:
    """A stream object: its dictionary and its bytes, still encoded."""

    info: dict
    raw: bytes


def extract_text(data: bytes) -> str:
    """The text of every page in data: one line of text per line on the page, with a tab between cells."""
    if _ENCRYPTED.search(data):
        raise PdfError("encrypted")
    try:
        objects = _read_objects(data)
        pages = []
        for page, resources in _pages(objects):
            pieces = []
            _paint(objects, _contents(objects, page), resources, _IDENTITY, pieces, 0)
            pages.append("\n".join(_lines(pieces)))
    except (ValueError, RecursionError) as error:  # PdfError is a ValueError
        raise PdfError("unreadable") from error
    return "\n".join(pages)


# ---------------------------------------------------------------- reading PDF syntax

_ENCRYPTED = re.compile(rb"/Encrypt\s*(?:\d+\s+\d+\s+R|<<)")
_SKIP = re.compile(rb"(?:[ \t\r\n\f\x00]+|%[^\r\n]*)*")  # spaces and % comments
_REGULAR = re.compile(rb"[^ \t\r\n\f\x00()<>\[\]{}/%]+")
_NUMERIC = re.compile(rb"[+-]?(?:\d+\.?\d*|\.\d+)")
_NAME_ESCAPE = re.compile(rb"#([0-9A-Fa-f]{2})")
_STRING_SPECIAL = re.compile(rb"[()\\]")
_ESCAPE = re.compile(rb"[0-7]{1,3}|\r\n|[\s\S]?")
_OCTAL = re.compile(rb"[0-7]{1,3}")
_ESCAPED = {b"n": b"\n", b"r": b"\r", b"t": b"\t", b"b": b"\b", b"f": b"\f", b"\r\n": b"", b"\n": b"", b"\r": b""}
_NOT_HEX = re.compile(rb"[^0-9A-Fa-f]")
_KEYWORDS = {b"true": True, b"false": False, b"null": None}


class _Lexer:
    """Reads PDF syntax from data one token at a time, starting at pos."""

    def __init__(self, data: bytes, pos: int = 0):
        self.data, self.pos = data, pos

    def token(self) -> tuple[str, object]:
        """The next token as (kind, value). kind is "num", "name", "str", "[", "]", "<<", ">>", "op", or "eof"."""
        data = self.data
        pos = _SKIP.match(data, self.pos).end()
        if pos >= len(data):
            self.pos = len(data)
            return "eof", None
        if data.startswith(b"/", pos):
            raw = _REGULAR.match(data, pos + 1)
            raw = raw.group() if raw else b""
            self.pos = pos + 1 + len(raw)
            return "name", Name(_NAME_ESCAPE.sub(lambda m: bytes.fromhex(m.group(1).decode()), raw).decode("latin-1"))
        if data.startswith(b"(", pos):
            return "str", self._literal(pos + 1)
        if data.startswith((b"<<", b">>"), pos):
            self.pos = pos + 2
            return data[pos:pos + 2].decode(), None
        if data.startswith(b"<", pos):
            close = data.find(b">", pos)
            close = len(data) if close < 0 else close
            self.pos = close + 1
            return "str", _unhex(data[pos + 1:close])
        word = _REGULAR.match(data, pos)
        if word is None:  # "[", "]", or a stray delimiter such as ")"
            self.pos = pos + 1
            char = data[pos:pos + 1]
            return (char.decode(), None) if char in (b"[", b"]") else ("op", char)
        self.pos = word.end()
        word = word.group()
        if _NUMERIC.fullmatch(word):
            return "num", float(word) if b"." in word else int(word)
        return "op", word

    def _literal(self, pos: int) -> bytes:
        """A (literal string) that starts just after its "(", with its escapes undone."""
        data, out, depth = self.data, bytearray(), 1
        while True:
            special = _STRING_SPECIAL.search(data, pos)
            if special is None:  # no closing ")": the string runs to the end
                out += data[pos:]
                self.pos = len(data)
                return bytes(out)
            out += data[pos:special.start()]
            pos = special.end()
            char = special.group()
            if char == b"(":
                depth += 1
                out += char
            elif char == b")":
                depth -= 1
                if depth == 0:
                    self.pos = pos
                    return bytes(out)
                out += char
            else:  # a backslash: an octal code, a letter such as \n, a line break that continues the string, or a char
                code = _ESCAPE.match(data, pos)
                pos = code.end()
                code = code.group()
                if _OCTAL.fullmatch(code):
                    out.append(int(code, 8) & 0xFF)
                else:
                    out += _ESCAPED.get(code, code)


def _unhex(text: bytes) -> bytes:
    """Bytes from hex digits. Anything else, such as spaces, is skipped, and a lone last digit is followed by 0."""
    digits = _NOT_HEX.sub(b"", text)
    if len(digits) % 2:
        digits += b"0"
    return bytes.fromhex(digits.decode())


def _object(lexer: _Lexer, kind: str | None = None, value: object = None, depth: int = 0) -> object:
    """Read one object (a number, name, string, array, dictionary, or reference) from lexer.

    Pass kind and value when the object's first token has already been read.
    """
    if depth > MAX_DEPTH:
        raise PdfError("unreadable")
    if kind is None:
        kind, value = lexer.token()
    if kind == "num" and isinstance(value, int):  # "12 0 R" is a reference; any other number is itself
        mark = lexer.pos
        if lexer.token()[0] == "num" and lexer.token() == ("op", b"R"):
            return Ref(value)
        lexer.pos = mark
    elif kind == "[":
        items = []
        while (token := lexer.token())[0] not in ("]", "eof"):
            items.append(_object(lexer, *token, depth + 1))
        return items
    elif kind == "<<":
        result = {}
        while (token := lexer.token())[0] not in (">>", "eof"):
            if token[0] == "name":  # a key; anything else where a key should be is skipped
                item = lexer.token()
                if item[0] in (">>", "eof"):
                    break
                result[token[1]] = _object(lexer, *item, depth + 1)
        return result
    elif kind == "op":
        return _KEYWORDS.get(value, value)
    return value


# ---------------------------------------------------------------- finding the objects and the pages

_OBJECT = re.compile(rb"(?<![0-9])(\d+)\s+\d+\s+obj\b")
_ENDSTREAM = re.compile(rb"\s*endstream")


def _read_objects(data: bytes) -> dict[int, object]:
    """Every object in the file by number, found by looking for "n 0 obj", so a broken cross-reference table does
    not matter. An object defined again later replaces the earlier one, as when a PDF has been updated."""
    objects = {}
    pos = 0
    while match := _OBJECT.search(data, pos):
        lexer = _Lexer(data, match.end())
        value = _object(lexer)
        if isinstance(value, dict):
            mark = lexer.pos
            if lexer.token() == ("op", b"stream"):
                value = _stream(lexer, value)
            else:
                lexer.pos = mark
        objects[int(match.group(1))] = value
        pos = lexer.pos
    _unpack_object_streams(objects)
    return objects


def _stream(lexer: _Lexer, info: dict) -> Stream:
    """The stream whose data follows the "stream" keyword the lexer just read. Moves the lexer past "endstream"."""
    data, start = lexer.data, lexer.pos
    if data.startswith(b"\r\n", start):
        start += 2
    elif data.startswith((b"\n", b"\r"), start):
        start += 1
    length = info.get("Length")
    if isinstance(length, int) and length >= 0 and _ENDSTREAM.match(data, start + length):
        end = start + length
    else:  # a missing or wrong /Length: the data ends at "endstream", without the line break before it
        end = data.find(b"endstream", start)
        end = len(data) if end < 0 else end
        end -= 2 if data[start:end].endswith(b"\r\n") else 1 if data[start:end].endswith((b"\n", b"\r")) else 0
    after = data.find(b"endstream", end)
    lexer.pos = len(data) if after < 0 else after + len(b"endstream")
    return Stream(info, data[start:end])


def _unpack_object_streams(objects: dict[int, object]) -> None:
    """Add the objects packed in object streams (PDF 1.5 and later). An object outside a stream wins."""
    for stream in [value for value in objects.values() if isinstance(value, Stream)]:
        first = _resolve(objects, stream.info.get("First"))
        if stream.info.get("Type") != "ObjStm" or not isinstance(first, int):
            continue
        data = _decode(objects, stream)
        lexer, header = _Lexer(data), []
        while lexer.pos < first and (token := lexer.token())[0] == "num":  # pairs of object number and offset
            header.append(token[1])
        for num, offset in zip(header[::2], header[1::2]):
            if isinstance(num, int) and isinstance(offset, int) and num not in objects:
                objects[num] = _object(_Lexer(data, first + offset))


def _resolve(objects: dict[int, object], value: object) -> object:
    """value, with references followed to the objects they name: None if one is missing or they go in a loop."""
    for _ in range(MAX_DEPTH):
        if not isinstance(value, Ref):
            return value
        value = objects.get(value.num)
    return None


def _decode(objects: dict[int, object], stream: Stream) -> bytes:
    """A stream's bytes with its filters undone, or b"" for a picture's filter or another one not read here."""
    filters = _resolve(objects, stream.info.get("Filter"))
    if not isinstance(filters, list):
        filters = [] if filters is None else [filters]
    data = stream.raw
    for name in filters:
        name = _resolve(objects, name)
        if name in ("FlateDecode", "Fl"):
            data = _inflate(data)
        elif name in ("ASCIIHexDecode", "AHx"):
            data = _unhex(data.split(b">")[0])
        elif name in ("ASCII85Decode", "A85"):
            data = _un85(data)
        else:  # DCT, JPX, CCITT, and JBIG2 hold pictures; LZW and run-length are old and rare
            return b""
    return data


def _inflate(data: bytes) -> bytes:
    """Flate-compressed data, inflated: at most MAX_STREAM_BYTES, and up to any damage in it."""
    inflater, out = zlib.decompressobj(), bytearray()
    for start in range(0, len(data), 65_536):
        try:
            out += inflater.decompress(data[start:start + 65_536], MAX_STREAM_BYTES + 1 - len(out))
        except zlib.error:
            break  # damaged data: keep what came out before the damage
        if len(out) > MAX_STREAM_BYTES or inflater.eof:
            break
    return bytes(out[:MAX_STREAM_BYTES])


def _un85(data: bytes) -> bytes:
    """ASCII-85 data (between "<~" and "~>"), decoded, or b"" if it is not valid."""
    text = re.sub(rb"\s+", b"", data)
    text = text[2:] if text.startswith(b"<~") else text
    try:
        return a85decode(text.split(b"~>")[0])
    except ValueError:
        return b""


def _pages(objects: dict[int, object]) -> list[tuple[dict, object]]:
    """Each page with its resources, in page order. Without a page tree, every page object in number order."""
    catalog = next((value for value in objects.values() if isinstance(value, dict)
                    and value.get("Type") == "Catalog"), {})
    root = _resolve(objects, catalog.get("Pages"))
    found = []
    if isinstance(root, dict):
        _walk(objects, root, None, found, set(), 0)
    return found or [(value, value.get("Resources")) for _, value in sorted(objects.items())
                     if isinstance(value, dict) and value.get("Type") == "Page"]


def _walk(objects: dict[int, object], node: dict, resources: object, found: list, seen: set, depth: int) -> None:
    """Add the pages under one node of the page tree. Resources are inherited from the nodes above a page."""
    resources = node.get("Resources", resources)
    kids = _resolve(objects, node.get("Kids"))
    if not isinstance(kids, list):
        found.append((node, resources))
        return
    for kid in kids:
        if isinstance(kid, Ref):
            if kid.num in seen:  # a broken tree that loops back on itself
                continue
            seen.add(kid.num)
        kid = _resolve(objects, kid)
        if isinstance(kid, dict) and depth < MAX_DEPTH:
            _walk(objects, kid, resources, found, seen, depth + 1)


def _contents(objects: dict[int, object], page: dict) -> bytes:
    """A page's content streams, decoded and joined."""
    contents = _resolve(objects, page.get("Contents"))
    parts = [_resolve(objects, part) for part in (contents if isinstance(contents, list) else [contents])]
    return b"\n".join(_decode(objects, part) for part in parts if isinstance(part, Stream))


# ---------------------------------------------------------------- fonts

_CODECS = {"WinAnsiEncoding": "cp1252", "MacRomanEncoding": "mac_roman", "StandardEncoding": "latin-1"}

# Glyph names that are not their own text, for fonts that list their characters by name (a /Differences array).
# A one-letter name, such as /A, is the letter itself, and "uni20AC" or "u20AC" gives the character by its code.
_GLYPHS = {
    "space": " ", "exclam": "!", "quotedbl": '"', "numbersign": "#", "dollar": "$", "percent": "%",
    "ampersand": "&", "quotesingle": "'", "quoteright": "’", "quoteleft": "‘", "parenleft": "(",
    "parenright": ")", "asterisk": "*", "plus": "+", "comma": ",", "hyphen": "-", "minus": "−", "period": ".",
    "slash": "/", "colon": ":", "semicolon": ";", "less": "<", "equal": "=", "greater": ">", "question": "?",
    "at": "@", "bracketleft": "[", "backslash": "\\", "bracketright": "]", "underscore": "_", "endash": "–",
    "emdash": "—", "bullet": "•", "periodcentered": "·", "nbspace": " ",
    **dict(zip(["zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine"], "0123456789")),
}
_UNICODE_NAME = re.compile(r"uni([0-9A-Fa-f]{4})|u([0-9A-Fa-f]{4,6})")


@dataclass
class _Font:
    """What drawing text needs from a font: how many bytes make a character code, the text each code stands for,
    and how wide it is."""

    code_bytes: int = 1                          # 2 for CID fonts (Type0)
    codec: str = "cp1252"                        # for one-byte codes that chars does not list
    chars: dict = field(default_factory=dict)    # character code → text
    widths: dict = field(default_factory=dict)   # character code → width, in thousandths of the font size
    default_width: float = 500

    def codes(self, text: bytes) -> list[int]:
        """The character codes in a string."""
        if self.code_bytes == 1:
            return list(text)
        return [int.from_bytes(text[i:i + 2], "big") for i in range(0, len(text) - 1, 2)]

    def char(self, code: int) -> str:
        """The text a character code stands for ("" for a two-byte code with no ToUnicode entry)."""
        if code in self.chars:
            return self.chars[code]
        return bytes([code]).decode(self.codec, errors="replace") if self.code_bytes == 1 else ""


def _load_font(objects: dict[int, object], info: object) -> _Font:
    """The _Font for a font dictionary, or a plain one-byte font if info is not one."""
    info = _resolve(objects, info)
    font = _Font()
    if not isinstance(info, dict):
        return font
    if info.get("Subtype") == "Type0":
        font.code_bytes, font.default_width = 2, 1000
        descendants = _resolve(objects, info.get("DescendantFonts"))
        child = _resolve(objects, descendants[0]) if isinstance(descendants, list) and descendants else None
        if isinstance(child, dict):
            font.default_width = _number(_resolve(objects, child.get("DW")), 1000)
            font.widths = _cid_widths(objects, _resolve(objects, child.get("W")))
    else:
        _simple_font(objects, info, font)
    to_unicode = _resolve(objects, info.get("ToUnicode"))
    if isinstance(to_unicode, Stream):
        font.chars.update(_cmap(_decode(objects, to_unicode)))
    return font


def _simple_font(objects: dict[int, object], info: dict, font: _Font) -> None:
    """Fill in a one-byte font's encoding, its /Differences, and its widths."""
    encoding = _resolve(objects, info.get("Encoding"))
    base = _resolve(objects, encoding.get("BaseEncoding")) if isinstance(encoding, dict) else encoding
    font.codec = _CODECS.get(base, "cp1252")
    differences = _resolve(objects, encoding.get("Differences")) if isinstance(encoding, dict) else None
    code = 0
    for item in differences if isinstance(differences, list) else []:
        if isinstance(item, Name):
            font.chars[code] = _glyph_text(item)
            code += 1
        elif isinstance(item, int):
            code = item
    first = _resolve(objects, info.get("FirstChar"))
    widths = _resolve(objects, info.get("Widths"))
    matrix = _resolve(objects, info.get("FontMatrix"))  # a Type 3 font measures its widths in its own units
    scale = _number(matrix[0], 0.001) * 1000 if isinstance(matrix, list) and matrix else 1
    if isinstance(first, int) and isinstance(widths, list):
        for offset, width in enumerate(widths):
            font.widths[first + offset] = _number(_resolve(objects, width), font.default_width) * scale


def _cid_widths(objects: dict[int, object], items: object) -> dict[int, float]:
    """Widths from a CID font's /W array: "c [w1 w2 ...]" gives codes c, c+1, ...; "c1 c2 w" gives c1 to c2."""
    widths = {}
    items = [_resolve(objects, item) for item in items] if isinstance(items, list) else []
    i = 0
    while i + 1 < len(items):
        first, second = items[i], items[i + 1]
        if isinstance(first, int) and isinstance(second, list):
            for offset, width in enumerate(second):
                widths[first + offset] = _number(width, 1000)
            i += 2
        elif i + 2 < len(items) and isinstance(first, int) and isinstance(second, int):
            for code in range(first, min(second, first + 0xFFFF) + 1):
                widths[code] = _number(items[i + 2], 1000)
            i += 3
        else:
            break  # a /W array this does not understand: the rest use the default width
    return widths


def _number(value: object, default: float) -> float:
    """value if it is a number, otherwise default."""
    return value if isinstance(value, (int, float)) and not isinstance(value, bool) else default


_HEX = rb"<([0-9A-Fa-f\s]*)>"
_BFCHAR = re.compile(rb"beginbfchar(.*?)endbfchar", re.S)
_BFRANGE = re.compile(rb"beginbfrange(.*?)endbfrange", re.S)
_CHAR_PAIR = re.compile(_HEX + rb"\s*" + _HEX)
_RANGE = re.compile(_HEX + rb"\s*" + _HEX + rb"\s*(<[0-9A-Fa-f\s]*>|\[[^\]]*\])")


def _cmap(data: bytes) -> dict[int, str]:
    """Character code → text, from a ToUnicode CMap's bfchar and bfrange sections."""
    chars = {}
    for block in _BFCHAR.findall(data):
        for code, text in _CHAR_PAIR.findall(block):
            chars[int.from_bytes(_unhex(code), "big")] = _utf16(text)
    for block in _BFRANGE.findall(data):
        for low, high, target in _RANGE.findall(block):
            low, high = int.from_bytes(_unhex(low), "big"), int.from_bytes(_unhex(high), "big")
            if target.startswith(b"["):  # a list with one target for each code
                for offset, text in enumerate(re.findall(_HEX, target)):
                    chars[low + offset] = _utf16(text)
                continue
            text = _utf16(target[1:-1])  # one target: consecutive codes stand for consecutive characters
            for offset in range(min(high - low, 0xFFFF) + 1):
                chars[low + offset] = text[:-1] + chr(min(ord(text[-1]) + offset, 0x10FFFF)) if text else ""
    return chars


def _utf16(hex_text: bytes) -> str:
    """Text from a CMap's hex target, which is UTF-16 (some PDFs write one-byte targets for plain ASCII)."""
    raw = _unhex(hex_text)
    if len(raw) % 2:
        raw = b"\x00" + raw
    return raw.decode("utf-16-be", errors="replace")


def _glyph_text(name: str) -> str:
    """The text a glyph name stands for: "dollar" → "$", "uni20AC" → "€", "f_i" → "fi", "zero.lf" → "0"."""
    text = ""
    for part in name.split(".")[0].split("_"):
        code = _UNICODE_NAME.fullmatch(part)
        if part in _GLYPHS:
            text += _GLYPHS[part]
        elif len(part) == 1:
            text += part
        elif code:
            text += chr(min(int(code.group(1) or code.group(2), 16), 0x10FFFF))
    return text


# ---------------------------------------------------------------- following the drawing instructions

_IDENTITY = (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)
_SETTINGS = {b"Tc": "char_space", b"Tw": "word_space", b"TL": "leading", b"Ts": "rise"}
_INLINE_DATA = re.compile(rb"(?<![^\s])ID\s")
_INLINE_END = re.compile(rb"\sEI(?=\s|$)")


@dataclass
class _State:
    """The settings that drawing text uses. q saves them and Q puts them back."""

    ctm: tuple = _IDENTITY                     # where the page's coordinates are (a, b, c, d, e, f)
    font: _Font = field(default_factory=_Font)
    size: float = 0.0                          # font size (Tf)
    char_space: float = 0.0                    # extra space after each character (Tc)
    word_space: float = 0.0                    # extra space after each space character (Tw)
    scale: float = 1.0                         # horizontal stretch (Tz, as a fraction)
    leading: float = 0.0                       # the distance from one line to the next (TL)
    rise: float = 0.0                          # raised or lowered text (Ts)


@dataclass
class _Piece:
    """Some text drawn in one go: where it starts (x, y) and ends (end), and the font size on the page."""

    x: float
    y: float
    end: float
    size: float
    text: str


def _multiply(m: tuple, n: tuple) -> tuple:
    """The matrix product m × n, for matrices written as PDF writes them: (a, b, c, d, e, f)."""
    a, b, c, d, e, f = m
    a2, b2, c2, d2, e2, f2 = n
    return (a * a2 + b * c2, a * b2 + b * d2, c * a2 + d * c2, c * b2 + d * d2,
            e * a2 + f * c2 + e2, e * b2 + f * d2 + f2)


def _numbers(args: list, count: int) -> tuple:
    """The last count operands, as floats. Raises ValueError if there are too few or they are not numbers."""
    values = args[-count:] if len(args) >= count else []
    if len(values) != count or not all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in values):
        raise ValueError("expected numbers")
    return tuple(float(value) for value in values)


def _paint(objects: dict, content: bytes, resources: object, ctm: tuple, pieces: list, depth: int) -> None:
    """Follow a content stream's instructions, and add each piece of text it draws to pieces."""
    resources = _resolve(objects, resources)
    resources = resources if isinstance(resources, dict) else {}
    font_infos, xobjects = (_resolve(objects, resources.get(key)) for key in ("Font", "XObject"))
    font_infos = font_infos if isinstance(font_infos, dict) else {}
    xobjects = xobjects if isinstance(xobjects, dict) else {}
    fonts, saved, operands = {}, [], []
    state = _State(ctm=ctm)
    tm = lm = _IDENTITY  # the text matrix, and the text line matrix (where the current line starts)
    lexer = _Lexer(content)
    while (token := lexer.token())[0] != "eof":
        kind, op = token
        if kind != "op":
            operands.append(_object(lexer, kind, op) if kind in ("[", "<<") else op)
            continue
        args, operands = operands, []
        try:
            if op == b"BI":
                lexer.pos = _after_inline_image(content, lexer.pos)
            elif op == b"q":
                saved.append(replace(state))
            elif op == b"Q" and saved:
                state = saved.pop()
            elif op == b"cm":
                state.ctm = _multiply(_numbers(args, 6), state.ctm)
            elif op == b"BT":
                tm = lm = _IDENTITY
            elif op == b"Tf":
                (state.size,) = _numbers(args, 1)
                if args[-2] not in fonts:
                    fonts[args[-2]] = _load_font(objects, font_infos.get(args[-2]))
                state.font = fonts[args[-2]]
            elif op in _SETTINGS:
                setattr(state, _SETTINGS[op], _numbers(args, 1)[0])
            elif op == b"Tz":
                state.scale = _numbers(args, 1)[0] / 100
            elif op in (b"Td", b"TD"):
                tx, ty = _numbers(args, 2)
                if op == b"TD":
                    state.leading = -ty
                tm = lm = _multiply((1, 0, 0, 1, tx, ty), lm)
            elif op == b"Tm":
                tm = lm = _numbers(args, 6)
            elif op in (b"T*", b"'", b'"'):  # ' and " start a new line, then draw a string
                if op == b'"':
                    state.word_space, state.char_space = _numbers(args[:-1], 2)
                tm = lm = _multiply((1, 0, 0, 1, 0, -state.leading), lm)
                if op != b"T*":
                    tm = _show(args[-1], state, tm, pieces)
            elif op == b"Tj":
                tm = _show(args[-1], state, tm, pieces)
            elif op == b"TJ":  # strings, and numbers that move the next string left (thousandths of the size)
                for item in args[-1]:
                    if isinstance(item, bytes):
                        tm = _show(item, state, tm, pieces)
                    else:
                        tm = _multiply((1, 0, 0, 1, -_numbers([item], 1)[0] / 1000 * state.size * state.scale, 0), tm)
            elif op == b"Do":
                form = _resolve(objects, xobjects.get(args[-1]))
                if isinstance(form, Stream) and form.info.get("Subtype") == "Form" and depth < MAX_DEPTH:
                    matrix = _resolve(objects, form.info.get("Matrix"))
                    matrix = _numbers(matrix, 6) if isinstance(matrix, list) else _IDENTITY
                    _paint(objects, _decode(objects, form), form.info.get("Resources", resources),
                           _multiply(matrix, state.ctm), pieces, depth + 1)
        except (IndexError, TypeError, ValueError):
            pass  # a broken instruction is skipped, as PDF viewers do


def _after_inline_image(content: bytes, pos: int) -> int:
    """Where the content continues after an inline image (BI ... ID data EI), whose data is not PDF syntax."""
    start = _INLINE_DATA.search(content, pos)
    end = _INLINE_END.search(content, start.end()) if start else None
    return end.end() if end else len(content)


def _show(text: bytes, state: _State, tm: tuple, pieces: list) -> tuple:
    """Draw a string: add it to pieces as one piece, and return the text matrix moved past it."""
    if not isinstance(text, bytes):
        raise TypeError("a string to draw must be bytes")
    start = _multiply((1, 0, 0, 1, 0, state.rise), _multiply(tm, state.ctm))
    chars = []
    for code in state.font.codes(text):
        chars.append(state.font.char(code))
        width = state.font.widths.get(code, state.font.default_width) / 1000
        spacing = state.char_space + (state.word_space if code == 32 and state.font.code_bytes == 1 else 0)
        tm = _multiply((1, 0, 0, 1, (width * state.size + spacing) * state.scale, 0), tm)
    size = math.hypot(start[2], start[3]) * state.size
    text = "".join(chars)
    if text.strip() and size > 0:
        pieces.append(_Piece(start[4], start[5], _multiply(tm, state.ctm)[4], size, text))
    return tm


# ---------------------------------------------------------------- putting the text back into lines

def _lines(pieces: list[_Piece]) -> list[str]:
    """One page's pieces of text as lines: top to bottom, and left to right within each line."""
    lines, line = [], []
    for piece in sorted(pieces, key=lambda p: -p.y):
        if line and abs(line[0].y - piece.y) > SAME_LINE * max(line[0].size, piece.size):
            lines.append(_join(line))
            line = []
        line.append(piece)
    if line:
        lines.append(_join(line))
    return lines


def _join(line: list[_Piece]) -> str:
    """A line's pieces, left to right, with a space or a tab where there is a gap between two of them."""
    line = sorted(line, key=lambda p: p.x)
    text = line[0].text
    for before, piece in zip(line, line[1:]):
        gap = (piece.x - before.end) / max(before.size, piece.size)
        if gap > TAB_GAP:
            text += "\t"
        elif gap > SPACE_GAP and not text.endswith(" ") and not piece.text.startswith(" "):
            text += " "
        text += piece.text
    return text
