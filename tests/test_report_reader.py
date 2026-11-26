"""White-box tests for the Report Reader (dealcalc/report_reader.py; not yet in the SDS: see "Property reports" in
ARCHITECTURE.md).

The tests are written from the code: each branch below is taken both ways by at least one test, named in the
right-hand column. python tests/line_coverage.py confirms that every line runs.

read_report(data)
    D1  a PDF                                   true: test_D1_pdf                     false: test_D4_text_encodings
    D2  PDF Text cannot read it                 true: test_D1_pdf_problems            false: test_D1_pdf
    D3  a zip file                              true: test_D3_word_file               false: test_D4_text_encodings
    D4  the zip is damaged                      true: test_D3_damaged_word_files      false: test_D3_word_file
    D5  the zip is not a Word file              true: test_D3_not_a_word_file         false: test_D3_word_file
    D6  other binary data (a picture)           true: test_D6_picture                 false: test_D4_text_encodings
    D7  no text                                 true: test_D7_no_text, test_D1_pdf_problems   false: test_D1_pdf
_word_lines(element, lines) and _word_paragraph(paragraph)
    W1  a paragraph, a table row, or a container to look inside                       test_D3_word_file
    W2  a run of text (empty or not), a tab, a line break, or something else           test_D3_word_file
_plain_text(data)
    E1  UTF-16; UTF-8 (with or without a byte order mark); Windows-1252               test_D4_text_encodings
read_text(text)
    T1  the input was already found             true: test_T1_first_search_wins       false: test_T_each_conversion
    T2  a search finds nothing                  true: test_T2_nothing_found           false: test_T_each_conversion
    T3  an average rent: units found or not     test_T_each_conversion, test_T3_average_rent_needs_units
    T4  how is "input" (nothing worked out)     true: test_T1_first_search_wins       false: test_T_each_conversion
_period(field, how, context)
    M1  a "yearly" rent given for a month       true: test_M_monthly_amounts          false: test_T_each_conversion
    M2  operating costs given for a month       true: test_T_each_conversion          false: test_T1_first_search_wins
_find(...) and _number_for(...)
    N1  a blocked word just before the label    true: test_N1_blocked_words           false: test_T1_first_search_wins
    N2  a percent just before its label         true: test_T_each_conversion (95% occupied)   false: the others
    N3  the number in the label's cell          true: test_T1_first_search_wins       false: test_N4_next_cell
    N4  the rest of the cell has the wrong words  true: test_N1_price_per_unit        false: test_N4_next_cell
    N5  the number in the next cell             true: test_N4_next_cell               false: test_N5_cell_below
    N6  the number in the cell below            true: test_N5_cell_below              false: test_N6_no_number
_number_after(cell, label_end, want)
    A1  no number after the label               true: test_N4_next_cell               false: test_T1_first_search_wins
    A2  the gap is too long, too wordy, or has the wrong words   true: test_A2_gaps   false: test_T1_...
    A3  a second number after one of another kind; words between them   test_A3_two_numbers
_heads_one_value(rows, i, j, want)
    H1  no next row, or one with a different number of cells     true: test_H1_no_row_below
    H2  the column carries on (a table such as a rent roll)      true: test_H2_rent_roll   false: test_N5_cell_below
_value(number, want)
    V1  percents, counts, and money, each wanted or not          test_V_kinds_of_numbers
_unit_count(rows)
    U1  from a label; from a phrase; out of range; none          test_U_unit_counts
"""

import io
import unittest
import zipfile
from pathlib import Path

from dealcalc import report_reader
from dealcalc.number_format import format_input
from dealcalc.report_reader import Reading, read_report, read_text
from dealcalc.teaching_content import SAMPLE_DEALS
from tests.pdf_maker import make_pdf, page_pdf, text_pdf, word_file

ROOT = Path(__file__).resolve().parent.parent
WORD_NAMESPACE = 'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"'


def values(text: str) -> dict:
    return read_text(text).values


class TestFiles(unittest.TestCase):

    def test_D1_pdf(self):
        reading = read_report(text_pdf("Asking Price\t$1,200,000", "Total Monthly Rent\t$14,400",
                                       "Vacancy Rate\t5%", "Total Expenses\t$62,000"))
        self.assertEqual(reading, Reading(
            values={"price": 1_200_000, "monthly_rent": 14_400, "vacancy_pct": 5, "operating_costs": 62_000},
            sources={"price": "Asking Price $1,200,000", "monthly_rent": "Total Monthly Rent $14,400",
                     "vacancy_pct": "Vacancy Rate 5%", "operating_costs": "Total Expenses $62,000"},
            worked={}))

    def test_D1_pdf_problems(self):
        self.assertEqual(read_report(page_pdf(b"", trailer=b"/Root 1 0 R /Encrypt 9 0 R")).problem, "encrypted")
        self.assertEqual(read_report(make_pdf({1: b"[" * 40})).problem, "unreadable")
        self.assertEqual(read_report(page_pdf(b"")).problem, "no_text")  # a page with no text, as in a scan

    def test_D3_word_file(self):
        document = (f'<w:document {WORD_NAMESPACE}><w:body>'
                    '<w:p><w:r><w:t>Oak Grove</w:t></w:r><w:r><w:t/></w:r><w:r><w:br/></w:r>'
                    '<w:r><w:t>12 units</w:t></w:r><w:proofErr/></w:p>'
                    '<w:p><w:r><w:t>List Price:</w:t><w:tab/><w:t>$1.35M</w:t></w:r></w:p>'
                    '<w:tbl><w:tr><w:trPr/><w:tc><w:p><w:r><w:t>Gross Scheduled Income</w:t></w:r></w:p></w:tc>'
                    '<w:tc><w:p><w:r><w:t>$187,200</w:t></w:r></w:p></w:tc></w:tr></w:tbl>'
                    '<w:sdt><w:sdtContent><w:p><w:r><w:t>Vacancy: 7%</w:t></w:r></w:p></w:sdtContent></w:sdt>'
                    '</w:body></w:document>')
        data = word_file(document)
        self.assertEqual(report_reader._word_text(data),
                         "Oak Grove\n12 units\nList Price:\t$1.35M\nGross Scheduled Income\t$187,200\nVacancy: 7%")
        reading = read_report(data)
        self.assertEqual(reading.values, {"price": 1_350_000, "monthly_rent": 15_600, "vacancy_pct": 7})
        self.assertEqual(reading.worked, {"monthly_rent": ("yearly_rent", 187_200, None)})

    def test_D3_damaged_word_files(self):
        self.assertEqual(read_report(b"PK\x03\x04 not really a zip file").problem, "unreadable")
        self.assertEqual(read_report(word_file("<w:document")).problem, "unreadable")  # not valid XML

    def test_D3_not_a_word_file(self):
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w") as archive:
            archive.writestr("xl/workbook.xml", "<workbook/>")  # an Excel file
        self.assertEqual(read_report(buffer.getvalue()).problem, "not_supported")

    def test_D4_text_encodings(self):
        text = "Asking Price: $1,200,000 – firm"
        for data in (text.encode("utf-8"), text.encode("utf-8-sig"), text.encode("utf-16"),
                     text.encode("cp1252")):
            with self.subTest(data=data[:6]):
                self.assertEqual(read_report(data).values, {"price": 1_200_000})

    def test_D6_picture(self):
        self.assertEqual(read_report(b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR").problem, "not_supported")

    def test_D7_no_text(self):
        for data in (b"", b"  \n\t "):
            with self.subTest(data=data):
                self.assertEqual(read_report(data), Reading(problem="no_text"))


class TestSampleReports(unittest.TestCase):
    """Real reports: the samples members can try (made by Chrome) and the same listings made by macOS and Word."""

    def read(self, *path):
        return read_report(ROOT.joinpath(*path).read_bytes())

    def test_maple_court_gives_sample_deal_a(self):
        for path in (("samples", "maple-court-listing.pdf"), ("tests", "reports", "maple-court-listing.docx")):
            with self.subTest(path=path[-1]):
                reading = self.read(*path)
                self.assertEqual({f: format_input(v) for f, v in reading.values.items()}, SAMPLE_DEALS["A"])
                self.assertEqual(reading.worked, {})
                self.assertEqual(reading.sources["operating_costs"], "Total Operating Expenses (yearly) $62,000")

    def test_oak_grove_gives_sample_deal_b(self):
        for path in (("samples", "oak-grove-listing.pdf"), ("tests", "reports", "oak-grove-listing-quartz.pdf")):
            with self.subTest(path=path[-1]):
                reading = self.read(*path)
                self.assertEqual({f: format_input(v) for f, v in reading.values.items()}, SAMPLE_DEALS["B"])
                self.assertEqual(reading.worked, {"monthly_rent": ("yearly_rent", 187_200, None)})
                self.assertEqual(reading.sources["price"], "List Price: $1.35M")  # not "Price per Unit"


class TestFindingInputs(unittest.TestCase):

    def test_T_each_conversion(self):
        reading = read_text("Listing: 6-unit building\nAsking price: $640,000\nAverage rent: $1,150 per month\n"
                            "95% occupied\nMonthly expenses: $3,000")
        self.assertEqual(reading.values, {"price": 640_000, "monthly_rent": 6_900, "vacancy_pct": 5,
                                          "operating_costs": 36_000})
        self.assertEqual(reading.worked, {"monthly_rent": ("average_rent", 1_150, 6),
                                          "vacancy_pct": ("occupancy", 95, None),
                                          "operating_costs": ("monthly_costs", 3_000, None)})
        self.assertEqual(reading.sources["vacancy_pct"], "95% occupied")

    def test_T1_first_search_wins(self):
        # a total monthly rent is used as it is, even when a yearly one is also given
        reading = read_text("Total Monthly Rent: $14,400\nGross Potential Rent: $999,999\nVacancy: 5%\n"
                            "Vacancy: 9%\nOperating Expenses: $62,000")
        self.assertEqual(reading.values, {"monthly_rent": 14_400, "vacancy_pct": 5, "operating_costs": 62_000})
        self.assertEqual(reading.worked, {})

    def test_T2_nothing_found(self):
        self.assertEqual(read_text("A lovely building near campus.\nCall for details."), Reading())

    def test_T3_average_rent_needs_units(self):
        self.assertEqual(values("Average Rent: $1,200"), {})
        self.assertEqual(values("UNITS\tBUILT\n12\t1985\nAverage Rent\t$1,200"), {"monthly_rent": 14_400})

    def test_M_monthly_amounts(self):
        # "Gross Income" is usually yearly, but not when the report says it is monthly
        reading = read_text("Gross Income: $14,400/mo\nTotal Expenses: $62,000 per year")
        self.assertEqual(reading.values, {"monthly_rent": 14_400, "operating_costs": 62_000})
        self.assertEqual(reading.worked, {})
        self.assertEqual(values("Gross Rental Income (annual): $172,800"), {"monthly_rent": 14_400})

    def test_N1_blocked_words(self):
        self.assertEqual(values("Last Sold Price: $800,000\nAsking Price: $1,200,000"), {"price": 1_200_000})
        self.assertEqual(values("Effective Gross Income\t$174,096\nGross Scheduled Income\t$187,200"),
                         {"monthly_rent": 15_600})
        self.assertEqual(values("Average Monthly Rent: $1,200\n12 units"), {"monthly_rent": 14_400})
        self.assertEqual(values("Capital Expenses: $50,000\nTotal Expenses: $62,000"), {"operating_costs": 62_000})

    def test_N1_price_per_unit(self):
        self.assertEqual(values("Price per Unit\t$112,500\nList Price: $1.35M"), {"price": 1_350_000})
        self.assertEqual(values("Price/Unit: $112,500"), {})
        self.assertEqual(values("Monthly Rent per Unit: $1,200"), {})

    def test_N4_next_cell(self):
        self.assertEqual(values("Total Expenses\t($70,000)\nVacancy Rate  5%"),  # two spaces also start a cell
                         {"operating_costs": 70_000, "vacancy_pct": 5})

    def test_N5_cell_below(self):
        self.assertEqual(values("Asking Price\n$1,200,000\nVacancy\n5%"), {"price": 1_200_000, "vacancy_pct": 5})

    def test_N6_no_number(self):
        self.assertEqual(values("Vacancy: $13,104 lost, 7%"), {})  # the percent is about something else
        self.assertEqual(values("Vacancy\t$13,104"), {})          # the next cell is not a percent
        self.assertEqual(values("Price: call\tUnits"), {})        # the next cell is not a number

    def test_A2_gaps(self):
        cases = ["The asking price reflects recent upgrades costing $45,000.",  # too many words
                 "Price " + "-" * 45 + " $1,200,000",                            # too long
                 "Price Reduced: $50,000",                                       # a different number
                 "Gross Income (pro forma): $200,000",
                 "Expense Ratio 35%"]
        for text in cases:
            with self.subTest(text=text):
                self.assertEqual(values(text), {})

    def test_A3_two_numbers(self):
        # one number of another kind may come first, but not when words come between the two
        self.assertEqual(values("Total Expenses (35%) $62,000"), {"operating_costs": 62_000})
        self.assertEqual(values("Less Vacancy ($13,104) (7%)"), {"vacancy_pct": 7})
        self.assertEqual(values("Total Expenses 35% of income, $62,000"), {})

    def test_H1_no_row_below(self):
        self.assertEqual(values("Asking Price"), {})
        self.assertEqual(values("Asking Price\tUnits\n$1,200,000"), {})  # the next row has fewer cells

    def test_H2_rent_roll(self):
        # "Monthly Rent" heads a column of several rents, so no one number is the monthly rent
        self.assertEqual(values("Unit\tMonthly Rent\n1\t$1,200\n2\t$1,250\nTotal\t$2,450"), {})
        self.assertEqual(values("Unit\tMonthly Rent\n1\t$1,200"), {"monthly_rent": 1_200})  # one row: its value

    def test_tidy_characters(self):
        self.assertEqual(values("Asking Price: $1,200,000\nTotal Expenses: −$62,000"),
                         {"price": 1_200_000, "operating_costs": 62_000})


class TestNumbers(unittest.TestCase):

    def value(self, text, want):
        return report_reader._value(report_reader._NUMBER.search(text), want)

    def test_V_kinds_of_numbers(self):
        cases = [
            ("5%", "percent", 5), ("7.5 percent", "percent", 7.5), ("5", "percent", None), ("5%", "money", None),
            ("12", "count", 12), ("12.5", "count", None), ("$12", "count", None), ("0", "count", None),
            ("20000", "count", None), ("10000", "count", 10_000),
            ("$500", "money", 500), ("1,200", "money", 1_200), ("1200000", "money", 1_200_000),
            ("12", "money", None), ("2.5 million", "money", 2_500_000), ("$850K", "money", 850_000),
            ("$1.35M", "money", 1_350_000), ("$1.2MM", "money", 1_200_000), ("850K", "money", None),
            ("($62,000)", "money", 62_000), ("-$4,500", "money", 4_500), ("75 thousand", "money", 75_000),
        ]
        for text, want, expected in cases:
            with self.subTest(text=text, want=want):
                self.assertEqual(self.value(text, want), expected)

    def test_U_unit_counts(self):
        cases = [("Number of Units: 12", 12), ("Units: 12.5", None), ("# of Units: 24", 24), ("the 8 units", 8),
                 ("a 20000-unit complex", None), ("Units: 0\n4-unit", 4), ("No units listed", None)]
        for text, units in cases:
            with self.subTest(text=text):
                self.assertEqual(report_reader._unit_count(report_reader._rows(text)), units)


if __name__ == "__main__":
    unittest.main()
