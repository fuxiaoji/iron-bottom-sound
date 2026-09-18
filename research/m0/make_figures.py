"""Figures for the M0 cheap-kill checkpoint.  Every figure is script-generated.

Run:
    PYTHONPATH=backend/src:research/m0 .venv/bin/python research/m0/make_figures.py
"""

from __future__ import annotations

import csv
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

REPO = Path(__file__).resolve().parents[2]
RES = REPO / "research" / "m0" / "results"
FIG = REPO / "research" / "m0" / "figures"
FIG.mkdir(parents=True, exist_ok=True)


def _rows(name):
    p = RES / name
    if not p.exists():
        return []
    with p.open() as fh:
        return list(csv.DictReader(fh))


def fig_delta_distribution():
    rows = [r for r in _rows("A0_delta_rows.csv") if r["delta"] not in ("", None)]
    d = [float(r["delta"]) for r in rows]
    fig, ax = plt.subplots(figsize=(6, 3.6))
    ax.hist(d, bins=20, color="#3b7dd8", edgecolor="white")
    ax.set_xlabel(r"$\Delta_t = V_{replan} - V_{continue}$")
    ax.set_ylabel("count")
    ax.set_title(f"A0: replanning value over {len(d)} decision nodes")
    ax.axvline(0.10, color="crimson", ls="--", lw=1,
               label=r"signal floor $\Delta=0.1$")
    ax.legend(loc="upper right", fontsize=8)
    fig.tight_layout()
    fig.savefig(FIG / "A0_delta_distribution.png", dpi=150)
    plt.close(fig)


def fig_delta_vs_horizon_and_commitment():
    rows = [r for r in _rows("A0_delta_rows.csv") if r["delta"] not in ("", None)]
    by_h = defaultdict(list)
    by_c = defaultdict(list)
    for r in rows:
        by_h[int(r["remaining_horizon"])].append(float(r["delta"]))
        by_c[int(r["commitment_len"])].append(float(r["delta"]))
    fig, axes = plt.subplots(1, 2, figsize=(8.5, 3.4))
    for ax, data, lab in ((axes[0], by_h, "remaining horizon"),
                          (axes[1], by_c, "commitment length (rf)")):
        ks = sorted(data)
        means = [sum(data[k]) / len(data[k]) for k in ks]
        sems = [(max(data[k]) - min(data[k])) / 2 for k in ks]
        ax.errorbar(ks, means, yerr=sems, marker="o", capsize=3, color="#3b7dd8")
        ax.set_xlabel(lab)
        ax.set_ylabel(r"mean $\Delta$")
        ax.set_title(f"A0: $\\Delta$ vs {lab}")
        ax.grid(alpha=.3)
    fig.tight_layout()
    fig.savefig(FIG / "A0_delta_vs_horizon_commitment.png", dpi=150)
    plt.close(fig)


def fig_within_snapshot_spread():
    rows = [r for r in _rows("A0_delta_rows.csv") if r["delta"] not in ("", None)]
    groups = defaultdict(list)
    for r in rows:
        groups[(r["game_id"], r["snapshot"])].append(float(r["delta"]))
    spreads = [max(v) - min(v) for v in groups.values() if len(v) > 1]
    fig, ax = plt.subplots(figsize=(6, 3.6))
    ax.hist(spreads, bins=20, color="#e0803a", edgecolor="white")
    ax.set_xlabel(r"within-snapshot spread of $\Delta$")
    ax.set_ylabel("count")
    ax.set_title("A0: same public state, different replanning value")
    fig.tight_layout()
    fig.savefig(FIG / "A0_within_snapshot_spread.png", dpi=150)
    plt.close(fig)


def fig_compute_value_frontier():
    rows = _rows("A0_frontier.csv")
    pts = defaultdict(list)
    for r in rows:
        if float(r.get("span", 0) or 0) <= 1e-12:
            continue
        for P in (2, 3, 4):
            s, t = r.get(f"saving_periodic_P{P}"), r.get(f"retention_periodic_P{P}")
            if s and t:
                pts[f"periodic_P{P}"].append((float(s), float(t)))
        for k in range(1, int(r["T"])):
            s, t = r.get(f"saving_k{k}"), r.get(f"retention_random_k{k}")
            if s and t:
                pts[f"random_k{k}"].append((float(s), float(t)))
            s, t = r.get(f"saving_k{k}"), r.get(f"retention_oracle_k{k}")
            if s and t:
                pts["oracle_topK"].append((float(s), float(t)))
    fig, ax = plt.subplots(figsize=(6.4, 4))
    for name, vals in sorted(pts.items()):
        vals.sort()
        xs = [v[0] for v in vals]
        ys = [v[1] for v in vals]
        style = "-o" if name == "oracle_topK" else "o"
        ax.plot(xs, ys, style, ms=4, alpha=.7, label=name)
    ax.axhline(0.95, color="crimson", ls="--", lw=1, label="retention bar 95%")
    ax.axvline(0.30, color="gray", ls=":", lw=1, label="saving bar 30%")
    ax.set_xlabel("planning-call saving")
    ax.set_ylabel("value retention")
    ax.set_title("A0/A1: compute-value frontier (exact)")
    ax.legend(fontsize=7, ncol=2)
    ax.grid(alpha=.3)
    fig.tight_layout()
    fig.savefig(FIG / "A0_compute_value_frontier.png", dpi=150)
    plt.close(fig)


def fig_alias_gaps():
    rows = _rows("B0_alias_stats.csv")
    sealed = [r for r in rows if r["family"] != "null"]
    fig, axes = plt.subplots(1, 2, figsize=(9, 3.6))
    ax = axes[0]
    rates = [float(r["action_disagree_rate"]) for r in sealed]
    ax.hist(rates, bins=20, color="#3b7dd8", edgecolor="white")
    ax.set_xlabel("action-disagreement rate within snapshot cells")
    ax.set_ylabel("count")
    ax.set_title("B0: sealed-commitment games")
    ax = axes[1]
    vg = [float(r["max_v_gap"]) for r in sealed]
    dg = [float(r["max_delta_gap"]) for r in sealed]
    ax.hist(dg, bins=20, color="#e0803a", edgecolor="white", label=r"max $\Delta$ gap")
    ax.hist(vg, bins=20, color="#3b7dd8", edgecolor="white", alpha=.8, label="max V gap")
    ax.set_xlabel("gap size")
    ax.set_ylabel("count")
    ax.set_title("B0: value gap vs delta gap")
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(FIG / "B0_alias_gaps.png", dpi=150)
    plt.close(fig)


def fig_d0_identification():
    """D0: per-type identifiability + the inseparability structure."""
    import numpy as np
    d = json.loads((RES / "D0_summary.json").read_text())
    types = ["OPT", "MYO", "NOM", "NBU", "AMB"]
    # inseparability matrix
    pairs = {tuple(x) for x in d["inseparable_pairs"]}
    M = np.zeros((5, 5))
    for i, a in enumerate(types):
        for j, b in enumerate(types):
            if i == j:
                M[i, j] = 1.0
            elif (a, b) in pairs or (b, a) in pairs:
                M[i, j] = M[j, i] = 1.0
    fig, axes = plt.subplots(1, 2, figsize=(9.2, 3.8))
    ax = axes[0]
    ax.imshow(M, cmap="Reds", vmin=0, vmax=1.3)
    ax.set_xticks(range(5), types)
    ax.set_yticks(range(5), types)
    for i in range(5):
        for j in range(5):
            if M[i, j] > 0 and i != j:
                ax.text(j, i, "same", ha="center", va="center", fontsize=8,
                        color="white" if i != j else "black")
    ax.set_title("D0: inseparable agent pairs (all tests)")
    ax = axes[1]
    ids = [d["per_type"][t]["identified_runs"] for t in types]
    ax.bar(types, ids, color=["#3b7dd8" if n else "#d9534f" for n in ids])
    ax.set_ylabel("identified runs")
    ax.set_title("D0: identification success (pre-declared pool)")
    ax.set_ylim(0, max(ids) + 1)
    fig.tight_layout()
    fig.savefig(FIG / "D0_identification.png", dpi=150)
    plt.close(fig)


def fig_c0_sampling():
    """C0: certificate width vs simulated matches, per policy (medians)."""
    p = RES / "C0_summary.json"
    if not p.exists():
        return
    d = json.loads(p.read_text())
    fig, axes = plt.subplots(1, len(d["scenarios"]), figsize=(5.2 * len(d["scenarios"]), 3.8),
                             squeeze=False)
    for ax, (scen, res) in zip(axes[0], d["scenarios"].items()):
        for policy, info in res["policies"].items():
            med = info["median_samples"]
            if med is None:
                continue
            ax.bar(policy, med,
                   color="#2e8b57" if policy == "cert_sensitivity" else "#3b7dd8")
        ax.set_ylabel("median matches to certificate width 0.20")
        ax.set_title(f"C0: {scen}")
        ax.tick_params(axis="x", rotation=45)
        u = res["policies"]["uniform"]["median_samples"]
        if u:
            ax.axhline(u, color="gray", ls="--", lw=1, label="uniform")
            ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(FIG / "C0_matches_to_certificate.png", dpi=150)
    plt.close(fig)


def main() -> int:
    fig_delta_distribution()
    fig_delta_vs_horizon_and_commitment()
    fig_within_snapshot_spread()
    fig_compute_value_frontier()
    fig_alias_gaps()
    fig_d0_identification()
    fig_c0_sampling()
    made = sorted(p.name for p in FIG.glob("*.png"))
    print("figures:", made)
    (RES / "figures_manifest.json").write_text(json.dumps(made, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
