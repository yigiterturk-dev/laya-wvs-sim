import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from laya_sim import wvs

HEADER = "cntry,X003,X025R,X028,X047_WVS7,F063,A165,E037,E069_11,A170,pwght\n"


class CodebookMappingTests(unittest.TestCase):
    def test_negative_codes_are_missing_not_answers(self):
        self.assertIsNone(wvs.map_stance("-1"))   # don't know must not become "disagree"
        self.assertIsNone(wvs.map_stance("-2"))
        self.assertIsNone(wvs.map_government_trust("-1"))
        self.assertIsNone(wvs.map_social_trust("-2"))
        self.assertEqual(wvs.map_income("-1"), ("unknown", None))

    def test_stance_scale(self):
        self.assertEqual(wvs.map_stance("1"), -1)
        self.assertEqual(wvs.map_stance("5"), 0)
        self.assertEqual(wvs.map_stance("10"), 1)

    def test_religiosity_direction(self):
        row = dict.fromkeys(HEADER.strip().split(","), "1")
        row["F063"] = "10"   # God very important
        self.assertEqual(wvs.profile_from_row(row, 0).religiosity, 100)
        row["F063"] = "1"
        self.assertEqual(wvs.profile_from_row(row, 0).religiosity, 0)

    def test_government_trust_direction(self):
        self.assertEqual(wvs.map_government_trust("1"), 100)   # a great deal
        self.assertEqual(wvs.map_government_trust("4"), 0)     # none at all

    def test_retired_is_not_employed(self):
        self.assertEqual(wvs.map_employment("4"), "retired")
        self.assertEqual(wvs.map_employment("7"), "unemployed")
        self.assertEqual(wvs.map_employment("2"), "employed")


class LoadTests(unittest.TestCase):
    def _write(self, directory, body):
        path = Path(directory) / "wvs.csv"
        path.write_text(HEADER + body, encoding="utf-8")
        return path

    def test_filters_country_and_keeps_weight(self):
        with TemporaryDirectory() as d:
            path = self._write(d, "792,24,3,7,2,10,1,-1,1,3,1.7\n840,60,1,1,9,1,2,2,4,9,1\n")
            profiles = wvs.load_profiles(path, "792")
        self.assertEqual(len(profiles), 1)
        p = profiles[0]
        self.assertEqual((p.age_group, p.education, p.employment, p.income), ("18-29", "upper", "unemployed", "low"))
        self.assertTrue(p.stance_missing)
        self.assertEqual(p.stance, 0)
        self.assertEqual(p.weight, 1.7)

    def test_missing_columns_fail_closed(self):
        with TemporaryDirectory() as d:
            path = Path(d) / "bad.csv"
            path.write_text("cntry,X003\n792,30\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                wvs.load_profiles(path)


if __name__ == "__main__":
    unittest.main()
