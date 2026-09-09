"""乱打 AI（RandomCommander）：在所有合法选择里均匀随机选择，用于对照实验。

与战术状态机的区别：不按启发式打分，而是对每一阶段的可选空间均匀随机抽选——
移动选随机可达 (格, 航向)、炮击选随机合法目标、鱼雷选随机合法齐射组合、
增援选随机合法入口。设计约束：

- 合法空间全部来自引擎只读候选接口（`movement_candidates` / `gunnery_target_options`
  / `_assist_launch_combos` / `_reinforcement_candidates`），绝不复制规则常量、
  绝不读敌方私有状态（只经 `observe` 可见信息）。
- 随机源按 (seed, turn, side, phase) 纯整数派生（与战术 AI 同纪律），同 seed
  跨进程/跨 PYTHONHASHSEED 完全可复现；不碰模块级 `random.*`、不用 hash()/set 迭代序。
- 兜底：随机批次若被 `validate_orders` 拒绝（理论上不应发生），回退到确定性合法
  策略（`DeterministicCommander`），保证乱打 AI 永不产出非法订单导致对局失败。
"""

from __future__ import annotations

import random

from .engine import IronBottomEngine
from .llm import DeterministicCommander
from .models import (
    AIPlanSheet,
    ContactMovementOrder,
    ContactSetupOrder,
    GunMountOrder,
    GunneryOrder,
    HexCoord,
    MAP_COLUMNS,
    MAP_ROWS,
    LLMCallAudit,
    MovementOrder,
    OrderBatch,
    Phase,
    ReinforcementOrder,
    Side,
    TorpedoOrder,
)

# 各阶段独立随机相位码（与战术 AI 的 _AI_PHASE_INT 不同取值，避免风格间序列相关）
_RANDOM_PHASE_INT: dict[Phase, int] = {
    Phase.CONTACT_SETUP: 2,
    Phase.REINFORCEMENT: 4,
    Phase.MOVEMENT_PLANNING: 6,
    Phase.TORPEDO_PLANNING: 8,
    Phase.GUNNERY: 10,
}


class RandomCommander(DeterministicCommander):
    """在所有合法选择里均匀随机抽选的指挥官；`_finalize` 前先随机选，再校验兜底。"""

    model = "random-v1"

    def _rng(self, state, side: Side) -> random.Random:
        """本阶段独立随机源：纯整数 (seed, turn, side, phase) 派生，与引擎骰子流隔离。
        每阶段派生一次并下传给该阶段全部舰的抽样（绝不分舰派生，保证序列可复现）。"""
        side_int = 1 if side == Side.AXIS else 2
        phase_int = _RANDOM_PHASE_INT.get(state.phase, 0)
        rng_seed = (
            state.seed * 1_000_003 + state.turn * 10_007
            + side_int * 101 + phase_int * 11 + 37
        )
        return random.Random(rng_seed)

    # ------------------------------------------------------------------ 各阶段随机选

    def _random_contacts(
        self, engine: IronBottomEngine, game_id: str, side: Side, rng: random.Random,
    ) -> list[ContactSetupOrder]:
        """随机合法隐蔽编队：打散编队划分、随机边缘入口（保持整编队在地图内）。
        结构复刻 `DeterministicCommander._contact_setup`，但把"取首个合法候选"
        改为"打乱候选后取首个"，并对舰船分组做随机洗牌。"""
        state = engine.get(game_id)
        ship_ids = [
            ship_id for ship_id in state.contact_reserve_positions
            if state.ships[ship_id].side == side
        ]
        if not ship_ids:
            return []
        rng.shuffle(ship_ids)
        split = max(1, len(ship_ids) // 2)
        groups = [ship_ids[:split], ship_ids[split:]]
        markers = sorted(
            (marker for marker in state.markers if marker.kind == "contact" and marker.secret_side == side),
            key=lambda marker: marker.id,
        )
        columns, rows = state.map_columns, state.map_rows
        candidates = self._edge_coords(columns=columns, rows=rows)
        if side == Side.ALLIES:
            candidates.reverse()
        used: set[str] = set()
        orders: list[ContactSetupOrder] = []

        def has_inward_run(candidate: HexCoord, distance: int) -> bool:
            position = candidate
            try:
                heading = self._inward_heading(candidate, columns=columns, rows=rows)
                for _ in range(distance):
                    position = position.neighbor(heading, columns=columns, rows=rows)
            except ValueError:
                return False
            return True

        def pick(entry: HexCoord, distance: int, group: list[str]) -> bool:
            if entry.label in used or not has_inward_run(entry, distance):
                return False
            if not group:
                return True
            anchor = state.contact_reserve_positions[group[0]]
            return all(
                engine._coord_on_map(
                    entry.q + state.contact_reserve_positions[ship_id].q - anchor.q,
                    entry.r + state.contact_reserve_positions[ship_id].r - anchor.r,
                    columns=columns, rows=rows,
                )
                for ship_id in group
            )

        for marker, group in zip(markers[:2], groups, strict=True):
            pool = [candidate for candidate in candidates if candidate.label not in used]
            rng.shuffle(pool)
            entry = next((candidate for candidate in pool if pick(candidate, 4, group)), None)
            if entry is None:  # 兜底：任意未用且可内进的边缘格（极罕见）
                entry = next(candidate for candidate in candidates
                             if candidate.label not in used and has_inward_run(candidate, 4))
            used.add(entry.label)
            orders.append(ContactSetupOrder(
                marker_id=marker.id,
                entry_hex=entry,
                heading=self._inward_heading(entry, columns=columns, rows=rows),
                speed=4,
                ship_ids=group,
            ))
        for marker in markers[2:]:
            pool = [candidate for candidate in candidates if candidate.label not in used]
            rng.shuffle(pool)
            entry = next((candidate for candidate in pool if pick(candidate, 5, [])), None)
            if entry is None:
                entry = next(candidate for candidate in candidates
                             if candidate.label not in used and has_inward_run(candidate, 5))
            used.add(entry.label)
            orders.append(ContactSetupOrder(
                marker_id=marker.id,
                entry_hex=entry,
                heading=self._inward_heading(entry, columns=columns, rows=rows),
                speed=5,
            ))
        return orders

    def _random_reinforcements(
        self, engine: IronBottomEngine, game_id: str, side: Side, rng: random.Random,
    ) -> list[ReinforcementOrder]:
        """随机合法增援入场：每艘待入场舰随机取一个合法入口格（互不相同），
        航向 1..6、速度 0..当前最大航速 均匀随机。"""
        state = engine.get(game_id)
        ships = [
            ship for ship in state.ships.values()
            if ship.side == side and ship.position is None
            and ship.reinforcement_turn == state.turn and state.reinforcement_available
        ]
        if not ships:
            return []
        occupied = {ship.position.label for ship in state.ships.values() if ship.position and not ship.sunk}
        entries = [
            HexCoord(q=q, r=row - (q - (q & 1)) // 2)
            for q in range(state.map_columns) for row in range(state.map_rows)
        ]
        entries = [
            entry for entry in entries
            if engine._reinforcement_entry_legal(state, entry)
            and entry.label not in occupied and not engine._terrain_impassable(state, entry)
        ]
        rng.shuffle(entries)
        orders: list[ReinforcementOrder] = []
        for ship in ships:
            if not entries:
                break
            entry = entries.pop()
            orders.append(ReinforcementOrder(
                ship_id=ship.id,
                entry_hex=entry,
                heading=rng.randint(1, 6),
                speed=rng.randint(0, ship.max_speed_for_turn(state.turn)),
            ))
        return orders

    def _random_movement(
        self, engine: IronBottomEngine, game_id: str, side: Side, rng: random.Random,
    ) -> tuple[list[MovementOrder], list[ContactMovementOrder], dict[str, str]]:
        """随机合法移动：每艘活动舰从 `movement_candidates` 可达格中随机取一个
        (格, 末航向)，用 `movement_path` 生成合法计划；无候选回退 `_stationary_plan`。"""
        state = engine.get(game_id)
        obs = engine.observe(game_id, side)
        movement: list[MovementOrder] = []
        intents: dict[str, str] = {}
        for ship in state.ships.values():
            if ship.side != side or ship.sunk or not ship.position:
                continue
            candidates = engine.movement_candidates(state, ship, include_plans=False)["reachable"]
            plan = None
            if candidates:
                entry = rng.choice(candidates)
                hexc = HexCoord(q=entry["hex"]["q"], r=entry["hex"]["r"])
                heading = rng.choice(entry["final_headings"])
                path = engine.movement_path(state, ship, hexc, heading)
                if path.get("valid"):
                    plan = path["plan"]
            if plan is None:
                plan = self._stationary_plan(engine, game_id, ship.id)
            movement.append(MovementOrder(ship_id=ship.id, plan=plan))
            intents[ship.id] = "乱打：随机移动"
        contact_movement = [
            ContactMovementOrder(marker_id=marker.id, plan="4")
            for marker in obs.markers
            if marker.kind == "contact" and marker.secret_side == side and marker.position
        ]
        intents.update({order.marker_id: "乱打：随机推进" for order in contact_movement})
        return movement, contact_movement, intents

    def _random_torpedoes(
        self, engine: IronBottomEngine, game_id: str, side: Side, rng: random.Random,
    ) -> list[TorpedoOrder]:
        """随机合法鱼雷：对每枚可用发射器，以 50% 概率决定发射；发射时随机取一个
        合法齐射组合（`_assist_launch_combos` 已按引擎候选枚举，含全部字段）。"""
        state = engine.get(game_id)
        combos = engine._assist_launch_combos(state, side)
        orders: list[TorpedoOrder] = []
        by_launcher: dict[tuple[str, str], list[dict]] = {}
        for combo in combos:
            by_launcher.setdefault((combo["ship_id"], combo["launcher_id"]), []).append(combo)
        for (ship_id, launcher_id), options in by_launcher.items():
            if rng.random() < 0.5:
                combo = rng.choice(options)
                orders.append(TorpedoOrder(
                    ship_id=combo["ship_id"],
                    launcher_id=combo["launcher_id"],
                    count=combo["salvo_size"],
                    launch_at_mf=combo["launch_at_mf"],
                    launch_hex=combo["launch_hex"],
                    bearing=combo["launch_heading"],
                    launch_side=combo["launch_side"],
                    launch_angle=combo["launch_angle"],
                    setting_index=combo["setting_index"],
                ))
        return orders

    def _random_gunnery(
        self, engine: IronBottomEngine, game_id: str, side: Side, rng: random.Random,
    ) -> list[GunneryOrder]:
        """随机合法炮击：每艘有合法目标/射界的舰以 50% 概率开火，随机取一个目标，
        该目标的全部可指向炮位一次性齐射（`gunnery_target_options` 已含全部射界）。"""
        state = engine.get(game_id)
        orders: list[GunneryOrder] = []
        for candidate in engine.gunnery_target_options(state, side):
            if candidate["blocked_reason"] or not candidate["targets"]:
                continue
            if rng.random() < 0.5:
                chosen = rng.choice(candidate["targets"])
                orders.append(GunneryOrder(
                    ship_id=candidate["ship_id"],
                    primary_target=chosen["target_id"],
                    mounts=[
                        GunMountOrder(mount_id=mount_id, target_id=chosen["target_id"])
                        for mount_id in chosen["mount_ids"]
                    ],
                ))
        return orders

    # ------------------------------------------------------------------ 总入口

    def choose_plan(
        self, engine: IronBottomEngine, game_id: str, side: Side,
    ) -> tuple[AIPlanSheet, OrderBatch, list[LLMCallAudit]]:
        state = engine.get(game_id)
        rng = self._rng(state, side)
        batch = OrderBatch(side=side, phase=state.phase)
        intents: dict[str, str] = {}
        if state.phase == Phase.CONTACT_SETUP:
            batch.contacts = self._random_contacts(engine, game_id, side, rng)
            intents = {order.marker_id: "乱打：随机隐蔽入口" for order in batch.contacts}
        elif state.phase == Phase.REINFORCEMENT:
            batch.reinforcements = self._random_reinforcements(engine, game_id, side, rng)
            intents = {order.ship_id: "乱打：随机入场口" for order in batch.reinforcements}
        elif state.phase == Phase.MOVEMENT_PLANNING:
            batch.movement, batch.contact_movement, intents = self._random_movement(engine, game_id, side, rng)
        elif state.phase == Phase.TORPEDO_PLANNING:
            batch.torpedoes = self._random_torpedoes(engine, game_id, side, rng)
            intents = {order.ship_id: "乱打：随机发射" for order in batch.torpedoes}
        elif state.phase == Phase.GUNNERY:
            batch.gunnery = self._random_gunnery(engine, game_id, side, rng)
            intents = {order.ship_id: "乱打：随机开火" for order in batch.gunnery}
        else:
            raise ValueError(f"No orders may be chosen during automatic phase {state.phase}")
        validation = engine.validate_orders(state.game_id, batch)
        if validation.valid:
            plan = AIPlanSheet(
                turn=state.turn,
                phase=state.phase,
                situation_summary=f"{side.value} 方在 {state.phase.value} 阶段执行乱打策略（均匀随机合法选择）。",
                phase_goal="在所有合法选择里均匀随机选取",
                unit_intents=intents,
                orders=batch.model_dump(mode="json"),
                contingency=["若订单被拒绝则回退确定性合法策略"],
            )
            return plan, batch, [self._audit(state, side, validation, 1)]
        # 兜底：随机批次被拒 → 用确定性合法策略（保持对局可继续）。
        fallback_plan, fallback_batch, fallback_audits = super().choose_plan(engine, game_id, side)
        audit = self._audit(state, side, validation, 1)
        audit.valid = False
        audit.validation_errors = validation.errors + ["fallback to deterministic"]
        return fallback_plan, fallback_batch, [audit, *fallback_audits]

    def _audit(self, state, side: Side, validation, attempt: int) -> LLMCallAudit:
        return LLMCallAudit(
            side=side,
            turn=state.turn,
            phase=state.phase,
            attempt=attempt,
            model=self.model,
            elapsed_ms=0,
            valid=validation.valid,
            validation_errors=validation.errors,
        )
