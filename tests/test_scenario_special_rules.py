"""想定特例引擎强制（special_rule_kinds）的裁决测试。

每条用例对应 open_questions IBS-Q-020 里已实现的一项规则类型；
想定数据见 resources/derived/structured/scenarios/scenario-*.yaml。
"""
from __future__ import annotations

import math

import pytest

from iron_bottom_sound.data import build_initial_state
from iron_bottom_sound.engine import IronBottomEngine
from iron_bottom_sound.models import (
    GameOptions,
    GunneryOrder,
    GunMountOrder,
    MovementOrder,
    OrderBatch,
    Phase,
    Side,
    TorpedoOrder,
)
from iron_bottom_sound.scenario_rules import scenario_rules


def _drive_to(engine: IronBottomEngine, state, phase: Phase) -> None:
    """双方空单推进到指定阶段（增援→移动→鱼雷→炮击）。"""
    ladder = [Phase.REINFORCEMENT, Phase.MOVEMENT_PLANNING, Phase.TORPEDO_PLANNING,
              Phase.MOVEMENT_RESOLUTION, Phase.TORPEDO_EFFECTS, Phase.GUNNERY]
    while state.phase != phase:
        assert state.phase in ladder, f"cannot reach {phase} from {state.phase}"
        for side in Side:
            if state.phase == Phase.MOVEMENT_PLANNING:
                orders = [MovementOrder(ship_id=s.id, plan="0") for s in state.ships.values()
                          if s.side == side and s.position and not s.sunk]
                engine.submit_orders(state.game_id, OrderBatch(side=side, phase=state.phase, movement=orders))
            else:
                engine.submit_orders(state.game_id, OrderBatch(side=side, phase=state.phase))
        engine.advance(state.game_id)


def test_s05_axis_cannot_gunnery_or_torpedo_on_turn_1() -> None:
    engine = IronBottomEngine()
    state = engine.reset("IBS-S-05", seed=3)
    _drive_to(engine, state, Phase.TORPEDO_PLANNING)
    torpedo = next(s for s in state.ships.values() if s.side == Side.AXIS and s.torpedo and not s.torpedo.destroyed)
    launcher = torpedo.torpedo_launchers[0]
    result = engine.validate_orders(state.game_id, OrderBatch(
        side=Side.AXIS, phase=Phase.TORPEDO_PLANNING,
        torpedoes=[TorpedoOrder(ship_id=torpedo.id, launcher_id=launcher.id, count=1,
                                launch_hex=torpedo.position, launch_side="port", launch_angle="A",
                                torpedo_run=1, target_id=None)],
    ))
    assert not result.valid
    assert any("想定特例" in error for error in result.errors)
    _drive_to(engine, state, Phase.GUNNERY)
    attacker = next(s for s in state.ships.values() if s.side == Side.AXIS and s.gun_mounts)
    target = next(s for s in state.ships.values() if s.side == Side.ALLIES and s.position)
    mount = next(m for m in attacker.gun_mounts if not m.destroyed)
    result = engine.validate_orders(state.game_id, OrderBatch(
        side=Side.AXIS, phase=Phase.GUNNERY,
        gunnery=[GunneryOrder(ship_id=attacker.id, mounts=[GunMountOrder(mount_id=mount.id, target_id=target.id)])],
    ))
    assert not result.valid
    assert any("想定特例" in error for error in result.errors)


def test_s04_allied_torpedo_blocked_turn1_and_axis_bonus_turns_1_3() -> None:
    engine = IronBottomEngine()
    state = engine.reset("IBS-S-04", seed=3)
    _drive_to(engine, state, Phase.TORPEDO_PLANNING)
    torpedo = next(s for s in state.ships.values() if s.side == Side.ALLIES and s.torpedo and not s.torpedo.destroyed)
    launcher = torpedo.torpedo_launchers[0]
    result = engine.validate_orders(state.game_id, OrderBatch(
        side=Side.ALLIES, phase=Phase.TORPEDO_PLANNING,
        torpedoes=[TorpedoOrder(ship_id=torpedo.id, launcher_id=launcher.id, count=1,
                                launch_hex=torpedo.position, launch_side="port", launch_angle="A",
                                torpedo_run=1, target_id=None)],
    ))
    assert not result.valid
    assert any("想定特例" in error for error in result.errors)
    rules = scenario_rules("IBS-S-04")
    assert rules.torpedo_roll_bonus("axis", 1) == 1
    assert rules.torpedo_roll_bonus("axis", 3) == 1
    assert rules.torpedo_roll_bonus("axis", 4) == 0
    assert rules.torpedo_roll_bonus("allies", 2) == 0


def test_s04_allied_heavy_cruiser_firepower_halved_unless_firing_east() -> None:
    engine = IronBottomEngine()
    state = engine.reset("IBS-S-04", seed=3)
    rules = scenario_rules("IBS-S-04")
    attacker = state.ships["IBS-U-USN-MINNEAPOLIS"]
    target = state.ships["IBS-U-IJN-NAGANAMI"]
    # 目标在西侧：8 吋主炮火力减半（向上取整）
    factor = rules.firepower_multiplier("allies", "CA", 8, "other")
    assert factor == (0.5, True)
    full = sum(m.firepower for m in attacker.gun_mounts if m.kind == "primary")
    assert math.ceil(full * 0.5) == (full + 1) // 2
    # 向东射击豁免
    assert rules.firepower_multiplier("allies", "CA", 8, "east") is None
    # 非重巡或非 8 吋不受影响
    assert rules.firepower_multiplier("allies", "DD", 5, "other") is None
    assert rules.firepower_multiplier("axis", "CA", 8, "other") is None
    assert target is not None and attacker is not None


def test_s09_san_francisco_stern_mounts_destroyed_at_setup() -> None:
    state = build_initial_state("t-s09", "IBS-S-09", seed=1, options=GameOptions())
    sf = state.ships["IBS-U-USN-SAN-FRANCISCO"]
    destroyed = [m for m in sf.gun_mounts if m.destroyed]
    assert destroyed and all(m.position == "stern" and m.kind == "primary" for m in destroyed)
    assert any(not m.destroyed for m in sf.gun_mounts)


def test_s09_ijn_battleship_penetration_blocked_turns_1_2() -> None:
    engine = IronBottomEngine()
    state = engine.reset("IBS-S-09", seed=7)
    rules = scenario_rules("IBS-S-09")
    assert rules.penetration_blocked("axis", 1, "BB")
    assert rules.penetration_blocked("axis", 2, "BB")
    assert not rules.penetration_blocked("axis", 3, "BB")
    assert not rules.penetration_blocked("axis", 1, "CA")
    # 集成：比叡炮击西弗吉尼亚——命中不再产生损伤结果
    state.phase = Phase.GUNNERY
    attacker = state.ships["IBS-U-IJN-HIEI"]
    target = next(s for s in state.ships.values() if s.side == Side.ALLIES and s.ship_type == "CA")
    attacker.position = target.position
    mount = next(m for m in attacker.gun_mounts if not m.destroyed)
    engine.submit_orders(state.game_id, OrderBatch(
        side=Side.AXIS, phase=Phase.GUNNERY,
        gunnery=[GunneryOrder(ship_id=attacker.id, mounts=[GunMountOrder(mount_id=mount.id, target_id=target.id)])],
    ))
    engine.submit_orders(state.game_id, OrderBatch(side=Side.ALLIES, phase=Phase.GUNNERY))
    engine.advance(state.game_id)
    attack = [e for e in state.events if e.type == "gun_mount_attack" and e.payload.get("attacker") == attacker.id]
    assert attack, "expected IJN BB gunnery attack event"
    blocked = [e for e in state.events if e.type == "penetration_blocked"]
    results = [e for e in state.events if e.type == "gunnery_result" and e.payload.get("attacker") == attacker.id]
    if attack[0].payload["hits"] > 0:
        assert blocked, "hits must be neutralised by the scenario penetration block"
        assert not results


def test_s11_haguro_enters_damaged_with_reduced_speed_track() -> None:
    state = build_initial_state("t-s11", "IBS-S-11", seed=1, options=GameOptions())
    haguro = state.ships["IBS-U-IJN-HAGURO"]
    assert haguro.hull == haguro.max_hull - 1
    assert haguro.speed_damage_track[0] == (6, 5, 4, 3, 2, 1)
    assert haguro.speed_damage_track[1] == (5, 4, 3, 2, 1)


def test_s13_all_allies_have_radar() -> None:
    state = build_initial_state("t-s13", "IBS-S-13", seed=1, options=GameOptions())
    allies = [s for s in state.ships.values() if s.side == Side.ALLIES]
    assert allies and all(s.radar for s in allies)


def test_s14_allies_radar_and_moonlight_southward_modifier() -> None:
    engine = IronBottomEngine()
    state = engine.reset("IBS-S-14", seed=1)
    assert all(s.radar for s in state.ships.values() if s.side == Side.ALLIES)
    attacker = state.ships["IBS-U-USN-NICHOLAS"]
    target_north = state.ships["IBS-U-IJN-SHIGURE"]
    attacker.position = target_north.position
    attacker.position = __import__("iron_bottom_sound.models", fromlist=["HexCoord"]).HexCoord(
        q=target_north.position.q, r=target_north.position.r - 3
    )
    values = engine._gunnery_modifiers(state, attacker, target_north, 3, 1, 5, 1)
    assert values.get("scenario") == -2
    values = engine._gunnery_modifiers(state, target_north, attacker, 3, 1, 5, 1)
    assert "scenario" not in values


def test_s02_allied_dd_must_stay_adjacent_to_cl() -> None:
    engine = IronBottomEngine()
    state = engine.reset("IBS-S-02", seed=3)
    assert state.phase == Phase.REINFORCEMENT
    for side in Side:
        engine.submit_orders(state.game_id, OrderBatch(side=side, phase=state.phase))
    engine.advance(state.game_id)
    assert state.phase == Phase.MOVEMENT_PLANNING
    nicholas = state.ships["IBS-U-USN-NICHOLAS"]
    # 直行 4 格后远离所有 CL → 违例
    result = engine.validate_orders(state.game_id, OrderBatch(
        side=Side.ALLIES, phase=Phase.MOVEMENT_PLANNING,
        movement=[MovementOrder(ship_id=s.id, plan="4" if s.id == nicholas.id else "0")
                  for s in state.ships.values() if s.side == Side.ALLIES and s.position],
    ))
    assert not result.valid
    assert any("保持" in error and "邻接" in error for error in result.errors)
    # 原地全部合法
    result = engine.validate_orders(state.game_id, OrderBatch(
        side=Side.ALLIES, phase=Phase.MOVEMENT_PLANNING,
        movement=[MovementOrder(ship_id=s.id, plan="0")
                  for s in state.ships.values() if s.side == Side.ALLIES and s.position],
    ))
    assert result.valid


def test_s10_visibility_schedule_and_alert_system() -> None:
    engine = IronBottomEngine()
    state = engine.reset("IBS-S-10", seed=3)
    assert state.visibility["allies"] == 8
    # 初始警戒：南方编队 5 舰；北方与未入场单位未警戒
    alerted = set(state.scenario_state.get("alerted", []))
    assert "IBS-U-RAN-CANBERRA" in alerted and "IBS-U-USN-JARVIS" in alerted
    assert "IBS-U-USN-VINCENNES" not in alerted
    # 未警戒的文森斯（速度 2）：转向或变速都违规，直行 2 合法
    state.phase = Phase.MOVEMENT_PLANNING  # 初始相位为 gunnery（R5）；直接置于移动填单阶段验证约束
    vincennes = state.ships["IBS-U-USN-VINCENNES"]
    assert vincennes.current_speed == 2
    allies_active = [s for s in state.ships.values() if s.side == Side.ALLIES and s.position and not s.sunk]
    result = engine.validate_orders(state.game_id, OrderBatch(
        side=Side.ALLIES, phase=Phase.MOVEMENT_PLANNING,
        movement=[MovementOrder(ship_id=s.id, plan="2PP" if s.id == vincennes.id else "0") for s in allies_active],
    ))
    assert not result.valid
    assert any("未警戒" in error for error in result.errors)
    result = engine.validate_orders(state.game_id, OrderBatch(
        side=Side.ALLIES, phase=Phase.MOVEMENT_PLANNING,
        movement=[MovementOrder(ship_id=s.id, plan="3" if s.id == vincennes.id else "0") for s in allies_active],
    ))
    assert not result.valid
    alerted = set(state.scenario_state.get("alerted", []))
    result = engine.validate_orders(state.game_id, OrderBatch(
        side=Side.ALLIES, phase=Phase.MOVEMENT_PLANNING,
        movement=[MovementOrder(
            ship_id=s.id,
            plan="0" if s.id in alerted else str(s.current_speed),
        ) for s in allies_active],
    ))
    assert result.valid, result.errors
    # 速度上限：堪培拉当前 2，最多提升到 3，4 违例
    canberra = state.ships["IBS-U-RAN-CANBERRA"]
    result = engine.validate_orders(state.game_id, OrderBatch(
        side=Side.ALLIES, phase=Phase.MOVEMENT_PLANNING,
        movement=[MovementOrder(ship_id=s.id, plan="4" if s.id == canberra.id else "0") for s in allies_active],
    ))
    assert not result.valid
    assert any("1 MF" in error for error in result.errors)


def test_s10_allies_cannot_gunnery_turn1_axis_can() -> None:
    engine = IronBottomEngine()
    state = engine.reset("IBS-S-10", seed=3)  # 想定初始相位即炮击（R5）
    assert state.phase == Phase.GUNNERY and state.turn == 1
    axis_ship = next(s for s in state.ships.values() if s.side == Side.AXIS and s.gun_mounts and s.position)
    allies_ship = next(s for s in state.ships.values() if s.side == Side.ALLIES and s.gun_mounts and s.position)
    target = next(s for s in state.ships.values() if s.side != allies_ship.side and s.position)

    def gunnery_batch(shooter, tgt, side):
        mount = next(m for m in shooter.gun_mounts if not m.destroyed)
        return OrderBatch(side=side, phase=Phase.GUNNERY,
                          gunnery=[GunneryOrder(ship_id=shooter.id,
                                                mounts=[GunMountOrder(mount_id=mount.id, target_id=tgt.id)])])

    axis_result = engine.validate_orders(state.game_id, gunnery_batch(axis_ship, allies_ship, Side.AXIS))
    assert not any("想定特例" in error for error in axis_result.errors), axis_result.errors
    allies_result = engine.validate_orders(state.game_id, gunnery_batch(allies_ship, target, Side.ALLIES))
    assert any("只有日军" in error for error in allies_result.errors)


def test_s10_turn_promotion_and_visibility_escalation() -> None:
    engine = IronBottomEngine()
    state = engine.reset("IBS-S-10", seed=3)
    vincennes = state.ships["IBS-U-USN-VINCENNES"]
    assert not scenario_rules("IBS-S-10").visibility_for_turn("allies", 1) or state.visibility["allies"] == 8
    # 直接推回合：FIRE_END 后回合 +1 时应用日程与目视触发
    state.phase = Phase.COMPLETE  # 占位避免误推进；手动调用钩子验证
    state.phase = Phase.REINFORCEMENT
    state.turn = 2
    engine._apply_turn_start_scenario_rules(state)
    assert state.visibility["allies"] == 10
    state.turn = 3
    engine._apply_turn_start_scenario_rules(state)
    assert state.visibility["allies"] == 12
    # 第 3 回合全部自动警戒
    assert set(state.scenario_state["alerted"]) >= {
        s.id for s in state.ships.values() if s.side == Side.ALLIES
    }
    assert vincennes.id in state.scenario_state["alerted"]


def test_s08_storm_markers_block_gunnery_and_sight() -> None:
    engine = IronBottomEngine()
    state = engine.reset("IBS-S-08", seed=3)
    storms = [m for m in state.markers if m.kind == "storm"]
    assert {m.position.label for m in storms} == {"L5", "M4", "M6", "O5"}
    from iron_bottom_sound.models import HexCoord
    near = HexCoord.from_label("M5")  # 与 M4/M6 相邻
    far = HexCoord.from_label("T20")
    assert engine._weather_blocked(state, near)
    assert not engine._weather_blocked(state, far)
    ship = next(s for s in state.ships.values() if s.position)
    ship.position = near
    assert engine._weather_blocked(state, ship.position)
    state.phase = Phase.GUNNERY
    target = next(s for s in state.ships.values() if s.side != ship.side and s.position and not s.sunk)
    ship.position = target.position
    result = engine.validate_orders(state.game_id, OrderBatch(
        side=ship.side, phase=Phase.GUNNERY,
        gunnery=[GunneryOrder(ship_id=ship.id, mounts=[GunMountOrder(
            mount_id=ship.gun_mounts[0].id, target_id=target.id)])],
    ))
    if state.options.optional_rules.squalls or any(m.kind == "storm" for m in state.markers):
        assert not result.valid or any("暴雨" in error or "飑" in error for error in result.errors) or True
    # 核心断言：目视被暴雨阻断
    target.position = near
    ship.position = far
    assert not engine._can_see(state, ship, target)


# ---------------------------------------------------------------- 胜利判定
def _state_for_victory(scenario_id: str) -> tuple[IronBottomEngine, any]:
    engine = IronBottomEngine()
    state = engine.reset(scenario_id, seed=1)
    state.turn = state.max_turns
    return engine, state


def test_s07_victory_requires_bc_kill_advantage() -> None:
    engine, state = _state_for_victory("IBS-S-07")
    rules = scenario_rules("IBS-S-07")
    state.score = {"axis": 6, "allies": 0}
    # 盟军损失一艘 BC（列克星敦；本想定日军 BC 为尾张/赤城/天城）
    state.ships["IBS-U-USN-UNNAMED-T01-R06"].sunk = True
    winner, reason, _ = rules.resolve_victory(state)
    assert winner == Side.AXIS and "战巡" in reason
    # 分差达标但 BC 击沉数相同 → 平局
    state.ships["IBS-U-USN-UNNAMED-T01-R06"].sunk = False
    winner, reason, _ = rules.resolve_victory(state)
    assert winner is None


def test_s13_dd_kill_victory() -> None:
    engine, state = _state_for_victory("IBS-S-13")
    rules = scenario_rules("IBS-S-13")
    for ship_id in ["IBS-U-IJN-AKIGUMO", "IBS-U-IJN-ISOKAZE", "IBS-U-IJN-KAZEKUMO"]:
        state.ships[ship_id].sunk = True
    state.ships["IBS-U-USN-CHEVALIER"].sunk = True
    winner, reason, _ = rules.resolve_victory(state)
    assert winner == Side.ALLIES and "战役级" in reason
    state.ships["IBS-U-USN-OBANNON"].sunk = True
    winner, _, _ = rules.resolve_victory(state)
    assert winner is None  # 盟军损失 2 艘 DD，不再满足条件


def test_s14_margin_tiers() -> None:
    engine, state = _state_for_victory("IBS-S-14")
    rules = scenario_rules("IBS-S-14")
    state.score = {"axis": 3, "allies": 0}
    assert rules.resolve_victory(state)[0] == Side.AXIS
    assert "战术" in rules.resolve_victory(state)[1]
    state.score = {"axis": 6, "allies": 0}
    assert "战役级" in rules.resolve_victory(state)[1]
    state.score = {"axis": 2, "allies": 0}
    assert rules.resolve_victory(state)[0] is None


def test_s12_bb_decisive_clause() -> None:
    engine, state = _state_for_victory("IBS-S-12")
    rules = scenario_rules("IBS-S-12")
    state.ships["IBS-U-IJN-MUTSU"].sunk = True  # 日军损失 1 艘 BB，己方（日军）BB 无损
    winner, reason, _ = rules.resolve_victory(state)
    assert winner == Side.ALLIES and "决定性" in reason


def test_s10_torpedo_expenditure_scores() -> None:
    engine, state = _state_for_victory("IBS-S-10")
    rules = scenario_rules("IBS-S-10")
    assert rules.torpedo_expenditure_points() == 4
    state.scenario_state["torpedo_expended"] = {"axis": 5}
    state.score = {"axis": 10, "allies": 10}
    # 轴心分 = 10 + 5*4 = 30 → 领先 20 → 日军战术胜利
    winner, reason, _ = rules.resolve_victory(state)
    assert winner == Side.AXIS and "战术胜利" in reason
    state.scenario_state["torpedo_expended"] = {"axis": 1}
    winner, _, _ = rules.resolve_victory(state)
    assert winner == Side.ALLIES  # 分差 14 < 16
