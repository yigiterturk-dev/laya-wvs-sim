"""Map rows of the official Joint EVS/WVS CSV (v5.0) into agent profiles.

Codebook conventions used here (Joint EVS/WVS 2017-2022):
- Negative values (-1 don't know, -2 no answer, -3 not applicable, -4 not
  asked, -5 missing) are treated as missing, never as a substantive answer.
- F063 "How important is God in your life": 1 = not at all ... 10 = very.
- A165 "Most people can be trusted": 1 = can be trusted, 2 = need to be careful.
- E037 "Government vs people responsibility": 1 = people should take more
  responsibility ... 10 = government should take more responsibility.
- E069_11 confidence in government: 1 = a great deal ... 4 = none at all.
- X028 employment: 1 full time, 2 part time, 3 self employed, 4 retired,
  5 housewife, 6 student, 7 unemployed, 8 other.
- X047_WVS7 household income step, 1 (lowest) ... 10 (highest).
- A170 life satisfaction, 1 ... 10.
- X025R education, 1 lower, 2 middle, 3 upper.

The raw file is read in place and never copied or embedded in any output.
"""

import csv
from collections import Counter
from pathlib import Path

from .model import Profile

REQUIRED_COLUMNS = ("cntry", "X003", "X025R", "X028", "X047_WVS7", "F063",
                    "A165", "E037", "E069_11", "A170", "pwght")


def _code(value):
    """Return the integer code, or None for blank and negative missing codes."""
    try:
        number = int(float(str(value).strip()))
    except (TypeError, ValueError):
        return None
    return number if number >= 0 else None


def _scale(value, low, high):
    """Map a code in [low, high] onto 0..100; anything else is missing."""
    code = _code(value)
    if code is None or not low <= code <= high:
        return None
    return round((code - low) * 100 / (high - low))


def map_stance(value):
    """E037 -> -1 (people responsible), 0 (middle), 1 (government responsible)."""
    code = _code(value)
    if code is None or not 1 <= code <= 10:
        return None
    if code <= 4:
        return -1
    if code >= 7:
        return 1
    return 0


def map_government_trust(value):
    code = _code(value)
    if code is None or not 1 <= code <= 4:
        return None
    return round((4 - code) * 100 / 3)


def map_social_trust(value):
    return {1: True, 2: False}.get(_code(value))


def map_employment(value):
    code = _code(value)
    if code in (1, 2, 3):
        return "employed"
    if code == 7:
        return "unemployed"
    if code == 4:
        return "retired"
    if code in (5, 6, 8):
        return "inactive"
    return "unknown"


def map_income(value):
    code = _code(value)
    if code is None or not 1 <= code <= 10:
        return "unknown", None
    label = "low" if code <= 3 else "high" if code >= 8 else "middle"
    return label, (code - 1) / 9


def map_education(value):
    return {1: "lower", 2: "middle", 3: "upper"}.get(_code(value), "unknown")


def map_age_group(value):
    age = _code(value)
    if age is None:
        return "unknown"
    return "18-29" if age < 30 else "30-44" if age < 45 else "45-59" if age < 60 else "60+"


def profile_from_row(row, profile_id):
    income, income_score = map_income(row.get("X047_WVS7"))
    if income_score is None:   # EVS rows carry income in X047E_EVS5 (same 1-10 scale)
        income, income_score = map_income(row.get("X047E_EVS5"))
    stance = map_stance(row.get("E037"))
    try:
        weight = float(str(row.get("pwght", "")).replace(",", "."))
    except ValueError:
        weight = 1.0
    return Profile(
        profile_id=profile_id,
        age_group=map_age_group(row.get("X003")),
        education=map_education(row.get("X025R")),
        income=income,
        income_score=income_score,
        employment=map_employment(row.get("X028")),
        religiosity=_scale(row.get("F063"), 1, 10),
        social_trust=map_social_trust(row.get("A165")),
        government_trust=map_government_trust(row.get("E069_11")),
        life_satisfaction=_scale(row.get("A170"), 1, 10),
        stance=0 if stance is None else stance,
        stance_missing=stance is None,
        weight=weight if weight > 0 else 1.0,
    )


def load_profiles(path, country="792"):
    """Read every respondent of one country from the Joint EVS/WVS CSV."""
    file_path = Path(path)
    if not file_path.is_file():
        raise ValueError("wvs_csv_not_found")
    profiles = []
    with file_path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        missing = [column for column in REQUIRED_COLUMNS if column not in (reader.fieldnames or [])]
        if missing:
            raise ValueError(f"missing_columns:{','.join(missing)}")
        for row in reader:
            if str(row["cntry"]).strip() == str(country):
                profiles.append(profile_from_row(row, len(profiles)))
    if not profiles:
        raise ValueError("no_rows_for_country")
    return profiles


def load_all_countries(path, years=None):
    """One pass over the file: {cntry code: (alpha code, [profiles])}.

    If `years` is a dict, it is filled with {cntry code: Counter(fieldwork year)}.
    """
    file_path = Path(path)
    if not file_path.is_file():
        raise ValueError("wvs_csv_not_found")
    countries = {}
    with file_path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        missing = [column for column in REQUIRED_COLUMNS if column not in (reader.fieldnames or [])]
        if missing:
            raise ValueError(f"missing_columns:{','.join(missing)}")
        for row in reader:
            code = str(row["cntry"]).strip()
            name, profiles = countries.setdefault(code, (row.get("cntry_AN", code).strip(), []))
            profiles.append(profile_from_row(row, len(profiles)))
            if years is not None and str(row.get("year", "")).strip().isdigit():
                years.setdefault(code, Counter())[int(row["year"])] += 1
    return countries


def data_quality(profiles):
    """Count missing values per mapped field so the report can show them."""
    total = len(profiles)
    missing = Counter()
    for profile in profiles:
        missing["stance (E037)"] += profile.stance_missing
        missing["income (X047_WVS7)"] += profile.income == "unknown"
        missing["employment (X028)"] += profile.employment == "unknown"
        missing["religiosity (F063)"] += profile.religiosity is None
        missing["social trust (A165)"] += profile.social_trust is None
        missing["government trust (E069_11)"] += profile.government_trust is None
        missing["life satisfaction (A170)"] += profile.life_satisfaction is None
    return {"respondents": total, "missing": dict(missing)}
