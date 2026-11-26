"""White-box tests for PDF Text (dealcalc/pdf_text.py; not yet in the SDS: see "Property reports" in ARCHITECTURE.md).

The tests are written from the code: each branch below is taken both ways by at least one test, named in the
right-hand column. python tests/line_coverage.py confirms that every line runs. Small PDFs are built by
tests/pdf_maker.py; real ones, made by Chrome and by macOS, are in samples/ and tests/reports/.

extract_text(data)
    X1  the PDF is encrypted                    true: test_X1_encrypted               false: test_X3_lines_cells_spaces
    X2  the PDF cannot be parsed                true: test_X2_unreadable              false: test_X3_lines_cells_spaces
_Lexer.token()
    K1  end of the data                         true: test_K_every_kind_of_token (last)  false: the same test
    K2  a name (#xx escapes; may be empty)      true/false: test_K_every_kind_of_token
    K3  a (literal string)                      true/false: test_K_every_kind_of_token
    K4  << or >>                                true/false: test_K_every_kind_of_token
    K5  a <hex string> (may be unterminated)    true/false: test_K_every_kind_of_token, test_K_unterminated_hex
    K6  [ ] or a stray delimiter                true/false: test_K_every_kind_of_token
    K7  a number (int or float) or a keyword    true/false: test_K_every_kind_of_token
_Lexer._literal()
    L1  no closing ")"                          true: test_L_unterminated             false: test_L_nested
    L2  "(" / ")" inside (nesting)              true: test_L_nested                   false: test_L_escapes
    L3  an octal escape, or another escape      true/false: test_L_escapes
_unhex(text)
    H1  an odd number of digits                 true: test_H_odd_digits               false: test_K_every_kind_of_token
_object(lexer)
    O1  nested deeper than MAX_DEPTH            true: test_X2_unreadable              false: test_O_references
    O2  an int followed by "g R"                true: test_O_references (Ref)         false: the same test (plain)
    O3  an array (ends at "]" or the end)       true: test_O_arrays                   false: test_O_references
    O4  a dictionary; a key; a key with no value  test_O_dictionaries
    O5  a keyword                               true: test_O_keywords                 false: test_O_references
_read_objects(data) and _stream(lexer, info)
    R1  a dictionary followed by "stream"       true: test_R1_stream_lengths          false: test_R2_later_object_wins
    R2  the line break after "stream"           \r\n, \n, \r: test_R1_stream_lengths
    R3  /Length is right                        true: test_R1_stream_lengths (first)  false: the same test (others)
    R4  "endstream" is missing                  true: test_R1_stream_lengths (last)   false: the others
_unpack_object_streams(objects)
    U1  an object stream with /First            true: test_U_object_streams           false: the same test (XRef)
    U2  each number and offset in the header    taken / skipped (not ints, or defined outside): test_U_object_streams
_resolve(objects, value)
    V1  a reference to a missing object or a loop                                     test_V_missing_and_looping
_decode(objects, stream)
    D1  each filter: Flate, ASCII-hex, ASCII-85, one not read here; none; a chain       test_D_filters
_inflate(data)
    I1  damaged data                            true: test_I_damaged                  false: test_D_filters
    I2  more than MAX_STREAM_BYTES              true: test_I_too_big                  false: test_D_filters
_un85(data)
    A1  "<~" at the start; not valid ASCII-85   test_D_filters, test_A_not_ascii85
_pages(objects) and _walk(...)
    P1  a page tree from the catalog            true: test_P_page_tree_order          false: test_P_no_catalog
    P2  a kid already seen, a kid that is not a page tree node, an inline kid          test_P_page_tree_order
    P3  deeper than MAX_DEPTH                   true: test_P_walk_stops_at_max_depth
_contents(objects, page)
    C1  one stream, or an array of them (skipping any that are not streams)            test_C_contents_array
_load_font(objects, info), _simple_font(...), _cid_widths(...), _cmap(data), _utf16(text), _glyph_text(name)
    F1  not a dictionary                        true: test_F_not_a_font               false: the font tests
    F2  a CID font, with and without descendants    test_F_cid_font, test_F_cid_font_without_descendants
    F3  a simple font: encodings, /Differences, /Widths, a Type 3 /FontMatrix          test_F_simple_fonts
    F4  each form of /W, and one not understood test_F_cid_font, test_F_cid_widths_not_understood
    F5  ToUnicode: bfchar, a bfrange with one target, with a list, with an empty target   test_F_cid_font
    F6  a one-byte target                       true: test_F_cid_font                 false: the same test
    F7  glyph names                             test_F_glyph_names
_paint(...): each instruction             q/Q/cm: test_T_save_restore_and_scale; BT Tf Td TD Tm T* ' " Tj:
                                          test_T_line_moves; TJ: test_T_tj_spacing; Tc Tw Tz Ts:
                                          test_T_char_word_space_scale_rise; Do: test_T_forms;
                                          BI: test_T_inline_images; a broken instruction: test_T_broken_instructions
_show(text, state, tm, pieces)
    S1  not bytes (raises TypeError)            true: test_T_broken_instructions      false: test_T_line_moves
    S2  only spaces, or size 0 (no piece)       true: test_T_nothing_to_show          false: test_T_line_moves
_lines(pieces) and _join(line)
    J1  the next piece is on a new line         true/false: test_X3_lines_cells_spaces
    J2  a gap wider than TAB_GAP, than SPACE_GAP, or none   test_X3_lines_cells_spaces, test_T_tj_spacing
"""

import hashlib
import unittest
import zlib
from base64 import a85encode
from pathlib import Path
from unittest import mock

from dealcalc import pdf_text
from dealcalc.pdf_text import Name, PdfError, Ref, Stream, extract_text
from tests.pdf_maker import make_pdf, page_pdf, stream

ROOT = Path(__file__).resolve().parent.parent
HELVETICA = {"Type": "Font", "Subtype": "Type1"}


def tokens(data: bytes) -> list:
    lexer, found = pdf_text._Lexer(data), []
    while (token := lexer.token())[0] != "eof":
        found.append(token)
    return found


def parse(data: bytes) -> object:
    return pdf_text._object(pdf_text._Lexer(data))


def paint(content: bytes, objects: dict | None = None, resources: dict | None = None) -> list:
    """The pieces of text a content stream draws, with Helvetica (500 wide) as /F1 unless objects say otherwise."""
    objects = {4: HELVETICA} if objects is None else objects
    resources = {"Font": {"F1": Ref(4)}} if resources is None else resources
    pieces = []
    pdf_text._paint(objects, content, resources, pdf_text._IDENTITY, pieces, 0)
    return pieces


def placed(pieces: list) -> list:
    """Each piece as (text, x, y, end, size), rounded."""
    return [(p.text, round(p.x, 2), round(p.y, 2), round(p.end, 2), round(p.size, 2)) for p in pieces]


class TestExtractText(unittest.TestCase):

    def test_X1_encrypted(self):
        with self.assertRaises(PdfError) as caught:
            extract_text(page_pdf(b"", trailer=b"/Root 1 0 R /Encrypt 9 0 R"))
        self.assertEqual(str(caught.exception), "encrypted")

    def test_X2_unreadable(self):
        too_deep = make_pdf({1: b"[" * 40 + b"]" * 40})
        with self.assertRaises(PdfError) as caught:
            extract_text(too_deep)
        self.assertEqual(str(caught.exception), "unreadable")

    def test_X3_lines_cells_spaces(self):
        content = (b"BT /F1 10 Tf 72 700 Td (Asking) Tj 37 0 Td (Price) Tj 100 0 Td ($1,200,000) Tj ET\n"
                   b"BT /F1 10 Tf 72 686 Td (Units) Tj 100 0 Td (12) Tj 10 0 Td (00) Tj ET")
        # "Asking" ends at 102 and "Price" starts at 109 (0.7 font sizes: a space); "Price" ends at 134 and the price
        # starts at 209 (7.5: a tab); "12" ends at 182, where "00" starts (no gap)
        self.assertEqual(extract_text(page_pdf(content)), "Asking Price\t$1,200,000\nUnits\t1200")

    def test_X3_compressed_and_not_a_pdf(self):
        content = b"BT /F1 12 Tf 72 700 Td (Vacancy Rate) Tj 200 0 Td (5%) Tj ET"
        self.assertEqual(extract_text(page_pdf(content, compress=True)), "Vacancy Rate\t5%")
        self.assertEqual(extract_text(b"plain text, no PDF objects"), "")

    def test_sample_pdfs(self):
        # real PDFs: Chrome draws each character on its own; macOS draws whole lines in a TrueType font
        maple = extract_text((ROOT / "samples" / "maple-court-listing.pdf").read_bytes()).splitlines()
        for line in ["Asking Price\t$1,200,000", "Total Monthly Rent\t$14,400", "Vacancy Rate\t5%",
                     "Total Operating Expenses (yearly)\t$62,000", "Maple Court Apartments"]:
            with self.subTest(line=line):
                self.assertIn(line, maple)
        oak = extract_text((ROOT / "samples" / "oak-grove-listing.pdf").read_bytes()).splitlines()
        for line in ["Oak Grove Apartments\tList Price: $1.35M", "Gross Scheduled Income (annual)\t$187,200",
                     "Less Vacancy (7%)\t($13,104)", "UNITS\tBUILT\tLOT\tPARKING", "12\t1985\t0.6 acres\t16 spaces"]:
            with self.subTest(line=line):
                self.assertIn(line, oak)
        quartz = extract_text((ROOT / "tests" / "reports" / "oak-grove-listing-quartz.pdf").read_bytes())
        self.assertIn("Gross Scheduled Income (annual)       $187,200", quartz)


class TestLexer(unittest.TestCase):

    def test_K_every_kind_of_token(self):
        data = b"% a comment\n/Name /A#20B / 12 -3.5 .5 (text) <48 49> << >> [ ] true R ) { >"
        self.assertEqual(tokens(data), [
            ("name", "Name"), ("name", "A B"), ("name", ""), ("num", 12), ("num", -3.5), ("num", 0.5),
            ("str", b"text"), ("str", b"HI"), ("<<", None), (">>", None), ("[", None), ("]", None),
            ("op", b"true"), ("op", b"R"), ("op", b")"), ("op", b"{"), ("op", b">"),
        ])
        self.assertIsInstance(tokens(b"/Font")[0][1], Name)
        self.assertEqual(pdf_text._Lexer(b"   ").token(), ("eof", None))

    def test_K_unterminated_hex(self):
        self.assertEqual(tokens(b"<4142"), [("str", b"AB")])

    def test_L_nested(self):
        self.assertEqual(tokens(b"(a(b)c) (d)"), [("str", b"a(b)c"), ("str", b"d")])

    def test_L_escapes(self):
        self.assertEqual(tokens(rb"(\101\n\(x\)\\\q\0053)"), [("str", b"A\n(x)\\q\x053")])
        self.assertEqual(tokens(b"(ab\\\ncd) (ef\\\r\ngh) (ij\\\rkl)"), [("str", b"abcd"), ("str", b"efgh"),
                                                                        ("str", b"ijkl")])

    def test_L_unterminated(self):
        self.assertEqual(tokens(b"(abc"), [("str", b"abc")])
        self.assertEqual(tokens(b"(ab\\"), [("str", b"ab")])

    def test_H_odd_digits(self):
        self.assertEqual(pdf_text._unhex(b"4 1 4"), b"A@")  # "414" is read as "4140"


class TestObjects(unittest.TestCase):

    def test_O_references(self):
        self.assertEqual(parse(b"12 0 R"), Ref(12))
        self.assertEqual(parse(b"12 0 obj"), 12)      # two numbers, then not "R"
        self.assertEqual(parse(b"12 /Name"), 12)      # one number
        self.assertEqual(parse(b"1.5 0 R"), 1.5)      # a reference number is never a float

    def test_O_arrays(self):
        self.assertEqual(parse(b"[1 2 0 R (x) [3]]"), [1, Ref(2), b"x", [3]])
        self.assertEqual(parse(b"[1 2"), [1, 2])      # no "]": the array ends at the end

    def test_O_dictionaries(self):
        self.assertEqual(parse(b"<< /A 1 /B [2] 5 /C (x) >>"), {"A": 1, "B": [2], "C": b"x"})  # 5 is not a key
        self.assertEqual(parse(b"<< /A >>"), {})       # a key with no value
        self.assertEqual(parse(b"<< /A 1"), {"A": 1})  # no ">>"

    def test_O_keywords(self):
        self.assertEqual([parse(word) for word in (b"true", b"false", b"null", b"endobj")],
                         [True, False, None, b"endobj"])
        self.assertIsNone(parse(b"]"))

    def test_R1_stream_lengths(self):
        cases = [
            (b"<< /Length 3 >> stream\r\nabc\r\nendstream", b"abc"),   # /Length right, \r\n after "stream"
            (b"<< /Length 99 >> stream\nabc\r\nendstream", b"abc"),    # /Length wrong: up to "endstream"
            (b"<< /Length 6 0 R >> stream\nabc\nendstream", b"abc"),   # /Length in another object
            (b"<< /Length 99 >> stream\rabc\rendstream", b"abc"),      # \r alone
        ]
        for body, raw in cases:
            with self.subTest(body=body):
                objects = pdf_text._read_objects(b"1 0 obj\n" + body + b"\nendobj\n2 0 obj (next) endobj")
                self.assertIsInstance(objects[1], Stream)
                self.assertEqual(objects[1].raw, raw)
                self.assertEqual(objects[2], b"next")  # reading carries on after the stream
        self.assertEqual(pdf_text._read_objects(b"1 0 obj << >> stream\nabc")[1].raw, b"abc")  # no "endstream"

    def test_R2_later_object_wins(self):
        objects = pdf_text._read_objects(b"1 0 obj << /A 1 >> endobj 2 0 obj (two) endobj 1 0 obj << /A 2 >> endobj")
        self.assertEqual(objects, {1: {"A": 2}, 2: b"two"})

    def test_U_object_streams(self):
        packed = b"(ten)  << /Type /Font >>"           # object 10 at offset 0, object 11 at offset 7
        header = b"10 0 11 7 12 1.5 1 0 "              # 12 has a float offset; 1 is also defined outside
        objects = pdf_text._read_objects(make_pdf({
            1: b"(outside)",
            2: stream(header + packed, b" /Type /ObjStm /N 4 /First %d" % len(header), compress=True),
            3: stream(b"10 0 (no)", b" /Type /XRef /First 5"),   # not an object stream
            4: stream(b"10 0 (no)", b" /Type /ObjStm"),          # no /First
        }))
        self.assertEqual(objects[10], b"ten")
        self.assertEqual(objects[11], {"Type": "Font"})
        self.assertEqual(objects[1], b"outside")
        self.assertNotIn(12, objects)

    def test_V_missing_and_looping(self):
        objects = {1: Ref(2), 2: Ref(1), 3: 7}
        self.assertIsNone(pdf_text._resolve(objects, Ref(9)))
        self.assertIsNone(pdf_text._resolve(objects, Ref(1)))
        self.assertEqual(pdf_text._resolve(objects, Ref(3)), 7)
        self.assertEqual(pdf_text._resolve(objects, "plain"), "plain")

    def test_D_filters(self):
        data = b"BT (hello) Tj ET"
        flate = zlib.compress(data)
        objects = {7: Name("FlateDecode")}
        cases = [
            (Stream({}, data), data),
            (Stream({"Filter": Name("FlateDecode")}, flate), data),
            (Stream({"Filter": Ref(7)}, flate), data),
            (Stream({"Filter": Name("AHx")}, flate.hex().encode() + b"> junk"), flate),
            (Stream({"Filter": [Name("ASCIIHexDecode"), Name("Fl")]}, flate.hex().encode() + b">"), data),
            (Stream({"Filter": Name("A85")}, b"<~" + a85encode(data) + b"~>"), data),
            (Stream({"Filter": Name("ASCII85Decode")}, a85encode(data) + b"~>"), data),
            (Stream({"Filter": Name("DCTDecode")}, b"\xff\xd8 a picture"), b""),
        ]
        for item, decoded in cases:
            with self.subTest(info=item.info):
                self.assertEqual(pdf_text._decode(objects, item), decoded)

    def test_A_not_ascii85(self):
        self.assertEqual(pdf_text._un85(b"<~abc{~>"), b"")

    def test_I_damaged(self):
        self.assertEqual(pdf_text._inflate(b"\x78\x9c\xff\xff\xff"), b"")  # an invalid block right away
        original = b"".join(hashlib.sha256(str(i).encode()).digest() for i in range(4000))  # 128,000 bytes
        damaged = bytearray(zlib.compress(original))
        damaged[-2] ^= 0xFF  # the checksum at the end is wrong, so only the last piece is lost
        inflated = pdf_text._inflate(bytes(damaged))
        self.assertTrue(original.startswith(inflated))
        self.assertGreater(len(inflated), 60_000)

    def test_I_too_big(self):
        with mock.patch.object(pdf_text, "MAX_STREAM_BYTES", 1_000):
            self.assertEqual(pdf_text._inflate(zlib.compress(b"a" * 5_000)), b"a" * 1_000)


class TestPages(unittest.TestCase):

    def test_P_page_tree_order(self):
        # the tree lists page 4 before page 3, repeats page 4, and has a kid that is not a node; the font is
        # inherited from the tree's root, and an inline page (a dictionary, not a reference) also counts
        text = extract_text(make_pdf({
            1: b"<< /Type /Catalog /Pages 2 0 R >>",
            2: b"<< /Type /Pages /Kids [4 0 R 3 0 R 4 0 R 9 0 R 7 << /Type /Page /Contents 6 0 R >>] "
               b"/Resources << /Font << /F1 8 0 R >> >> >>",
            3: b"<< /Type /Page /Contents 5 0 R >>",
            4: b"<< /Type /Page /Contents [6 0 R 9 0 R 5 0 R] >>",
            5: stream(b"BT /F1 10 Tf 72 700 Td (five) Tj ET"),
            6: stream(b"BT /F1 10 Tf 72 680 Td (six) Tj ET"),
            8: b"<< /Type /Font /Subtype /Type1 >>",
        }))
        self.assertEqual(text, "five\nsix\nfive\nsix")  # page 4 (streams 6 and 5), page 3, the inline page

    def test_P_no_catalog(self):
        # without a catalog, each page object counts, in object number order
        text = extract_text(make_pdf({
            9: b"<< /Type /Page /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
            3: b"<< /Type /Page /Resources << /Font << /F1 4 0 R >> >> /Contents 6 0 R >>",
            4: b"<< /Type /Font /Subtype /Type1 >>",
            5: stream(b"BT /F1 10 Tf 72 700 Td (nine) Tj ET"),
            6: stream(b"BT /F1 10 Tf 72 700 Td (three) Tj ET"),
            1: b"<< /Type /Catalog >>",  # a catalog with no page tree
        }))
        self.assertEqual(text, "three\nnine")

    def test_P_walk_stops_at_max_depth(self):
        objects = {n: {"Kids": [Ref(n + 1)]} for n in range(1, 50)}
        objects[50] = {"Type": "Page"}
        found = []
        pdf_text._walk(objects, objects[1], None, found, set(), 0)
        self.assertEqual(found, [])

    def test_C_contents_array(self):
        objects = {5: Stream({}, b"one"), 6: {"not": "a stream"}, 7: Stream({}, b"two")}
        self.assertEqual(pdf_text._contents(objects, {"Contents": [Ref(5), Ref(6), Ref(7)]}), b"one\ntwo")
        self.assertEqual(pdf_text._contents(objects, {"Contents": Ref(7)}), b"two")
        self.assertEqual(pdf_text._contents(objects, {}), b"")


class TestFonts(unittest.TestCase):

    CMAP = (b"1 begincodespacerange <0000> <FFFF> endcodespacerange\n"
            b"3 beginbfchar <0003> <0020> <0040> <24> <0041> <D83DDE00> endbfchar\n"
            b"3 beginbfrange <0024> <0026> <0041> <0030> <0031> [<0031> <0032>] <0050> <0051> <> endbfrange")

    def test_F_not_a_font(self):
        font = pdf_text._load_font({}, None)
        self.assertEqual((font.code_bytes, font.codec, font.chars, font.default_width), (1, "cp1252", {}, 500))

    def test_F_cid_font(self):
        objects = {
            5: {"Subtype": "CIDFontType2", "DW": 900, "W": [3, [250], 10, 12, 600]},
            6: Stream({}, self.CMAP),
        }
        font = pdf_text._load_font(objects, {"Subtype": "Type0", "DescendantFonts": [Ref(5)], "ToUnicode": Ref(6)})
        self.assertEqual(font.code_bytes, 2)
        self.assertEqual(font.default_width, 900)
        self.assertEqual(font.widths, {3: 250, 10: 600, 11: 600, 12: 600})
        self.assertEqual(font.chars, {3: " ", 0x40: "$", 0x41: "\U0001F600", 0x24: "A", 0x25: "B", 0x26: "C",
                                      0x30: "1", 0x31: "2", 0x50: "", 0x51: ""})
        self.assertEqual(font.codes(b"\x00\x24\x00\x03\x00"), [0x24, 3])  # a lone last byte is dropped
        self.assertEqual(font.char(0x24), "A")
        self.assertEqual(font.char(0x99), "")  # a two-byte code with no ToUnicode entry

    def test_F_cid_font_without_descendants(self):
        for descendants in (None, [], [Ref(9)]):
            with self.subTest(descendants=descendants):
                font = pdf_text._load_font({}, {"Subtype": "Type0", "DescendantFonts": descendants})
                self.assertEqual((font.code_bytes, font.default_width, font.widths), (2, 1000, {}))

    def test_F_cid_widths_not_understood(self):
        self.assertEqual(pdf_text._cid_widths({}, [5, b"x", 6, [300]]), {})
        self.assertEqual(pdf_text._cid_widths({}, [1, 2]), {})
        self.assertEqual(pdf_text._cid_widths({}, "not a list"), {})

    def test_F_simple_fonts(self):
        font = pdf_text._load_font({}, {
            "Subtype": "TrueType", "FirstChar": 65, "Widths": [600, b"x", 400],
            "Encoding": {"BaseEncoding": Name("MacRomanEncoding"),
                         "Differences": [65, Name("dollar"), Name("uni20AC"), 1, Name("f_i"), Name("zero.lf"),
                                         Name("g7"), Name("B"), b"junk"]},
        })
        self.assertEqual(font.codec, "mac_roman")
        self.assertEqual(font.chars, {65: "$", 66: "€", 1: "fi", 2: "0", 3: "", 4: "B"})
        self.assertEqual(font.widths, {65: 600, 66: 500, 67: 400})
        self.assertEqual(font.char(65), "$")
        self.assertEqual(font.char(0x8E), "é")  # MacRoman for a code /Differences does not list
        for encoding, codec in [(Name("WinAnsiEncoding"), "cp1252"), (Name("StandardEncoding"), "latin-1"),
                                (Name("Unknown"), "cp1252"), (None, "cp1252")]:
            with self.subTest(encoding=encoding):
                self.assertEqual(pdf_text._load_font({}, {"Subtype": "Type1", "Encoding": encoding}).codec, codec)
        type3 = pdf_text._load_font({}, {"Subtype": "Type3", "FontMatrix": [0.01, 0, 0, 0.01, 0, 0],
                                         "FirstChar": 0, "Widths": [50]})
        self.assertEqual(type3.widths, {0: 500})  # 50 units of 1/100 is half the font size
        odd = pdf_text._load_font({}, {"Subtype": "Type3", "FontMatrix": [b"x"], "FirstChar": 0, "Widths": [700]})
        self.assertEqual(odd.widths, {0: 700})

    def test_F_glyph_names(self):
        cases = {"dollar": "$", "A": "A", "uni20AC": "€", "u1F600": "\U0001F600", "f_i": "fi", "zero.lf": "0",
                 "g7": "", "uniZZZZ": "", "seven": "7"}
        for name, text in cases.items():
            with self.subTest(name=name):
                self.assertEqual(pdf_text._glyph_text(name), text)


class TestDrawing(unittest.TestCase):

    def test_T_line_moves(self):
        content = (b"BT /F1 10 Tf 14 TL 72 700 Td (one) Tj T* (two) Tj (three) ' 0 -14 TD (four) Tj T* (five) Tj "
                   b"1 0 0 1 72 600 Tm (six) Tj 2 3 (seven) \" ET")
        self.assertEqual([(p.text, p.y) for p in paint(content)],
                         [("one", 700), ("two", 686), ("three", 672), ("four", 658), ("five", 644), ("six", 600),
                          ("seven", 586)])

    def test_T_tj_spacing(self):
        content = (b"BT /F1 10 Tf 72 700 Td [(Asking) -600 (Price) -2000 ($1.2M)] TJ "
                   b"0 -20 Td [(1,2) 30 (00)] TJ ET")
        # -600 moves 6 (a space), -2000 moves 20 (a tab), and 30 moves back 0.3 (no gap)
        self.assertEqual(pdf_text._lines(paint(content)), ["Asking Price\t$1.2M", "1,200"])

    def test_T_char_word_space_scale_rise(self):
        cases = [
            (b"5 Tc (ab) Tj 20 0 Td (cd) Tj", "abcd"),     # each character 5 wider, so no gap
            (b"(ab) Tj 20 0 Td (cd) Tj", "ab cd"),         # without Tc: a gap of 1 font size, a space
            (b"5 Tw (a b) Tj 30 0 Td (c) Tj", "a b c"),    # the space character 5 wider: a gap of 1, a space
            (b"(a b) Tj 30 0 Td (c) Tj", "a b\tc"),        # without Tw: a gap of 1.5, a tab
            (b"50 Tz (abcd) Tj 20 0 Td (e) Tj", "abcd e"),  # half as wide: a gap of 1, a space
        ]
        for content, text in cases:
            with self.subTest(content=content):
                pieces = paint(b"BT /F1 10 Tf 72 700 Td " + content + b" ET")
                self.assertEqual(pdf_text._lines(pieces), [text])
        risen = paint(b"BT /F1 10 Tf 72 700 Td (base) Tj 10 Ts (up) Tj ET")
        self.assertEqual(pdf_text._lines(risen), ["up", "base"])

    def test_T_save_restore_and_scale(self):
        content = (b"Q q 2 0 0 2 0 0 cm BT /F1 10 Tf 36 350 Td (big) Tj ET Q "
                   b"BT /F1 10 Tf q /F1 30 Tf Q 72 680 Td (small) Tj /F1 10 Tf (again) Tj ET")
        self.assertEqual(placed(paint(content)), [("big", 72, 700, 102, 20), ("small", 72, 680, 97, 10),
                                                  ("again", 97, 680, 122, 10)])

    def test_T_forms(self):
        form = Stream({"Subtype": "Form", "Matrix": [1, 0, 0, 1, 100, 0]}, b"BT /F1 10 Tf 0 0 Td (inform) Tj ET")
        plain = Stream({"Subtype": "Form"}, b"BT /F2 10 Tf 0 0 Td (plain) Tj ET")
        inner = {"Font": {"F2": Ref(4)}, "XObject": {"Fm2": Ref(8)}}
        objects = {4: HELVETICA, 6: form, 7: Stream({"Subtype": "Image"}, b"pixels"), 8: plain,
                   9: Stream({"Subtype": "Form", "Resources": inner}, b"/Fm2 Do")}
        resources = {"Font": {"F1": Ref(4)}, "XObject": {"Fm1": Ref(6), "Im1": Ref(7), "Fm3": Ref(9)}}
        pieces = paint(b"q 1 0 0 1 0 500 cm /Fm1 Do Q /Im1 Do /Missing Do /Fm3 Do", objects, resources)
        # Fm1 is moved by its matrix and the page's; Fm2 has no resources, so it uses those of Fm3, which draws it
        self.assertEqual(placed(pieces), [("inform", 100, 500, 130, 10), ("plain", 0, 0, 25, 10)])

    def test_T_forms_stop_at_max_depth(self):
        itself = Stream({"Subtype": "Form", "Resources": {"Font": {"F1": Ref(4)}, "XObject": {"Me": Ref(6)}}},
                        b"BT /F1 10 Tf (x) Tj ET /Me Do")
        pieces = paint(b"/Me Do", {4: HELVETICA, 6: itself}, {"XObject": {"Me": Ref(6)}})
        self.assertEqual(len(pieces), pdf_text.MAX_DEPTH)

    def test_T_inline_images(self):
        content = b"BI /W 2 /H 1 /BPC 8 ID \x00\xff) Tj (fake EI BT /F1 10 Tf 72 700 Td (after) Tj ET"
        self.assertEqual([p.text for p in paint(content)], ["after"])
        self.assertEqual(paint(b"BT /F1 10 Tf (x) Tj ET BI /W 2"), paint(b"BT /F1 10 Tf (x) Tj ET"))  # no ID
        self.assertEqual([p.text for p in paint(b"BT /F1 10 Tf (x) Tj BI ID \x00 (y) Tj")], ["x"])  # no EI

    def test_T_broken_instructions(self):
        content = (b"BT /F1 10 Tf 72 700 Td /Oops Td (ok) Tj /Name Tj 12 Tf [(a) /N (b)] TJ 1 2 3 Tm "
                   b"/Unknown 10 Tf (default) Tj ET")
        # each broken instruction is skipped; an unknown font name draws with a plain font
        self.assertEqual([p.text for p in paint(content)], ["ok", "a", "default"])

    def test_T_nothing_to_show(self):
        self.assertEqual(paint(b"BT /F1 10 Tf 72 700 Td ( ) Tj /F1 0 Tf (zero) Tj ET"), [])
        self.assertEqual(paint(b"(no font) Tj"), [])  # size 0 until Tf sets one


if __name__ == "__main__":
    unittest.main()
