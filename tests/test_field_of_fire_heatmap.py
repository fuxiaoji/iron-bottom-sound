"""Field-of-fire heatmap: per-hex aggregated gunnery coverage (arcs × range ×
distance-modifier-weighted firepower), stacked across guns/ships, both sides."""

import pytest
from fastapi.testclient import TestClient

from iron_bottom_sound.api import app, engine as api_engine
from iron_bottom_sound.engine import D66_VALUES, IronBottomEngine, d66_adjust
from iron_bottom_sound.models import HexCoord, Side


def brute_expected(engine: IronBottomEngine, firepower: int, distance: int, target_speed: int = 4) -> float:
    """36 档 D66 穷举：距离修正 + 目标航速修正的期望命中数（与引擎内部公式独立对照）。"""
    return sum(
        engine.rules.hit_count(
            firepower,
            d66_adjust(
                roll,
                engine.rules.range_modifier("gunnery", distance)
                + engine.rules.target_speed_modifier("gunnery", target_speed),
            ),
        )
        for roll in D66_VALUES
    ) / len(D66_VALUES)


def isolated_axis_ship(engine: IronBottomEngine, game_id: str, seed: int = 3):
    """把想定里其它轴心舰全部移出地图，只留一艘，使热值可逐舰核对。"""
    state = engine.reset("IBS-S-03", seed=seed, game_id=game_id)
    positioned = [ship for ship in state.ships.values() if ship.side == Side.AXIS and ship.position]
    keep = positioned[0]
    for ship in state.ships.values():
        if ship.side == Side.AXIS and ship is not keep:
            ship.position = None
    return state, keep


def all_cells():
    return [
        HexCoord(q=q, r=row - (q - (q & 1)) // 2)
        for q in range(34)
        for row in range(27)
    ]


def expected_heat_for_ship(engine: IronBottomEngine, ship, cell: HexCoord) -> float:
    """该舰全部可射炮位对某格的 `firepower × 期望命中` 之和（引擎公式的独立复算）。"""
    if cell == ship.position:
        return 0.0
    total = 0.0
    for mount in ship.gun_mounts:
        if mount.destroyed:
            continue
        if IronBottomEngine._relative_aspect(ship.position, ship.heading, cell) not in mount.arcs:
            continue
        total += mount.firepower * brute_expected(engine, mount.firepower, ship.position.distance(cell))
    return round(total, 4)


def test_heatmap_equals_brute_force_exhaustion_per_mount() -> None:
    engine = IronBottomEngine()
    state, ship = isolated_axis_ship(engine, "hm-brute")
    result = engine.field_of_fire_heatmap(state, Side.AXIS)
    hexes = result["sides"]["axis"]["hexes"]
    assert len(hexes) > 0
    for cell in all_cells():
        assert hexes.get(cell.label, 0.0) == expected_heat_for_ship(engine, ship, cell)
    assert result["sides"]["axis"]["max_heat"] == max(hexes.values())


def test_destroyed_own_mount_drops_exactly_its_contribution() -> None:
    engine = IronBottomEngine()
    state, ship = isolated_axis_ship(engine, "hm-destroyed")
    mount = ship.gun_mounts[0]
    before = engine.field_of_fire_heatmap(state, Side.AXIS)["sides"]["axis"]["hexes"]
    mount.destroyed = True
    after = engine.field_of_fire_heatmap(state, Side.AXIS)["sides"]["axis"]["hexes"]
    assert after != before  # 该炮位至少覆盖一格，其热值必须消失
    for cell in all_cells():
        contribution = 0.0
        if cell != ship.position and IronBottomEngine._relative_aspect(ship.position, ship.heading, cell) in mount.arcs:
            contribution = mount.firepower * brute_expected(engine, mount.firepower, ship.position.distance(cell))
        before_heat = before.get(cell.label, 0.0)
        after_heat = after.get(cell.label, 0.0)
        if contribution == 0.0:
            assert before_heat == after_heat
        else:
            # 两次独立四舍五入，容差对齐
            assert abs((before_heat - after_heat) - contribution) <= 2e-4


def test_enemy_side_uses_recorded_mounts_no_hidden_damage_leak() -> None:
    engine = IronBottomEngine()
    state = engine.reset("IBS-S-03", seed=3, game_id="hm-enemy-record")
    enemy = next(ship for ship in state.ships.values() if ship.side == Side.ALLIES and ship.gun_mounts)
    before = engine.field_of_fire_heatmap(state, Side.AXIS)["sides"]["allies"]["hexes"]
    enemy.gun_mounts[0].destroyed = True  # 隐藏损伤不得泄漏到敌方热力图
    after = engine.field_of_fire_heatmap(state, Side.AXIS)["sides"]["allies"]["hexes"]
    assert before == after
    assert enemy.id in {ship["ship_id"] for ship in engine.field_of_fire_heatmap(state, Side.AXIS)["sides"]["allies"]["ships"]}


def test_own_side_heatmap_drops_destroyed_mounts_for_each_viewer() -> None:
    engine = IronBottomEngine()
    state = engine.reset("IBS-S-03", seed=3, game_id="hm-own-damage")

    # axis 视角：axis 是本方 → 已毁轴心炮位被剔除
    axis_own = next(ship for ship in state.ships.values() if ship.side == Side.AXIS and ship.gun_mounts)
    before_axis = engine.field_of_fire_heatmap(state, Side.AXIS)["sides"]["axis"]["hexes"]
    axis_own.gun_mounts[0].destroyed = True
    after_axis = engine.field_of_fire_heatmap(state, Side.AXIS)["sides"]["axis"]["hexes"]
    assert after_axis != before_axis

    # allies 视角：axis 是敌方 → 已毁轴心炮位按记录全炮位保留，不得因隐藏损伤变化
    assert engine.field_of_fire_heatmap(state, Side.ALLIES)["sides"]["axis"]["hexes"] == before_axis


def test_invisible_enemy_ship_is_excluded() -> None:
    engine = IronBottomEngine()
    state = engine.reset("IBS-S-03", seed=3, game_id="hm-hidden")
    enemy = next(ship for ship in state.ships.values() if ship.side == Side.ALLIES and ship.position)
    own = [ship for ship in state.ships.values() if ship.side == Side.AXIS and ship.position]
    assert min(enemy.position.distance(o.position) for o in own) <= 4  # 初始在可见范围内
    visible = engine.field_of_fire_heatmap(state, Side.AXIS)["sides"]["allies"]
    assert enemy.id in {ship["ship_id"] for ship in visible["ships"]}
    before = visible["hexes"]
    # 选一个离所有本舰都超过 4 格的合法角格（地图角点）
    corners = [
        HexCoord(q=0, r=0), HexCoord(q=0, r=26), HexCoord(q=16, r=-8),
        HexCoord(q=16, r=18), HexCoord(q=33, r=-16), HexCoord(q=33, r=10),
    ]
    far = max(corners, key=lambda c: min(c.distance(o.position) for o in own))
    assert all(far.distance(o.position) > 4 for o in own)
    enemy.position = far
    hidden = engine.field_of_fire_heatmap(state, Side.AXIS)["sides"]["allies"]
    assert enemy.id not in {ship["ship_id"] for ship in hidden["ships"]}
    assert hidden["hexes"] != before  # 该舰热值消失


def test_both_sides_present_and_read_only_api() -> None:
    client = TestClient(app)
    created = client.post("/games", json={"scenario_id": "IBS-S-03", "seed": 3}).json()
    game_id = created["game_id"]
    before = len(api_engine.get(game_id).events)
    response = client.post(f"/games/{game_id}/field-of-fire", headers={"X-Player-Side": "axis"})
    assert response.status_code == 200
    body = response.json()
    assert body["viewer"] == "axis"
    assert set(body["sides"]) == {"axis", "allies"}
    for side_data in body["sides"].values():
        hexes = side_data["hexes"]
        assert all(heat > 0 for heat in hexes.values())
        assert side_data["max_heat"] == (round(max(hexes.values()), 4) if hexes else 0.0)
        assert isinstance(side_data["ships"], list)
    assert len(api_engine.get(game_id).events) == before  # 只读


def test_per_ship_heat_matches_brute_force_and_empty_other_side() -> None:
    engine = IronBottomEngine()
    state, ship = isolated_axis_ship(engine, "hm-ship")
    result = engine.field_of_fire_heatmap(state, Side.AXIS, ship_id=ship.id)
    hexes = result["sides"]["axis"]["hexes"]
    assert len(hexes) > 0
    for cell in all_cells():
        assert hexes.get(cell.label, 0.0) == expected_heat_for_ship(engine, ship, cell)
    assert result["sides"]["axis"]["max_heat"] == max(hexes.values())
    assert result["sides"]["axis"]["ships"] == [{
        "ship_id": ship.id, "name": ship.name, "position": ship.position.label, "heading": ship.heading,
    }]
    # 另一侧为空
    assert result["sides"]["allies"]["hexes"] == {}
    assert result["sides"]["allies"]["max_heat"] == 0.0
    assert result["sides"]["allies"]["ships"] == []


def test_per_ship_own_drops_destroyed_mount_enemy_keeps_recorded() -> None:
    engine = IronBottomEngine()
    state = engine.reset("IBS-S-03", seed=3, game_id="hm-ship-damage")

    # 选本方舰：已毁炮位从单舰热力中消失
    own = next(ship for ship in state.ships.values() if ship.side == Side.AXIS and ship.gun_mounts)
    before_own = engine.field_of_fire_heatmap(state, Side.AXIS, ship_id=own.id)["sides"]["axis"]["hexes"]
    own.gun_mounts[0].destroyed = True
    after_own = engine.field_of_fire_heatmap(state, Side.AXIS, ship_id=own.id)["sides"]["axis"]["hexes"]
    assert after_own != before_own

    # 选敌方舰：记录全炮位，隐藏损伤不得泄漏
    enemy = next(ship for ship in state.ships.values() if ship.side == Side.ALLIES and ship.gun_mounts)
    before_enemy = engine.field_of_fire_heatmap(state, Side.AXIS, ship_id=enemy.id)["sides"]["allies"]["hexes"]
    enemy.gun_mounts[0].destroyed = True
    after_enemy = engine.field_of_fire_heatmap(state, Side.AXIS, ship_id=enemy.id)["sides"]["allies"]["hexes"]
    assert after_enemy == before_enemy


def test_per_ship_invalid_and_hidden_ship_return_empty() -> None:
    engine = IronBottomEngine()
    state = engine.reset("IBS-S-03", seed=3, game_id="hm-ship-empty")
    for ship_id in ("no-such-ship",):
        result = engine.field_of_fire_heatmap(state, Side.AXIS, ship_id=ship_id)
        for side_data in result["sides"].values():
            assert side_data["hexes"] == {}
            assert side_data["max_heat"] == 0.0
            assert side_data["ships"] == []
    # 超视距敌舰：选中也被兜底拒绝
    enemy = next(ship for ship in state.ships.values() if ship.side == Side.ALLIES and ship.position)
    own = [ship for ship in state.ships.values() if ship.side == Side.AXIS and ship.position]
    corners = [
        HexCoord(q=0, r=0), HexCoord(q=0, r=26), HexCoord(q=16, r=-8),
        HexCoord(q=16, r=18), HexCoord(q=33, r=-16), HexCoord(q=33, r=10),
    ]
    far = max(corners, key=lambda c: min(c.distance(o.position) for o in own))
    enemy.position = far
    hidden = engine.field_of_fire_heatmap(state, Side.AXIS, ship_id=enemy.id)
    assert hidden["sides"]["allies"]["hexes"] == {}


def test_per_ship_api_shape() -> None:
    client = TestClient(app)
    created = client.post("/games", json={"scenario_id": "IBS-S-03", "seed": 3}).json()
    game_id = created["game_id"]
    own = next(ship for ship in api_engine.get(game_id).ships.values() if ship.side == Side.AXIS and ship.gun_mounts)
    response = client.post(
        f"/games/{game_id}/field-of-fire", json={"ship_id": own.id}, headers={"X-Player-Side": "axis"}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["viewer"] == "axis"
    assert body["sides"]["allies"]["hexes"] == {}
    assert body["sides"]["axis"]["hexes"]
    assert body["sides"]["axis"]["ships"][0]["ship_id"] == own.id
    # 不带 ship_id 仍是双方全图
    full = client.post(f"/games/{game_id}/field-of-fire", headers={"X-Player-Side": "axis"}).json()
    assert full["sides"]["allies"]["hexes"] and full["sides"]["axis"]["hexes"]


def test_target_speed_4_uses_verified_zero_modifier_and_parameter_applies() -> None:
    engine = IronBottomEngine()
    # 已验证目标航速表：0→-18、1→-9、2-3→-4、4+→0 → 航速 4 修正为 0
    assert engine.rules.target_speed_modifier("gunnery", 4) == 0
    assert engine.rules.target_speed_modifier("gunnery", 3) == -4

    state, ship = isolated_axis_ship(engine, "hm-speed")
    default = engine.field_of_fire_heatmap(state, Side.AXIS)["sides"]["axis"]["hexes"]
    explicit4 = engine.field_of_fire_heatmap(state, Side.AXIS, target_speed=4)["sides"]["axis"]["hexes"]
    assert default == explicit4
    # 航速 3（修正 -4）应改变热值，且与 36 档穷举逐格一致
    speed3 = engine.field_of_fire_heatmap(state, Side.AXIS, target_speed=3)["sides"]["axis"]["hexes"]
    assert speed3 != default
    for cell in all_cells():
        expected = 0.0
        for mount in ship.gun_mounts:
            if mount.destroyed or cell == ship.position:
                continue
            if IronBottomEngine._relative_aspect(ship.position, ship.heading, cell) in mount.arcs:
                expected += mount.firepower * brute_expected(engine, mount.firepower, ship.position.distance(cell), target_speed=3)
        assert speed3.get(cell.label, 0.0) == round(expected, 4)


def test_relative_aspect_matches_mount_can_bear() -> None:
    engine = IronBottomEngine()
    state = engine.reset("IBS-S-03", seed=3, game_id="hm-aspect")
    ship = next(ship for ship in state.ships.values() if ship.side == Side.AXIS and ship.position)
    probe = ship.model_copy(deep=True)
    for cell in all_cells():
        if cell == ship.position:
            continue
        probe.position = cell
        for mount in ship.gun_mounts:
            assert IronBottomEngine._mount_can_bear(ship, probe, mount.arcs) == (
                IronBottomEngine._relative_aspect(ship.position, ship.heading, cell) in mount.arcs
            )
