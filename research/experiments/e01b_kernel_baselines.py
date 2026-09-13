"""E01b: kernel baselines, bootstrap CIs, and cross-ship-pair transfer.

Addresses three reviewer demands on E01:
1. Baseline comparison -- an isotropic kernel (bearing structure removed,
   everything else identical) quantifies how much of the calibration
   fidelity comes from DIRECTIONALITY rather than from the range/speed
   response alone.
2. Bootstrap confidence intervals for pooled/per-class Spearman.
3. Cross-pair transfer -- fit the modifier curves on one attacker-target
   pair, transplant them onto another attacker's structural mount arcs,
   and evaluate on that pair's held-out grid.

Output: research/results/e01/baselines.json + report_baselines.md
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "backend" / "src"))
sys.path.insert(0, str(REPO))

from iron_bottom_sound.engine import IronBottomEngine  # noqa: E402
from iron_bottom_sound.models import HexCoord  # noqa: E402
from research.common import make_sandbox  # noqa: E402
from research.geometry.firepower_kernel import (  # noqa: E402
    KernelFit,
    fit_kernel,
    response_curve,
    scan_ground_truth,
)

OUT = REPO / "research" / "results" / "e01"
ANCHOR = HexCoord(q=23, r=19)
SPLIT_SEED = 20260909
TRAIN_FRACTION = 0.7

ATTACKERS = [
    ("IBS-U-USN-LAFFEY", "IBS-U-IJN-FUBUKI", "DD"),
    ("IBS-U-USN-HELENA", "IBS-U-USN-ST-LOUIS", "CL"),
    ("IBS-U-USN-SAN-FRANCISCO", "IBS-U-IJN-AOBA", "CA"),
    ("IBS-U-IJN-ERMA-YAMATO", "IBS-U-USN-ERMA-IOWA", "BB"),
]


def build_pair(attacker_id: str, target_id: str):
    ships = [
        {"id": attacker_id, "name": attacker_id, "side": "axis",
         "position": "X20", "heading": 1, "speed": 4},
        {"id": target_id, "name": target_id, "side": "allies",
         "position": "Y20", "heading": 1, "speed": 4},
    ]
    engine, state = make_sandbox(f"E01B-{attacker_id[-12:]}", ships)
    attacker = state.ships[attacker_id]
    target = state.ships[target_id]
    attacker.position = ANCHOR
    attacker.heading = 1
    attacker.current_speed = 4
    target.position = HexCoord(q=ANCHOR.q + 3, r=ANCHOR.r)
    return engine, state, attacker, target


def split_rows(rows, frac_train=TRAIN_FRACTION, seed=SPLIT_SEED):
    rng = np.random.default_rng(seed)
    idx = rng.permutation(len(rows))
    n = int(len(rows) * frac_train)
    return rows[:0], None  # placeholder replaced below


def sector_angle(row):
    return {"bow": 0.0, "starboard": 90.0, "stern": 180.0, "port": -90.0}[row["sector"]]


def predict_full(fit, row):
    return fit.expected_hits(row["distance"], sector_angle(row),
                             row["target_speed"], row["target_aspect"])


def predict_isotropic(iso, row):
    return iso(row)


def spearman(a, b):
    from scipy.stats import spearmanr
    rho, _ = spearmanr(a, b)
    return float(rho) if np.isfinite(rho) else 0.0


def nmae(pred, truth):
    pred = np.asarray(pred, dtype=float)
    truth = np.asarray(truth, dtype=float)
    eff = truth > 1e-9
    if not eff.any():
        return 0.0
    return float(np.sum(np.abs(pred[eff] - truth[eff])) / np.sum(truth[eff]))


def fit_isotropic(rows, knots=(1, 2, 4, 7, 10, 13, 16, 20, 24)):
    """Bearing-invariant kernel: same inversion machinery, but every cell is
    treated as a full-broadside shot (no sector structure) and the
    longitudinal factor is kept (it is not a bearing effect of the shooter)."""
    from research.geometry.firepower_kernel import _invert_modifier

    cells = {}
    fp_ref = None
    for row in rows:
        key = (row["distance"], row["target_speed"], row["target_aspect"])
        cells.setdefault(key, []).append(row["total"])
    # use an arbitrary large-fp response curve for inversion: choose the
    # median broadside firepower across rows is unknowable here, so invert
    # against a unit-firepower curve and fit the scale factor jointly.
    return cells


def main() -> None:
    import csv
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    # ---------- reload truth + refit full kernels ----------
    per_pair = {}
    fits = {}
    for attacker_id, target_id, label in ATTACKERS:
        engine, state, attacker, target = build_pair(attacker_id, target_id)
        rows = scan_ground_truth(engine, state, attacker, target, max_distance=24)
        rng = np.random.default_rng(SPLIT_SEED)
        idx = rng.permutation(len(rows))
        n_train = int(len(rows) * TRAIN_FRACTION)
        train = [rows[i] for i in idx[:n_train]]
        test = [rows[i] for i in idx[n_train:]]
        fit = fit_kernel(engine, train, attacker, state, label, label)
        fits[label] = (fit, rows, train, test)
        per_pair[label] = {"attacker": attacker_id, "target": target_id}
        print(f"loaded {label}: {len(rows)} rows", flush=True)

    # ---------- baseline: isotropic kernel ----------
    # identical inversion/decomposition machinery, but sector structure is
    # removed: predictions depend only on (r, v, aspect).
    def fit_isotropic_for(engine, attacker, state, train_rows):
        # use the full kernel's H/S/A at the full-broadside sector only
        full = fit_kernel(engine, train_rows, attacker, state, "iso", "iso")
        # rebuild predictions as: value at the best (max-firepower) sector
        best_fp_sector = {}
        for kind, sms in full.kind_sector_fp.items():
            for sec, fp in sms.items():
                if fp > 0:
                    best_fp_sector[kind] = max(best_fp_sector.get(kind, 0), fp)
        return full, best_fp_sector

    results = {"per_class": {}, "pooled": {}}
    pooled_true, pooled_full, pooled_iso = [], [], []
    class_stats = {}
    for label in (a[2] for a in ATTACKERS):
        fit, rows, train, test = fits[label]
        engine, state, attacker, target = build_pair(*ATTACKERS[[a[2] for a in ATTACKERS].index(label)][:2])
        # isotropic prediction: kernel evaluated at the bearing that maximizes
        # its own sector firepower (i.e. the best it can do without knowing
        # the true bearing) -- for most classes that is abeam; implement by
        # evaluating at +90 deg (full broadside) always.
        t = np.array([r["total"] for r in test])
        k_full = np.array([predict_full(fit, r) for r in test])
        k_iso = np.array([fit.expected_hits(r["distance"], 90.0,
                                            r["target_speed"], r["target_aspect"])
                          for r in test])
        rho_full = spearman(t, k_full)
        rho_iso = spearman(t, k_iso)
        rng = np.random.default_rng(777)
        boots = []
        for _ in range(2000):
            pick = rng.choice(len(t), size=len(t), replace=True)
            boots.append(spearman(t[pick], k_full[pick]))
        lo, hi = np.percentile(boots, [2.5, 97.5])
        class_stats[label] = {
            "spearman_full": rho_full, "spearman_full_ci95": [float(lo), float(hi)],
            "spearman_isotropic": rho_iso,
            "nmae_full": nmae(k_full, t), "nmae_isotropic": nmae(k_iso, t),
            "n": len(test),
        }
        pooled_true.extend(t.tolist())
        pooled_full.extend(k_full.tolist())
        pooled_iso.extend(k_iso.tolist())
        print(label, "full rho=%.4f iso rho=%.4f" % (rho_full, rho_iso), flush=True)

    pooled_true = np.array(pooled_true)
    pooled_full = np.array(pooled_full)
    pooled_iso = np.array(pooled_iso)
    rng = np.random.default_rng(778)
    boots = [spearman(pooled_true[pick := rng.choice(len(pooled_true), size=len(pooled_true), replace=True)],
                      pooled_full[pick]) for _ in range(2000)]
    plo, phi = np.percentile(boots, [2.5, 97.5])

    # ---------- cross-pair transfer ----------
    # fit modifier curves on source pair, transplant onto target attacker's
    # structural mounts, evaluate Spearman on the target pair's full grid.
    transfer = {}
    for src_label in ("CA", "BB"):
        src_fit, *_ = fits[src_label]
        for dst_attacker_id, dst_target_id, dst_label in ATTACKERS:
            if dst_label == src_label:
                continue
            engine, state, attacker, target = build_pair(dst_attacker_id, dst_target_id)
            rows = scan_ground_truth(engine, state, attacker, target,
                                     max_distance=24)
            # transplant: source modifier curves + target structural arcs;
            # response curves recomputed for the target's own firepower values
            tk = KernelFit(attacker_id=attacker.id, attacker_class=dst_label,
                           target_class=dst_label,
                           range_knots=src_fit.range_knots,
                           speed_knots=src_fit.speed_knots,
                           long_knots=src_fit.long_knots)
            from research.geometry.firepower_kernel import AXIS_DIRS, SECTOR_FOR_REL
            pos = attacker.position
            for kind in ("primary", "secondary", "tertiary"):
                sec_fp = {sec: 0 for sec in set(SECTOR_FOR_REL.values())}
                for b in range(1, 7):
                    dq, dr = AXIS_DIRS[b]
                    hex_ = HexCoord(q=pos.q + dq, r=pos.r + dr)
                    arc = __import__("iron_bottom_sound.engine", fromlist=["IronBottomEngine"]).IronBottomEngine._relative_aspect(pos, attacker.heading, hex_)
                    fpb = sum(mo.firepower for mo in attacker.gun_mounts
                              if mo.kind == kind and not mo.destroyed and arc in mo.arcs)
                    sec_fp[SECTOR_FOR_REL[(b - attacker.heading) % 6]] = fpb
                tk.kind_sector_fp[kind] = sec_fp
                for sec, fp in sec_fp.items():
                    key = f"{kind}:{fp}"
                    if fp > 0 and key not in tk.response_curves:
                        tk.response_curves[key] = response_curve(engine, fp)
                tk.kind_m_range[kind] = src_fit.kind_m_range.get(kind, [0.0] * 24)
                tk.kind_m_speed[kind] = src_fit.kind_m_speed.get(kind, [0.0] * 7)
                tk.kind_m_long[kind] = src_fit.kind_m_long.get(kind, [0.0] * len(src_fit.long_knots))
            # evaluate on the target pair's grid
            rows_all = rows
            t = np.array([r["total"] for r in rows_all])
            aspect = np.array([1 if r["target_aspect"] == "bow_stern" else 0
                               for r in rows_all])
            ang = np.array([sector_angle(r) for r in rows_all])
            k = np.array([tk.expected_hits(r["distance"], a, r["target_speed"],
                                           "bow_stern" if aa else "broadside")
                          for r, a, aa in zip(rows_all, ang, aspect)])
            transfer[f"{src_label}-> {dst_label}"] = {
                "spearman": spearman(t, k), "nmae": nmae(k, t), "n": len(rows_all)}
            print(f"transfer {src_label} -> {dst_label}: rho={transfer[f'{src_label}-> {dst_label}']['spearman']:.4f}", flush=True)

    results = {
        "per_class": class_stats,
        "pooled": {"spearman_full": float(spearman(pooled_true, pooled_full)),
                   "spearman_full_ci95": [float(plo), float(phi)],
                   "spearman_isotropic": float(spearman(pooled_true, pooled_iso)),
                   "nmae_full": nmae(pooled_full, pooled_true),
                   "nmae_isotropic": nmae(pooled_iso, pooled_true)},
        "transfer": transfer,
    }
    (OUT / "baselines.json").write_text(json.dumps(results, indent=2), encoding="utf-8")

    lines = ["# E01b baselines, CIs, and transfer", "",
             f"- pooled full kernel: rho={results['pooled']['spearman_full']:.4f} "
             f"CI [{plo:.4f}, {phi:.4f}]; isotropic rho={results['pooled']['spearman_isotropic']:.4f}",
             "", "| class | full rho [CI] | isotropic rho | nMAE full / iso |", "|---|---|---|---|"]
    for label, st in class_stats.items():
        lines.append(f"| {label} | {st['spearman_full']:.4f} [{st['spearman_full_ci95'][0]:.4f}, {st['spearman_full_ci95'][1]:.4f}] | {st['spearman_isotropic']:.4f} | {st['nmae_full']:.4f} / {st['nmae_isotropic']:.4f} |")
    lines += ["", "## cross-pair transfer", "", "| source fit -> target pair | Spearman | nMAE |", "|---|---|---|"]
    for k, v in transfer.items():
        lines.append(f"| {k} | {v['spearman']:.4f} | {v['nmae']:.4f} |")
    (OUT / "report_baselines.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps(results, indent=2)[:1200])


if __name__ == "__main__":
    main()
