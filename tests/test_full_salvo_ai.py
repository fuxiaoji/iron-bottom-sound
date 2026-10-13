"""State-machine policy, not a ban on legal partial player/LLM salvos."""
import pytest
from fastapi.testclient import TestClient

from iron_bottom_sound.engine import IronBottomEngine, ORDER_PHASES
from iron_bottom_sound.match import run_match
from iron_bottom_sound.models import GameOptions, HexCoord, MovementOrder, OrderBatch, Phase, Side, TorpedoOrder
from iron_bottom_sound.realistic_command import RealisticCommander
from iron_bottom_sound.tactical import PROFILES, TacticalCommander
from iron_bottom_sound.torpedo_tactics import AdaptiveTorpedoPlanner


@pytest.fixture(params=[False, True], ids=["classic", "realistic"])
def torpedo_game(request):
    engine = IronBottomEngine()
    state = engine.reset("IBS-S-03", 44, GameOptions(realistic_command=request.param, battle_report=False))
    commander = RealisticCommander() if request.param else TacticalCommander()
    for _ in range(20):
        if state.phase == Phase.TORPEDO_PLANNING:
            return engine, state
        if state.phase in ORDER_PHASES:
            for side in Side:
                result = engine.submit_orders(state.game_id, commander.choose_orders(engine, state.game_id, side))
                assert result.valid, result.errors
        engine.advance(state.game_id)
    raise AssertionError("Did not reach torpedo planning")


def commander_for(state, profile):
    factory = RealisticCommander if state.options.realistic_command else TacticalCommander
    return factory(PROFILES[profile])


def assert_full_loads(state, orders, unique=True):
    if unique:
        assert len({(order.ship_id, order.launcher_id) for order in orders}) == len(orders)
    for order in orders:
        launcher = next(item for item in state.ships[order.ship_id].torpedo_launchers if item.id == order.launcher_id)
        assert order.count == launcher.loaded > 0


@pytest.mark.parametrize("profile", [name for name, profile in PROFILES.items() if profile.torpedo_doctrine != "legacy"])
def test_all_adaptive_and_new_state_machines_use_full_loads(torpedo_game, profile):
    engine, state = torpedo_game
    before = state.model_dump(mode="json")
    for side in Side:
        plan, batch, _ = commander_for(state, profile).choose_plan(engine, state.game_id, side)
        assert engine.validate_orders(state.game_id, batch).valid
        assert_full_loads(state, batch.torpedoes)
        assert_full_loads(state, [TorpedoOrder.model_validate(order) for order in plan.tactical_analysis["orders"]])
        # These are alternatives (possibly multiple lanes from the same tube),
        # not simultaneously submitted orders; every alternative is still full.
        assert_full_loads(state, [TorpedoOrder.model_validate(row["order"]) for row in plan.tactical_analysis["top_candidates"]], unique=False)
        assert commander_for(state, profile).choose_orders(engine, state.game_id, side) == batch
    assert state.model_dump(mode="json") == before


def test_partial_inventory_empty_destroyed_and_reloading_tubes(torpedo_game):
    engine, state = torpedo_game
    own = [ship for ship in state.ships.values() if ship.side == Side.AXIS]
    tubes = [launcher for ship in own for launcher in ship.torpedo_launchers]
    tubes[0].loaded = 1
    tubes[1].loaded = 0
    tubes[2].destroyed = True
    tubes[3].reload_turns_remaining = 1
    orders, _ = AdaptiveTorpedoPlanner(PROFILES["rc_coordinated"]).orders(engine, state, Side.AXIS)
    assert orders
    assert_full_loads(state, orders)
    blocked = {(ship.id, launcher.id) for ship in own for launcher in ship.torpedo_launchers
               if launcher.loaded == 0 or launcher.destroyed or launcher.reload_turns_remaining}
    assert not blocked.intersection((order.ship_id, order.launcher_id) for order in orders)
    assert any(order.count == 1 for order in orders), "A genuinely one-round load remains a full salvo"


def test_partial_only_candidates_are_not_inflated_and_no_safe_lane_is_not_forced(torpedo_game, monkeypatch):
    engine, state = torpedo_game
    partial = [row for row in engine.torpedo_tactical_combos(state, Side.AXIS) if row["salvo_size"] == 1]
    assert partial
    monkeypatch.setattr(engine, "torpedo_tactical_combos", lambda *args: partial)
    orders, audit = AdaptiveTorpedoPlanner(PROFILES["rc_coordinated"]).orders(engine, state, Side.AXIS)
    assert not orders and not audit.selected_option_ids and not audit.top_candidates
    monkeypatch.setattr(engine, "torpedo_tactical_combos", lambda *args: [])
    assert not AdaptiveTorpedoPlanner(PROFILES["rc_coordinated"]).orders(engine, state, Side.AXIS)[0]


def test_engine_still_accepts_partial_player_orders(torpedo_game):
    engine, state = torpedo_game
    full = commander_for(state, "rc_coordinated").choose_orders(engine, state.game_id, Side.AXIS)
    assert full.torpedoes
    manual = full.model_copy(deep=True)
    manual.torpedoes = [manual.torpedoes[0].model_copy(update={"count": 1})]
    assert engine.validate_orders(state.game_id, manual).valid
    assert full.torpedoes[0].count > 1


def test_enemy_ammunition_never_affects_our_full_salvo_choice(torpedo_game):
    engine, state = torpedo_game
    before = AdaptiveTorpedoPlanner(PROFILES["rc_coordinated"]).analyze(engine, state, Side.AXIS)
    for ship in state.ships.values():
        if ship.side == Side.ALLIES:
            for launcher in ship.torpedo_launchers:
                launcher.loaded = 0
                launcher.destroyed = True
    assert AdaptiveTorpedoPlanner(PROFILES["rc_coordinated"]).analyze(engine, state, Side.AXIS) == before


def test_erma_three_round_tubes_fire_all_three_with_no_hardcoded_count():
    engine = IronBottomEngine()
    state = engine.reset("IBS-S-EM-01", 44, GameOptions(battle_report=False))
    attacker = state.ships["IBS-U-IJN-ERMA-SHIMAKAZE"]
    target = next(ship for ship in state.ships.values() if ship.side == Side.ALLIES)
    # Controlled engagement geometry, retaining actual ship records and loads.
    state.ships = {attacker.id: attacker, target.id: target}
    state.phase = Phase.TORPEDO_PLANNING
    state.land_hexes.clear()
    state.visibility = {side.value: 50 for side in Side}
    attacker.position, attacker.heading, attacker.current_speed = HexCoord.from_label("M12"), 1, 0
    target.position, target.heading, target.current_speed = HexCoord.from_label("M8"), 6, 0
    state.sealed_orders[f"{state.turn}:movement_planning"] = {
        side.value: OrderBatch(side=side, phase=Phase.MOVEMENT_PLANNING,
                              movement=[MovementOrder(ship_id=ship.id, plan="0")])
        for side, ship in [(Side.AXIS, attacker), (Side.ALLIES, target)]
    }
    orders, _ = AdaptiveTorpedoPlanner(PROFILES["rc_torpedo_wings"]).orders(engine, state, Side.AXIS)
    assert orders and {order.count for order in orders} == {3}
    assert_full_loads(state, orders)
    assert engine.validate_orders(state.game_id, OrderBatch(side=Side.AXIS, phase=state.phase, torpedoes=orders)).valid


def test_ai_api_submits_actual_full_salvo_without_revealing_orders(torpedo_game, monkeypatch):
    from iron_bottom_sound import api
    engine, state = torpedo_game
    monkeypatch.setattr(api, "engine", engine)
    api.repository.save(state)
    client = TestClient(api.app)
    expected = commander_for(state, "rc_coordinated").choose_orders(engine, state.game_id, Side.AXIS)
    assert expected.torpedoes
    player = OrderBatch(side=Side.ALLIES, phase=state.phase)
    response = client.post(f"/games/{state.game_id}/orders", headers={"X-Player-Side": "allies"}, json=player.model_dump(mode="json"))
    assert response.status_code == 200, response.text
    response = client.post(f"/games/{state.game_id}/ai-opponent", headers={"X-Player-Side": "allies"}, json={"profile": "rc_coordinated"})
    assert response.status_code == 200 and response.json() == {"valid": True, "ai_submitted": True}
    submitted = state.submitted_orders[Side.AXIS.value]
    assert submitted.torpedoes == expected.torpedoes
    assert_full_loads(state, submitted.torpedoes)
    seen = client.get(f"/games/{state.game_id}/view", headers={"X-Player-Side": "allies"}).json()
    assert "submitted_orders" not in seen


@pytest.mark.parametrize("realistic", [False, True])
def test_full_salvo_matches_finish_and_replay_without_friendly_damage(realistic):
    report, engine, _ = run_match(
        "IBS-S-03", axis="tactical", allies="tactical", axis_profile="rc_coordinated",
        allies_profile="adaptive", seed=83,
        options=GameOptions(realistic_command=realistic, battle_report=False), request_limit=200,
    )
    assert report.passed and report.completed, report.failure_reason
    assert report.fallback_count == report.manual_state_changes == 0
    state = engine.get(report.game_id)
    assert not any(event.type == "torpedo_hit" and event.payload.get("attacker_side") == event.payload.get("target_side")
                   for event in state.events)
    assert any(event.type == "torpedo_launched" for event in state.events)
    assert engine.replay(state.game_id).model_dump(mode="json") == state.model_dump(mode="json")
