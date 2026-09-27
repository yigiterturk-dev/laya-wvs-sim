"""Agent-based opinion dynamics seeded from survey respondents.

Every mechanism below is an explicit, tunable assumption. The model does not
predict real behaviour; it shows what follows from the assumptions when they
are applied to the real joint distribution of respondent attributes.
"""

from collections import Counter
from dataclasses import dataclass
import random

STANCES = (-1, 0, 1)
STANCE_LABELS = {-1: "people_responsible", 0: "middle", 1: "government_responsible"}

BASE_PERSUASION = 0.18   # max chance per contact that a listener moves one step
DRIFT_BASE = 0.05        # max per-round chance of a crisis-driven drift step
GROUP_FIELDS = ("age_group", "education", "income", "employment", "vulnerability_band")


@dataclass(frozen=True)
class Profile:
    profile_id: int
    age_group: str
    education: str
    income: str
    income_score: float | None
    employment: str
    religiosity: int | None
    social_trust: bool | None
    government_trust: int | None
    life_satisfaction: int | None
    stance: int
    stance_missing: bool = False
    weight: float = 1.0

    @property
    def vulnerability(self):
        """Economic vulnerability proxy in [0, 1]: mean of available parts.

        Parts: low household income, unemployment, low life satisfaction.
        This is a model proxy, not a measured "hit by crisis" label.
        """
        parts = []
        if self.income_score is not None:
            parts.append(1 - self.income_score)
        if self.employment != "unknown":
            parts.append({"unemployed": 1.0, "inactive": 0.4, "retired": 0.3}.get(self.employment, 0.0))
        if self.life_satisfaction is not None:
            parts.append(1 - self.life_satisfaction / 100)
        return sum(parts) / len(parts) if parts else 0.5

    @property
    def vulnerability_band(self):
        value = self.vulnerability
        return "low" if value < 0.33 else "high" if value >= 0.55 else "middle"


@dataclass
class Agent:
    profile: Profile
    stance: int
    openness: float
    influence: float


@dataclass(frozen=True)
class Scenario:
    name: str
    mode: str = "baseline"      # baseline | entrenchment | drift | trust_building
    strength: float = 0.0       # 0..1

    def __post_init__(self):
        if self.mode not in ("baseline", "entrenchment", "drift", "trust_building"):
            raise ValueError("unknown_mode")
        if not 0 <= self.strength <= 1:
            raise ValueError("strength_out_of_range")


BASELINE = Scenario("baseline")


def similarity(a, b):
    """Homophily in [0, 1] over the attributes both respondents answered."""
    scores = []
    if a.religiosity is not None and b.religiosity is not None:
        scores.append(1 - abs(a.religiosity - b.religiosity) / 100)
    if a.income_score is not None and b.income_score is not None:
        scores.append(1 - abs(a.income_score - b.income_score))
    if a.social_trust is not None and b.social_trust is not None:
        scores.append(1.0 if a.social_trust == b.social_trust else 0.0)
    if a.education != "unknown" and b.education != "unknown":
        scores.append(1.0 if a.education == b.education else 0.0)
    if a.age_group != "unknown" and b.age_group != "unknown":
        scores.append(1.0 if a.age_group == b.age_group else 0.0)
    return sum(scores) / len(scores) if scores else 0.5


def build_population(profiles, size, seed, weighted=True):
    """Sample agents from respondents, by survey weight when `weighted`."""
    if not profiles:
        raise ValueError("profiles_required")
    if not 2 <= size <= 100_000:
        raise ValueError("population_size_out_of_range")
    rng = random.Random(seed)
    weights = [p.weight for p in profiles] if weighted else None
    chosen = rng.choices(profiles, weights=weights, k=size)
    return [Agent(p, p.stance, rng.uniform(0.15, 0.85), rng.uniform(0.25, 0.75)) for p in chosen]


def _openness(agent, scenario):
    value = agent.openness
    if scenario.mode == "entrenchment":
        value *= 1 - scenario.strength * agent.profile.vulnerability
    elif scenario.mode == "trust_building" and agent.profile.government_trust is not None:
        value *= 1 + scenario.strength * agent.profile.government_trust / 100
    return value


def _step_toward(stance, target):
    return stance + (target > stance) - (target < stance)


def _group_key(profile, field_name):
    return getattr(profile, field_name)


def run(profiles, scenario=BASELINE, agents=10_000, rounds=10, seed=7, weighted=True):
    """One simulation run; returns JSON-safe aggregate metrics only."""
    if not 1 <= rounds <= 200:
        raise ValueError("round_count_out_of_range")
    population = build_population(profiles, agents, seed, weighted)
    rng = random.Random(seed * 7919 + 1)
    drift_rng = random.Random(seed * 7919 + 2)   # separate stream keeps paired runs aligned
    group_sizes = {f: Counter(_group_key(a.profile, f) for a in population) for f in GROUP_FIELDS}
    group_changes = {f: Counter() for f in GROUP_FIELDS}
    initial_mean = sum(a.stance for a in population) / len(population)
    changes = 0

    def record(agent):
        for f in GROUP_FIELDS:
            group_changes[f][_group_key(agent.profile, f)] += 1

    for _ in range(rounds):
        rng.shuffle(population)
        for a, b in zip(population[::2], population[1::2]):
            if a.stance == b.stance:
                continue
            closeness = 0.25 + 0.75 * similarity(a.profile, b.profile)
            for listener, speaker in ((a, b), (b, a)):
                p = BASE_PERSUASION * closeness * _openness(listener, scenario) * speaker.influence
                if listener.stance != speaker.stance and rng.random() < p:
                    listener.stance = _step_toward(listener.stance, speaker.stance)
                    changes += 1
                    record(listener)
        if scenario.mode == "drift":
            for agent in population:
                if agent.stance < 1 and drift_rng.random() < DRIFT_BASE * scenario.strength * agent.profile.vulnerability:
                    agent.stance += 1
                    changes += 1
                    record(agent)

    counts = Counter(a.stance for a in population)
    per_round = len(population) * rounds / 100
    return {
        "scenario": scenario.name,
        "seed": seed,
        "changes_per_100_per_round": changes / per_round,
        "final_mean_stance": sum(a.stance for a in population) / len(population),
        "initial_mean_stance": initial_mean,
        "final_shares": {STANCE_LABELS[s]: counts.get(s, 0) / len(population) for s in STANCES},
        "group_rates": {
            f: {g: group_changes[f][g] / (n * rounds / 100) for g, n in sorted(group_sizes[f].items())}
            for f in GROUP_FIELDS
        },
        "group_sizes": {f: dict(sorted(v.items())) for f, v in group_sizes.items()},
    }
