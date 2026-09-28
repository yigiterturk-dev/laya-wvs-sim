import unittest

from laya_sim.crossnational import eligible, gradient, run_crossnational
from laya_sim.model import Profile


def person(i, income_score, stance, missing=False):
    return Profile(i, "30-44", "middle", "x", income_score, "employed", 50, True, 50, 50, stance, missing)


class CrossNationalTests(unittest.TestCase):
    def test_gradient_detects_poor_leaning_toward_state(self):
        profiles = [person(i, 0.0, 1) for i in range(100)] + [person(100 + i, 1.0, -1) for i in range(100)] \
            + [person(200 + i, 0.5, 0) for i in range(100)]
        g = gradient(profiles)
        self.assertAlmostEqual(g["gap"], 1.0)
        self.assertGreater(g["low"], 0)

    def test_no_gradient_when_attitude_is_independent(self):
        profiles = [person(i, i % 10 / 9, 1 if (i // 10) % 2 else -1) for i in range(600)]
        g = gradient(profiles)
        self.assertLess(g["low"], 0)
        self.assertGreater(g["high"], 0)

    def test_low_coverage_country_is_skipped(self):
        profiles = [person(i, None, 0) for i in range(50)]
        self.assertFalse(eligible(profiles))
        result = run_crossnational({"1": ("XX", profiles)}, model=False)
        self.assertEqual(result["skipped"], ["XX"])


if __name__ == "__main__":
    unittest.main()
