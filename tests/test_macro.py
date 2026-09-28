import unittest

from laya_sim.macro import analyse, mean_difference, rank_test, spearman, window_mean


def country(code, gap, year):
    return {"name": code, "survey_year": year, "gradient": {"gap": gap}}


class MacroTests(unittest.TestCase):
    def test_spearman_is_rank_based_and_handles_ties(self):
        self.assertAlmostEqual(spearman([1, 2, 3, 4], [10, 20, 30, 1000]), 1.0)
        self.assertAlmostEqual(spearman([1, 2, 3, 4], [4, 3, 2, 1]), -1.0)
        self.assertAlmostEqual(spearman([1, 1, 2, 2], [5, 5, 6, 6]), 1.0)

    def test_window_mean_skips_missing_years(self):
        series = {"TUR:2018": 10.0, "TUR:2016": 20.0}
        self.assertEqual(window_mean(series, "TUR", 2018), 15.0)
        self.assertIsNone(window_mean(series, "TUR", 2030))

    def test_rank_test_separates_signal_from_noise(self):
        xs = list(range(60))
        strong = rank_test(xs, [x + (x % 3) for x in xs], draws=500)
        self.assertGreater(strong["low"], 0.8)
        self.assertLess(strong["p"], 0.01)
        noise = rank_test(xs, [(x * 37) % 60 for x in xs], draws=500)
        self.assertLess(noise["low"], 0)
        self.assertGreater(noise["high"], 0)
        self.assertGreater(noise["p"], 0.05)

    def test_mean_difference_sign(self):
        result = mean_difference([0.1] * 10, [0.3] * 10, draws=200)
        self.assertAlmostEqual(result["diff"], 0.2)
        self.assertLess(result["p"], 0.01)

    def test_analyse_joins_by_iso_and_year_and_reports_unmatched(self):
        worldbank = {"source": "test", "iso3": {"AA": "AAA", "BB": "BBB"},
                     "series": {"unemployment": {"AAA:2018": 5.0, "BBB:2020": 9.0},
                                "inflation": {"AAA:2018": 2.0, "BBB:2020": 50.0},
                                "gdp_growth": {"AAA:2018": 3.0, "BBB:2020": -4.0}}}
        rows = [country("AA", 0.1, 2018), country("BB", 0.2, 2020), country("ZZ", 0.3, 2019)]
        result = analyse(rows, worldbank)
        self.assertEqual([j["name"] for j in result["countries"]], ["AA", "BB"])
        self.assertEqual(result["countries"][1]["inflation"], 50.0)
        self.assertEqual(result["unmatched"], ["ZZ"])
        self.assertEqual(result["pandemic"]["n_b"], 1)


if __name__ == "__main__":
    unittest.main()
