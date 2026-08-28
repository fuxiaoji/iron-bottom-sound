"""Public scenario guidance shared by state-machine and LLM commanders.

The helpers only read published scenario setup zones.  They never inspect an opposing
side's current positions or sealed orders, so hidden-information boundaries stay intact.
"""

from __future__ import annotations

from .data import load_scenario
from .models import GameState, HexCoord, Side, index_to_column


def public_search_target(state: GameState, side: Side) -> HexCoord | None:
    """Return the midpoint of the opponent's published deployment-zone diagonal."""
    zone = (
        load_scenario(state.scenario_id)
        .get("setup", {})
        .get("zones", {})
        .get(side.opponent.value)
    )
    if not isinstance(zone, dict) or not zone.get("from") or not zone.get("to"):
        return None
    try:
        start = HexCoord.from_label(str(zone["from"]))
        end = HexCoord.from_label(str(zone["to"]))
        q = round((start.q + end.q) / 2)
        start_row = int(''.join(char for char in start.label if char.isdigit()))
        end_row = int(''.join(char for char in end.label if char.isdigit()))
        row = round((start_row + end_row) / 2)
        return HexCoord.from_label(f"{index_to_column(q)}{row}")
    except (TypeError, ValueError):
        return None
