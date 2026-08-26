from __future__ import annotations

import json
import os
import time
from abc import ABC, abstractmethod
from typing import Any

import httpx

from .engine import IronBottomEngine
from .state_export import export_frame, render_board
from .models import (
    AIPlanSheet,
    ContactMovementOrder,
    ContactSetupOrder,
    GameState,
    HexCoord,
    LLMCallAudit,
    MovementOrder,
    OrderBatch,
    Phase,
    ReinforcementOrder,
    Side,
)


class LLMCommander(ABC):
    model = "unknown"

    @abstractmethod
    def choose_plan(
        self, engine: IronBottomEngine, game_id: str, side: Side
    ) -> tuple[AIPlanSheet, OrderBatch, list[LLMCallAudit]]:
        raise NotImplementedError

    def choose_orders(self, engine: IronBottomEngine, game_id: str, side: Side) -> OrderBatch:
        return self.choose_plan(engine, game_id, side)[1]


class DeterministicCommander(LLMCommander):
    """Offline phase-aware policy used for deterministic integration tests."""

    model = "deterministic-fixture"

    @staticmethod
    def _edge_coords() -> list[HexCoord]:
        result: list[HexCoord] = []
        for q in range(34):
            for display_row in (0, 26):
                result.append(HexCoord(q=q, r=display_row - (q - (q & 1)) // 2))
        for display_row in range(1, 26):
            result.append(HexCoord(q=0, r=display_row))
            result.append(HexCoord(q=33, r=display_row - 16))
        return result

    @staticmethod
    def _inward_heading(coord: HexCoord) -> int:
        display_row = coord.r + (coord.q - (coord.q & 1)) // 2
        if display_row == 0:
            return 3
        if display_row == 26:
            return 6
        if coord.q == 0:
            return 2
        if coord.q == 33:
            return 5
        raise ValueError(f"{coord.label} is not on a map edge")

    def _contact_setup(
        self, engine: IronBottomEngine, game_id: str, side: Side
    ) -> list[ContactSetupOrder]:
        state = engine.get(game_id)
        ship_ids = [
            ship_id for ship_id in state.contact_reserve_positions
            if state.ships[ship_id].side == side
        ]
        split = max(1, len(ship_ids) // 2)
        groups = [ship_ids[:split], ship_ids[split:]]
        markers = sorted(
            (marker for marker in state.markers if marker.kind == "contact" and marker.secret_side == side),
            key=lambda marker: marker.id,
        )
        candidates = self._edge_coords()
        if side == Side.ALLIES:
            candidates.reverse()
        used: set[str] = set()
        orders: list[ContactSetupOrder] = []

        def has_inward_run(candidate: HexCoord, distance: int) -> bool:
            position = candidate
            try:
                heading = self._inward_heading(candidate)
                for _ in range(distance):
                    position = position.neighbor(heading)
            except ValueError:
                return False
            return True

        for marker, group in zip(markers[:2], groups, strict=True):
            anchor = state.contact_reserve_positions[group[0]]
            entry = next(
                candidate for candidate in candidates
                if candidate.label not in used
                and has_inward_run(candidate, 4)
                and all(
                    engine._coord_on_map(
                        candidate.q + state.contact_reserve_positions[ship_id].q - anchor.q,
                        candidate.r + state.contact_reserve_positions[ship_id].r - anchor.r,
                    )
                    for ship_id in group
                )
            )
            used.add(entry.label)
            orders.append(ContactSetupOrder(
                marker_id=marker.id,
                entry_hex=entry,
                heading=self._inward_heading(entry),
                speed=4,
                ship_ids=group,
            ))
        for marker in markers[2:]:
            entry = next(
                candidate for candidate in candidates
                if candidate.label not in used and has_inward_run(candidate, 5)
            )
            used.add(entry.label)
            orders.append(ContactSetupOrder(
                marker_id=marker.id,
                entry_hex=entry,
                heading=self._inward_heading(entry),
                speed=5,
            ))
        return orders

    @staticmethod
    def _reinforcements(
        engine: IronBottomEngine, game_id: str, side: Side
    ) -> list[ReinforcementOrder]:
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
            for q in range(34) for row in range(27)
        ]
        entries = [
            entry for entry in entries
            if engine._reinforcement_entry_legal(state, entry)
            and entry.label not in occupied and not engine._terrain_impassable(state, entry)
        ]
        return [
            ReinforcementOrder(
                ship_id=ship.id,
                entry_hex=entries[index],
                heading=1,
                speed=0,
            )
            for index, ship in enumerate(ships)
        ]

    @staticmethod
    def _stationary_plan(engine: IronBottomEngine, game_id: str, ship_id: str) -> str:
        """基线移动计划：优先 `"0"`；桥楼/舵损伤（forced_speed>0、forced_circle）
        使 `"0"` 非法时回退到直行最大成本或首个可达格路径，保证计划永远合法。"""
        state = engine.get(game_id)
        ship = state.ships[ship_id]
        if engine.movement_preview(state, ship, plan="0")["commitable"]:
            return "0"
        candidates = engine.movement_candidates(state, ship)
        if candidates["max_cost"] > 0:
            plan = str(candidates["max_cost"])
            if engine.movement_preview(state, ship, plan=plan)["commitable"]:
                return plan
        for entry in candidates["reachable"]:
            hexc = HexCoord(q=entry["hex"]["q"], r=entry["hex"]["r"])
            result = engine.movement_path(state, ship, hexc, None)
            if result["valid"] and engine.movement_preview(state, ship, plan=result["plan"])["commitable"]:
                return result["plan"]
        return "0"

    def choose_plan(
        self, engine: IronBottomEngine, game_id: str, side: Side
    ) -> tuple[AIPlanSheet, OrderBatch, list[LLMCallAudit]]:
        state = engine.get(game_id)
        observation = engine.observe(game_id, side)
        batch = OrderBatch(side=side, phase=state.phase)
        intents: dict[str, str] = {}
        if state.phase == Phase.CONTACT_SETUP:
            batch.contacts = self._contact_setup(engine, game_id, side)
            intents = {order.marker_id: "部署隐蔽编队" for order in batch.contacts}
        elif state.phase == Phase.REINFORCEMENT:
            batch.reinforcements = self._reinforcements(engine, game_id, side)
            intents = {order.ship_id: "按想定边界进入" for order in batch.reinforcements}
        elif state.phase == Phase.MOVEMENT_PLANNING:
            own = [ship for ship in observation.ships if ship.side == side and not ship.sunk and ship.position]
            batch.movement = [
                MovementOrder(ship_id=ship.id, plan=self._stationary_plan(engine, state.game_id, ship.id))
                for ship in own
            ]
            batch.contact_movement = [
                ContactMovementOrder(marker_id=marker.id, plan="4")
                for marker in observation.markers
                if marker.kind == "contact" and marker.secret_side == side and marker.position
            ]
            intents = {ship.id: "保持位置" for ship in own}
        elif state.phase not in {Phase.TORPEDO_PLANNING, Phase.GUNNERY}:
            raise ValueError(f"No orders may be chosen during automatic phase {state.phase}")
        plan = AIPlanSheet(
            turn=state.turn,
            phase=state.phase,
            situation_summary=f"{side.value} 方在 {state.phase.value} 阶段执行确定性测试策略。",
            phase_goal="提交完整合法订单并保持状态可重放",
            unit_intents=intents,
            orders=batch.model_dump(mode="json"),
            contingency=["若订单被拒绝则测试失败"],
        )
        validation = engine.validate_orders(game_id, batch)
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


# ── 提示词工程（投影一）──────────────────────────────────────────────
# 棋盘 + 世界态帧 + few-shot 示范输出 + 反过度思考纪律。规则常量绝不复制到引擎外：
# 距离公式/符号约定只作为给 LLM 的读取提示，裁决仍唯一由引擎负责。

_DISCIPLINE_SYSTEM_PROMPT = (
    "你是铁底湾的回响 IV（二战太平洋海战六角格兵棋）中某阵营的舰队指挥官。\n"
    "任务只有一件：根据【棋盘】【世界态帧】与【合法动作】，输出一个完整、合法的 AIPlanSheet "
    "JSON（其 orders 字段是 OrderBatch，绑定本方 side 与当前 phase）。\n"
    "响应必须以 `{` 开头，正文只有 JSON，无任何解释文字。\n"
    "【思考纪律】（逐条强制）：\n"
    "1. 只做一件事：写完完整合法的 JSON 立即停止。不补充、不复述、不解释。\n"
    "2. 禁止候选枚举：不要写「方案 A/B/C」、不要列多个选项再挑。选定一个保守合法动作直接输出。\n"
    "3. 禁止自我怀疑与复读：不写「也许」「不确定」「再检查一遍」这类句子。敌方信息不明时，"
    "用一个保守合法动作直接输出，不纠结。\n"
    "4. 禁止重复推导：不要重述规则、距离公式、或已给出棋盘/帧里的内容。\n"
    "5. 篇幅硬限：situation_summary ≤ 80 字，phase_goal ≤ 40 字，contingency ≤ 2 条且每条一句话。\n"
    "6. 产出即终稿：不回头修订自己。\n"
    "距离：六角格轴向距离 = (|Δq| + |Δr| + |Δq+Δr|) / 2。用【世界态帧】里各实体的 q/r 计算，"
    "不要数棋盘格子（ASCII 棋盘排版对六角格只是近似）。例：O14(q14,r6) → P15(q15,r7) "
    "距离 = (1+1+2)/2 = 2。\n"
    "领域指导（不要自行推导规则）：\n"
    "- 【合法动作】里的 movement_candidates / torpedo_candidates / gunnery_candidates 是引擎算好的"
    "合法值（可达格、speed 范围、launcher/sides/angles/settings/launch_positions、mount_ids）。直接采用"
    "候选组合，不要自己重算方位、射程、速度或齐射修正。\n"
    "- MovementOrder：plan 的直航 MF 总数必须等于声明的 speed；不移动就 plan=\"0\" 且 speed 留 0 或 null。\n"
    "- TorpedoOrder：先在该舰 torpedo_candidates 的 launch_positions 里选一个发射 MF 序号 i"
    "（第 0 项=开火前，之后每项=第 i 个机动点）。launch_at_mf=i，launch_hex=launch_positions[i].hex，"
    "bearing=launch_positions[i].heading。bearing 是发射瞬间舰船航向（1..6），不是鱼雷行进方向；"
    "不要用 relative_heading 或 launch_side/launch_angle 去换算 bearing。launcher_id 取该舰 launchers 里 "
    "loaded>0 且 sides 含所需舷的；launch_side 取该发射器 sides 之一，launch_angle 取 angles 之一"
    "（A/B/X/Y），setting_index 取 settings 里的 index。\n"
    "- 地图边缘：舰船不要驶出棋盘边缘（棋盘 34 列×27 行，边缘行号见帧里各舰的 hex）。舰队接近"
    "上下边缘时应减速或转向，避免整队压线；若同时有其它算子（鱼雷/残骸/舰）贴住对侧边缘，引擎"
    "无法平移整个世界，对局会中止。鱼雷发射也要选择让鱼雷航迹留在图内的方位。\n"
    "所有 ship_id / marker_id / target_id 必须来自【世界态帧】或【合法动作】；示例里的 "
    "SAMPLE- 开头 id 是占位符，照抄会被引擎判非法并在重试时告知。"
)

# 每订单阶段一个完整 AIPlanSheet 示范（orders 字段与 OrderBatch 结构一致）。
# 全部 id 用 SAMPLE- 保留前缀占位；turn/phase/side 在调用时注入当前值。
_FEW_SHOT_BY_PHASE: dict[str, dict[str, Any]] = {
    "contact_setup": {
        "turn": 1, "phase": "contact_setup",
        "situation_summary": "轴心舰队在北侧岛链外部署两枚隐蔽编队标记，预置南下入口。",
        "phase_goal": "分配隐蔽编队入口与航向。",
        "unit_intents": {"SAMPLE-CM-1": "北缘N2入口三舰编队", "SAMPLE-CM-2": "西缘B3入口单舰"},
        "orders": {
            "side": "axis", "phase": "contact_setup",
            "reinforcements": [],
            "contacts": [
                {"marker_id": "SAMPLE-CM-1", "entry_hex": {"q": 14, "r": -3}, "heading": 3, "speed": 4,
                 "ship_ids": ["SAMPLE-U-KM-0001", "SAMPLE-U-KM-0002", "SAMPLE-U-KM-0003"]},
                {"marker_id": "SAMPLE-CM-2", "entry_hex": {"q": 0, "r": 10}, "heading": 2, "speed": 5},
            ],
            "contact_movement": [], "movement": [], "gunnery": [], "torpedoes": [],
            "smoke_ships": [], "smoke": [], "illumination": [], "searchlights": [],
            "confirmation": {"ready": True},
        },
        "contingency": ["入口格被占时改相邻北缘入口。"],
    },
    "reinforcement": {
        "turn": 2, "phase": "reinforcement",
        "situation_summary": "盟军增援舰按想定自南缘进入，本回合可部署两艘。",
        "phase_goal": "在合法南缘入口部署增援。",
        "unit_intents": {"SAMPLE-U-RN-0001": "南缘V26进入", "SAMPLE-U-RN-0002": "南缘Z25进入"},
        "orders": {
            "side": "allies", "phase": "reinforcement",
            "reinforcements": [
                {"ship_id": "SAMPLE-U-RN-0001", "entry_hex": {"q": 21, "r": 10}, "heading": 6, "speed": 0},
                {"ship_id": "SAMPLE-U-RN-0002", "entry_hex": {"q": 25, "r": 9}, "heading": 6, "speed": 0},
            ],
            "contacts": [], "contact_movement": [], "movement": [], "gunnery": [], "torpedoes": [],
            "smoke_ships": [], "smoke": [], "illumination": [], "searchlights": [],
            "confirmation": {"ready": True},
        },
        "contingency": ["入口被占则选相邻南缘合法入口。"],
    },
    "movement_planning": {
        "turn": 2, "phase": "movement_planning",
        "situation_summary": "轴心舰队以4节纵队南下，各舰保持间距并远离鱼雷轨道。",
        "phase_goal": "全舰队合法移动并保持队形。",
        "unit_intents": {"SAMPLE-U-KM-0001": "直行4节", "SAMPLE-U-KM-0002": "右转1格保持间距"},
        "orders": {
            "side": "axis", "phase": "movement_planning",
            "movement": [
                {"ship_id": "SAMPLE-U-KM-0001", "plan": "4", "speed": None, "commands": []},
                {"ship_id": "SAMPLE-U-KM-0002", "plan": "1S3", "speed": None, "commands": []},
            ],
            "contact_movement": [{"marker_id": "SAMPLE-CM-1", "plan": "4"}],
            "contacts": [], "reinforcements": [], "gunnery": [], "torpedoes": [],
            "smoke_ships": [], "smoke": [], "illumination": [], "searchlights": [],
            "confirmation": {"ready": True},
        },
        "contingency": ["若4节非法则用引擎接受的最小速度。"],
    },
    "torpedo_planning": {
        "turn": 3, "phase": "torpedo_planning",
        "situation_summary": "盟军驱逐舰前出，对轴心旗舰发射扇形鱼雷。",
        "phase_goal": "用装填完成的发射器发射一组鱼雷。",
        "unit_intents": {"SAMPLE-U-RN-0003": "左舷发射器齐射2枚"},
        "orders": {
            "side": "allies", "phase": "torpedo_planning",
            "torpedoes": [
                {"ship_id": "SAMPLE-U-RN-0003", "target_id": "SAMPLE-U-KM-0001", "count": 2,
                 "speed": "fast", "launcher_id": "SAMPLE-L-0001", "launch_at_mf": 4,
                 "launch_hex": {"q": 14, "r": 6}, "bearing": 3, "launch_side": "port",
                 "launch_angle": "A", "setting_index": 0},
            ],
            "reinforcements": [], "contacts": [], "contact_movement": [], "movement": [],
            "gunnery": [], "smoke_ships": [], "smoke": [], "illumination": [], "searchlights": [],
            "confirmation": {"ready": True},
        },
        "contingency": ["若发射格非法则顺延到下一机动时刻。"],
    },
    "gunnery": {
        "turn": 3, "phase": "gunnery",
        "situation_summary": "轴心主力对盟军旗舰集中射击，压制其舰桥。",
        "phase_goal": "主炮齐射盟军旗舰。",
        "unit_intents": {"SAMPLE-U-KM-0001": "主炮集火SAMPLE-E-RN-0001"},
        "orders": {
            "side": "axis", "phase": "gunnery",
            "gunnery": [
                {"ship_id": "SAMPLE-U-KM-0001", "primary_target": "SAMPLE-E-RN-0001",
                 "secondary_target": None, "searchlight_target": None,
                 "mounts": [{"mount_id": "SAMPLE-M-0001", "target_id": "SAMPLE-E-RN-0001"}]},
            ],
            "reinforcements": [], "contacts": [], "contact_movement": [], "movement": [],
            "torpedoes": [], "smoke_ships": [], "smoke": [], "illumination": [], "searchlights": [],
            "confirmation": {"ready": True},
        },
        "contingency": ["若目标沉没则转打最近敌舰。"],
    },
}


def _few_shot_for(state: GameState, side: Side) -> dict[str, Any]:
    """当前阶段的 few-shot 示范，turn/phase/orders.side 注入当前值。"""
    template = _FEW_SHOT_BY_PHASE.get(state.phase.value)
    if template is None:
        return {}
    example = json.loads(json.dumps(template))
    example["turn"] = state.turn
    example["phase"] = state.phase.value
    example["orders"]["side"] = side.value
    return example


class OpenAICompatibleCommander(LLMCommander):
    """DeepSeek/OpenAI-compatible JSON adapter with no silent fallback.

    提示词 = 棋盘 + 世界态帧 + 合法动作 + few-shot 示范 + 【思考纪律】。可选
    `thinking_enabled`：开启时 DeepSeek 返回 reasoning_content，采集进
    LLMCallAudit.reasoning_preview，供观察思考过程/找死循环点。"""

    def __init__(
        self,
        endpoint: str = "https://api.deepseek.com",
        model: str = "deepseek-v4-flash",
        api_key_env: str = "DEEPSEEK_API_KEY",
        timeout: float = 45,
        max_tokens: int | None = None,
        thinking_enabled: bool = False,
        reasoning_effort: str | None = None,
        client: httpx.Client | None = None,
    ) -> None:
        self.endpoint = endpoint.rstrip("/")
        self.model = model
        self.api_key_env = api_key_env
        self.timeout = timeout
        self.thinking_enabled = thinking_enabled
        # thinking 开启时 completion 预算会被 reasoning 吃掉，须加大 max_tokens 防 JSON 截断。
        self.reasoning_effort = reasoning_effort or ("low" if thinking_enabled else None)
        self.max_tokens = max_tokens or (6000 if thinking_enabled else 2400)
        self.client = client

    def choose_plan(
        self, engine: IronBottomEngine, game_id: str, side: Side
    ) -> tuple[AIPlanSheet, OrderBatch, list[LLMCallAudit]]:
        state = engine.get(game_id)
        api_key = os.environ.get(self.api_key_env)
        if not api_key:
            raise RuntimeError(f"{self.api_key_env} is not configured")
        prompt: dict[str, Any] = {
            "board": render_board(state, engine, side),
            "world_state": export_frame(state, engine, side),
            "legal_actions": [item.model_dump(mode="json") for item in engine.legal_actions(game_id, side)],
            "order_batch_json_schema": OrderBatch.model_json_schema(),
            "plan_sheet_json_schema": AIPlanSheet.model_json_schema(),
            "few_shot_example_output": _few_shot_for(state, side),
        }
        payload: dict[str, Any] = {
            "model": self.model,
            "temperature": 0,
            "max_tokens": self.max_tokens,
            "response_format": {"type": "json_object"},
            "thinking": {"type": "enabled" if self.thinking_enabled else "disabled"},
            "messages": [
                {"role": "system", "content": _DISCIPLINE_SYSTEM_PROMPT},
                {"role": "user", "content": json.dumps(prompt, ensure_ascii=False)},
            ],
        }
        if self.thinking_enabled and self.reasoning_effort:
            payload["reasoning_effort"] = self.reasoning_effort
        audits: list[LLMCallAudit] = []
        for attempt in range(1, 4):
            started = time.perf_counter()
            errors: list[str] = []
            request_id: str | None = None
            usage: dict[str, Any] = {}
            reasoning_preview: str | None = None
            try:
                client = self.client or httpx.Client(timeout=self.timeout)
                response = client.post(
                    f"{self.endpoint}/chat/completions",
                    headers={"Authorization": f"Bearer {api_key}"},
                    json=payload,
                )
                response.raise_for_status()
                body = response.json()
                request_id = body.get("id")
                usage = body.get("usage") or {}
                message = body["choices"][0]["message"]
                reasoning = message.get("reasoning_content") or ""
                if reasoning:
                    reasoning_preview = reasoning[:500] + "…"
                plan = AIPlanSheet.model_validate_json(message["content"])
                batch = OrderBatch.model_validate(plan.orders)
                validation = engine.validate_orders(game_id, batch)
                if plan.turn != state.turn or plan.phase != state.phase:
                    errors.append("Plan sheet turn or phase does not match current state")
                if batch.side != side:
                    errors.append("OrderBatch side does not match bound session side")
                errors.extend(validation.errors)
                if not errors:
                    audits.append(self._audit(
                        state.turn, state.phase, side, attempt, started, request_id, usage,
                        True, [], reasoning_preview,
                    ))
                    return plan, batch, audits
            except (httpx.HTTPError, KeyError, TypeError, ValueError) as error:
                errors.append(type(error).__name__)
            audits.append(self._audit(
                state.turn, state.phase, side, attempt, started, request_id, usage,
                False, errors, reasoning_preview,
            ))
            prompt["validation_errors"] = errors
        raise ValueError({"message": "LLM failed to self-correct within two retries", "audits": audits})

    def _audit(
        self,
        turn: int,
        phase: Phase,
        side: Side,
        attempt: int,
        started: float,
        request_id: str | None,
        usage: dict[str, Any],
        valid: bool,
        errors: list[str],
        reasoning_preview: str | None = None,
    ) -> LLMCallAudit:
        details = usage.get("prompt_tokens_details") or {}
        return LLMCallAudit(
            side=side,
            turn=turn,
            phase=phase,
            attempt=attempt,
            model=self.model,
            request_id=request_id,
            elapsed_ms=int((time.perf_counter() - started) * 1000),
            input_tokens=int(usage.get("prompt_tokens") or 0),
            output_tokens=int(usage.get("completion_tokens") or 0),
            cache_hit_tokens=int(details.get("cached_tokens") or 0),
            valid=valid,
            validation_errors=errors,
            reasoning_preview=reasoning_preview,
        )


class LLMPlayerSession:
    """Side-bound private session; opposing sessions never share context."""

    def __init__(self, side: Side, commander: LLMCommander) -> None:
        self.side = side
        self.commander = commander
        self.plan_sheets: list[AIPlanSheet] = []
        self.audits: list[LLMCallAudit] = []

    def choose_orders(self, engine: IronBottomEngine, game_id: str) -> OrderBatch:
        plan, batch, audits = self.commander.choose_plan(engine, game_id, self.side)
        if batch.side != self.side:
            raise ValueError("Session commander attempted to submit for the opposing side")
        self.plan_sheets.append(plan)
        self.audits.extend(audits)
        return batch
