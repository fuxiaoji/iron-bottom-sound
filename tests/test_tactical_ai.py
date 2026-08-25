"""TacticalCommander（简单战术 AI）与引擎新只读辅助方法。

引擎新方法：expected_gunnery_hits / ship_gun_pressure / movement_path /
共享转移枚举器 _movement_expand；以及同格（distance=0）射程表钳制修复。

AI 各阶段：移动（规避敌方热力 + 抢占己方火力 + 射程外接近）、炮击（采纳
gunnery_assist 齐射推荐）、鱼雷（近距且高置信度才发射）。集成：双想定
S-01/S-03 tactical 对 deterministic / 对 tactical 自动终局且可复现。
"""

import json
import os
import random
import subprocess
import sys
from dataclasses import replace
from pathlib import Path

import pytest

from iron_bottom_sound.engine import D66_VALUES, IronBottomEngine, ORDER_PHASES, d66_adjust
from iron_bottom_sound.llm import DeterministicCommander, LLMPlayerSession
from iron_bottom_sound.match import run_match
from iron_bottom_sound.models import HexCoord, Phase, Side, TorpedoOrder
from iron_bottom_sound import tactical
from iron_bottom_sound.tactical import APPROACH_RANGE, TacticalCommander


# --------------------------------------------------------------------------- helpers

def session_for(name: str, side: Side) -> LLMPlayerSession:
    commander = TacticalCommander() if name == "tactical" else DeterministicCommander()
    return LLMPlayerSession(side, commander)


def drive_to(
    engine: IronBottomEngine, game_id: str, sessions: dict[Side, LLMPlayerSession],
    target_phase: Phase, max_steps: int = 40,
):
    """用给定指挥官逐阶段推进对局直到目标阶段（或 COMPLETE 抛错）。"""
    state = engine.get(game_id)
    for _ in range(max_steps):
        if state.phase == target_phase:
            return state
        if state.phase == Phase.COMPLETE:
            raise AssertionError(f"reached COMPLETE before {target_phase}")
        if state.phase in ORDER_PHASES:
            for side in (Side.AXIS, Side.ALLIES):
                batch = sessions[side].choose_orders(engine, game_id)
                result = engine.submit_orders(game_id, batch)
                assert result.valid, result.errors
        engine.advance(game_id)
    raise AssertionError(f"did not reach {target_phase}")


def axis_ships(state):
    return [ship for ship in state.ships.values() if ship.side == Side.AXIS and ship.position]


def far_hex_from(positions, minimum: int = 6) -> HexCoord:
    """取离所有给定格都超过 minimum 的合法角格（用于制造不可见敌舰）。"""
    corners = [
        HexCoord(q=0, r=0), HexCoord(q=0, r=26), HexCoord(q=16, r=-8),
        HexCoord(q=16, r=18), HexCoord(q=33, r=-16), HexCoord(q=33, r=10),
    ]
    return max(corners, key=lambda cell: min(cell.distance(position) for position in positions))


# ===========================================================================
# 引擎：expected_gunnery_hits
# ===========================================================================

def brute_expected_hits(engine: IronBottomEngine, firepower: int, distance: int) -> float:
    """36 档 D66 穷举的期望命中（独立复算，不含 target_speed 项以便对照）。"""
    return sum(
        engine.rules.hit_count(
            firepower,
            d66_adjust(roll, engine.rules.range_modifier("gunnery", distance)),
        )
        for roll in D66_VALUES
    ) / len(D66_VALUES)


def test_expected_gunnery_hits_matches_brute_force_exhaustion() -> None:
    engine = IronBottomEngine()
    for firepower in (3, 6, 9, 15):
        for distance in (1, 2, 5, 8, 12, 18, 24):
            assert engine.expected_gunnery_hits(firepower, distance) == pytest.approx(
                brute_expected_hits(engine, firepower, distance)
            )


def test_expected_gunnery_hits_routes_distance_zero_through_nearest_bucket() -> None:
    engine = IronBottomEngine()
    # 同格（distance=0）按最近射程行处理，与 distance=1 一致。
    assert engine.expected_gunnery_hits(15, 0) == pytest.approx(engine.expected_gunnery_hits(15, 1))


# ===========================================================================
# 引擎：ship_gun_pressure
# ===========================================================================

def isolated_ship_and_target(state, side: Side, target_side: Side):
    """只留一艘本舰与一艘可见敌舰（其余出图），返回 (本舰, 敌舰)。"""
    ship = next(s for s in state.ships.values() if s.side == side and s.position)
    target = next(s for s in state.ships.values() if s.side == target_side and s.position)
    for other in state.ships.values():
        if other is not ship and other is not target and other.side == side:
            other.position = None
    return ship, target


def independent_pressure(engine: IronBottomEngine, ship, position: HexCoord, heading: int, target: HexCoord) -> float:
    """舰在假想位/航向下对单目标格的压力（引擎公式的独立复算）。"""
    total = 0.0
    for mount in ship.gun_mounts:
        if mount.destroyed or target == position:
            continue
        if IronBottomEngine._relative_aspect(position, heading, target) not in mount.arcs:
            continue
        total += mount.firepower * engine.expected_gunnery_hits(mount.firepower, position.distance(target))
    return total


def test_ship_gun_pressure_matches_independent_recompute() -> None:
    engine = IronBottomEngine()
    state = engine.reset("IBS-S-03", seed=3, game_id="pressure-recompute")
    ship, target = isolated_ship_and_target(state, Side.AXIS, Side.ALLIES)
    for position, heading in (
        (ship.position, ship.heading),
        (ship.position.neighbor(ship.heading), (ship.heading % 6) + 1),
    ):
        actual = engine.ship_gun_pressure(
            state, ship, position=position, heading=heading,
            target_hexes=[target.position],
        )
        assert actual == pytest.approx(independent_pressure(engine, ship, position, heading, target.position))


def test_ship_gun_pressure_default_uses_only_visible_enemies() -> None:
    engine = IronBottomEngine()
    state = engine.reset("IBS-S-03", seed=3, game_id="pressure-visible")
    # 只留一艘本舰与一艘敌舰
    ship = next(s for s in state.ships.values() if s.side == Side.AXIS and s.position)
    for other in state.ships.values():
        if other.side == Side.AXIS and other is not ship:
            other.position = None
    enemy = next(s for s in state.ships.values() if s.side == Side.ALLIES and s.position)
    for other in state.ships.values():
        if other.side == Side.ALLIES and other is not enemy:
            other.position = None
    # 把唯一敌舰放到超视距 → 默认 target_hexes 排除它（压力归零）
    far = far_hex_from([ship.position])
    assert far.distance(ship.position) > 4
    enemy.position = far
    assert engine._visible_to(state, enemy, Side.AXIS, [ship.position]) is False
    assert engine.ship_gun_pressure(state, ship) == 0.0
    # 显式塞回原可见位则压力恢复非零（证明默认过滤只来自可见性，不是恒零）
    enemy.position = ship.position.neighbor(ship.heading)
    assert engine.ship_gun_pressure(state, ship, target_hexes=[enemy.position]) > 0.0


def test_ship_gun_pressure_excludes_destroyed_mounts() -> None:
    engine = IronBottomEngine()
    state = engine.reset("IBS-S-03", seed=3, game_id="pressure-destroyed")
    ship, target = isolated_ship_and_target(state, Side.AXIS, Side.ALLIES)
    mount = ship.gun_mounts[0]
    before = engine.ship_gun_pressure(state, ship, target_hexes=[target.position])
    mount.destroyed = True
    after = engine.ship_gun_pressure(state, ship, target_hexes=[target.position])
    contribution = 0.0
    if (
        target.position != ship.position
        and IronBottomEngine._relative_aspect(ship.position, ship.heading, target.position) in mount.arcs
    ):
        contribution = mount.firepower * engine.expected_gunnery_hits(mount.firepower, ship.position.distance(target.position))
    assert (before - after) == pytest.approx(contribution)


# ===========================================================================
# 引擎：movement_path（与 movement_candidates 共享状态机）
# ===========================================================================

def test_movement_path_valid_for_every_candidate_hex() -> None:
    engine = IronBottomEngine()
    state = engine.reset("IBS-S-03", seed=7, game_id="path-candidates")
    for ship in axis_ships(state):
        candidates = engine.movement_candidates(state, ship)["reachable"]
        assert candidates
        for entry in candidates:
            target = HexCoord(q=entry["hex"]["q"], r=entry["hex"]["r"])
            heading = entry["final_headings"][0]
            result = engine.movement_path(state, ship, target, heading)
            assert result["valid"], f"{ship.id} -> {target.label}@{heading}: {result['reason']}"
            assert result["end_hex"] == target.label
            assert result["end_heading"] == heading
            assert result["cost"] == entry["cost"]
            preview = engine.movement_preview(state, ship, plan=result["plan"])
            assert preview["commitable"] is True
            assert preview["current_label"] == target.label


def test_movement_path_stationary_returns_zero_when_legal() -> None:
    engine = IronBottomEngine()
    state = engine.reset("IBS-S-03", seed=7, game_id="path-stationary")
    ship = axis_ships(state)[0]
    result = engine.movement_path(state, ship, ship.position, ship.heading)
    assert result["valid"]
    assert result["plan"] == "0"
    assert result["cost"] == 0


def test_movement_path_respects_forced_speed_and_circle() -> None:
    engine = IronBottomEngine()
    state = engine.reset("IBS-S-03", seed=7, game_id="path-forced")

    ship = axis_ships(state)[0]
    ship.forced_straight_turns = 1
    ship.forced_speed = 2
    candidates = engine.movement_candidates(state, ship)["reachable"]
    assert (engine.movement_candidates(state, ship)["min_cost"],
            engine.movement_candidates(state, ship)["max_cost"]) == (2, 2)
    for entry in candidates:
        result = engine.movement_path(state, ship, HexCoord(q=entry["hex"]["q"], r=entry["hex"]["r"]))
        assert result["valid"]
        assert result["cost"] == 2
        assert engine.movement_preview(state, ship, plan=result["plan"])["commitable"]

    circled = axis_ships(state)[1]
    circled.forced_circle_turns = 1
    circled.forced_turn_side = "port"
    circle_candidates = engine.movement_candidates(state, circled)["reachable"]
    assert circle_candidates
    for entry in circle_candidates:
        result = engine.movement_path(state, circled, HexCoord(q=entry["hex"]["q"], r=entry["hex"]["r"]))
        assert result["valid"], result["reason"]
        assert engine.movement_preview(state, circled, plan=result["plan"])["commitable"]


def test_movement_path_unreachable_heading_is_invalid() -> None:
    engine = IronBottomEngine()
    state = engine.reset("IBS-S-03", seed=7, game_id="path-bad-heading")
    ship = axis_ships(state)[0]
    entry = engine.movement_candidates(state, ship)["reachable"][1]
    target = HexCoord(q=entry["hex"]["q"], r=entry["hex"]["r"])
    legal_headings = set(entry["final_headings"])
    bad_heading = next(h for h in range(1, 7) if h not in legal_headings)
    result = engine.movement_path(state, ship, target, bad_heading)
    assert result["valid"] is False


def test_same_hex_distance_zero_uses_nearest_range_bucket() -> None:
    engine = IronBottomEngine()
    rules = engine.rules
    # 射程表下限钳到 1（同格=最近射程行）
    rows = rules.modifiers["range_modifier"]["gunnery"]
    assert rules._range_value(rows, 0)["value"] == rules._range_value(rows, 1)["value"]
    assert rules.range_modifier("gunnery", 0) == rules.range_modifier("gunnery", 1)
    # 纵射修正表同样钳制
    long_rows = rules.modifiers["longitudinal_modifier"]
    assert rules._range_value(long_rows, 0)["value"] == rules._range_value(long_rows, 1)["value"]
    # 穿深表距离 0 按最近档
    assert rules.penetration("UK", 15.0, 0) == rules.penetration("UK", 15.0, 1)
    assert rules.penetration("UK", 15.0, 0) > 0


# ===========================================================================
# AI：阶段分派与继承
# ===========================================================================

def test_contact_setup_and_reinforcement_inherited_from_deterministic() -> None:
    # 未覆写：直接继承父类实现（逐引用相同），避免策略分叉
    assert TacticalCommander._contact_setup is DeterministicCommander._contact_setup
    assert TacticalCommander._reinforcements is DeterministicCommander._reinforcements
    # 功能级：S-03 开场 REINFORCEMENT 阶段两指挥官产出一致（均为空）
    engine = IronBottomEngine()
    state = engine.reset("IBS-S-03", seed=1, game_id="inherit-reinf")
    assert state.phase == Phase.REINFORCEMENT
    deterministic = DeterministicCommander().choose_plan(engine, state.game_id, Side.AXIS)[1]
    tactical_plan = TacticalCommander().choose_plan(engine, state.game_id, Side.AXIS)[1]
    assert tactical_plan == deterministic


# ===========================================================================
# AI：移动
# ===========================================================================

def movement_planning_state(seed: int = 1) -> tuple[IronBottomEngine, object]:
    engine = IronBottomEngine()
    state = engine.reset("IBS-S-03", seed=seed, game_id=f"move-plan-{seed}")
    sessions = {Side.AXIS: session_for("tactical", Side.AXIS), Side.ALLIES: session_for("tactical", Side.ALLIES)}
    return engine, drive_to(engine, state.game_id, sessions, Phase.MOVEMENT_PLANNING)


def test_movement_orders_cover_all_active_ships_and_validate() -> None:
    engine, state = movement_planning_state()
    plan, batch, _audits = TacticalCommander().choose_plan(engine, state.game_id, Side.AXIS)
    submitted = {order.ship_id for order in batch.movement}
    expected = {ship.id for ship in axis_ships(state)}
    assert submitted == expected
    assert plan.turn == state.turn and plan.phase == Phase.MOVEMENT_PLANNING
    assert engine.validate_orders(state.game_id, batch).valid


def empty_context(threat: float = 0.0, pred_hexes: list[HexCoord] | None = None,
                  my_positions: list[HexCoord] | None = None) -> tactical._MovementContext:
    """构造威胁项可控、其余项为空的 `_MovementContext`（供打分单元测试隔离各项）。"""
    return tactical._MovementContext(
        enemies=[],
        pred_by_id={},
        pred_hexes=pred_hexes or [],
        enemy_threat_of=lambda h: threat,
        my_positions=my_positions or [],
    )


def test_movement_scoring_prefers_lower_enemy_threat() -> None:
    """敌（预测落点）威胁越小分越高（"去敌方火力热力图小处"，火力项持平等价）。"""
    engine, state = movement_planning_state(3)
    ship = axis_ships(state)[0]
    hexc = ship.position
    scorer = TacticalCommander()
    hot = scorer._score_hex(engine, state, ship, hexc, ship.heading, empty_context(1.0), 0.5, 1.0, 1.0, 1.0)
    cool = scorer._score_hex(engine, state, ship, hexc, ship.heading, empty_context(0.0), 0.5, 1.0, 0.0, 1.0)
    assert cool > hot


def test_movement_scoring_prefers_higher_fire_pressure() -> None:
    """己方火力压力越大分越高（"保持敌方处于我方火力热力图大处"）。"""
    engine, state = movement_planning_state(3)
    ship = axis_ships(state)[0]
    hexc = ship.position
    scorer = TacticalCommander()
    ctx = empty_context(0.0)
    low = scorer._score_hex(engine, state, ship, hexc, ship.heading, ctx, 0.2, 1.0, 0.0, 1.0)
    high = scorer._score_hex(engine, state, ship, hexc, ship.heading, ctx, 1.0, 1.0, 0.0, 1.0)
    assert high > low


def test_movement_scoring_approaches_enemy_outside_gun_range() -> None:
    """射程外（>APPROACH_RANGE）时，更接近敌（预测落点）的候选得分更高。"""
    engine, state = movement_planning_state(3)
    ship = axis_ships(state)[0]
    enemy = next(s for s in state.ships.values() if s.side == Side.ALLIES and s.position)
    # 把敌舰放到 > APPROACH_RANGE 的距离
    start = ship.position
    probe = start
    for _ in range(APPROACH_RANGE + 2):
        probe = probe.neighbor(ship.heading)
    enemy.position = probe
    assert start.distance(enemy.position) > APPROACH_RANGE
    scorer = TacticalCommander()
    ctx = empty_context(0.0, pred_hexes=[enemy.position])
    near = scorer._score_hex(engine, state, ship, enemy.position, ship.heading, ctx, 0.0, 1.0, 0.0, 1.0)
    far = scorer._score_hex(engine, state, ship, start, ship.heading, ctx, 0.0, 1.0, 0.0, 1.0)
    assert near > far


def legacy_profile() -> tactical.TacticalProfile:
    """新态势感知/随机权重全 0、温度 0：还原"基础打分"（规避威胁+火力+接近+编队）语义。"""
    return tactical.PROFILES["balanced"].model_copy(update={
        "w_retreat": 0.0, "w_protect_own": 0.0, "w_vp": 0.0,
        "w_finish": 0.0, "w_self_status": 0.0, "temperature": 0.0,
    })


def test_movement_net_reduces_predicted_threat_across_fleet() -> None:
    """聚合断言（基础打分语义，隔离新价值/退避项）：对抗评分下所选终点"敌预测落点
    威胁"均值不高于起点均值（每舰追赶火力压力可能局部升高，但整体应净避威胁）。"""
    deltas: list[float] = []
    for seed in range(1, 6):
        engine, state = movement_planning_state(seed)
        obs = engine.observe(state.game_id, Side.AXIS)
        enemies = [ship for ship in obs.ships if ship.side != Side.AXIS and not ship.sunk and ship.position]
        commander = TacticalCommander(profile=legacy_profile())
        ctx = commander._build_movement_context(engine, state, Side.AXIS, enemies)
        for ship in axis_ships(state):
            order = commander._movement_order_for(engine, state, ship, ctx)
            preview = engine.movement_preview(state, ship, plan=order.plan)
            start = ctx.enemy_threat_of(ship.position)
            end = ctx.enemy_threat_of(HexCoord(q=preview["current_hex"]["q"], r=preview["current_hex"]["r"]))
            deltas.append(end - start)
    assert sum(deltas) / len(deltas) <= 0


def test_fallback_movement_legal_when_zero_plan_illegal() -> None:
    """forced_speed>0 / forced_circle 下 "0" 非法，回退链必须产出合法计划。"""
    engine, state = movement_planning_state()
    ship = axis_ships(state)[0]
    ship.forced_straight_turns = 1
    ship.forced_speed = 2
    assert engine.movement_preview(state, ship, plan="0")["commitable"] is False
    order = TacticalCommander()._fallback_movement(engine, state, ship)
    preview = engine.movement_preview(state, ship, plan=order.plan)
    assert preview["commitable"] is True
    assert preview["cost"] == 2


def test_deterministic_stationary_fallback_legal_for_forced_ships() -> None:
    """基线指挥官（教程/测试对手）在 forced 损伤下也要产出合法计划，不能再硬发 "0"。"""
    engine, state = movement_planning_state()
    # forced_speed>0：直行固定成本
    straight = axis_ships(state)[0]
    straight.forced_straight_turns = 1
    straight.forced_speed = 2
    plan = DeterministicCommander._stationary_plan(engine, state.game_id, straight.id)
    assert engine.movement_preview(state, straight, plan=plan)["commitable"] is True
    assert plan != "0"
    # forced_circle：必须含 60° 转向
    circled = axis_ships(state)[1]
    circled.forced_circle_turns = 1
    circled.forced_turn_side = "port"
    plan = DeterministicCommander._stationary_plan(engine, state.game_id, circled.id)
    assert engine.movement_preview(state, circled, plan=plan)["commitable"] is True
    assert plan != "0"


# ===========================================================================
# AI：炮击
# ===========================================================================

def test_gunnery_adopts_recommendations_and_validates() -> None:
    """AI 炮击目标必须来自该舰引擎合法候选集，炮位与该目标一致，订单合法。"""
    engine = IronBottomEngine()
    state = engine.reset("IBS-S-03", seed=1, game_id="gunnery-adopt")
    sessions = {Side.AXIS: session_for("tactical", Side.AXIS), Side.ALLIES: session_for("deterministic", Side.ALLIES)}
    state = drive_to(engine, state.game_id, sessions, Phase.GUNNERY)
    plan, batch, _audits = TacticalCommander().choose_plan(engine, state.game_id, Side.AXIS)
    options = engine.gunnery_target_options(state, Side.AXIS)
    by_ship = {cand["ship_id"]: cand for cand in options}
    assert batch.gunnery
    for order in batch.gunnery:
        cand = by_ship[order.ship_id]
        target = next(item for item in cand["targets"] if item["target_id"] == order.primary_target)
        assert [mount.mount_id for mount in order.mounts] == target["mount_ids"]
    assert engine.validate_orders(state.game_id, batch).valid
    assert plan.phase == Phase.GUNNERY


def test_gunnery_ibs_s01_axis_turn1_has_no_orders() -> None:
    """IBS-S-01 日军第 1 回合禁射由引擎 blocked 自动覆盖，AI 不产出炮击订单。"""
    engine = IronBottomEngine()
    state = engine.reset("IBS-S-01", seed=1, game_id="gunnery-s01-blocked")
    assert state.phase == Phase.GUNNERY and state.turn == 1
    plan, batch, _audits = TacticalCommander().choose_plan(engine, state.game_id, Side.AXIS)
    assert batch.gunnery == []
    assert engine.validate_orders(state.game_id, batch).valid


# ===========================================================================
# AI：鱼雷
# ===========================================================================

def torpedo_planning_state(seed: int = 1) -> tuple[IronBottomEngine, object]:
    engine = IronBottomEngine()
    state = engine.reset("IBS-S-03", seed=seed, game_id=f"torp-plan-{seed}")
    sessions = {Side.AXIS: session_for("tactical", Side.AXIS), Side.ALLIES: session_for("tactical", Side.ALLIES)}
    return engine, drive_to(engine, state.game_id, sessions, Phase.TORPEDO_PLANNING)


def qualifying_combos(engine: IronBottomEngine, state, side: Side, profile: tactical.TacticalProfile | None = None) -> list[dict]:
    """与 TacticalCommander 相同口径：最近可见敌舰 → 距离/置信度过滤的组合。"""
    profile = profile or tactical.PROFILES["balanced"]
    obs = engine.observe(state.game_id, side)
    own_pos = [s.position for s in obs.ships if s.side == side and not s.sunk and s.position]
    enemies = [s for s in obs.ships if s.side != side and not s.sunk and s.position]
    if not own_pos or not enemies:
        return []
    nearest = min(enemies, key=lambda enemy: min(enemy.position.distance(pos) for pos in own_pos))
    assist = engine.torpedo_assist(state, side, target_id=nearest.id)
    return [
        combo for combo in assist["combos"]
        if not combo["blocked_reason"]
        and combo["distance"] <= profile.torpedo_max_range
        and combo["expected_hits"] >= profile.torpedo_min_expected
    ]


def test_torpedo_adopts_qualifying_combos_matching_sealed_trajectory() -> None:
    engine, state = torpedo_planning_state()
    plan, batch, _audits = TacticalCommander().choose_plan(engine, state.game_id, Side.AXIS)
    combos = qualifying_combos(engine, state, Side.AXIS)
    assert combos  # 近距存在合格组合，AI 应发射
    by_key: dict[tuple[str, str], dict] = {}
    for combo in combos:  # 与 AI 一致：每 (舰, 发射器) 取排序后的首个组合
        by_key.setdefault((combo["ship_id"], combo["launcher_id"]), combo)
    assert batch.torpedoes, "应有鱼雷订单"
    assert len(batch.torpedoes) == len({(order.ship_id, order.launcher_id) for order in batch.torpedoes})
    sealed = engine.sealed_movement_trajectories(state, Side.AXIS)["trajectories"]
    track = {entry["ship_id"]: entry["trajectory"] for entry in sealed}
    for order in batch.torpedoes:
        combo = by_key[(order.ship_id, order.launcher_id)]
        assert order.count == combo["salvo_size"]
        assert order.bearing == combo["launch_heading"]
        # launch_hex 必须等于封存移动轨迹在 launch_at_mf 处的格（mf=0 即舰当前位置）
        if order.launch_at_mf == 0:
            assert order.launch_hex.label == state.ships[order.ship_id].position.label
        else:
            segment = next(
                item for item in track[order.ship_id]
                if item["mf"] == order.launch_at_mf
            )
            assert order.launch_hex.label == segment["label"]
    assert engine.validate_orders(state.game_id, batch).valid


def test_torpedo_threshold_gate_and_dedup_per_launcher() -> None:
    """鱼雷置信度阈值经 profile 生效（不再是模块常量）：阈值高到不可能满足时空。"""
    gate = TacticalCommander(
        profile=tactical.PROFILES["balanced"].model_copy(update={"torpedo_min_expected": 100.0})
    )
    engine, state = torpedo_planning_state()
    _plan, batch, _audits = gate.choose_plan(engine, state.game_id, Side.AXIS)
    assert batch.torpedoes == []


def test_torpedo_ibs_s01_axis_blocked_before_turn_4() -> None:
    """IBS-S-01 日军第 4 回合前禁射：第 2 回合鱼雷计划阶段轴心方无鱼雷订单。"""
    engine = IronBottomEngine()
    state = engine.reset("IBS-S-01", seed=1, game_id="torp-s01-blocked")
    sessions = {Side.AXIS: session_for("tactical", Side.AXIS), Side.ALLIES: session_for("deterministic", Side.ALLIES)}
    state = drive_to(engine, state.game_id, sessions, Phase.TORPEDO_PLANNING)
    assert state.turn < 4
    _plan, batch, _audits = TacticalCommander().choose_plan(engine, state.game_id, Side.AXIS)
    assert batch.torpedoes == []
    assert engine.validate_orders(state.game_id, batch).valid


# ===========================================================================
# 对抗评分（预测对手下一步）与风格 profile
# ===========================================================================

def test_predict_enemy_move_returns_valid_and_deterministic_candidate() -> None:
    """敌预测落点必须在敌可达 (格, 末航向) 内，且两次调用结果一致（确定性）。"""
    engine, state = movement_planning_state(3)
    obs = engine.observe(state.game_id, Side.AXIS)
    enemies = [ship for ship in obs.ships if ship.side != Side.AXIS and not ship.sunk and ship.position]
    assert enemies
    commander = TacticalCommander()
    for enemy in enemies:
        hexc, heading = commander._predict_enemy_move(engine, state, enemy, Side.AXIS)
        reachable = engine.movement_candidates(state, state.ships[enemy.id])["reachable"]
        assert any(
            HexCoord(q=entry["hex"]["q"], r=entry["hex"]["r"]) == hexc and heading in entry["final_headings"]
            for entry in reachable
        ), f"{enemy.id} 预测 {hexc.label}@{heading} 不在可达集"
        hexc2, heading2 = commander._predict_enemy_move(engine, state, enemy, Side.AXIS)
        assert (hexc, heading) == (hexc2, heading2)


def test_enemy_move_score_prefers_lower_my_heat() -> None:
    """敌视角打分镜像：敌规避"我方可视火力"（heat 项越小分越高）。"""
    engine, state = movement_planning_state(3)
    enemy = next(s for s in state.ships.values() if s.side == Side.ALLIES and s.position)
    scorer = TacticalCommander()
    hexc = enemy.position
    hot = scorer._enemy_move_score(enemy, hexc, enemy.heading, [], [], lambda h: 1.0, 1.0, 0.5, 1.0)
    cool = scorer._enemy_move_score(enemy, hexc, enemy.heading, [], [], lambda h: 0.0, 1.0, 0.5, 1.0)
    assert cool > hot


def test_public_copy_strips_hidden_damage_when_enabled() -> None:
    """隐藏损伤启用时敌预测副本剥离全部损伤派生约束；未启用时原样返回。"""
    engine = IronBottomEngine()
    state = engine.reset("IBS-S-03", seed=3, game_id="public-copy")
    ship = axis_ships(state)[0]
    ship.forced_straight_turns = 1
    ship.forced_speed = 2
    ship.gun_mounts[0].destroyed = True
    scorer = TacticalCommander()
    # 默认（hidden_damage=False）：真实状态直接复用
    assert scorer._public_copy(state, ship) is ship
    # 启用隐藏损伤：全部隐藏字段复位
    state.options.optional_rules.hidden_damage = True
    public = scorer._public_copy(state, ship)
    assert public.forced_straight_turns == 0 and public.forced_speed is None
    assert all(mount.destroyed is False for mount in public.gun_mounts)
    assert public is not ship


def test_formation_factor_prefers_ideal_spacing() -> None:
    """fleet profile：候选格与最近友舰距离落在理想间距时得分更高。"""
    fleet = TacticalCommander(profile=tactical.PROFILES["fleet"])
    ship_pos = HexCoord(q=5, r=5)
    own = [ship_pos, HexCoord(q=5, r=7)]  # 友舰在正南 2 格（fleet spacing 1-3 理想）
    d2 = HexCoord(q=5, r=7)
    d8 = HexCoord(q=5, r=13)
    assert fleet._formation_factor(ship_pos, d2, 3, own) > fleet._formation_factor(ship_pos, d8, 3, own)


def test_line_ahead_prefers_collinear_friend() -> None:
    """line profile：最近友舰在航向正前方 1-3 格同线时得分更高（长纵队）。"""
    line = TacticalCommander(profile=tactical.PROFILES["line"])
    ship_pos = HexCoord(q=5, r=5)
    friend = HexCoord(q=5, r=7)  # 正南 2 格（航向 3）
    own = [ship_pos, friend]
    on_line = HexCoord(q=5, r=6)   # 舰位正前 1 格，与友舰同线
    off_line = HexCoord(q=6, r=6)  # 斜侧（友舰距离 2，队形项相当）
    assert line._formation_factor(ship_pos, on_line, 3, own) > line._formation_factor(ship_pos, off_line, 3, own)


def test_profiles_produce_distinct_movement_plans() -> None:
    """不同风格 profile 在相同局况下应产生不同的移动计划（风格确实改变行为）。"""
    different = False
    for seed in (1, 3, 9):
        engine, state = movement_planning_state(seed)
        plans: dict[str, tuple[str, ...]] = {}
        for name in ("balanced", "cautious", "fleet"):
            commander = TacticalCommander(profile=tactical.PROFILES[name])
            _plan, batch, _audits = commander.choose_plan(engine, state.game_id, Side.AXIS)
            plans[name] = tuple(sorted(order.plan for order in batch.movement))
        if len(set(plans.values())) >= 2:
            different = True
            break
    assert different, "风格 profile 应在某些 seed 下产生不同移动计划"


# ===========================================================================
# 集成：AI 对 AI 自动终局
# ===========================================================================

def test_tactical_vs_deterministic_both_scenarios_both_directions() -> None:
    for scenario in ("IBS-S-03", "IBS-S-01"):
        for axis, allies in (("tactical", "deterministic"), ("deterministic", "tactical")):
            report, engine, sessions = run_match(scenario, axis=axis, allies=allies, seed=9)
            assert report.passed, report.failure_reason
            assert report.completed
            assert report.request_count <= 128
            assert report.fallback_count == 0
            assert engine.get(report.game_id).phase == Phase.COMPLETE
            assert sessions[Side.AXIS] is not sessions[Side.ALLIES]


def test_tactical_vs_tactical_completes_both_scenarios() -> None:
    for scenario in ("IBS-S-03", "IBS-S-01"):
        report, engine, _ = run_match(scenario, axis="tactical", allies="tactical", seed=9)
        assert report.passed, report.failure_reason
        assert report.completed
        assert engine.get(report.game_id).phase == Phase.COMPLETE


def test_tactical_match_is_deterministic_across_runs() -> None:
    def outcome(seed: int):
        report, engine, _ = run_match("IBS-S-03", axis="tactical", allies="deterministic", seed=seed)
        return (report.winner, engine.get(report.game_id).turn,
                report.request_count, report.axis_plan_count, report.allies_plan_count)
    assert outcome(5) == outcome(5)
    assert outcome(9) == outcome(9)


def test_match_profiles_finish_and_are_deterministic() -> None:
    """多 profile 对局（cautious vs fleet）能跑到终局且同 seed 两次结果一致。"""
    def outcome(seed: int):
        report, engine, _ = run_match(
            "IBS-S-03", axis="tactical", allies="tactical",
            axis_profile="cautious", allies_profile="fleet", seed=seed,
        )
        return (report.winner, report.completed, report.request_count,
                report.axis_plan_count, report.allies_plan_count)
    first = outcome(9)
    assert first[1] is True, "多 profile 对局应能完成"
    assert outcome(9) == first


# ===========================================================================
# 引擎确定性回归：碰撞检定顺序不能依赖字符串哈希
# ===========================================================================

_SUBPROCESS_DETERMINISM_SCRIPT = (
    "import json, sys\n"
    "sys.stdout.reconfigure(encoding='utf-8')\n"
    "from iron_bottom_sound.match import run_match\n"
    "report, engine, _ = run_match('IBS-S-03', axis='tactical', allies='tactical', seed=9)\n"
    "state = engine.get(report.game_id)\n"
    "checks = [\n"
    "    (ev.payload.get('ships'), ev.dice.raw)\n"
    "    for ev in state.events if ev.type == 'collision_check'\n"
    "]\n"
    "print(json.dumps({\n"
    "    'winner': report.winner, 'victory_reason': report.victory_reason,\n"
    "    'request_count': report.request_count, 'checks': checks,\n"
    "}, ensure_ascii=False))\n"
)
_REPO_ROOT = Path(__file__).resolve().parents[1]


def test_collision_resolution_is_deterministic_across_hash_seeds() -> None:
    """引擎碰撞检定顺序不能依赖字符串哈希。

    回归：碰撞组用 set[frozenset[str]] 迭代，顺序随 PYTHONHASHSEED 随机化 →
    骰子错配到不同碰撞 → 同 seed 跨进程战果分叉（实测 seed 2/8 一局
    “战术胜利/一艘德舰”、另一局“战略胜利/多艘德舰”）。修复后按组成员
    排序迭代，任意哈希种子下事件序列与战果必须一致。
    """
    def outcome(hashseed: str):
        env = dict(os.environ, PYTHONHASHSEED=hashseed)
        proc = subprocess.run(
            [sys.executable, "-c", _SUBPROCESS_DETERMINISM_SCRIPT],
            cwd=_REPO_ROOT, env=env, capture_output=True,
            text=True, encoding="utf-8", timeout=120,
        )
        assert proc.returncode == 0, proc.stderr
        return json.loads(proc.stdout)

    # seed 2 与 8 在修复前必产出不同战果与碰撞序列
    assert outcome("2") == outcome("8")


# ===========================================================================
# AI：态势感知（残血自保 / 价值加权火力 / 目标价值）
# ===========================================================================

def test_movement_retreats_when_critically_damaged() -> None:
    """残血自保：hull 跌破阈值后 `_own_value` 从 0 跃升为正，且 `_score_hex` 给
    "离最近敌预测落点更远"的候选更高分（退避项为正）；健康舰无退避（不与接近项打架）。"""
    engine, state = movement_planning_state(3)
    obs = engine.observe(state.game_id, Side.AXIS)
    enemies = [ship for ship in obs.ships if ship.side != Side.AXIS and not ship.sunk and ship.position]
    commander = TacticalCommander()  # 产品默认：w_retreat=1.0, retreat_hull_threshold=0.35
    ctx = commander._build_movement_context(engine, state, Side.AXIS, enemies)
    # 选一艘离最近敌预测格在炮射程内（approach 项为 0，避免与退避项对冲）的舰
    ship = next(
        s for s in axis_ships(state)
        if min(s.position.distance(position) for position in ctx.pred_hexes) <= APPROACH_RANGE
    )
    # 满血：无伤 → own_value=0（正常接敌，不退避）
    assert commander._own_value(state, ship, ctx) == 0.0
    # 残血：survival>0 → own_value 显著为正
    ship.hull = max(1, int(ship.max_hull * 0.2)) if ship.max_hull else 1
    damaged_value = commander._own_value(state, ship, ctx)
    assert damaged_value > 0.5
    # 打分：起点为"近"候选，取一个比起点更远离最近敌预测格的邻格为"远"候选
    start = ship.position
    nearest_pred = min(ctx.pred_hexes, key=lambda position: start.distance(position))
    start_dist = start.distance(nearest_pred)
    far = next(
        (candidate for candidate in (start.neighbor(h) for h in range(1, 7))
         if candidate.distance(nearest_pred) > start_dist),
        None,
    )
    assert far is not None, "应存在比起点更远离敌预测格的邻格"
    score_at = lambda hexc: commander._score_hex(
        engine, state, ship, hexc, ship.heading, ctx,
        0.0, 1.0, 0.0, 1.0, 0.0, 0.0, damaged_value,
    )
    assert score_at(far) > score_at(start)  # 残血时离敌越远分越高


def test_value_factor_weights_vp_and_finish() -> None:
    """目标价值系数：高 VP 敌 > 低 VP 敌；同 VP 低血量（可补刀）敌 > 满血敌；
    hidden_damage（hull=None）敌只用 VP、不猜血量、不崩。"""
    engine, state = movement_planning_state(3)
    obs = engine.observe(state.game_id, Side.AXIS)
    enemies = [ship for ship in obs.ships if ship.side != Side.AXIS and not ship.sunk and ship.position]
    commander = TacticalCommander()
    hi = max(enemies, key=lambda enemy: enemy.vp)
    lo = min(enemies, key=lambda enemy: enemy.vp)
    assert hi.vp > lo.vp
    max_vp = max(enemy.vp for enemy in enemies)
    assert commander._value_factor(hi, max_vp) > 1.0
    assert commander._value_factor(lo, max_vp) < commander._value_factor(hi, max_vp)
    # 同舰压血：finish 项生效
    damaged = hi.model_copy(update={"hull": 1})
    assert commander._value_factor(damaged, max_vp) > commander._value_factor(hi, max_vp)
    # 隐藏损伤：hull=None → hull_frac=1.0，只用 VP
    hidden = hi.model_copy(update={"hull": None, "max_hull": None})
    assert commander._value_factor(hidden, max_vp) == commander._value_factor(hi, max_vp)


def test_value_pressure_weights_high_value_enemy() -> None:
    """价值加权火力：同一 (格, 航向) 下敌价值越高 `_value_pressure` 越大（线性倍率）。"""
    engine, state = movement_planning_state(3)
    obs = engine.observe(state.game_id, Side.AXIS)
    enemies = [ship for ship in obs.ships if ship.side != Side.AXIS and not ship.sunk and ship.position]
    commander = TacticalCommander()
    ctx = commander._build_movement_context(engine, state, Side.AXIS, enemies)
    # 找一个"当前位置/航向能对其预测落点开火"的舰-敌组合，保证加权项非零
    hexc = heading = None
    target = None
    for ship in axis_ships(state):
        for enemy in enemies:
            probe = replace(ctx, enemy_value={enemy.id: 1.0})
            if commander._value_pressure(engine, state, ship, ship.position, ship.heading, probe) > 0:
                hexc, heading, target = ship.position, ship.heading, enemy
                break
        if target is not None:
            break
    assert target is not None, "应存在当前阵位可开火的舰-敌组合"
    zeroed = {enemy.id: 0.0 for enemy in enemies}
    low = replace(ctx, enemy_value={**zeroed, target.id: 1.0})
    high = replace(ctx, enemy_value={**zeroed, target.id: 5.0})
    p_low = commander._value_pressure(engine, state, ship, hexc, heading, low)
    p_high = commander._value_pressure(engine, state, ship, hexc, heading, high)
    assert p_low > 0.0
    assert p_high > p_low
    # 其余敌价值恒 0 → 目标价值因子只是线性倍率（逐候选加权成立）
    assert p_high == pytest.approx(5.0 * p_low)


def test_score_hex_defaults_match_legacy() -> None:
    """新态势感知项全默认 0 时 `_score_hex` 逐项退化为旧公式（回归保护：
    默认路径不引入任何偏移）。"""
    engine, state = movement_planning_state(3)
    ship = axis_ships(state)[0]
    scorer = TacticalCommander(profile=legacy_profile())
    ctx = empty_context(0.0)  # enemies/pred_hexes/my_positions 全空
    got = scorer._score_hex(engine, state, ship, ship.position, ship.heading, ctx,
                            0.5, 1.0, 0.0, 1.0, 0.0, 0.0, 0.0)
    # 旧公式：threat_norm=0，pressure_term=0.5，无接近/编队/退避项
    assert got == pytest.approx(0.5)


# ===========================================================================
# AI：概率抽样（softmax / 种子化 RNG）
# ===========================================================================

def test_sample_weighted_variety_and_temperature_zero_argmax() -> None:
    """`_sample_weighted`：温度=0 恒 argmax 且不消耗 RNG；温度>0 同一 RNG 流内
    多次抽取出现多个目标（概率非退化，随机因素确实起作用）。"""
    scored = [(1.0, "a"), (0.99, "b"), (0.5, "c")]
    rng = random.Random(42)
    assert tactical.TacticalCommander._sample_weighted(scored, 0.0, rng) == "a"
    assert tactical.TacticalCommander._sample_weighted(scored, 0.0, rng) == "a"  # 两次一致（未耗 RNG）
    rng = random.Random(42)
    picks = {tactical.TacticalCommander._sample_weighted(scored, 0.5, rng) for _ in range(300)}
    assert len(picks) >= 2


def test_movement_sampling_stays_legal_and_within_candidates() -> None:
    """温度>0 种子化抽样：多次产出计划均 commitable 且终点在可达集内；
    rng=None 时不抽样、恒 argmax（两次一致）。"""
    for seed in (1, 3, 9):
        engine, state = movement_planning_state(seed)
        obs = engine.observe(state.game_id, Side.AXIS)
        enemies = [ship for ship in obs.ships if ship.side != Side.AXIS and not ship.sunk and ship.position]
        commander = TacticalCommander()  # 产品默认 temperature=0.5
        ctx = commander._build_movement_context(engine, state, Side.AXIS, enemies,
                                                commander._ai_rng(state, Side.AXIS))
        reachable = {
            ship.id: {HexCoord(q=entry["hex"]["q"], r=entry["hex"]["r"]).label
                      for entry in engine.movement_candidates(state, ship)["reachable"]}
            for ship in axis_ships(state)
        }
        for ship in axis_ships(state):
            order = commander._movement_order_for(engine, state, ship, ctx)
            preview = engine.movement_preview(state, ship, plan=order.plan)
            assert preview["commitable"] is True
            assert preview["current_label"] in reachable[ship.id]
        # rng=None → 不抽样
        ctx0 = commander._build_movement_context(engine, state, Side.AXIS, enemies)
        first = [commander._movement_order_for(engine, state, ship, ctx0).plan for ship in axis_ships(state)]
        second = [commander._movement_order_for(engine, state, ship, ctx0).plan for ship in axis_ships(state)]
        assert first == second


def test_same_seed_same_sampling_sequence() -> None:
    """同 seed 两遍 MOVEMENT 计划逐位一致（种子化 RNG 保证概率抽样可复现）。"""
    def movement_plans(seed: int) -> tuple[tuple[str, str], ...]:
        engine, state = movement_planning_state(seed)
        _plan, batch, _ = TacticalCommander().choose_plan(engine, state.game_id, Side.AXIS)
        return tuple(sorted((order.ship_id, order.plan) for order in batch.movement))
    assert movement_plans(3) == movement_plans(3)
    assert movement_plans(9) == movement_plans(9)


def test_rng_seed_ignores_game_id() -> None:
    """同 seed 不同 game_id：MOVEMENT 与 GUNNERY 计划一致（AI 种子不依赖随机 uuid）。"""
    def orders(seed: int, game_id: str) -> tuple[object, object]:
        engine = IronBottomEngine()
        state = engine.reset("IBS-S-03", seed=seed, game_id=game_id)
        sessions = {Side.AXIS: session_for("tactical", Side.AXIS),
                    Side.ALLIES: session_for("tactical", Side.ALLIES)}
        state = drive_to(engine, state.game_id, sessions, Phase.MOVEMENT_PLANNING)
        commander = TacticalCommander()
        _plan, batch, _ = commander.choose_plan(engine, state.game_id, Side.AXIS)
        move = tuple(sorted((order.ship_id, order.plan) for order in batch.movement))
        state = drive_to(engine, state.game_id, sessions, Phase.GUNNERY)
        _plan, batch, _ = commander.choose_plan(engine, state.game_id, Side.AXIS)
        gun = tuple(sorted(
            (order.ship_id, order.primary_target,
             tuple(sorted(mount.mount_id for mount in order.mounts)))
            for order in batch.gunnery
        ))
        return move, gun
    assert orders(3, "rng-gid-a") == orders(3, "rng-gid-b")


# ===========================================================================
# AI：炮击目标价值 / 抽样
# ===========================================================================

def test_gunnery_temperature_zero_picks_best_expected_hits_value() -> None:
    """温度=0：每舰目标 = argmax(expected_hits × 目标价值)，炮位与目标一致，订单合法。"""
    engine = IronBottomEngine()
    state = engine.reset("IBS-S-03", seed=1, game_id="gun-temp0")
    sessions = {Side.AXIS: session_for("tactical", Side.AXIS),
                Side.ALLIES: session_for("deterministic", Side.ALLIES)}
    state = drive_to(engine, state.game_id, sessions, Phase.GUNNERY)
    commander = TacticalCommander(
        profile=tactical.PROFILES["balanced"].model_copy(update={"temperature": 0.0})
    )
    _plan, batch, _ = commander.choose_plan(engine, state.game_id, Side.AXIS)
    assert batch.gunnery
    options = engine.gunnery_target_options(state, Side.AXIS)
    by_ship = {cand["ship_id"]: cand for cand in options}
    obs = engine.observe(state.game_id, Side.AXIS)
    enemies = {ship.id: ship for ship in obs.ships if ship.side != Side.AXIS and not ship.sunk and ship.position}
    max_vp = max((ship.vp for ship in obs.ships), default=1)
    for order in batch.gunnery:
        cand = by_ship[order.ship_id]
        best, best_score = None, -1.0
        for target in cand["targets"]:
            score = target["expected_hits"] * commander._value_factor(enemies[target["target_id"]], max_vp)
            if score > best_score:
                best, best_score = target["target_id"], score
        assert order.primary_target == best
        chosen = next(target for target in cand["targets"] if target["target_id"] == best)
        assert [mount.mount_id for mount in order.mounts] == chosen["mount_ids"]
    assert engine.validate_orders(state.game_id, batch).valid


def test_gunnery_targets_high_value_or_finishable() -> None:
    """价值权重驱动目标选择：把某舰"次优"候选目标压到 1 血（可补刀）后，温度=0
    下该目标必须反超被选中（w_finish 项使残血敌优先）。"""
    engine = IronBottomEngine()
    state = engine.reset("IBS-S-03", seed=1, game_id="gun-finishable")
    sessions = {Side.AXIS: session_for("tactical", Side.AXIS),
                Side.ALLIES: session_for("deterministic", Side.ALLIES)}
    state = drive_to(engine, state.game_id, sessions, Phase.GUNNERY)
    commander = TacticalCommander(
        profile=tactical.PROFILES["balanced"].model_copy(update={"temperature": 0.0})
    )

    def target_scores(cand: dict) -> list[tuple[float, str]]:
        obs = engine.observe(state.game_id, Side.AXIS)
        enemies = {ship.id: ship for ship in obs.ships if ship.side != Side.AXIS and not ship.sunk and ship.position}
        max_vp = max((ship.vp for ship in obs.ships), default=1)
        return [(target["expected_hits"] * commander._value_factor(enemies[target["target_id"]], max_vp),
                 target["target_id"])
                for target in cand["targets"]]

    # 对每艘轴心舰：把次优目标压到 1 血；若价值权重使其反超为 argmax → 记录场景
    flipped: dict | None = None
    for cand in engine.gunnery_target_options(state, Side.AXIS):
        if cand["blocked_reason"] or len(cand["targets"]) < 2:
            continue
        ordered = sorted(target_scores(cand), reverse=True)
        second_id = ordered[1][1]
        ship = state.ships[second_id]
        saved_hull = ship.hull
        ship.hull = 1
        # 压血后重算并取 argmax（必须先排序；cand 列表序≠分序）
        if sorted(target_scores(cand), reverse=True)[0][1] == second_id:
            flipped = (cand, second_id)  # 保留损伤供 choose_plan
            break
        ship.hull = saved_hull
    assert flipped, "价值权重应使某个可补刀目标反超（数据不支持则需复核）"
    cand, target_id = flipped
    _plan, batch, _ = commander.choose_plan(engine, state.game_id, Side.AXIS)
    order = next(item for item in batch.gunnery if item.ship_id == cand["ship_id"])
    assert order.primary_target == target_id


def test_gunnery_sampling_stays_within_legal_targets() -> None:
    """温度>0：抽样选择的目标均在 `gunnery_target_options` 该舰 targets 内，订单合法。"""
    engine = IronBottomEngine()
    state = engine.reset("IBS-S-03", seed=1, game_id="gun-sample-legal")
    sessions = {Side.AXIS: session_for("tactical", Side.AXIS),
                Side.ALLIES: session_for("deterministic", Side.ALLIES)}
    state = drive_to(engine, state.game_id, sessions, Phase.GUNNERY)
    commander = TacticalCommander()  # 产品默认 temperature=0.5
    for _ in range(3):
        _plan, batch, _ = commander.choose_plan(engine, state.game_id, Side.AXIS)
        assert batch.gunnery
        options = engine.gunnery_target_options(state, Side.AXIS)
        legal = {cand["ship_id"]: {target["target_id"] for target in cand["targets"]} for cand in options}
        for order in batch.gunnery:
            assert order.primary_target in legal[order.ship_id]
        assert engine.validate_orders(state.game_id, batch).valid


# ===========================================================================
# AI：订单级跨哈希种子确定性（比"只比战果"更强的 AI 序列校验）
# ===========================================================================

_SUBPROCESS_AI_DETERMINISM_SCRIPT = (
    "import json, sys\n"
    "sys.stdout.reconfigure(encoding='utf-8')\n"
    "from iron_bottom_sound.engine import IronBottomEngine, ORDER_PHASES\n"
    "from iron_bottom_sound.models import Phase, Side\n"
    "from iron_bottom_sound.tactical import TacticalCommander\n"
    "engine = IronBottomEngine()\n"
    "state = engine.reset('IBS-S-03', seed=3, game_id='ai-orders')\n"
    "commander = TacticalCommander()\n"
    "def drive_to(target):\n"
    "    for _ in range(60):\n"
    "        if state.phase == target:\n"
    "            return\n"
    "        if state.phase == Phase.COMPLETE:\n"
    "            raise RuntimeError('COMPLETE before ' + str(target))\n"
    "        if state.phase in ORDER_PHASES:\n"
    "            for side in (Side.AXIS, Side.ALLIES):\n"
    "                batch = commander.choose_plan(engine, state.game_id, side)[1]\n"
    "                result = engine.submit_orders(state.game_id, batch)\n"
    "                assert result.valid, result.errors\n"
    "        engine.advance(state.game_id)\n"
    "drive_to(Phase.MOVEMENT_PLANNING)\n"
    "plan, batch, _ = commander.choose_plan(engine, state.game_id, Side.AXIS)\n"
    "move = sorted((order.ship_id, order.plan) for order in batch.movement)\n"
    "drive_to(Phase.GUNNERY)\n"
    "plan, batch, _ = commander.choose_plan(engine, state.game_id, Side.AXIS)\n"
    "gun = sorted(\n"
    "    (order.ship_id, order.primary_target,\n"
    "     tuple(sorted(mount.mount_id for mount in order.mounts)))\n"
    "    for order in batch.gunnery\n"
    ")\n"
    "print(json.dumps({'move': move, 'gun': gun}, ensure_ascii=False))\n"
)


def test_ai_orders_deterministic_across_hash_seeds() -> None:
    """AI 订单序列（移动 plan / 炮击目标+炮位）不能依赖字符串哈希。

    回归：AI 概率抽样若用 set 迭代序或 hash() 派生种子，序列随 PYTHONHASHSEED 变化。
    本测试跨 PYTHONHASHSEED=2/8 跑完整 MOVEMENT+GUNNERY 轴心订单序列并比对一致。
    """
    def outcome(hashseed: str):
        env = dict(os.environ, PYTHONHASHSEED=hashseed)
        proc = subprocess.run(
            [sys.executable, "-c", _SUBPROCESS_AI_DETERMINISM_SCRIPT],
            cwd=_REPO_ROOT, env=env, capture_output=True,
            text=True, encoding="utf-8", timeout=120,
        )
        assert proc.returncode == 0, proc.stderr
        return json.loads(proc.stdout)

    assert outcome("2") == outcome("8")
