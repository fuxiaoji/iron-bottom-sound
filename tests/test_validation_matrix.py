from iron_bottom_sound.engine import IronBottomEngine
from iron_bottom_sound.models import (
    FiringArc,
    GunMountOrder,
    GunneryOrder,
    HexCoord,
    IlluminationOrder,
    MovementOrder,
    OrderBatch,
    Phase,
    SearchlightOrder,
    Side,
    SmokeOrder,
    TorpedoOrder,
)


def test_validation_rejects_cross_phase_and_damaged_movement_orders() -> None:
    engine = IronBottomEngine()
    state = engine.reset("IBS-S-03", 21)
    foreign_field = OrderBatch(
        side=Side.AXIS,
        phase=Phase.GUNNERY,
        movement=[MovementOrder(ship_id="enemy", plan="1")],
    )
    errors = engine.validate_orders(state.game_id, foreign_field).errors
    assert any("does not match" in error for error in errors)
    assert any("not legal" in error for error in errors)

    state.phase = Phase.MOVEMENT_PLANNING
    own = [ship for ship in state.ships.values() if ship.side == Side.AXIS and ship.position]
    damaged = own[0]
    damaged.turn_limit_degrees = 60
    damaged.forced_straight_turns = 1
    damaged.forced_circle_turns = 1
    damaged.forced_turn_side = "port"
    damaged.forced_speed = 2
    orders = [MovementOrder(ship_id=ship.id, plan="0") for ship in own]
    orders[0] = MovementOrder(ship_id=damaged.id, plan="1SS1", speed=7)
    errors = engine.validate_orders(
        state.game_id, OrderBatch(side=Side.AXIS, phase=state.phase, movement=orders)
    ).errors
    assert any("declared speed" in error for error in errors)
    assert any("limits turns" in error for error in errors)
    assert any("requires straight" in error for error in errors)
    assert any("requires original speed" in error for error in errors)
    assert any("circling turn" in error for error in errors)

    malformed = [MovementOrder(ship_id=ship.id, plan="0") for ship in own]
    malformed[0] = MovementOrder(ship_id=damaged.id, plan="not-a-plan")
    errors = engine.validate_orders(
        state.game_id, OrderBatch(side=Side.AXIS, phase=state.phase, movement=malformed)
    ).errors
    assert any(damaged.id in error for error in errors)

    state.phase = Phase.MOVEMENT_RESOLUTION
    assert "may not be submitted" in engine.validate_orders(
        state.game_id, OrderBatch(side=Side.AXIS)
    ).errors[0]


def test_validation_rejects_illegal_gunnery_optional_and_torpedo_orders() -> None:
    engine = IronBottomEngine()
    state = engine.reset("IBS-S-03", 22)
    attacker = next(ship for ship in state.ships.values() if ship.side == Side.AXIS and ship.position)
    friendly = next(
        ship for ship in state.ships.values() if ship.side == Side.AXIS and ship.id != attacker.id
    )
    enemy = next(ship for ship in state.ships.values() if ship.side == Side.ALLIES and ship.position)
    mount = attacker.gun_mounts[0]
    state.phase = Phase.GUNNERY
    batch = OrderBatch(
        side=Side.AXIS,
        phase=state.phase,
        gunnery=[
            GunneryOrder(ship_id="not-owned", primary_target=enemy.id),
            GunneryOrder(
                ship_id=attacker.id,
                primary_target=friendly.id,
                mounts=[
                    GunMountOrder(mount_id=mount.id, target_id=friendly.id),
                    GunMountOrder(mount_id=mount.id, target_id="missing"),
                ],
            ),
        ],
        illumination=[IlluminationOrder(ship_id="missing", mount_id="X", target_hex=HexCoord(q=1, r=1))],
        searchlights=[SearchlightOrder(ship_id="missing", target_id=enemy.id)],
        smoke=[SmokeOrder(ship_id="missing")],
    )
    errors = engine.validate_orders(state.game_id, batch).errors
    assert any("non-owned" in error for error in errors)
    assert any("Illegal target" in error for error in errors)
    assert any("duplicate gun mount" in error for error in errors)
    assert any("Star-shell" in error for error in errors)
    assert any("Searchlight" in error for error in errors)
    assert any("Smoke" in error for error in errors)
    assert any("cannot fire star shell" in error for error in errors)
    assert any("cannot use searchlight" in error for error in errors)
    assert any("only DD or CL" in error for error in errors)

    torpedo_ship = next(
        ship for ship in state.ships.values()
        if ship.side == Side.AXIS and ship.torpedo and ship.torpedo_launchers
    )
    launcher = torpedo_ship.torpedo_launchers[0]
    launcher.arcs = (FiringArc.PORT,)
    state.phase = Phase.TORPEDO_PLANNING
    order = TorpedoOrder(
        ship_id=torpedo_ship.id,
        launcher_id=launcher.id,
        count=9,
        launch_side="starboard",
        launch_angle="A",
        setting_index=99,
        launch_hex=torpedo_ship.position,
    )
    errors = engine.validate_orders(
        state.game_id,
        OrderBatch(side=Side.AXIS, phase=state.phase, torpedoes=[order, order]),
    ).errors
    assert any("lacks torpedo ammunition" in error for error in errors)
    assert any("cannot launch to starboard" in error for error in errors)
    assert any("invalid torpedo speed" in error for error in errors)
    assert any("missing sealed movement" in error for error in errors)
    assert any("only one launch order" in error for error in errors)

    errors = engine.validate_orders(
        state.game_id,
        OrderBatch(
            side=Side.AXIS,
            phase=state.phase,
            torpedoes=[TorpedoOrder(ship_id="missing", launcher_id="missing")],
        ),
    ).errors
    assert any("cannot fire torpedoes" in error for error in errors)
