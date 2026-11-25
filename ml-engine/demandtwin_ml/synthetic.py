"""Development-only choice panels with known, seeded utilities."""
import numpy as np

from .choice import Observation, SEGMENTS, design


def candidates():
    return [
        [
            {"name": "Millet crisps", "price": price, "grams": size, "flavour": flavour,
             "packaging": pack, "positioning": positioning},
            {"name": "Masala crackers", "price": price + 5, "grams": 50, "flavour": "classic",
             "packaging": "standard", "positioning": "standard"},
        ]
        for price in (15, 20, 30, 40, 50)
        for size, flavour, pack, positioning in ((40, "classic", "standard", "standard"),
                                                (60, "spicy", "resealable", "premium"))
    ]


def sample(seed=42, people=90):
    rng = np.random.default_rng(seed)
    rows = []
    options = candidates()
    for person in range(people):
        segment = person % len(SEGMENTS)
        beta = np.array([0.6, -2.4 + 0.65 * segment, 0.7, 0.25, 0.2, -0.3 + segment * 0.25])
        beta += rng.normal(0, 0.24, len(beta))
        for idx in rng.choice(len(options), size=6, replace=False):
            alternatives = options[idx]
            chosen = int(np.argmax(design(alternatives) @ beta + rng.gumbel(size=len(alternatives) + 1)))
            rows.append(Observation(f"synthetic-{seed}-{person}", SEGMENTS[segment], alternatives, chosen))
    return rows
