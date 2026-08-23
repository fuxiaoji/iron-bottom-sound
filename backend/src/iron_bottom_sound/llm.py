from __future__ import annotations

import json
import os
from abc import ABC, abstractmethod
from typing import Any

import httpx

from .engine import IronBottomEngine
from .models import MovementOrder, OrderBatch, Side


class LLMCommander(ABC):
    @abstractmethod
    def choose_orders(self, engine: IronBottomEngine, game_id: str, side: Side) -> OrderBatch:
        raise NotImplementedError


class DeterministicCommander(LLMCommander):
    """Offline, reproducible conservative policy used by tests and demos."""

    def choose_orders(self, engine: IronBottomEngine, game_id: str, side: Side) -> OrderBatch:
        observation = engine.observe(game_id, side)
        own = [ship for ship in observation.ships if ship.side == side and not ship.sunk]
        return OrderBatch(side=side, movement=[MovementOrder(ship_id=ship.id, plan="0") for ship in own])


class OpenAICompatibleCommander(LLMCommander):
    """Provider-neutral JSON completion adapter; the engine remains the adjudicator."""

    def __init__(self, endpoint: str, model: str, api_key_env: str = "IBS_LLM_API_KEY", timeout: float = 30) -> None:
        self.endpoint = endpoint.rstrip("/")
        self.model = model
        self.api_key_env = api_key_env
        self.timeout = timeout

    def choose_orders(self, engine: IronBottomEngine, game_id: str, side: Side) -> OrderBatch:
        fallback = DeterministicCommander()
        observation = engine.observe(game_id, side).model_dump(mode="json")
        legal = [item.model_dump(mode="json") for item in engine.legal_actions(game_id, side)]
        api_key = os.environ.get(self.api_key_env)
        if not api_key:
            return fallback.choose_orders(engine, game_id, side)
        prompt = {
            "observation": observation,
            "legal_actions": legal,
            "instruction": "Return one JSON OrderBatch. Never invent units or hidden information.",
        }
        for _ in range(3):
            try:
                response = httpx.post(
                    f"{self.endpoint}/chat/completions",
                    headers={"Authorization": f"Bearer {api_key}"},
                    json={
                        "model": self.model,
                        "temperature": 0,
                        "response_format": {"type": "json_object"},
                        "messages": [{"role": "user", "content": json.dumps(prompt, ensure_ascii=False)}],
                    },
                    timeout=self.timeout,
                )
                response.raise_for_status()
                content: Any = response.json()["choices"][0]["message"]["content"]
                batch = OrderBatch.model_validate_json(content)
                validation = engine.validate_orders(game_id, batch)
                if batch.side == side and validation.valid:
                    return batch
                prompt["validation_errors"] = validation.errors
            except (httpx.HTTPError, KeyError, TypeError, ValueError) as error:
                prompt["validation_errors"] = [type(error).__name__]
        return fallback.choose_orders(engine, game_id, side)
