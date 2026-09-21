"""Unit tests for the M2.2-R intent compiler (PRE_REGISTRATION_B1E §2D).

    PYTHONPATH=backend/src:research/m2_2/scripts:research/m2_1/scripts \
        .venv/bin/python research/m2_2/scripts/test_intent_compiler.py

Assertions:
  (i)   `repaired_intent_plans` never returns the narrow arm's plan for the frozen
        MG1 focal ship;
  (ii)  [REPORTED, not a criterion] the repaired focal plan's usable mount count,
        against the pre-fix arm and the gold arm, with the arc counts that
        produced it.  The PI's required criterion is (i): BROADSIDE must not
        compile to the narrow arm.  Mount-count recovery is bounded by F18 (the
        pre-movement bearing is invalidated by simultaneous movement), so it is
        reported as a diagnostic and is NOT asserted;
  (iii) `pre_fix_intent_plans` still returns the narrow arm's plan — the
        reproduction guard proving the frozen module was not mutated;
  (iv)  on a synthetic sweep, the repaired heading never leaves the target
        dead-ahead/dead-astern when an abeam heading is legal.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parent))

from iron_bottom_sound.engine import IronBottomEngine  # noqa: E402
from iron_bottom_sound.models import FiringArc, HexCoord  # noqa: E402
from m22_b0 import build_mg1, play_movement  # noqa: E402
from mg.mg_cases import ships_of  # noqa: E402
from intent_compiler import (arc_counts, pre_fix_intent_plans,  # noqa: E402
                             repaired_desired_heading, repaired_intent_plans)

FAILS: list[str] = []


def check(name: str, cond: bool, detail: str = "") -> None:
    print(f"  [{'PASS' if cond else 'FAIL'}] {name}{(' — ' + detail) if detail else ''}")
    if not cond:
        FAILS.append(name)


def mounts_bearing(eng, st, a_id, b_id) -> int:
    a, b = st.ships[a_id], st.ships[b_id]
    return sum(1 for m in a.gun_mounts
               if not m.destroyed and eng._mount_can_bear(a, b, m.arcs))


def main() -> int:
    case = build_mg1(log=lambda *a: None)
    focal, target = case["focal"], case["target"]
    side = case["side"]
    pre = pre_fix_intent_plans(case["eng"], case["st"], side, "BROADSIDE", case["enemies"])
    rep = repaired_intent_plans(case["eng"], case["st"], side, "BROADSIDE", case["enemies"])
    print(f"MG1 frozen case: focal={focal} target={target}")
    print(f"  pre_fix  focal plan = {pre.get(focal)}")
    print(f"  repaired focal plan = {rep.get(focal)}")
    print(f"  gold (broadside) = {case['gold_plan']}, narrow arm = {case['ref_plan']}")

    check("(iii) pre_fix still returns the narrow arm's plan (frozen module unmutated)",
          pre.get(focal) == case["ref_plan"], f"got {pre.get(focal)}")
    check("(i) repaired does not return the narrow arm's plan",
          rep.get(focal) != case["ref_plan"], f"got {rep.get(focal)}")

    st_fix, e_fix, err = play_movement(case["st"], side,
                                       {**case["policy_map"], focal: rep[focal]},
                                       case["enemy_plans"], case["se"])
    diagnostic = {}
    if st_fix is None:
        check("(ii) repaired focal plan is a legal batch", False, str(err))
    else:
        check("(ii) repaired focal plan is a legal batch", True)
        got = mounts_bearing(e_fix, st_fix, focal, target)
        st_pre, e_pre, _err = play_movement(case["st"], side,
                                            {**case["policy_map"], focal: pre[focal]},
                                            case["enemy_plans"], case["se"])
        st_gold, e_gold, _err = play_movement(case["st"], side,
                                              {**case["policy_map"], focal: case["gold_plan"]},
                                              case["enemy_plans"], case["se"])
        diagnostic = {
            "REPAIRED_MOUNT_RECOVERY": f"{got}/{mounts_bearing(e_gold, st_gold, focal, target)}"
                                       f" (pre_fix {mounts_bearing(e_pre, st_pre, focal, target)})",
            "arc_counts_at_current_bearing": arc_counts(case["eng"], case["st"].ships[focal],
                                                        case["st"].ships[target]),
            "repaired_desired_heading": repaired_desired_heading(
                case["eng"], case["st"].ships[focal], case["st"].ships[target]),
            "note": "diagnostic only — not a pass/fail criterion (PRE_REGISTRATION_B1E §2D)",
        }
        print(f"  [REPORTED] mount recovery {diagnostic['REPAIRED_MOUNT_RECOVERY']}; "
              f"arc counts {diagnostic['arc_counts_at_current_bearing']}; "
              f"desired heading {diagnostic['repaired_desired_heading']}")

    # (iv) synthetic sweep: dead ahead / dead astern never chosen when abeam is legal
    ship = SimpleNamespace(
        position=HexCoord(q=0, r=0), heading=1,
        gun_mounts=[SimpleNamespace(destroyed=False, arcs=(FiringArc.BOW,)),
                    SimpleNamespace(destroyed=False, arcs=(FiringArc.STARBOARD,)),
                    SimpleNamespace(destroyed=False, arcs=(FiringArc.PORT,))])
    eng = IronBottomEngine()
    bad = []
    for dq, dr in ((4, 0), (3, 3), (0, 4), (-2, 3), (-4, 0), (-2, -3), (0, -4), (3, -3)):
        q, r = 6 + dq, 6 + dr
        target = SimpleNamespace(position=HexCoord(q=q, r=r))
        h = repaired_desired_heading(eng, ship, target)
        asp = IronBottomEngine._relative_aspect(ship.position, h, target.position)
        cnt = arc_counts(eng, ship, target)
        if asp.name in ("BOW", "STERN") and cnt[h] < max(cnt.values()):
            bad.append((q, r, h, asp.name))
    check("(iv) repaired heading never dead-ahead/astern when more mounts bear elsewhere",
          not bad, str(bad))

    print()
    (Path(__file__).resolve().parents[1] / "metrics").mkdir(exist_ok=True)
    (Path(__file__).resolve().parents[1] / "metrics"
     / "intent_compiler_unit_test.json").write_text(json.dumps(
         {"criteria": ["(i) repaired != narrow arm", "(iii) pre_fix == narrow arm",
                       "(iv) no dead-ahead/astern when abeam bears more"],
          "reported": diagnostic, "failed": FAILS}, indent=1))
    if FAILS:
        print(f"RESULT: {len(FAILS)} FAILED — {FAILS}")
        return 1
    print("RESULT: all intent-compiler checks PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
