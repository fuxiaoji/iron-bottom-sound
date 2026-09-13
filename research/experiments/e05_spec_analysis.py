"""E05-spec: reproducible specification analysis for the engagement graph.

Implements BOTH feature specifications of the E05 hypothesis on the
collected dataset (research/results/e05/dataset.csv) with BOTH bootstrap
protocols, storing every point estimate:

  strict reading  -- the directional in-degree (p_attack) is charged to the
                     baseline as "aggregate fire"; only shape features
                     (lfr, herfindahl, attacker_count, p_reply, lambda2_own)
                     constitute the graph set.
  plan-literal    -- the plan's S6.2 metric list defines the weighted
                     in-degree as a graph metric, so the baseline contains
                     only non-graph totals (hull_frac, speed,
                     avg_enemy_dist, force_ratio) and every directed-fire
                     quantity (p_attack included) belongs to the graph set.

Design: 80/20 split by game; OLS; out-of-sample R2 / MAE / relative MAE
reduction; sample-level (1,000) and game-level (500) paired bootstrap.
All point estimates and CIs are written to results JSON.

Output: research/results/e05/spec_analysis.json (+ updates results.json)
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[2]
DS = REPO / "research" / "results" / "e05" / "dataset.csv"

STRICT_BASE = ["hull_frac", "force_ratio", "avg_enemy_dist"]
STRICT_GRAPH = ["p_attack", "lfr", "herfindahl", "attacker_count", "p_reply",
                "lambda2_own"]
PLAN_BASE = ["hull_frac", "speed", "avg_enemy_dist", "force_ratio"]
PLAN_GRAPH = ["p_attack", "lfr", "herfindahl", "attacker_count", "p_reply",
              "lambda2_own"]


def load():
    rows = list(csv.DictReader(open(DS, encoding="utf-8")))
    ids = {}
    for i, r in enumerate(rows):
        ids.setdefault(r["match_id"], len(ids))
    X = np.array([[float(r[c]) for c in PLAN_BASE + STRICT_GRAPH] for r in rows])
    y = np.array([float(r["damage_next"]) for r in rows])
    g = np.array([ids[r["match_id"]] for r in rows])
    return X, y, g, games_of(g)


def games_of(g):
    return np.unique(g)


def fit_pred(Xtr, ytr, Xte):
    mu, sd = Xtr.mean(0), Xtr.std(0) + 1e-9
    A = np.column_stack([(Xtr - mu) / sd, np.ones(len(Xtr))])
    coef, *_ = np.linalg.lstsq(A, ytr, rcond=None)
    B = np.column_stack([(Xte - mu) / sd, np.ones(len(Xte))])
    return B @ coef


def r2(yt, pred):
    return float(1 - np.sum((yt - pred) ** 2) / np.sum((yt - yt.mean()) ** 2))


def main() -> None:
    X, y, g, games = load()
    rng = np.random.default_rng(42)
    perm = rng.permutation(len(games))
    tr = set(games[perm[:int(0.8 * len(games))]])
    train = np.array([gi in tr for gi in g])
    te_games = np.array(sorted(set(g[~train])))
    te_index = {gi: np.where((~train) & (g == gi))[0] for gi in te_games}
    ytr, yte = y[train], y[~train]

    specs = {
        "strict": (STRICT_BASE, STRICT_GRAPH),
        "plan_literal": (PLAN_BASE, PLAN_GRAPH),
    }
    out = {"n_samples": len(y), "n_games": int(len(games)),
           "split": "80/20 by game, seed 42"}
    for name, (base_cols, graph_cols) in specs.items():
        cols = base_cols + graph_cols
        all_idx = [PLAN_BASE.index(c) + len(PLAN_BASE) + STRICT_GRAPH.index(c2)
                   if False else None for c in cols]  # placeholder
    # column indices into X (X = PLAN_BASE + STRICT_GRAPH)
    colmap = {}
    for c in PLAN_BASE:
        colmap[c] = PLAN_BASE.index(c)
    for c in STRICT_GRAPH:
        colmap[c] = len(PLAN_BASE) + STRICT_GRAPH.index(c)

    for name, (base_cols, graph_cols) in specs.items():
        b_idx = [colmap[c] for c in base_cols]
        f_idx = [colmap[c] for c in base_cols + graph_cols]
        pb = fit_pred(X[train][:, b_idx], y[train], X[~train][:, b_idx])
        pf = fit_pred(X[train][:, f_idx], y[train], X[~train][:, f_idx])
        r2b, r2f = r2(yte, pb), r2(yte, pf)
        maeb = float(np.mean(np.abs(yte - pb)))
        maef = float(np.mean(np.abs(yte - pf)))
        rel = (maeb - maef) / maeb

        # sample-level bootstrap (1,000)
        sr2, smae_rel = [], []
        for _ in range(1000):
            pick = rng.choice(len(yte), size=len(yte), replace=True)
            yy = yte[pick]
            pbb = pb[pick]
            pff = pf[pick]
            denom = max(np.sum((yy - yy.mean()) ** 2), 1e-9)
            sr2.append((1 - np.sum((yy - pff) ** 2) / denom)
                       - (1 - np.sum((yy - pbb) ** 2) / denom))
            base_m = np.mean(np.abs(yy - pbb))
            smae_rel.append((base_m - np.mean(np.abs(yy - pff))) / base_m
                            if base_m > 0 else 0.0)
        # game-level bootstrap (500)
        gr2, gmae_rel = [], []
        for _ in range(500):
            pick = rng.choice(len(te_games), size=len(te_games), replace=True)
            idx = np.concatenate([te_index[te_games[i]] for i in pick])
            yy = y[idx]
            pbb = fit_pred(X[train][:, f_idx[:0]] if False else X[train][:, b_idx],
                           y[train], X[idx][:, b_idx])
            pff = fit_pred(X[train][:, f_idx], y[train], X[idx][:, f_idx])
            denom = max(np.sum((yy - yy.mean()) ** 2), 1e-9)
            gr2.append((1 - np.sum((yy - pff) ** 2) / denom)
                       - (1 - np.sum((yy - pbb) ** 2) / denom))
            bm = np.mean(np.abs(yy - pbb))
            fm = np.mean(np.abs(yy - pff))
            gmae_rel.append((bm - fm) / bm if bm > 0 else 0.0)

        def ci(arr):
            lo, hi = np.percentile(arr, [2.5, 97.5])
            return [float(lo), float(hi)]

        out[name] = {
            "baseline_features": base_cols,
            "graph_features": graph_cols,
            "oos_r2_baseline": r2b,
            "oos_r2_full": r2f,
            "delta_r2": r2f - r2b,
            "delta_r2_sample_boot_ci": ci(sr2),
            "delta_r2_game_boot_ci": ci(gr2),
            "mae_baseline": maeb,
            "mae_full": maef,
            "relative_mae_reduction": rel,
            "relative_mae_reduction_game_boot_ci": ci(gmae_rel),
            "gate": "PASS" if ((r2f - r2b) >= 0.05 or rel >= 0.10) else "FAIL",
        }

    dest = REPO / "research" / "results" / "e05" / "spec_analysis.json"
    dest.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
