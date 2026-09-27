import random
import unittest

from laya_sim.experiment import bootstrap_ci, run_study, shuffle_attributes
from laya_sim.model import BASELINE, Profile, Scenario, run, similarity


def fake_profiles(n=200, seed=1):
    rng = random.Random(seed)
    return [Profile(i, rng.choice(["18-29", "30-44", "45-59", "60+"]), rng.choice(["lower", "middle", "upper"]),
                    "middle", rng.random(), rng.choice(["employed", "unemployed", "retired"]), rng.randint(0, 100),
                    rng.random() < 0.2, rng.randint(0, 100), rng.randint(0, 100), rng.choice([-1, 0, 1]),
                    weight=rng.uniform(0.5, 2)) for i in range(n)]


class ModelTests(unittest.TestCase):
    def test_reproducible(self):
        profiles = fake_profiles()
        self.assertEqual(run(profiles, BASELINE, 400, 3, 5), run(profiles, BASELINE, 400, 3, 5))

    def test_zero_strength_crisis_equals_baseline(self):
        profiles = fake_profiles()
        base = run(profiles, BASELINE, 400, 3, 5)
        for mode in ("entrenchment", "drift", "trust_building"):
            crisis = run(profiles, Scenario("x", mode, 0.0), 400, 3, 5)
            self.assertEqual(crisis["changes_per_100_per_round"], base["changes_per_100_per_round"])

    def test_invulnerable_population_is_untouched_by_entrenchment(self):
        profiles = [Profile(i, "30-44", "upper", "high", 1.0, "employed", 50, True, 50, 100, i % 3 - 1) for i in range(30)]
        base = run(profiles, BASELINE, 300, 3, 2)
        crisis = run(profiles, Scenario("x", "entrenchment", 1.0), 300, 3, 2)
        self.assertEqual(crisis["changes_per_100_per_round"], base["changes_per_100_per_round"])

    def test_drift_only_moves_toward_government(self):
        profiles = fake_profiles()
        base = run(profiles, BASELINE, 2000, 5, 3)
        drift = run(profiles, Scenario("x", "drift", 1.0), 2000, 5, 3)
        self.assertGreater(drift["final_mean_stance"], base["final_mean_stance"])

    def test_similarity_ignores_missing(self):
        a = Profile(0, "unknown", "unknown", "unknown", None, "unknown", None, None, None, None, 0)
        self.assertEqual(similarity(a, a), 0.5)

    def test_limits_fail_closed(self):
        with self.assertRaises(ValueError):
            run(fake_profiles(), BASELINE, agents=1)
        with self.assertRaises(ValueError):
            Scenario("x", "secret")
        with self.assertRaises(ValueError):
            Scenario("x", "drift", 2.0)


class ExperimentTests(unittest.TestCase):
    def test_bootstrap_ci_brackets_mean(self):
        ci = bootstrap_ci([1.0, 2.0, 3.0, 4.0])
        self.assertLessEqual(ci["low"], ci["mean"])
        self.assertGreaterEqual(ci["high"], ci["mean"])

    def test_placebo_keeps_marginals(self):
        profiles = fake_profiles()
        shuffled = shuffle_attributes(profiles, 1)
        self.assertEqual(sorted(p.religiosity for p in profiles), sorted(p.religiosity for p in shuffled))
        self.assertNotEqual([p.religiosity for p in profiles], [p.religiosity for p in shuffled])

    def test_study_is_reproducible(self):
        profiles = fake_profiles(60)
        first = run_study(profiles, (1, 2, 3), agents=200, rounds=2)
        second = run_study(profiles, (1, 2, 3), agents=200, rounds=2)
        self.assertEqual(first, second)
        self.assertEqual(set(first["headline"]), {"entrenchment", "drift", "trust_building"})
        self.assertIn("placebo", first)


if __name__ == "__main__":
    unittest.main()
