"""White-box tests for Deal Math (dealcalc/deal_math.py; SDS 4.1; R4, R5, R12, and the report conversions).

Deal Math has no branches: compute() is four formulas in a row, deltas() is two loops over fixed field lists, and
each report conversion is one formula. White-box testing here means testing each statement where it can go wrong:

compute(deal)
    F1  gpr = monthly_rent × 12                  test_F1_gpr
    F2  egi = gpr × (1 − vacancy_pct ÷ 100)      test_F2_egi_at_0_and_100_percent_vacancy
    F3  noi = egi − operating_costs              test_F3_noi_can_be_zero_or_negative
    F4  cap_rate_pct = noi ÷ price × 100         test_F4_cap_rate_is_a_percent
    all four together (known answers)            test_sample_deal_a_matches_r5, test_sample_deal_b
deltas(deal_a, results_a, deal_b, results_b)
    L1  loop over the 4 input fields             test_L1_L2_every_field_is_b_minus_a
    L2  loop over the 4 result fields            test_L1_L2_every_field_is_b_minus_a
    the order is B minus A, not A minus B        test_sample_deltas, test_swapping_a_and_b_flips_signs
    the same property gives all zeros            test_same_property_gives_zero_deltas
report conversions (used by the Report Reader)
    C1  monthly_from_yearly: yearly ÷ 12         test_C1_monthly_from_yearly
    C2  yearly_from_monthly: monthly × 12        test_C2_yearly_from_monthly
    C3  total_from_average: average × units      test_C3_total_from_average
    C4  vacancy_from_occupancy: 100 − occupancy  test_C4_vacancy_from_occupancy
"""

import unittest

from dealcalc.deal_math import (INPUT_FIELDS, RESULT_FIELDS, Deal, Results, compute, deltas, monthly_from_yearly,
                                total_from_average, vacancy_from_occupancy, yearly_from_monthly)

SAMPLE_A = Deal(price=1_200_000, monthly_rent=14_400, vacancy_pct=5, operating_costs=62_000)
SAMPLE_B = Deal(price=1_350_000, monthly_rent=15_600, vacancy_pct=7, operating_costs=70_000)


class TestCompute(unittest.TestCase):

    def assertResults(self, results, gpr, egi, noi, cap_rate_pct):
        self.assertAlmostEqual(results.gpr, gpr, places=6)
        self.assertAlmostEqual(results.egi, egi, places=6)
        self.assertAlmostEqual(results.noi, noi, places=6)
        self.assertAlmostEqual(results.cap_rate_pct, cap_rate_pct, places=6)

    def test_sample_deal_a_matches_r5(self):
        # R5: GPR $172,800, EGI $164,160, NOI $102,160, cap rate 8.51%
        self.assertResults(compute(SAMPLE_A), 172_800, 164_160, 102_160, 102_160 / 1_200_000 * 100)
        self.assertEqual(round(compute(SAMPLE_A).cap_rate_pct, 2), 8.51)

    def test_sample_deal_b(self):
        # the comparison sample in R9: NOI $104,096, cap rate 7.71%
        self.assertResults(compute(SAMPLE_B), 187_200, 174_096, 104_096, 104_096 / 1_350_000 * 100)
        self.assertEqual(round(compute(SAMPLE_B).cap_rate_pct, 2), 7.71)

    def test_F1_gpr(self):
        self.assertEqual(compute(Deal(price=1, monthly_rent=1_000, vacancy_pct=0, operating_costs=0)).gpr, 12_000)
        self.assertEqual(compute(Deal(price=1, monthly_rent=0, vacancy_pct=0, operating_costs=0)).gpr, 0)

    def test_F2_egi_at_0_and_100_percent_vacancy(self):
        # vacancy is a percent: 0 keeps all the rent, 100 keeps none
        full = compute(Deal(price=1_000_000, monthly_rent=10_000, vacancy_pct=0, operating_costs=0))
        empty = compute(Deal(price=1_000_000, monthly_rent=10_000, vacancy_pct=100, operating_costs=0))
        half = compute(Deal(price=1_000_000, monthly_rent=10_000, vacancy_pct=50, operating_costs=0))
        self.assertEqual(full.egi, 120_000)
        self.assertEqual(empty.egi, 0)
        self.assertEqual(half.egi, 60_000)

    def test_F3_noi_can_be_zero_or_negative(self):
        even = compute(Deal(price=1_000_000, monthly_rent=10_000, vacancy_pct=0, operating_costs=120_000))
        loss = compute(Deal(price=1_000_000, monthly_rent=10_000, vacancy_pct=0, operating_costs=124_500))
        self.assertEqual(even.noi, 0)
        self.assertEqual(even.cap_rate_pct, 0)
        self.assertEqual(loss.noi, -4_500)
        self.assertAlmostEqual(loss.cap_rate_pct, -0.45)

    def test_F4_cap_rate_is_a_percent(self):
        # NOI of $80,000 on a $1,000,000 price is 8 percent, stored as 8 (not 0.08)
        results = compute(Deal(price=1_000_000, monthly_rent=10_000, vacancy_pct=0, operating_costs=40_000))
        self.assertAlmostEqual(results.cap_rate_pct, 8)

    def test_compute_has_no_side_effects(self):
        before = SAMPLE_A
        compute(SAMPLE_A)
        self.assertEqual(SAMPLE_A, before)
        self.assertEqual(compute(SAMPLE_A), compute(SAMPLE_A))


class TestDeltas(unittest.TestCase):

    def test_L1_L2_every_field_is_b_minus_a(self):
        a = Deal(price=1, monthly_rent=2, vacancy_pct=3, operating_costs=4)
        b = Deal(price=11, monthly_rent=22, vacancy_pct=33, operating_costs=44)
        ra = Results(gpr=5, egi=6, noi=7, cap_rate_pct=8)
        rb = Results(gpr=55, egi=66, noi=77, cap_rate_pct=88)
        self.assertEqual(deltas(a, ra, b, rb), {"price": 10, "monthly_rent": 20, "vacancy_pct": 30,
                                                "operating_costs": 40, "gpr": 50, "egi": 60, "noi": 70,
                                                "cap_rate_pct": 80})
        self.assertEqual(list(deltas(a, ra, b, rb)), list(INPUT_FIELDS + RESULT_FIELDS))

    def test_sample_deltas(self):
        # the comparison in the prototype UI: B minus A
        d = deltas(SAMPLE_A, compute(SAMPLE_A), SAMPLE_B, compute(SAMPLE_B))
        self.assertEqual(d["price"], 150_000)
        self.assertEqual(d["vacancy_pct"], 2)
        self.assertAlmostEqual(d["gpr"], 14_400)
        self.assertAlmostEqual(d["egi"], 9_936)
        self.assertAlmostEqual(d["noi"], 1_936)
        self.assertEqual(round(d["cap_rate_pct"], 2), -0.80)

    def test_swapping_a_and_b_flips_signs(self):
        forward = deltas(SAMPLE_A, compute(SAMPLE_A), SAMPLE_B, compute(SAMPLE_B))
        backward = deltas(SAMPLE_B, compute(SAMPLE_B), SAMPLE_A, compute(SAMPLE_A))
        for field in forward:
            with self.subTest(field=field):
                self.assertAlmostEqual(forward[field], -backward[field])

    def test_same_property_gives_zero_deltas(self):
        self.assertEqual(set(deltas(SAMPLE_A, compute(SAMPLE_A), SAMPLE_A, compute(SAMPLE_A)).values()), {0})


class TestReportConversions(unittest.TestCase):

    def test_C1_monthly_from_yearly(self):
        self.assertEqual(monthly_from_yearly(187_200), 15_600)  # sample deal B's yearly rent (R9)
        self.assertAlmostEqual(monthly_from_yearly(175_000), 14_583.333333, places=5)
        self.assertEqual(monthly_from_yearly(0), 0)

    def test_C2_yearly_from_monthly(self):
        self.assertEqual(yearly_from_monthly(3_000), 36_000)
        self.assertEqual(yearly_from_monthly(0), 0)

    def test_C3_total_from_average(self):
        self.assertEqual(total_from_average(1_200, 12), 14_400)  # sample deal A: 12 units at $1,200
        self.assertEqual(total_from_average(1_150, 6), 6_900)

    def test_C4_vacancy_from_occupancy(self):
        self.assertEqual(vacancy_from_occupancy(95), 5)
        self.assertEqual(vacancy_from_occupancy(100), 0)
        self.assertEqual(vacancy_from_occupancy(0), 100)
        self.assertAlmostEqual(vacancy_from_occupancy(92.5), 7.5)

    def test_conversions_and_compute_agree(self):
        # a yearly rent turned into a monthly rent gives that yearly rent back as GPR
        deal = Deal(price=1_000_000, monthly_rent=monthly_from_yearly(175_000), vacancy_pct=0, operating_costs=0)
        self.assertAlmostEqual(compute(deal).gpr, 175_000)


if __name__ == "__main__":
    unittest.main()
