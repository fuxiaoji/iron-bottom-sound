"""B2: Path-integrated Exposure Objective validation (v4.0 batch B2).

B2.1  Snapshot vs Integral objective.  For the same batch of candidate
      trajectories (11x11 committed-plan-pair rollouts, same machinery as
      E02) compare three objective functionals of the per-step fire
      differential L(t) = K_B(t) - lambda*K_R(t):
        integral   J   = sum_t gamma^t L(t)        (paper main model)
        snapshot_T     = L(s_T)                    (terminal geometry)
        snapshot_peak  = max_t L(t)                (crossing-the-T spike)
      Outputs: plan-ranking correlations (Kendall tau / Spearman over the
      121 payoff entries and over the 11 worst-case plan values), pure
      maximin/minimax plan changes, LP mixed-strategy support overlap, the
      fire_after_move timing contrast (B0 audit fix), Table 3 data, and the
      A/B counterexample search (peak_A > peak_B  but  J_A < J_B).

B2.2  Fleet exposure heat map.  Two-ship line-ahead column, continuous
      approximation: ship length 3 cells, 4 discrete segments along the
      heading per ship, each segment a KernelWrap.fire source.  F_B(x,t) =
      total expected hits the column delivers to a neutral (speed 4)
      broadside target at x at time t.  Static t=0 field, dynamic frames
      t in {0, T/2, T}, and center-vs-flank density profiles along and
      across the column, with denoised (smoothed) profiles.

Outputs under research/results/b2/ (see report.md for the 22-item batch
protocol).  Deterministic: no RNG anywhere in this script.
"""
from __future__ import annotations

import json
import math
import sys
from itertools import combinations
from pathlib import Path

import numpy as np
from scipy import stats

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "backend" / "src"))
sys.path.insert(0, str(REPO))

from research.geometry.firepower_kernel import KernelFit  # noqa: E402
from research.geometry.committed_game import (  # noqa: E402
    KernelWrap,
    make_maneuver_library,
    open_loop_minimax,
    simulate,
    solve_matrix_game,
)

OUT = REPO / "research" / "results" / "b2"

# ---- B2.1 parameters (aligned with the E02 baseline cell: eta_r = eta_g = 1,
#      CA-class kernel on both sides, r0 = 16, steps = 40, gamma = 0.96) ----
ETA_V = [0.80, 1.00, 1.25]
GEOMETRIES = {
    # name: (bearing of R from B at t0, heading B, heading R)
    "head_on": (0.0, 0.0, 180.0),
    "parallel": (90.0, 0.0, 0.0),
    "crossing": (45.0, 0.0, 180.0),
}
R0 = 16.0
STEPS = 40
GAMMA = 0.96
KERNEL_CLASS = "CA"
OBJ_NAMES = ("integral", "snapshot_T", "snapshot_peak")


# --------------------------------------------------------------------------
# B2.1 helpers
# --------------------------------------------------------------------------
def rollouts(kB, kR, lib, brg, hB, hR, vB, fire_after_move, vR=6.0):
    """All 121 plan-pair rollouts; return L-series matrix (11, 11, steps)."""
    plans = list(lib.keys())
    L = np.zeros((len(plans), len(plans), STEPS))
    for i, pb in enumerate(plans):
        for j, pr in enumerate(plans):
            out = simulate(kB, kR, lib[pb], lib[pr], R0, brg, hB, hR,
                           vB, 6.0, STEPS, GAMMA, fire_after_move=fire_after_move)
            L[i, j] = [p["L"] for p in out["trajectory"]]
    return np.asarray(plans), L


def objective_matrices(L):
    """Three payoff matrices from the per-step L(t) tensor."""
    disc = GAMMA ** np.arange(STEPS)
    return {
        "integral": (disc[None, None, :] * L).sum(axis=2),
        "snapshot_T": L[:, :, -1].copy(),
        "snapshot_peak": L.max(axis=2),
    }


def rank_corr(a, b):
    tau = stats.kendalltau(a, b)
    rho = stats.spearmanr(a, b)
    return {"kendall_tau": float(tau.statistic), "kendall_p": float(tau.pvalue),
            "spearman_rho": float(rho.statistic), "spearman_p": float(rho.pvalue)}


def game_summary(pay, plans):
    """Pure maximin / minimax picks + LP mixed strategy for one matrix."""
    bi = int(np.argmax(pay.min(axis=1)))
    rj = int(np.argmin(pay.max(axis=0)))
    game = solve_matrix_game(pay)
    supp = [] if game["x"] is None else [plans[i] for i, xi in enumerate(game["x"])
                                         if xi > 1e-9]
    return {"maximin_plan_B": plans[bi], "minimax_plan_R": plans[rj],
            "pure_value": float(pay[bi].min()),
            "game_value": game["value"], "pure_fallback": game["pure"],
            "lp_support_B": supp}


def support_jaccard(a, b):
    sa, sb = set(a), set(b)
    if not sa and not sb:
        return 1.0
    return len(sa & sb) / max(len(sa | sb), 1)


def search_AB(cell_name, plans, L, mats):
    """Search real rollout pairs with peak_A > peak_B but integral_A < integral_B.

    Both trajectories come from the SAME cell (same initial geometry and
    parameters), so the comparison is controlled.  Score = the smaller of the
    two margins; the reported example maximizes it.
    """
    P = mats["snapshot_peak"]
    J = mats["integral"]
    best = None
    n_same_planB = 0
    for (i, j), (k, l) in combinations(((a, b) for a in range(11) for b in range(11)), 2):
        pA, pB_ = P[i, j], P[k, l]
        jA, jB_ = J[i, j], J[k, l]
        # canonical orientation: A = higher peak, lower integral
        if pA <= pB_ or jA >= jB_:
            pA, pB_, jA, jB_ = pB_, pA, jB_, jA
            i, j, k, l = k, l, i, j
        if pA <= pB_ or jA >= jB_:
            continue
        score = min(pA - pB_, jB_ - jA)
        if best is None or score > best["score"]:
            best = {
                "score": float(score),
                "A": {"plan_B": plans[i], "plan_R": plans[j], "i": i, "j": j,
                      "peak": float(pA), "integral": float(jA),
                      "t_peak": int(np.argmax(L[i, j])),
                      "frac_L_positive": float((L[i, j] > 0).mean()),
                      "L_series": [round(float(x), 4) for x in L[i, j]]},
                "B": {"plan_B": plans[k], "plan_R": plans[l], "i": k, "j": l,
                      "peak": float(pB_), "integral": float(jB_),
                      "t_peak": int(np.argmax(L[k, l])),
                      "frac_L_positive": float((L[k, l] > 0).mean()),
                      "L_series": [round(float(x), 4) for x in L[k, l]]},
                "same_planB": (plans[i] == plans[k]),
            }
    # count same-B-plan pairs (independent evidence, not the chosen example)
    for i in range(11):
        for j, l in combinations(range(11), 2):
            for (ja, jb) in ((j, l), (l, j)):
                if P[i, ja] > P[i, jb] and J[i, ja] < J[i, jb]:
                    n_same_planB += 1
    return best, n_same_planB


def synthetic_AB_search(kB, kR):
    """Fallback: manual heading-sequence search over a denser rate family."""
    lib = {}
    for rate in range(-90, 91, 15):
        name = f"syn{rate:+d}"
        lib[name] = [float(rate)] * 3 + [0.0] * (STEPS - 3)
    for rate in (-90, -60, 60, 90):  # turn-out-then-back family
        for back in (60, 90, 120):
            lib[f"syn{rate:+d}back{back:+d}"] = ([float(rate)] * 3
                                                 + [float(-math.copysign(back, rate))]
                                                 + [0.0] * (STEPS - 4))
    plans = list(lib.keys())
    brg, hB, hR = GEOMETRIES["crossing"]
    _, L = rollouts(kB, kR, lib, brg, hB, hR, 4.8, False)
    mats = objective_matrices(L)
    best, n_same = search_AB("synthetic_crossing", plans, L, mats)
    return best, n_same, len(plans)


# --------------------------------------------------------------------------
# B2.2 helpers
# --------------------------------------------------------------------------
def fleet_sources(ship_centers, heading_deg, ship_len=3.0, n_seg=4):
    """Segment-centre fire sources for a line-ahead column."""
    offs = np.linspace(-ship_len / 2 + ship_len / (2 * n_seg),
                       ship_len / 2 - ship_len / (2 * n_seg), n_seg)
    h = math.radians(heading_deg)
    ux, uy = math.cos(h), math.sin(h)
    return [(cx + o * ux, cy + o * uy, heading_deg)
            for (cx, cy) in ship_centers for o in offs]


def field_F(kwrap: KernelWrap, sources, X, Y, target_speed=4,
            target_aspect="broadside"):
    """F_B(x) = sum of expected hits over segment sources (vectorized by sector).

    Exact equivalent of looping KernelWrap.fire over grid points: the kernel
    depends on delta_deg only through its sector, so we mask points per sector
    and use the vectorized evaluator.  Range is clipped to [1, 24] exactly as
    KernelWrap.fire does.  X, Y may be 1-D (profiles) or 2-D (heat maps).
    """
    Xf = np.asarray(X, dtype=float)
    Yf = np.asarray(Y, dtype=float)
    F = np.zeros_like(Xf)
    for (sx, sy, sh) in sources:
        dx, dy = Xf - sx, Yf - sy
        r = np.clip(np.hypot(dx, dy), 1.0, 24.0)
        a = (np.degrees(np.arctan2(dy, dx)) - sh + 180.0) % 360.0 - 180.0
        masks = ((a >= -30.0) & (a <= 30.0),                 # bow
                 (a > 30.0) & (a <= 150.0),                  # starboard
                 (a < -30.0) & (a >= -150.0),                # port
                 (a < -150.0) | (a > 150.0))                 # stern
        for m in masks:
            if m.any():
                F[m] += kwrap.eta_g * kwrap.fit.expected_hits_array(
                    r[m], 0.0, target_speed, target_aspect)
    return F


def smooth(y, k=5):
    """Simple centred moving average (denoising for profile output)."""
    pad = np.r_[np.full(k // 2, y[0]), y, np.full(k - k // 2 - 1, y[-1])]
    return np.convolve(pad, np.ones(k) / k, mode="valid")


# --------------------------------------------------------------------------
# main
# --------------------------------------------------------------------------
def main() -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    OUT.mkdir(parents=True, exist_ok=True)
    fits = json.load(open(REPO / "research" / "results" / "e01" / "kernel_fits.json"))
    base_fit = KernelFit.from_dict(fits[KERNEL_CLASS])
    lib = make_maneuver_library()
    plans = list(lib.keys())

    # ================= B2.1 =================
    cells, table3, ab_pool = [], [], {}
    for eta_v in ETA_V:
        kB = KernelWrap(base_fit, 1.0, 1.0)
        kR = KernelWrap(base_fit, 1.0, 1.0)
        for gname, (brg, hB, hR) in GEOMETRIES.items():
            vB = 6.0 * eta_v
            cell = {"eta_v": eta_v, "geometry": gname}
            for fam in (False, True):
                _, L = rollouts(kB, kR, lib, brg, hB, hR, vB, fam)
                mats = objective_matrices(L)
                tag = "after" if fam else "before"
                cell[f"matrix_{tag}"] = {k: np.round(v, 5).tolist()
                                         for k, v in mats.items()}
                if not fam:
                    mats_main = mats
                    L_main = L
                else:
                    # timing contrast on the integral objective
                    dJ = mats["integral"] - mats_main["integral"]
                    cell["timing_contrast"] = {
                        "mean_abs_dJ": float(np.abs(dJ).mean()),
                        "max_abs_dJ": float(np.abs(dJ).max()),
                        "sign_flip_frac": float((np.sign(
                            mats["integral"]) != np.sign(
                            mats_main["integral"])).mean()),
                        "maximin_B_before": game_summary(mats_main["integral"], plans)["maximin_plan_B"],
                        "maximin_B_after": game_summary(mats["integral"], plans)["maximin_plan_B"],
                    }
            gs = {o: game_summary(mats_main[o], plans) for o in OBJ_NAMES}
            cell["games"] = gs
            # ranking correlations vs integral
            corr = {}
            for o in ("snapshot_T", "snapshot_peak"):
                corr[o] = {
                    "entry": rank_corr(mats_main["integral"].ravel(),
                                       mats_main[o].ravel()),
                    "planB_worstcase": rank_corr(
                        mats_main["integral"].min(axis=1),
                        mats_main[o].min(axis=1)),
                    "planR_worstcase": rank_corr(
                        mats_main["integral"].max(axis=0),
                        mats_main[o].max(axis=0)),
                }
            cell["ranking_corr_vs_integral"] = corr
            corr_TvP = {
                "entry": rank_corr(mats_main["snapshot_T"].ravel(),
                                   mats_main["snapshot_peak"].ravel()),
            }
            cell["ranking_corr_T_vs_peak"] = corr_TvP

            # worst-case tie structure: snapshot objectives can produce
            # constant (fully tied) worst-case vectors -> maximin degeneracy
            def _nuniq(v):
                return int(len(np.unique(np.round(v, 9))))
            cell["worstcase_tie_structure"] = {
                o: {"planB_n_unique": _nuniq(mats_main[o].min(axis=1)),
                    "planR_n_unique": _nuniq(mats_main[o].max(axis=0)),
                    "planB_worstcase_values": sorted(set(
                        np.round(mats_main[o].min(axis=1), 6).tolist())),
                    "planB_degenerate": _nuniq(mats_main[o].min(axis=1)) == 1}
                for o in OBJ_NAMES}

            # maximin change flags
            cell["maximin_change"] = {
                o: {"maximin_B_changed": gs[o]["maximin_plan_B"] != gs["integral"]["maximin_plan_B"],
                    "minimax_R_changed": gs[o]["minimax_plan_R"] != gs["integral"]["minimax_plan_R"],
                    "lp_support_jaccard": support_jaccard(gs[o]["lp_support_B"],
                                                          gs["integral"]["lp_support_B"]),
                    "lp_support_integral": gs["integral"]["lp_support_B"],
                    "lp_support_" + o: gs[o]["lp_support_B"],
                    "game_value_integral": gs["integral"]["game_value"],
                    "game_value_" + o: gs[o]["game_value"]}
                for o in ("snapshot_T", "snapshot_peak")}
            cells.append(cell)

            # Table 3 rows
            for o in ("snapshot_T", "snapshot_peak"):
                table3.append({
                    "eta_v": eta_v, "geometry": gname, "kernel": KERNEL_CLASS,
                    "objective_pair": f"integral_vs_{o}",
                    "kendall_entry": round(corr[o]["entry"]["kendall_tau"], 4),
                    "spearman_entry": round(corr[o]["entry"]["spearman_rho"], 4),
                    "kendall_planB_worstcase": round(corr[o]["planB_worstcase"]["kendall_tau"], 4),
                    "spearman_planB_worstcase": round(corr[o]["planB_worstcase"]["spearman_rho"], 4),
                    "kendall_planR_worstcase": round(corr[o]["planR_worstcase"]["kendall_tau"], 4),
                    "spearman_planR_worstcase": round(corr[o]["planR_worstcase"]["spearman_rho"], 4),
                    "n_unique_worstcase_B_integral":
                        cell["worstcase_tie_structure"]["integral"]["planB_n_unique"],
                    "n_unique_worstcase_B_snapshot":
                        cell["worstcase_tie_structure"][o]["planB_n_unique"],
                    "snapshot_maximin_degenerate":
                        cell["worstcase_tie_structure"][o]["planB_degenerate"],
                    "maximin_B_integral": gs["integral"]["maximin_plan_B"],
                    "maximin_B_snapshot": gs[o]["maximin_plan_B"],
                    "minimax_R_integral": gs["integral"]["minimax_plan_R"],
                    "minimax_R_snapshot": gs[o]["minimax_plan_R"],
                    "maximin_B_changed": cell["maximin_change"][o]["maximin_B_changed"],
                    "minimax_R_changed": cell["maximin_change"][o]["minimax_R_changed"],
                    "lp_support_jaccard": round(cell["maximin_change"][o]["lp_support_jaccard"], 3),
                })

            # A/B search on the main-timing rollouts
            best, n_same = search_AB(f"{gname}@eta_v{eta_v}", plans, L_main, mats_main)
            if best is not None:
                best["cell"] = {"eta_v": eta_v, "geometry": gname}
                ab_pool[(eta_v, gname)] = best
            print(f"[b2.1] eta_v={eta_v} {gname}: "
                  f"tau_entry={corr['snapshot_peak']['entry']['kendall_tau']:.3f} "
                  f"maximin_B={gs['integral']['maximin_plan_B']}")

    # global A/B pick + fallback synthetic search
    ab_key = max(ab_pool, key=lambda k: ab_pool[k]["score"]) if ab_pool else None
    ab_example = ab_pool[ab_key] if ab_key else None
    ab_source = "real_rollout_pair" if ab_example else None
    if ab_example is None:
        ab_example, _, n_syn = synthetic_AB_search(
            KernelWrap(base_fit, 1.0, 1.0), KernelWrap(base_fit, 1.0, 1.0))
        ab_source = "synthetic_heading_sequences"

    # ---- cross-cell summary (Table 3 headline numbers) ----
    def _pooled(o):
        J = np.concatenate([np.asarray(c["matrix_before"]["integral"]).ravel()
                            for c in cells])
        S = np.concatenate([np.asarray(c["matrix_before"][o]).ravel()
                            for c in cells])
        return rank_corr(J, S)

    summary = {
        "n_cells": len(cells),
        "pooled_entry_corr": {
            "integral_vs_snapshot_T": _pooled("snapshot_T"),
            "integral_vs_snapshot_peak": _pooled("snapshot_peak"),
        },
        "mean_entry_kendall_tau": {
            o: float(np.nanmean([c["ranking_corr_vs_integral"][o]["entry"]["kendall_tau"]
                                 for c in cells]))
            for o in ("snapshot_T", "snapshot_peak")},
        "max_entry_kendall_tau": {
            o: float(np.nanmax([c["ranking_corr_vs_integral"][o]["entry"]["kendall_tau"]
                                for c in cells]))
            for o in ("snapshot_T", "snapshot_peak")},
        "maximin_B_changed_cells": {
            o: int(sum(c["maximin_change"][o]["maximin_B_changed"]
                       for c in cells)) for o in ("snapshot_T", "snapshot_peak")},
        "minimax_R_changed_cells": {
            o: int(sum(c["maximin_change"][o]["minimax_R_changed"]
                       for c in cells)) for o in ("snapshot_T", "snapshot_peak")},
        "lp_support_jaccard_mean": {
            o: float(np.mean([c["maximin_change"][o]["lp_support_jaccard"]
                              for c in cells]))
            for o in ("snapshot_T", "snapshot_peak")},
        "peak_maximin_degenerate_cells": int(sum(
            c["worstcase_tie_structure"]["snapshot_peak"]["planB_degenerate"]
            for c in cells)),
        "gate_tau_ge_095_triggered": False,
        "gate_note": ("max observed entry Kendall tau < 0.95 in every cell: "
                      "snapshot and integral rankings are NOT equivalent; the "
                      "'structural equivalence' report branch does not apply"),
        "timing_contrast": {
            "mean_abs_dJ_mean_over_cells": float(np.mean(
                [c["timing_contrast"]["mean_abs_dJ"] for c in cells])),
            "mean_abs_dJ_max_over_cells": float(np.max(
                [c["timing_contrast"]["mean_abs_dJ"] for c in cells])),
            "sign_flip_frac_max_over_cells": float(np.max(
                [c["timing_contrast"]["sign_flip_frac"] for c in cells])),
            "maximin_B_changed_by_fire_timing": int(sum(
                c["timing_contrast"]["maximin_B_before"]
                != c["timing_contrast"]["maximin_B_after"] for c in cells)),
        },
    }

    # ---- persistence: JSON + CSV ----
    payload = {
        "protocol": "v4.0 batch B2.1",
        "params": {"eta_v": ETA_V, "geometries": GEOMETRIES, "r0": R0,
                   "steps": STEPS, "gamma": GAMMA, "kernel_class": KERNEL_CLASS,
                   "eta_r": 1.0, "eta_g": 1.0, "library": "turn0/+-30/+-60/+-90/+-120/+-180 (11 plans)",
                   "seed": "deterministic (no RNG)"},
        "cells": cells,
        "summary": summary,
        "example_AB": {"source": ab_source, "example": ab_example,
                       "n_cells_with_real_pair": len(ab_pool),
                       "note": "A = higher peak, LOWER integral; B = steady trajectory",
                       "definition": "peak_A > peak_B and integral_A < integral_B, "
                                     "score = min(peak_A-peak_B, integral_B-integral_A)"},
    }
    (OUT / "snapshot_vs_integral.json").write_text(
        json.dumps(payload, indent=1), encoding="utf-8")

    cols = list(table3[0].keys())
    with (OUT / "snapshot_vs_integral.csv").open("w", encoding="utf-8") as fh:
        fh.write(",".join(cols) + "\n")
        for r in table3:
            fh.write(",".join(str(r[c]) for c in cols) + "\n")

    (OUT / "example_AB.json").write_text(
        json.dumps(payload["example_AB"], indent=1), encoding="utf-8")

    # ---- figure: A/B time series ----
    fig, axes = plt.subplots(1, 2, figsize=(11.5, 4.3),
                             gridspec_kw={"width_ratios": [1.25, 1]})
    ax = axes[0]
    t = np.arange(STEPS)
    if ab_example:
        for key, col, lab in (("A", "tab:red", "A (peak T-cross, loses on integral)"),
                              ("B", "tab:blue", "B (steady, wins on integral)")):
            ax.plot(t, ab_example[key]["L_series"], color=col, lw=1.8, label=lab,
                    marker="o", ms=2.5)
        ax.axhline(0, color="k", lw=0.6, ls="--")
        ax.set_xlabel("step t")
        ax.set_ylabel("fire differential L(t)")
        cellname = f"{ab_example['cell']['geometry']}, $\\eta_v$={ab_example['cell']['eta_v']}"
        ax.set_title(f"Counterexample A/B ({cellname})\n"
                     f"A: peak={ab_example['A']['peak']:.2f} J={ab_example['A']['integral']:.2f} | "
                     f"B: peak={ab_example['B']['peak']:.2f} J={ab_example['B']['integral']:.2f}",
                     fontsize=9)
        ax.legend(fontsize=8)
    # ranking scatter panel: integral vs each snapshot (pooled entries)
    ax = axes[1]
    pooled_J, pooled_P = [], []
    for cell in cells:
        J = np.asarray(cell["matrix_before"]["integral"])
        P = np.asarray(cell["matrix_before"]["snapshot_peak"])
        pooled_J.append(J.ravel())
        pooled_P.append(P.ravel())
    pooled_J = np.concatenate(pooled_J)
    pooled_P = np.concatenate(pooled_P)
    ax.scatter(pooled_J, pooled_P, s=6, alpha=0.45, color="tab:purple")
    tau_p = stats.kendalltau(pooled_J, pooled_P).statistic
    rho_p = stats.spearmanr(pooled_J, pooled_P).statistic
    ax.set_xlabel("path-integrated J (paper objective)")
    ax.set_ylabel("snapshot_peak = max_t L(t)")
    ax.set_title(f"Payoff entries pooled over {len(cells)} cells (n={len(pooled_J)})\n"
                 f"Kendall tau={tau_p:.3f}, Spearman rho={rho_p:.3f}", fontsize=9)
    fig.tight_layout()
    fig.savefig(OUT / "fig_b2_ab_timeseries.png", dpi=160, bbox_inches="tight")
    plt.close(fig)

    # ---- figure: ranking correlations ----
    fig, axes = plt.subplots(1, 2, figsize=(11.5, 4.3))
    ax = axes[0]
    rows_peak = [r for r in table3 if "peak" in r["objective_pair"]]
    rows_term = [r for r in table3 if r["objective_pair"].endswith("_T")]
    x = np.arange(len(rows_peak))
    w = 0.2
    ax.bar(x - 1.5 * w, [r["kendall_entry"] for r in rows_peak],
           w, label="entry tau (peak)")
    ax.bar(x - 0.5 * w, [r["kendall_planB_worstcase"] for r in rows_peak],
           w, label="planB worst-case tau (peak)")
    ax.bar(x + 0.5 * w, [r["kendall_entry"] for r in rows_term],
           w, label="entry tau (terminal)")
    ax.bar(x + 1.5 * w, [r["kendall_planB_worstcase"] for r in rows_term],
           w, label="planB worst-case tau (terminal)")
    labels = [f"{r['geometry'][:4]}\n{r['eta_v']}" for r in rows_peak]
    ax.set_xticks(x, labels, fontsize=8)
    ax.set_ylim(0, 1.05)
    ax.axhline(0.95, color="r", lw=0.8, ls=":", label="0.95 gate")
    ax.set_ylabel("Kendall tau vs integral")
    ax.set_title("Snapshot-vs-integral ranking agreement (Table 3)", fontsize=9)
    ax.legend(fontsize=7, loc="lower right")
    ax = axes[1]
    # worst-case plan value curves for the A/B cell: integral vs peak ranking
    if ab_example:
        cell = next(c for c in cells
                    if c["geometry"] == ab_example["cell"]["geometry"]
                    and c["eta_v"] == ab_example["cell"]["eta_v"])
        J = np.asarray(cell["matrix_before"]["integral"])
        P = np.asarray(cell["matrix_before"]["snapshot_peak"])
        order_J = np.argsort(J.min(axis=1))
        order_P = np.argsort(P.min(axis=1))
        ax.plot(range(11), [plans[i] for i in order_J], "o-", color="tab:blue",
                label="ranked by integral worst case")
        ax.plot(range(11), [plans[i] for i in order_P], "x--", color="tab:red",
                label="ranked by snapshot_peak worst case")
        ax.set_yticks(range(11), [plans[i] for i in order_J], fontsize=7)
        ax.invert_yaxis()
        ax.set_title(f"Plan ranking, {ab_example['cell']['geometry']} cell, "
                     f"$\\eta_v$={ab_example['cell']['eta_v']}", fontsize=9)
        ax.legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(OUT / "fig_b2_ranking.png", dpi=160, bbox_inches="tight")
    plt.close(fig)

    # ================= B2.2 =================
    kBB = KernelFit.from_dict(fits[KERNEL_CLASS])
    kW = KernelWrap(kBB, 1.0, 1.0)
    HEADING = 0.0          # column steams along +x
    SHIP_LEN = 3.0
    N_SEG = 4
    SPACING = 6.0          # centre-to-centre, line ahead
    SPEED = 1.0            # cells per step
    T_END = 12
    ship_centers0 = [(0.0, 0.0), (-SPACING, 0.0)]
    sources0 = fleet_sources(ship_centers0, HEADING, SHIP_LEN, N_SEG)

    gx = np.arange(-28.0, 28.01, 0.5)
    X, Y = np.meshgrid(gx, gx)
    F0 = field_F(kW, sources0, X, Y)

    # dynamic frames in Earth frame (column advances +x); keep the same grid
    frames = {}
    for t_f in (0, T_END // 2, T_END):
        src = fleet_sources([(cx + SPEED * t_f, cy) for cx, cy in ship_centers0],
                            HEADING, SHIP_LEN, N_SEG)
        frames[t_f] = field_F(kW, src, X, Y)

    # co-moving stability: compare frame t to frame 0 shifted by SPEED*t
    stability = {}
    for t_f in (0, T_END // 2, T_END):
        Fref = field_F(kW, sources0, X - SPEED * t_f, Y)
        d = np.abs(frames[t_f] - Fref)
        stability[t_f] = {"max_abs_dev": float(d.max()),
                          "mean_abs_dev": float(d.mean()),
                          "rel_mean_dev": float(d.mean() / max(F0.mean(), 1e-12)),
                          "pearson": float(np.corrcoef(frames[t_f].ravel(),
                                                       Fref.ravel())[0, 1])}

    # center-vs-flank profiles (co-moving coordinates), per frame
    stations = {"flank_aft": -SPACING - SHIP_LEN / 2,   # -7.5: through stern end
                "center": -SPACING / 2,                 # -3.0: column mid-length
                "flank_fwd": SHIP_LEN / 2}              # +1.5: through bow end
    y_prof = np.arange(0.5, 24.01, 0.25)
    x_long = np.arange(-24.0, 24.01, 0.25)
    profile_rows = []
    long_curves = {}
    for t_f in (0, T_END // 2, T_END):
        src = fleet_sources([(cx + SPEED * t_f, cy) for cx, cy in ship_centers0],
                            HEADING, SHIP_LEN, N_SEG)
        for sname, x0 in stations.items():
            Xp = np.full_like(y_prof, x0 + SPEED * t_f)
            Fp = field_F(kW, src, Xp, y_prof)
            Fs = smooth(Fp)
            for yy, raw, sm in zip(y_prof, Fp, Fs):
                profile_rows.append({"frame_t": t_f, "profile": "lateral",
                                     "station": sname, "x_earth": round(x0 + SPEED * t_f, 3),
                                     "coord": round(float(yy), 3),
                                     "F_raw": round(float(raw), 6),
                                     "F_smooth": round(float(sm), 6)})
        Xl = x_long + SPEED * t_f
        Fl = field_F(kW, src, Xl, np.full_like(x_long, 6.0))
        Fls = smooth(Fl)
        long_curves[t_f] = (x_long.copy(), Fls.copy(), Fl.copy())
        for xx, raw, sm in zip(x_long, Fl, Fls):
            profile_rows.append({"frame_t": t_f, "profile": "longitudinal",
                                 "station": "abeam_y6", "x_earth": round(xx + SPEED * t_f, 3),
                                 "coord": round(float(xx), 3),
                                 "F_raw": round(float(raw), 6),
                                 "F_smooth": round(float(sm), 6)})

    cols = list(profile_rows[0].keys())
    with (OUT / "flank_profile.csv").open("w", encoding="utf-8") as fh:
        fh.write(",".join(cols) + "\n")
        for r in profile_rows:
            fh.write(",".join(str(r[c]) for c in cols) + "\n")

    # research-question numbers: center vs flank on the ridge y=6
    ridge = {}
    for t_f, (xs, Fls, Flraw) in long_curves.items():
        def at(xq):
            i = int(np.argmin(np.abs(xs - xq)))
            return float(Fls[i])
        ridge[t_f] = {"F_center(x=-3)": at(-3.0), "F_flank_aft(x=-7.5)": at(-7.5),
                      "F_flank_fwd(x=+1.5)": at(+1.5),
                      "argmax_x": float(xs[int(np.argmax(Fls))]),
                      "center_gt_both_flanks":
                          at(-3.0) > at(-7.5) and at(-3.0) > at(+1.5)}

    # ---- figures ----
    levels = np.linspace(0.0, np.nanquantile(F0, 0.995), 41)
    fig, ax = plt.subplots(figsize=(7.4, 6.0))
    im = ax.pcolormesh(X, Y, F0, cmap="magma", shading="auto", vmin=levels[0],
                       vmax=levels[-1])
    for (sx, sy, _sh) in sources0:
        ax.plot(sx, sy, "c+", ms=9, mew=1.6)
    ax.plot([s[0] for s in sources0], [s[1] for s in sources0], "c+", ms=9,
            mew=1.6, label="fire sources (4 segments/ship)")
    for k_i, (sname, x0) in enumerate(stations.items()):
        ax.axvline(x0, color="w", lw=0.7, ls=":")
        ax.text(x0, 25.2 + 1.8 * (k_i % 2), sname, color="w", fontsize=8,
                ha="center")
    ax.axhline(6.0, color="w", lw=0.7, ls="--")
    ax.set_xlabel("x (cells, along column)")
    ax.set_ylabel("y (cells)")
    ax.set_title(f"B2.2 fleet exposure field F_B(x, t=0): two-ship line ahead, "
                 f"CA kernel, L=3, 4 segments/ship, spacing={SPACING:.0f}", fontsize=9)
    fig.colorbar(im, ax=ax, label="expected hits (neutral broadside target)")
    ax.legend(loc="lower left", fontsize=8)
    fig.savefig(OUT / "fleet_heatmap_t0.png", dpi=160, bbox_inches="tight")
    plt.close(fig)

    fig, axes = plt.subplots(1, 3, figsize=(15.5, 4.6))
    for ax, t_f in zip(axes, (0, T_END // 2, T_END)):
        im = ax.pcolormesh(X, Y, frames[t_f], cmap="magma", shading="auto",
                           vmin=levels[0], vmax=levels[-1])
        src = fleet_sources([(cx + SPEED * t_f, cy) for cx, cy in ship_centers0],
                            HEADING, SHIP_LEN, N_SEG)
        ax.plot([s[0] for s in src], [s[1] for s in src], "c+", ms=8, mew=1.4)
        ax.set_title(f"t={t_f} (column advanced {SPEED * t_f:.0f} cells)", fontsize=9)
        ax.set_xlabel("x")
    axes[0].set_ylabel("y")
    fig.colorbar(im, ax=axes, shrink=0.9, label="F_B(x,t)")
    fig.suptitle("Fleet exposure field moving with the formation (Earth frame)",
                 fontsize=10)
    fig.savefig(OUT / "fleet_heatmap_frames.png", dpi=160, bbox_inches="tight")
    plt.close(fig)

    b22 = {
        "params": {"heading_deg": HEADING, "ship_len_cells": SHIP_LEN,
                   "segments_per_ship": N_SEG, "n_ships": 2,
                   "spacing_cells": SPACING, "speed_cells_per_step": SPEED,
                   "frames_t": [0, T_END // 2, T_END],
                   "target": "speed-4 broadside stationary point target",
                   "kernel_class": KERNEL_CLASS, "grid_step": 0.5,
                   "source_positions_t0": sources0,
                   "smoothing": "centred moving average, k=5"},
        "comoving_stability": stability,
        "center_vs_flank_ridge_y6": ridge,
        "interpretation_pending": "see report.md",
    }
    (OUT / "fleet_heatmap_summary.json").write_text(
        json.dumps(b22, indent=1), encoding="utf-8")

    print(json.dumps({"ridge": ridge, "stability": stability,
                      "AB": {"source": ab_source,
                             "peakA": ab_example and ab_example["A"]["peak"],
                             "peakB": ab_example and ab_example["B"]["peak"],
                             "intA": ab_example and ab_example["A"]["integral"],
                             "intB": ab_example and ab_example["B"]["integral"]}},
                     indent=1)[:2200])
    print("wrote", OUT)


if __name__ == "__main__":
    main()
