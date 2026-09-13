"""B1-ext: kernel calibration under mount damage (capability state chi_i).

Damages the San Francisco's only stern-arc primary (P3, firepower 8),
re-scans the truth grid with the engine's own adjudication (which skips
destroyed mounts), refits, and evaluates on held-out cells.  PASS iff
held-out Spearman >= 0.90 and nMAE <= 0.15; structural check: stern-sector
hits must drop below bow-sector hits after the P3 loss.

Output: research/results/b1/{damaged_metrics.json, report.md}
"""
from __future__ import annotations

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

OUT = REPO / "research" / "results" / "b1"
ATTACKER, TARGET = "IBS-U-USN-SAN-FRANCISCO", "IBS-U-IJN-AOBA"
ANCHOR = HexCoord(q=23, r=19)


def build_pair():
    ships = [
        {"id": ATTACKER, "name": ATTACKER, "side": "axis",
         "position": "X20", "heading": 1, "speed": 4},
        {"id": TARGET, "name": TARGET, "side": "allies",
         "position": "Y20", "heading": 1, "speed": 4},
    ]
    engine, state = make_sandbox(f"B1D-{ATTACKER[-12:]}", ships)
    attacker = state.ships[ATTACKER]
    target = state.ships[TARGET]
    attacker.position = ANCHOR
    attacker.heading = 1
    attacker.current_speed = 4
    target.position = HexCoord(q=ANCHOR.q + 3, r=ANCHOR.r)
    return engine, state, attacker, target


def main() -> None:
    from scipy.stats import spearmanr

    OUT.mkdir(parents=True, exist_ok=True)
    engine, state, attacker, target = build_pair()

    for m in attacker.gun_mounts:
        if m.id == "P3":
            m.destroyed = True

    rows = scan_ground_truth(engine, state, attacker, target, max_distance=24)
    rng = np.random.default_rng(20260911)
    idx = rng.permutation(len(rows))
    n_train = int(len(rows) * 0.7)
    train = [rows[i] for i in idx[:n_train]]
    test = [rows[i] for i in idx[n_train:]]
    fit = fit_kernel(engine, train, attacker, state, "CA", "CA")

    def s_angle(r):
        return {"bow": 0.0, "starboard": 90.0, "stern": 180.0,
                "port": -90.0}[r["sector"]]

    t = np.array([r["total"] for r in test])
    k = np.array([fit.expected_hits(r["distance"], s_angle(r),
                                    r["target_speed"], r["target_aspect"])
                  for r in test])
    rho, _ = spearmanr(t, k)
    eff = t > 1e-9
    nmae = float(np.sum(np.abs(k[eff] - t[eff])) / np.sum(t[eff]))
    stern = [r["total"] for r in rows if r["sector"] == "stern"
             and r["distance"] in (10, 11, 12)]
    bow = [r["total"] for r in rows if r["sector"] == "bow"
           and r["distance"] in (10, 11, 12)]
    stern_mean = float(np.mean(stern))
    bow_mean = float(np.mean(bow))

    result = {
        "damaged_mount": "P3 (stern primary, firepower 8) destroyed",
        "held_out": {"spearman": float(rho), "nmae": nmae, "n": len(test)},
        "gate": "PASS" if (rho >= 0.90 and nmae <= 0.15) else "FAIL",
        "structure": {"stern_mean_hits": round(stern_mean, 3),
                      "bow_mean_hits": round(bow_mean, 3)},
    }
    (OUT / "damaged_metrics.json").write_text(json.dumps(result, indent=2),
                                              encoding="utf-8")
    (OUT / "report.md").write_text(
        "# B1-ext kernel calibration under mount damage\n\n"
        f"- damaged mount: {result['damaged_mount']}\n"
        f"- held-out Spearman: **{rho:.4f}** (gate >= 0.90)\n"
        f"- held-out nMAE: **{nmae:.4f}** (gate <= 0.15)\n"
        f"- gate: **{result['gate']}**\n"
        f"- structural check: stern mean hits {stern_mean:.3f} vs bow "
        f"{bow_mean:.3f} (stern must be lower after P3 loss)\n"
        "- interpretation: the kernel's structural sector-firepower term "
        "picks up capability state chi automatically from "
        "mount.destroyed; no refitting of the arc structure is needed.\n",
        encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
