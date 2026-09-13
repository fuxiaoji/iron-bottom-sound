"""Full legal movement-plan space, mirroring the engine's own movement rules.

The engine enumerates reachable FINAL hexes (`movement_candidates`), but E04
needs every distinct legal command sequence (a MovementOrder plan), because the
denial hazard depends on the whole spatio-temporal route, not only the endpoint.
The DFS below applies exactly the transition rules encoded in
`IronBottomEngine._movement_expand` / `_movement_reachable`:

    - first command must be advance,
    - turns only after an advance, a turn must be followed by an advance,
    - free 60-degree turn allowed as the final command, 120-degree turns cost 1 MF,
    - cost within the legal speed range, land and map edge block advance,
    - forced-rudder/bridge constraints (not triggered for healthy sandbox ships,
      kept for parity).

Read-only with respect to the engine: it only calls `_legal_speed_range`,
`_advance_impossible`, `_terrain_impassable` and HexCoord helpers.
"""
from __future__ import annotations

from dataclasses import dataclass

from iron_bottom_sound.engine import IronBottomEngine
from iron_bottom_sound.models import GameState, HexCoord, ShipState


@dataclass(frozen=True)
class Plan:
    """One legal MovementOrder (command sequence) with its projected timeline."""

    end_hex: HexCoord
    end_heading: int
    cost: int
    commands: tuple[str, ...]
    # Per-MF timeline exactly as engine `_movement_program` builds it: an entry
    # after each advance and each 120-degree turn (60-degree turns are free and
    # hold position with no entry).
    trajectory: tuple[tuple[HexCoord, int], ...]

    @property
    def signature(self) -> tuple[str, int, int]:
        """Decision-level identity: endpoint, final heading and MF cost."""
        return (self.end_hex.label, self.end_heading, self.cost)

    @property
    def plan_string(self) -> str:
        tokens: list[str] = []
        advances = 0
        mapping = {"turn_port_60": "P", "turn_starboard_60": "S",
                   "turn_port_120": "PP", "turn_starboard_120": "SS"}
        for command in self.commands:
            if command == "advance":
                advances += 1
                continue
            if advances:
                tokens.append(str(advances))
                advances = 0
            tokens.append(mapping[command])
        if advances:
            tokens.append(str(advances))
        return "".join(tokens) if tokens else "0"

    def position_at_impulse(self, impulse: int) -> tuple[HexCoord, int]:
        """Ship (hex, heading) at the END of `impulse` (1-based) of the turn."""
        if impulse <= 0:
            return (self.trajectory[0][0], self.trajectory[0][1]) if self.trajectory else (self.end_hex, self.end_heading)
        if impulse <= len(self.trajectory):
            return self.trajectory[impulse - 1]
        return (self.end_hex, self.end_heading)


def enumerate_plans(engine: IronBottomEngine, state: GameState, ship: ShipState) -> list[Plan]:
    """Every distinct legal command sequence for `ship` this turn (see module doc)."""
    minimum, maximum = engine._legal_speed_range(ship, state.turn)
    stay_only = engine._advance_impossible(state, ship)
    turn_ok = not ship.forced_straight_turns
    turn_120_ok = turn_ok and ship.turn_limit_degrees != 60 and not ship.forced_circle_turns
    circle_side = ship.forced_turn_side if ship.forced_circle_turns else None
    plans: list[Plan] = []

    def terminal(cost: int, last: str | None, turned_flag: bool) -> bool:
        return (
            (minimum <= cost or stay_only)
            and cost <= maximum
            and last in (None, "advance", "turn_port_60", "turn_starboard_60")
            and (not ship.forced_circle_turns or turned_flag or stay_only or maximum == 0)
        )

    def walk(pos, head, cost, last, turned_flag, commands, trajectory) -> None:
        if terminal(cost, last, turned_flag):
            plans.append(Plan(
                end_hex=pos, end_heading=head, cost=cost,
                commands=tuple(commands), trajectory=tuple(trajectory),
            ))
        if cost < maximum:
            try:
                target = pos.neighbor(head, columns=state.map_columns, rows=state.map_rows)
            except ValueError:
                target = None
            if target is not None and not engine._terrain_impassable(state, target):
                commands.append("advance")
                trajectory.append((target, head))
                walk(target, head, cost + 1, "advance", turned_flag, commands, trajectory)
                commands.pop()
                trajectory.pop()
        if last == "advance" and turn_ok:
            port60 = 6 if head == 1 else head - 1
            starboard60 = 1 if head == 6 else head + 1
            for new_head, action in ((port60, "turn_port_60"), (starboard60, "turn_starboard_60")):
                if circle_side and IronBottomEngine._turn_side(head, new_head) != circle_side:
                    continue
                commands.append(action)
                walk(pos, new_head, cost, action, True, commands, trajectory)
                commands.pop()
            if turn_120_ok and cost + 1 <= maximum:
                port120 = ((head - 3) % 6) + 1
                starboard120 = ((head + 1) % 6) + 1
                for new_head, action in ((port120, "turn_port_120"), (starboard120, "turn_starboard_120")):
                    if circle_side and IronBottomEngine._turn_side(head, new_head) != circle_side:
                        continue
                    commands.append(action)
                    trajectory.append((pos, new_head))
                    walk(pos, new_head, cost + 1, action, True, commands, trajectory)
                    commands.pop()
                    trajectory.pop()

    if ship.position is None:
        return []
    walk(ship.position, ship.heading, 0, None, False, [], [])
    return plans
