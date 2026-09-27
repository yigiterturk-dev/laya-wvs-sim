"""Seeded experiment design: paired effects, bootstrap CIs, sensitivity, placebo."""

from dataclasses import replace
import random
from statistics import mean

from .model import BASELINE, GROUP_FIELDS, Scenario, run

STRENGTHS = (0.2, 0.4, 0.6, 0.8, 1.0)
HEADLINE = {
    "entrenchment": Scenario("crisis_entrenchment", "entrenchment", 0.6),
    "drift": Scenario("crisis_drift", "drift", 0.6),
    "trust_building": Scenario("public_trust_building", "trust_building", 0.6),
}


def bootstrap_ci(values, seed=0, draws=2000):
    """Mean and percentile 95% CI; deterministic for a given input."""
    rng = random.Random(seed)
    n = len(values)
    means = sorted(mean(rng.choices(values, k=n)) for _ in range(draws))
    return {"mean": mean(values), "low": means[int(0.025 * draws)], "high": means[int(0.975 * draws) - 1], "n": n}


def _paired(profiles, scenario, seeds, agents, rounds, baselines):
    """Scenario minus baseline, matched by seed (same starting population)."""
    diffs = {"changes": [], "mean_stance": [], "groups": {f: {} for f in GROUP_FIELDS}}
    for seed in seeds:
        result = run(profiles, scenario, agents, rounds, seed)
        base = baselines[seed]
        diffs["changes"].append(result["changes_per_100_per_round"] - base["changes_per_100_per_round"])
        diffs["mean_stance"].append(result["final_mean_stance"] - base["final_mean_stance"])
        for f in GROUP_FIELDS:
            for group, rate in result["group_rates"][f].items():
                diffs["groups"][f].setdefault(group, []).append(rate - base["group_rates"][f].get(group, 0.0))
    return {
        "scenario": scenario.name,
        "mode": scenario.mode,
        "strength": scenario.strength,
        "delta_changes_per_100": bootstrap_ci(diffs["changes"]),
        "delta_mean_stance": bootstrap_ci(diffs["mean_stance"]),
        "delta_group_rates": {
            f: {g: bootstrap_ci(v) for g, v in groups.items() if g != "unknown"}
            for f, groups in diffs["groups"].items()
        },
    }


def shuffle_attributes(profiles, seed):
    """Placebo: permute each attribute column independently.

    Marginal distributions stay identical, but the joint structure (who is
    vulnerable, who is religious, who trusts whom) is destroyed.
    """
    rng = random.Random(seed)
    columns = ("age_group", "education", "income_score", "employment", "religiosity",
               "social_trust", "government_trust", "life_satisfaction", "stance")
    shuffled = {c: [getattr(p, c) for p in profiles] for c in columns}
    for values in shuffled.values():
        rng.shuffle(values)
    result = []
    for i, p in enumerate(profiles):
        values = {c: shuffled[c][i] for c in columns}
        score = values["income_score"]
        values["income"] = "unknown" if score is None else "low" if score <= 2 / 9 else "high" if score >= 7 / 9 else "middle"
        result.append(replace(p, **values))
    return result


def stance_by_band(profiles):
    """Survey-weighted share leaning 'government responsible' per vulnerability band."""
    totals = {}
    for p in profiles:
        w, g = totals.get(p.vulnerability_band, (0.0, 0.0))
        totals[p.vulnerability_band] = (w + p.weight, g + p.weight * (p.stance == 1))
    return {band: g / w for band, (w, g) in totals.items()}


def run_study(profiles, seeds=tuple(range(1, 21)), agents=10_000, rounds=10, sensitivity=True, placebo=True):
    baselines = {seed: run(profiles, BASELINE, agents, rounds, seed) for seed in seeds}
    study = {
        "design": {"agents": agents, "rounds": rounds, "seeds": list(seeds), "respondents": len(profiles),
                   "weighted_sampling": True},
        "baseline": {
            "changes_per_100": bootstrap_ci([b["changes_per_100_per_round"] for b in baselines.values()]),
            "final_mean_stance": bootstrap_ci([b["final_mean_stance"] for b in baselines.values()]),
            "initial_mean_stance": baselines[seeds[0]]["initial_mean_stance"],
            "group_sizes": baselines[seeds[0]]["group_sizes"],
            "government_share_by_vulnerability": stance_by_band(profiles),
        },
        "headline": {key: _paired(profiles, s, seeds, agents, rounds, baselines) for key, s in HEADLINE.items()},
    }
    if sensitivity:
        sweep_seeds = seeds[:10]
        study["sensitivity"] = {
            mode: [_paired(profiles, Scenario(f"{mode}_{s}", mode, s), sweep_seeds, agents, rounds, baselines)
                   for s in STRENGTHS]
            for mode in ("entrenchment", "drift")
        }
    if placebo:
        fake = shuffle_attributes(profiles, seed=99)
        fake_baselines = {seed: run(fake, BASELINE, agents, rounds, seed) for seed in seeds}
        study["placebo"] = {key: _paired(fake, HEADLINE[key], seeds, agents, rounds, fake_baselines)
                            for key in ("entrenchment", "drift")}
    return study
