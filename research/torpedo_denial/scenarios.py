"""Synthetic E04 scenarios: DD torpedo attack against a CA, engine-driven.

Scenarios are registered as custom sandbox scenarios via `research.common.make_sandbox`
and progress through the REAL engine phase machine (submit_orders / advance) with
neutral shared orders, so no adjudication is ever bypassed and no GameState field
is mutated for adjudication purposes.

Protocol (same-turn threat, perfect-information response):
    turn 1 REINFORCEMENT/MOVEMENT - both sides run fixed straight plans
                                    (attackers 3 MF, CA 5 MF) so the engagement
                                    geometry is reached with engine-faithful
                                    kinematics (previous_speed, speed track row).
    turn 1 resolves with no launches and no dice consumed.
    turn 2 MOVEMENT_PLANNING      - attacker turn-2 plans (straight 3 MF) are
                                    sealed for all ships; CA's response is NOT
                                    committed (measured analytically).
    turn 2 TORPEDO_PLANNING       - launch opportunities are enumerated from the
                                    sealed turn-2 attacker plans and every
                                    sampled TorpedoOrder is validated through
                                    engine.validate_orders.  Nothing is launched.
    The target's best response to each lane is measured over its turn-2 plan
    space (see protocol.py) - the standard perfect-information counterfactual,
    identical in spirit to the engine's own torpedo-assist intercept model.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from iron_bottom_sound.engine import IronBottomEngine
from iron_bottom_sound.models import (
    HexCoord,
    MovementOrder,
    OrderBatch,
    Phase,
    Side,
    TorpedoOrder,
)
from research.common import make_sandbox

DD_IDS = ("IBS-U-IJN-FUBUKI", "IBS-U-IJN-HATSUYUKI")   # jp-24-type90, 2x TT (2 rounds, port+starboard)
CA_ID = "IBS-U-USN-NORTHAMPTON"                          # USN CA (new-orleans class)

ATTACKER_PLAN = "3"   # straight 3 MF per turn
TARGET_PLAN = "5"     # straight 5 MF on turn 1 (and sealed turn-2 placeholder)
DD1_T1_START = (16, 12)  # (q, r); turn-1 straight 3 ends at (19, 9)
DD2_T1_START = (16, 10)  # 2v1 wingman
HEX_DIRS = {1: (1, -1), 2: (1, 0), 3: (0, 1), 4: (-1, 1), 5: (-1, 0), 6: (0, -1)}


@dataclass(frozen=True)
class Geometry:
    """Engagement defined by the CA's TURN-2 START position and heading.

    The CA reaches that position from `ca_t2_start - 5 * dir(heading)` with a
    straight turn-1 plan, so turn-2 kinematics (previous_speed=5, speed row 2)
    are engine-faithful.  The DDs' turn-2 course runs NE from (19, 9).
    """

    key: str
    label_zh: str
    ca_t2_start: tuple[int, int]   # (q, r) at start of turn 2
    ca_heading: int                # heading carried from turn 1
    ca_speed: int = 5
    dd_speed: int = 3

    def ca_t1_start(self) -> tuple[int, int]:
        dq, dr = HEX_DIRS[self.ca_heading]
        q, r = self.ca_t2_start
        return q - 5 * dq, r - 5 * dr

    def ca_end(self) -> tuple[int, int]:
        return self.ca_t2_start


FLEETS: dict[str, int] = {"1v1": 1, "2v1": 2}

# Geometry selection (documented decision, E04 report): a pilot grid scan
# (research/torpedo_denial/pilot.py, ~700 candidates x 2 seeds) showed the
# low-direct-hit crossing population and the close-broadside (direct-kill)
# population never coexist in one geometry, so four geometries are used:
# three with stable low-hit pools (5-13 crossing lanes per seed) for the
# A/C/D condition, plus one close-quarters geometry whose crossings are all
# high-E direct shots; it feeds the supplementary direct sample of the
# decomposition analysis (its condition-C pool is empty by design).
GEOMETRIES: dict[str, Geometry] = {
    # 平行相向: CA northbound head-on into the DD's southbound lane fan.
    "opposing": Geometry("opposing", "平行相向", (16, 20), 6),
    # 追击: CA fleeing north, DD pursuing from astern-beam.
    "chase": Geometry("chase", "追击", (14, 4), 6),
    # 斜交: CA rail crossing west ahead of the DD lane fan.
    "crossing": Geometry("crossing", "斜交", (16, 2), 5),
    # 近距直瞄对照: close-quarters closing geometry, direct-kill crossings only.
    "close": Geometry("close", "近距直瞄", (20, 6), 4),
}


def build_sandbox(geometry: Geometry, fleet: str, seed: int) -> tuple[IronBottomEngine, object]:
    import time as _time

    n_dd = FLEETS[fleet]
    ships = []
    dd_starts = [DD1_T1_START, DD2_T1_START]
    for index in range(n_dd):
        q, r = dd_starts[index]
        ships.append({
            "id": DD_IDS[index], "name": DD_IDS[index], "side": "axis",
            "position": HexCoord(q=q, r=r).label, "heading": 1, "speed": geometry.dd_speed,
        })
    qs, rs = geometry.ca_t1_start()
    ships.append({
        "id": CA_ID, "name": CA_ID, "side": "allies",
        "position": HexCoord(q=qs, r=rs).label, "heading": geometry.ca_heading,
        "speed": geometry.ca_speed,
    })
    # Retry: rules/records YAML can transiently fail while a concurrent process
    # regenerates the derived data; a short back-off makes runs robust.
    last_error: Exception | None = None
    for attempt in range(4):
        try:
            return make_sandbox(f"E04-{geometry.key}-{fleet}", ships, seed=seed)
        except (AttributeError, ValueError) as error:
            last_error = error
            _time.sleep(0.5 * (attempt + 1))
    raise last_error  # type: ignore[misc]


def submit_empty(engine: IronBottomEngine, state, side: Side, phase: Phase) -> None:
    result = engine.submit_orders(state.game_id, OrderBatch(side=side, phase=phase))
    if not result.valid:
        raise ValueError(f"empty {phase} batch rejected for {side}: {result.errors}")


def submit_movement(engine: IronBottomEngine, state, side: Side, plan_by_ship: dict[str, str]) -> None:
    movement = [MovementOrder(ship_id=ship_id, plan=plan)
                for ship_id, plan in sorted(plan_by_ship.items())]
    result = engine.submit_orders(
        state.game_id,
        OrderBatch(side=side, phase=Phase.MOVEMENT_PLANNING, movement=movement),
    )
    if not result.valid:
        raise ValueError(f"movement batch rejected for {side}: {result.errors}")


def progress_to_torpedo_planning(engine: IronBottomEngine, state) -> None:
    """Turn 1: REINFORCEMENT -> MOVEMENT_PLANNING (sealed plans) -> TORPEDO_PLANNING."""
    for side in Side:
        submit_empty(engine, state, side, Phase.REINFORCEMENT)
    engine.advance(state.game_id)
    for side in Side:
        plans = {
            ship.id: (TARGET_PLAN if ship.id == CA_ID else ATTACKER_PLAN)
            for ship in state.ships.values() if ship.side == side and ship.position
        }
        submit_movement(engine, state, side, plans)
    engine.advance(state.game_id)
    if state.phase != Phase.TORPEDO_PLANNING:
        raise ValueError(f"expected TORPEDO_PLANNING, got {state.phase}")


def resolve_turn(engine: IronBottomEngine, state) -> None:
    """Finish turn 1 with empty torpedo/gunnery orders and reach turn-2 planning."""
    for side in Side:
        submit_empty(engine, state, side, Phase.TORPEDO_PLANNING)
    engine.advance(state.game_id)
    engine.advance(state.game_id)
    for side in Side:
        submit_empty(engine, state, side, Phase.GUNNERY)
    engine.advance(state.game_id)
    engine.advance(state.game_id)
    engine.advance(state.game_id)
    if state.turn != 2 or state.phase != Phase.REINFORCEMENT:
        raise ValueError(f"expected turn-2 REINFORCEMENT, got turn {state.turn} phase {state.phase}")
    for side in Side:
        submit_empty(engine, state, side, Phase.REINFORCEMENT)
    engine.advance(state.game_id)
    if state.phase != Phase.MOVEMENT_PLANNING:
        raise ValueError(f"expected turn-2 MOVEMENT_PLANNING, got {state.phase}")


def seal_turn2_plans(engine: IronBottomEngine, state) -> None:
    """Seal straight turn-2 plans for every ship; advance to TORPEDO_PLANNING.

    The CA's sealed plan is a kinematic placeholder (it is never adjudicated);
    its actual response is measured analytically over the full legal plan space.
    """
    for side in Side:
        plans = {
            ship.id: (TARGET_PLAN if ship.id == CA_ID else ATTACKER_PLAN)
            for ship in state.ships.values() if ship.side == side and ship.position
        }
        submit_movement(engine, state, side, plans)
    engine.advance(state.game_id)
    if state.phase != Phase.TORPEDO_PLANNING:
        raise ValueError(f"expected turn-2 TORPEDO_PLANNING, got {state.phase}")


@dataclass
class LaunchOption:
    """One legal torpedo launch opportunity (full salvo of one launcher)."""

    ship_id: str
    launcher_id: str
    launch_at_mf: int
    launch_hex: HexCoord
    ship_heading: int
    launch_side: str
    launch_angle: str
    setting_index: int
    count: int
    lane_key: tuple = field(compare=True)

    def order(self, target_id: str) -> TorpedoOrder:
        return TorpedoOrder(
            ship_id=self.ship_id, target_id=target_id, count=self.count,
            launcher_id=self.launcher_id, launch_at_mf=self.launch_at_mf,
            launch_hex=self.launch_hex, bearing=self.ship_heading,
            launch_side=self.launch_side, launch_angle=self.launch_angle,
            setting_index=self.setting_index,
        )


def enumerate_launch_options(engine: IronBottomEngine, state, attacker_plan_strings: dict[str, str]) -> list[LaunchOption]:
    """All legal (launcher, side, angle, setting, launch MF) combos for the attackers.

    Enumeration mirrors `engine._torpedo_candidates` (the single source of truth
    used by legal_actions/assist), restricted to the fixed straight attacker
    plans sealed this turn; `count` is the launcher's full loaded salvo.  Combos
    are deduplicated by physical lane identity (launch hex, anchor, torpedo
    heading, speed setting, launch MF) so identical lanes from twin launchers
    count once.
    """
    options: list[LaunchOption] = []
    seen: set[tuple] = set()
    angles = engine.rules.torpedo_launch_directions["angles"]
    for ship in sorted(state.ships.values(), key=lambda item: item.id):
        if ship.side != Side.AXIS or ship.sunk or not ship.torpedo or ship.torpedo.destroyed:
            continue
        plan_string = attacker_plan_strings[ship.id]
        order = MovementOrder(ship_id=ship.id, plan=plan_string)
        commands = engine.movement_commands(order)
        trajectory, _ = engine.movement_trajectory(
            ship, plan_string, commands, columns=state.map_columns, rows=state.map_rows,
        )
        launch_positions = [(0, ship.position, ship.heading)] + [
            (mf, position, heading) for mf, (position, heading) in enumerate(trajectory, start=1)
        ]
        for launcher in ship.torpedo_launchers:
            if launcher.destroyed or launcher.reload_turns_remaining or launcher.loaded <= 0:
                continue
            sides = [arc.value for arc in launcher.arcs if arc.value in ("port", "starboard")]
            for launch_at_mf, launch_hex, ship_heading in launch_positions:
                for launch_side in sides:
                    for angle in angles:
                        for setting_index in range(len(engine.rules.torpedoes[ship.torpedo_type or ""]["settings"])):
                            heading = engine._torpedo_launch_heading(ship_heading, launch_side, angle)
                            anchor = engine._torpedo_anchor_hex(
                                launch_hex, ship_heading, angle,
                                columns=state.map_columns, rows=state.map_rows,
                            )
                            key = (launch_hex.label, anchor.label, heading, setting_index, launch_at_mf)
                            if key in seen:
                                continue
                            seen.add(key)
                            options.append(LaunchOption(
                                ship_id=ship.id, launcher_id=launcher.id,
                                launch_at_mf=launch_at_mf, launch_hex=launch_hex,
                                ship_heading=ship_heading, launch_side=launch_side,
                                launch_angle=angle, setting_index=setting_index,
                                count=launcher.loaded, lane_key=key,
                            ))
    return options


def validate_launch_options(engine: IronBottomEngine, state, options: list[LaunchOption], target_id: str) -> dict[tuple, list[str]]:
    """Validate every option's TorpedoOrder through engine.validate_orders."""
    errors: dict[tuple, list[str]] = {}
    for option in options:
        batch = OrderBatch(
            side=Side.AXIS, phase=Phase.TORPEDO_PLANNING,
            torpedoes=[option.order(target_id)],
        )
        result = engine.validate_orders(state.game_id, batch)
        if not result.valid:
            errors[option.lane_key] = result.errors
    return errors
