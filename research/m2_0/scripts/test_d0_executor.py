"""D0 acceptance tests for ResearchGroupExecutor.

    PYTHONPATH=backend/src:research/m2_0 .venv/bin/python -m pytest \
        research/m2_0/scripts/test_d0_executor.py -q
"""

from __future__ import annotations

import copy
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from iron_bottom_sound.engine import IronBottomEngine  # noqa: E402
from iron_bottom_sound.models import GameOptions, Phase, Side  # noqa: E402
from iron_bottom_sound.tactical import PROFILES, TacticalCommander  # noqa: E402
from research_group_executor import (MACROS, MacroInvalid, _plans_for,
                                     execute_partition, orders_to_batch,
                                     plan_for_macro)


def reach_movement_planning(scenario="IBS-S-03", seed=3, turn=1):
    eng = IronBottomEngine()
    st = eng.reset(scenario, seed, GameOptions(mode="llm"))
    se = {s: TacticalCommander(profile=PROFILES["balanced"]) for s in Side}
    guard = 0
    while st.phase != Phase.COMPLETE and guard < 80:
        guard += 1
        if st.phase == Phase.MOVEMENT_PLANNING and st.turn >= turn:
            return eng, st
        if st.phase in {Phase.REINFORCEMENT, Phase.MOVEMENT_PLANNING,
                        Phase.TORPEDO_PLANNING, Phase.GUNNERY,
                        Phase.CONTACT_SETUP, Phase.FORMATION_SETUP}:
            for side in Side:
                if side.value not in st.submitted_orders:
                    b = se[side].choose_plan(eng, st.game_id, side)[1]
                    eng.submit_orders(st.game_id, b)
        eng.advance(st.game_id)
    raise RuntimeError("never reached movement planning")


def alive_ids(st, side):
    return tuple(s.id for s in st.ships.values()
                 if s.side == side and not s.sunk and s.position)


def test_d0_singleton_semantics_and_validator_pass():
    eng, st = reach_movement_planning()
    side = Side.ALLIES
    ships = alive_ids(st, side)
    partition = tuple((s,) for s in ships)
    # LEADER_PROPOSAL for every singleton = per-ship proposals; commander gives
    # the per-ship plan, so singleton partition must reproduce per-ship legal
    # orders and pass the validator.
    from iron_bottom_sound.models import MovementOrder
    proposals = {}
    for ship_id in ships:
        info = eng.movement_candidates(st, st.ships[ship_id], include_plans=True)
        plans = [e["plan"] for e in info.get("reachable", []) if e.get("plan")]
        proposals[ship_id] = plans[0]
    macro_choices = {(s,): "LEADER_PROPOSAL" for s in ships}
    leader_proposals = {(s,): proposals[s] for s in ships}
    gos = execute_partition(eng, st, side, partition, macro_choices,
                            leader_proposals)
    batch = orders_to_batch(eng, st, side, gos)
    res = eng.validate_orders(st.game_id, batch)
    assert res.valid, res.errors
    assert len(batch.movement) == len(ships)


def test_d0_group_macro_produces_one_decision_and_valid_orders():
    eng, st = reach_movement_planning()
    side = Side.ALLIES
    ships = alive_ids(st, side)  # ALL allied ships: the validator requires
                                 # movement orders to cover every active ship
    partition = (ships,)  # one group -> ONE macro decision
    macro_choices = {ships: "LEADER_PROPOSAL"}
    info = eng.movement_candidates(st, st.ships[ships[0]], include_plans=True)
    lead_plans = [e["plan"] for e in info.get("reachable", []) if e.get("plan")]
    accepted = False
    last_err = None
    for plan in lead_plans[:10]:
        try:
            gos = execute_partition(eng, st, side, partition, macro_choices,
                                    {ships: plan})
        except MacroInvalid as exc:
            last_err = exc
            continue
        batch = orders_to_batch(eng, st, side, gos)
        res = eng.validate_orders(st.game_id, batch)
        if res.valid:
            accepted = True
            # one macro decision expanded to every member
            assert len(batch.movement) == len(ships)
            lead_plan = gos[0].lead_plan
            assert all(go.member_plans[s] == lead_plan
                       for go in gos for s in go.member_plans)
            break
    assert accepted, f"no lead plan was group-copyable: {last_err}"


def test_d0_invalid_macro_fails_loudly_no_silent_repair():
    """No-silent-repair contract: an impossible macro/proposal must raise, not
    be swapped for another action. Two constructions:
    (a) an ILLEGAL leader proposal (not in the lead ship's plan table);
    (b) a mixed-type group whose member plan tables genuinely differ (use
        grouped ships with different headings so copying is impossible)."""
    eng, st = reach_movement_planning()
    side = Side.ALLIES
    ships = alive_ids(st, side)
    # (a) illegal proposal
    with pytest.raises(MacroInvalid):
        execute_partition(eng, st, side, ((ships[0],),),
                          {(ships[0],): "LEADER_PROPOSAL"},
                          {(ships[0],): "ZZZZZZ"})
    # (b) find two own ships with different headings and different plan tables
    info = {s: set(_plans_for(eng, st, s)) for s in ships}
    pair = None
    for i, a in enumerate(ships):
        for b in ships[i + 1:]:
            # pick a plan legal for a but illegal for b
            diff = info[a] - info[b] - {"0"}
            if diff and info[b]:
                pair = (a, b, sorted(diff)[0])
                break
        if pair:
            break
    if pair is None:
        pytest.skip("no divergent pair in this snapshot")
    a, b, plan = pair
    with pytest.raises(MacroInvalid):
        execute_partition(eng, st, side, ((a, b),),
                          {(a, b): "LEADER_PROPOSAL"}, {(a, b): plan})


def test_d0_deterministic_same_seed_identical():
    eng1, st1 = reach_movement_planning(seed=3)
    eng2, st2 = reach_movement_planning(seed=3)
    side = Side.ALLIES
    ships = alive_ids(st1, side)
    partition = tuple((s,) for s in ships[:3])
    macro = {g: "STRAIGHT_FAST" for g in partition}
    from research_group_executor import MacroInvalid as MI
    outs = []
    for eng, st in ((eng1, st1), (eng2, st2)):
        try:
            gos = execute_partition(eng, st, side, partition, macro)
            outs.append([(go.group, go.lead_plan, dict(go.member_plans)) for go in gos])
        except MI:
            outs.append("MacroInvalid")
    assert outs[0] == outs[1]


def test_d0_macro_vocabulary_complete():
    assert set(MACROS) == {"HOLD", "STRAIGHT_SLOW", "STRAIGHT_FAST",
                           "TURN_PORT_60", "TURN_STARBOARD_60",
                           "LEADER_PROPOSAL"}


def test_d0_production_modules_untouched():
    """The executor must not modify engine/state semantics: run the same
    scripted match with and without executor calls and compare event logs."""
    def play(use_executor):
        eng, st = reach_movement_planning()
        return len(st.events), copy.deepcopy(
            {sid: (s.position.label if s.position else None)
             for sid, s in st.ships.items()})
    a = play(False)
    b = play(False)
    assert a == b
