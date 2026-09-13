"""E01: Directional firepower kernel calibration (plan section 8 / M1).

Ground truth: exact engine-expected hits over a (distance, bearing sector,
target heading, target speed) grid, generated with the engine's own modifier
pipeline.  The kernel is fitted on a 70% train split and evaluated on the
held-out 30%.

Acceptance (plan E01): pooled Spearman rank correlation >= 0.90; normalized
MAE <= 10-15% within the effective-range region; bow/stern and broadside
sectors must respect engine mount arcs (structural, exact).

Outputs: research/results/e01/{truth.csv, kernel_fits.json, metrics.json,
fig_e01_polar_<class>.png, fig_e01_calibration.png, report.md}
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "backend" / "src"))
sys.path.insert(0, str(REPO))

from iron_bottom_sound.models import HexCoord  # noqa: E402
from research.common import make_sandbox  # noqa: E402
from research.geometry.firepower_kernel import (  # noqa: E402
    fit_kernel,
    scan_ground_truth,
)

OUT = REPO / "research" / "results" / "e01"

ATTACKERS = [
    # (attacker ship id, target ship id, label) — ids must differ: state.ships
    # is keyed by id, so equal ids would alias attacker and target into one object.
    ("IBS-U-USN-LAFFEY", "IBS-U-IJN-FUBUKI", "DD"),
    ("IBS-U-USN-HELENA", "IBS-U-USN-ST-LOUIS", "CL"),
    ("IBS-U-USN-SAN-FRANCISCO", "IBS-U-IJN-AOBA", "CA"),
    ("IBS-U-IJN-ERMA-YAMATO", "IBS-U-USN-ERMA-IOWA", "BB"),
]

ANCHOR = HexCoord(q=23, r=19)
SPLIT_SEED = 20260909
TRAIN_FRACTION = 0.7


def build_pair(attacker_id: str, target_id: str):
    ships = [
        {"id": attacker_id, "name": attacker_id, "side": "axis",
         "position": "X20", "heading": 1, "speed": 4},
        {"id": target_id, "name": target_id, "side": "allies",
         "position": "Y20", "heading": 1, "speed": 4},
    ]
    engine, state = make_sandbox(f"E01-{attacker_id[-12:]}", ships)
    attacker = state.ships[attacker_id]
    target = state.ships[target_id]
    attacker.position = ANCHOR
    attacker.heading = 1
    attacker.current_speed = 4
    target.position = HexCoord(q=ANCHOR.q + 3, r=ANCHOR.r)
    return engine, state, attacker, target


def split_rows(rows: list[dict], frac_train: float = TRAIN_FRACTION, seed: int = SPLIT_SEED):
    rng = np.random.default_rng(seed)
    idx = rng.permutation(len(rows))
    n_train = int(len(rows) * frac_train)
    return ([rows[i] for i in idx[:n_train]], [rows[i] for i in idx[n_train:]])


def sector_angle(row: dict) -> float:
    return {"bow": 0.0, "starboard": 90.0, "stern": 180.0, "port": -90.0}[row["sector"]]


def metrics(rows: list[dict], fit) -> dict:
    from scipy.stats import spearmanr

    t = np.array([r["total"] for r in rows])
    k = np.array([fit.expected_hits(r["distance"], sector_angle(r), r["target_speed"],
                                    r["target_aspect"]) for r in rows])
    rho, p = spearmanr(t, k)
    if not np.isfinite(rho):
        rho, p = 0.0, 1.0  # constant input (degenerate split); counted as failure
    eff = t > 1e-9
    nmae = float(np.sum(np.abs(k[eff] - t[eff])) / np.sum(t[eff])) if eff.any() else 0.0
    return {"spearman": float(rho), "p_value": float(p), "nmae": nmae, "n": int(len(rows))}


def main() -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    OUT.mkdir(parents=True, exist_ok=True)
    all_rows: list[dict] = []
    summary: dict[str, dict] = {}
    fits_json: dict[str, dict] = {}
    fits_by_label: dict[str, object] = {}

    for attacker_id, target_id, label in ATTACKERS:
        engine, state, attacker, target = build_pair(attacker_id, target_id)
        rows = scan_ground_truth(engine, state, attacker, target, max_distance=24)
        train, test = split_rows(rows)
        fit = fit_kernel(engine, train, attacker, state, label, label)
        m_train = metrics(train, fit)
        m_test = metrics(test, fit)
        summary[label] = {"train": m_train, "test": m_test,
                          "attacker": attacker_id, "target": target_id}
        all_rows.extend(rows)
        fits_by_label[label] = fit
        fits_json[label] = {
            "attacker_id": attacker_id, "attacker_class": label, "target_class": label,
            "kind_sector_fp": fit.kind_sector_fp,
            "range_knots": fit.range_knots,
            "kind_m_range": fit.kind_m_range,
            "speed_knots": fit.speed_knots,
            "kind_m_speed": fit.kind_m_speed,
            "long_knots": fit.long_knots,
            "kind_m_long": fit.kind_m_long,
            "response_curves": {k: v for k, v in fit.response_curves.items()},
        }

        # ---- polar kernel map + engine truth map ----
        dists = np.arange(1, 25)
        angles = np.linspace(-180, 180, 73)
        K = np.zeros((len(angles), len(dists)))
        for ai, ang in enumerate(angles):
            K[ai, :] = fit.expected_hits_array(dists.astype(float), float(ang), 4, "broadside")
        axis_truth: dict[tuple[int, int], float] = {}
        for r in rows:
            key = (r["rel"], r["distance"])
            axis_truth[key] = axis_truth.get(key, 0.0) + r["total"] / 6.0
        TT = np.zeros_like(K)
        for ai, ang in enumerate(angles):
            rel6 = int(round(ang / 60.0)) % 6
            for di, dist in enumerate(dists):
                TT[ai, di] = axis_truth.get((rel6, int(dist)), 0.0)
        fig, axes = plt.subplots(1, 2, figsize=(11, 4.6),
                                 subplot_kw={"projection": "polar"})
        for ax, M, title in ((axes[0], K, f"{label} kernel $K(r,\\theta)$, v=4"),
                             (axes[1], TT, f"{label} engine expected hits")):
            im = ax.pcolormesh(np.deg2rad(angles), dists, M.T, shading="auto", cmap="inferno")
            ax.set_theta_zero_location("N")
            ax.set_theta_direction(-1)
            ax.set_thetagrids([0, 180],
                              ["bow 0°", "stern 180°"], fontsize=9)
            ax.tick_params(axis='y', labelsize=8)
            ax.set_title(title, fontsize=11)
            ax.set_rlabel_position(180)
        fig.colorbar(im, ax=axes, shrink=0.8, label="expected hits / phase")
        fig.savefig(OUT / f"fig_e01_polar_{label}.png", dpi=160, bbox_inches="tight")
        plt.close(fig)

    # ---- pooled calibration scatter (held-out cells, all classes) ----
    fig, ax = plt.subplots(figsize=(5.6, 5.6))
    rng = np.random.default_rng(7)
    colors = {"DD": "#1f77b4", "CL": "#2ca02c", "CA": "#ff7f0e", "BB": "#d62728"}
    for attacker_id, target_id, label in ATTACKERS:
        engine, state, attacker, target = build_pair(attacker_id, target_id)
        rows = scan_ground_truth(engine, state, attacker, target, max_distance=24)
        _, test = split_rows(rows)
        fit = fits_by_label[label]
        t = np.array([r["total"] for r in test])
        k = np.array([fit.expected_hits(r["distance"], sector_angle(r),
                                        r["target_speed"], r["target_aspect"]) for r in test])
        jitter = rng.uniform(-0.12, 0.12, size=len(t))
        ax.scatter(t, k + jitter, s=6, alpha=0.45, color=colors[label], label=label)
    lim = float(max(r["total"] for r in all_rows)) * 1.05
    ax.plot([0, lim], [0, lim], "k--", lw=1)
    ax.set_xlabel("engine exact expected hits")
    ax.set_ylabel("kernel prediction")
    ax.set_title("E01 kernel calibration (held-out 30%)")
    ax.legend()
    fig.savefig(OUT / "fig_e01_calibration.png", dpi=160, bbox_inches="tight")
    plt.close(fig)

    with (OUT / "truth.csv").open("w", newline="", encoding="utf-8") as fh:
        fieldnames: list[str] = []
        for row in all_rows:
            for key in row:
                if key not in fieldnames:
                    fieldnames.append(key)
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_rows)

    pooled_rho = float(np.mean([summary[k]["test"]["spearman"] for k in summary]))
    pooled_nmae = float(np.mean([summary[k]["test"]["nmae"] for k in summary]))
    accepted = pooled_rho >= 0.90 and pooled_nmae <= 0.15
    result = {"per_class": summary, "pooled_spearman": pooled_rho,
              "pooled_nmae": pooled_nmae, "acceptance": "PASS" if accepted else "FAIL",
              "criteria": {"spearman_min": 0.90, "nmae_max": 0.15}}
    (OUT / "metrics.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    (OUT / "kernel_fits.json").write_text(json.dumps(fits_json, indent=2), encoding="utf-8")

    lines = [
        "# E01 firepower kernel calibration", "",
        f"- pooled Spearman (held-out): **{pooled_rho:.4f}** (criterion >= 0.90)",
        f"- pooled nMAE (held-out): **{pooled_nmae:.4f}** (criterion <= 0.15)",
        f"- acceptance: **{result['acceptance']}**", "",
        "| class | Spearman(test) | nMAE(test) | n(test) |", "|---|---|---|---|",
    ]
    for label in summary:
        m = summary[label]["test"]
        lines.append(f"| {label} | {m['spearman']:.4f} | {m['nmae']:.4f} | {m['n']} |")
    (OUT / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
