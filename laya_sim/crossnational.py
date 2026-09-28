"""Cross-national comparison over every country in the Joint EVS/WVS file.

Two layers, kept separate on purpose:
1. Descriptive (no model): within each country, how much more do the most
   economically vulnerable lean toward "government should take more
   responsibility" than the least vulnerable? CI from a respondent bootstrap,
   so it reflects survey sampling error.
2. Model: under the drift assumption, how far does the mean stance move with
   real profiles versus a placebo with shuffled attributes? The difference is
   the part of the simulated effect that comes from each country's real joint
   structure rather than from the mechanism alone.
"""

import random
from statistics import mean

from .experiment import bootstrap_ci, shuffle_attributes
from .model import BASELINE, Scenario, run

MIN_COVERAGE = 0.8
DRIFT = Scenario("crisis_drift", "drift", 0.6)


def _weighted_quantile(pairs, q):
    pairs = sorted(pairs)
    total = sum(w for _, w in pairs)
    running = 0.0
    for value, weight in pairs:
        running += weight
        if running >= q * total:
            return value
    return pairs[-1][0]


def eligible(profiles):
    """Skip countries where stance or the vulnerability inputs are mostly missing."""
    n = len(profiles)
    stance_ok = sum(not p.stance_missing for p in profiles) / n
    income_ok = sum(p.income_score is not None for p in profiles) / n
    return stance_ok >= MIN_COVERAGE and income_ok >= MIN_COVERAGE


def _vulnerability(p):
    return p.vulnerability


def _income_only(p):
    return 1 - p.income_score


def gradient(profiles, draws=400, seed=0, score=_vulnerability):
    """Weighted gov-share of top score tercile minus bottom tercile."""
    answered = [p for p in profiles if not p.stance_missing
                and (score is not _income_only or p.income_score is not None)]
    pairs = [(score(p), p.weight) for p in answered]
    low_cut, high_cut = _weighted_quantile(pairs, 1 / 3), _weighted_quantile(pairs, 2 / 3)
    top = [p for p in answered if score(p) > high_cut]
    bottom = [p for p in answered if score(p) <= low_cut]

    def share(group):
        weight = sum(p.weight for p in group)
        return sum(p.weight for p in group if p.stance == 1) / weight if weight else 0.0

    rng = random.Random(seed)
    boots = sorted(share(rng.choices(top, k=len(top))) - share(rng.choices(bottom, k=len(bottom)))
                   for _ in range(draws))
    return {
        "top_share": share(top),
        "bottom_share": share(bottom),
        "gap": share(top) - share(bottom),
        "low": boots[int(0.025 * draws)],
        "high": boots[int(0.975 * draws) - 1],
        "n_top": len(top),
        "n_bottom": len(bottom),
    }


def drift_structure(profiles, seeds, agents, rounds):
    """Per-seed Δ mean stance (drift − baseline), real vs placebo profiles."""
    fake = shuffle_attributes(profiles, seed=99)
    real_d, fake_d = [], []
    for seed in seeds:
        real_d.append(run(profiles, DRIFT, agents, rounds, seed)["final_mean_stance"]
                      - run(profiles, BASELINE, agents, rounds, seed)["final_mean_stance"])
        fake_d.append(run(fake, DRIFT, agents, rounds, seed)["final_mean_stance"]
                      - run(fake, BASELINE, agents, rounds, seed)["final_mean_stance"])
    return {
        "real": bootstrap_ci(real_d),
        "placebo": bootstrap_ci(fake_d),
        "structure": bootstrap_ci([r - f for r, f in zip(real_d, fake_d)]),
    }


def run_crossnational(countries, seeds=tuple(range(1, 11)), agents=5000, rounds=10, model=True):
    rows, skipped = [], []
    for code, (name, profiles) in sorted(countries.items()):
        if not eligible(profiles):
            skipped.append(name)
            continue
        row = {"code": code, "name": name, "respondents": len(profiles),
               "mean_vulnerability": mean(p.vulnerability for p in profiles),
               "gradient": gradient(profiles),
               "gradient_income_only": gradient(profiles, score=_income_only)}
        if model:
            row["drift"] = drift_structure(profiles, seeds, agents, rounds)
        rows.append(row)
    return {"design": {"seeds": list(seeds), "agents": agents, "rounds": rounds, "drift_strength": DRIFT.strength},
            "countries": rows, "skipped": skipped}
