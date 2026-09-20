"""M2.1-R fleet-level tactical intents -> per-ship legal movement plans.

An intent maps every own ship to a desired (final_heading, speed_class) pose
relative to the enemy, then selects the legal engine plan that best matches.
All plans come from ``engine.movement_candidates`` and the joint batch must
pass the full side-level validator (checked by the caller).

PUBLIC candidates use only what a legal commander sees (own state + visible
enemy positions).  ORACLE candidates may use research full state; they are a
leverage ceiling, never a deployable policy.
"""

from __future__ import annotations

import math

INTENTS = ("UNMASK_BROADSIDE", "KEEP_NARROW_CLOSE", "KEEP_NARROW_OPEN",
           "CROSS_T_PORT", "CROSS_T_STARBOARD", "CLOSE_RANGE", "OPEN_RANGE",
           "MAINTAIN_RANGE", "CONCENTRATE_LOCAL_FORCE", "BREAK_CONTACT",
           "POLICY")


def _bearing_hex(frm, to) -> int:
    """Hex bearing (1..6) from hex a to hex b (axial coords)."""
    dq, dr = to.q - frm.q, to.r - frm.r
    # cube rounding of direction: pick the neighbour direction most aligned
    dirs = {1: (1, -1), 2: (1, 0), 3: (0, 1), 4: (-1, 1), 5: (-1, 0), 6: (0, -1)}
    best, best_score = 1, None
    for h, (dx, dy) in dirs.items():
        norm = math.hypot(dx, dy)
        score = (dq * dx + dr * dy) / (math.hypot(dq, dr) * norm + 1e-9)
        if best_score is None or score > best_score:
            best, best_score = h, score
    return best


def _angle_diff(h1: int, h2: int) -> int:
    d = (h1 - h2) % 6
    return min(d, 6 - d)


def enemy_context(st, side):
    """Nearest-enemy bearing/centroid per own ship, from PUBLIC info (own
    observation: visible enemy positions only)."""
    own = [s for s in st.ships.values() if s.side == side and not s.sunk and s.position]
    enemies = [s for s in st.ships.values()
               if s.side != side and not s.sunk and s.position]
    ctx = {}
    for s in own:
        if not enemies:
            ctx[s.id] = None
            continue
        near = min(enemies, key=lambda e: s.position.distance(e.position))
        ctx[s.id] = {"enemy": near, "bearing": _bearing_hex(s.position, near.position),
                     "distance": s.position.distance(near.position)}
    return own, enemies, ctx


def fleet_centroid(enemies):
    if not enemies:
        return None
    q = sum(e.position.q for e in enemies) / len(enemies)
    r = sum(e.position.r for e in enemies) / len(enemies)
    return (q, r)


def enemy_line_heading(enemies) -> int:
    if not enemies:
        return 1
    from collections import Counter
    return Counter(e.heading for e in enemies).most_common(1)[0][0]


def _hdg(bearing: int, k: int) -> int:
    """Heading k hex-directions (60 deg each) away from bearing, in 1..6."""
    return ((bearing - 1 + k) % 6) + 1


def desired_pose(intent: str, ship, ctx: dict, enemies, centroid, line_heading):
    """Returns (desired_final_heading or None, speed_class in {-1,0,+1}).

    Headings use the corrected wrap: _hdg(bearing, k) with k in 0..5
    (0 = straight at the enemy, 3 = directly away).  The previous
    implementation had an off-by-one that made UNMASK and KEEP_NARROW
    identical (M21R-F10)."""
    if ctx is None:
        return None, 0
    bearing = ctx["bearing"]
    if intent == "UNMASK_BROADSIDE":
        # enemy on the beam: closest hex-representable perpendicular (60 deg)
        return _hdg(bearing, 1), 0
    if intent == "KEEP_NARROW_CLOSE":
        return _hdg(bearing, 0), 0
    if intent == "KEEP_NARROW_OPEN":
        return _hdg(bearing, 0), -1     # stay narrow, drift away slowly
    if intent == "CROSS_T_PORT":
        # perpendicular to the ENEMY LINE = line_heading +/- 2 (120 deg)
        return _hdg(line_heading, -2), +1
    if intent == "CROSS_T_STARBOARD":
        return _hdg(line_heading, +2), +1
    if intent == "CLOSE_RANGE":
        return _hdg(bearing, 0), +1
    if intent == "OPEN_RANGE":
        return _hdg(bearing, 3), +1
    if intent == "MAINTAIN_RANGE":
        return None, 0     # keep current heading, mid speed
    if intent == "CONCENTRATE_LOCAL_FORCE":
        return _hdg(bearing, 0), +1
    if intent == "BREAK_CONTACT":
        return _hdg(bearing, 3), +1
    raise ValueError(intent)


def select_plan(plans: dict, current_heading: int, desired_heading, speed_class: int,
                min_advance: int = 1) -> str:
    """Pick the legal plan whose (final heading, advance) best matches."""
    best, best_key = None, None
    for plan in plans:
        if plan == "0":
            continue
        turns = plan.count("P") - plan.count("S")
        advance = sum(int(ch) for ch in plan if ch.isdigit())
        final = ((current_heading - 1 + turns) % 6) + 1
        if desired_heading is not None:
            ang = _angle_diff(final, desired_heading)
        else:
            ang = _angle_diff(final, current_heading)
        speed_err = abs(advance - (3 if speed_class > 0 else (1 if speed_class < 0 else 2)))
        key = (ang * 10 + speed_err, -advance)
        if best_key is None or key < best_key:
            best, best_key = plan, key
    if best is None and "0" in plans:
        best = "0"
    return best


def intent_batch(eng, st, side, intent: str, plans_by_ship: dict) -> dict:
    """Build {ship_id: plan} implementing the intent; None when impossible."""
    own, enemies, ctx = enemy_context(st, side)
    if not own:
        return None
    centroid = fleet_centroid(enemies)
    line_heading = enemy_line_heading(enemies)
    out = {}
    for s in own:
        plans = plans_by_ship.get(s.id) or set()
        if not plans:
            return None
        if intent == "POLICY":
            return None     # handled upstream
        dh, spd = desired_pose(intent, s, ctx.get(s.id), enemies, centroid,
                               line_heading)
        plan = select_plan(plans, s.heading, dh, spd)
        if plan is None:
            return None
        out[s.id] = plan
    return out
