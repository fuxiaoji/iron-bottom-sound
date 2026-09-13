"""MUST-2 (v7): matched external engine validation — formation level.

Position (v7 5.1): external validity check of the reduced formation-level
OR model inside the Iron Bottom Sound rules engine.  NOT an AI benchmark:
only sign, ranking, and mechanism direction are compared.

Design — matched 2x2 commitment arms.  Both sides run the SAME policy class
(same model, same objective, same horizon, same action parameterisation);
the ONLY difference is replanning vs commitment (v7 5.4):

    arm   axis/allies   movement protocol
    F-F   fixed/fixed   both solve once at t=0, execute open-loop (frozen)
    R-R   react/react   both re-solve every turn (receding horizon)
    R-F   react/fixed   only axis replans   -> axis feedback premium
    F-R   fixed/react   only allies replans -> allies feedback premium

Scenarios: 3-vessel line-ahead formations per side (rigid column, 2-hex
astern spacing, matched `ca-american-1942` class on both sides), so any
paired damage differential isolates decision structure, not force
composition.  100 paired seeds per (cell, arm) with Common Random Numbers.

Cells (v7 5.5 minimum 12): {head_on, parallel, crossing} x range {12, 20}
x initial speed {4, 6}.

Model predictions: formation-level surrogate open-loop game value V_surr
per cell (same 3-vessel kernel aggregation as MUST-1, exact LP over the
legacy plan library, H=6).  Pre-specified gates (v7 5.6):
    sign agreement >= 80%   (sign of V_surr vs sign of engine axis margin, F-F)
    Spearman rho    >= 0.60 (V_surr vs engine axis margin across cells)
    pairwise ordering >= 75%
Verdict: PASS if all three; PARTIAL if sign >= 60% and rho >= 0.40 and
ordering >= 55%; else FAIL.  Definitions frozen before the run.

The true feedback premium is Delta_FB = J_receding - J_fixed (R-F vs F-F for
axis; F-R vs F-F for allies).  Legacy +5.14 numbers are NOT feedback
premiums (policy-class confound) and are not reported as such.

Output: research/results/final_v7/{must2_games.jsonl, must2_results.json,
must2_report.md}.
"""
from __future__ import annotations

import csv
import json
import math
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "backend" / "src"))
sys.path.insert(0, str(REPO))

from iron_bottom_sound.data import register_custom_scenario  # noqa: E402
from iron_bottom_sound.engine import IronBottomEngine  # noqa: E402
from iron_bottom_sound.models import (  # noqa: E402
    HexCoord,
    MovementOrder,
    OrderBatch,
    Phase,
    Side,
)
from research.geometry.firepower_kernel import KernelFit  # noqa: E402
from research.policies.geometry_policy import (  # noqa: E402
    GeometryPolicy,
    geometry_orders,
)
from research.geometry.committed_game import (  # noqa: E402
    KernelWrap,
    make_maneuver_library,
    open_loop_minimax,
)

OUT = REPO / "research" / "results" / "final_v7"
TEMPLATE = "ca-american-1942"
N_SHIPS = 3
GAP_HEX = 2          # astern spacing between column vessels
N_SEEDS = 100
TURNS = 8
B0 = HexCoord(q=10, r=4)

_DIRS = {  # (target hex, target heading) defining the initial geometry
    "parallel": (HexCoord(q=21, r=4), 2),
    "head_on": (HexCoord(q=22, r=11), 5),
    "crossing": (HexCoord(q=22, r=1), 5),
}
_RANGES = (12, 20)
_SPEEDS = (4, 6)
ARMS = ("F-F", "R-R", "R-F", "F-R")
_HEADING_DEG = {h: (330.0 + (h - 1) * 60.0) % 360.0 for h in range(1, 7)}
_AXIAL_DIRS = [(1, -1), (1, 0), (0, 1), (-1, 1), (-1, 0), (0, -1)]


def place_at(range_hex: int, base: HexCoord, target: HexCoord) -> HexCoord:
    """Hex nearest to `range_hex` along the base->target direction."""
    dq, dr = target.q - base.q, target.r - base.r
    s = range_hex / max(base.distance(target), 1)
    best, best_err = None, 1e9
    for fq in (int(np.floor(dq * s)), int(np.ceil(dq * s))):
        for fr in (int(np.floor(dr * s)), int(np.ceil(dr * s))):
            for dqo in (-1, 0, 1):
                for dro in (-1, 0, 1):
                    cand = HexCoord(q=base.q + fq + dqo, r=base.r + fr + dro)
                    err = abs(cand.distance(base) - range_hex)
                    if err < best_err:
                        best, best_err = cand, err
    return best


CELLS = []
for gname, (thex, theading) in _DIRS.items():
    for rng in _RANGES:
        for spd in _SPEEDS:
            # axis column: lead at B0, heading 2 (E06 convention), astern spacing
            ax_d = _AXIAL_DIRS[2 - 1]
            ax_hexes = [HexCoord(q=B0.q - ax_d[0] * GAP_HEX * k,
                                 r=B0.r - ax_d[1] * GAP_HEX * k).label
                        for k in range(N_SHIPS)]
            # ally column: lead placed at `rng` hexes from B0 toward thex
            ally_lead = place_at(rng, B0, thex)
            al_d = _AXIAL_DIRS[theading - 1]
            al_hexes = [HexCoord(q=ally_lead.q - al_d[0] * GAP_HEX * k,
                                 r=ally_lead.r - al_d[1] * GAP_HEX * k).label
                        for k in range(N_SHIPS)]
            CELLS.append({"geometry": gname, "range": rng, "speed": spd,
                          "axis_heading": 2, "ally_heading": theading,
                          "axis_hexes": ax_hexes, "ally_hexes": al_hexes,
                          "axis_lead": B0.label,
                          "true_range": ally_lead.distance(B0)})


def formation_scenario(cell: dict) -> dict:
    """Custom scenario definition: 3-vessel columns on both sides.

    Axis column at cell["axis_hexes"] (lead first, heading axis_heading);
    ally column at cell["ally_hexes"] (heading ally_heading, E06 geometry
    conventions)."""
    ships = []
    for k, hex_label in enumerate(cell["axis_hexes"]):
        ships.append({"id": f"AX-CA-{k + 1}", "name": f"AX-CA-{k + 1}",
                      "side": "axis", "template": TEMPLATE,
                      "position": hex_label, "heading": cell["axis_heading"],
                      "speed": cell["speed"]})
    for k, hex_label in enumerate(cell["ally_hexes"]):
        ships.append({"id": f"AL-CA-{k + 1}", "name": f"AL-CA-{k + 1}",
                      "side": "allies", "template": TEMPLATE,
                      "position": hex_label, "heading": cell["ally_heading"],
                      "speed": cell["speed"]})
    return {
        "id": f"IBS-CUSTOM-MUST2-{cell['geometry']}-{cell['range']}-{cell['speed']}",
        "title": f"MUST2 {cell['geometry']} r{cell['range']} v{cell['speed']}",
        "turns": TURNS,
        "visibility": {"axis": 20, "allies": 20},
        "optional_rules": [],
        "ships": ships,
    }


class FormationArmPolicy(GeometryPolicy):
    """GeometryPolicy whose commitment length is parametrised.

    commit_len=1  -> re-solve every turn (receding horizon)
    commit_len=99 -> solve once at t=0, execute the plan open-loop, then
                     hold the last course (frozen; no further re-solving)

    The lead vessel of the side solves; every vessel of the side translates
    the SAME desired heading delta into its own legal engine plan, so the
    column manoeuvres as a quasi-rigid formation (v7 formation semantics).
    """

    def __init__(self, kernel: KernelFit, horizon: int = 4, commit_len: int = 1):
        super().__init__(kernel, horizon=horizon, commit_turns=max(1, commit_len))
        self.commit_len = commit_len
        self.last_delta = 0.0

    def lead_delta(self, engine, state, side: Side) -> float:
        lead = None
        for s in state.ships.values():
            if s.side == side and not s.sunk and s.position:
                lead = s
                break
        if lead is None:
            self.last_delta = 0.0
            return 0.0
        enemy = self._nearest_enemy(state, lead)
        if enemy is None:
            self.last_delta = 0.0
            return 0.0
        geo = self._geometry(lead, enemy)
        if geo is None:
            self.last_delta = 0.0
            return 0.0
        r0, brg, hB, hR = geo
        if not self._committed or self._ship_key != lead.id:
            out = open_loop_minimax(
                self.kB, self.kR, self.lib, r0=r0, bearing0_deg=brg,
                headingB0_deg=hB, headingR0_deg=hR,
                vB=float(lead.current_speed), vR=float(enemy.current_speed),
                steps=self.horizon, gamma=0.9)
            plan = out["maximin_plan_B"]
            delta = float(plan.split("turn")[1]) if plan != "straight" else 0.0
            per_turn = delta / 3.0
            if self.commit_len >= 99:
                # frozen open-loop plan: full delta over 3 turns, then straight
                self._committed = [per_turn] * 3 + [0.0] * 96
            else:
                self._committed = [per_turn] * self.commit_len
            self._ship_key = lead.id
        self.last_delta = self._committed.pop(0)
        return self.last_delta


_KFITS: dict[str, KernelFit] = {}


def _kernel() -> KernelFit:
    if "fit" not in _KFITS:
        fits = json.load(open(REPO / "research" / "results" / "e01" / "kernel_fits.json"))
        _KFITS["fit"] = KernelFit.from_dict(fits["CA"])
    return _KFITS["fit"]



def surrogate_values() -> list[dict]:
    """Formation-level model prediction per cell (exact LP, H=6, v7 5.2)."""
    sys.path.insert(0, str(REPO / "research" / "experiments"))
    from must1_formation_do import FormationGame, seed_segments, restricted_lp, seg_setup
    rows = []
    lib = seed_segments(6, 1)
    for cell in CELLS:
        fit = _kernel()
        kB = KernelWrap(fit, 1.0)
        axis_pos = HexCoord.from_label(cell["axis_lead"])
        ally_pos = HexCoord.from_label(formation_scenario(cell)["ships"][N_SHIPS]["position"])
        r0 = float(axis_pos.distance(ally_pos))
        brg = math.degrees(math.atan2(
            (ally_pos.r - axis_pos.r + (ally_pos.q - axis_pos.q) / 2.0) * math.sqrt(3.0),
            (ally_pos.q - axis_pos.q) * 1.5))
        v_ax, v_al = float(cell["speed"]), float(cell["speed"])
        game = FormationGame(kB, KernelWrap(fit, 1.0), r0=r0,
                             bearing0_deg=brg,
                             hB0_deg=_HEADING_DEG[cell["axis_heading"]],
                             hR0_deg=_HEADING_DEG[cell["ally_heading"]],
                             vB=v_ax, vR=v_al, H=6)
        pay = np.array([[game.payoff(a, b, 1) for b in lib] for a in lib])
        v, _, _ = restricted_lp(pay)
        rows.append({**{k: cell[k] for k in ("geometry", "range", "speed")},
                     "true_range": cell["true_range"], "V_surrogate": float(v)})
    return rows


def run_one(args) -> dict:
    cell, arm, seed = args
    axis_arm, ally_arm = arm.split("-")
    scen = formation_scenario(cell)
    register_custom_scenario(scen)
    engine = IronBottomEngine()
    state = engine.reset(scen["id"], seed=seed)
    game_id = state.game_id

    pol_axis = FormationArmPolicy(_kernel(), 4,
                                  commit_len=1 if axis_arm == "R" else 99)
    pol_ally = FormationArmPolicy(_kernel(), 4,
                                  commit_len=1 if ally_arm == "R" else 99)

    ORDER_PHASES = {Phase.REINFORCEMENT, Phase.MOVEMENT_PLANNING,
                    Phase.TORPEDO_PLANNING, Phase.GUNNERY,
                    Phase.CONTACT_SETUP, Phase.FORMATION_SETUP}

    def try_submit(batch) -> bool:
        res = engine.submit_orders(game_id, batch)
        if not res.valid:
            print(f"SUBMIT-FAIL {cell['geometry']} r{cell['range']} v{cell['speed']} "
                  f"{arm} s{seed} phase={state.phase}: {res.errors[:2]}", flush=True)
        return bool(res.valid)

    def movement_batch(side: Side, policy: FormationArmPolicy) -> OrderBatch:
        batch = OrderBatch(side=side, phase=state.phase)
        delta = policy.lead_delta(engine, state, side)
        moves = []
        for s in state.ships.values():
            if s.side != side or s.sunk or not s.position:
                continue
            try:
                plan = policy._engine_plan(engine, state, s, delta)
            except Exception:
                plan = "0"
            moves.append(MovementOrder(ship_id=s.id, plan=plan or "0"))
        batch.movement = moves
        return batch

    def safe_submit(side: Side, policy: FormationArmPolicy) -> None:
        if state.phase == Phase.MOVEMENT_PLANNING:
            if try_submit(movement_batch(side, policy)):
                return
            # escalating fallbacks: per-ship candidate plans -> all-"0" -> empty
            for fallback_index in range(0, 4):
                moves = []
                for s in state.ships.values():
                    if s.side != side or s.sunk or not s.position:
                        continue
                    plan = "0"
                    try:
                        cands = engine.movement_candidates(state, s, include_plans=True)
                        reach = [e.get("plan") for e in (cands.get("reachable") or [])
                                 if e.get("plan")]
                        if len(reach) > fallback_index:
                            plan = reach[fallback_index]
                    except Exception:
                        pass
                    moves.append(MovementOrder(ship_id=s.id, plan=plan))
                if try_submit(OrderBatch(side=side, phase=state.phase, movement=moves)):
                    return
            if try_submit(OrderBatch(side=side, phase=state.phase,
                                     movement=[MovementOrder(ship_id=s.id, plan="0")
                                               for s in state.ships.values()
                                               if s.side == side and s.position])):
                return
        elif state.phase == Phase.GUNNERY:
            # matched reactive target selection: part of the shared policy
            # class in both arms (the commitment manipulation is movement-only)
            batch = OrderBatch(side=side, phase=state.phase)
            try:
                batch.gunnery = policy.gunnery_orders(engine, state, side)
            except Exception:
                batch.gunnery = []
            if try_submit(batch):
                return
        try_submit(OrderBatch(side=side, phase=state.phase))

    guard = 0
    try:
        while state.phase != Phase.COMPLETE and guard < 400:
            guard += 1
            phase = state.phase
            if phase in ORDER_PHASES:
                if phase == Phase.MOVEMENT_PLANNING:
                    safe_submit(Side.AXIS, pol_axis)
                    safe_submit(Side.ALLIES, pol_ally)
                else:
                    safe_submit(Side.AXIS, pol_axis)
                    safe_submit(Side.ALLIES, pol_ally)
            engine.advance(game_id)
            state = engine.get(game_id)
    except Exception as exc:  # one failed game must never kill the sweep
        return {"geometry": cell["geometry"], "range": cell["range"],
                "speed": cell["speed"], "arm": arm, "seed": seed,
                "damage_axis": -1, "damage_allies": -1, "diff": 0,
                "axis_win": 0, "allies_win": 0,
                "error": f"{type(exc).__name__}: {exc}"}

    dmg_axis = state.hull_damage_taken.get("axis", 0)
    dmg_allies = state.hull_damage_taken.get("allies", 0)
    winner = state.winner.value if state.winner is not None else "draw"
    return {"geometry": cell["geometry"], "range": cell["range"],
            "speed": cell["speed"], "arm": arm, "seed": seed,
            "damage_axis": dmg_axis, "damage_allies": dmg_allies,
            "diff": dmg_allies - dmg_axis,
            "axis_win": int(winner == "axis"),
            "allies_win": int(winner == "allies")}


def paired_boot_ci(d: np.ndarray, n: int = 10000) -> tuple:
    """95% percentile-bootstrap CI of the mean of paired differences."""
    rng = np.random.default_rng(7)
    idx = rng.integers(0, len(d), size=(n, len(d)))
    means = d[idx].mean(axis=1)
    return float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5))


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    t0 = time.time()

    svals = surrogate_values()
    json.dump(svals, open(OUT / "must2_surrogate_cells.json", "w"), indent=2)

    jobs = [(cell, arm, s) for cell in CELLS for arm in ARMS
            for s in range(1, N_SEEDS + 1)]
    total = len(jobs)
    print(f"[MUST2] {total} games: {len(CELLS)} cells x {len(ARMS)} arms "
          f"x {N_SEEDS} paired seeds", flush=True)

    rows: list[dict] = []
    done = 0
    with open(OUT / "must2_games.jsonl", "a") as jf:
        with ProcessPoolExecutor(max_workers=5) as ex:
            futs = {ex.submit(run_one, j): j for j in jobs}
            for fut in as_completed(futs):
                r = fut.result()
                rows.append(r)
                jf.write(json.dumps(r) + "\n")
                jf.flush()
                done += 1
                if done % 60 == 0 or done == total:
                    el = time.time() - t0
                    eta = el * (total - done) / max(done, 1)
                    print(f"PROGRESS {done}/{total} pct={100.0 * done / total:.1f}% "
                          f"elapsed={time.strftime('%H:%M:%S', time.gmtime(el))} "
                          f"eta={time.strftime('%H:%M:%S', time.gmtime(eta))}",
                          flush=True)

    # ---- aggregate (error rows excluded, reported) ----
    ok_rows = [r for r in rows if "error" not in r]
    err_rows = [r for r in rows if "error" in r]
    index = {(r["geometry"], r["range"], r["speed"], r["arm"], r["seed"]): r
             for r in ok_rows}
    per_cell = []
    for cell in CELLS:
        g, rng_, spd = cell["geometry"], cell["range"], cell["speed"]
        entry = {"geometry": g, "range": rng_, "speed": spd}
        vs = next((v["V_surrogate"] for v in svals
                   if v["geometry"] == g and v["range"] == rng_
                   and v["speed"] == spd), None)
        entry["V_surrogate"] = vs
        for arm in ARMS:
            ds = np.array([index[(g, rng_, spd, arm, s)]["diff"]
                           for s in range(1, N_SEEDS + 1)
                           if (g, rng_, spd, arm, s) in index])
            lo, hi = paired_boot_ci(ds)
            # diff = allies_damage - axis_damage, so diff > 0 favours axis
            entry[arm] = {"n": len(ds),
                          "axis_adv": float(ds.mean()),
                          "ci": [lo, hi]}
        ff = np.array([index[(g, rng_, spd, "F-F", s)]["diff"]
                       for s in range(1, N_SEEDS + 1)
                       if (g, rng_, spd, "F-F", s) in index])
        for label, arm in (("premium_axis_RF", "R-F"), ("premium_allies_FR", "F-R")):
            da = np.array([index[(g, rng_, spd, arm, s)]["diff"]
                           for s in range(1, N_SEEDS + 1)
                           if (g, rng_, spd, arm, s) in index])
            # axis-side advantage under `arm` minus under F-F
            d = da - ff
            lo, hi = paired_boot_ci(d)
            entry[label] = {"mean": float(d.mean()), "ci": [lo, hi]}
        per_cell.append(entry)

    # ---- pre-specified gates (v7 5.6) ----
    signs = [1 if c["V_surrogate"] > 0.05 else -1 if c["V_surrogate"] < -0.05 else 0
             for c in per_cell]
    margins = [c["F-F"]["axis_adv"] for c in per_cell]
    agree = 0
    comparable = 0
    for c, sgn in zip(per_cell, signs):
        if sgn == 0:
            continue
        comparable += 1
        if (c["F-F"]["axis_adv"] > 0) == (sgn > 0):
            agree += 1
    sign_rate = agree / max(comparable, 1)
    from scipy.stats import spearmanr
    rho, rho_p = spearmanr([c["V_surrogate"] for c in per_cell], margins)
    pairs_ok = pairs_tot = 0
    for i in range(len(per_cell)):
        for j in range(i + 1, len(per_cell)):
            dv = per_cell[i]["V_surrogate"] - per_cell[j]["V_surrogate"]
            dm = margins[i] - margins[j]
            if abs(dv) < 0.05:
                continue
            pairs_tot += 1
            if (dv > 0) == (dm > 0):
                pairs_ok += 1
    order_rate = pairs_ok / max(pairs_tot, 1)

    if sign_rate >= 0.8 and rho >= 0.6 and order_rate >= 0.75:
        verdict = "PASS"
    elif sign_rate >= 0.6 and rho >= 0.4 and order_rate >= 0.55:
        verdict = "PARTIAL"
    else:
        verdict = "FAIL"

    prem_axis_pos = sum(1 for c in per_cell if c["premium_axis_RF"]["ci"][0] > 0)
    prem_allies_pos = sum(1 for c in per_cell
                          if c["premium_allies_FR"]["ci"][0] > 0)

    results = {
        "n_games": total, "n_errors": len(err_rows),
        "error_examples": [r["error"] for r in err_rows[:5]],
        "per_cell": per_cell,
        "gates": {"sign_agreement": sign_rate, "spearman_rho": float(rho),
                  "pairwise_ordering": order_rate,
                  "n_sign_comparable": comparable,
                  "n_pairs": pairs_tot},
        "feedback_premium_cells": {"axis_RF": f"{prem_axis_pos}/{len(per_cell)}",
                                   "allies_FR": f"{prem_allies_pos}/{len(per_cell)}"},
        "verdict": verdict,
    }
    json.dump(results, open(OUT / "must2_results.json", "w"), indent=2)
    with open(OUT / "must2_games.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    lines = ["# MUST-2 (v7): matched external engine validation (formation 3v3)", "",
             f"Cells: {len(CELLS)} (3 geom x 2 range x 2 speed), arms: {ARMS}, "
             f"seeds: {N_SEEDS} paired CRN, games: {total} (errors: {len(err_rows)})",
             "", "| geometry | r | v | V_surr | F-F ax adv [CI] | R-R ax adv [CI] | "
             "axis prem R-F [CI] | allies prem F-R [CI] |",
             "|---|---|---|---|---|---|---|---|"]
    for c in per_cell:
        lines.append(
            f"| {c['geometry']} | {c['range']} | {c['speed']} "
            f"| {c['V_surrogate']:+.3f} "
            f"| {c['F-F']['axis_adv']:+.2f} [{c['F-F']['ci'][0]:+.2f},{c['F-F']['ci'][1]:+.2f}] "
            f"| {c['R-R']['axis_adv']:+.2f} [{c['R-R']['ci'][0]:+.2f},{c['R-R']['ci'][1]:+.2f}] "
            f"| {c['premium_axis_RF']['mean']:+.2f} [{c['premium_axis_RF']['ci'][0]:+.2f},{c['premium_axis_RF']['ci'][1]:+.2f}] "
            f"| {c['premium_allies_FR']['mean']:+.2f} [{c['premium_allies_FR']['ci'][0]:+.2f},{c['premium_allies_FR']['ci'][1]:+.2f}] |")
    lines += ["", "## Pre-specified gates (v7 5.6)",
              f"- sign agreement: **{sign_rate:.0%}** (>= 80%)",
              f"- Spearman rho: **{rho:.3f}** (p={rho_p:.1e}) (>= 0.60)",
              f"- pairwise ordering: **{order_rate:.0%}** of {pairs_tot} pairs (>= 75%)",
              f"- feedback premium cells (R-F>0): {prem_axis_pos}/{len(per_cell)}; "
              f"(F-R>0): {prem_allies_pos}/{len(per_cell)}",
              f"- **VERDICT: {verdict}**",
              "", f"Wall time: {time.strftime('%H:%M:%S', time.gmtime(time.time() - t0))}"]
    (OUT / "must2_report.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"[MUST2] DONE verdict={verdict} sign={sign_rate:.0%} rho={rho:.3f} "
          f"order={order_rate:.0%} errors={len(err_rows)} in "
          f"{time.strftime('%H:%M:%S', time.gmtime(time.time() - t0))}", flush=True)


if __name__ == "__main__":
    main()
