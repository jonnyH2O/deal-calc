"""White-box tests for the Input Checker (dealcalc/input_checker.py; SDS 4.2; R1, R2, R3).

The tests are written from the code: each branch below is taken both ways by at least one test, named in the
right-hand column. python tests/line_coverage.py confirms that every line runs.

parse_number(text)
    P1  text ends with "%"                    true: test_P1_trailing_percent        false: test_P2_leading_dollar
    P2  text starts with "$"                  true: test_P2_leading_dollar          false: test_P1_trailing_percent
    P3  else text starts with "-$"            true: test_P3_minus_then_dollar       false: test_P1_trailing_percent
    P4  float() raises ValueError             true: test_P4_not_a_number            false: test_P2_leading_dollar
    P5  the number is finite                  true: test_P2_leading_dollar          false: test_P5_nan_and_inf
valid_range(field)
    V1  field is a percent                    true: test_V1_V2_ranges (vacancy)     false: test_V1_V2_ranges (price)
    V2  field's lowest value is excluded      true: test_V1_V2_ranges (price)       false: test_V1_V2_ranges (rent)
check_inputs(raw)
    C1  input missing or blank                true: test_C1_missing_or_blank        false: test_C5_all_valid
    C2  input is not a number                 true: test_C2_not_a_number            false: test_C5_all_valid
    C3  input below its lowest value          true: test_C3_below_lowest            false: test_C5_all_valid
        (price: at or below 0; others: below 0)
    C4  input above its highest value         true: test_C4_above_highest           false: test_C5_all_valid
    C5  any errors after the loop             true: test_C6_every_error_at_once     false: test_C5_all_valid
find_warnings(deal, results)
    W1  vacancy above 25%                     true: test_W1_vacancy_above_25        false: test_W_sample_deal
    W2  NOI negative (returns early)          true: test_W2_negative_noi            false: test_W_sample_deal
    W3  cap rate below 2%                     true: test_W3_cap_rate_below_2        false: test_W_sample_deal
    W4  else cap rate above 15%               true: test_W4_cap_rate_above_15       false: test_W_sample_deal

Boundary values are tested on both sides of every comparison (<, <=, >).
"""

import unittest

from dealcalc.deal_math import Deal, Results
from dealcalc.input_checker import LABELS, check_inputs, find_warnings, parse_number, valid_range
from dealcalc.teaching_content import SAMPLE_DEALS

SAMPLE_A = SAMPLE_DEALS["A"]


def with_field(field, text):
    """Sample deal A with one input changed."""
    return {**SAMPLE_A, field: text}


class TestParseNumber(unittest.TestCase):

    def test_P1_trailing_percent(self):
        self.assertEqual(parse_number("5%"), 5)
        self.assertEqual(parse_number("7.5 %"), 7.5)
        self.assertEqual(parse_number("5"), 5)  # P1 false, P2 false, P3 false

    def test_P2_leading_dollar(self):
        self.assertEqual(parse_number("$1,200,000"), 1_200_000)
        self.assertEqual(parse_number(" $ 14,400 "), 14_400)  # spaces anywhere are removed first
        self.assertEqual(parse_number("$-5"), -5)

    def test_P3_minus_then_dollar(self):
        self.assertEqual(parse_number("-$4,500"), -4_500)
        self.assertEqual(parse_number("−$4,500"), -4_500)  # the minus sign "−" is read as "-"

    def test_P4_not_a_number(self):
        for text in ["", "   ", "$", "%", "-$", "abc", "12abc", "1.2.3", "$$5", "5%%", "--5"]:
            with self.subTest(text=text):
                self.assertIsNone(parse_number(text))

    def test_P5_nan_and_inf(self):
        for text in ["nan", "inf", "-inf", "1e999"]:
            with self.subTest(text=text):
                self.assertIsNone(parse_number(text))


class TestValidRange(unittest.TestCase):

    def test_V1_V2_ranges(self):
        self.assertEqual(valid_range("vacancy_pct"), "from 0% to 100%")              # V1 true, V2 false
        self.assertEqual(valid_range("price"), "more than $0, up to $100,000,000")   # V1 false, V2 true
        self.assertEqual(valid_range("monthly_rent"), "from $0 to $10,000,000")      # V1 false, V2 false


class TestCheckInputs(unittest.TestCase):

    def test_C1_missing_or_blank(self):
        missing = {k: v for k, v in SAMPLE_A.items() if k != "price"}
        for raw in (missing, with_field("price", ""), with_field("price", "   ")):
            with self.subTest(raw=raw):
                deal, errors = check_inputs(raw)
                self.assertIsNone(deal)
                self.assertEqual(errors, {"price": "Enter the purchase price: more than $0, up to $100,000,000."})

    def test_C2_not_a_number(self):
        deal, errors = check_inputs(with_field("monthly_rent", "lots"))
        self.assertIsNone(deal)
        self.assertEqual(errors, {"monthly_rent": "The monthly rent must be a number: from $0 to $10,000,000."})

    def test_C3_below_lowest(self):
        # price excludes its lowest value: 0 is too low, 0.01 is not; the others allow 0
        cases = [("price", "0", True), ("price", "0.01", False), ("price", "-1", True),
                 ("monthly_rent", "0", False), ("monthly_rent", "-0.01", True),
                 ("vacancy_pct", "0", False), ("vacancy_pct", "-0.1", True),
                 ("operating_costs", "0", False), ("operating_costs", "-1", True)]
        for field, text, too_low in cases:
            with self.subTest(field=field, text=text):
                _, errors = check_inputs(with_field(field, text))
                self.assertEqual(field in errors, too_low)
                if too_low:
                    self.assertEqual(errors[field], f"Out of range: the {LABELS[field]} must be {valid_range(field)}.")

    def test_C4_above_highest(self):
        cases = [("price", "100,000,000", False), ("price", "100,000,000.01", True),
                 ("monthly_rent", "10,000,000", False), ("monthly_rent", "10,000,001", True),
                 ("vacancy_pct", "100%", False), ("vacancy_pct", "100.1", True),
                 ("operating_costs", "100,000,000", False), ("operating_costs", "100,000,001", True)]
        for field, text, too_high in cases:
            with self.subTest(field=field, text=text):
                _, errors = check_inputs(with_field(field, text))
                self.assertEqual(field in errors, too_high)

    def test_C5_all_valid(self):
        deal, errors = check_inputs(SAMPLE_A)
        self.assertEqual(errors, {})
        self.assertEqual(deal, Deal(price=1_200_000, monthly_rent=14_400, vacancy_pct=5, operating_costs=62_000))

    def test_C5_extra_fields_and_numbers_instead_of_text(self):
        # fields other than the four inputs are ignored, and numbers are read through str()
        deal, errors = check_inputs({"price": 1_200_000, "monthly_rent": 14_400, "vacancy_pct": 5,
                                     "operating_costs": 62_000, "name": "Meeting listing"})
        self.assertEqual(errors, {})
        self.assertEqual(deal.price, 1_200_000)

    def test_C6_every_error_at_once(self):
        # one input takes each error path, so the loop keeps going after each error
        deal, errors = check_inputs({"price": "", "monthly_rent": "x", "vacancy_pct": "150", "operating_costs": "-3"})
        self.assertIsNone(deal)
        self.assertEqual(errors, {
            "price": "Enter the purchase price: more than $0, up to $100,000,000.",
            "monthly_rent": "The monthly rent must be a number: from $0 to $10,000,000.",
            "vacancy_pct": "Out of range: the vacancy rate must be from 0% to 100%.",
            "operating_costs": "Out of range: the yearly operating costs must be from $0 to $100,000,000.",
        })


class TestFindWarnings(unittest.TestCase):

    def deal(self, vacancy_pct=5):
        return Deal(price=1_200_000, monthly_rent=14_400, vacancy_pct=vacancy_pct, operating_costs=62_000)

    def results(self, noi=102_160, cap_rate_pct=8.51):
        return Results(gpr=172_800, egi=164_160, noi=noi, cap_rate_pct=cap_rate_pct)

    def test_W_sample_deal(self):
        self.assertEqual(find_warnings(self.deal(), self.results()), {})  # W1 to W4 all false

    def test_W1_vacancy_above_25(self):
        self.assertEqual(find_warnings(self.deal(vacancy_pct=25), self.results()), {})
        self.assertEqual(set(find_warnings(self.deal(vacancy_pct=25.1), self.results())), {"vacancy_pct"})

    def test_W2_negative_noi(self):
        warnings = find_warnings(self.deal(), self.results(noi=-4_500, cap_rate_pct=-0.38))
        self.assertEqual(set(warnings), {"noi"})  # returns early: no cap rate warning
        self.assertIn("negative", warnings["noi"])
        # zero NOI is not negative, so it falls through to the cap rate check
        self.assertEqual(set(find_warnings(self.deal(), self.results(noi=0, cap_rate_pct=0))), {"cap_rate_pct"})

    def test_W1_and_W2_together(self):
        # the early return in W2 must not drop the vacancy warning found before it
        warnings = find_warnings(self.deal(vacancy_pct=40), self.results(noi=-4_500, cap_rate_pct=-0.38))
        self.assertEqual(set(warnings), {"vacancy_pct", "noi"})

    def test_W3_cap_rate_below_2(self):
        self.assertNotIn("cap_rate_pct", find_warnings(self.deal(), self.results(cap_rate_pct=2)))
        warnings = find_warnings(self.deal(), self.results(cap_rate_pct=1.99))
        self.assertIn("below 2%", warnings["cap_rate_pct"])

    def test_W4_cap_rate_above_15(self):
        self.assertNotIn("cap_rate_pct", find_warnings(self.deal(), self.results(cap_rate_pct=15)))
        warnings = find_warnings(self.deal(), self.results(cap_rate_pct=15.01))
        self.assertIn("above 15%", warnings["cap_rate_pct"])


if __name__ == "__main__":
    unittest.main()
