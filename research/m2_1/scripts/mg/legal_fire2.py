"""Faithful team-level legal fire, matching _resolve_gunnery's grouping:

* every mount fires at most once per turn;
* a ship's fire is grouped by (attacker, target): the engine computes
  ``attackers = #distinct ships firing at that target`` and
  ``target_count = #distinct targets that attacker fires at``;
* concentration gives the additional-attacker bonus, splitting pays the
  additional-target penalty — so allocation is a coupled choice across ships.

Allocation model: one target per ship (all its bearing mounts), which is what
the game's own commander does and what the rules describe.  The choice is
resolved by greedy best-response iteration against the current global
attacker counts (3 rounds), then the final numbers are computed with the
engine's exact modifiers.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO / "backend" / "src"))

from iron_bottom_sound.engine import d66_adjust  # noqa: E402
from iron_bottom_sound.models import (GunMountOrder, GunneryOrder,  # noqa: E402
                                      OrderBatch, Phase, Side)

D66 = [t * 10 + u for t in range(1, 7) for u in range(1, 7)]


def _kind_groups(mounts):
    """The engine groups attacks by (attacker, target, mount.kind): primary and
    secondary batteries are separate hit-table lookups."""
    groups = {}
    for m in mounts:
        groups.setdefault(m.kind, []).append(m)
    return groups


def _group_eh(eng, st, ship, mounts, target, attackers, target_count) -> float:
    """Expected hits for one (attacker, target) pairing with the engine's exact
    modifier set and per-mount-kind grouping."""
    if not mounts:
        return 0.0
    d = ship.position.distance(target.position)
    total = 0.0
    for kind, kind_mounts in _kind_groups(mounts).items():
        fp = sum(float(getattr(m, "firepower", 0) or 0) for m in kind_mounts)
        if fp <= 0:
            continue
        caliber = max((getattr(m, "caliber", 8.0) or 8.0) for m in kind_mounts)
        mods = eng._gunnery_modifiers(st, ship, target, d, attackers, caliber, target_count)
        shift = sum(mods.values())
        total += sum(eng.rules.hit_count(int(fp), d66_adjust(x, shift))
                     for x in D66) / 36.0
    return total


def _can_engage(eng, st, ship, target) -> bool:
    """A target is engageable iff the engine would accept fire at it: visible
    (``_can_see``) — the validator rejects orders against unseen ships."""
    try:
        return bool(eng._can_see(st, ship, target))
    except Exception:
        return False


def _bearable_mounts(eng, st, ship, target):
    if not _can_engage(eng, st, ship, target):
        return []
    return [m for m in ship.gun_mounts
            if not m.destroyed and not m.fired_this_phase
            and eng._mount_can_bear(ship, target, m.arcs)]


def team_legal_fire_v2(eng, st, side, opp_side, rounds: int = 3):
    side = Side(side) if isinstance(side, str) else side
    opp = Side(opp_side) if isinstance(opp_side, str) else opp_side
    enemies = [s for s in st.ships.values() if s.side == opp and not s.sunk and s.position]
    shooters = [s for s in st.ships.values() if s.side == side and not s.sunk and s.position]
    # legal targets per shooter
    legal = {}
    for sh in shooters:
        legal[sh.id] = [e for e in enemies if _bearable_mounts(eng, st, sh, e)]
    choice = {sh.id: (legal[sh.id][0] if legal[sh.id] else None) for sh in shooters}
    for _ in range(rounds):
        counts = {}
        for sh in shooters:
            t = choice.get(sh.id)
            if t is not None:
                counts[t.id] = counts.get(t.id, 0) + 1
        for sh in shooters:
            if not legal[sh.id]:
                continue
            n_targets = 1      # one target per ship (model)
            best = None
            for tgt in legal[sh.id]:
                mounts = _bearable_mounts(eng, st, sh, tgt)
                # attackers on this target EXCLUDING this ship's current share
                atk = counts.get(tgt.id, 0) + (1 if choice.get(sh.id) is not tgt else 0)
                base = _group_eh(eng, st, sh, mounts, tgt, max(1, atk), n_targets)
                if best is None or base > best[0]:
                    best = (base, tgt)
            if best:
                choice[sh.id] = best[1]
    # final counts and exact numbers
    counts = {}
    for sh in shooters:
        t = choice.get(sh.id)
        if t is not None:
            counts[t.id] = counts.get(t.id, 0) + 1
    detail = []
    total_eh = total_gf = 0.0
    active = 0
    long_pairs = 0
    for sh in shooters:
        tgt = choice.get(sh.id)
        if tgt is None:
            detail.append({"ship": sh.id, "target": None, "mounts": [], "eh": 0.0, "gf": 0.0})
            continue
        mounts = _bearable_mounts(eng, st, sh, tgt)
        eh = _group_eh(eng, st, sh, mounts, tgt, counts[tgt.id], 1)
        gf = sum(float(getattr(m, "firepower", 0) or 0) for m in mounts)
        aspect = eng._target_aspect(sh, tgt)
        if aspect == "bow_stern":
            long_pairs += 1
        if mounts:
            active += 1
        total_eh += eh
        total_gf += gf
        detail.append({"ship": sh.id, "target": tgt.id,
                       "mounts": [(m.id, tgt.id) for m in mounts],
                       "eh": eh, "gf": gf, "aspect": aspect,
                       "attackers_on_target": counts[tgt.id]})
    return {"team_eh": total_eh, "team_gf": total_gf, "active_shooters": active,
            "longitudinal": long_pairs, "detail": detail,
            "target_distribution": {t: c for t, c in counts.items()}}


def materialize_batch(eng, st, side, team_result):
    side = Side(side) if isinstance(side, str) else side
    batch = OrderBatch(side=side, phase=Phase.GUNNERY)
    for row in team_result["detail"]:
        if not row["mounts"]:
            continue
        order = GunneryOrder(ship_id=row["ship"], primary_target=row["target"])
        order.mounts = [GunMountOrder(mount_id=m, target_id=t) for m, t in row["mounts"]]
        batch.gunnery.append(order)
    res = eng.validate_orders(st.game_id, batch, _prepared=True)
    return batch.model_dump_json(), res.valid, res.errors[:4]
