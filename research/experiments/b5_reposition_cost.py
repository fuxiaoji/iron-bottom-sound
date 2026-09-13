"""B5: nonholonomic lateral reposition cost (v2: fine d grid + diagnostics).

Task: a target sits d_perp hexes to B's flank, 16 hexes ahead on a shared
parallel course.  B executes the classic lateral reposition: turn out
90 deg (3 turns of +30 deg/turn) toward the flank line, run
perpendicular as needed, turn back 90 deg, hold on the new abeam course.

v1 artifact diagnosis (why C_reposition was identical for d=2/4/6):
  1. Axis swap: v1 spawned R at (d_perp, -16) on a +x course, so d_perp
     varied the LONGITUDINAL separation and the 16-hex separation was the
     lateral one.  d=2..8 only moved the range from 16.1 to 17.9 hex.
  2. Turn-away + kernel clip: the v1 template turned B AWAY from the
     target, so range grew 16 -> 44 hex within 5 turns, past the kernel's
     24-hex clip, where the port/starboard sectors are mirror-identical
     and L = 0 exactly.  The only surviving event was the |delta| >= 150
     end-on aspect flip at t=3, which triggered for d <= 6 (d_b = -155
     to -162) but not d = 8 (-149.5) -- hence the single 0.258-vs-0 step.
  3. Coupling no-op: v1 computed turning pulses as round(|30 deg|/60) =
     round(0.5) = 0 (banker's rounding) for EVERY turn of the +-30
     deg/turn template, so engine_coupled always advanced at full speed
     and was numerically identical to independent.

v2 changes:
  - Geometry per the documented scenario: shared course along +x, R at
    (16, +d_perp), B turns TOWARD the flank line (+y).
  - d_perp grid {0, 1, ..., 10} (11 values).
  - Per-run diagnostics: T_repos (first crossing of R's course line, i.e.
    lateral-offset elimination turn), heading excursion, path length,
    min range, time in firing envelope (L>0, L<0, |L|~0).
  - engine_coupled advance factor per turning turn:
        (3 - |dh|/60) / 3 = 1 - |dh|/180
    (each 60-deg turning pulse of the turn's 3 displacement pulses is
    consumed by turning; fractional pulses, so 30 deg/turn costs 1/6 of
    that turn's advance).  independent: full advance every turn.

Output (overwrites): research/results/b5/{cost_curve.csv, results.json,
report.md, fig_b5_cost.png}
"""
from __future__ import annotations

import csv
import json
import math
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "backend" / "src"))
sys.path.insert(0, str(REPO))

from research.geometry.committed_game import KernelWrap  # noqa: E402
from research.geometry.firepower_kernel import KernelFit  # noqa: E402

OUT = REPO / "research" / "results" / "b5"

T = 24
GAMMA = 0.96
RANGE_AHEAD = 16.0          # longitudinal separation along the shared course
D_GRID = list(range(0, 11))  # d_perp in hex: 0..10
ETA_V_GRID = (0.8, 1.0, 1.25)
COUPLINGS = ("independent", "engine_coupled")
BEAM_TOL = 0.5              # "on the flank line" tolerance (half a hex)


def wrap_deg(a: float) -> float:
    return (a + 180.0) % 360.0 - 180.0


def advance_factor(dh_deg: float, coupling: str) -> float:
    """Displacement fraction of a turn's 3 movement pulses.

    independent    : turning turns advance at full speed (surrogate default).
    engine_coupled : each 60-deg turning pulse produces no displacement, so a
                     turn of dh degrees consumes dh/60 of the 3 pulses:
                     factor = (3 - dh/60)/3 = 1 - dh/180.
    """
    if coupling == "engine_coupled":
        return 1.0 - min(abs(dh_deg), 180.0) / 180.0
    return 1.0


def build_plan(d_perp: float, v: float, coupling: str) -> tuple[list[float], int]:
    """Turn out 90 (3x+30), run perpendicular only as needed, turn back 90.

    Returns (heading deltas, number of perpendicular-run turns)."""
    turn_out = [30.0] * 3
    turn_back = [-30.0] * 3
    # lateral gain of the out+back template; the gain of each turn is set by
    # the CUMULATIVE heading after applying the delta (move uses post-turn
    # heading), not by the delta itself
    g = 0.0
    h = 0.0
    for dh in turn_out + turn_back:
        h = wrap_deg(h + dh)
        g += v * advance_factor(dh, coupling) * math.sin(math.radians(h))
    v_perp = v * advance_factor(90.0, coupling)
    k_run = max(0, math.ceil((d_perp - g) / v_perp)) if v_perp > 0 else 0
    plan = turn_out + [0.0] * k_run + turn_back + [0.0] * (T - 6 - k_run)
    return plan, k_run


def _fire_differential(kB, kR, r, d_b, d_r):
    a_b = "bow_stern" if (abs(d_b) <= 30 or abs(d_b) >= 150) else "broadside"
    a_r = "bow_stern" if (abs(d_r) <= 30 or abs(d_r) >= 150) else "broadside"
    return kB.fire(r, d_b, 6, a_r) - kR.fire(r, d_r, 6, a_b)


def run_maneuver(kB, kR, turns_b, v, d_perp, coupling) -> dict:
    """B executes the reposition plan; R holds the shared course.

    Course axis +x (heading 0); R starts (RANGE_AHEAD, +d_perp) and sails
    straight.  Gunnery then movement each turn (v1 ordering, preserved).
    """
    xB = yB = 0.0
    xR, yR = RANGE_AHEAD, float(d_perp)
    hB = hR = 0.0
    J = 0.0
    disc = 1.0
    heading_exc = 0.0
    path_len = 0.0
    min_r = math.inf
    t_lpos = t_lneg = t_lzero = 0
    t_repos = -1
    min_offset = math.inf
    for t in range(T):
        dx, dy = xR - xB, yR - yB
        r = max(math.hypot(dx, dy), 0.5)
        bearing = math.degrees(math.atan2(dy, dx))
        d_b = wrap_deg(bearing - hB)
        d_r = wrap_deg(bearing + 180.0 - hR)
        L = _fire_differential(kB, kR, r, d_b, d_r)
        J += disc * L
        disc *= GAMMA
        min_r = min(min_r, r)
        if L > 1e-12:
            t_lpos += 1
        elif L < -1e-12:
            t_lneg += 1
        else:
            t_lzero += 1
        offset = abs(yR - yB)
        min_offset = min(min_offset, offset)
        if t_repos < 0 and yB >= yR - 1e-9:
            t_repos = t  # first crossing of R's course line (offset eliminated)
        dh = turns_b[t]
        heading_exc += abs(dh)
        hB = wrap_deg(hB + dh)
        f = advance_factor(dh, coupling)
        step = v * f
        xB += step * math.cos(math.radians(hB))
        yB += step * math.sin(math.radians(hB))
        xR += v * math.cos(math.radians(hR))
        yR += v * math.sin(math.radians(hR))
        path_len += step
    if t_repos < 0:
        # check t = 0 / final state: offset already eliminated before t = 1
        t_repos = 0 if d_perp <= 0.0 else -1
    return {"J": J, "T_repos": t_repos, "heading_excursion_deg": heading_exc,
            "path_length": path_len, "min_range": min_r,
            "t_Lpos": t_lpos, "t_Lneg": t_lneg, "t_Lzero": t_lzero,
            "min_lateral_offset": min_offset}


def run_stay(kB, kR, v, d_perp) -> float:
    """Both ships hold the shared parallel course (no turning -> coupling
    irrelevant).  Gunnery then movement, same ordering."""
    xB = yB = 0.0
    xR, yR = RANGE_AHEAD, float(d_perp)
    hB = hR = 0.0
    J = 0.0
    disc = 1.0
    for _ in range(T):
        dx, dy = xR - xB, yR - yB
        r = max(math.hypot(dx, dy), 0.5)
        bearing = math.degrees(math.atan2(dy, dx))
        d_b = wrap_deg(bearing)
        d_r = wrap_deg(bearing + 180.0)
        J += disc * _fire_differential(kB, kR, r, d_b, d_r)
        disc *= GAMMA
        xB += v
        xR += v
    return J


def main() -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    OUT.mkdir(parents=True, exist_ok=True)
    fits = json.load(open(REPO / "research" / "results" / "e01" / "kernel_fits.json"))
    kB = KernelWrap(KernelFit.from_dict(fits["CA"]))
    kR = KernelWrap(KernelFit.from_dict(fits["CA"]))

    results = []
    for eta_v in ETA_V_GRID:
        v = 6.0 * eta_v
        for coupling in COUPLINGS:
            for d_perp in D_GRID:
                plan, k_run = build_plan(d_perp, v, coupling)
                man = run_maneuver(kB, kR, plan, v, d_perp, coupling)
                j_stay = run_stay(kB, kR, v, d_perp)
                j_man = man["J"]
                results.append({
                    "eta_v": eta_v,
                    "coupling": coupling,
                    "d_perp": d_perp,
                    "run_turns": k_run,
                    "T_repos": man["T_repos"],
                    "heading_excursion_deg": round(man["heading_excursion_deg"], 1),
                    "path_length_hex": round(man["path_length"], 3),
                    "min_range_hex": round(man["min_range"], 3),
                    "t_firing_envelope_Lpos": man["t_Lpos"],
                    "t_Lneg": man["t_Lneg"],
                    "t_Lzero": man["t_Lzero"],
                    "min_lateral_offset_hex": round(man["min_lateral_offset"], 3),
                    "J_stay": round(j_stay, 4),
                    "J_maneuver": round(j_man, 4),
                    "C_reposition": round(j_stay - j_man, 4),
                })

    # ---- platform-effect check: does C still fail to vary with d? ----
    platform = {"tol": 1e-9, "series": []}
    for eta_v in ETA_V_GRID:
        for coupling in COUPLINGS:
            cs = [r["C_reposition"] for r in results
                  if r["eta_v"] == eta_v and r["coupling"] == coupling]
            spread = float(np.max(cs) - np.min(cs))
            n_distinct = len({round(c, 9) for c in cs})
            platform["series"].append({
                "eta_v": eta_v, "coupling": coupling,
                "n_distinct_C": n_distinct, "spread": round(spread, 6),
                "flat": bool(spread < platform["tol"]),
            })
    n_flat = sum(1 for s in platform["series"] if s["flat"])
    platform["n_flat_series"] = n_flat
    platform["n_series"] = len(platform["series"])
    platform["verdict"] = ("PLATFORM EFFECT PERSISTS: C_reposition is still "
                           "independent of d_perp -> real structure, not an "
                           "artifact" if n_flat == len(platform["series"]) else
                           "PLATFORM EFFECT GONE: C_reposition now varies with "
                           "d_perp (v1 flatness was an artifact)")

    json.dump({"meta": {
        "scenario": ("shared course +x; R at (16, d_perp) sailing straight; "
                     "B turns toward the flank line: 90 out (3x+30), "
                     "perpendicular run as needed, 90 back (3x-30), hold abeam"),
        "fixes_vs_v1": ["d_perp now truly lateral (v1 had it longitudinal)",
                        "turn toward (not away from) the flank line",
                        "coupling factor 1 - |dh|/180 (v1 round(|dh|/60) was "
                        "always 0 for 30-deg turns -> coupling was a no-op)",
                        "d_perp grid 0..10 (11 values, was {2,4,6,8})"],
        "coupling_semantics": {"independent": "full advance in turning turns",
                               "engine_coupled": "advance factor 1 - |dh|/180"},
        "kernel": "e01 CA fit, both sides", "T": T, "gamma": GAMMA,
        "range_ahead_hex": RANGE_AHEAD, "d_grid": D_GRID,
        "eta_v_grid": list(ETA_V_GRID),
        "T_repos_def": "first turn at which B crosses R's course line "
                       "(lateral offset eliminated; -1 = never within T)",
    },
        "platform_effect": platform, "results": results},
        open(OUT / "results.json", "w"), indent=2)

    cols = list(results[0].keys())
    with (OUT / "cost_curve.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(cols)
        for r in results:
            w.writerow([r[c] for c in cols])

    # ---- figure: cost curve + T_repos ----
    fig, (ax, ax2) = plt.subplots(1, 2, figsize=(11.0, 4.4))
    for coupling, ls in (("independent", "--"), ("engine_coupled", "-")):
        for eta_v, mk in ((0.8, "o"), (1.0, "s"), (1.25, "^")):
            sel = sorted([r for r in results if r["eta_v"] == eta_v
                          and r["coupling"] == coupling],
                         key=lambda r: r["d_perp"])
            ax.plot([r["d_perp"] for r in sel], [r["C_reposition"] for r in sel],
                    ls, marker=mk, ms=4,
                    label=f"eta_v={eta_v} {coupling.split('_')[0]}")
            ax2.step([r["d_perp"] for r in sel], [r["T_repos"] for r in sel],
                     ls, where="post")
    ax.set_xlabel(r"lateral offset $d_\perp$ (hex)")
    ax.set_ylabel(r"$C_{reposition} = J_{stay} - J_{maneuver}$")
    ax.set_title("B5 v2: lateral reposition cost (CA duel)")
    ax.legend(fontsize=7)
    ax2.set_xlabel(r"lateral offset $d_\perp$ (hex)")
    ax2.set_ylabel("$T_{repos}$ (turns to flank line, -1 = never)")
    ax2.set_title("offset-elimination turn")
    fig.tight_layout()
    fig.savefig(OUT / "fig_b5_cost.png", dpi=160, bbox_inches="tight")
    plt.close(fig)

    # ---- report ----
    lines = ["# B5 nonholonomic reposition cost (v2, refined)", "",
             "Scenario: R 16 hex ahead on a shared course, d_perp lateral;",
             "B: 90-deg turn out toward the flank line, run as needed, turn",
             "back, hold abeam.  C = J_stay - J_maneuver (discounted, T=24).", "",
             "## v1 artifact diagnosis",
             "- v1 placed R at (d_perp, -16) on a +x course: d_perp was",
             "  longitudinal, so d = 2/4/6 only moved range 16.1 -> 17.1 hex.",
             "- v1 turned B away from R: range left the 24-hex kernel clip by",
             "  t=3; the only d-sensitivity was the |delta|>=150 end-on flip,",
             "  which fired for d<=6 but not d=8 -> the single 0.258-vs-0 step.",
             "- v1 coupling was a no-op: round(30/60)=0 pulses on every turn,",
             "  so engine_coupled == independent to machine precision.", "",
             "## Results", "",
             "| d | coupling | eta_v | T_repos | head.exc | path | min r | L>0 "
             "| J_stay | J_man | C |",
             "|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in results:
        lines.append(
            f"| {r['d_perp']} | {r['coupling']} | {r['eta_v']} "
            f"| {r['T_repos']} | {r['heading_excursion_deg']:.0f} "
            f"| {r['path_length_hex']:.1f} | {r['min_range_hex']:.1f} "
            f"| {r['t_firing_envelope_Lpos']} | {r['J_stay']:+.3f} "
            f"| {r['J_maneuver']:+.3f} | {r['C_reposition']:+.3f} |")
    lines += ["", "## Platform-effect check",
              f"- flat (d-independent) series: {n_flat}/{len(platform['series'])}",
              f"- verdict: {platform['verdict']}"]
    for s in platform["series"]:
        lines.append(f"  - eta_v={s['eta_v']} {s['coupling']}: "
                     f"{s['n_distinct_C']} distinct C values, "
                     f"spread={s['spread']:.4f}, flat={s['flat']}")
    (OUT / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(platform["verdict"])
    print(json.dumps(platform["series"], indent=1))
    print(f"wrote {OUT}/{{cost_curve.csv, results.json, report.md, fig_b5_cost.png}}")


if __name__ == "__main__":
    main()
