"""Unit tests for the Track C certificate machinery.

These run against synthetic games with KNOWN values, before any Iron Bottom
Sound data is touched.  If any of these fail, the C0 results are unusable.

    PYTHONPATH=backend/src:research/m0 .venv/bin/python -m pytest \
        research/m0/c0_psro/tests -q
"""

from __future__ import annotations

import math
import random

import pytest

from c0_psro.certs import (certificate, game_value, intervals, run_sampling,
                           true_value_matrix)


def test_game_value_known_matrices():
    # matching pennies
    assert game_value([[1.0, -1.0], [-1.0, 1.0]]) == pytest.approx(0.0, abs=1e-9)
    # row-dominant game: value = max over rows of min over cols
    assert game_value([[1.0, 0.0], [0.5, 0.5]]) == pytest.approx(0.5, abs=1e-9)
    # pure saddle
    assert game_value([[3.0, 2.0], [1.0, 0.0]]) == pytest.approx(1.0, abs=1e-9)
    # constant matrix
    assert game_value([[0.3, 0.3], [0.3, 0.3]]) == pytest.approx(0.3, abs=1e-9)


def test_interval_shrinks_monotonically_with_n():
    counts = {(0, 0): [0, 0, 0], (0, 1): [0, 0, 0]}
    prev = None
    for n in (1, 2, 4, 8, 16, 64, 256):
        counts[(0, 0)] = [n // 2, 0, n - n // 2]
        counts[(0, 1)] = [n // 2, 0, n - n // 2]
        iv = intervals(counts, 0.05)
        w = iv[(0, 0)][1] - iv[(0, 0)][0]
        if prev is not None:
            assert w <= prev + 1e-12
        prev = w


def test_certificate_brackets_true_value():
    """With enough samples per cell, v_L <= v* <= v_U must hold."""
    rng = random.Random(7)
    # a 3x3 game with known cell means
    means = [[0.6, -0.2, 0.1], [-0.4, 0.3, 0.0], [0.2, -0.1, -0.5]]
    truth = [[(1 + m) / 2, 0.0, (1 - m) / 2] for row in means for m in row]
    dist = [[((1 + m) / 2, 0.0, (1 - m) / 2) for m in row] for row in means]
    v_star = game_value(true_value_matrix(dist))
    counts = {}
    for i in range(3):
        for j in range(3):
            pw, pd, pl = dist[i][j]
            n = 2000
            w = sum(1 for _ in range(n) if rng.random() < pw)
            l = sum(1 for _ in range(n - w) if rng.random() < pl / max(1e-9, 1 - pw))
            counts[(i, j)] = [w, 0, l]
    v_l, v_u, _ = certificate(counts, 0.05, (3, 3))
    assert v_l <= v_star + 1e-9, (v_l, v_star)
    assert v_u >= v_star - 1e-9, (v_u, v_star)


def test_widening_a_cell_never_shrinks_the_certificate():
    rng = random.Random(3)
    shape = (3, 3)
    counts = {}
    for i in range(3):
        for j in range(3):
            n = rng.randrange(50, 300)
            counts[(i, j)] = [rng.randrange(0, n), 0, 0]
            counts[(i, j)][2] = n - counts[(i, j)][0]
    base = certificate(counts, 0.05, shape)[2]
    # widen one cell arbitrarily (drop its n)
    key = (1, 1)
    saved = counts[key]
    counts[key] = [saved[0] // 4, 0, saved[2] // 4]
    wider = certificate(counts, 0.05, shape)[2]
    assert wider >= base - 1e-12
    counts[key] = saved
    # shrinking that same cell must not increase the width
    counts[key] = [saved[0] * 4, 0, saved[2] * 4]
    tighter = certificate(counts, 0.05, shape)[2]
    assert tighter <= base + 1e-12


def test_coverage_monte_carlo():
    """Empirical coverage of the simultaneous bracket must be >= 1 - alpha."""
    rng = random.Random(11)
    means = [[0.4, -0.3], [-0.1, 0.2]]
    dist = [[((1 + m) / 2, 0.0, (1 - m) / 2) for m in row] for row in means]
    v_star = game_value(true_value_matrix(dist))
    alpha = 0.05
    n_seeds = 300
    hits = 0
    n_per_cell = 150
    for s in range(n_seeds):
        r = random.Random(1000 + s)
        counts = {}
        for i in range(2):
            for j in range(2):
                pw, _pd, pl = dist[i][j]
                w = sum(1 for _ in range(n_per_cell) if r.random() < pw)
                l = sum(1 for _ in range(n_per_cell - w) if r.random() < pl / max(1e-9, 1 - pw))
                counts[(i, j)] = [w, 0, l]
        v_l, v_u, _ = certificate(counts, alpha, (2, 2))
        if v_l <= v_star + 1e-12 and v_u >= v_star - 1e-12:
            hits += 1
    coverage = hits / n_seeds
    assert coverage >= 1 - alpha, f"coverage {coverage:.3f} < {1 - alpha}"


def test_sampling_loop_runs_and_terminates():
    dist = [[(0.8, 0.1, 0.1), (0.2, 0.2, 0.6)],
            [(0.3, 0.2, 0.5), (0.45, 0.1, 0.45)]]
    res = run_sampling(dist, "uniform", target=0.6, alpha=0.05,
                       max_samples=2000, seed=1, batch=10)
    assert res["reached"]
    assert res["samples"] >= 10
    # NOTE: the certificate width is NOT monotone along a trajectory.  Hoeffding
    # intervals are not nested (the centre moves with the sample mean), so
    # v_U - v_L can briefly widen.  The invariants that DO hold are asserted
    # elsewhere: per-cell half-width shrinks with n at fixed mean, and widening
    # one cell's interval can never shrink the certificate.  Here we only assert
    # the overall contraction over a large sample increase.
    hist = res["history"]
    assert hist[-1][1] < hist[0][1]
    assert res["width"] <= 0.6 + 1e-9
