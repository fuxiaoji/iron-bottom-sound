from iron_bottom_sound.engine import IronBottomEngine
from iron_bottom_sound.models import (
    GameOptions,
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


def test_torpedo_launches_at_planned_mf_moves_by_impulse_and_contacts_ship() -> None:
    engine = IronBottomEngine()
    state = engine.reset("IBS-S-03", seed=9)
    attacker = state.ships["IBS-U-KM-KARL-GALSTER"]
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
    launch_hex = HexCoord.from_label("O15")
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
    assert next(item for item in attacker.torpedo_launchers if item.id == "TT1").loaded == 0
    for side in Side:
        assert engine.submit_orders(
            state.game_id, OrderBatch(side=side, phase=Phase.GUNNERY)
        ).valid
    engine.advance(state.game_id)
    engine.advance(state.game_id)
    assert not state.torpedo_tracks
    assert any(event.type == "torpedo_attack" for event in state.events)


def test_torpedo_plan_rejects_wrong_launch_hex_and_side_angle_pair() -> None:
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
    assert any("angles X/Y are starboard" in error for error in result.errors)
    assert any("launch_hex does not match" in error for error in result.errors)


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


def test_sunk_ship_creates_structured_wreck_at_its_hex() -> None:
    engine = IronBottomEngine()
    state = engine.reset("IBS-S-03", seed=1)
    ship = state.ships["IBS-U-KM-KARL-GALSTER"]
    original_position = ship.position
    engine._damage_hull(state, ship, ship.hull, "test")
    assert ship.sunk
    assert len(state.wrecks) == 1
    assert state.wrecks[0].position == original_position
    assert state.wrecks[0].source_ship_id == ship.id


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
