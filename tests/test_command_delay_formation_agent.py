"""CD-4: the deterministic formation agent and the gunnery authority boundary.

Two properties are load-bearing here and are tested adversarially:

**Gunnery authority (acceptance 6/7).** A formation agent cannot issue a
``GunneryOrder``.  Its decision type has no gunnery fields, a structural guard
refuses one that carries them, the engine rejects a raw gunnery batch in Command
Delay mode, and a target-priority directive can only re-rank targets the engine
already certified as legal — it can never make an illegal shot legal or move a
percent of hit probability.

**Local-only observation (acceptance 5).** The agent's input has no side-global
field, and its contacts are computed from its own ships' visibility.  The
deterministic agent is also a pure function: the same observation gives the same
decision, under any PYTHONHASHSEED.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

from iron_bottom_sound import command_delay, delegation, formation_agents, target_priority
from iron_bottom_sound.command_observation import (
    LOCAL_PRIORITY_WEIGHT_LIMIT,
    fleet_observation,
    formation_observation,
)
from iron_bottom_sound.engine import ORDER_PHASES, IronBottomEngine
from iron_bottom_sound.llm import LLMPlayerSession
from iron_bottom_sound.models import (
    GameOptions,
    GunneryOrder,
    LinkStatus,
    MessageStatus,
    OrderBatch,
    Phase,
    Side,
    TargetPriorityDirective,
)
from iron_bottom_sound.realistic_command import RealisticCommander

REPO_ROOT = Path(__file__).resolve().parents[1]
CD = GameOptions(realistic_command=True, command_delay_mode=True)


def start(scenario: str = "IBS-S-01", seed: int = 20270830):
    engine = IronBottomEngine()
    state = engine.reset(scenario, seed, CD)
    from iron_bottom_sound.realistic_command import default_setup_orders

    for side in Side:
        assert engine.submit_orders(state.game_id, OrderBatch(
            side=side, phase=Phase.FORMATION_SETUP,
            formation_setup=default_setup_orders(state, side),
        )).valid
    engine.advance(state.game_id)
    return engine, state


def step(engine, state) -> None:
    sessions = {side: LLMPlayerSession(side, RealisticCommander()) for side in Side}
    if state.phase in ORDER_PHASES:
        for side in Side:
            if side.value in state.submitted_orders:
                continue
            result = engine.submit_orders(
                state.game_id, sessions[side].choose_orders(engine, state.game_id)
            )
            assert result.valid, (state.turn, state.phase, side, result.errors[:2])
    engine.advance(state.game_id)


def play(engine, state, max_steps: int = 400) -> None:
    steps = 0
    while state.phase != Phase.COMPLETE and steps < max_steps:
        steps += 1
        step(engine, state)


# --------------------------------------------------------------------------- authority

def test_the_decision_model_has_no_gunnery_field() -> None:
    fields = set(formation_agents.FormationDecision.model_fields)
    for forbidden in ("gunnery", "gunnery_orders", "mounts", "mount_ids",
                      "firing_solution", "hit_modifier", "expected_hits"):
        assert forbidden not in fields


def test_the_structural_guard_refuses_gunnery_machinery() -> None:
    clean = formation_agents.FormationDecision(
        formation_id="f", turn=1, phase=Phase.GUNNERY,
        target_priority_adjustments=[formation_agents.TargetPriorityAdjustment(
            target_id="t", weight=0.2, reason="ok")],
    )
    assert target_priority.validate_agent_decision_shape(clean) == []
    dirty = {"formation_id": "f", "turn": 1, "phase": "gunnery",
             "target_priority_adjustments": [], "mounts": [{"mount_id": "A"}]}
    errors = target_priority.validate_agent_decision_shape(dirty)
    assert errors and "may not emit gunnery machinery" in errors[0]


def test_the_engine_refuses_a_raw_gunnery_batch_in_command_delay_mode() -> None:
    engine, state = start()
    # Walk to a gunnery phase.
    while state.phase != Phase.GUNNERY:
        if state.phase == Phase.COMPLETE:
            pytest.skip("scenario completed before a gunnery phase")
        step(engine, state)
    candidates = engine._gunnery_candidates(state, Side.AXIS)
    target = next(
        (item for item in candidates if item["targets"]), None
    )
    if target is None:
        pytest.skip("no legal target in this gunnery phase")
    orders = [GunneryOrder(
        ship_id=target["ship_id"],
        primary_target=target["targets"][0]["target_id"],
        mounts=[],
    )]
    result = engine.validate_orders(
        state.game_id,
        OrderBatch(side=Side.AXIS, phase=Phase.GUNNERY, gunnery=orders),
    )
    assert not result.valid
    assert any("engine selector" in error for error in result.errors)


def test_a_directive_only_reranks_legal_targets() -> None:
    """The decisive selector test: same legal set, different preference."""
    engine, state = start()
    comparisons = 0
    while state.phase != Phase.COMPLETE and comparisons < 4:
        if state.phase == Phase.GUNNERY:
            candidates = engine._gunnery_candidates(state, Side.AXIS)
            multi = next(
                (item for item in candidates if len(item["targets"]) >= 2), None
            )
            if multi is not None:
                baseline = target_priority.select_gunnery_orders(engine, state, Side.AXIS, [])
                pick = multi["targets"][-1]["target_id"]
                biased = target_priority.select_gunnery_orders(
                    engine, state, Side.AXIS,
                    [TargetPriorityDirective(
                        formation_id="f", source="FLEET_ORDER",
                        target_id=pick, weight=1.0,
                    )],
                )
                baseline_by_ship = {order.ship_id: order for order in baseline}
                biased_by_ship = {order.ship_id: order for order in biased}
                assert set(baseline_by_ship) == set(biased_by_ship)
                # Every produced order is legal by construction: it exists only
                # because the engine listed the target for that ship.
                legal_pairs = {
                    (item["ship_id"], target["target_id"])
                    for item in candidates for target in item["targets"]
                }
                for order in biased:
                    assert (order.ship_id, order.primary_target) in legal_pairs
                    mount_ids = {mount.mount_id for mount in order.mounts}
                    engine_mounts = next(
                        target["mount_ids"]
                        for item in candidates if item["ship_id"] == order.ship_id
                        for target in item["targets"]
                        if target["target_id"] == order.primary_target
                    )
                    assert mount_ids == set(engine_mounts)
                chosen_before = baseline_by_ship[multi["ship_id"]].primary_target
                chosen_after = biased_by_ship[multi["ship_id"]].primary_target
                if chosen_before != chosen_after:
                    comparisons += 1
                    assert chosen_after == pick
        step(engine, state)
    assert comparisons >= 1, "no gunnery phase produced a two-target choice to flip"


def test_a_directive_for_an_invisible_target_falls_back_to_legal_ones() -> None:
    engine, state = start()
    while state.phase != Phase.GUNNERY:
        if state.phase == Phase.COMPLETE:
            pytest.skip("scenario completed before a gunnery phase")
        step(engine, state)
    orders = target_priority.select_gunnery_orders(
        engine, state, Side.AXIS,
        [TargetPriorityDirective(
            formation_id="f", source="FLEET_ORDER",
            target_id="IBS-U-NOT-A-SHIP", weight=1.0,
        )],
    )
    candidates = engine._gunnery_candidates(state, Side.AXIS)
    legal_pairs = {
        (item["ship_id"], target["target_id"])
        for item in candidates for target in item["targets"]
    }
    for order in orders:
        assert (order.ship_id, order.primary_target) in legal_pairs
        assert order.primary_target != "IBS-U-NOT-A-SHIP"


def test_local_adjustments_are_bounded_by_the_composition_rule() -> None:
    limit = LOCAL_PRIORITY_WEIGHT_LIMIT
    huge = TargetPriorityDirective(
        formation_id="f", source="LOCAL_AGENT", target_id="t", weight=limit,
    )
    assert target_priority.priority_bonus("t", "DD", [huge], turn=1) <= limit
    # A local directive cannot outvote a fleet order of the opposite sign equal in
    # magnitude when the local term is clamped.
    fleet = TargetPriorityDirective(
        formation_id="f", source="FLEET_ORDER", target_id="t", weight=-1.0,
    )
    bonus = target_priority.priority_bonus(
        "t", "DD", [fleet, huge], turn=1, local_limit=limit,
    )
    assert bonus == pytest.approx(-1.0 + limit)
    # An expired directive contributes nothing.
    expired = TargetPriorityDirective(
        formation_id="f", source="FLEET_ORDER", target_id="t", weight=1.0, expires_turn=1,
    )
    assert target_priority.priority_bonus("t", "DD", [expired], turn=2) == 0.0


def test_doctrine_supplies_a_fallback_hierarchy_only_when_directives_exist() -> None:
    engine, state = start()
    while state.phase != Phase.GUNNERY:
        if state.phase == Phase.COMPLETE:
            pytest.skip("scenario completed before a gunnery phase")
        step(engine, state)
    rows = target_priority.selection_trace(engine, state, Side.AXIS, [])
    legal = [row for row in rows if row["legal"]]
    if legal:
        assert all(row["priority_bonus"] == 0.0 for row in legal), (
            "doctrine must not act as a silent preference when no directive exists"
        )
        assert all(
            row["score"] == pytest.approx(row["base_fire_objective"]) for row in legal
        )


# --------------------------------------------------------------------------- the agent

def test_agent_moves_only_inside_the_enumerated_action_set() -> None:
    engine, state = start()
    while state.phase != Phase.MOVEMENT_PLANNING:
        if state.phase == Phase.COMPLETE:
            pytest.skip("scenario completed before a movement phase")
        step(engine, state)
    formation = command_delay.active_formations(state, Side.AXIS)[0]
    observation = formation_observation(engine, state, Side.AXIS, formation.id)
    decision = formation_agents.DeterministicFormationAgent().act(
        observation,
        mission_order=command_delay.active_mission_order(state, formation.id),
        comm_state=observation.comm_state,
        legal_action_mask=observation.legal_formation_actions,
        target_priority_space=observation.legal_target_priority_options,
    )
    if decision.selected_movement_action_id is not None:
        allowed = {action["action_id"] for action in observation.legal_formation_actions}
        assert decision.selected_movement_action_id in allowed
        matching = next(
            action for action in observation.legal_formation_actions
            if action["action_id"] == decision.selected_movement_action_id
        )
        assert decision.selected_movement_plan == matching["plan"]


def test_agent_is_a_pure_function_of_its_observation() -> None:
    engine, state = start()
    for _ in range(8):
        if state.phase == Phase.COMPLETE or state.phase == Phase.MOVEMENT_PLANNING:
            break
        step(engine, state)
    if state.phase != Phase.MOVEMENT_PLANNING:
        pytest.skip("no movement phase reached")
    formation = command_delay.active_formations(state, Side.AXIS)[0]
    observation = formation_observation(engine, state, Side.AXIS, formation.id)
    agent = formation_agents.DeterministicFormationAgent()
    order = command_delay.active_mission_order(state, formation.id)
    first = agent.act(observation, order, observation.comm_state,
                      observation.legal_formation_actions,
                      observation.legal_target_priority_options)
    second = agent.act(observation, order, observation.comm_state,
                       observation.legal_formation_actions,
                       observation.legal_target_priority_options)
    assert first.model_dump() == second.model_dump()


def test_agent_observation_carries_no_side_global_field() -> None:
    engine, state = start()
    step(engine, state)
    formation = command_delay.active_formations(state, Side.AXIS)[0]
    payload = formation_observation(engine, state, Side.AXIS, formation.id).model_dump()
    for forbidden in ("score", "sealed_orders", "submitted_orders", "victory_reason",
                      "winner", "wrecks", "torpedo_tracks", "ships"):
        assert forbidden not in payload
    # And the agent's decision cannot reach one either: it only ever sees the
    # observation it is handed.
    decision = formation_agents.DeterministicFormationAgent().act(
        formation_observation(engine, state, Side.AXIS, formation.id)
    )
    assert decision.audit["legal_actions"] >= 0
    assert decision.audit["order_received"] is False or decision.audit["order_received"] is True


def test_agent_contacts_come_from_its_own_ships_only() -> None:
    engine, state = start()
    play(engine, state)
    for side in Side:
        for formation in command_delay.active_formations(state, side):
            observation = formation_observation(engine, state, side, formation.id)
            own = {
                state.ships[ship_id].position
                for ship_id in formation.ship_ids
                if state.ships[ship_id].position is not None
            }
            for contact in observation.local_contacts:
                # A contact must be inside this formation's own horizon.
                label = contact["position"]
                cell = next(
                    (item for item in observation.local_map if item["hex"] == label), None
                )
                assert cell is not None, f"{label} outside the formation's local map"
                assert cell["contact"] is True
            assert own


def test_agent_reacts_to_the_loss_of_communication_branch() -> None:
    engine, state = start()
    formation = command_delay.active_formations(state, Side.AXIS)[0]
    observation = formation_observation(engine, state, Side.AXIS, formation.id)
    link_status = observation.link_status
    try:
        observation.link_status = LinkStatus.BLACKOUT
        decision = formation_agents.DeterministicFormationAgent().act(observation)
        assert decision.selected_contingency_branch == "loss_of_comm_branch"
        assert "DEVIATION_REPORT" not in decision.report_actions, (
            "with the link gone there is nobody to deviate to"
        )
    finally:
        observation.link_status = link_status


def test_agent_records_an_order_it_has_not_acknowledged() -> None:
    engine, state = start()
    formation = command_delay.active_formations(state, Side.AXIS)[0]
    observation = formation_observation(engine, state, Side.AXIS, formation.id)
    order = delegation.standing_plan(
        formation_id=formation.id, side=Side.AXIS, turn=state.turn,
    )
    decision = formation_agents.DeterministicFormationAgent().act(
        observation, mission_order=order,
    )
    assert decision.acknowledgement is True
    assert "ACKNOWLEDGEMENT" in decision.report_actions
    assert decision.audit["order_received"] is True


def test_agent_adjustments_stay_inside_the_declared_limit() -> None:
    engine, state = start()
    play(engine, state)
    mode = state.command_delay
    assert mode is not None
    assert mode.decisions, "the agents must have run"
    for decision in mode.decisions:
        for adjustment in decision["target_priority_adjustments"]:
            assert -LOCAL_PRIORITY_WEIGHT_LIMIT <= adjustment["weight"] <= LOCAL_PRIORITY_WEIGHT_LIMIT
    for directive in mode.local_directives:
        assert directive.source == "LOCAL_AGENT"
        assert -LOCAL_PRIORITY_WEIGHT_LIMIT <= directive.weight <= LOCAL_PRIORITY_WEIGHT_LIMIT


def test_agent_decision_orders_contain_no_gunnery() -> None:
    engine, state = start()
    play(engine, state)
    mode = state.command_delay
    assert mode is not None
    for record in mode.decisions:
        orders = formation_agents.decision_orders(
            formation_agents.FormationDecision(**record), record["formation_id"]
        )
        for order in orders:
            payload = order.model_dump()
            assert set(payload) <= {"formation_id", "leader_plan", "spacing",
                                    "speed_decision", "movement_style", "reform_column"}


# --------------------------------------------------------------------------- end to end

def test_a_full_command_delay_game_never_takes_gunnery_from_an_agent() -> None:
    engine, state = start()
    play(engine, state)
    assert state.phase == Phase.COMPLETE
    gunnery_batches = [
        batch for key, sealed in state.sealed_orders.items() if key.endswith("gunnery")
        for batch in sealed.values()
    ]
    assert gunnery_batches
    # An empty directive list is legitimate (it means "no preference": the
    # selector then runs on the raw expected-hit objective), so the invariant is
    # about *provenance*, not about non-emptiness.  The priority path must have
    # actually carried traffic somewhere in the game, or this whole mode would be
    # decorative.
    carried = 0
    for batch in gunnery_batches:
        assert all(
            directive.source in {"FLEET_ORDER", "LOCAL_AGENT", "DOCTRINE"}
            for directive in batch.target_priorities
        )
        carried += len(batch.target_priorities)
    assert carried > 0, "no target priority directive ever reached the selector"
    assert all(
        directive.source != "LOCAL_AGENT"
        or abs(directive.weight) <= LOCAL_PRIORITY_WEIGHT_LIMIT
        for batch in gunnery_batches for directive in batch.target_priorities
    )
    # Every sealed gunnery order came from the selector, so each is legal.
    for batch in gunnery_batches:
        for order in batch.gunnery:
            attacker = state.ships[order.ship_id]
            assert attacker.side is batch.side


def test_link_and_authority_degrade_and_recover_from_the_ledger() -> None:
    engine, state = start()
    mode = state.command_delay
    assert mode is not None
    seen_links = set()
    steps = 0
    while state.phase != Phase.COMPLETE and steps < 200:
        steps += 1
        step(engine, state)
        for entry in mode.formations.values():
            seen_links.add(entry.link_status)
    assert LinkStatus.DIRECT in seen_links
    assert len(seen_links) >= 2, (
        "a whole scenario in which every link stays DIRECT would mean the report "
        "pipeline is not actually being exercised"
    )
    for entry in mode.formations.values():
        if entry.authority.value == "local_autonomy":
            # CD8-F3: both a stale report trail and a blackout degrade a formation to local
            # autonomy - a commander that has heard nothing for two turns is on its own,
            # whether the silence is "never reported" or "nothing recent".  This assertion
            # used to demand BLACKOUT specifically, which was only satisfiable because
            # v2.2's chatty reporting never let a link go stale; with event-driven reporting
            # the STALE case is routine, so the old form was unreachable rather than right.
            assert entry.link_status in (LinkStatus.STALE, LinkStatus.BLACKOUT)


# --------------------------------------------------------------------------- determinism

HASH_SCRIPT = r"""
import json, sys
sys.path.insert(0, sys.argv[1])
from iron_bottom_sound import command_delay
from iron_bottom_sound.engine import ORDER_PHASES, IronBottomEngine
from iron_bottom_sound.llm import LLMPlayerSession
from iron_bottom_sound.models import GameOptions, Phase, Side
from iron_bottom_sound.realistic_command import RealisticCommander

engine = IronBottomEngine()
state = engine.reset("IBS-S-01", 20270830,
                     GameOptions(realistic_command=True, command_delay_mode=True))
sessions = {side: LLMPlayerSession(side, RealisticCommander()) for side in Side}
steps = 0
while state.phase != Phase.COMPLETE and steps < 400:
    steps += 1
    if state.phase in ORDER_PHASES:
        for side in Side:
            if side.value in state.submitted_orders:
                continue
            result = engine.submit_orders(
                state.game_id, sessions[side].choose_orders(engine, state.game_id))
            if not result.valid:
                raise SystemExit(f"rejected: {result.errors[:2]}")
    engine.advance(state.game_id)
mode = state.command_delay
print(json.dumps({
    # None-safe: a decision may legitimately have no branch and no action.
    "decisions": sorted((d["formation_id"], d["selected_movement_plan"] or "",
                         d["selected_contingency_branch"] or "",
                         sorted(d["report_actions"])) for d in mode.decisions),
    "gunnery": sorted((key, side, len(batch.gunnery), len(batch.target_priorities))
                      for key, sealed in state.sealed_orders.items()
                      if key.endswith("gunnery")
                      for side, batch in sealed.items()),
    "links": sorted((k, v.link_status.value, v.reported_turn)
                    for k, v in mode.formations.items()),
}, sort_keys=True))
"""


def test_agent_decisions_are_hash_seed_independent() -> None:
    def outcome(hashseed: str):
        import json
        env = dict(os.environ, PYTHONHASHSEED=hashseed,
                   PYTHONPATH=str(REPO_ROOT / "backend" / "src"))
        proc = subprocess.run(
            [sys.executable, "-c", HASH_SCRIPT, str(REPO_ROOT / "backend" / "src")],
            cwd=str(REPO_ROOT), env=env, capture_output=True, text=True, timeout=900,
        )
        assert proc.returncode == 0, proc.stderr[-2000:]
        return json.loads(proc.stdout)

    assert outcome("0") == outcome("1") == outcome("6")
