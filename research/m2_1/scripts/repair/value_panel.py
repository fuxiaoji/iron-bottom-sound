"""M2.1-R value panel: scenario-native-first values plus the repaired U1.

U1 (frozen definition, REPAIRED per PI review):
    U1 = ( sum_enemy VP_i * damageFrac_i - sum_own VP_i * damageFrac_i )
         / sum_all VP_i            (VP totals of the SNAPSHOT roster, constant)
    damageFrac_i = 1 if sunk else (1 - hull_i / max_hull_i)

The previous implementation used remaining-hull VP with a dynamic denominator
and an inconsistent sunk branch — see FAILURES M21R-F1.
"""

from __future__ import annotations


def damage_frac(ship) -> float:
    if getattr(ship, "sunk", False):
        return 1.0
    hull, max_hull = getattr(ship, "hull", None), getattr(ship, "max_hull", None)
    if hull is None or not max_hull:
        return 0.0
    return max(0.0, min(1.0, 1.0 - hull / max_hull))


def u1_material(state, side, roster_vp=None) -> float:
    """Repaired U1.  ``roster_vp`` = {ship_id: vp} frozen at the snapshot; if
    None, the snapshot's current roster is used (constant within a branch)."""
    other = "allies" if side == "axis" else "axis"
    enemy_dmg = own_dmg = total = 0.0
    for s in state.ships.values():
        vp = float((roster_vp or {}).get(s.id, s.vp) or 0.0)
        total += vp
        frac = vp * damage_frac(s)
        if s.side == side:
            own_dmg += frac
        else:
            enemy_dmg += frac
    if total <= 0:
        return 0.0
    return (enemy_dmg - own_dmg) / total
