"""v10 Phase 4/5: representative sensitivity checks (plan sections 25-28).

Phase 4 -- reposition cost (v10 section 25).  NOT a rerun of the old dense
B5 grid: three turn severities (gentle / medium / tight) x three
representative cells, comparing the reposition cost
    C_reposit = J(manoeuvre) - J(hold straight)
under the rigid line-ahead baseline and the leader-follower model, together
with path length, manoeuvre time, heading dispersion and minimum range.

Phase 5 -- delayed-threat sensitivity (v10 sections 27-28).  Question: does
the mechanism (coverage + local intensity + alternative-response landscape)
survive leader-follower motion?  For three geometry anchors we build the
near-optimal plan set B_eps from the frozen Grid-5 space under the gun
payoff, then add a delayed threat: plans whose trajectory enters the hazard
corridor at the hazard time are penalised in proportion to the threat
intensity, and we measure the response-set contraction

    C_resp = 1 - |B_eps^H| / |B_eps|

for both representations, at two coverage levels (narrow corridor vs broad
corridor) and two intensities.  This is a mechanism check, not a new sweep.

Outputs: research/final_v10/{reposition_sensitivity, torpedo_sensitivity}/
"""
from __future__ import annotations

import csv
import itertools
import json
import math
import sys
import time
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "backend" / "src"))
sys.path.insert(0, str(REPO))

from research.formation.path_following import (  # noqa: E402
    LeaderPath, batch_payoff_lf, line_ahead_offsets, make_lf_game,
)
from research.experiments.v10_bridge import batch_payoff_rigid_la  # noqa: E402

KD = json.load(open(REPO / "research" / "results" / "e01" / "kernel_fits.json"))["CA"]
H = 6
OMEGA_MAX = 60.0
GRID5 = (-1.0, -0.5, 0.0, 0.5, 1.0)
REPOUT = REPO / "research" / "final_v10" / "reposition_sensitivity"
THREATOUT = REPO / "research" / "final_v10" / "torpedo_sensitivity"

SEVERITIES = {"gentle": 20.0, "medium": 40.0, "tight": 60.0}
CASES = [("head_on", 1.0), ("parallel", 1.2), ("crossing", 0.8)]


def plans_grid5():
    return np.array(list(itertools.product(GRID5, repeat=H))) * OMEGA_MAX


# ------------------------------------------------------------ Phase 4
def reposition():
    REPOUT.mkdir(parents=True, exist_ok=True)
    rows = []
    for name, omega in SEVERITIES.items():
        for geometry, eta_r in CASES:
            for model in ("rigid", "lf"):
                mode = "rigid_line_ahead" if model == "rigid" else "leader_follower"
                g = make_lf_game(KD, geometry, eta_r, 1.0, H, formation_mode=mode)
                # three-turn manoeuvre then straight (engine turn granularity)
                man = np.array([omega] + [0.0] * (H - 1))
                hold = np.zeros(H)
                opp = np.zeros(H)
                J_man = float(g.payoff(man, opp, 1))
                J_hold = float(g.payoff(hold, opp, 1))
                # trajectory diagnostics of the manoeuvring side
                if mode == "leader_follower":
                    p = LeaderPath.from_sequence(g, "B", man, H, g.n_sub)
                    pos = np.array([p.vessel_states(t, g.offsets)[0]
                                    for t in range(H)])
                    psi = np.array([p.vessel_states(t, g.offsets)[1]
                                    for t in range(H)])
                else:
                    from research.formation.path_following import vessel_states_rigid_line_ahead
                    pos = np.array([vessel_states_rigid_line_ahead(g, man, "B", t)[0]
                                    for t in range(H)])
                    psi = np.array([vessel_states_rigid_line_ahead(g, man, "B", t)[1]
                                    for t in range(H)])
                lead = pos[:, 0, :]
                path_len = float(np.hypot(*np.diff(lead, axis=0).T).sum())
                disp = max(float(np.ptp(np.unwrap(np.radians(psi[t]))) * 180 / math.pi)
                           for t in range(H))
                # minimum range between formations (nearest vessel pair, all t)
                min_r = float("inf")
                for t in range(H):
                    if mode == "leader_follower":
                        q = LeaderPath.from_sequence(g, "R", opp, H, g.n_sub)
                        pr = q.vessel_states(t, g.offsets)[0]
                    else:
                        from research.formation.path_following import vessel_states_rigid_line_ahead
                        pr = vessel_states_rigid_line_ahead(g, opp, "R", t)[0]
                    for a in range(g.n_ships):
                        for b in range(g.n_ships):
                            min_r = min(min_r, float(np.hypot(*(pos[t, a] - pr[b]))))
                rows.append({"severity": name, "omega_deg": omega,
                             "geometry": geometry, "eta_r": eta_r, "model": mode,
                             "J_manoeuvre": round(J_man, 4),
                             "J_hold": round(J_hold, 4),
                             "C_reposition": round(J_man - J_hold, 4),
                             "path_length": round(path_len, 3),
                             "manoeuvre_turns": 1,
                             "heading_dispersion_deg": round(disp, 2),
                             "min_range": round(min_r, 3)})
    with open(REPOUT / "reposition_cells.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader(); w.writerows(rows)
    # qualitative trend comparison
    trend = {}
    for model in ("rigid_line_ahead", "leader_follower"):
        pts = []
        for name in SEVERITIES:
            sub = [r for r in rows if r["model"] == model and r["severity"] == name]
            pts.append(float(np.mean([r["C_reposition"] for r in sub])))
        trend[model] = pts
    same_dir = all((trend["rigid_line_ahead"][i + 1] - trend["rigid_line_ahead"][i])
                   * (trend["leader_follower"][i + 1] - trend["leader_follower"][i]) >= 0
                   for i in range(len(SEVERITIES) - 1))
    summary = {"trend_by_severity": trend,
               "qualitative_trend_preserved": bool(same_dir)}
    json.dump(summary, open(REPOUT / "reposition_summary.json", "w"), indent=2)
    lines = ["# v10 Phase 4: reposition-cost sensitivity", "",
             "| severity | model | C_reposition (mean over cells) |", "|---|---|---|"]
    for model, pts in trend.items():
        for name, v in zip(SEVERITIES, pts):
            lines.append(f"| {name} | {model} | {v:+.3f} |")
    lines += ["", f"Qualitative trend preserved: **{same_dir}**", "",
              "| severity | geometry | eta_r | model | J_man | J_hold | C_reposit | path len | heading disp | min range |",
              "|---|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        lines.append(f"| {r['severity']} | {r['geometry']} | {r['eta_r']} | {r['model']} "
                     f"| {r['J_manoeuvre']:+.3f} | {r['J_hold']:+.3f} "
                     f"| {r['C_reposition']:+.3f} | {r['path_length']:.1f} "
                     f"| {r['heading_dispersion_deg']:.1f} | {r['min_range']:.1f} |")
    (REPOUT / "reposition_report.md").write_text("\n".join(lines), encoding="utf-8")
    print("[v10-P4] reposition done; trend preserved:", same_dir, flush=True)
    return summary


# ------------------------------------------------------------ Phase 5
def threat_contraction(model: str, geometry: str, eta_r: float,
                       corridor_halfwidth: float, intensity: float,
                       eps_frac: float = 0.05) -> dict:
    """Near-optimal response set contraction under a delayed threat."""
    mode = "rigid_line_ahead" if model == "rigid" else "leader_follower"
    g = make_lf_game(KD, geometry, eta_r, 1.0, H, formation_mode=mode)
    batch = batch_payoff_rigid_la if model == "rigid" else batch_payoff_lf
    plans = plans_grid5()
    n = len(plans)
    # payoff of every plan against a straight-holding opponent
    opp = np.zeros(H)
    J = batch(g, plans, opp, True)
    jmax = float(J.max())
    eps = eps_frac * max(1.0, abs(jmax))
    base = J >= (jmax - eps)
    # Delayed hazard band (v10 sections 27-28): a weapon launched at t_launch
    # arms a threat field at the position our own fleet would occupy if it HELD
    # COURSE, effective for turns t >= t_launch.  Plans that transit within
    # `corridor_halfwidth` of that arming point are threatened; the width is a
    # genuine coverage knob because a manoeuvring plan can leave the band.
    t_launch = 2
    hold = np.zeros(H)
    if mode == "leader_follower":
        p_hold = LeaderPath.from_sequence(g, "B", hold, H, g.n_sub)
        centre = p_hold.vessel_states(t_launch, g.offsets)[0]
    else:
        from research.formation.path_following import vessel_states_rigid_line_ahead as vsh
        centre = vsh(g, hold, "B", t_launch)[0]

    def in_band(pos_at_t) -> bool:
        for a in range(g.n_ships):
            for c in centre:
                if math.hypot(*(pos_at_t[a] - c)) <= corridor_halfwidth:
                    return True
        return False

    hit = np.zeros(n, dtype=bool)
    for i in range(n):
        seq = plans[i]
        p_i = LeaderPath.from_sequence(g, "B", seq, H, g.n_sub) \
            if mode == "leader_follower" else None
        for t in range(t_launch, H):
            if mode == "leader_follower":
                pb = p_i.vessel_states(t, g.offsets)[0]
            else:
                from research.formation.path_following import vessel_states_rigid_line_ahead as vs
                pb = vs(g, seq, "B", t)[0]
            if in_band(pb):
                hit[i] = True
                break
    # threatened near-optimal plans lose value proportional to intensity
    J_threat = J.copy()
    J_threat[hit & base] = J[hit & base] - intensity
    jmax_t = float(J_threat.max())
    eps_t = eps_frac * max(1.0, abs(jmax_t))
    after = J_threat >= (jmax_t - eps_t)
    b0 = int(base.sum())
    b1 = int((base & after).sum())
    c_resp = 1.0 - (b1 / max(b0, 1))
    return {"model": mode, "geometry": geometry, "eta_r": eta_r,
            "corridor_halfwidth": corridor_halfwidth, "intensity": intensity,
            "n_base": b0, "n_surviving": b1, "c_resp": round(c_resp, 4),
            "mean_direct_loss": round(float(np.mean(J[hit])) if hit.any() else 0.0, 4),
            "n_threatened": int(hit.sum())}


def torpedo():
    THREATOUT.mkdir(parents=True, exist_ok=True)
    rows = []
    for geometry, eta_r in [("head_on", 1.0), ("parallel", 1.2), ("crossing", 0.8)]:
        for model in ("rigid", "lf"):
            for halfwidth, intensity, label in ((3.0, 0.5, "narrow_weak"),
                                                (3.0, 2.0, "narrow_strong"),
                                                (8.0, 0.5, "broad_weak"),
                                                (8.0, 2.0, "broad_strong"),
                                                (14.0, 0.5, "wide_weak"),
                                                (14.0, 2.0, "wide_strong")):
                r = threat_contraction(model, geometry, eta_r, halfwidth, intensity)
                r["threat"] = label
                rows.append(r)
    with open(THREATOUT / "threat_contraction.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader(); w.writerows(rows)
    # mechanism check: does contraction respond to coverage AND intensity in
    # both representations, and do the representations agree?
    summ = {}
    for model in ("rigid_line_ahead", "leader_follower"):
        sub = [r for r in rows if r["model"] == model]
        c = {r["threat"]: r["c_resp"] for r in sub}
        coverage_effect = float(np.mean([c["broad_weak"] - c["narrow_weak"],
                                         c["broad_strong"] - c["narrow_strong"],
                                         c["wide_weak"] - c["broad_weak"],
                                         c["wide_strong"] - c["broad_strong"]]))
        intensity_effect = float(np.mean([c["narrow_strong"] - c["narrow_weak"],
                                          c["broad_strong"] - c["broad_weak"],
                                          c["wide_strong"] - c["wide_weak"]]))
        summ[model] = {"coverage_effect": round(coverage_effect, 4),
                       "intensity_effect": round(intensity_effect, 4),
                       "cells": c}
    # Mechanism statement (v10 sections 27-28): the v9 mechanism is threshold
    # + intensity + response landscape rather than coverage alone.  Report the
    # three properties explicitly for each representation.
    def props(m):
        c = summ[m]["cells"]
        return {
            "responds_to_intensity": bool(
                abs(c["narrow_strong"]) > abs(c["narrow_weak"]) or
                abs(c["broad_strong"]) > abs(c["broad_weak"])),
            "coverage_alone_insufficient": bool(
                abs(c["broad_weak"] - c["narrow_weak"]) < 1e-9 and
                abs(c["wide_weak"] - c["narrow_weak"]) < 1e-9),
            "thin_threat_gives_zero": bool(abs(c["narrow_weak"]) < 1e-9),
        }
    mech = {m: props(m) for m in summ}
    agree = all(mech["rigid_line_ahead"][k] == mech["leader_follower"][k]
                for k in mech["rigid_line_ahead"])
    summary = {"by_model": summ, "mechanism_agrees": bool(agree),
               "mechanism_properties": mech,
               "narrow_corridor_weak_intensity_is_zero":
                   all(abs(summ[m]["cells"]["narrow_weak"]) < 1e-9 for m in summ)}
    json.dump(summary, open(THREATOUT / "torpedo_summary.json", "w"), indent=2)
    lines = ["# v10 Phase 5: delayed-threat sensitivity under leader-follower motion", "",
             "| geometry | eta_r | model | threat | corridor | intensity | base set | surviving | C_resp |",
             "|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        lines.append(f"| {r['geometry']} | {r['eta_r']} | {r['model']} | {r['threat']} "
                     f"| {r['corridor_halfwidth']} | {r['intensity']} | {r['n_base']} "
                     f"| {r['n_surviving']} | {r['c_resp']:.3f} |")
    lines += ["", "## Mechanism check", "",
              "| model | coverage effect | intensity effect |", "|---|---|---|"]
    for m, v in summ.items():
        lines.append(f"| {m} | {v['coverage_effect']:+.4f} | {v['intensity_effect']:+.4f} |")
    lines += ["", f"Representations agree on the sign pattern: **{agree}**"]
    (THREATOUT / "torpedo_report.md").write_text("\n".join(lines), encoding="utf-8")
    print("[v10-P5] threat sensitivity done; mechanism agrees:", agree, flush=True)
    return summary


if __name__ == "__main__":
    t0 = time.time()
    s4 = reposition()
    s5 = torpedo()
    print(f"[v10-P4/P5] all done in {time.strftime('%H:%M:%S', time.gmtime(time.time() - t0))}")
