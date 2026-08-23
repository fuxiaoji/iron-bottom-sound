from __future__ import annotations

import json
import os
import time
from abc import ABC, abstractmethod
from typing import Any

import httpx

from .engine import IronBottomEngine
from .models import (
    AIPlanSheet,
    ContactMovementOrder,
    ContactSetupOrder,
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
            return 4
        if display_row == 26:
            return 1
        if coord.q == 0:
            return 3
        if coord.q == 33:
            return 6
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
            batch.movement = [MovementOrder(ship_id=ship.id, plan="0") for ship in own]
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


class OpenAICompatibleCommander(LLMCommander):
    """DeepSeek/OpenAI-compatible JSON adapter with no silent fallback."""

    def __init__(
        self,
        endpoint: str = "https://api.deepseek.com",
        model: str = "deepseek-v4-flash",
        api_key_env: str = "DEEPSEEK_API_KEY",
        timeout: float = 45,
        max_tokens: int = 1200,
        client: httpx.Client | None = None,
    ) -> None:
        self.endpoint = endpoint.rstrip("/")
        self.model = model
        self.api_key_env = api_key_env
        self.timeout = timeout
        self.max_tokens = max_tokens
        self.client = client

    def choose_plan(
        self, engine: IronBottomEngine, game_id: str, side: Side
    ) -> tuple[AIPlanSheet, OrderBatch, list[LLMCallAudit]]:
        state = engine.get(game_id)
        api_key = os.environ.get(self.api_key_env)
        if not api_key:
            raise RuntimeError(f"{self.api_key_env} is not configured")
        prompt: dict[str, Any] = {
            "observation": engine.observe(game_id, side).model_dump(mode="json"),
            "legal_actions": [item.model_dump(mode="json") for item in engine.legal_actions(game_id, side)],
            "order_batch_json_schema": OrderBatch.model_json_schema(),
            "plan_sheet_json_schema": AIPlanSheet.model_json_schema(),
            "instruction": (
                "Return one JSON AIPlanSheet object. Its orders field must be a complete OrderBatch for "
                "the bound side and current phase. Use only observed information and listed legal actions."
            ),
        }
        audits: list[LLMCallAudit] = []
        for attempt in range(1, 4):
            started = time.perf_counter()
            errors: list[str] = []
            request_id: str | None = None
            usage: dict[str, Any] = {}
            try:
                client = self.client or httpx.Client(timeout=self.timeout)
                response = client.post(
                    f"{self.endpoint}/chat/completions",
                    headers={"Authorization": f"Bearer {api_key}"},
                    json={
                        "model": self.model,
                        "thinking": {"type": "disabled"},
                        "temperature": 0,
                        "max_tokens": self.max_tokens,
                        "response_format": {"type": "json_object"},
                        "messages": [
                            {"role": "system", "content": "Output JSON only. Do not reveal private reasoning."},
                            {"role": "user", "content": json.dumps(prompt, ensure_ascii=False)},
                        ],
                    },
                )
                response.raise_for_status()
                body = response.json()
                request_id = body.get("id")
                usage = body.get("usage") or {}
                plan = AIPlanSheet.model_validate_json(body["choices"][0]["message"]["content"])
                batch = OrderBatch.model_validate(plan.orders)
                validation = engine.validate_orders(game_id, batch)
                if plan.turn != state.turn or plan.phase != state.phase:
                    errors.append("Plan sheet turn or phase does not match current state")
                if batch.side != side:
                    errors.append("OrderBatch side does not match bound session side")
                errors.extend(validation.errors)
                if not errors:
                    audits.append(self._audit(
                        state.turn, state.phase, side, attempt, started, request_id, usage, True, []
                    ))
                    return plan, batch, audits
            except (httpx.HTTPError, KeyError, TypeError, ValueError) as error:
                errors.append(type(error).__name__)
            audits.append(self._audit(
                state.turn, state.phase, side, attempt, started, request_id, usage, False, errors
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
