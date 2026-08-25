"""批次 C：战报损伤摘要。

五个结算点（gunnery_result / torpedo_result / special_damage / fire_check /
ship_sunk）在 payload 并入归一化损伤字段，`_damage_hull`/`_lose_speed` 返回
实际值，火灾沉没可追溯点火者，`ShipCombatEntry` 携带 payload。隐藏损伤过滤后
不泄漏；回放保持字节等价。
"""

from iron_bottom_sound.engine import IronBottomEngine
from iron_bottom_sound.models import (
    GameOptions,
    GunMountOrder,
    GunneryOrder,
    HexCoord,
    MovementOrder,
    OptionalRules,
    OrderBatch,
    Phase,
    Side,
    TorpedoTrack,
)


def gunnery_attack_orders(engine: IronBottomEngine, state, attacker, target) -> OrderBatch:
    mounts = [mount for mount in attacker.gun_mounts if mount.kind == "primary"]
    return OrderBatch(
        side=attacker.side,
        phase=Phase.GUNNERY,
        gunnery=[GunneryOrder(
            ship_id=attacker.id,
            mounts=[GunMountOrder(mount_id=mount.id, target_id=target.id) for mount in mounts],
        )],
    )


def run_gunnery(engine: IronBottomEngine, state, attacker, target) -> None:
    axis, allies = (attacker, target) if attacker.side == Side.AXIS else (target, attacker)
    for batch in (
        gunnery_attack_orders(engine, state, axis, allies),
        OrderBatch(side=allies.side, phase=Phase.GUNNERY),
    ):
        assert engine.submit_orders(state.game_id, batch).valid
    engine.advance(state.game_id)


def test_damage_snapshot_delta_helpers_match_real_state_diff() -> None:
    engine = IronBottomEngine()
    state = engine.reset("IBS-S-03", seed=1)
    ship = state.ships["IBS-U-KM-KARL-GALSTER"]
    before = engine._damage_snapshot(ship)
    engine._damage_hull(state, ship, 2, "test")
    engine._lose_speed(ship, 3)
    engine._add_fire(state, ship, None)
    ship.guns_disabled_turns = max(ship.guns_disabled_turns, 1)
    after = engine._damage_snapshot(ship)
    delta = engine._damage_delta(before, after)
    assert delta["hull_lost"] == 2
    assert delta["speed_lost"] == 3
    assert delta["fire_added"] == 1
    assert delta["fire_remaining"] == 1
    assert delta["flags"]["guns_disabled_turns"] == 1


def test_damage_hull_and_lose_speed_return_actual_values() -> None:
    engine = IronBottomEngine()
    state = engine.reset("IBS-S-01", seed=1)
    helena = state.ships["IBS-U-USN-HELENA"]
    before = helena.hull
    assert engine._damage_hull(state, helena, before, "test") == before
    assert helena.sunk
    assert engine._damage_hull(state, helena, 5, "test") == 0  # 已沉没
    other = state.ships["IBS-U-IJN-AOBA"]
    assert engine._lose_speed(other, 7) == 7
    assert sum(other.speed_damage_crossed) == 7


def test_gunnery_result_payload_delta_matches_state_and_names() -> None:
    engine = IronBottomEngine()
    state = engine.reset("IBS-S-01", seed=5)
    state.turn = 2  # 想定1日舰第1回合禁炮击
    state.phase = Phase.GUNNERY
    attacker = state.ships["IBS-U-IJN-AOBA"]
    target = state.ships["IBS-U-USN-HELENA"]
    attacker.position = HexCoord.from_label("A1")
    attacker.heading = 1
    target.position = HexCoord.from_label("A3")
    target.heading = 6
    target.current_speed = 0
    target.belt_armor = 0
    before_hull = target.hull
    # 命中判定 + 多份结果 24（{"hull":1,"armour_check":true}），不触发特殊分支。
    rolls = iter([(26, [2, 6])] + [(24, [2, 4])] * 6)
    engine._roll_d66 = lambda _: next(rolls)  # type: ignore[method-assign]
    run_gunnery(engine, state, attacker, target)
    results = [event for event in state.events if event.type == "gunnery_result"]
    assert results
    for event in results:
        assert event.payload["attacker_name"] == attacker.name
        assert event.payload["target_name"] == target.name
        assert event.payload["damage"]["hull_lost"] == 1
        assert event.payload["damage"]["fire_added"] == 0
    assert sum(event.payload["damage"]["hull_lost"] for event in results) == before_hull - target.hull


def test_torpedo_result_payload_delta_matches_rulebook_example() -> None:
    engine = IronBottomEngine()
    state = engine.reset("IBS-S-01", seed=9)
    aoba = state.ships["IBS-U-IJN-AOBA"]
    helena = state.ships["IBS-U-USN-HELENA"]
    helena.current_speed = 5
    helena.previous_speed = 5
    helena.heading = 1
    helena.speed_damage_crossed = (0, 0, 0)
    before_hull = helena.hull
    state.torpedo_tracks.append(TorpedoTrack(
        id="DELTA-TT",
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
    event = next(event for event in state.events if event.type == "torpedo_result")
    assert event.payload["attacker_name"] == aoba.name
    assert event.payload["target_name"] == helena.name
    assert event.payload["damage"]["hull_lost"] == before_hull - helena.hull == 5
    assert event.payload["damage"]["speed_lost"] == 7
    assert event.payload["damage"]["sank"] is False
    assert event.payload["damage"]["fire_added"] == 1  # damage_roll == 8 触发起火


def test_special_damage_payload_delta_reports_flags_only() -> None:
    engine = IronBottomEngine()
    state = engine.reset("IBS-S-03", seed=11)
    ship = state.ships["IBS-U-KM-KARL-GALSTER"]
    before_hull = ship.hull
    engine._roll_d66 = lambda _: (66, [6, 6])  # type: ignore[method-assign]
    engine._resolve_special_damage(state, ship, armour_already_penetrated=True)
    event = next(event for event in state.events if event.type == "special_damage")
    assert event.payload["target_name"] == ship.name
    assert event.payload["damage"]["hull_lost"] == before_hull - ship.hull == 0
    assert event.payload["damage"]["flags"]["guns_disabled_turns"] == 1
    assert event.payload["damage"]["flags"]["captain_status"] == "wounded"


def test_fire_check_payload_delta_matches_hull_speed_and_mount_loss() -> None:
    engine = IronBottomEngine()
    state = engine.reset("IBS-S-03", seed=1)
    ship = state.ships["IBS-U-KM-KARL-GALSTER"]
    ship.fire_markers = 1
    ship.fired = True
    before_hull = ship.hull
    before_crossed = sum(ship.speed_damage_crossed)
    before_mounts = sum(mount.destroyed for mount in ship.gun_mounts)
    engine._roll_2d6 = lambda _: (11, [5, 6])  # type: ignore[method-assign]
    engine._resolve_fire(state)
    event = next(event for event in state.events if event.type == "fire_check")
    assert event.payload["target_name"] == ship.name
    assert event.payload["damage"]["hull_lost"] == before_hull - ship.hull == 1
    assert event.payload["damage"]["speed_lost"] == sum(ship.speed_damage_crossed) - before_crossed == 1
    destroyed = sum(mount.destroyed for mount in ship.gun_mounts) - before_mounts
    assert event.payload["damage"]["gun_mounts_destroyed"] == destroyed


def test_gunnery_sinking_attributes_attacker_name_and_position() -> None:
    engine = IronBottomEngine()
    state = engine.reset("IBS-S-01", seed=5)
    state.turn = 2  # 想定1日舰第1回合禁炮击
    state.phase = Phase.GUNNERY
    attacker = state.ships["IBS-U-IJN-AOBA"]
    target = state.ships["IBS-U-USN-HELENA"]
    attacker.position = HexCoord.from_label("A1")
    attacker.heading = 1
    target.position = HexCoord.from_label("A3")
    target.heading = 6
    target.current_speed = 0
    target.belt_armor = 0
    target.hull = 1
    target_position = target.position.label
    rolls = iter([(26, [2, 6])] + [(24, [2, 4])] * 6)
    engine._roll_d66 = lambda _: next(rolls)  # type: ignore[method-assign]
    run_gunnery(engine, state, attacker, target)
    assert target.sunk
    sunk = next(event for event in state.events if event.type == "ship_sunk")
    assert sunk.payload["cause"] == "gunnery"
    assert sunk.payload["attacker"] == attacker.id
    assert sunk.payload["attacker_name"] == attacker.name
    assert sunk.payload["position"] == target_position


def test_fire_sinking_traces_to_first_igniter() -> None:
    engine = IronBottomEngine()
    state = engine.reset("IBS-S-03", seed=1)
    ship = state.ships["IBS-U-KM-KARL-GALSTER"]
    igniter = state.ships["IBS-U-RN-JAVELIN"]
    engine._add_fire(state, ship, igniter)
    assert ship.fire_source_attacker == igniter.id
    assert ship.fire_source_turn == state.turn
    ship.hull = 1
    ship.fired = True
    ship.position = HexCoord.from_label("O14")
    engine._roll_2d6 = lambda _: (7, [3, 4])  # type: ignore[method-assign]
    engine._resolve_fire(state)
    assert ship.sunk
    sunk = next(event for event in state.events if event.type == "ship_sunk")
    assert sunk.payload["cause"] == "fire"
    assert sunk.payload["attacker"] == igniter.id
    assert sunk.payload["attacker_name"] == igniter.name


def test_first_igniter_is_never_overwritten_and_internal_fire_is_attributable_none() -> None:
    engine = IronBottomEngine()
    state = engine.reset("IBS-S-03", seed=1)
    ship = state.ships["IBS-U-KM-KARL-GALSTER"]
    other = state.ships["IBS-U-RN-JAVELIN"]
    engine._add_fire(state, ship, None)  # 本舰故障起火：无攻击者
    assert ship.fire_source_attacker is None
    engine._add_fire(state, ship, other)
    assert ship.fire_source_attacker == other.id  # 首次攻击性点火记入
    another = state.ships["IBS-U-RN-KASHMIR"]
    engine._add_fire(state, ship, another)
    assert ship.fire_source_attacker == other.id  # 不被覆盖
    assert ship.fire_markers == 3


def test_ship_combat_entry_carries_damage_payload_for_received_hits() -> None:
    engine = IronBottomEngine()
    state = engine.reset("IBS-S-01", seed=5)
    state.turn = 2  # 想定1日舰第1回合禁炮击
    state.phase = Phase.GUNNERY
    attacker = state.ships["IBS-U-IJN-AOBA"]
    target = state.ships["IBS-U-USN-HELENA"]
    attacker.position = HexCoord.from_label("A1")
    attacker.heading = 1
    target.position = HexCoord.from_label("A3")
    target.heading = 6
    target.current_speed = 0
    target.belt_armor = 0
    rolls = iter([(26, [2, 6])] + [(24, [2, 4])] * 6)
    engine._roll_d66 = lambda _: next(rolls)  # type: ignore[method-assign]
    run_gunnery(engine, state, attacker, target)
    view = engine.observe(state.game_id, Side.ALLIES)
    public = next(ship for ship in view.ships if ship.id == target.id)
    received = [entry for entry in public.combat_history if entry.direction == "received" and entry.event_type == "gunnery_result"]
    assert received
    assert all(entry.payload["damage"]["hull_lost"] == 1 for entry in received)
    assert all(entry.payload["target_name"] == target.name for entry in received)


def test_hidden_damage_filters_damage_payload_and_combat_history() -> None:
    engine = IronBottomEngine()
    options = GameOptions(optional_rules=OptionalRules(hidden_damage=True))
    state = engine.reset("IBS-S-01", seed=5, options=options)
    state.turn = 2  # 想定1日舰第1回合禁炮击
    state.phase = Phase.GUNNERY
    attacker = state.ships["IBS-U-IJN-AOBA"]
    target = state.ships["IBS-U-USN-HELENA"]
    attacker.position = HexCoord.from_label("A1")
    attacker.heading = 1
    target.position = HexCoord.from_label("A3")
    target.heading = 6
    target.current_speed = 0
    target.belt_armor = 0
    rolls = iter([(26, [2, 6])] + [(24, [2, 4])] * 6)
    engine._roll_d66 = lambda _: next(rolls)  # type: ignore[method-assign]
    run_gunnery(engine, state, attacker, target)

    allies_view = engine.observe(state.game_id, Side.ALLIES)
    allies_results = [e for e in allies_view.recent_events if e.type == "gunnery_result"]
    assert allies_results
    assert all("damage" in event.payload for event in allies_results)

    axis_view = engine.observe(state.game_id, Side.AXIS)
    assert not any(e.type == "gunnery_result" for e in axis_view.recent_events)
    attacker_public = next(ship for ship in axis_view.ships if ship.id == attacker.id)
    assert not any(entry.payload.get("damage") for entry in attacker_public.combat_history)
    enemy_public = next(ship for ship in axis_view.ships if ship.id == target.id)
    assert not any(entry.event_type == "gunnery_result" for entry in enemy_public.combat_history)


def test_attack_events_carry_attacker_and_target_side() -> None:
    engine = IronBottomEngine()
    state = engine.reset("IBS-S-01", seed=5)
    state.turn = 2  # 想定1日舰第1回合禁炮击
    state.phase = Phase.GUNNERY
    attacker = state.ships["IBS-U-IJN-AOBA"]
    target = state.ships["IBS-U-USN-HELENA"]
    attacker.position = HexCoord.from_label("A1")
    attacker.heading = 1
    target.position = HexCoord.from_label("A3")
    target.heading = 6
    target.current_speed = 0
    target.belt_armor = 0
    rolls = iter([(26, [2, 6])] + [(24, [2, 4])] * 6)
    engine._roll_d66 = lambda _: next(rolls)  # type: ignore[method-assign]
    run_gunnery(engine, state, attacker, target)
    attack = next(event for event in state.events if event.type == "gun_mount_attack")
    assert attack.payload["attacker_side"] == attacker.side.value
    assert attack.payload["target_side"] == target.side.value


def test_torpedo_attack_event_carries_attacker_and_target_side() -> None:
    engine = IronBottomEngine()
    state = engine.reset("IBS-S-01", seed=9)
    aoba = state.ships["IBS-U-IJN-AOBA"]
    helena = state.ships["IBS-U-USN-HELENA"]
    helena.current_speed = 5
    helena.previous_speed = 5
    helena.heading = 1
    helena.speed_damage_crossed = (0, 0, 0)
    state.torpedo_tracks.append(TorpedoTrack(
        id="DELTA-TT",
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
    assert attack.payload["attacker_side"] == aoba.side.value
    assert attack.payload["target_side"] == helena.side.value


def test_observe_exposes_own_speed_damage_and_hides_enemy() -> None:
    engine = IronBottomEngine()
    state = engine.reset("IBS-S-03", seed=1)
    karl = state.ships["IBS-U-KM-KARL-GALSTER"]
    engine._lose_speed(karl, 2)
    axis_view = engine.observe(state.game_id, Side.AXIS)
    public_karl = next(ship for ship in axis_view.ships if ship.id == karl.id)
    assert public_karl.speed_damage_crossed == list(karl.speed_damage_crossed)
    assert public_karl.speed_damage_track == [list(row) for row in karl.speed_damage_track]
    assert sum(public_karl.speed_damage_crossed) == 2
    # 敌舰速度损伤对本方隐藏
    enemy = next(ship for ship in state.ships.values() if ship.side == Side.ALLIES and ship.position)
    enemy.speed_damage_crossed = (1, 0, 0)
    axis_public_enemy = next(ship for ship in axis_view.ships if ship.id == enemy.id)
    assert axis_public_enemy.speed_damage_crossed is None
    assert axis_public_enemy.speed_damage_track is None


def test_replay_rebuilds_byte_equivalent_events_with_damage_payloads() -> None:
    # 走完整阶段流程到炮击并真正命中：回放必须以相同 seed 再生出含损伤 payload 的同一事件流。
    engine = IronBottomEngine()
    state = engine.reset("IBS-S-03", seed=123)
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
            state.game_id, OrderBatch(side=side, phase=Phase.MOVEMENT_PLANNING, movement=movement)
        ).valid
    engine.advance(state.game_id)
    for side in Side:
        assert engine.submit_orders(
            state.game_id, OrderBatch(side=side, phase=Phase.TORPEDO_PLANNING)
        ).valid
    engine.advance(state.game_id)
    engine.advance(state.game_id)
    assert state.phase == Phase.GUNNERY
    karl = state.ships["IBS-U-KM-KARL-GALSTER"]
    javelin = state.ships["IBS-U-RN-JAVELIN"]
    mounts = [mount for mount in karl.gun_mounts if mount.kind == "primary"]
    assert engine.submit_orders(
        state.game_id,
        OrderBatch(
            side=Side.AXIS,
            phase=Phase.GUNNERY,
            gunnery=[GunneryOrder(
                ship_id=karl.id,
                mounts=[GunMountOrder(mount_id=mount.id, target_id=javelin.id) for mount in mounts],
            )],
        ),
    ).valid
    assert engine.submit_orders(
        state.game_id, OrderBatch(side=Side.ALLIES, phase=Phase.GUNNERY)
    ).valid
    engine.advance(state.game_id)
    results = [event for event in state.events if event.type == "gunnery_result"]
    assert results
    assert sum(event.payload["damage"]["hull_lost"] for event in results) > 0

    rebuilt = engine.replay(state.events)
    assert rebuilt.model_dump(mode="json") == state.model_dump(mode="json")
    assert [event.model_dump_json() for event in rebuilt.events] == [
        event.model_dump_json() for event in state.events
    ]
