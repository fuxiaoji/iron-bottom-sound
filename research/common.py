"""Shared helpers for research experiments (engine bootstrap, seeds)."""
from __future__ import annotations

from typing import Any

from iron_bottom_sound.data import register_custom_scenario
from iron_bottom_sound.engine import IronBottomEngine
from iron_bottom_sound.models import GameOptions, GameState, Side

CUSTOM_SCENARIO_IDS = {}


def make_sandbox(scenario_key: str, ships: list[dict[str, Any]], turns: int = 8,
                 seed: int = 1, visibility: int = 16) -> tuple[IronBottomEngine, GameState]:
    """Register a minimal custom scenario and reset an engine on it.

    Ships: [{"id": <ship-record id>, "side": "axis"|"allies", "position": "O14",
             "heading": 1..6, "speed": int}, ...]
    Used for offline ground-truth measurement and synthetic experiments.
    """
    definition = {
        "id": f"IBS-CUSTOM-{scenario_key}",
        "title": f"research-{scenario_key}",
        "turns": turns,
        "visibility": {"axis": visibility, "allies": visibility},
        "optional_rules": [],
        "ships": ships,
    }
    register_custom_scenario(definition)
    engine = IronBottomEngine()
    state = engine.reset(definition["id"], seed=seed)
    return engine, state


def derive_seed(base: int, *keys: int) -> int:
    """Deterministic seed derivation (mirrors rl/evolve.py discipline)."""
    seed = base
    for i, key in enumerate(keys):
        seed += (key % 9973) * (100003 ** (i + 1) % 999331)
    return seed % 1_000_000_007
