"""Distribution and synthetic pooled-interval checks; no third-party runtime."""
import csv
import math
from pathlib import Path
import unittest

from metakit import engine


class StudentTPrecision(unittest.TestCase):
    def test_nonpositive_degrees_remain_undefined(self):
        for df in (0, -1):
            self.assertTrue(math.isnan(engine.t_quantile_975(df)))

    def test_integer_degrees_against_base_r_quantiles(self):
        fixture = Path(__file__).parent / "validation" / "student_t_975.csv"
        with fixture.open(encoding="utf-8", newline="") as source:
            rows = list(csv.DictReader(source))
        self.assertEqual([int(row["df"]) for row in rows],
                         list(range(1, 101)) + [128, 256, 512, 1000, 10000, 1000000])
        for row in rows:
            with self.subTest(df=row["df"]):
                self.assertAlmostEqual(engine.t_quantile_975(int(row["df"])),
                                       float(row["quantile_975"]), delta=1e-6)

    def test_small_degrees_against_analytic_distributions(self):
        # df=1 is Cauchy; df=2 has F(t)=1/2+t/(2*sqrt(t*t+2)).
        expected = {1: 1 / math.tan(math.pi * .025),
                    2: math.sqrt(2) * .95 / math.sqrt(1 - .95**2)}
        for df, value in expected.items():
            with self.subTest(df=df):
                self.assertAlmostEqual(engine.t_quantile_975(df), value, delta=1e-9)

    def test_synthetic_three_study_interval_against_closed_form(self):
        # Invented equal log-effects, known variance .2: Q=0, tau2=0,
        # floored KH standard error sqrt(.2/3), exactly two degrees of freedom.
        trials = [engine.TrialEffect(name="synthetic-" + str(i), yi=.25, vi=.2)
                  for i in range(3)]
        result = engine.pool_effects(trials, "OR")
        critical = math.sqrt(2) * .95 / math.sqrt(1 - .95**2)
        width = critical * math.sqrt(.2 / 3)
        self.assertEqual(result.tau2, 0)
        self.assertTrue(result.hksj_floor_applied)
        self.assertAlmostEqual(result.ci_low, math.exp(.25 - width), delta=1e-6)
        self.assertAlmostEqual(result.ci_high, math.exp(.25 + width), delta=1e-6)


if __name__ == "__main__":
    unittest.main()
