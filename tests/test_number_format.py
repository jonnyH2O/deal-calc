"""White-box tests for the Number Formatter (dealcalc/number_format.py; SDS 4.3; SRS Section 3.1 formats).

The tests are written from the code: each branch below is taken both ways by at least one test, named in the
right-hand column. python tests/line_coverage.py confirms that every line runs.

_rounded(x, places)  (no branches; rounding is tested at the halfway points, where the method matters)
    R   rounds half away from zero, using repr(x)     test_R_halfway_values_round_away_from_zero,
                                                      test_R_uses_the_number_as_printed
_sign(value, plus)
    S1  value < 0                       true: test_S1_negative          false: test_S2_positive_with_plus
    S2  value > 0 and plus              true: test_S2_positive_with_plus
                                        false (value > 0, plus false): test_S2_positive_without_plus
                                        false (value is 0, plus true): test_S2_zero_gets_no_sign
format_delta(field, x)
    D1  field is a rate field           true: test_D1_rate_fields       false: test_D1_dollar_fields

format_money, format_percent, and _money have no branches of their own; they are covered by the tests above.
"""

import unittest

from dealcalc.number_format import MINUS, format_delta, format_money, format_percent


class TestRounding(unittest.TestCase):

    def test_R_halfway_values_round_away_from_zero(self):
        # Python's round() would give $0 and $2 here ("banker's rounding"); people expect $1 and $3
        self.assertEqual(format_money(0.5), "$1")
        self.assertEqual(format_money(2.5), "$3")
        self.assertEqual(format_money(-0.5), f"{MINUS}$1")
        self.assertEqual(format_money(102_159.49), "$102,159")
        self.assertEqual(format_money(102_159.5), "$102,160")
        self.assertEqual(format_percent(0.125), "0.13%")

    def test_R_uses_the_number_as_printed(self):
        # 8.515 and 1.005 are stored as slightly less in a float; they still round up, as they look
        self.assertEqual(format_percent(8.515), "8.52%")
        self.assertEqual(format_percent(1.005), "1.01%")
        self.assertEqual(format_percent(8.514999), "8.51%")


class TestSign(unittest.TestCase):

    def test_S1_negative(self):
        self.assertEqual(format_money(-4_500), f"{MINUS}$4,500")
        self.assertEqual(format_percent(-0.375), f"{MINUS}0.38%")
        self.assertEqual(format_delta("noi", -1_936), f"{MINUS}$1,936")
        self.assertEqual(format_delta("cap_rate_pct", -0.8), f"{MINUS}0.80 points")

    def test_S2_positive_with_plus(self):
        self.assertEqual(format_delta("noi", 1_936), "+$1,936")
        self.assertEqual(format_delta("vacancy_pct", 2), "+2.00 points")

    def test_S2_positive_without_plus(self):
        self.assertEqual(format_money(102_160), "$102,160")
        self.assertEqual(format_percent(8.513), "8.51%")

    def test_S2_zero_gets_no_sign(self):
        # zero, and numbers that round to zero, get no sign even where a "+" or "−" would otherwise go
        for x in (0, 0.4, -0.4, -0.0):
            with self.subTest(x=x):
                self.assertEqual(format_money(x), "$0")
                self.assertEqual(format_delta("price", x), "$0")
        for x in (0, 0.004, -0.004):
            with self.subTest(x=x):
                self.assertEqual(format_percent(x), "0.00%")
                self.assertEqual(format_delta("cap_rate_pct", x), "0.00 points")


class TestFormatDelta(unittest.TestCase):

    def test_D1_rate_fields(self):
        self.assertEqual(format_delta("vacancy_pct", 2), "+2.00 points")
        self.assertEqual(format_delta("cap_rate_pct", 7.71 - 8.51), f"{MINUS}0.80 points")

    def test_D1_dollar_fields(self):
        for field in ("price", "monthly_rent", "operating_costs", "gpr", "egi", "noi"):
            with self.subTest(field=field):
                self.assertEqual(format_delta(field, 14_400), "+$14,400")


class TestSrsExamples(unittest.TestCase):
    """Every example in SRS Section 3.1 and the sample deals in R5 and R9."""

    def test_srs_section_3_1_examples(self):
        self.assertEqual(format_money(102_160), "$102,160")
        self.assertEqual(format_money(-4_500), f"{MINUS}$4,500")
        self.assertEqual(format_percent(102_160 / 1_200_000 * 100), "8.51%")
        self.assertEqual(format_delta("noi", 1_936), "+$1,936")
        self.assertEqual(format_delta("cap_rate_pct", -0.80), f"{MINUS}0.80 points")

    def test_sample_deal_results(self):
        self.assertEqual(format_money(14_400 * 12), "$172,800")
        self.assertEqual(format_money(172_800 * 0.95), "$164,160")
        self.assertEqual(format_percent(104_096 / 1_350_000 * 100), "7.71%")

    def test_large_numbers_have_commas(self):
        self.assertEqual(format_money(100_000_000), "$100,000,000")
        self.assertEqual(format_percent(12_345.678), "12,345.68%")


if __name__ == "__main__":
    unittest.main()
