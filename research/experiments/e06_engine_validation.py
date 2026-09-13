"""E06 (M6): engine validation of the geometry policy against doctrine baselines.

Symmetric heavy-cruiser duel (San Francisco vs San Francisco), so any paired
damage differential for the geometry policy is attributable to maneuvering
quality alone.  Paired seeds (common random numbers) across policies; the
opponent side is always TacticalCommander(balanced).

Policies (AXIS): geometry (surrogate receding-horizon minimax), line,
balanced, straight.  Outcomes: hull damage differential (allies - axis),
win/loss, paired bootstrap 95% CI of geometry vs each baseline.

Outputs: research/results/e06/{games.csv, results.json, report.md}
"""
from __future__ import annotations

import json
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "backend" / "src"))
sys.path.insert(0, str(REPO))

from iron_bottom_sound.data import register_custom_scenario  # noqa: E402
from iron_bottom_sound.engine import IronBottomEngine  # noqa: E402
from iron_bottom_sound.models import (  # noqa: E402
    MovementOrder,
    OrderBatch,
    Phase,
    Side,
)
from iron_bottom_sound.tactical import PROFILES, TacticalCommander  # noqa: E402

from research.geometry.firepower_kernel import KernelFit  # noqa: E402
from research.policies.geometry_policy import GeometryPolicy, geometry_orders  # noqa: E402

OUT = REPO / "research" / "results" / "e06"

SF = "IBS-U-USN-SAN-FRANCISCO"

from iron_bottom_sound.models import HexCoord as _HC

_B = _HC(q=10, r=4)
GEOMETRIES = {
    # internal-coordinate placements so label parity cannot skew geometry:
    # parallel (abeam-ish ~30 deg, same course), head-on, crossing
    "parallel": (_B.label, 2, _HC(q=21, r=4).label, 2),
    "head_on": (_B.label, 2, _HC(q=22, r=11).label, 5),
    "crossing": (_B.label, 2, _HC(q=22, r=1).label, 5),
}
POLICIES = ("geometry", "line", "balanced", "straight")
N_SEEDS = 60


def run_one(args) -> dict:
    policy_name, geometry, seed = args
    bhex, bh, rhex, rh = GEOMETRIES[geometry]
    definition = {
        "id": f"IBS-CUSTOM-E06-{geometry}",
        "title": f"E06 {geometry}",
        "turns": 6,
        "visibility": {"axis": 20, "allies": 20},
        "optional_rules": [],
        # near-identical US heavy cruisers (same class family) on both sides,
        # so a paired damage differential isolates maneuvering quality
        "ships": [
            {"id": SF, "name": "SF-axis", "side": "axis",
             "position": bhex, "heading": bh, "speed": 5},
            {"id": "IBS-U-USN-NEW-ORLEANS", "name": "NO-allies", "side": "allies",
             "position": rhex, "heading": rh, "speed": 5},
        ],
    }
    register_custom_scenario(definition)

    engine = IronBottomEngine()
    state = engine.reset(definition["id"], seed=seed)
    game_id = state.game_id

    ally_cmd = TacticalCommander(PROFILES["balanced"])
    axis_cmd = None
    if policy_name in ("line", "balanced"):
        axis_cmd = TacticalCommander(PROFILES[policy_name])
    geom = None
    if policy_name == "geometry":
        geom = GeometryPolicy(KernelFit.from_dict(KernelFit_load()), 4)

    ORDER_PHASES = {Phase.REINFORCEMENT, Phase.MOVEMENT_PLANNING,
                    Phase.TORPEDO_PLANNING, Phase.GUNNERY,
                    Phase.CONTACT_SETUP, Phase.FORMATION_SETUP}

    def axis_batch(phase: Phase) -> OrderBatch:
        if policy_name in ("line", "balanced"):
            return axis_cmd.choose_plan(engine, game_id, Side.AXIS)[1]
        if policy_name == "straight":
            if phase == Phase.MOVEMENT_PLANNING:
                obs = engine.observe(game_id, Side.AXIS)
                return OrderBatch(side=Side.AXIS, phase=phase,
                                  movement=[MovementOrder(ship_id=s.id, plan="3")
                                            for s in obs.ships
                                            if s.side == Side.AXIS and s.position is not None])
            return OrderBatch(side=Side.AXIS, phase=phase)
        return geometry_orders(engine, state, Side.AXIS, geom)

    def try_submit(batch) -> bool:
        """submit_orders validates internally and does NOT store when invalid;
        it returns the ValidationResult, so use that as the acceptance test."""
        return bool(engine.submit_orders(game_id, batch).valid)

    def safe_submit(batch) -> None:
        """Submit with escalating fallbacks so that every order phase always
        ends with both sides sealed:
          original batch -> per-ship engine candidate plans -> all-"0" -> empty.
        """
        side = batch.side
        if try_submit(batch):
            return
        if state.phase == Phase.MOVEMENT_PLANNING:
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
        try_submit(OrderBatch(side=side, phase=state.phase))

    guard = 0
    while state.phase != Phase.COMPLETE and guard < 300:
        guard += 1
        phase = state.phase
        if phase in ORDER_PHASES:
            safe_submit(axis_batch(phase))
            safe_submit(ally_cmd.choose_plan(engine, game_id, Side.ALLIES)[1])
        engine.advance(game_id)
        state = engine.get(game_id)

    dmg_axis = state.hull_damage_taken.get("axis", 0)
    dmg_allies = state.hull_damage_taken.get("allies", 0)
    winner = state.winner.value if state.winner is not None else "draw"
    return {"policy": policy_name, "geometry": geometry, "seed": seed,
            "damage_axis": dmg_axis, "damage_allies": dmg_allies,
            "diff": dmg_allies - dmg_axis,
            "axis_win": int(winner == "axis"),
            "allies_win": int(winner == "allies")}


def KernelFit_load():
    fits = json.load(open(REPO / "research" / "results" / "e01" / "kernel_fits.json"))
    return fits["CA"]


def main() -> None:
    import csv

    OUT.mkdir(parents=True, exist_ok=True)
    jobs = [(p, g, s) for p in POLICIES for g in GEOMETRIES for s in range(1, N_SEEDS + 1)]
    with ProcessPoolExecutor(max_workers=6) as pool:
        rows = list(pool.map(run_one, jobs))

    with (OUT / "games.csv").open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    # paired comparison geometry vs each baseline on common (geometry, seed)
    results = {}
    rng = np.random.default_rng(20260910)
    index = {(r["policy"], r["geometry"], r["seed"]): r for r in rows}
    for geometry in GEOMETRIES:
        geom_rows = [index[("geometry", geometry, s)] for s in range(1, N_SEEDS + 1)]
        entry = {"n": N_SEEDS}
        for baseline in ("line", "balanced", "straight"):
            base_rows = [index[(baseline, geometry, s)] for s in range(1, N_SEEDS + 1)]
            diffs = np.array([g["diff"] - b["diff"] for g, b in zip(geom_rows, base_rows)])
            boots = [float(np.mean(rng.choice(diffs, size=len(diffs)))) for _ in range(4000)]
            lo, hi = np.percentile(boots, [2.5, 97.5])
            entry[baseline] = {
                "mean_diff_edge": float(np.mean(diffs)),
                "ci95": [float(lo), float(hi)],
                "positive_fraction": float(np.mean(diffs > 0)),
            }
        results[geometry] = entry

    summary = {"paired_comparisons": results, "n_seeds": N_SEEDS,
               "policies": POLICIES, "geometries": list(GEOMETRIES)}
    (OUT / "results.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

    lines = ["# E06 engine validation (geometry policy vs doctrine baselines)", ""]
    for geometry, entry in results.items():
        lines.append(f"## {geometry}")
        for baseline, st in entry.items():
            if baseline == "n":
                continue
            lines.append(f"- vs {baseline}: mean damage-diff edge "
                         f"{st['mean_diff_edge']:+.2f} "
                         f"(95% CI [{st['ci95'][0]:+.2f}, {st['ci95'][1]:+.2f}]), "
                         f"positive in {100 * st['positive_fraction']:.0f}% of pairs")
    (OUT / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2)[:2000])


if __name__ == "__main__":
    main()
