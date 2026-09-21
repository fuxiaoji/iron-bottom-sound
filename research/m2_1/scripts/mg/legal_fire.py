"""M2.1-R2.1 legal fire allocation: each gun mount allocated at most once.

Replaces the double-counting measure_side() (F21).  Used by MG2-R and MG5-R.
"""

from __future__ import annotations

from itertools import product

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO / "backend" / "src"))
sys.path.insert(0, str(REPO / "research" / "m2_1" / "scripts"))

from iron_bottom_sound.engine import d66_adjust  # noqa: E402
from iron_bottom_sound.models import (GameState, GunMountOrder, GunneryOrder,  # noqa: E402
                                      OrderBatch, Phase, Side)

D66 = [t * 10 + u for t in range(1, 7) for u in range(1, 7)]


def _mount_eh(eng, st, ship, mount, target, distance) -> float:
    fp = float(getattr(mount, "firepower", 0) or 0)
    if fp <= 0:
        return 0.0
    mods = eng._gunnery_modifiers(st, ship, target, distance, 1, 8.0, 1)
    total = sum(mods.values())
    return sum(eng.rules.hit_count(int(fp), d66_adjust(d, total)) for d in D66) / 36.0


def legal_options(eng, st, ship, enemies):
    """Legal (mount, target) pairs for one ship: mount not destroyed/fired and
    able to bear on that target."""
    out = []
    for m in ship.gun_mounts:
        if m.destroyed or m.fired_this_phase:
            continue
        for tgt in enemies:
            if not tgt.position or tgt.sunk:
                continue
            if eng._mount_can_bear(ship, tgt, m.arcs):
                d = ship.position.distance(tgt.position)
                out.append((m, tgt, d))
    return out


def best_allocation(eng, st, ship, enemies, max_mounts=6):
    """Best legal allocation for one ship: each mount used at most once, each
    mount assigned at most one target.  Exhaustive over per-mount choices."""
    options = legal_options(eng, st, ship, enemies)
    if not options:
        return {"mounts": [], "target": None, "eh": 0.0, "gf": 0.0}
    by_mount = {}
    for m, tgt, d in options:
        by_mount.setdefault(m.id, []).append((m, tgt, d))
    mount_ids = sorted(by_mount)[:max_mounts]
    # per-mount best (mount -> target) and per-mount eh contribution
    best_per_mount = {}
    for mid in mount_ids:
        best = None
        for m, tgt, d in by_mount[mid]:
            eh = _mount_eh(eng, st, ship, m, tgt, d)
            if best is None or eh > best[0]:
                best = (eh, m, tgt, d)
        best_per_mount[mid] = best
    chosen = [best_per_mount[mid] for mid in mount_ids if best_per_mount[mid][0] > 0]
    total_eh = sum(c[0] for c in chosen)
    gf = sum(float(getattr(c[1], "firepower", 0) or 0) for c in chosen)
    # dominant target = the target receiving the most expected hits
    shares = {}
    for eh, m, tgt, d in chosen:
        shares[tgt.id] = shares.get(tgt.id, 0.0) + eh
    dominant = max(shares, key=shares.get) if shares else None
    return {"mounts": [(c[1].id, c[2].id) for c in chosen],
            "target": dominant, "eh": total_eh, "gf": gf,
            "n_mounts": len(chosen), "shares": shares}


def team_legal_fire(eng, st, side, opp_side):
    """Team-level legal fire: sum over shooters of their best legal
    allocation.  Also returns per-ship detail and the aspect of each
    shooter's dominant target."""
    side = Side(side) if isinstance(side, str) else side
    opp = Side(opp_side) if isinstance(opp_side, str) else opp_side
    enemies = [s for s in st.ships.values()
               if s.side == opp and not s.sunk and s.position]
    shooters = [s for s in st.ships.values()
                if s.side == side and not s.sunk and s.position]
    detail = []
    total_eh = total_gf = 0.0
    active = 0
    long_pairs = 0
    target_hits = {}
    for ship in shooters:
        alloc = best_allocation(eng, st, ship, enemies)
        aspect = None
        if alloc["target"]:
            tgt = st.ships[alloc["target"]]
            aspect = eng._target_aspect(ship, tgt)
            if aspect == "bow_stern":
                long_pairs += 1
            target_hits[alloc["target"]] = target_hits.get(alloc["target"], 0.0) + alloc["eh"]
        if alloc["n_mounts"] > 0:
            active += 1
        total_eh += alloc["eh"]
        total_gf += alloc["gf"]
        detail.append({"ship": ship.id, "target": alloc["target"],
                       "mounts": alloc["mounts"], "eh": alloc["eh"],
                       "gf": alloc["gf"], "target_aspect": aspect})
    return {"team_eh": total_eh, "team_gf": total_gf,
            "active_shooters": active, "longitudinal": long_pairs,
            "target_distribution": target_hits, "detail": detail}


def materialize_batch(eng, st, side, team_result) -> tuple[str, bool, list[str]]:
    """Build a real GunneryOrder batch from the chosen allocations and require
    validate_orders(..., _prepared=True) to pass."""
    side = Side(side) if isinstance(side, str) else side
    batch = OrderBatch(side=side, phase=Phase.GUNNERY)
    for row in team_result["detail"]:
        if not row["mounts"]:
            continue
        order = GunneryOrder(ship_id=row["ship"], primary_target=row["target"])
        order.mounts = [GunMountOrder(mount_id=m, target_id=t)
                        for m, t in row["mounts"]]
        batch.gunnery.append(order)
    res = eng.validate_orders(st.game_id, batch, _prepared=True)
    return batch.model_dump_json(), res.valid, res.errors[:4]
