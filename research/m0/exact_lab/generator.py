"""Random sealed-commitment game generator.

Discovery and confirmatory pools must come from *different* generator seeds and
must differ in distribution — the confirmatory pool deliberately includes a
payoff family and a horizon the discovery pool never saw, so that a result which
only holds on the discovery grid is visible as such.
"""

from __future__ import annotations

import random

from .core import FAMILIES, GameSpec

DISCOVERY_FAMILIES = ("coordination", "anticor", "delayed")
DISCOVERY_HORIZONS = (3, 4, 5)
# confirmatory: one family and one horizon never used in discovery
CONFIRMATORY_FAMILIES = ("coordination", "anticor", "delayed", "pathdep")
CONFIRMATORY_HORIZONS = (3, 4, 5, 6)


def generate(count: int, seed: int, *, split: str = "discovery") -> list[GameSpec]:
    rng = random.Random(seed)
    families = DISCOVERY_FAMILIES if split == "discovery" else CONFIRMATORY_FAMILIES
    horizons = DISCOVERY_HORIZONS if split == "discovery" else CONFIRMATORY_HORIZONS
    out: list[GameSpec] = []
    seen: set[tuple] = set()
    guard = 0
    while len(out) < count and guard < count * 200:
        guard += 1
        T = rng.choice(horizons)
        b = rng.choice((2, 3))
        K = rng.choice((2, 3))
        m = rng.choice((2,))
        L = rng.choice([x for x in (2, 3) if x <= T])
        fam = rng.choice(families)
        key = (T, b, K, m, L, fam)
        if key in seen and len(seen) < 40:
            continue
        seen.add(key)
        out.append(GameSpec(name=f"{split}_{len(out):04d}_T{T}b{b}K{K}L{L}_{fam}",
                            T=T, b=b, K=K, m=m, L=L, family=fam, seed=rng.randrange(10**6)))
    return out


def grid(split: str = "discovery") -> list[GameSpec]:
    """A small deterministic grid, so the census has full coverage of the knobs
    rather than relying on random draws."""
    families = DISCOVERY_FAMILIES if split == "discovery" else CONFIRMATORY_FAMILIES
    horizons = (3, 4, 5) if split == "discovery" else (4, 5, 6)
    specs = []
    for fam in families:
        for T in horizons:
            for b in (2, 3):
                for K in (2, 3):
                    for L in (2, 3):
                        if L > T:
                            continue
                        specs.append(GameSpec(
                            name=f"{split}_grid_T{T}b{b}K{K}L{L}_{fam}",
                            T=T, b=b, K=K, m=2, L=L, family=fam, seed=11, alpha=1))
    # controls always present
    specs.append(GameSpec(name="control_markov", T=4, b=2, K=1, m=2, L=2,
                          family="null", seed=11, alpha=1))
    specs.append(GameSpec(name="control_negative", T=4, b=2, K=3, m=2, L=2,
                          family="null", seed=11, alpha=1))
    if split != "discovery":
        specs.append(GameSpec(name="confirm_pathdep_T6", T=6, b=3, K=3, m=2, L=3,
                              family="pathdep", seed=11, alpha=1))
    return specs
