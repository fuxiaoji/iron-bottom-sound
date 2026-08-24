from iron_bottom_sound.engine import D66_VALUES, IronBottomEngine
from iron_bottom_sound.models import (
    GameOptions,
    ContactSetupOrder,
    ContactMovementOrder,
    GunMountOrder,
    GunneryOrder,
    HexCoord,
    IlluminationOrder,
    MarkerState,
    MovementCommand,
    MovementOrder,
    OptionalRules,
    OrderBatch,
    Phase,
    Side,
    SmokeOrder,
    TorpedoOrder,
    TorpedoTrack,
    WreckState,
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
    assert len([ship for ship in state.ships.values() if ship.position]) == 14
    assert len([ship for ship in state.ships.values() if ship.reinforcement_turn == 4]) == 8
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


def test_replay_rebuilds_state_and_byte_equivalent_event_stream_without_snapshot() -> None:
    engine = IronBottomEngine()
    state = engine.reset("IBS-S-03", 41, game_id="replay-source")
    engine.step(
        state.game_id,
        {side: standing_orders(engine, state.game_id, side) for side in Side},
    )
    rebuilt = engine.replay(state.events)
    assert rebuilt.model_dump(mode="json") == state.model_dump(mode="json")
    assert [event.model_dump_json() for event in rebuilt.events] == [
        event.model_dump_json() for event in state.events
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
    own = next(ship for ship in state.ships.values() if ship.side == Side.ALLIES)
    public_own = next(ship for ship in view.ships if ship.id == own.id)
    assert public_own.hull == own.hull

    plain = IronBottomEngine()
    plain_state = plain.reset("IBS-S-03", 1)
    plain_enemy = next(ship for ship in plain_state.ships.values() if ship.side == Side.AXIS)
    plain_view = plain.observe(plain_state.game_id, Side.ALLIES)
    assert next(ship for ship in plain_view.ships if ship.id == plain_enemy.id).hull == plain_enemy.hull


def test_ship_combat_history_attributes_source_and_respects_hidden_damage() -> None:
    engine = IronBottomEngine()
    state = engine.reset("IBS-S-03", 13)
    attacker = next(ship for ship in state.ships.values() if ship.side == Side.AXIS)
    target = next(ship for ship in state.ships.values() if ship.side == Side.ALLIES)
    engine._event(
        state,
        "gunnery_result",
        f"{target.name} 命中结果 44",
        payload={"attacker": attacker.id, "target": target.id, "result": {"hull": 1}},
    )
    axis_ship = next(ship for ship in engine.observe(state.game_id, Side.AXIS).ships if ship.id == attacker.id)
    allies_ship = next(ship for ship in engine.observe(state.game_id, Side.ALLIES).ships if ship.id == target.id)
    assert axis_ship.combat_history[-1].direction == "inflicted"
    assert axis_ship.combat_history[-1].related_ship_name == target.name
    assert allies_ship.combat_history[-1].direction == "received"
    assert allies_ship.combat_history[-1].related_ship_name == attacker.name

    hidden = IronBottomEngine()
    hidden_state = hidden.reset(
        "IBS-S-03", 13, GameOptions(optional_rules=OptionalRules(hidden_damage=True))
    )
    hidden._event(
        hidden_state,
        "gunnery_result",
        "敌舰隐藏损伤",
        payload={"attacker": attacker.id, "target": target.id, "result": {"hull": 1}},
    )
    hidden_attacker = next(
        ship for ship in hidden.observe(hidden_state.game_id, Side.AXIS).ships if ship.id == attacker.id
    )
    assert not any(entry.message == "敌舰隐藏损伤" for entry in hidden_attacker.combat_history)


def test_observation_exposes_only_own_planning_hardware() -> None:
    engine = IronBottomEngine()
    state = engine.reset("IBS-S-03", 17)
    view = engine.observe(state.game_id, Side.AXIS)
    own = next(ship for ship in view.ships if ship.side == Side.AXIS)
    enemy = next(ship for ship in view.ships if ship.side == Side.ALLIES)
    assert own.max_speed is not None
    assert (own.min_legal_speed, own.max_legal_speed) == (0, 6)
    assert own.gun_mounts
    assert own.torpedo_launchers
    assert own.torpedo_type
    assert enemy.max_speed is None
    assert enemy.min_legal_speed is None
    assert enemy.max_legal_speed is None
    assert enemy.gun_mounts == []
    assert enemy.torpedo_launchers == []
    assert enemy.torpedo_type is None


def test_secret_orders_and_hidden_damage_score_never_enter_opponent_observation() -> None:
    engine = IronBottomEngine()
    options = GameOptions(optional_rules=OptionalRules(hidden_damage=True))
    state = engine.reset("IBS-S-01", seed=1, options=options)
    assert engine.submit_orders(
        state.game_id, OrderBatch(side=Side.ALLIES, phase=Phase.GUNNERY)
    ).valid
    enemy_view = engine.observe(state.game_id, Side.AXIS)
    assert not any(event.type == "orders_submitted" for event in enemy_view.recent_events)
    assert all("order_batch" not in event.payload for event in enemy_view.recent_events)
    state.score[Side.AXIS.value] = 4
    state.score[Side.ALLIES.value] = 7
    assert engine.observe(state.game_id, Side.AXIS).score == {"axis": 0, "allies": 0}


def test_four_turns_reach_automatic_terminal_state() -> None:
    engine = IronBottomEngine()
    state = engine.reset("IBS-S-03", seed=3)
    while state.phase != Phase.COMPLETE:
        engine.step(state.game_id, {side: standing_orders(engine, state.game_id, side) for side in Side})
    assert state.turn == 4
    assert state.winner == Side.AXIS
    assert state.victory_reason and "德军战术胜利" in state.victory_reason


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


def test_main_map_heading_compass_and_scenario_3_heading_four_gold() -> None:
    origin = HexCoord.from_label("O14")
    assert {heading: origin.neighbor(heading).label for heading in range(1, 7)} == {
        1: "P13", 2: "P14", 3: "O15", 4: "N14", 5: "N13", 6: "O13"
    }
    engine = IronBottomEngine()
    state = engine.reset("IBS-S-03", seed=3)
    ship = state.ships["IBS-U-KM-KARL-GALSTER"]
    trajectory, heading = engine.movement_trajectory(ship, "1", ["advance"])
    assert ship.position.label == "O14"
    assert ship.heading == heading == 4
    assert trajectory == [(HexCoord.from_label("N14"), 4)]


def test_speed_is_a_legal_range_not_a_mandatory_maximum() -> None:
    engine = IronBottomEngine()
    state = engine.reset("IBS-S-03", seed=3)
    for side in Side:
        assert engine.submit_orders(state.game_id, OrderBatch(side=side, phase=Phase.REINFORCEMENT)).valid
    engine.advance(state.game_id)
    axis_orders = [
        MovementOrder(ship_id=ship.id, plan="0")
        for ship in state.ships.values() if ship.side == Side.AXIS and ship.position
    ]
    assert engine.validate_orders(
        state.game_id, OrderBatch(side=Side.AXIS, phase=Phase.MOVEMENT_PLANNING, movement=axis_orders)
    ).valid
    state.ships[axis_orders[0].ship_id].ship_type = "BB"
    rejected = engine.validate_orders(
        state.game_id, OrderBatch(side=Side.AXIS, phase=Phase.MOVEMENT_PLANNING, movement=axis_orders)
    )
    assert not rejected.valid
    assert any("outside legal range 2-6" in error for error in rejected.errors)


def test_tutorial_contact_preserving_example_keeps_a_british_ship_visible() -> None:
    engine = IronBottomEngine()
    state = engine.reset("IBS-S-03", seed=3, options=GameOptions(mode="tutorial"))
    for side in Side:
        assert engine.submit_orders(state.game_id, OrderBatch(side=side, phase=Phase.REINFORCEMENT)).valid
    engine.advance(state.game_id)
    for side in Side:
        ships = [ship for ship in state.ships.values() if ship.side == side and ship.position]
        movement = [
            MovementOrder(
                ship_id=ship.id,
                plan="1" if side == Side.AXIS and ship.id == "IBS-U-KM-KARL-GALSTER" else "0",
            )
            for ship in ships
        ]
        assert engine.submit_orders(
            state.game_id, OrderBatch(side=side, phase=Phase.MOVEMENT_PLANNING, movement=movement)
        ).valid
    engine.advance(state.game_id)
    for side in Side:
        assert engine.submit_orders(
            state.game_id, OrderBatch(side=side, phase=Phase.TORPEDO_PLANNING)
        ).valid
    engine.advance(state.game_id)
    engine.advance(state.game_id)
    view = engine.observe(state.game_id, Side.AXIS)
    assert view.phase == Phase.GUNNERY
    assert view.visibility == 4
    assert any(ship.side == Side.ALLIES for ship in view.ships)


def test_atlanta_rulebook_movement_example_costs_six_mf_for_3pp2() -> None:
    engine = IronBottomEngine()
    state = engine.reset("IBS-S-03", seed=3)
    ship = state.ships["IBS-U-KM-KARL-GALSTER"]
    commands = engine.movement_commands(MovementOrder(ship_id=ship.id, plan="3PP2"))
    trajectory, final_heading = engine.movement_trajectory(ship, "3PP2", commands)
    assert engine.movement_cost("3PP2", commands) == 6
    assert len(trajectory) == 6
    assert final_heading == ((ship.heading - 3) % 6) + 1


def test_leaving_map_shifts_every_other_counter_and_emits_rule_event() -> None:
    engine = IronBottomEngine()
    state = engine.reset("IBS-S-03", seed=3)
    mover = state.ships["IBS-U-KM-KARL-GALSTER"]
    other = state.ships["IBS-U-RN-JAVELIN"]
    mover.position = HexCoord.from_label("A10")
    mover.heading = 5
    other.position = HexCoord.from_label("R16")
    original_other = other.position
    state.torpedo_tracks.append(TorpedoTrack(
        id="edge-track",
        side=Side.AXIS,
        launcher_ship_id=mover.id,
        torpedo_type="G7a",
        position=HexCoord.from_label("S16"),
        heading=1,
        speed_cycle=(0, 0, 0),
        range_remaining=1,
        launched_turn=1,
    ))
    state.wrecks.append(WreckState(
        id="edge-wreck", position=HexCoord.from_label("T16"), source_ship_id="test"
    ))
    state.markers.append(MarkerState(
        id="edge-marker", kind="smoke", position=HexCoord.from_label("U16")
    ))
    originals = (
        state.torpedo_tracks[0].position,
        state.wrecks[0].position,
        state.markers[0].position,
    )
    state.sealed_orders["1:movement_planning"] = {
        Side.AXIS.value: OrderBatch(
            side=Side.AXIS,
            phase=Phase.MOVEMENT_PLANNING,
            movement=[MovementOrder(ship_id=mover.id, plan="1")],
        )
    }

    engine._resolve_movement(state)

    assert mover.position == HexCoord.from_label("A10")
    assert other.position == HexCoord(q=original_other.q + 1, r=original_other.r)
    assert state.torpedo_tracks[0].position == HexCoord(q=originals[0].q + 1, r=originals[0].r)
    assert state.wrecks[0].position == HexCoord(q=originals[1].q + 1, r=originals[1].r)
    assert state.markers[0].position == HexCoord(q=originals[2].q + 1, r=originals[2].r)
    event = next(event for event in state.events if event.type == "world_shifted")
    assert event.rule and event.rule.rule_id == "IBS-R-06.1.8"
    assert event.payload["movement_impulse"] == 1


def test_structured_land_blocks_ship_plan_and_torpedo_track() -> None:
    engine = IronBottomEngine()
    state = engine.reset("IBS-S-03", seed=3)
    ship = state.ships["IBS-U-KM-KARL-GALSTER"]
    ship.position = HexCoord.from_label("A1")
    ship.heading = 3
    state.land_hexes.add("A2")
    state.phase = Phase.MOVEMENT_PLANNING
    result = engine.validate_orders(
        state.game_id,
        OrderBatch(
            side=ship.side,
            phase=Phase.MOVEMENT_PLANNING,
            movement=[MovementOrder(ship_id=ship.id, plan="1")],
        ),
    )
    assert not result.valid
    assert any("enters land" in error for error in result.errors)

    state.torpedo_tracks.append(TorpedoTrack(
        id="land-track",
        side=ship.side,
        launcher_ship_id=ship.id,
        torpedo_type="test",
        position=HexCoord.from_label("A1"),
        heading=3,
        speed_cycle=(1, 1, 1),
        range_remaining=2,
        launched_turn=1,
    ))
    engine._resolve_movement(state)
    assert not state.torpedo_tracks
    event = next(event for event in state.events if event.type == "torpedo_grounded")
    assert event.payload["land_hex"] == "A2"


def test_structured_island_blocks_optical_line_and_radar_within_four_hexes() -> None:
    engine = IronBottomEngine()
    options = GameOptions(optional_rules=OptionalRules(radar=True))
    state = engine.reset("IBS-S-01", seed=1, options=options)
    attacker = state.ships["IBS-U-USN-HELENA"]
    target = state.ships["IBS-U-IJN-AOBA"]
    attacker.position = HexCoord.from_label("A1")
    target.position = HexCoord.from_label("A5")
    state.visibility[attacker.side.value] = 10
    state.land_hexes.add("A3")
    assert not engine._can_see(state, attacker, target)

    state.land_hexes.clear()
    state.visibility[attacker.side.value] = 0
    state.radar_blocking_hexes.add("B5")
    assert target.position.distance(HexCoord.from_label("B5")) <= 4
    assert not engine._can_see(state, attacker, target)
    state.radar_blocking_hexes.clear()
    assert engine._can_see(state, attacker, target)


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


def test_scenario_one_reinforcement_roll_is_once_and_audited() -> None:
    engine = IronBottomEngine()
    state = engine.reset("IBS-S-01", seed=3)
    state.turn = 3
    state.phase = Phase.REINFORCEMENT
    for side in Side:
        assert engine.submit_orders(
            state.game_id, OrderBatch(side=side, phase=Phase.REINFORCEMENT)
        ).valid
    engine.advance(state.game_id)
    rolls = [event for event in state.events if event.type == "reinforcement_roll"]
    assert len(rolls) == 1
    assert rolls[0].dice and rolls[0].dice.notation == "1D6"
    assert rolls[0].rule and rolls[0].rule.rule_id == "IBS-S-01-R5"
    assert state.reinforcement_roll_done
    assert state.reinforcement_available


def test_scenario_one_reinforcement_rejects_off_boundary_entry() -> None:
    engine = IronBottomEngine()
    state = engine.reset("IBS-S-01", seed=3)
    state.turn = 4
    state.phase = Phase.REINFORCEMENT
    state.reinforcement_available = True
    result = engine.validate_orders(
        state.game_id,
        OrderBatch(
            side=Side.AXIS,
            phase=Phase.REINFORCEMENT,
            reinforcements=[{
                "ship_id": "IBS-U-IJN-CHITOSE",
                "entry_hex": HexCoord.from_label("A1"),
                "heading": 1,
                "speed": 1,
            }],
        ),
    )
    assert not result.valid
    assert any("Illegal reinforcement entry hex" in error for error in result.errors)


def test_gunnery_executes_individual_mount_orders_for_both_sides() -> None:
    engine = IronBottomEngine()
    state = engine.reset("IBS-S-03", seed=5)
    state.phase = Phase.GUNNERY
    axis_ship = state.ships["IBS-U-KM-KARL-GALSTER"]
    allied_ship = state.ships["IBS-U-RN-JAVELIN"]
    orders = {
        Side.AXIS: OrderBatch(
            side=Side.AXIS,
            phase=Phase.GUNNERY,
            gunnery=[GunneryOrder(
                ship_id=axis_ship.id,
                mounts=[GunMountOrder(mount_id="P1", target_id=allied_ship.id)],
            )],
        ),
        Side.ALLIES: OrderBatch(
            side=Side.ALLIES,
            phase=Phase.GUNNERY,
            gunnery=[GunneryOrder(
                ship_id=allied_ship.id,
                mounts=[GunMountOrder(mount_id="P1", target_id=axis_ship.id)],
            )],
        ),
    }
    for batch in orders.values():
        assert engine.submit_orders(state.game_id, batch).valid
    engine.advance(state.game_id)
    attacks = [event for event in state.events if event.type == "gun_mount_attack"]
    assert len(attacks) == 2
    assert {event.payload["mount_id"] for event in attacks} == {"P1"}


def test_legal_actions_publish_only_engine_valid_weapon_candidates() -> None:
    engine = IronBottomEngine()
    state = engine.reset("IBS-S-03", seed=51)
    state.phase = Phase.GUNNERY
    hint = engine.legal_actions(state.game_id, Side.AXIS)[0].schema_hint
    candidates = hint["gunnery_candidates"]
    assert len(candidates) == 3
    assert any(candidate["targets"] for candidate in candidates)
    for candidate in candidates:
        attacker = state.ships[candidate["ship_id"]]
        for target_hint in candidate["targets"]:
            target = state.ships[target_hint["target_id"]]
            assert engine._can_see(state, attacker, target)
            for mount_id in target_hint["mount_ids"]:
                mount = next(item for item in attacker.gun_mounts if item.id == mount_id)
                assert engine._mount_can_bear(attacker, target, mount.arcs)

    state.phase = Phase.TORPEDO_PLANNING
    axis_ships = [ship for ship in state.ships.values() if ship.side == Side.AXIS and ship.position]
    state.sealed_orders["1:movement_planning"] = {
        Side.AXIS.value: OrderBatch(
            side=Side.AXIS,
            phase=Phase.MOVEMENT_PLANNING,
            movement=[MovementOrder(ship_id=ship.id, plan="1") for ship in axis_ships],
        )
    }
    torpedo_hint = engine.legal_actions(state.game_id, Side.AXIS)[0].schema_hint
    torpedo_candidates = torpedo_hint["torpedo_candidates"]
    assert len(torpedo_candidates) == 3
    assert all(candidate["launchers"] for candidate in torpedo_candidates)
    assert all(
        launcher["angles"] == ["A", "B", "X", "Y"]
        for candidate in torpedo_candidates for launcher in candidate["launchers"]
    )
    assert all(candidate["launch_positions"][0]["mf"] == 0 for candidate in torpedo_candidates)
    assert all(candidate["launch_positions"][1]["mf"] == 1 for candidate in torpedo_candidates)
    assert all(candidate["settings"] for candidate in torpedo_candidates)


def test_gunnery_rejects_destroyed_mount_and_scenario_one_axis_turn_one_fire() -> None:
    engine = IronBottomEngine()
    state = engine.reset("IBS-S-01", seed=5)
    attacker = state.ships["IBS-U-IJN-AOBA"]
    target = state.ships["IBS-U-USN-HELENA"]
    attacker.gun_mounts[0].destroyed = True
    result = engine.validate_orders(
        state.game_id,
        OrderBatch(
            side=Side.AXIS,
            phase=Phase.GUNNERY,
            gunnery=[GunneryOrder(
                ship_id=attacker.id,
                mounts=[GunMountOrder(mount_id=attacker.gun_mounts[0].id, target_id=target.id)],
            )],
        ),
    )
    assert not result.valid
    assert any("may not fire" in error for error in result.errors)
    assert any("unavailable gun mount" in error for error in result.errors)


def test_scenario_one_allied_mount_firepower_is_halved_rounding_up() -> None:
    engine = IronBottomEngine()
    state = engine.reset("IBS-S-01", seed=5)
    attacker = state.ships["IBS-U-USN-HELENA"]
    target = state.ships["IBS-U-IJN-AOBA"]
    mount = next(mount for mount in attacker.gun_mounts if engine._mount_can_bear(attacker, target, mount.arcs))
    allied = OrderBatch(
        side=Side.ALLIES,
        phase=Phase.GUNNERY,
        gunnery=[GunneryOrder(
            ship_id=attacker.id,
            mounts=[GunMountOrder(mount_id=mount.id, target_id=target.id)],
        )],
    )
    assert engine.submit_orders(state.game_id, allied).valid
    assert engine.submit_orders(
        state.game_id, OrderBatch(side=Side.AXIS, phase=Phase.GUNNERY)
    ).valid
    engine.advance(state.game_id)
    event = next(event for event in state.events if event.type == "gun_mount_attack")
    assert event.payload["firepower"] == (mount.firepower + 1) // 2


def test_aoba_helena_rulebook_gunnery_example_aggregates_main_battery() -> None:
    engine = IronBottomEngine()
    state = engine.reset("IBS-S-01", seed=5)
    state.turn = 2
    state.phase = Phase.GUNNERY
    aoba = state.ships["IBS-U-IJN-AOBA"]
    helena = state.ships["IBS-U-USN-HELENA"]
    aoba.position = HexCoord.from_label("A1")
    aoba.heading = 1
    helena.position = HexCoord.from_label("J5")
    helena.heading = 6
    helena.current_speed = 4
    primary = [mount for mount in aoba.gun_mounts if mount.kind == "primary"]
    assert sum(mount.firepower for mount in primary) == 16
    assert all(engine._mount_can_bear(aoba, helena, mount.arcs) for mount in primary)
    rolls = iter([(26, [2, 6]), (66, [6, 6]), (66, [6, 6])])
    engine._roll_d66 = lambda _: next(rolls)  # type: ignore[method-assign]
    axis = OrderBatch(
        side=Side.AXIS,
        phase=Phase.GUNNERY,
        gunnery=[GunneryOrder(
            ship_id=aoba.id,
            mounts=[GunMountOrder(mount_id=mount.id, target_id=helena.id) for mount in primary],
        )],
    )
    assert engine.submit_orders(state.game_id, axis).valid
    assert engine.submit_orders(
        state.game_id, OrderBatch(side=Side.ALLIES, phase=Phase.GUNNERY)
    ).valid
    engine.advance(state.game_id)
    attack = next(event for event in state.events if event.type == "gun_mount_attack")
    assert attack.payload["mount_ids"] == ["P1", "P2", "P3"]
    assert attack.payload["firepower"] == 16
    assert attack.payload["modifier"] == -6
    assert attack.dice and attack.dice.raw == 26 and attack.dice.adjusted == 16
    assert attack.payload["hits"] == 2


def test_torpedo_launches_at_planned_mf_moves_by_impulse_and_contacts_ship() -> None:
    engine = IronBottomEngine()
    state = engine.reset("IBS-S-03", seed=9)
    attacker = state.ships["IBS-U-KM-KARL-GALSTER"]
    attacker.heading = 3
    target = state.ships["IBS-U-RN-JAVELIN"]
    target.position = HexCoord.from_label("N15")
    for side in Side:
        assert engine.submit_orders(
            state.game_id, OrderBatch(side=side, phase=Phase.REINFORCEMENT)
        ).valid
    engine.advance(state.game_id)
    for side in Side:
        own = [ship for ship in state.ships.values() if ship.side == side and ship.position]
        movement = [
            MovementOrder(ship_id=ship.id, plan="3" if ship.id == attacker.id else "0")
            for ship in own
        ]
        assert engine.submit_orders(
            state.game_id,
            OrderBatch(side=side, phase=Phase.MOVEMENT_PLANNING, movement=movement),
        ).valid
    engine.advance(state.game_id)
    launch_hex = attacker.position.neighbor(attacker.heading)
    axis_torpedo = TorpedoOrder(
        ship_id=attacker.id,
        launcher_id="TT1",
        count=1,
        launch_at_mf=1,
        launch_hex=launch_hex,
        launch_side="starboard",
        launch_angle="X",
        setting_index=0,
    )
    assert engine.submit_orders(
        state.game_id,
        OrderBatch(side=Side.AXIS, phase=Phase.TORPEDO_PLANNING, torpedoes=[axis_torpedo]),
    ).valid
    assert engine.submit_orders(
        state.game_id, OrderBatch(side=Side.ALLIES, phase=Phase.TORPEDO_PLANNING)
    ).valid
    engine.advance(state.game_id)
    engine.advance(state.game_id)
    assert len(state.torpedo_tracks) == 1
    track = state.torpedo_tracks[0]
    assert track.position == target.position
    assert track.contact_ship_ids == [target.id]
    assert track.distance_travelled == 1
    assert track.salvo_size == 1
    assert next(item for item in attacker.torpedo_launchers if item.id == "TT1").loaded == 1
    for side in Side:
        assert engine.submit_orders(
            state.game_id, OrderBatch(side=side, phase=Phase.GUNNERY)
        ).valid
    engine.advance(state.game_id)
    engine.advance(state.game_id)
    assert not state.torpedo_tracks
    assert any(event.type == "torpedo_attack" for event in state.events)


def test_stationary_ship_launches_from_its_current_hex_at_mf_zero() -> None:
    engine = IronBottomEngine()
    state = engine.reset("IBS-S-03", seed=90)
    attacker = state.ships["IBS-U-RN-JAVELIN"]
    for side in Side:
        assert engine.submit_orders(
            state.game_id, OrderBatch(side=side, phase=Phase.REINFORCEMENT)
        ).valid
    engine.advance(state.game_id)
    for side in Side:
        movement = [
            MovementOrder(ship_id=ship.id, plan="0")
            for ship in state.ships.values() if ship.side == side and ship.position
        ]
        assert engine.submit_orders(
            state.game_id,
            OrderBatch(side=side, phase=Phase.MOVEMENT_PLANNING, movement=movement),
        ).valid
    engine.advance(state.game_id)
    hints = engine.legal_actions(state.game_id, Side.ALLIES)[0].schema_hint["torpedo_candidates"]
    javelin_hint = next(item for item in hints if item["ship_id"] == attacker.id)
    assert [launcher["loaded"] for launcher in javelin_hint["launchers"]] == [2, 2]
    assert javelin_hint["launch_positions"] == [{
        "mf": 0,
        "hex": attacker.position.model_dump(mode="json"),
        "heading": attacker.heading,
    }]
    wrong_hex = attacker.position.neighbor(attacker.heading)
    invalid = TorpedoOrder(
        ship_id=attacker.id,
        launcher_id="TT1",
        launch_at_mf=0,
        launch_hex=wrong_hex,
        launch_side="port",
        launch_angle="X",
    )
    result = engine.validate_orders(
        state.game_id,
        OrderBatch(side=Side.ALLIES, phase=Phase.TORPEDO_PLANNING, torpedoes=[invalid]),
    )
    assert not result.valid
    assert any("launch_hex does not match" in error for error in result.errors)
    order = invalid.model_copy(update={"launch_hex": attacker.position, "count": 2})
    assert engine.submit_orders(
        state.game_id,
        OrderBatch(side=Side.ALLIES, phase=Phase.TORPEDO_PLANNING, torpedoes=[order]),
    ).valid
    assert engine.submit_orders(
        state.game_id, OrderBatch(side=Side.AXIS, phase=Phase.TORPEDO_PLANNING)
    ).valid
    engine.advance(state.game_id)
    engine.advance(state.game_id)
    launch = next(event for event in state.events if event.type == "torpedo_launched")
    assert launch.payload["launch_mf"] == 0
    track = state.torpedo_tracks[0]
    assert track.distance_travelled == track.speed_cycle[0]
    assert track.salvo_size == 2
    assert next(item for item in attacker.torpedo_launchers if item.id == "TT1").loaded == 0


def test_aoba_helena_rulebook_torpedo_example_scores_one_hit_and_5h_7mf() -> None:
    engine = IronBottomEngine()
    state = engine.reset("IBS-S-01", seed=9)
    aoba = state.ships["IBS-U-IJN-AOBA"]
    helena = state.ships["IBS-U-USN-HELENA"]
    assert aoba.torpedo_type == "jp-24-type93"
    helena.current_speed = 5
    helena.previous_speed = 5
    helena.heading = 1
    before_hull = helena.hull
    state.torpedo_tracks.append(TorpedoTrack(
        id="AOBA-HELENA-GOLD",
        side=aoba.side,
        launcher_ship_id=aoba.id,
        torpedo_type=aoba.torpedo_type,
        position=helena.position,
        heading=2,
        speed_cycle=(8, 8, 8),
        range_remaining=32,
        distance_travelled=4,
        launched_turn=1,
        salvo_size=1,
        contact_ship_ids=[helena.id],
    ))
    rolls = iter([(8, [4, 4]), (7, [3, 4])])
    engine._roll_2d6 = lambda _: next(rolls)  # type: ignore[method-assign]
    engine._resolve_torpedoes(state)
    attack = next(event for event in state.events if event.type == "torpedo_attack")
    result = next(event for event in state.events if event.type == "torpedo_result")
    assert attack.dice and attack.dice.raw == 8 and attack.dice.adjusted == 11
    assert attack.payload["hits"] == 1
    assert result.dice and result.dice.raw == 7 and result.dice.adjusted == 8
    assert result.payload["effect"] == "5H/-7MF"
    assert helena.hull == before_hull - 5
    assert helena.speed_track == (3, 3, 3)


def test_torpedo_plan_accepts_port_x_but_rejects_wrong_launch_hex() -> None:
    engine = IronBottomEngine()
    state = engine.reset("IBS-S-03", seed=9)
    for side in Side:
        assert engine.submit_orders(
            state.game_id, OrderBatch(side=side, phase=Phase.REINFORCEMENT)
        ).valid
    engine.advance(state.game_id)
    for side in Side:
        own = [ship for ship in state.ships.values() if ship.side == side and ship.position]
        movement = [MovementOrder(ship_id=ship.id, plan="1") for ship in own]
        assert engine.submit_orders(
            state.game_id,
            OrderBatch(side=side, phase=Phase.MOVEMENT_PLANNING, movement=movement),
        ).valid
    engine.advance(state.game_id)
    result = engine.validate_orders(
        state.game_id,
        OrderBatch(
            side=Side.AXIS,
            phase=Phase.TORPEDO_PLANNING,
            torpedoes=[TorpedoOrder(
                ship_id="IBS-U-KM-KARL-GALSTER",
                launcher_id="TT1",
                launch_at_mf=1,
                launch_hex=HexCoord.from_label("A1"),
                launch_side="port",
                launch_angle="X",
            )],
        ),
    )
    assert not result.valid
    assert not any("angle" in error.lower() for error in result.errors)
    assert any("launch_hex does not match" in error for error in result.errors)


def test_torpedo_port_and_starboard_each_offer_abxy_directions() -> None:
    engine = IronBottomEngine()
    expected = {
        ("port", "A"): 5,
        ("port", "B"): 6,
        ("port", "X"): 1,
        ("port", "Y"): 2,
        ("starboard", "A"): 5,
        ("starboard", "B"): 4,
        ("starboard", "X"): 3,
        ("starboard", "Y"): 2,
    }
    assert {
        (side, angle): engine._torpedo_launch_heading(2, side, angle)
        for side in ("port", "starboard") for angle in ("A", "B", "X", "Y")
    } == expected
    # Rulebook p.12 Aoba example: heading 2, port-X follows heading 1.
    assert engine._torpedo_launch_heading(2, "port", "X") == 1


def test_helena_seven_mf_loss_reproduces_rulebook_three_three_three_example() -> None:
    engine = IronBottomEngine()
    state = engine.reset("IBS-S-01", seed=1)
    helena = state.ships["IBS-U-USN-HELENA"]
    assert helena.speed_track == (6, 5, 5)
    engine._lose_speed(helena, 7)
    assert helena.speed_track == (3, 3, 3)
    assert helena.speed_damage_crossed == (3, 2, 2)


def test_collision_requires_five_or_six_then_uses_collision_table_for_both_ships() -> None:
    engine = IronBottomEngine()
    state = engine.reset("IBS-S-03", seed=1)
    left = state.ships["IBS-U-KM-KARL-GALSTER"]
    right = state.ships["IBS-U-RN-JAVELIN"]
    assert engine._resolve_ship_collision(state, left, right)
    check = next(event for event in state.events if event.type == "collision_check")
    results = [event for event in state.events if event.type == "collision_result"]
    assert check.dice and check.dice.raw == 5
    assert len(results) == 2
    assert all(event.rule and event.rule.rule_id == "IBS-T-THDT" for event in results)


def test_moving_sunk_ship_drifts_one_hex_at_next_movement_then_creates_wreck() -> None:
    engine = IronBottomEngine()
    state = engine.reset("IBS-S-03", seed=1)
    ship = state.ships["IBS-U-KM-KARL-GALSTER"]
    assert ship.position
    expected_position = ship.position.neighbor(ship.heading)
    engine._damage_hull(state, ship, ship.hull, "test")
    assert ship.sunk
    assert ship.sinking_drift_pending
    assert len(state.wrecks) == 0
    state.turn += 1
    engine._resolve_sinking_drift(state)
    assert len(state.wrecks) == 1
    assert state.wrecks[0].position == expected_position
    assert state.wrecks[0].source_ship_id == ship.id
    assert ship.position is None
    assert any(event.type == "sinking_marker_placed" for event in state.events)


def test_zero_speed_ship_sinks_in_place_without_drift() -> None:
    engine = IronBottomEngine()
    state = engine.reset("IBS-S-03", seed=1)
    ship = state.ships["IBS-U-KM-KARL-GALSTER"]
    original_position = ship.position
    ship.previous_speed = 0
    engine._damage_hull(state, ship, ship.hull, "test")
    assert not ship.sinking_drift_pending
    assert ship.position is None
    assert state.wrecks[0].position == original_position


def test_scenario_three_one_slowed_german_ship_is_allied_tactical_victory() -> None:
    engine = IronBottomEngine()
    state = engine.reset("IBS-S-03", seed=1)
    ship = state.ships["IBS-U-KM-KARL-GALSTER"]
    ship.speed_track = (2, 2, 2)
    state.turn = 4
    state.phase = Phase.FIRE_END
    engine.advance(state.game_id)
    assert state.winner == Side.ALLIES
    assert state.victory_reason and "英军战术胜利" in state.victory_reason


def test_scenario_one_requires_four_point_margin_from_hull_damage_only() -> None:
    engine = IronBottomEngine()
    state = engine.reset("IBS-S-01", seed=1)
    helena = state.ships["IBS-U-USN-HELENA"]
    engine._damage_hull(state, helena, 12, "test")
    assert state.score[Side.AXIS.value] == 4
    state.turn = 7
    state.phase = Phase.FIRE_END
    engine.advance(state.game_id)
    assert state.winner == Side.AXIS
    assert state.victory_reason and "领先 4 分" in state.victory_reason


def test_optional_star_shell_creates_next_turn_illumination_marker() -> None:
    engine = IronBottomEngine()
    options = GameOptions(optional_rules=OptionalRules(star_shells=True))
    state = engine.reset("IBS-S-03", seed=1, options=options)
    ship = state.ships["IBS-U-KM-KARL-GALSTER"]
    mount = ship.gun_mounts[0]
    batch = OrderBatch(
        side=ship.side,
        phase=Phase.GUNNERY,
        illumination=[IlluminationOrder(ship_id=ship.id, mount_id=mount.id, target_hex=HexCoord.from_label("R16"))],
    )
    engine._resolve_optional_gunnery(state, [batch])
    assert mount.fired_this_phase
    assert any(marker.kind == "star_shell" and marker.expires_turn == 2 for marker in state.markers)
    assert any(event.type == "star_shell_fired" and event.rule and event.rule.rule_id == "IBS-R-09.3" for event in state.events)


def test_optional_radar_extends_detection_only_for_radar_equipped_attacker() -> None:
    engine = IronBottomEngine()
    options = GameOptions(optional_rules=OptionalRules(radar=True))
    state = engine.reset("IBS-S-01", seed=1, options=options)
    helena = state.ships["IBS-U-USN-HELENA"]
    aoba = state.ships["IBS-U-IJN-AOBA"]
    helena.position = HexCoord.from_label("A1")
    aoba.position = HexCoord.from_label("HH27")
    assert helena.radar
    assert engine._can_see(state, helena, aoba)
    helena.radar_destroyed = True
    assert not engine._can_see(state, helena, aoba)


def test_optional_squall_blocks_fire_and_moves_with_audited_die() -> None:
    engine = IronBottomEngine()
    options = GameOptions(optional_rules=OptionalRules(squalls=True))
    state = engine.reset("IBS-S-03", seed=1, options=options)
    attacker = state.ships["IBS-U-KM-KARL-GALSTER"]
    target = state.ships["IBS-U-RN-JAVELIN"]
    state.markers.append(MarkerState(id="SQ-1", kind="squall", position=attacker.position))
    assert not engine._can_see(state, attacker, target)
    original = state.markers[0].position
    engine._move_squalls(state)
    assert state.markers[0].position != original
    event = next(event for event in state.events if event.type == "squall_moved")
    assert event.rule and event.rule.rule_id == "IBS-R-09.6"


def test_blind_torpedo_is_visible_only_to_owner_until_contact() -> None:
    engine = IronBottomEngine()
    options = GameOptions(optional_rules=OptionalRules(blind_torpedoes=True))
    state = engine.reset("IBS-S-03", seed=1, options=options)
    ship = state.ships["IBS-U-KM-KARL-GALSTER"]
    state.torpedo_tracks.append(TorpedoTrack(
        id="SECRET-TT",
        side=Side.AXIS,
        launcher_ship_id=ship.id,
        torpedo_type=ship.torpedo_type or "de-nl-21",
        position=ship.position,
        heading=1,
        speed_cycle=(8, 8, 2),
        range_remaining=10,
        launched_turn=1,
        hidden=True,
    ))
    assert [track.id for track in engine.observe(state.game_id, Side.AXIS).torpedo_tracks] == ["SECRET-TT"]
    assert not engine.observe(state.game_id, Side.ALLIES).torpedo_tracks


def test_optional_smoke_releases_marker_and_applies_exact_plus_six_modifier() -> None:
    engine = IronBottomEngine()
    options = GameOptions(optional_rules=OptionalRules(smoke=True))
    state = engine.reset("IBS-S-03", seed=1, options=options)
    attacker = state.ships["IBS-U-KM-KARL-GALSTER"]
    target = state.ships["IBS-U-RN-JAVELIN"]
    distance = attacker.position.distance(target.position)  # type: ignore[union-attr]
    baseline = engine._gunnery_modifier(state, attacker, target, distance, 1)
    batch = OrderBatch(
        side=attacker.side,
        phase=Phase.GUNNERY,
        smoke=[SmokeOrder(ship_id=attacker.id)],
    )
    engine._resolve_optional_gunnery(state, [batch])
    assert attacker.smoke
    assert engine._gunnery_modifier(state, attacker, target, distance, 1) == baseline + 6
    assert any(marker.kind == "smoke" for marker in state.markers)


def test_optional_commands_are_rejected_when_their_rule_is_disabled() -> None:
    engine = IronBottomEngine()
    state = engine.reset("IBS-S-03", seed=1)
    state.phase = Phase.GUNNERY
    result = engine.validate_orders(
        state.game_id,
        OrderBatch(
            side=Side.AXIS,
            phase=Phase.GUNNERY,
            smoke=[SmokeOrder(ship_id="IBS-U-KM-KARL-GALSTER")],
        ),
    )
    assert not result.valid
    assert any("optional rule 9.7" in error for error in result.errors)


def test_optional_searchlight_applies_both_exact_minus_three_modifiers() -> None:
    engine = IronBottomEngine()
    options = GameOptions(optional_rules=OptionalRules(searchlights=True))
    state = engine.reset("IBS-S-03", seed=1, options=options)
    attacker = state.ships["IBS-U-KM-KARL-GALSTER"]
    target = state.ships["IBS-U-RN-JAVELIN"]
    state.markers.append(MarkerState(
        id="SEARCH-test", kind="searchlight", ship_id=attacker.id, target_ship_id=target.id
    ))
    values = engine._gunnery_modifiers(
        state,
        attacker,
        target,
        attacker.position.distance(target.position),  # type: ignore[union-attr]
        attackers=1,
        caliber=5,
        target_count=1,
    )
    assert values["target_searchlit"] == -3
    assert values["searchlight_user"] == -3


def test_optional_silhouette_reveals_only_intervening_ship_during_current_fire() -> None:
    engine = IronBottomEngine()
    options = GameOptions(optional_rules=OptionalRules(silhouettes=True))
    state = engine.reset("IBS-S-03", seed=1, options=options)
    attacker = state.ships["IBS-U-KM-KARL-GALSTER"]
    candidate = state.ships["IBS-U-RN-JAVELIN"]
    target = state.ships["IBS-U-RN-KASHMIR"]
    attacker.position = HexCoord.from_label("A1")
    candidate.position = HexCoord.from_label("A3")
    target.position = HexCoord.from_label("A5")
    state.visibility[Side.AXIS.value] = 0
    state.sealed_orders["1:gunnery"] = {
        Side.AXIS.value: OrderBatch(
            side=Side.AXIS,
            phase=Phase.GUNNERY,
            gunnery=[GunneryOrder(ship_id=attacker.id, primary_target=target.id)],
        )
    }
    assert engine._can_see(state, attacker, candidate)
    state.options.optional_rules.silhouettes = False
    assert not engine._can_see(state, attacker, candidate)


def test_fire_table_applies_no_fire_plus_one_and_ignores_adjusted_seven() -> None:
    engine = IronBottomEngine()
    state = engine.reset("IBS-S-03", seed=1)
    ship = state.ships["IBS-U-KM-KARL-GALSTER"]
    ship.fire_markers = 1
    ship.fired = False
    before = ship.hull
    engine._roll_2d6 = lambda _: (6, [3, 3])  # type: ignore[method-assign]
    engine._resolve_fire(state)
    assert ship.hull == before
    event = next(event for event in state.events if event.type == "fire_check")
    assert event.dice and event.dice.raw == 6 and event.dice.adjusted == 7
    assert event.payload["ignored_for_no_fire"] is True


def test_optional_malfunction_power_failure_disables_all_guns_temporarily() -> None:
    engine = IronBottomEngine()
    state = engine.reset("IBS-S-03", seed=1)
    ship = state.ships["IBS-U-KM-KARL-GALSTER"]
    engine._roll_2d6 = lambda _: (2, [1, 1])  # type: ignore[method-assign]
    engine._resolve_malfunction(state, ship)
    assert ship.guns_disabled_turns == 2
    assert not ship.mfc_destroyed
    event = next(event for event in state.events if event.type == "malfunction")
    assert event.rule and event.rule.rule_id == "IBS-R-09.5"
    assert event.payload["result"] == {"power_failure_turns": 2}


def test_every_fire_table_result_executes_for_fired_and_non_firing_ships() -> None:
    for fired in (False, True):
        for raw in range(2, 13):
            engine = IronBottomEngine()
            state = engine.reset("IBS-S-03", seed=raw)
            ship = state.ships["IBS-U-KM-KARL-GALSTER"]
            ship.fire_markers = 1
            ship.fired = fired
            engine._roll_2d6 = lambda _, value=raw: (  # type: ignore[method-assign]
                value, [max(1, value - 6), min(6, value - 1)]
            )
            engine._roll_d66 = lambda _: (66, [6, 6])  # type: ignore[method-assign]
            engine._resolve_fire(state)
            event = next(event for event in state.events if event.type == "fire_check")
            expected = min(12, raw + (0 if fired else 1))
            assert event.dice and event.dice.raw == raw and event.dice.adjusted == expected


def test_every_malfunction_table_result_executes_with_audited_effect() -> None:
    for raw in range(2, 13):
        engine = IronBottomEngine()
        state = engine.reset("IBS-S-01", seed=raw)
        ship = state.ships["IBS-U-IJN-AOBA"]
        engine._roll_2d6 = lambda _, value=raw: (  # type: ignore[method-assign]
            value, [max(1, value - 6), min(6, value - 1)]
        )
        engine._roll_d66 = lambda _: (66, [6, 6])  # type: ignore[method-assign]
        engine._resolve_malfunction(state, ship)
        event = next(event for event in state.events if event.type == "malfunction")
        assert event.dice and event.dice.raw == raw
        assert event.payload["result"] == engine.rules.table_2d6(
            engine.rules.malfunction_results, raw
        )


def test_hidden_contacts_setup_seals_two_real_formations_and_two_decoys_per_side() -> None:
    engine = IronBottomEngine()
    options = GameOptions(optional_rules=OptionalRules(hidden_contacts=True))
    state = engine.reset("IBS-S-03", seed=1, options=options)
    assert state.phase == Phase.CONTACT_SETUP
    assert not [ship for ship in state.ships.values() if ship.position]

    edge_coords = []
    for q in range(34):
        for display_row in (0, 26):
            edge_coords.append(HexCoord(q=q, r=display_row - (q - (q & 1)) // 2))
    for display_row in range(1, 26):
        edge_coords.append(HexCoord(q=0, r=display_row))
        edge_coords.append(HexCoord(q=33, r=display_row - 16))
    used: set[str] = set()

    def entry_for(group: list[str]) -> HexCoord:
        anchor = state.contact_reserve_positions[group[0]]
        for candidate in edge_coords:
            if candidate.label in used:
                continue
            if all(
                engine._coord_on_map(
                    candidate.q + state.contact_reserve_positions[ship_id].q - anchor.q,
                    candidate.r + state.contact_reserve_positions[ship_id].r - anchor.r,
                )
                for ship_id in group
            ):
                used.add(candidate.label)
                return candidate
        raise AssertionError("No legal contact entry")

    def inward_heading(coord: HexCoord) -> int:
        display_row = coord.r + (coord.q - (coord.q & 1)) // 2
        if coord.q == 0:
            return 2
        if coord.q == 33:
            return 5
        return 3 if display_row == 0 else 6

    for side in Side:
        ships = [ship_id for ship_id in state.contact_reserve_positions if state.ships[ship_id].side == side]
        split = max(1, len(ships) // 2)
        groups = [ships[:split], ships[split:]]
        orders = [
            ContactSetupOrder(
                marker_id=f"CONTACT-{side.value}-{index + 1}",
                entry_hex=(entry := entry_for(group)),
                heading=inward_heading(entry),
                speed=4,
                ship_ids=group,
            )
            for index, group in enumerate(groups)
        ]
        for index in (3, 4):
            entry = next(coord for coord in edge_coords if coord.label not in used)
            used.add(entry.label)
            orders.append(ContactSetupOrder(
                marker_id=f"CONTACT-{side.value}-{index}",
                entry_hex=entry,
                heading=inward_heading(entry),
                speed=5,
            ))
        assert engine.submit_orders(
            state.game_id, OrderBatch(side=side, phase=Phase.CONTACT_SETUP, contacts=orders)
        ).valid
    engine.advance(state.game_id)
    assert state.phase == Phase.REINFORCEMENT
    allied_view = engine.observe(state.game_id, Side.ALLIES)
    enemy_contacts = [marker for marker in allied_view.markers if marker.secret_side == Side.AXIS]
    assert enemy_contacts and all(marker.contact_truth is None for marker in enemy_contacts)

    axis_real = next(marker for marker in state.markers if marker.id == "CONTACT-axis-1")
    allied_real = next(marker for marker in state.markers if marker.id == "CONTACT-allies-1")
    axis_real.position = HexCoord.from_label("O14")
    allied_real.position = HexCoord.from_label("P14")
    engine._reveal_detected_contacts(state)
    assert axis_real not in state.markers
    assert allied_real not in state.markers
    assert all(state.ships[ship_id].position for ship_id in state.contact_formations[axis_real.id])
    assert all(state.ships[ship_id].position for ship_id in state.contact_formations[allied_real.id])

    for side in Side:
        assert engine.submit_orders(
            state.game_id, OrderBatch(side=side, phase=Phase.REINFORCEMENT)
        ).valid
    engine.advance(state.game_id)
    for side in Side:
        active_ships = [ship for ship in state.ships.values() if ship.side == side and ship.position]
        contacts = [
            marker for marker in state.markers
            if marker.kind == "contact" and marker.secret_side == side and marker.position
        ]
        batch = OrderBatch(
            side=side,
            phase=Phase.MOVEMENT_PLANNING,
            movement=[MovementOrder(ship_id=ship.id, plan="0") for ship in active_ships],
            contact_movement=[ContactMovementOrder(marker_id=marker.id, plan="4") for marker in contacts],
        )
        assert engine.submit_orders(state.game_id, batch).valid
    engine.advance(state.game_id)
    for side in Side:
        assert engine.submit_orders(
            state.game_id, OrderBatch(side=side, phase=Phase.TORPEDO_PLANNING)
        ).valid
    engine.advance(state.game_id)
    engine.advance(state.game_id)
    assert any(event.type == "contact_moved" for event in state.events)


def test_gunnery_modifier_breakdown_applies_longitudinal_additional_ship_and_multiple_targets() -> None:
    engine = IronBottomEngine()
    state = engine.reset("IBS-S-03", seed=1)
    attacker = state.ships["IBS-U-KM-KARL-GALSTER"]
    target = state.ships["IBS-U-RN-JAVELIN"]
    attacker.position = HexCoord.from_label("O10")
    target.position = HexCoord.from_label("O14")
    target.heading = 6
    target.current_speed = 5
    values = engine._gunnery_modifiers(
        state, attacker, target, distance=4, attackers=3, caliber=5, target_count=2
    )
    assert values["range"] == -12
    assert values["longitudinal"] == -8
    assert values["additional_attackers"] == 2
    assert values["multiple_targets"] == 6
    assert values["caliber_target"] == 0


def test_small_caliber_against_battleship_uses_exact_target_class_modifier() -> None:
    engine = IronBottomEngine()
    assert engine._caliber_target_modifier(5, "BB") == 18
    assert engine._caliber_target_modifier(8, "CA") == 0


def test_positional_gun_hit_destroys_only_matching_operational_mount() -> None:
    engine = IronBottomEngine()
    state = engine.reset("IBS-S-01", seed=1)
    attacker = state.ships["IBS-U-IJN-AOBA"]
    target = state.ships["IBS-U-USN-HELENA"]
    bow_mounts = [mount for mount in target.gun_mounts if mount.kind == "primary" and mount.position.value == "bow"]
    engine._apply_gunnery_result(state, attacker, target, 13, "primary_bow", 9, caliber=8)
    assert sum(mount.destroyed for mount in bow_mounts) == 1
    assert not any(
        mount.destroyed for mount in target.gun_mounts
        if mount.kind == "primary" and mount.position.value != "bow"
    )
    for mount in bow_mounts:
        mount.destroyed = True
    before = sum(mount.destroyed for mount in target.gun_mounts)
    engine._apply_gunnery_result(state, attacker, target, 13, "primary_bow", 9, caliber=8)
    assert sum(mount.destroyed for mount in target.gun_mounts) == before


def test_special_damage_torpedo_launcher_hit_updates_launcher_and_aggregate_ammo() -> None:
    engine = IronBottomEngine()
    state = engine.reset("IBS-S-01", seed=1)
    ship = state.ships["IBS-U-IJN-AOBA"]
    initial_ammo = ship.torpedo.ammo if ship.torpedo else 0
    destroyed = engine._destroy_torpedo_launchers(state, ship, 1, "test")
    assert len(destroyed) == 1
    assert ship.torpedo and ship.torpedo.ammo == initial_ammo - 2
    assert ship.torpedo.ammo == sum(launcher.loaded for launcher in ship.torpedo_launchers)
    assert any(event.type == "torpedo_launcher_destroyed" for event in state.events)


def test_special_damage_66_disables_all_guns_next_turn_and_wounds_captain() -> None:
    engine = IronBottomEngine()
    state = engine.reset("IBS-S-03", seed=11)
    ship = state.ships["IBS-U-KM-KARL-GALSTER"]
    engine._resolve_special_damage(state, ship, armour_already_penetrated=True)
    event = next(event for event in state.events if event.type == "special_damage")
    assert event.dice and event.dice.raw == 66
    assert ship.guns_disabled_turns == 1
    assert ship.captain_status == "wounded"


def test_special_damage_deck_fire_is_ignored_for_ship_without_aircraft() -> None:
    engine = IronBottomEngine()
    state = engine.reset("IBS-S-03", seed=1)
    ship = state.ships["IBS-U-KM-KARL-GALSTER"]
    assert not ship.aircraft and ship.belt_armor == 0
    before = ship.hull
    engine._roll_d66 = lambda _: (33, [3, 3])  # type: ignore[method-assign]
    engine._resolve_special_damage(state, ship, armour_already_penetrated=True)
    assert ship.hull == before - 1
    assert ship.fire_markers == 0
    assert ship.mfc_destroyed


def test_special_damage_belt_armour_exactly_equal_penetration_sinks_but_above_does_not() -> None:
    exact_engine = IronBottomEngine()
    exact = exact_engine.reset("IBS-S-01", seed=1)
    attacker = exact.ships["IBS-U-IJN-AOBA"]
    target = exact.ships["IBS-U-USN-HELENA"]
    target.belt_armor = 7
    exact_engine._roll_d66 = lambda _: (43, [4, 3])  # type: ignore[method-assign]
    exact_engine._resolve_special_damage(exact, target, attacker, distance=21, caliber=8)
    assert target.sunk
    event = next(event for event in exact.events if event.type == "special_damage")
    assert event.payload["penetrated"] is True

    blocked_engine = IronBottomEngine()
    blocked = blocked_engine.reset("IBS-S-01", seed=1)
    blocked_attacker = blocked.ships["IBS-U-IJN-AOBA"]
    blocked_target = blocked.ships["IBS-U-USN-HELENA"]
    blocked_target.belt_armor = 7.1
    blocked_engine._roll_d66 = lambda _: (43, [4, 3])  # type: ignore[method-assign]
    blocked_engine._resolve_special_damage(
        blocked, blocked_target, blocked_attacker, distance=21, caliber=8
    )
    assert not blocked_target.sunk
    blocked_event = next(event for event in blocked.events if event.type == "special_damage")
    assert blocked_event.payload["penetrated"] is False


def test_special_damage_31_destroys_radar_even_when_bridge_armour_stops_bridge_effects() -> None:
    engine = IronBottomEngine()
    state = engine.reset("IBS-S-01", seed=1)
    attacker = state.ships["IBS-U-IJN-AOBA"]
    target = state.ships["IBS-U-USN-HELENA"]
    target.bridge_armor = 99
    engine._roll_d66 = lambda _: (31, [3, 1])  # type: ignore[method-assign]
    engine._resolve_special_damage(state, target, attacker, distance=9, caliber=8)
    assert target.radar_destroyed
    assert not target.bridge_destroyed
    assert target.captain_status == "fit"
    assert target.forced_straight_turns == 0


def test_every_special_damage_d66_result_executes_with_audited_event() -> None:
    for roll in D66_VALUES:
        engine = IronBottomEngine()
        state = engine.reset("IBS-S-01", seed=roll)
        attacker = state.ships["IBS-U-IJN-AOBA"]
        target = state.ships["IBS-U-USN-HELENA"]
        engine._roll_d66 = lambda _, value=roll: (value, [value // 10, value % 10])  # type: ignore[method-assign]
        engine._resolve_special_damage(
            state, target, attacker, distance=9, armour_already_penetrated=True, caliber=8
        )
        event = next(event for event in state.events if event.type == "special_damage")
        assert event.dice and event.dice.raw == roll
        assert event.payload["effect"] == engine.rules.special_damage_result(
            roll, target.displacement_band
        )


def test_rudder_and_bridge_restrictions_reject_illegal_movement_plan() -> None:
    engine = IronBottomEngine()
    state = engine.reset("IBS-S-03", seed=1)
    for side in Side:
        assert engine.submit_orders(
            state.game_id, OrderBatch(side=side, phase=Phase.REINFORCEMENT)
        ).valid
    engine.advance(state.game_id)
    restricted = state.ships["IBS-U-KM-KARL-GALSTER"]
    restricted.turn_limit_degrees = 60
    restricted.forced_straight_turns = 1
    restricted.forced_speed = 5
    movement = [
        MovementOrder(ship_id=ship.id, plan="1PP1" if ship.id == restricted.id else "0")
        for ship in state.ships.values()
        if ship.side == Side.AXIS and ship.position
    ]
    result = engine.validate_orders(
        state.game_id,
        OrderBatch(side=Side.AXIS, phase=Phase.MOVEMENT_PLANNING, movement=movement),
    )
    assert not result.valid
    assert any("limits turns to 60" in error for error in result.errors)
    assert any("requires straight movement" in error for error in result.errors)
    assert any("requires original speed 5" in error for error in result.errors)
