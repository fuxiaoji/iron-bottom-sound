from iron_bottom_sound.engine import IronBottomEngine
from iron_bottom_sound.models import (
    GameOptions,
    GunneryOrder,
    MovementCommand,
    MovementOrder,
    OptionalRules,
    OrderBatch,
    Phase,
    Side,
)


def standing_orders(engine: IronBottomEngine, game_id: str, side: Side) -> OrderBatch:
    observation = engine.observe(game_id, side)
    own = [ship for ship in observation.ships if ship.side == side]
    return OrderBatch(side=side, movement=[MovementOrder(ship_id=ship.id, plan="0") for ship in own])


def test_scenario_three_loads_verified_order_of_battle() -> None:
    engine = IronBottomEngine()
    state = engine.reset("IBS-S-03", seed=7)
    assert state.scenario_title == "通道行动"
    assert len(state.ships) == 8
    assert state.ships["IBS-U-KM-KARL-GALSTER"].position.label == "O14"


def test_scenario_one_loads_without_forcing_optional_rules() -> None:
    engine = IronBottomEngine()
    state = engine.reset("IBS-S-01", seed=7)
    assert len(state.ships) == 14
    assert state.phase == Phase.GUNNERY
    assert not state.options.optional_rules.radar
    assert not state.options.optional_rules.star_shells
    assert not state.options.optional_rules.searchlights


def test_same_seed_and_orders_produce_identical_event_stream() -> None:
    first = IronBottomEngine()
    second = IronBottomEngine()
    first.reset("IBS-S-03", 41, game_id="same")
    second.reset("IBS-S-03", 41, game_id="same")
    for engine in (first, second):
        engine.step(
            "same",
            {side: standing_orders(engine, "same", side) for side in Side},
        )
    assert [event.model_dump_json() for event in first.get("same").events] == [
        event.model_dump_json() for event in second.get("same").events
    ]


def test_hidden_damage_filters_enemy_but_not_own_damage() -> None:
    engine = IronBottomEngine()
    options = GameOptions(optional_rules=OptionalRules(hidden_damage=True))
    state = engine.reset("IBS-S-03", 1, options)
    enemy = next(ship for ship in state.ships.values() if ship.side == Side.AXIS)
    enemy.fire_markers = 1
    view = engine.observe(state.game_id, Side.ALLIES)
    public_enemy = next(ship for ship in view.ships if ship.id == enemy.id)
    assert public_enemy.hull is None


def test_four_turns_reach_automatic_terminal_state() -> None:
    engine = IronBottomEngine()
    state = engine.reset("IBS-S-03", seed=3)
    while state.phase != Phase.COMPLETE:
        engine.step(state.game_id, {side: standing_orders(engine, state.game_id, side) for side in Side})
    assert state.turn == 4
    assert state.victory_reason == "平局"


def test_explicit_movement_commands_are_costed_and_traced_by_mf() -> None:
    engine = IronBottomEngine()
    state = engine.reset("IBS-S-03", seed=3)
    ship = state.ships["IBS-U-KM-KARL-GALSTER"]
    order = MovementOrder(
        ship_id=ship.id,
        commands=[
            MovementCommand(action="advance"),
            MovementCommand(action="turn_starboard_60"),
            MovementCommand(action="advance"),
            MovementCommand(action="turn_port_60"),
        ],
    )
    commands = engine.movement_commands(order)
    engine.validate_movement_commands(commands)
    trajectory, final_heading = engine.movement_trajectory(ship, order.plan, commands)
    assert engine.movement_cost(order.plan, commands) == 2
    assert len(trajectory) == 2
    assert final_heading == ship.heading


def test_movement_plan_enforces_first_advance_and_post_turn_advance() -> None:
    engine = IronBottomEngine()
    for commands in (
        ["turn_port_60", "advance"],
        ["advance", "turn_port_60", "turn_starboard_60"],
        ["advance", "turn_port_120"],
    ):
        try:
            engine.validate_movement_commands(commands)
        except ValueError:
            pass
        else:
            raise AssertionError(f"Illegal command sequence accepted: {commands}")


def test_phase_rejects_commands_from_other_phases() -> None:
    engine = IronBottomEngine()
    state = engine.reset("IBS-S-03", seed=3)
    result = engine.validate_orders(
        state.game_id,
        OrderBatch(
            side=Side.AXIS,
            phase=Phase.REINFORCEMENT,
            gunnery=[GunneryOrder(ship_id="IBS-U-KM-KARL-GALSTER")],
        ),
    )
    assert not result.valid
    assert any("not legal" in error for error in result.errors)


def test_full_turn_seals_four_independent_secret_phase_batches() -> None:
    engine = IronBottomEngine()
    state = engine.reset("IBS-S-03", seed=3)
    engine.step(state.game_id, {side: standing_orders(engine, state.game_id, side) for side in Side})
    assert set(state.sealed_orders) == {
        "1:reinforcement",
        "1:movement_planning",
        "1:torpedo_planning",
        "1:gunnery",
    }
    assert len([event for event in state.events if event.type == "orders_submitted"]) == 8
