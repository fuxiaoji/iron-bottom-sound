"""M2.2-R intent compiler: PRE_FIX (frozen, re-exported) vs REPAIRED_INTENT_BASELINE.

Provenance verdict for the BROADSIDE defect (see
`research/m2_2r/02_BROADSIDE_COMPILER_BUG.md`): `RESEARCH_COMPILER_BUG`.  The
defective function lives in the frozen M2.1 tree and is **not edited**, because
the census arm `CURRENT_INTENT_PRE_FIX` must stay reproducible.  The repair lives
here, under a name that can never be mistaken for the old baseline.

Frozen translation rule (PRE_REGISTRATION_B1E §2C): for each own ship take the
bearing to its nearest visible enemy; among the six candidate headings choose the
one that maximises the count of the ship's own non-destroyed mounts whose firing
arcs contain `_relative_aspect(position, heading, target_position)`.  The intent
is compiled from the ship's own arc table — not from a value function, and not by
searching movement plans.  Ties: smaller circular |heading − bearing| first, then
the clockwise heading (smallest positive `(heading − bearing) % 6`).
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
for p in (REPO / "backend" / "src", REPO / "research" / "m2_1" / "scripts"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from iron_bottom_sound.engine import IronBottomEngine  # noqa: E402
from mg.mg_cases import intent_plans as pre_fix_intent_plans  # noqa: E402
from mg.mg_cases import plan_for_pose, ships_of  # noqa: E402
from mg.micro import plan_tables  # noqa: E402

NAME_PRE_FIX = "CURRENT_INTENT_PRE_FIX"
NAME_REPAIRED = "REPAIRED_INTENT_BASELINE"


def arc_counts(eng, ship, target) -> dict[int, int]:
    """Non-destroyed mounts bearing on `target` for each of the six headings."""
    counts = {}
    for h in range(1, 7):
        aspect = IronBottomEngine._relative_aspect(ship.position, h, target.position)
        counts[h] = sum(1 for m in ship.gun_mounts
                        if not m.destroyed and aspect in m.arcs)
    return counts


def repaired_desired_heading(eng, ship, target) -> int:
    """The heading that best compiles 'present the broadside to `target`'."""
    bearing = IronBottomEngine._bearing_between(ship.position, target.position)
    counts = arc_counts(eng, ship, target)
    best = max(counts.values())
    tied = [h for h in range(1, 7) if counts[h] == best]
    return min(tied, key=lambda h: (min((h - bearing) % 6, (bearing - h) % 6),
                                    (h - bearing) % 6))


def repaired_intent_plans(eng, st, side, intent, enemies) -> dict:
    """Drop-in replacement for `mg_cases.intent_plans`.

    BROADSIDE is compiled by the frozen arc rule above; every other intent
    delegates to the pre-fix implementation unchanged so this module cannot
    silently alter the other frozen micro-cases.
    """
    if intent != "BROADSIDE":
        return pre_fix_intent_plans(eng, st, side, intent, enemies)
    own = ships_of(st, side)
    tables = plan_tables(eng, st, side)
    out = {}
    for s in own:
        visible = [e for e in enemies if e.position]
        if not visible or s.position is None:
            continue
        near = min(visible, key=lambda e: s.position.distance(e.position))
        dh = repaired_desired_heading(eng, s, near)
        plans = tables.get(s.id) or set()
        out[s.id] = plan_for_pose(eng, st, s, plans, dh, 0)
    return out
