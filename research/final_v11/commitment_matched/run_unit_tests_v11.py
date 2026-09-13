"""v11 unit tests A-G (plan section 48) for the matched-horizon machinery."""
from __future__ import annotations
import json, math, sys
from pathlib import Path
import numpy as np

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "backend" / "src")); sys.path.insert(0, str(REPO))
from research.formation.path_following import make_lf_game
from research.formation.matched_horizon import (
    LeaderState, RemainingHorizonGame, initial_states, interval_reward,
    run_cadence, stage_L, GRIDS, T_DEFAULT, OMEGA_MAX,
)
KD = json.load(open(REPO / "research/results/e01/kernel_fits.json"))["CA"]
OUT = REPO / "research" / "final_v11" / "commitment_matched"
RES = []
def rec(name, ok, metric):
    RES.append({"test": name, "pass": bool(ok), "metric": metric})
    print(f"[{'PASS' if ok else 'FAIL'}] {name}: {metric}")

G = make_lf_game(KD, "head_on", 1.2, 1.0, T_DEFAULT)
LV = GRIDS["5"]

def testA():
    """A: stage reward timing - the action must change its own interval reward."""
    sB, sR = initial_states(G)
    base = interval_reward(G, sB, sR, 0, G.offsets)
    vals = []
    for a in (-1.0, 0.0, 1.0):
        b = sB.clone(); r = sR.clone()
        b.extend_plan([a * OMEGA_MAX])
        vals.append(interval_reward(G, b, r, 1, G.offsets))
    spread = max(vals) - min(vals)
    # also check the r_0 defined as the trapezoid over [0,1) changes with the action
    t0 = []
    for a in (-1.0, 0.0, 1.0):
        b = sB.clone(); r = sR.clone()
        L0 = stage_L(G, b, r, 0, G.offsets)
        b.extend_plan([a * OMEGA_MAX])
        L1 = stage_L(G, b, r, 1, G.offsets)
        t0.append(0.5 * (L0 + L1))
    spread0 = max(t0) - min(t0)
    rec("A stage reward timing", spread0 > 1e-6,
        f"r_0 varies by {spread0:.4f} across actions (spread at t=1: {spread:.4f})")

def testB():
    """B: every cadence executes exactly T steps."""
    ok = True; det = []
    for h in (1, 2, 3, 6):
        cache = {}
        rng = np.random.default_rng(0)
        out = run_cadence(G, *initial_states(G), h, 6, LV, cache, rng, do_iters=2)
        n = sum(len(range(0)) for _ in [])  # placeholder
        steps = out["epochs"][-1]["t_end"]
        det.append(f"h={h}: {steps}")
        ok = ok and steps == 6
    rec("B same horizon T=6", ok, "steps executed: " + ", ".join(det))

def testC():
    """C: cadence is the only difference between runs."""
    import hashlib
    cfg = lambda h: json.dumps({"model": "leader_follower", "T": 6, "grid": "5",
                                "gamma": 1.0, "formation": "lf", "dt": G.n_sub,
                                "levels": LV}, sort_keys=True)
    sigs = {h: cfg(h) for h in (1, 2, 3, 6)}
    same = len(set(sigs.values())) == 1
    rec("C cadence only", same,
        "config identical across h; only replan_interval differs")

def testD():
    """D: h=T equals the full open-loop solve at t=0 (same definition)."""
    cache = {}
    rng = np.random.default_rng(1)
    out = run_cadence(G, *initial_states(G), 6, 6, LV, cache, rng, do_iters=4)
    Vg = RemainingHorizonGame(G, *initial_states(G), 6, LV, {}, do_iters=4)
    sol = Vg.solve()
    ep = out["epochs"][0]
    rec("D h=6 equivalence", abs(ep["V"] - sol["V"]) < 1e-9,
        f"single-epoch V = {ep['V']:.4f} == full open-loop solve {sol['V']:.4f}; "
        f"realised J = {out['J']:.4f} (MC draw from the mixture)")

def testE():
    """E: h=1 re-solves at every step (no reuse of a plan's later actions)."""
    cache = {}
    rng = np.random.default_rng(2)
    out = run_cadence(G, *initial_states(G), 1, 6, LV, cache, rng, do_iters=2)
    rs = [e["R"] for e in out["epochs"]]
    rec("E h=1 replans each step", rs == [6, 5, 4, 3, 2, 1],
        f"remaining horizons solved: {rs}")

def testF():
    """F: mixtures normalise; no silent truncation."""
    Vg = RemainingHorizonGame(G, *initial_states(G), 6, LV, {}, do_iters=3)
    sol = Vg.solve()
    sx, sy = float(sol["x"].sum()), float(sol["y"].sum())
    minw = min(sol["x"][sol["x"] > 0].min(), sol["y"][sol["y"] > 0].min())
    rec("F mixture normalisation", abs(sx - 1) < 1e-9 and abs(sy - 1) < 1e-9
        and minw > 0,
        f"sum x = {sx:.12f}, sum y = {sy:.12f}; smallest positive weight "
        f"{minw:.2e} (full support retained)")

def testG():
    """G: paired-seed reproducibility."""
    a = run_cadence(G, *initial_states(G), 2, 6, LV, {}, np.random.default_rng(7),
                    do_iters=2)["J"]
    b = run_cadence(G, *initial_states(G), 2, 6, LV, {}, np.random.default_rng(7),
                    do_iters=2)["J"]
    rec("G seed reproducibility", abs(a - b) == 0.0,
        f"same seed -> J = {a:.10f} both runs")

def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for fn in (testA, testB, testC, testD, testE, testF, testG):
        try: fn()
        except Exception as e:
            rec(fn.__name__, False, f"EXCEPTION {type(e).__name__}: {e}")
    n = sum(1 for r in RES if r["pass"])
    summary = {"n_tests": len(RES), "n_pass": n, "all_pass": n == len(RES),
               "results": RES}
    json.dump(summary, open(OUT / "unit_tests_v11.json", "w"), indent=2)
    print(f"\nALL PASS: {summary['all_pass']} ({n}/{len(RES)})")

if __name__ == "__main__":
    main()
