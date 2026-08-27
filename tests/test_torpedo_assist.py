"""Batch E: torpedo assist backend — hit thresholds, expectation vs 36-outcome
brute force, straight-line path projection, constant-motion target extrapolation,
recommendation ranking, order adoption, scenario block, and the read-only API."""

import pytest
from fastapi.testclient import TestClient

from iron_bottom_sound.api import app, engine as api_engine
from iron_bottom_sound.engine import IronBottomEngine
from iron_bottom_sound.models import (
    HexCoord,
    MovementOrder,
    OrderBatch,
    Phase,
    Side,
    TorpedoOrder,
)


def sealed_movement(state, plans: dict[str, str]) -> None:
    """Inject sealed movement plans for a side so torpedo planning has trajectories."""
    state.sealed_orders[f"{state.turn}:movement_planning"] = {
        Side.AXIS.value: OrderBatch(
            side=Side.AXIS,
            phase=Phase.MOVEMENT_PLANNING,
            movement=[MovementOrder(ship_id=ship_id, plan=plan) for ship_id, plan in plans.items()],
        ),
        Side.ALLIES.value: OrderBatch(side=Side.ALLIES, phase=Phase.MOVEMENT_PLANNING, movement=[]),
    }


def karl_vs_javelin(engine: IronBottomEngine, game_id: str):
    """KARL at M12 (q12,r5) heading 1; JAVELIN due north at M8 (q12,r1) stationary.
    A port-A launch from heading 1 heads 6/N straight into the target at distance 4."""
    state = engine.reset("IBS-S-03", seed=3, game_id=game_id)
    karl = state.ships["IBS-U-KM-KARL-GALSTER"]
    jav = state.ships["IBS-U-RN-JAVELIN"]
    karl.position = HexCoord(q=12, r=5)
    karl.heading = 1
    jav.position = HexCoord(q=12, r=1)
    jav.heading = 6
    jav.current_speed = 0
    state.phase = Phase.TORPEDO_PLANNING
    sealed_movement(state, {karl.id: "0"})
    return state, karl, jav


def full_movement_batch(game_id: str, side: Side) -> OrderBatch:
    own = [
        ship for ship in api_engine.get(game_id).ships.values()
        if ship.side == side and ship.position is not None
    ]
    return OrderBatch(
        side=side,
        phase=Phase.MOVEMENT_PLANNING,
        movement=[MovementOrder(ship_id=ship.id, plan="0") for ship in own],
    )


def game_in_torpedo_planning(client, seed: int = 11) -> str:
    created = client.post("/games", json={"scenario_id": "IBS-S-03", "seed": seed}).json()
    game_id = created["game_id"]
    api_engine.submit_orders(game_id, OrderBatch(side=Side.AXIS, phase=Phase.REINFORCEMENT))
    api_engine.submit_orders(game_id, OrderBatch(side=Side.ALLIES, phase=Phase.REINFORCEMENT))
    api_engine.advance(game_id)
    assert api_engine.get(game_id).phase == Phase.MOVEMENT_PLANNING
    api_engine.submit_orders(game_id, full_movement_batch(game_id, Side.AXIS))
    api_engine.submit_orders(game_id, full_movement_batch(game_id, Side.ALLIES))
    api_engine.advance(game_id)
    assert api_engine.get(game_id).phase == Phase.TORPEDO_PLANNING
    return game_id


def test_torpedo_hit_count_matches_rulebook_thresholds() -> None:
    # IBS-R-08.2: broadside 2D6 >= 13 -> 2 hits, >= 11 -> 1; bow_stern >= 13 -> 1.
    assert IronBottomEngine.torpedo_hit_count("broadside", 10) == 0
    assert IronBottomEngine.torpedo_hit_count("broadside", 11) == 1
    assert IronBottomEngine.torpedo_hit_count("broadside", 12) == 1
    assert IronBottomEngine.torpedo_hit_count("broadside", 13) == 2
    assert IronBottomEngine.torpedo_hit_count("broadside", 20) == 2
    assert IronBottomEngine.torpedo_hit_count("bow_stern", 12) == 0
    assert IronBottomEngine.torpedo_hit_count("bow_stern", 13) == 1
    assert IronBottomEngine.torpedo_hit_count("bow_stern", 20) == 1


def _brute_force(aspect: str, modifier: int, salvo: int) -> tuple[float, float]:
    total = 0
    hitting = 0
    for die_one in range(1, 7):
        for die_two in range(1, 7):
            count = IronBottomEngine.torpedo_hit_count(aspect, die_one + die_two + modifier)
            total += min(count, salvo)
            if count:
                hitting += 1
    return total / 36, hitting / 36


def test_expected_hits_and_probability_match_brute_force() -> None:
    for aspect in ("broadside", "bow_stern"):
        for modifier in (-2, 0, 3, 7, 10):
            for salvo in (1, 2, 3):
                expected, probability = _brute_force(aspect, modifier, salvo)
                assert IronBottomEngine.expected_torpedo_hits(aspect, modifier, salvo) == pytest.approx(expected)
                assert IronBottomEngine.torpedo_hit_probability(aspect, modifier) == pytest.approx(probability)


def test_known_threshold_corner_cases() -> None:
    # bow_stern +7 needs 2D6 >= 6 (26 of 36 outcomes); broadside +7 gives 1 hit on
    # 2D6 4-5 (7 outcomes) and 2 hits on 2D6 6-12 (26 outcomes).
    assert IronBottomEngine.torpedo_hit_probability("bow_stern", 7) == pytest.approx(26 / 36)
    assert IronBottomEngine.expected_torpedo_hits("bow_stern", 7, 2) == pytest.approx(26 / 36)
    assert IronBottomEngine.expected_torpedo_hits("broadside", 7, 2) == pytest.approx(59 / 36)


def test_project_torpedo_path_straight_range_and_edge() -> None:
    engine = IronBottomEngine()
    state = engine.reset("IBS-S-03", seed=3, game_id="torp-proj")
    a10 = HexCoord.from_label("A10")
    projection = engine._project_torpedo_path(state, "de-nl-21", a10, 3, 0, 0)
    assert projection["end_hex"] == "A20"
    assert projection["distance_travelled"] == 10
    assert projection["range_remaining"] == 0
    assert projection["obstacle"] is None
    assert projection["path"][0] == "A10"
    assert len(projection["path"]) == 11
    # launching later in the turn still reaches the full 10-hex range
    late = engine._project_torpedo_path(state, "de-nl-21", a10, 3, 0, 5)
    assert late["end_hex"] == "A20"
    assert late["distance_travelled"] == 10
    # medium setting (range 14) goes farther
    medium = engine._project_torpedo_path(state, "de-nl-21", a10, 3, 1, 0)
    assert medium["distance_travelled"] == 14
    assert medium["end_hex"] == "A24"
    # the southern map edge truncates the path with the range still unconsumed
    a22 = HexCoord.from_label("A22")
    edge = engine._project_torpedo_path(state, "de-nl-21", a22, 3, 1, 0)
    assert edge["obstacle"] == "edge"
    assert edge["end_hex"] == "A27"
    assert edge["distance_travelled"] == 5
    assert edge["range_remaining"] == 9


def test_torpedo_launch_anchor_offset_per_authoritative_rule() -> None:
    """IBS-Q-005 锚点偏移（用户权威规则 8.2.3 b）：A/Y 起点在舰发射格；B 向船头
    反方向（船尾）外 1 格；X 向船头方向外 1 格。左右舷同角度共用同一锚点表。"""
    engine = IronBottomEngine()
    state = engine.reset("IBS-S-03", seed=3, game_id="torp-anchor")
    aa12 = HexCoord.from_label("AA12")
    bow = aa12.neighbor(4)      # 船头方向（航向 4）= Z12
    stern = aa12.neighbor(1)    # 船头反方向（航向 4 的逆向 = 1）= BB11
    for side in ("port", "starboard"):
        for angle, expected in (
            ("A", aa12.label),
            ("B", stern.label),
            ("X", bow.label),
            ("Y", aa12.label),
        ):
            projection = engine._project_torpedo_path(state, "de-nl-21", aa12, 1, 0, 0, angle, 4)
            assert projection["start_hex"] == expected, (
                f"{side} {angle} 锚点应起于 {expected}"
            )
    # 方向规则不变：port A/B=m-1, X/Y=m-2；starboard A/B=m+1, X/Y=m+2（对航向 4）。
    assert engine._torpedo_launch_heading(4, "port", "A") == 3
    assert engine._torpedo_launch_heading(4, "port", "B") == 3
    assert engine._torpedo_launch_heading(4, "port", "X") == 2
    assert engine._torpedo_launch_heading(4, "port", "Y") == 2
    assert engine._torpedo_launch_heading(4, "starboard", "A") == 5
    assert engine._torpedo_launch_heading(4, "starboard", "B") == 5
    assert engine._torpedo_launch_heading(4, "starboard", "X") == 6
    assert engine._torpedo_launch_heading(4, "starboard", "Y") == 6


def test_project_target_position_constant_motion_and_clamp() -> None:
    engine = IronBottomEngine()
    state = engine.reset("IBS-S-03", seed=3, game_id="torp-target")
    ship = state.ships["IBS-U-RN-JAVELIN"]
    ship.position = HexCoord.from_label("A10")
    ship.heading = 3
    ship.current_speed = 4
    assert engine._project_target_position(state, ship, 1) == HexCoord.from_label("A14")
    assert engine._project_target_position(state, ship, 2) == HexCoord.from_label("A18")
    ship.current_speed = 0
    assert engine._project_target_position(state, ship, 5) == HexCoord.from_label("A10")
    # clamp at the map edge instead of leaving it
    ship.position = HexCoord.from_label("A24")
    ship.heading = 3
    ship.current_speed = 4
    assert engine._project_target_position(state, ship, 1) == HexCoord.from_label("A27")
    ship.position = None
    assert engine._project_target_position(state, ship, 1) is None


def test_torpedo_assist_recommends_intercepting_combo_and_adopts_as_order() -> None:
    engine = IronBottomEngine()
    state, karl, jav = karl_vs_javelin(engine, "torp-assist")
    assist = engine.torpedo_assist(state, Side.AXIS, target_id=jav.id)
    assert assist["target_id"] == jav.id
    assert assist["target_name"] == jav.name
    assert assist["projected_target"]["label"] == "M8"
    assert assist["combos"]
    best = assist["combos"][0]
    assert best["expected_hits"] > 0
    assert best["intercept_hex"] == "M8"
    assert best["aspect"] == "bow_stern"
    assert best["modifier"] == 7
    # the straight-ahead port-A torpedo from heading 1 points due north at distance 4
    straight = next(
        combo for combo in assist["combos"]
        if combo["launch_side"] == "port"
        and combo["launch_angle"] == "A"
        and combo["launch_at_mf"] == 0
        and combo["setting_index"] == 0
    )
    assert straight["torpedo_heading"] == 6
    assert straight["distance"] == 4
    assert straight["expected_hits"] == pytest.approx(
        IronBottomEngine.expected_torpedo_hits(straight["aspect"], straight["modifier"], straight["salvo_size"])
    )
    # adopting the recommended combo as an order validates against the engine
    order = TorpedoOrder(
        ship_id=karl.id,
        launcher_id=straight["launcher_id"],
        count=1,
        launch_at_mf=straight["launch_at_mf"],
        launch_hex=HexCoord.from_label(straight["launch_hex"]),
        bearing=straight["launch_heading"],
        launch_side=straight["launch_side"],
        launch_angle=straight["launch_angle"],
        setting_index=straight["setting_index"],
    )
    batch = OrderBatch(side=Side.AXIS, phase=Phase.TORPEDO_PLANNING, torpedoes=[order])
    result = engine.validate_orders(state.game_id, batch)
    assert result.valid, result.errors
    assert engine.submit_orders(state.game_id, batch).valid


def test_torpedo_assist_single_launch_path_overlay() -> None:
    engine = IronBottomEngine()
    state, karl, jav = karl_vs_javelin(engine, "torp-assist-launch")
    launch = {
        "ship_id": karl.id,
        "launcher_id": "TT1",
        "launch_at_mf": 0,
        "launch_side": "port",
        "launch_angle": "A",
        "setting_index": 0,
    }
    assist = engine.torpedo_assist(state, Side.AXIS, target_id=jav.id, launch=launch)
    assert len(assist["combos"]) == 1
    combo = assist["combos"][0]
    assert combo["launcher_id"] == "TT1"
    assert combo["intercept_hex"] == "M8"
    assert "M8" in combo["predicted_path"]
    assert combo["predicted_path"][0] == "M12"
    assert combo["blocked_reason"] is None


def test_torpedo_assist_respects_scenario_block() -> None:
    engine = IronBottomEngine()
    state = engine.reset("IBS-S-01", seed=3, game_id="torp-block")
    state.phase = Phase.TORPEDO_PLANNING
    plans = {ship.id: "0" for ship in state.ships.values() if ship.side == Side.AXIS and ship.position}
    sealed_movement(state, plans)
    assist = engine.torpedo_assist(state, Side.AXIS)
    # scenario 1 blocks all axis torpedoes before turn 4 -> no legal combos
    assert assist["combos"] == []
    assert assist["target_id"] is not None


def test_torpedo_assist_api_shape_and_read_only() -> None:
    client = TestClient(app)
    game_id = game_in_torpedo_planning(client)
    state = api_engine.get(game_id)
    enemy = next(ship for ship in state.ships.values() if ship.side == Side.ALLIES and ship.position)
    before = len(api_engine.get(game_id).events)
    response = client.post(
        f"/games/{game_id}/torpedo-assist",
        headers={"X-Player-Side": "axis"},
        json={"target_id": enemy.id},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["target_id"] == enemy.id
    assert body["projected_target"]["label"] == enemy.position.label
    assert body["combos"]
    for key in (
        "ship_id", "launcher_id", "launch_at_mf", "launch_hex", "launch_side",
        "launch_angle", "setting_index", "torpedo_heading", "salvo_size", "distance",
        "aspect", "modifier", "hit_probability", "expected_hits", "predicted_path",
        "friendly_risk", "friendly_ship_ids",
    ):
        assert key in body["combos"][0]
    assert len(api_engine.get(game_id).events) == before  # pure read-only


def test_torpedo_assist_marks_friendly_ship_on_predicted_lane() -> None:
    engine = IronBottomEngine()
    state, _karl, target = karl_vs_javelin(engine, "friendly-lane")
    assist = engine.torpedo_assist(state, Side.AXIS, target_id=target.id)
    combo = next(item for item in assist["combos"] if len(item["predicted_path"]) > 1)
    friend = next(
        ship for ship in state.ships.values()
        if ship.side == Side.AXIS and ship.id != combo["ship_id"] and not ship.sunk
    )
    friend.position = HexCoord.from_label(combo["predicted_path"][-1])
    checked = engine.torpedo_assist(
        state, Side.AXIS, target_id=assist["target_id"], launch=combo,
    )["combos"][0]
    assert checked["friendly_risk"] is True
    assert friend.id in checked["friendly_ship_ids"]


def test_torpedo_assist_api_wrong_phase_rejected() -> None:
    client = TestClient(app)
    created = client.post("/games", json={"scenario_id": "IBS-S-03", "seed": 11}).json()
    game_id = created["game_id"]
    api_engine.submit_orders(game_id, OrderBatch(side=Side.AXIS, phase=Phase.REINFORCEMENT))
    api_engine.submit_orders(game_id, OrderBatch(side=Side.ALLIES, phase=Phase.REINFORCEMENT))
    api_engine.advance(game_id)
    assert api_engine.get(game_id).phase == Phase.MOVEMENT_PLANNING
    response = client.post(
        f"/games/{game_id}/torpedo-assist",
        headers={"X-Player-Side": "axis"},
        json={},
    )
    assert response.status_code == 409
