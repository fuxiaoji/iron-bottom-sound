"""IR-7: the gunnery authority boundary, proved rather than asserted.

The mode's claim is that a formation or fleet agent can influence *preference* and nothing
else.  Five things must hold, and each is checked here against the engine's own records:

1. a decision object cannot carry gunnery fields, and one that does is rejected outright;
2. a raw gunnery batch submitted on an agent's behalf is refused in command-delay mode;
3. priority weights change which legal target is preferred, and never which targets or
   mounts are legal;
4. a weight outside the bound is refused where the decision is parsed (and clamped where
   the selector consumes it);
5. a directive naming a target the formation cannot see is inert - the selector still
   returns a legal order.

The audit (``run_audits.audit_gunnery_authority``) covers the same ground on a live game;
these are the unit-level proofs, so a regression is caught by the suite rather than only by
the audit.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend" / "src"))

from iron_bottom_sound import command_delay, formation_agents, target_priority  # noqa: E402
from iron_bottom_sound.command_observation import LOCAL_PRIORITY_WEIGHT_LIMIT  # noqa: E402
from iron_bottom_sound.engine import ORDER_PHASES, IronBottomEngine  # noqa: E402
from iron_bottom_sound.llm import LLMPlayerSession  # noqa: E402
from iron_bottom_sound.models import (  # noqa: E402
    GameOptions, GunneryOrder, OrderBatch, Phase, Side, TargetPriorityDirective,
)
from iron_bottom_sound.realistic_command import (  # noqa: E402
    RealisticCommander, default_setup_orders,
)

SCENARIO = "IBS-S-EM-01"
SEED = 19440619
GUNNERY_FIELDS = ("gunnery", "gunnery_orders", "mounts", "mount_ids", "firing_solution",
                  "hit_modifier", "expected_hits")


def _game_at_gunnery(turn: int = 3, *, require_candidates: bool = True):
    """A game sitting in a gunnery phase, by default one where the side has targets.

    Early turns have no contacts in this scenario, and a gunnery phase with no legal
    candidates proves nothing about the selector - so the fixture advances until the axes
    side actually has something to shoot at (bounded, and the caller can turn it off).
    """
    engine = IronBottomEngine()
    state = engine.reset(SCENARIO, SEED, GameOptions(
        realistic_command=True, command_delay_mode=True,
    ))
    for side in Side:
        assert engine.submit_orders(state.game_id, OrderBatch(
            side=side, phase=Phase.FORMATION_SETUP,
            formation_setup=default_setup_orders(state, side),
        )).valid
    engine.advance(state.game_id)
    sessions = {side: LLMPlayerSession(side, RealisticCommander()) for side in Side}
    steps = 0
    while state.phase is not Phase.COMPLETE and steps < 300:
        steps += 1
        if state.phase is Phase.GUNNERY and state.turn >= turn:
            # A candidate list is truthy as soon as any ship is afloat, even with no legal
            # target among them; what these tests need is at least one target row.
            rows = sum(len(item["targets"])
                       for item in engine._gunnery_candidates(state, Side.AXIS))
            if not require_candidates or rows:
                return engine, state
        if state.phase in ORDER_PHASES:
            for side in Side:
                if side.value in state.submitted_orders:
                    continue
                if state.phase is Phase.MOVEMENT_PLANNING:
                    batch = OrderBatch(side=side, phase=state.phase,
                                       formation_movement=command_delay.formation_orders(state, side))
                elif state.phase is Phase.GUNNERY:
                    batch = command_delay.gunnery_batch(state, side)
                else:
                    batch = sessions[side].choose_orders(engine, state.game_id)
                result = engine.submit_orders(state.game_id, batch)
                if not result.valid and state.phase is Phase.MOVEMENT_PLANNING:
                    _, fallback, _ = RealisticCommander().choose_plan(engine, state.game_id, side)
                    result = engine.submit_orders(state.game_id, fallback)
                assert result.valid, result.errors[:2]
        engine.advance(state.game_id)
    raise AssertionError("never reached a gunnery phase")


# --------------------------------------------------------------------- 1

def test_1_a_decision_cannot_carry_gunnery_fields() -> None:
    fields = set(formation_agents.FormationDecision.model_fields)
    assert not (set(GUNNERY_FIELDS) & fields), (
        f"a formation decision must not expose gunnery fields: {sorted(set(GUNNERY_FIELDS) & fields)}"
    )
    # the shape guard refuses a dict that tries anyway, whatever it says about itself
    errors = target_priority.validate_agent_decision_shape({
        "formation_id": "f", "turn": 1, "phase": "gunnery",
        "target_priority_adjustments": [], "mounts": [{"mount_id": "P1"}],
    })
    assert errors, "a decision that names mounts must be rejected"


# --------------------------------------------------------------------- 2

def test_2_a_raw_gunnery_batch_is_refused() -> None:
    engine, state = _game_at_gunnery()
    axis = Side.AXIS
    candidates = engine._gunnery_candidates(state, axis)
    if not candidates:
        pytest.skip("no legal candidates in this phase")
    ship_id, target = sorted(
        (item["ship_id"], row["target_id"])
        for item in candidates for row in item["targets"]
    )[0]
    result = engine.validate_orders(state.game_id, OrderBatch(
        side=axis, phase=Phase.GUNNERY,
        gunnery=[GunneryOrder(ship_id=ship_id, primary_target=target, mounts=[])],
    ))
    assert not result.valid, "an agent must not be able to submit gunnery orders directly"
    assert any("engine selector" in error for error in result.errors)


# --------------------------------------------------------------------- 3

def test_3_weights_change_preference_not_legality() -> None:
    engine, state = _game_at_gunnery()
    side = Side.AXIS
    candidates = engine._gunnery_candidates(state, side)
    legal_pairs = {
        (item["ship_id"], row["target_id"])
        for item in candidates for row in item["targets"]
    }
    assert legal_pairs, "no legal gunnery candidates to test with"

    plain = target_priority.select_gunnery_orders(engine, state, side, [])
    some_target = sorted({target for _, target in legal_pairs})[0]
    weighted = target_priority.select_gunnery_orders(
        engine, state, side,
        [TargetPriorityDirective(formation_id="any", source="LOCAL_AGENT",
                                 target_id=some_target, weight=0.5)],
    )
    # every order stays inside the engine's legal candidate set...
    for order in list(plain) + list(weighted):
        assert (order.ship_id, order.primary_target) in legal_pairs, (
            "a priority weight must never make an illegal shot legal"
        )
    # ...and the weights are what changed: the favoured target gains priority weight only
    favoured = [order for order in weighted if order.primary_target == some_target]
    assert favoured, "the weighted target should be preferred somewhere"
    # the engine's own mount allocation is untouched by weights: mounts come from the
    # candidate record either way
    for order in weighted:
        row = next(row for item in candidates if item["ship_id"] == order.ship_id
                   for row in item["targets"] if row["target_id"] == order.primary_target)
        # mounts come from the engine's candidate record: a weight can reorder targets, it
        # cannot add a mount the arc does not permit.  (Mounts are GunMountOrder objects,
        # so compare their identifiers rather than the objects.)
        assigned = {mount.mount_id if hasattr(mount, "mount_id") else str(mount)
                    for mount in order.mounts}
        assert assigned <= set(row["mount_ids"])


# --------------------------------------------------------------------- 4

def test_4_the_weight_bound_is_enforced() -> None:
    from iron_bottom_sound.formation_llm import parse_response
    from iron_bottom_sound.command_observation import formation_observation

    engine, state = _game_at_gunnery()
    side = Side.AXIS
    views = [
        formation_observation(engine, state, side, formation.id)
        for formation in command_delay.active_formations(state, side)
    ]
    with_targets = [item for item in views if item.legal_target_priority_options]
    assert with_targets, "need a formation with a visible target to weight"
    view = with_targets[0]
    target = view.legal_target_priority_options[0]["target_id"]
    over = f'{{"target_priority_adjustments": [{{"target_id": "{target}", "weight": 0.9}}]}}'
    decision, errors = parse_response(over, view)
    assert decision is None and errors, "a weight beyond the local limit must be refused"
    assert any("weight" in error for error in errors)
    ok = f'{{"target_priority_adjustments": [{{"target_id": "{target}", "weight": 0.4}}]}}'
    decision, errors = parse_response(ok, view)
    assert decision is not None and not errors
    # and the selector clamps anything that arrived from elsewhere
    assert target_priority.clamp_local(0.9, LOCAL_PRIORITY_WEIGHT_LIMIT) == LOCAL_PRIORITY_WEIGHT_LIMIT


# --------------------------------------------------------------------- 5

def test_5_a_directive_for_an_unseen_target_is_inert() -> None:
    engine, state = _game_at_gunnery()
    side = Side.AXIS
    enemies = [ship.id for ship in state.ships.values()
               if ship.side is not side and not ship.sunk]
    candidates = engine._gunnery_candidates(state, side)
    visible_targets = {row["target_id"] for item in candidates for row in item["targets"]}
    unseen = next((ship_id for ship_id in enemies if ship_id not in visible_targets), None)
    if unseen is None:
        pytest.skip("every enemy hull is visible to this side right now")

    baseline = target_priority.select_gunnery_orders(engine, state, side, [])
    with_unseen = target_priority.select_gunnery_orders(
        engine, state, side,
        [TargetPriorityDirective(formation_id="any", source="LOCAL_AGENT",
                                 target_id=unseen, weight=0.5)],
    )
    assert [(order.ship_id, order.primary_target) for order in with_unseen] == \
           [(order.ship_id, order.primary_target) for order in baseline], (
        "a directive naming an invisible ship must change nothing"
    )
    for order in with_unseen:
        assert order.primary_target in visible_targets
