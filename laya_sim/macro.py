"""Does the national economy explain the vulnerability gap?

The crisis in the simulation is an assumption. This layer uses measured
macro conditions instead: for each country, World Bank unemployment,
inflation and GDP growth averaged over the survey year and the two years
before it. If crises widen the gap, countries surveyed under worse
conditions should show bigger gaps.

Rank (Spearman) correlation, because inflation is heavily skewed
(Venezuela, Zimbabwe, Lebanon). p-values from a permutation test, CIs from
a country bootstrap. With ~85 countries, a correlation of |r| < 0.2 cannot
be told apart from zero, so a null result here means "no detectable
relationship", not "proved zero".
"""

import json
import random
import urllib.request
from pathlib import Path
from statistics import mean

INDICATORS = {
    "unemployment": ("SL.UEM.TOTL.ZS", "Unemployment, % of labour force"),
    "inflation": ("FP.CPI.TOTL.ZG", "Consumer price inflation, %"),
    "gdp_growth": ("NY.GDP.MKTP.KD.ZG", "Real GDP growth, %"),
}
WINDOW = 3
YEARS = "2012:2023"
API = "https://api.worldbank.org/v2"
PANDEMIC_FROM = 2020


def _get(url):
    with urllib.request.urlopen(url, timeout=60) as response:
        return json.load(response)


def fetch_worldbank(cache_path):
    """World Bank series keyed by ISO3 and year. Cached so reruns are offline and identical."""
    cache = Path(cache_path)
    if cache.is_file():
        return json.loads(cache.read_text(encoding="utf-8"))
    iso3 = {c["iso2Code"]: c["id"] for c in _get(f"{API}/country?format=json&per_page=400")[1]}
    series = {}
    for key, (code, _) in INDICATORS.items():
        rows = _get(f"{API}/country/all/indicator/{code}?format=json&date={YEARS}&per_page=20000")[1]
        series[key] = {f'{r["countryiso3code"]}:{r["date"]}': r["value"] for r in rows if r["value"] is not None}
    data = {"iso3": iso3, "series": series, "source": "World Bank WDI API", "years": YEARS}
    cache.parent.mkdir(exist_ok=True)
    cache.write_text(json.dumps(data), encoding="utf-8")
    return data


def window_mean(series, iso3, year, span=WINDOW):
    """Mean over the survey year and the span-1 years before it; None if no value."""
    values = [series.get(f"{iso3}:{year - k}") for k in range(span)]
    values = [v for v in values if v is not None]
    return mean(values) if values else None


def _ranks(values):
    order = sorted(range(len(values)), key=values.__getitem__)
    ranks = [0.0] * len(values)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and values[order[j + 1]] == values[order[i]]:
            j += 1
        for k in range(i, j + 1):
            ranks[order[k]] = (i + j) / 2
        i = j + 1
    return ranks


def _pearson(xs, ys):
    mx, my = mean(xs), mean(ys)
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    sxx = sum((x - mx) ** 2 for x in xs)
    syy = sum((y - my) ** 2 for y in ys)
    return sxy / (sxx * syy) ** 0.5 if sxx and syy else 0.0


def spearman(xs, ys):
    return _pearson(_ranks(xs), _ranks(ys))


def rank_test(xs, ys, draws=5000, seed=0):
    """Spearman r, two-sided permutation p and country-bootstrap 95% CI."""
    r = spearman(xs, ys)
    rng = random.Random(seed)
    shuffled = list(ys)
    hits = 0
    for _ in range(draws):
        rng.shuffle(shuffled)
        hits += abs(spearman(xs, shuffled)) >= abs(r)
    pairs = list(zip(xs, ys))
    boots = sorted(spearman(*zip(*rng.choices(pairs, k=len(pairs)))) for _ in range(draws // 5))
    return {"r": r, "p": (hits + 1) / (draws + 1), "low": boots[int(0.025 * len(boots))],
            "high": boots[int(0.975 * len(boots)) - 1], "n": len(xs)}


def mean_difference(a, b, draws=5000, seed=0):
    """Mean(b) - mean(a) with a two-sided permutation p."""
    observed = mean(b) - mean(a)
    pooled = list(a) + list(b)
    rng = random.Random(seed)
    hits = 0
    for _ in range(draws):
        rng.shuffle(pooled)
        hits += abs(mean(pooled[len(a):]) - mean(pooled[:len(a)])) >= abs(observed)
    return {"a_mean": mean(a), "b_mean": mean(b), "diff": observed, "p": (hits + 1) / (draws + 1),
            "n_a": len(a), "n_b": len(b)}


def analyse(countries, worldbank):
    """Join each country's gap to its macro conditions around the survey year."""
    joined = []
    for row in countries:
        iso3 = worldbank["iso3"].get(row["name"])
        year = row.get("survey_year")
        if iso3 is None or year is None:
            continue
        macro = {key: window_mean(worldbank["series"][key], iso3, year) for key in INDICATORS}
        joined.append({"name": row["name"], "year": year, "gap": row["gradient"]["gap"], **macro})
    tests = {}
    for key, (_, label) in INDICATORS.items():
        usable = [j for j in joined if j[key] is not None]
        tests[key] = {"label": label, **rank_test([j[key] for j in usable], [j["gap"] for j in usable])}
    dated = [r for r in countries if r.get("survey_year") is not None]
    before = [r["gradient"]["gap"] for r in dated if r["survey_year"] < PANDEMIC_FROM]
    during = [r["gradient"]["gap"] for r in dated if r["survey_year"] >= PANDEMIC_FROM]
    return {"window_years": WINDOW, "source": worldbank["source"], "tests": tests, "countries": joined,
            "pandemic": mean_difference(before, during) if before and during else None,
            "unmatched": sorted(r["name"] for r in countries if worldbank["iso3"].get(r["name"]) is None)}
