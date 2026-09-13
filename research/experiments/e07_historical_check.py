"""E07: qualitative historical-scenario check on Cape Esperance (IBS-S-01).

The geometry policy plays the AXIS (Japanese) side of the historical
Cape Esperance scenario against the doctrine-balanced ALLIES, compared
with the line-profile and straight baselines on the same seeds.  S-01
carries its historical special rules (allied fire halved, axis no-fire
first turn, allied reinforcements), so this is a qualitative
external-validity check only: do the surrogate's maneuvers translate
into sane historical-scenario behavior, and how do the policies rank?

Output: research/results/e07/{games.csv, report.md}
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

import json
import numpy as np

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "backend" / "src"))
sys.path.insert(0, str(REPO))

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

OUT = REPO / "research" / "results" / "e07"
ORDER_PHASES = {Phase.REINFORCEMENT, Phase.MOVEMENT_PLANNING,
                Phase.TORPEDO_PLANNING, Phase.GUNNERY,
                Phase.CONTACT_SETUP, Phase.FORMATION_SETUP}


def run_one(policy_name: str, seed: int) -> dict | None:
    try:
        return _run_one_inner(policy_name, seed)
    except Exception as exc:
        print(f"  [{policy_name} seed {seed}] failed: {exc}", flush=True)
        return None


def _run_one_inner(policy_name: str, seed: int) -> dict:
    engine = IronBottomEngine()
    state = engine.reset("IBS-S-01", seed=seed)
    gid = state.game_id
    ally = TacticalCommander(PROFILES["balanced"])
    axis_cmd = TacticalCommander(PROFILES["line"]) if policy_name == "line" else None
    geom = (GeometryPolicy(KernelFit.from_dict(
        json_load()), 4) if policy_name == "geometry" else None)

    def try_submit(batch) -> bool:
        return bool(engine.submit_orders(gid, batch).valid)

    def safe_submit(batch) -> None:
        """Escalating fallbacks; submit_orders validates internally and does
        not store invalid batches, so its return value is the test."""
        if try_submit(batch):
            return
        if state.phase == Phase.MOVEMENT_PLANNING:
            own_ships = [s for s in state.ships.values()
                         if s.side == batch.side and not s.sunk and s.position]
            plan_lists = []
            for s in own_ships:
                try:
                    cands = engine.movement_candidates(state, s, include_plans=True)
                    reach = [e.get("plan") for e in (cands.get("reachable") or [])
                             if e.get("plan")]
                except Exception:
                    reach = []
                plan_lists.append((s.id, reach or ["0"]))
            depth = max((len(pl) for _sid, pl in plan_lists), default=1)
            for d in range(depth):
                moves = [MovementOrder(ship_id=sid, plan=pl[min(d, len(pl) - 1)])
                         for sid, pl in plan_lists]
                if try_submit(OrderBatch(side=batch.side, phase=state.phase,
                                         movement=moves)):
                    return
            if try_submit(OrderBatch(side=batch.side, phase=state.phase,
                                     movement=[MovementOrder(ship_id=sid, plan="0")
                                               for sid, _ in plan_lists])):
                return
        try_submit(OrderBatch(side=batch.side, phase=state.phase))

    guard = 0
    while state.phase != Phase.COMPLETE and guard < 400:
        guard += 1
        ph = state.phase
        if ph in ORDER_PHASES:
            if policy_name == "line":
                safe_submit(axis_cmd.choose_plan(engine, gid, Side.AXIS)[1])
            elif policy_name == "straight":
                obs = engine.observe(gid, Side.AXIS)
                safe_submit(OrderBatch(
                    side=Side.AXIS, phase=ph,
                    movement=[MovementOrder(ship_id=s.id, plan="3")
                              for s in obs.ships
                              if s.side == Side.AXIS and s.position is not None]
                    ) if ph == Phase.MOVEMENT_PLANNING else
                    OrderBatch(side=Side.AXIS, phase=ph))
            else:
                safe_submit(geometry_orders(engine, state, Side.AXIS, geom))
            safe_submit(ally.choose_plan(engine, gid, Side.ALLIES)[1])
        engine.advance(gid)
        state = engine.get(gid)

    dmg_axis = state.hull_damage_taken.get("axis", 0)
    dmg_allies = state.hull_damage_taken.get("allies", 0)
    winner = state.winner.value if state.winner is not None else "draw"
    return {"policy": policy_name, "seed": seed,
            "damage_axis": dmg_axis, "damage_allies": dmg_allies,
            "diff": dmg_allies - dmg_axis, "axis_win": int(winner == "axis")}


def json_load():
    import json
    return json.load(open(REPO / "research" / "results" / "e01" / "kernel_fits.json"))["CA"]


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    rows = []
    for policy in ("geometry", "line", "straight"):
        for seed in range(1, 21):
            r = run_one(policy, seed)
            if r:
                rows.append(r)
                print(r, flush=True)
    if not rows:
        print("all seeds failed")
        return
    with (OUT / "games.csv").open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    index = {(r["policy"], r["seed"]): r for r in rows}
    lines = ["# E07 historical qualitative check: Cape Esperance (S-01), AXIS side", ""]
    rng = np.random.default_rng(20260910)
    for baseline in ("line", "straight"):
        pairs = [s for s in range(1, 21)
                 if ("geometry", s) in index and (baseline, s) in index]
        diffs = np.array([index[("geometry", s)]["diff"] - index[(baseline, s)]["diff"]
                          for s in pairs])
        boots = [float(np.mean(rng.choice(diffs, size=len(diffs)))) for _ in range(4000)]
        lo, hi = np.percentile(boots, [2.5, 97.5])
        lines.append(f"- geometry vs {baseline}: n={len(pairs)} mean damage-diff edge "
                     f"{np.mean(diffs):+.2f} (95% CI [{lo:+.2f}, {hi:+.2f}]), "
                     f"positive {int(np.mean(diffs > 0) * 100)}% of pairs")
    wins = {p: int(np.mean([r["axis_win"] for r in rows if r["policy"] == p]) * 100)
            for p in ("geometry", "line", "straight")}
    lines.append(f"- axis win rates: {wins}")
    (OUT / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(lines)


if __name__ == "__main__":
    main()
