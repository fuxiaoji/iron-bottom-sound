"""Certificate machinery for Track C: interval payoff matrices and game values.

Everything statistical lives here so it can be unit-tested against synthetic
games with known values before it is allowed near Iron Bottom Sound data.

Model
-----
* meta-game payoff cell (i, j): axis strategy i vs allies strategy j;
* utility is win/draw/loss from the AXIS perspective: +1 / 0 / -1;
* each cell holds counts [n_win, n_draw, n_loss];
* a simultaneous confidence interval per cell comes from Hoeffding
  (values lie in [-1, 1], so the range is 2) plus a union correction over all
  cells: delta = alpha / n_cells;
* the zero-sum game value is bracketed by
      v_L = value(L),  v_U = value(U),   value(A) = max_p min_q  p^T A q,
  which is monotone in the matrix entries, so L <= M <= U implies the bracket;
* the certificate width is v_U - v_L.

Scope: Hoeffding is deliberately loose (it ignores variance).  The plan says to
verify coverage with a simple, trustworthy bound first; tighter bounds
(empirical Bernstein, confidence sequences) are a later optimisation, not part
of this checkpoint.
"""

from __future__ import annotations

import math
import random

from scipy.optimize import linprog

VALUE_RANGE = 2.0  # utilities in [-1, 1]


def half_width(n: int, delta: float) -> float:
    if n <= 0:
        return VALUE_RANGE / 2.0
    return math.sqrt(2.0 * math.log(2.0 / delta) / n)


def intervals(counts: dict, alpha: float) -> dict:
    """Hoeffding + union simultaneous CI per cell."""
    n_cells = len(counts)
    delta = alpha / n_cells
    out = {}
    for key, (w, d, l) in counts.items():
        n = w + d + l
        if n <= 0:
            out[key] = (-1.0, 1.0)
        else:
            mean = (w - l) / n
            hw = half_width(n, delta)
            out[key] = (max(-1.0, mean - hw), min(1.0, mean + hw))
    return out


def game_value(A: list[list[float]]) -> float:
    """max_p min_j (p^T A)_j via LP (row player = axis, maximin)."""
    m = len(A)
    ncol = len(A[0]) if m else 0
    c = [0.0] * m + [-1.0]
    A_ub, b_ub = [], []
    for j in range(ncol):
        A_ub.append([-A[i][j] for i in range(m)] + [1.0])
        b_ub.append(0.0)
    A_eq = [[1.0] * m + [0.0]]
    b_eq = [1.0]
    bounds = [(0.0, 1.0)] * m + [(-1.0, 1.0)]
    res = linprog(c, A_ub=A_ub, b_ub=b_ub, A_eq=A_eq, b_eq=b_eq,
                  bounds=bounds, method="highs")
    if not res.success:
        raise RuntimeError(f"LP failed: {res.message}")
    return float(-res.fun)


def certificate(counts: dict, alpha: float, shape: tuple[int, int]):
    IV = intervals(counts, alpha)
    L = [[IV[(i, j)][0] for j in range(shape[1])] for i in range(shape[0])]
    U = [[IV[(i, j)][1] for j in range(shape[1])] for i in range(shape[0])]
    v_l = game_value(L)
    v_u = game_value(U)
    return v_l, v_u, v_u - v_l


def _norm(v: list[float]) -> list[float]:
    s = sum(v)
    if s <= 0:
        return [1.0 / len(v)] * len(v)
    return [x / s for x in v]


def regret_matching(M: list[list[float]], iterations: int = 2000) -> list[float]:
    """Maximin strategy for the row player via regret matching (zero-sum)."""
    m = len(M)
    ncol = len(M[0])
    regrets = [0.0] * m
    strategy_sum = [0.0] * m
    for _ in range(iterations):
        p = _norm([max(r, 0.0) for r in regrets])
        col_vals = [sum(p[i] * M[i][j] for i in range(m)) for j in range(ncol)]
        j = min(range(ncol), key=lambda jj: col_vals[jj])
        for i in range(m):
            regrets[i] += M[i][j] - col_vals[j]
        for i in range(m):
            strategy_sum[i] += p[i]
    return _norm(strategy_sum)


# --------------------------------------------------------------------------
# Sampling policies
# --------------------------------------------------------------------------

def _mid_matrix(IV: dict, shape):
    return [[(IV[(i, j)][0] + IV[(i, j)][1]) / 2.0 for j in range(shape[1])]
            for i in range(shape[0])]


def _std(w: int, d: int, l: int) -> float:
    n = w + d + l
    if n <= 1:
        return 1.0
    mean = (w - l) / n
    var = (w * (1 - mean) ** 2 + d * (0 - mean) ** 2 + l * (-1 - mean) ** 2) / n
    return math.sqrt(var)


def select_cell(policy: str, counts: dict, alpha: float, shape,
                rng: random.Random | None = None, step: int = 0):
    keys = sorted(counts)
    IV = intervals(counts, alpha)

    if policy == "uniform":
        return keys[(step - 1) % len(keys)]

    if policy == "largest_width":
        return max(keys, key=lambda k: IV[k][1] - IV[k][0])

    if policy == "variance_aware":
        # expected width reduction ~ std / sqrt(n): pick the cell where one more
        # sample buys the most under a normal approximation
        def score(k):
            w, d, l = counts[k]
            n = w + d + l
            return _std(w, d, l) / math.sqrt(n + 1)
        return max(keys, key=score)

    if policy == "support_weighted":
        M = _mid_matrix(IV, shape)
        p = regret_matching(M)
        ncol = shape[1]
        col_vals = [sum(p[i] * M[i][j] for i in range(shape[0])) for j in range(ncol)]
        best = min(col_vals)
        br_cols = [j for j in range(ncol) if col_vals[j] <= best + 1e-9]
        weights = {k: 0.0 for k in keys}
        for i, pi in enumerate(p):
            if pi <= 0:
                continue
            for j in br_cols:
                weights[(i, j)] = pi / len(br_cols)
        live = {k: v for k, v in weights.items() if v > 0}
        if not live:
            return keys[(step - 1) % len(keys)]
        if rng is not None:
            r = rng.random()
            acc = 0.0
            for k, v in live.items():
                acc += v
                if r <= acc:
                    return k
        return max(live, key=live.get)

    if policy == "cert_sensitivity":
        # candidate: if cell k's interval were halved around its current mean,
        # how much would the certificate width shrink?  Pick the argmin width.
        unsampled = [k for k in keys if sum(counts[k]) <= 0]
        if unsampled:
            # an unsampled cell sits at the full interval (-1, 1); resolving it
            # is the largest possible width reduction, so take one first.  (A
            # pseudo-count trial here would still clamp to the full interval
            # under Hoeffding and score it as useless - fixed after the first
            # run deadlocked at width 2.0 with unsampled cells forever.)
            return unsampled[0]
        best_key, best_w = None, None
        for k in keys:
            w, d, l = counts[k]
            n = w + d + l
            if False:
                pass
            else:
                mean = (w - l) / n
                hw = (IV[k][1] - IV[k][0]) / 4.0  # halve the width
                lo = max(-1.0, mean - hw)
                hi = min(1.0, mean + hw)
                trial = dict(counts)
                # encode the trial interval as fake counts with the right mean
                # and a Hoeffding half-width equal to hw: n' = 2 ln(2/delta)/hw^2
                n_cells = len(counts)
                delta = alpha / n_cells
                n_prime = max(1, int(2.0 * math.log(2.0 / delta) / (hw * hw))) if hw > 0 else 10 ** 9
                n_win = n_prime * (1 + mean) / 2
                n_loss = n_prime * (1 - mean) / 2
                trial[k] = [round(n_win), 0, round(n_loss)]
                cand = certificate(trial, alpha, shape)[2]
            if best_w is None or cand < best_w:
                best_key, best_w = k, cand
        return best_key

    raise ValueError(f"unknown policy {policy}")


POLICIES = ("uniform", "largest_width", "variance_aware", "support_weighted",
            "cert_sensitivity")


# --------------------------------------------------------------------------
# Sampling loop (calibrated simulator)
# --------------------------------------------------------------------------

def run_sampling(dist: list[list[tuple[float, float, float]]],
                 policy: str, *, target: float, alpha: float,
                 max_samples: int, seed: int, batch: int = 25,
                 eval_every_batch: int = 1):
    """Run one sampling trajectory against a calibrated outcome distribution.

    ``dist[i][j] = (p_win, p_draw, p_loss)`` is the *true* generating
    distribution of cell (i, j); each simulated "match" draws one outcome from
    it.  The certificate machinery never sees ``dist`` — only the counts.
    """
    rng = random.Random(seed)
    shape = (len(dist), len(dist[0]))
    keys = [(i, j) for i in range(shape[0]) for j in range(shape[1])]
    counts = {k: [0, 0, 0] for k in keys}
    history: list[tuple[int, float]] = []
    step = 0
    batch_no = 0
    n_batches = max_samples // batch
    while step < max_samples:
        batch_no += 1
        cell = select_cell(policy, counts, alpha, shape, rng=rng, step=batch_no)
        pw, pd_, pl = dist[cell[0]][cell[1]]
        for _ in range(batch):
            r = rng.random()
            outcome = 0 if r < pw else (1 if r < pw + pd_ else 2)
            counts[cell][outcome] += 1
            step += 1
        v_l, v_u, width = certificate(counts, alpha, shape)
        history.append((step, width))
        if width <= target:
            return {"reached": True, "samples": step, "width": width,
                    "history": history}
    v_l, v_u, width = certificate(counts, alpha, shape)
    return {"reached": False, "samples": None, "width": width,
            "history": history}


def true_value_matrix(dist) -> list[list[float]]:
    return [[pw - pl for (pw, _pd, pl) in row] for row in dist]
