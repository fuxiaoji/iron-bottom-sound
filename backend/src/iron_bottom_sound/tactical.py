from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from typing import Any, Callable

from pydantic import BaseModel

from .data import load_scenario
from .engine import IronBottomEngine
from .llm import DeterministicCommander
from .models import (
    AIPlanSheet,
    ContactMovementOrder,
    GunMountOrder,
    GunneryOrder,
    HexCoord,
    LLMCallAudit,
    MovementOrder,
    OrderBatch,
    Phase,
    PublicShip,
    ShipState,
    Side,
    TorpedoOrder,
)
from .torpedo_tactics import AdaptiveTorpedoPlanner, TorpedoDecisionAudit


class TacticalProfile(BaseModel):
    """战术 AI 启发式权重/阈值（非规则常量，可调；不改引擎裁决）。

    每个权重/阈值只决定 AI 对相同只读引擎信息的偏好方向与强度：
    - `w_enemy_heat` 敌火力规避权重（敌威胁按敌方 max 归一，量纲 [0,1]）
    - `w_fire_pressure` 我方火力压力权重（按本舰候选空间最大压力归一，量纲 [0,1]）
    - `w_approach` 接近权重：>0 炮射程外轻微接近；<0 把缩短距离变惩罚（等效奖励保持距离）
    - `approach_range` 判定"已入炮射程"的六角距离上限
    - `torpedo_max_range` / `torpedo_min_expected` 鱼雷近距/置信度发射阈值
    - `top_k_candidates` 路径回退时尝试的候选数
    - `w_formation` 编队权重（靠近最近己方舰到理想间距）
    - `formation_spacing` 与最近己方舰的理想六角距离区间
    - `line_ahead` 长纵队偏好：最近己方舰在航向正前方 1-3 格时的额外奖励
    - `w_predict_opponent` 对抗评分开关：>0 预测对手下一步（默认开）；<=0 退化为
      静态"对手当前阵位"语义（可关，供回归与对照）
    - `retreat_hull_threshold` hull 分数跌破此值 → 残血自保（退避）强度线性升到 1
    - `w_retreat` 退避项权重（残血/高价值/带伤舰远离敌预测落点）
    - `w_protect_own` 己舰价值自保权重（高 VP 舰更惜命）
    - `w_vp` 目标 VP 价值权重（高 VP 敌优先被火力覆盖/集火）
    - `w_finish` 目标可击沉价值权重（低血量敌优先补刀）
    - `w_self_status` 自身状态自保权重（起火/炮禁用/速度损伤 → 自保上调）
    - `temperature` softmax 温度：炮击目标/移动落点在打分后按 exp(score/T) 归一抽样；
      0 → 严格 argmax（完全确定，不消耗 AI RNG）
    - `rng_seed_off` profile 间 AI 随机种子偏移（保证不同风格抽样序列不同）
    """

    w_enemy_heat: float = 1.0
    w_fire_pressure: float = 1.0
    w_approach: float = 0.5
    approach_range: int = 12
    torpedo_max_range: int = 10
    torpedo_min_expected: float = 0.30
    top_k_candidates: int = 5
    w_formation: float = 0.0
    formation_spacing: tuple[int, int] = (2, 4)
    line_ahead: float = 0.0
    w_predict_opponent: float = 1.0
    retreat_hull_threshold: float = 0.35
    w_retreat: float = 1.0
    w_protect_own: float = 0.5
    w_vp: float = 0.3
    w_finish: float = 0.5
    w_self_status: float = 0.3
    temperature: float = 0.5
    rng_seed_off: int = 0
    torpedo_doctrine: str = "legacy"
    torpedo_min_tactical_score: float = 0.15
    w_torpedo_avoid: float = 2.5


# —— 风格预设（用户要求的 6 种打法）——
PROFILES: dict[str, TacticalProfile] = {
    "balanced": TacticalProfile(),
    # 大舰队编队：优先抱团到最近友舰 1-3 格，接近略降（稳定阵型而不是冲锋）
    "fleet": TacticalProfile(w_formation=2.0, formation_spacing=(1, 3), w_approach=0.3),
    # 长纵队：强烈偏好最近友舰在航向正前方 1-3 格的同向纵列
    "line": TacticalProfile(line_ahead=2.0, w_formation=1.5, formation_spacing=(2, 4), w_approach=0.3),
    # 乱阵近战：几乎不惧敌方热力、火力与接近权重拉满、鱼雷更激进、刻意散开（负队形）
    "brawl": TacticalProfile(
        w_enemy_heat=0.2, w_fire_pressure=1.5, w_approach=1.5, approach_range=16,
        torpedo_max_range=12, torpedo_min_expected=0.15, w_formation=-0.5,
    ),
    # 鱼雷专精：高接近（贴近）、更远的鱼雷射程与更低置信度门槛
    "torpedo": TacticalProfile(
        w_approach=1.2, approach_range=14, torpedo_max_range=14, torpedo_min_expected=0.10,
    ),
    # 猥琐保守：极度惧火、低火力追求、负接近（保持距离）、鱼雷阈值极高、轻度抱团
    "cautious": TacticalProfile(
        w_enemy_heat=2.0, w_fire_pressure=0.5, w_approach=-0.6,
        torpedo_min_expected=0.60, w_formation=0.5,
    ),
    # Adaptive and its six deterministic specialists share the same legal-action
    # boundary.  Only the doctrine selector differs; these profiles form the initial
    # PSRO-lite strategy population without changing classic profile behaviour.
    "adaptive": TacticalProfile(torpedo_doctrine="adaptive", torpedo_min_tactical_score=0.10),
    "direct_attack": TacticalProfile(torpedo_doctrine="direct_attack", torpedo_min_tactical_score=0.05),
    "area_denial": TacticalProfile(torpedo_doctrine="area_denial", torpedo_min_tactical_score=0.05),
    "break_crossing_t": TacticalProfile(torpedo_doctrine="break_crossing_t", torpedo_min_tactical_score=0.05),
    "formation_split": TacticalProfile(torpedo_doctrine="formation_split", torpedo_min_tactical_score=0.05),
    "crossfire": TacticalProfile(torpedo_doctrine="crossfire", torpedo_min_tactical_score=0.05),
    "cover_withdrawal": TacticalProfile(torpedo_doctrine="cover_withdrawal", torpedo_min_tactical_score=0.05),
}

# 旧模块级常量保留为 balanced 别名（兼容既有 import / 外部读参）；实现一律读 self.profile.*
W_ENEMY_HEAT = PROFILES["balanced"].w_enemy_heat
W_FIRE_PRESSURE = PROFILES["balanced"].w_fire_pressure
W_APPROACH = PROFILES["balanced"].w_approach
APPROACH_RANGE = PROFILES["balanced"].approach_range
TORPEDO_MAX_RANGE = PROFILES["balanced"].torpedo_max_range
TORPEDO_MIN_EXPECTED = PROFILES["balanced"].torpedo_min_expected
TOP_K_CANDIDATES = PROFILES["balanced"].top_k_candidates

# AI 概率抽样用独立 RNG 的固定相位码（与引擎 `state.rng_counter` 骰子流完全隔离）。
# 纯整数派生 → 同 seed 跨进程/跨 PYTHONHASHSEED 可复现；不得用 game_id/hash()/set 迭代序。
_AI_PHASE_INT: dict[Phase, int] = {
    Phase.MOVEMENT_PLANNING: 3, Phase.TORPEDO_PLANNING: 4, Phase.GUNNERY: 5,
}


@dataclass
class _MovementContext:
    """移动打分的一次性共享上下文（对抗评分）。

    `pred_by_id` 每艘可见敌舰的（预测落点, 末航向）；`pred_hexes` 为预测落点集合
    （我方火力压力与接近项的目标）；`enemy_threat_of` 敌在预测落点对指定格的火力
    压力之和（惰性 memo，按候选格只算一次）；`my_positions` 我方当前阵位（队形项）。
    """

    enemies: list[PublicShip]
    pred_by_id: dict[str, tuple[HexCoord, int]]
    pred_hexes: list[HexCoord]
    enemy_threat_of: Callable[[HexCoord], float]
    my_positions: list[HexCoord]
    # —— 态势感知（价值加权火力 + 残血自保 + 移动抽样）——
    enemy_value: dict[str, float] = field(default_factory=dict)  # enemy id → value_factor
    max_vp: float = 1.0
    rng: random.Random | None = None  # None → 退化为 argmax（单测/兼容路径）
    visible_torpedo_threat: dict[str, float] = field(default_factory=dict)


class TacticalCommander(DeterministicCommander):
    """确定性启发式战术 AI：移动按"规避敌方（预测后的）火力、让敌方处于我方火力
    覆盖内"，炮击采纳 `gunnery_assist` 齐射推荐，鱼雷仅在近距离且自动鱼雷
    系统置信度高时发射。只产订单、只读引擎方法，敌方信息一律经 observe /
    `_visible_to` 守卫的只读方法取得（不泄漏隐蔽舰位置与隐藏损伤）。

    对抗评分（`w_predict_opponent>0`）：先对每艘可见敌舰用同一套战术评分预测其
    下一回合最优落点（敌视角、只依赖敌当前可见信息、1-ply 不递归），再以预测
    落点作为我方威胁来源、压力目标与接近对象。

    继承 `DeterministicCommander` 以复用 CONTACT_SETUP / REINFORCEMENT 策略。
    """

    model = "tactical-v1"

    def __init__(self, profile: TacticalProfile = PROFILES["balanced"]) -> None:
        self.profile = profile
        self._last_torpedo_audit: TorpedoDecisionAudit | None = None

    # ------------------------------------------------------------------ AI 概率抽样基础设施

    def _ai_rng(self, state, side: Side) -> random.Random:
        """本阶段独立随机源：纯整数 (seed, turn, side, phase) 派生，与引擎骰子流隔离。

        每阶段派生一次并下传给该阶段全部舰的抽样（绝不分舰派生，保证同 seed 序列复现）。
        不得用 game_id（uuid 每局不同）、hash()/set 迭代序（随 PYTHONHASHSEED 变）。
        """
        side_int = 1 if side == Side.AXIS else 2
        phase_int = _AI_PHASE_INT.get(state.phase, 0)
        rng_seed = (
            state.seed * 1_000_003 + state.turn * 10_007
            + side_int * 101 + phase_int * 11 + self.profile.rng_seed_off
        )
        return random.Random(rng_seed)

    @staticmethod
    def _clamp01(x: float) -> float:
        return max(0.0, min(1.0, x))

    def _self_status_factor(self, ship) -> float:
        """己舰状态自保压力 [0,1]：起火 / 火炮禁用 / 速度损伤 → 更惜命。"""
        return self._clamp01(
            (1.0 if ship.fire_markers > 0 else 0.0)
            + (1.0 if ship.guns_disabled_turns > 0 else 0.0)
            + (0.5 if any(ship.speed_damage_crossed) else 0.0)
        )

    def _value_factor(self, enemy, max_vp: float) -> float:
        """目标价值系数（≥1）：VP 高、低血量（可补刀）的敌舰更值得火力覆盖/集火。

        敌情一律用 PublicShip 可见字段；hidden_damage 下 hull=None → hull_frac=1.0
        （只用 VP，不猜隐蔽血量，不泄漏隐藏损伤）。
        """
        hull_frac = 1.0
        if enemy.hull is not None and enemy.max_hull:
            hull_frac = enemy.hull / enemy.max_hull
        return (
            1.0
            + self.profile.w_vp * (enemy.vp / max_vp)
            + self.profile.w_finish * (1.0 - hull_frac)
        )

    def _own_value(self, state, ship, ctx: _MovementContext) -> float:
        """己舰自保/退避强度：满血且无伤 → 0（正常接敌，不退避）；残血（survival 线性
        升到 1）/起火/炮损/减速 → >0，高 VP 舰退避更坚决。"""
        hull_frac = ship.hull / ship.max_hull if ship.max_hull else 1.0
        threshold = self.profile.retreat_hull_threshold
        survival = self._clamp01((threshold - hull_frac) / threshold) if threshold > 0 else 0.0
        status = self._self_status_factor(ship)
        if survival <= 0 and status <= 0:
            return 0.0
        return (
            survival
            + self.profile.w_self_status * status
            + self.profile.w_protect_own * (ship.vp / ctx.max_vp)
        )

    def _value_pressure(
        self, engine: IronBottomEngine, state, ship, hexc: HexCoord, heading: int, ctx: _MovementContext,
    ) -> float:
        """候选 (格, 航向) 的价值加权火力：Σ_敌 我舰在此对敌预测落点的压力 × 敌价值。

        逐候选计算（非每舰常数），否则在 softmax 中会被 max 消掉、不驱动选格。
        全零价值权重时 `value_factor≡1` → 该项 ≡ 原 `ship_gun_pressure(...pred_hexes)`。
        """
        if not ctx.enemies:
            return 0.0
        total = 0.0
        for enemy in ctx.enemies:
            pred = ctx.pred_by_id.get(enemy.id)
            if pred is None:
                continue
            total += engine.ship_gun_pressure(
                state, ship, position=hexc, heading=heading, target_hexes=[pred[0]],
            ) * ctx.enemy_value.get(enemy.id, 1.0)
        return total

    @staticmethod
    def _sample_weighted(scored, temperature: float, rng: random.Random):
        """按 `exp(score/T)` 归一化概率抽样（softmax）；返回被抽中条目的载荷。

        条目形如 `(score, *payload)`：双元素条目返回 `payload[0]`（如炮击目标
        dict），更多元素返回 `tuple(payload)`（如移动落点 (cost, hexc, heading)）。

        - `temperature <= 0` 或候选 ≤ 1 → argmax，**不消耗 RNG**（温度=0 完全确定）。
        - 先减 max 防溢出；全部得分相等 → 均匀抽样（仍合法）。
        - 每阶段共享一个 rng 实例，消耗点在"候选≥2 且温度>0"时固定 → 同 seed 序列可复现。
        """

        def payload_of(item):
            return item[1] if len(item) == 2 else tuple(item[1:])

        if temperature <= 0 or len(scored) <= 1:
            return payload_of(max(scored, key=lambda item: item[0]))
        max_score = max(item[0] for item in scored)
        weights = [math.exp((item[0] - max_score) / temperature) for item in scored]
        total = sum(weights)
        if total <= 0:
            return payload_of(scored[0])
        roll = rng.random() * total
        acc = 0.0
        for i, item in enumerate(scored):
            acc += weights[i]
            if roll <= acc:
                return payload_of(item)
        return payload_of(scored[-1])

    # ------------------------------------------------------------------ 总入口

    def choose_plan(
        self, engine: IronBottomEngine, game_id: str, side: Side,
    ) -> tuple[AIPlanSheet, OrderBatch, list[LLMCallAudit]]:
        state = engine.get(game_id)
        batch = OrderBatch(side=side, phase=state.phase)
        intents: dict[str, str] = {}
        if state.phase == Phase.CONTACT_SETUP:
            batch.contacts = self._contact_setup(engine, game_id, side)
            intents = {order.marker_id: "部署隐蔽编队" for order in batch.contacts}
        elif state.phase == Phase.REINFORCEMENT:
            batch.reinforcements = self._reinforcements(engine, game_id, side)
            intents = {order.ship_id: "按想定边界进入" for order in batch.reinforcements}
        elif state.phase == Phase.MOVEMENT_PLANNING:
            batch.movement, batch.contact_movement, intents = self._plan_movement(engine, state, side, self._ai_rng(state, side))
        elif state.phase == Phase.TORPEDO_PLANNING:
            batch.torpedoes = self._plan_torpedoes(engine, state, side)
            doctrine = self._last_torpedo_audit.doctrine.value if self._last_torpedo_audit else "legacy"
            intents = {order.ship_id: f"鱼雷战术：{doctrine}" for order in batch.torpedoes}
        elif state.phase == Phase.GUNNERY:
            batch.gunnery = self._plan_gunnery(engine, state, side, self._ai_rng(state, side))
            intents = {order.ship_id: "采纳射界齐射推荐" for order in batch.gunnery}
        else:
            raise ValueError(f"No orders may be chosen during automatic phase {state.phase}")
        return self._finalize(engine, state, side, batch, intents)

    def _finalize(
        self, engine: IronBottomEngine, state, side: Side, batch: OrderBatch, intents: dict[str, str],
    ) -> tuple[AIPlanSheet, OrderBatch, list[LLMCallAudit]]:
        plan = AIPlanSheet(
            turn=state.turn,
            phase=state.phase,
            situation_summary=f"{side.value} 方在 {state.phase.value} 阶段执行热力/置信度战术策略。",
            phase_goal="规避敌方火力、抢占射击阵位；鱼雷仅在近距高置信时发射",
            unit_intents=intents,
            orders=batch.model_dump(mode="json"),
            contingency=["若订单被拒绝则回退保持位置/不发射"],
            tactical_analysis=(
                self._last_torpedo_audit.model_dump(mode="json")
                if state.phase == Phase.TORPEDO_PLANNING and self._last_torpedo_audit else None
            ),
        )
        validation = engine.validate_orders(state.game_id, batch)
        audit = LLMCallAudit(
            side=side,
            turn=state.turn,
            phase=state.phase,
            attempt=1,
            model=self.model,
            elapsed_ms=0,
            valid=validation.valid,
            validation_errors=validation.errors,
        )
        if not validation.valid:
            raise ValueError(validation.errors)
        return plan, batch, [audit]

    # ------------------------------------------------------------------ 对抗评分上下文

    def _public_copy(self, state, ship: ShipState) -> ShipState:
        """敌视角下的"公开信息"副本：当隐藏损伤启用时剥离全部损伤派生约束
        （被迫直行/旋回/限速、舵损转向上限、速度损伤跨格、已毁炮位），与热力图
        "敌方按记录全炮位"一致，不泄漏隐藏损伤；未启用时原样返回真实状态。
        """
        if not state.options.optional_rules.hidden_damage:
            return ship
        return ship.model_copy(update={
            "turn_limit_degrees": None,
            "forced_straight_turns": 0,
            "forced_circle_turns": 0,
            "forced_turn_side": None,
            "forced_speed": None,
            "forced_speed_turns": 0,
            "speed_damage_crossed": (0, 0, 0),
            "gun_mounts": [mount.model_copy(update={"destroyed": False}) for mount in ship.gun_mounts],
        })

    def _build_movement_context(
        self, engine: IronBottomEngine, state, side: Side, enemies: list[PublicShip],
        rng: random.Random | None = None,
    ) -> _MovementContext:
        """构造移动打分的共享上下文。`w_predict_opponent<=0` 或无敌舰时退化为
        "预测=敌当前位置"的静态语义（与旧行为同构）。"""
        my_positions = [
            ship.position for ship in state.ships.values()
            if ship.side == side and not ship.sunk and ship.position
        ]
        pred_by_id: dict[str, tuple[HexCoord, int]] = {}
        pred_hexes: list[HexCoord] = []
        if self.profile.w_predict_opponent > 0 and enemies:
            for enemy in enemies:
                hexc, heading = self._predict_enemy_move(engine, state, enemy, side)
                pred_by_id[enemy.id] = (hexc, heading)
                pred_hexes.append(hexc)
        else:
            pred_by_id = {enemy.id: (enemy.position, enemy.heading) for enemy in enemies}
            pred_hexes = [enemy.position for enemy in enemies]

        public_enemies = {enemy.id: self._public_copy(state, state.ships[enemy.id]) for enemy in enemies}
        memo: dict[str, float] = {}

        def enemy_threat_of(hexc: HexCoord) -> float:
            label = hexc.label
            if label not in memo:
                memo[label] = sum(
                    engine.ship_gun_pressure(
                        state, public_enemies[enemy.id],
                        position=pred_by_id[enemy.id][0], heading=pred_by_id[enemy.id][1],
                        target_hexes=[hexc],
                    )
                    for enemy in enemies
                )
            return memo[label]

        max_vp = max((ship.vp for ship in state.ships.values()), default=1)
        enemy_value = {enemy.id: self._value_factor(enemy, max_vp) for enemy in enemies}
        torpedo_threat = self._visible_torpedo_threat(engine, state, side)
        return _MovementContext(
            enemies, pred_by_id, pred_hexes, enemy_threat_of, my_positions,
            enemy_value=enemy_value, max_vp=max_vp, rng=rng,
            visible_torpedo_threat=torpedo_threat,
        )

    @staticmethod
    def _visible_torpedo_threat(engine: IronBottomEngine, state, side: Side) -> dict[str, float]:
        """Project only tracks present in the side-filtered observation.

        The map is advisory movement pressure, not adjudication.  A hidden enemy track is
        absent under ``blind_torpedoes`` and therefore contributes exactly zero.
        """
        threat: dict[str, float] = {}
        for track in engine.observe(state.game_id, side).torpedo_tracks:
            if track.side == side:
                continue
            position = track.position
            horizon = min(track.range_remaining, max(track.speed_cycle) + 2)
            for step in range(horizon + 1):
                threat[position.label] = max(threat.get(position.label, 0.0), 1.0 - step * 0.06)
                try:
                    position = position.neighbor(track.heading)
                except ValueError:
                    break
                if position.label in state.land_hexes:
                    break
        return threat

    def _predict_enemy_move(
        self, engine: IronBottomEngine, state, enemy: PublicShip, my_side: Side,
    ) -> tuple[HexCoord, int]:
        """预测敌舰下一回合最优落点（敌视角 1-ply）：敌规避"我方火力覆盖"、
        追求对我可见舰的火力压力、按自身风格接近与编队。只依赖敌当前可见信息，
        不递归预测我方反应。返回 (预测落点, 末航向)。"""
        es = self._public_copy(state, state.ships[enemy.id])
        candidates = engine.movement_candidates(state, es, include_plans=False)["reachable"]
        if not candidates:
            return es.position, es.heading
        my_positions = [
            ship.position for ship in state.ships.values()
            if ship.side == my_side and not ship.sunk and ship.position
        ]
        # 敌视角可见的我方舰（`_visible_to` 与我方 observe 同源）
        seen = [
            ship for ship in state.ships.values()
            if ship.side == my_side and not ship.sunk and ship.position
            and engine._visible_to(state, ship, es.side, my_positions)
        ]
        # 敌方的友舰（只计入我能看到的，不因不可见敌舰泄漏阵位）
        enemy_allies = [
            ship.position for ship in state.ships.values()
            if ship.side == es.side and ship.id != es.id and not ship.sunk and ship.position
            and engine._visible_to(state, ship, my_side, my_positions)
        ]
        heat_cache: dict[str, float] = {}

        def my_heat(hexc: HexCoord) -> float:
            label = hexc.label
            if label not in heat_cache:
                value = 0.0
                for my_ship in seen:
                    public = self._public_copy(state, my_ship)
                    value += engine.ship_gun_pressure(state, public, target_hexes=[hexc])
                heat_cache[label] = value
            return heat_cache[label]

        entries: list[tuple[int, HexCoord, int, float]] = []
        max_pressure = 0.0
        for entry in candidates:
            hexc = HexCoord(q=entry["hex"]["q"], r=entry["hex"]["r"])
            for heading in entry["final_headings"]:
                pressure = engine.ship_gun_pressure(
                    state, es, position=hexc, heading=heading,
                    target_hexes=[ship.position for ship in seen],
                )
                entries.append((entry["cost"], hexc, heading, pressure))
                max_pressure = max(max_pressure, pressure)
        max_heat = max((my_heat(hexc) for _cost, hexc, _heading, _p in entries), default=0.0)
        scored: list[tuple[float, int, HexCoord, int]] = [
            (
                self._enemy_move_score(
                    es, hexc, heading, enemy_allies, seen,
                    my_heat, max_heat, pressure, max_pressure,
                ),
                cost, hexc, heading,
            )
            for cost, hexc, heading, pressure in entries
        ]
        scored.sort(key=lambda item: (item[0], -item[1], item[2].label, item[3]), reverse=True)
        return scored[0][2], scored[0][3]

    def _enemy_move_score(
        self, es: ShipState, hexc: HexCoord, heading: int, enemy_allies: list[HexCoord],
        seen: list[ShipState], my_heat: Callable[[HexCoord], float], max_heat: float,
        pressure: float, max_pressure: float,
    ) -> float:
        """敌视角的候选打分（镜像 `_score_hex`）：敌规避我方可视火力（heat 项）、
        追求自身火力压力、按自身 profile 接近与编队。"""
        heat = my_heat(hexc) / max_heat if max_heat > 0 else 0.0
        pressure_term = pressure / max_pressure if max_pressure > 0 else 0.0
        score = -self.profile.w_enemy_heat * heat + self.profile.w_fire_pressure * pressure_term
        if seen:
            nearest = min((ship.position for ship in seen), key=lambda position: es.position.distance(position))
            score += self._approach_delta(es.position.distance(nearest), hexc.distance(nearest))
        score += self._formation_factor(es.position, hexc, heading, enemy_allies)
        return score

    # ------------------------------------------------------------------ 移动

    def _plan_movement(
        self, engine: IronBottomEngine, state, side: Side, rng: random.Random | None = None,
    ) -> tuple[list[MovementOrder], list[ContactMovementOrder], dict[str, str]]:
        obs = engine.observe(state.game_id, side)
        enemies = [ship for ship in obs.ships if ship.side != side and not ship.sunk and ship.position]
        ctx = self._build_movement_context(engine, state, side, enemies, rng)
        active = {
            ship.id: ship for ship in state.ships.values()
            if ship.side == side and not ship.sunk and ship.position
            and (not state.options.realistic_command or ship.command_status == "attached")
        }
        groups = self._movement_groups(state, side, list(active))
        movement: list[MovementOrder] = []
        reserved: list[tuple[ShipState, MovementOrder]] = []
        for group in groups:
            leader = active[group[0]]
            straight = MovementOrder(ship_id=leader.id, plan=str(leader.current_speed))
            if (
                self.profile.line_ahead
                and engine.movement_preview(state, leader, plan=straight.plan)["commitable"]
                and not self._movement_conflicts(engine, state, leader, straight, reserved)
            ):
                leader_order = straight
            else:
                leader_order = self._movement_order_for(engine, state, leader, ctx, reserved)
            coordinated = self._coordinated_group_orders(
                engine, state, [active[ship_id] for ship_id in group], leader_order, reserved
            )
            if coordinated:
                for ship, order in coordinated:
                    movement.append(order)
                    reserved.append((ship, order))
                continue
            # 共同机动因边缘/损伤不可行：先规划可达集最小的受约束舰，避免自由度
            # 高的队首先占掉它唯一能停留/转出的格位。
            constrained = sorted(
                (active[ship_id] for ship_id in group),
                key=lambda ship: (
                    len(engine.movement_candidates(state, ship, include_plans=False)["reachable"]),
                    ship.id,
                ),
            )
            for follower in constrained:
                order = self._movement_order_for(engine, state, follower, ctx, reserved)
                movement.append(order)
                reserved.append((follower, order))
        contact_movement = [
            ContactMovementOrder(marker_id=marker.id, plan="4")
            for marker in obs.markers
            if marker.kind == "contact" and marker.secret_side == side and marker.position
        ]
        intents = {order.ship_id: "规避敌方火力并抢占射击阵位" for order in movement}
        intents.update({order.marker_id: "保持隐蔽编队推进" for order in contact_movement})
        return movement, contact_movement, intents

    def _coordinated_group_orders(
        self, engine: IronBottomEngine, state, ships: list[ShipState],
        preferred: MovementOrder, reserved: list[tuple[ShipState, MovementOrder]],
    ) -> list[tuple[ShipState, MovementOrder]]:
        """为整支纵队寻找所有成员均合法且逐脉冲安全的共同机动。

        先尝试队首的战术最优计划；若队尾因地图边缘或损伤无法复制，则枚举队首
        其它合法命令串，避免把队首已经选定的危险机动强塞给全队。
        """
        if len(ships) == 1:
            return [(ships[0], preferred)]
        plans = [preferred.plan]
        leader = ships[0]
        for entry in engine.movement_candidates(state, leader, include_plans=False)["reachable"]:
            hexc = HexCoord(q=entry["hex"]["q"], r=entry["hex"]["r"])
            for heading in entry["final_headings"]:
                plan = self._path_to(engine, state, leader, hexc, heading)
                if plan is not None and plan not in plans:
                    plans.append(plan)
        for plan in plans:
            local: list[tuple[ShipState, MovementOrder]] = []
            for ship in ships:
                order = MovementOrder(ship_id=ship.id, plan=plan)
                preview = engine.movement_preview(state, ship, plan=plan)
                if not preview["commitable"]:
                    local = []
                    break
                # A close column that finishes bow-on to the printed edge will
                # be unsalvageable next turn: the front ship must stop while
                # the following ship's mandatory first advance enters it.
                # Keep one clear bow hex as a one-turn safety horizon.
                end = HexCoord(q=preview["current_hex"]["q"], r=preview["current_hex"]["r"])
                try:
                    ahead = end.neighbor(preview["current_heading"])
                except ValueError:
                    local = []
                    break
                if engine._terrain_impassable(state, ahead):
                    local = []
                    break
                if self._movement_conflicts(engine, state, ship, order, reserved + local):
                    local = []
                    break
                local.append((ship, order))
            if local:
                return local
        return []

    def _movement_groups(self, state, side: Side, active_ids: list[str]) -> list[list[str]]:
        """返回本方移动编组，优先读取想定的默认纵队元数据。

        元数据是 AI/便利部署信息，不是裁决规则。已有纵队的所有战术风格都先按队
        协调一个共同机动，具体机动仍由各 profile 评分；未列出的舰保持单舰编组，
        因而不会影响旧想定或增援舰。
        """
        active_set = set(active_ids)
        setup = load_scenario(state.scenario_id).get("setup", {})
        definitions = setup.get("engine_default_formations", {}).get(side.value, [])
        groups: list[list[str]] = []
        assigned: set[str] = set()
        for definition in definitions:
            members = [ship_id for ship_id in definition.get("ships", []) if ship_id in active_set]
            if members:
                groups.append(members)
                assigned.update(members)
        if self.profile.line_ahead and groups:
            # Long-column doctrine manoeuvres every parallel column with the
            # same helm/speed programme. This preserves spacing between the
            # columns as well as within each column and prevents two columns
            # independently turning head-on several turns later.
            groups = [[ship_id for group in groups for ship_id in group]]
        groups.extend([[ship_id] for ship_id in active_ids if ship_id not in assigned])
        return groups

    def _movement_order_for(
        self, engine: IronBottomEngine, state, ship, ctx: _MovementContext,
        reserved: list[tuple[ShipState, MovementOrder]] | None = None,
    ) -> MovementOrder:
        """对单舰在所有可达 (格, 末航向) 上打分，取最优者（温度>0 且带 RNG 时按
        softmax 概率抽样）生成合法移动计划；抽样只在 `movement_candidates` 合法可达
        集内进行，永不落到非法格。"""
        candidates = engine.movement_candidates(state, ship, include_plans=False)["reachable"]
        own_value = self._own_value(state, ship, ctx)
        entries: list[tuple[int, HexCoord, int, float, float, float]] = []
        max_pressure = 0.0
        max_threat = 0.0
        max_value_pressure = 0.0
        for entry in candidates:
            hexc = HexCoord(q=entry["hex"]["q"], r=entry["hex"]["r"])
            for heading in entry["final_headings"]:
                pressure = engine.ship_gun_pressure(
                    state, ship, position=hexc, heading=heading, target_hexes=ctx.pred_hexes,
                )
                threat = ctx.enemy_threat_of(hexc)
                value_pressure = self._value_pressure(engine, state, ship, hexc, heading, ctx)
                entries.append((entry["cost"], hexc, heading, pressure, threat, value_pressure))
                max_pressure = max(max_pressure, pressure)
                max_threat = max(max_threat, threat)
                max_value_pressure = max(max_value_pressure, value_pressure)
        scored: list[tuple[float, int, HexCoord, int]] = [
            (
                self._score_hex(
                    engine, state, ship, hexc, heading, ctx,
                    pressure, max_pressure, threat, max_threat,
                    value_pressure, max_value_pressure, own_value,
                ),
                cost, hexc, heading,
            )
            for cost, hexc, heading, pressure, threat, value_pressure in entries
        ]
        # 确定性：分数降 → 成本降 → label/heading 字典序
        scored.sort(key=lambda item: (item[0], -item[1], item[2].label, item[3]), reverse=True)
        # 温度>0 且带 RNG：按 softmax 概率把抽中项置首，其余保持原降序（_path_to 复核链不变）。
        ordered = scored
        if ctx.rng is not None and self.profile.temperature > 0 and len(scored) > 1:
            chosen = self._sample_weighted(scored, self.profile.temperature, ctx.rng)
            ordered = [item for item in scored if (item[1], item[2], item[3]) == chosen]
            ordered.extend(item for item in scored if (item[1], item[2], item[3]) != chosen)
        reserved = reserved or []
        preferred = ordered[:self.profile.top_k_candidates]
        remaining = ordered[self.profile.top_k_candidates:]
        for _score, _cost, hexc, heading in preferred + remaining:
            plan = self._path_to(engine, state, ship, hexc, heading)
            if plan is None:
                continue
            order = MovementOrder(ship_id=ship.id, plan=plan)
            if not self._movement_conflicts(engine, state, ship, order, reserved):
                return order
        return self._fallback_movement(engine, state, ship, reserved)

    @staticmethod
    def _movement_positions(
        engine: IronBottomEngine, state, ship: ShipState, order: MovementOrder,
    ) -> list[HexCoord]:
        preview = engine.movement_preview(state, ship, plan=order.plan)
        return [ship.position] + [
            HexCoord(q=item["hex"]["q"], r=item["hex"]["r"])
            for item in preview["trajectory"]
        ]

    def _movement_conflicts(
        self, engine: IronBottomEngine, state, ship: ShipState, order: MovementOrder,
        reserved: list[tuple[ShipState, MovementOrder]],
    ) -> bool:
        """逐脉冲检查同格与交换格，镜像引擎同步移动的友舰碰撞判定。"""
        left = self._movement_positions(engine, state, ship, order)
        for other, other_order in reserved:
            right = self._movement_positions(engine, state, other, other_order)
            impulses = max(len(left), len(right)) - 1
            for impulse in range(impulses):
                left_before = left[min(impulse, len(left) - 1)]
                right_before = right[min(impulse, len(right) - 1)]
                left_after = left[min(impulse + 1, len(left) - 1)]
                right_after = right[min(impulse + 1, len(right) - 1)]
                if left_after == right_after:
                    return True
                if left_after == right_before and right_after == left_before:
                    return True
        return False

    def _score_hex(
        self, engine: IronBottomEngine, state, ship,
        hexc: HexCoord, heading: int, ctx: _MovementContext,
        pressure: float, max_pressure: float, threat: float, max_threat: float,
        value_pressure: float = 0.0, max_value_pressure: float = 0.0, own_value: float = 0.0,
    ) -> float:
        """候选格复合分：(a) 敌方（预测落点）火力威胁越小越好；(b) 我方舰在该格/
        航向下对敌预测落点的火力压力越大越好（均按候选空间最大归一，同量纲）；
        (c) 炮射程外时按 profile 接近最近敌预测落点；(d) 编队/长纵队偏好。

        态势感知扩展（默认参数全 0 → 与旧公式逐位一致）：
        (e) 价值加权火力：火力压力按敌舰价值（VP/可击沉度）加权，高价值目标优先
        占据射击阵位；`max_value_pressure=0`（无价值数据/空敌）回落基础压力项。
        (f) 残血自保：`own_value>0` 时移动越远离最近敌预测落点分越高（残血/高价值/
        带伤舰退避）；健康舰 own_value≈0，该项≈0，不与接近项打架。"""
        threat_norm = threat / max_threat if max_threat > 0 else 0.0
        if max_value_pressure > 0:
            pressure_term = value_pressure / max_value_pressure
        else:
            pressure_term = pressure / max_pressure if max_pressure > 0 else 0.0
        score = -self.profile.w_enemy_heat * threat_norm + self.profile.w_fire_pressure * pressure_term
        if ctx.pred_hexes:
            nearest = min(ctx.pred_hexes, key=lambda position: hexc.distance(position))
            score += self._approach_delta(ship.position.distance(nearest), hexc.distance(nearest))
        if ctx.enemies and ctx.pred_hexes and own_value > 0 and self.profile.w_retreat:
            start_dist = min(ship.position.distance(position) for position in ctx.pred_hexes)
            cand_dist = min(hexc.distance(position) for position in ctx.pred_hexes)
            score += own_value * self.profile.w_retreat * (cand_dist - start_dist) / self.profile.approach_range
        score += self._formation_factor(ship.position, hexc, heading, ctx.my_positions)
        if ctx.visible_torpedo_threat:
            exact = ctx.visible_torpedo_threat.get(hexc.label, 0.0)
            nearby = max(
                (value * 0.35 for label, value in ctx.visible_torpedo_threat.items()
                 if HexCoord.from_label(label).distance(hexc) == 1),
                default=0.0,
            )
            score -= self.profile.w_torpedo_avoid * max(exact, nearby)
        return score

    def _approach_delta(self, start_dist: int, cand_dist: int) -> float:
        """接近项：`w_approach>0` 时在射程外奖励缩短距离；`w_approach<0` 时把
        缩短距离变惩罚（等效奖励保持距离，猥琐保守）。"""
        w = self.profile.w_approach
        if w == 0 or start_dist <= self.profile.approach_range:
            return 0.0
        return w * (start_dist - cand_dist) / self.profile.approach_range

    def _formation_factor(
        self, ship_pos: HexCoord, hexc: HexCoord, heading: int, own_positions: list[HexCoord],
    ) -> float:
        """编队项：奖励候选格与最近己方舰距离落在 `formation_spacing`；`line_ahead`
        额外奖励最近己方舰在航向正前方 1-3 格的同向纵列。负数权重（乱阵）把
        "理想间距"变惩罚 → 刻意散开。"""
        if not self.profile.w_formation and not self.profile.line_ahead:
            return 0.0
        friends = [position for position in own_positions if position != ship_pos]
        if not friends:
            return 0.0
        d = min(hexc.distance(position) for position in friends)
        lo, hi = self.profile.formation_spacing
        mid = (lo + hi) / 2.0
        if lo <= d <= hi:
            base = 1.0
        else:
            base = max(-1.0, min(1.0, 1.0 - abs(d - mid) / max(mid, 1.0)))
        score = self.profile.w_formation * base
        if self.profile.line_ahead:
            friend = min(friends, key=lambda position: hexc.distance(position))
            dq, dr = HexCoord.direction_delta(heading)
            fq, fr = friend.q - hexc.q, friend.r - hexc.r
            collinear = fq * dr - fr * dq == 0
            ahead = fq * dq + fr * dr > 0
            if collinear and ahead and 1 <= hexc.distance(friend) <= 3:
                score += self.profile.line_ahead
        return score

    def _path_to(
        self, engine: IronBottomEngine, state, ship, hexc: HexCoord, heading: int | None,
    ) -> str | None:
        """用引擎 `movement_path` 生成到目标格（可选末航向）的路径并复核；失败返回 None。"""
        result = engine.movement_path(state, ship, hexc, heading)
        if not result["valid"]:
            return None
        preview = engine.movement_preview(state, ship, plan=result["plan"])
        if not preview["commitable"] or preview["current_label"] != hexc.label:
            return None
        return result["plan"]

    def _fallback_movement(
        self, engine: IronBottomEngine, state, ship,
        reserved: list[tuple[ShipState, MovementOrder]] | None = None,
    ) -> MovementOrder:
        """保证任意舰都有合法计划：`"0"` 在 forced_speed>0 / forced_circle 下非法，
        依次回退 `"0"` → 直行 max_cost → 首个可达格路径。"""
        reserved = reserved or []
        if engine.movement_preview(state, ship, plan="0")["commitable"]:
            order = MovementOrder(ship_id=ship.id, plan="0")
            if not self._movement_conflicts(engine, state, ship, order, reserved):
                return order
        candidates = engine.movement_candidates(state, ship, include_plans=False)
        if candidates["max_cost"] > 0:
            plan = str(candidates["max_cost"])
            if engine.movement_preview(state, ship, plan=plan)["commitable"]:
                order = MovementOrder(ship_id=ship.id, plan=plan)
                if not self._movement_conflicts(engine, state, ship, order, reserved):
                    return order
        for entry in candidates["reachable"]:
            hexc = HexCoord(q=entry["hex"]["q"], r=entry["hex"]["r"])
            plan = self._path_to(engine, state, ship, hexc, None)
            if plan is not None:
                order = MovementOrder(ship_id=ship.id, plan=plan)
                if not self._movement_conflicts(engine, state, ship, order, reserved):
                    return order
        # `movement_path` may choose a different shortest route to the same
        # endpoint and thereby miss the safe "copy the ship ahead" solution.
        # Replaying an already reserved same-heading manoeuvre preserves the
        # relative offset and is the final collision-free emergency option.
        for other, other_order in reversed(reserved):
            if other.heading != ship.heading:
                continue
            order = MovementOrder(ship_id=ship.id, plan=other_order.plan)
            if not engine.movement_preview(state, ship, plan=order.plan)["commitable"]:
                continue
            if not self._movement_conflicts(engine, state, ship, order, reserved):
                return order
        # Greedy batch planning can create a local dead end even though the
        # fleet has a safe assignment. Re-plan one previously reserved ship
        # together with the blocked ship; mutating the existing order object
        # also updates the already assembled OrderBatch entry.
        current_candidates = self._candidate_movement_orders(engine, state, ship)
        for index in range(len(reserved) - 1, -1, -1):
            other, other_order = reserved[index]
            fixed = reserved[:index] + reserved[index + 1:]
            for alternative in self._candidate_movement_orders(engine, state, other):
                if self._movement_conflicts(engine, state, other, alternative, fixed):
                    continue
                revised = fixed + [(other, alternative)]
                for current in current_candidates:
                    if self._movement_conflicts(engine, state, ship, current, revised):
                        continue
                    other_order.plan = alternative.plan
                    reserved[index] = (other, other_order)
                    return current
        # One-step repair is insufficient when three or more ships form a
        # cyclic blocking pattern. Solve the already planned prefix as a
        # deterministic constraint problem, then mutate its existing order
        # objects so the assembled batch remains coherent.
        assignment = self._collision_free_prefix_assignment(
            engine, state, [other for other, _order in reserved] + [ship],
            {other.id: order.plan for other, order in reserved},
        )
        if assignment:
            for index, (other, other_order) in enumerate(reserved):
                other_order.plan = assignment[other.id].plan
                reserved[index] = (other, other_order)
            return assignment[ship.id]
        raise ValueError(f"{ship.id}: 无友舰冲突的合法移动计划")

    def _collision_free_prefix_assignment(
        self, engine: IronBottomEngine, state, ships: list[ShipState],
        preferred: dict[str, str],
    ) -> dict[str, MovementOrder] | None:
        """Find a collision-free legal assignment for a blocked planning prefix.

        This is an emergency safety layer, not a tactical scorer.  Minimum
        remaining values and forward checking keep the rare search bounded;
        preferred existing plans are tried first for deterministic stability.
        """
        options: dict[str, list[MovementOrder]] = {}
        by_id = {ship.id: ship for ship in ships}
        for ship in ships:
            candidates = self._candidate_movement_orders(engine, state, ship)
            candidates.sort(key=lambda order: (
                0 if order.plan == preferred.get(ship.id) else 1,
                engine.movement_cost(order.plan, engine.movement_commands(order)),
                order.plan,
            ))
            options[ship.id] = candidates
            if not candidates:
                return None
        nodes = 0

        def compatible(ship_id: str, chosen: list[tuple[ShipState, MovementOrder]]):
            ship = by_id[ship_id]
            return [
                order for order in options[ship_id]
                if not self._movement_conflicts(engine, state, ship, order, chosen)
            ]

        def search(
            remaining: tuple[str, ...],
            chosen: list[tuple[ShipState, MovementOrder]],
            result: dict[str, MovementOrder],
        ) -> dict[str, MovementOrder] | None:
            nonlocal nodes
            if not remaining:
                return dict(result)
            ranked = [
                (compatible(ship_id, chosen), ship_id)
                for ship_id in remaining
            ]
            ranked.sort(key=lambda item: (len(item[0]), item[1]))
            candidates, ship_id = ranked[0]
            if not candidates:
                return None
            tail = tuple(item for item in remaining if item != ship_id)
            ship = by_id[ship_id]
            for order in candidates:
                nodes += 1
                if nodes > 100_000:
                    return None
                revised = chosen + [(ship, order)]
                if any(not compatible(other_id, revised) for other_id in tail):
                    continue
                result[ship_id] = order
                solved = search(tail, revised, result)
                if solved is not None:
                    return solved
                result.pop(ship_id, None)
            return None

        return search(tuple(sorted(by_id)), [], {})

    def _candidate_movement_orders(
        self, engine: IronBottomEngine, state, ship: ShipState,
    ) -> list[MovementOrder]:
        """枚举一舰的确定性合法计划集，供批次死端的一步回溯使用。"""
        plans: list[str] = []
        if engine.movement_preview(state, ship, plan="0")["commitable"]:
            plans.append("0")
        candidates = engine.movement_candidates(state, ship, include_plans=False)
        for entry in candidates["reachable"]:
            hexc = HexCoord(q=entry["hex"]["q"], r=entry["hex"]["r"])
            for heading in entry["final_headings"]:
                plan = self._path_to(engine, state, ship, hexc, heading)
                if plan is not None and plan not in plans:
                    plans.append(plan)
        return [MovementOrder(ship_id=ship.id, plan=plan) for plan in plans]

    # ------------------------------------------------------------------ 鱼雷

    def _plan_torpedoes(self, engine: IronBottomEngine, state, side: Side) -> list[TorpedoOrder]:
        """对最近可见敌舰调自动鱼雷系统；仅发射 `distance ≤ torpedo_max_range`
        且 `expected_hits ≥ torpedo_min_expected` 的组合，每发射器一条订单。
        launch_at_mf/launch_hex/bearing 直接采纳组合（来自己方封存移动计划），
        天然满足校验。想定禁射由引擎 `_torpedo_candidates` blocked 自动覆盖。"""
        if self.profile.torpedo_doctrine != "legacy":
            orders, self._last_torpedo_audit = AdaptiveTorpedoPlanner(self.profile).orders(
                engine, state, side
            )
            return orders
        self._last_torpedo_audit = None
        obs = engine.observe(state.game_id, side)
        own_pos = [ship.position for ship in obs.ships if ship.side == side and not ship.sunk and ship.position]
        enemies = [ship for ship in obs.ships if ship.side != side and not ship.sunk and ship.position]
        if not own_pos or not enemies:
            return []
        nearest = min(enemies, key=lambda enemy: min(enemy.position.distance(pos) for pos in own_pos))
        assist = engine.torpedo_assist(state, side, target_id=nearest.id)
        orders: list[TorpedoOrder] = []
        used: set[tuple[str, str]] = set()
        for combo in assist["combos"]:
            if combo["blocked_reason"] or combo.get("friendly_risk"):
                continue
            if combo["distance"] > self.profile.torpedo_max_range or combo["expected_hits"] < self.profile.torpedo_min_expected:
                continue
            key = (combo["ship_id"], combo["launcher_id"])
            if key in used:
                continue
            used.add(key)
            orders.append(TorpedoOrder(
                ship_id=combo["ship_id"],
                launcher_id=combo["launcher_id"],
                count=combo["salvo_size"],
                launch_at_mf=combo["launch_at_mf"],
                launch_hex=HexCoord.from_label(combo["launch_hex"]),
                bearing=combo["launch_heading"],
                launch_side=combo["launch_side"],
                launch_angle=combo["launch_angle"],
                setting_index=combo["setting_index"],
            ))
        return orders

    # ------------------------------------------------------------------ 炮击

    def _plan_gunnery(self, engine: IronBottomEngine, state, side: Side, rng: random.Random | None = None) -> list[GunneryOrder]:
        """对每艘候选舰按 `expected_hits × 目标价值` 打分，softmax 概率抽样一个目标
        （温度>0 且有 RNG 时）；温度=0 退化为选最高分目标。目标/射界/期望命中全部
        来自引擎 `gunnery_target_options`，AI 不复制任何规则公式。blocked 舰（想定
        禁射/炮损/无射界）由引擎排除，未产出即不产订单（GUNNERY 无全舰覆盖校验）。
        敌情一律走 observe() 的 PublicShip（绝不读 `state.ships[敌].hull`）。"""
        obs = engine.observe(state.game_id, side)
        enemies = [ship for ship in obs.ships if ship.side != side and not ship.sunk and ship.position]
        max_vp = max((ship.vp for ship in obs.ships), default=1)
        value_of = {enemy.id: self._value_factor(enemy, max_vp) for enemy in enemies}
        orders: list[GunneryOrder] = []
        for candidate in engine.gunnery_target_options(state, side):
            if candidate["blocked_reason"] or not candidate["targets"]:
                continue
            scored = [
                (target["expected_hits"] * value_of.get(target["target_id"], 1.0), target)
                for target in candidate["targets"]
            ]
            if not scored:
                continue
            chosen = self._sample_weighted(scored, self.profile.temperature, rng)
            orders.append(GunneryOrder(
                ship_id=candidate["ship_id"],
                primary_target=chosen["target_id"],
                mounts=[
                    GunMountOrder(mount_id=mount_id, target_id=chosen["target_id"])
                    for mount_id in chosen["mount_ids"]
                ],
            ))
        return orders
