"""Project-extension command-chain rules for realistic formation play.

This module deliberately owns every IBS-R-RC-* constant and transformation.
The classic engine and ``TacticalCommander`` remain unchanged when the option is
disabled.  Formation orders are expanded into ordinary per-ship orders before
the existing adjudicator sees them, preserving torpedo timing and replay.
"""
from __future__ import annotations

from collections import deque
from copy import deepcopy
from typing import TYPE_CHECKING, Any

from .data import load_scenario
from .scenario_guidance import public_search_target
from .models import (
    AIPlanSheet,
    CommandSuccession,
    ContactMovementOrder,
    FormationMovementOrder,
    FormationSpeedDecision,
    FormationSetupOrder,
    FormationState,
    GameState,
    GunMountOrder,
    GunneryOrder,
    HexCoord,
    MAP_COLUMNS,
    MAP_ROWS,
    MovementOrder,
    OrderBatch,
    Phase,
    Side,
    ShipState,
    WithdrawalState,
)

if TYPE_CHECKING:
    from .engine import IronBottomEngine


SUPPORTED_SCENARIOS = {"IBS-S-01", "IBS-S-03", "IBS-S-EM-01"}
MAX_FORMATIONS_PER_SIDE = 4


def _source_position(state: GameState, ship_id: str) -> HexCoord | None:
    ship = state.ships[ship_id]
    return ship.position or state.contact_reserve_positions.get(ship_id)


def _opposite(heading: int) -> int:
    return ((heading + 2) % 6) + 1


def _group_key(ship) -> str:
    if ship.position is None and ship.reinforcement_turn:
        return "reserve-heavy" if ship.ship_type in {"BB", "BC", "CB", "CA", "CL", "AV"} else "reserve-light"
    return "active-heavy" if ship.ship_type in {"BB", "BC", "CB", "CA", "CL", "AV"} else "active-light"


def default_setup_orders(state: GameState, side: Side) -> list[FormationSetupOrder]:
    """Return a deterministic, editable setup proposal for UI and state-machine AI."""
    scenario = load_scenario(state.scenario_id)
    definitions = scenario.get("setup", {}).get("engine_default_formations", {}).get(side.value, [])
    owned = [ship for ship in state.ships.values() if ship.side == side]
    assigned: set[str] = set()
    groups: list[tuple[str, list[str]]] = []
    for definition in definitions:
        members = [ship_id for ship_id in definition.get("ships", []) if ship_id in state.ships and state.ships[ship_id].side == side]
        if len(members) >= 2:
            groups.append((str(definition.get("id", f"{side.value}-formation-{len(groups)+1}")), members))
            assigned.update(members)
    buckets: dict[str, list[str]] = {}
    for ship in owned:
        if ship.id not in assigned:
            buckets.setdefault(_group_key(ship), []).append(ship.id)
    for key in ("active-heavy", "active-light", "reserve-heavy", "reserve-light"):
        members = buckets.get(key, [])
        if members:
            groups.append((f"{side.value}-{key}", members))
    # No singleton formation: merge it into the nearest compatible previous group.
    index = 0
    while index < len(groups):
        if len(groups[index][1]) == 1 and len(groups) > 1:
            ship_id = groups[index][1][0]
            target = index - 1 if index else 1
            groups[target][1].append(ship_id)
            groups.pop(index)
            continue
        index += 1
    while len(groups) > MAX_FORMATIONS_PER_SIDE:
        _name, members = groups.pop()
        groups[-1][1].extend(members)
    result: list[FormationSetupOrder] = []
    for index, (name, members) in enumerate(groups, 1):
        positioned = [ship_id for ship_id in members if _source_position(state, ship_id)]
        leader = positioned[0] if positioned else members[0]
        ordered = [leader] + [ship_id for ship_id in members if ship_id != leader]
        flagship = next(
            (ship_id for ship_id in ordered if load_scenario(state.scenario_id).get("ships") and
             next((entry for entry in load_scenario(state.scenario_id)["ships"] if entry["id"] == ship_id), {}).get("flagship")),
            leader,
        )
        reserve = next(ship_id for ship_id in ordered if ship_id != flagship)
        heading = state.ships[leader].heading
        result.append(FormationSetupOrder(
            formation_id=name or f"{side.value}-formation-{index}",
            name=f"{side.value == 'axis' and '轴心' or '同盟'}第{index}编队",
            ship_ids=ordered,
            leader_id=leader,
            flagship_id=flagship,
            reserve_flagship_id=reserve,
            spacing=1,
            heading=heading,
        ))
    return result


def _layout_for_order(state: GameState, order: FormationSetupOrder) -> dict[str, HexCoord]:
    anchor = _source_position(state, order.leader_id)
    if anchor is None:
        return {}
    heading = order.heading or state.ships[order.leader_id].heading
    astern = _opposite(heading)
    layout: dict[str, HexCoord] = {order.leader_id: anchor}
    cursor = anchor
    for ship_id in order.ship_ids[1:]:
        if _source_position(state, ship_id) is None:
            continue
        for _ in range(order.spacing):
            cursor = cursor.neighbor(astern)
        layout[ship_id] = cursor
    return layout


def validate_setup(engine: "IronBottomEngine", state: GameState, batch: OrderBatch) -> list[str]:
    errors: list[str] = []
    orders = batch.formation_setup
    if not 1 <= len(orders) <= MAX_FORMATIONS_PER_SIDE:
        errors.append("Realistic command requires one to four formations per side")
        return errors
    owned = {ship.id for ship in state.ships.values() if ship.side == batch.side}
    listed = [ship_id for order in orders for ship_id in order.ship_ids]
    if set(listed) != owned or len(listed) != len(set(listed)):
        errors.append("Every owned initial or reinforcement ship must belong to exactly one formation")
    if len({order.formation_id for order in orders}) != len(orders):
        errors.append("Formation ids must be unique within a side")
    occupied: set[str] = set()
    for order in orders:
        members = set(order.ship_ids)
        if order.ship_ids[0] != order.leader_id:
            errors.append(f"{order.formation_id}: leader must be first in formation order")
        if not {order.leader_id, order.flagship_id, order.reserve_flagship_id} <= members:
            errors.append(f"{order.formation_id}: leader/flagships must be formation members")
        if order.flagship_id == order.reserve_flagship_id:
            errors.append(f"{order.formation_id}: flagship and reserve flagship must differ")
        try:
            layout = _layout_for_order(state, order)
        except ValueError:
            errors.append(f"{order.formation_id}: formation layout leaves the map")
            continue
        for ship_id, position in layout.items():
            if engine._terrain_impassable(state, position):
                errors.append(f"{order.formation_id}: {ship_id} would be placed on land {position.label}")
            if position.label in occupied:
                errors.append(f"{order.formation_id}: formation layout overlaps at {position.label}")
            occupied.add(position.label)
    return errors


def _shortest_hex_path(start: HexCoord, end: HexCoord) -> list[HexCoord]:
    if start == end:
        return [start]
    queue = deque([start])
    parent: dict[HexCoord, HexCoord | None] = {start: None}
    while queue:
        current = queue.popleft()
        for heading in range(1, 7):
            try:
                candidate = current.neighbor(heading)
            except ValueError:
                continue
            if candidate in parent:
                continue
            parent[candidate] = current
            if candidate == end:
                path = [candidate]
                while parent[path[-1]] is not None:
                    path.append(parent[path[-1]])  # type: ignore[arg-type]
                return list(reversed(path))
            queue.append(candidate)
    raise ValueError(f"No map path {start.label} -> {end.label}")


def rebuild_guide_trail(state: GameState, formation: FormationState) -> list[HexCoord]:
    active = [state.ships[ship_id] for ship_id in formation.ship_ids if state.ships[ship_id].position and state.ships[ship_id].command_status == "attached"]
    if not active:
        return []
    trail: list[HexCoord] = []
    for left, right in zip(reversed(active), list(reversed(active))[1:]):
        segment = _shortest_hex_path(left.position, right.position)  # type: ignore[arg-type]
        trail.extend(segment[:-1])
    trail.append(active[0].position)  # type: ignore[arg-type]
    return trail


def resolve_setup(engine: "IronBottomEngine", state: GameState) -> None:
    layouts: dict[str, HexCoord] = {}
    formations: dict[str, FormationState] = {}
    for batch in state.sealed_orders.get(f"{state.turn}:{Phase.FORMATION_SETUP.value}", {}).values():
        for order in batch.formation_setup:
            layout = _layout_for_order(state, order)
            for ship_id, position in layout.items():
                if position.label in {item.label for item in layouts.values()}:
                    raise ValueError(f"Opposing formation setups overlap at {position.label}")
                layouts[ship_id] = position
            heading = order.heading or state.ships[order.leader_id].heading
            formation = FormationState(
                id=order.formation_id,
                name=order.name,
                side=batch.side,
                ship_ids=list(order.ship_ids),
                leader_id=order.leader_id,
                flagship_id=order.flagship_id,
                reserve_flagship_id=order.reserve_flagship_id,
                succession_order=[order.reserve_flagship_id] + [
                    ship_id for ship_id in order.ship_ids
                    if ship_id not in {order.flagship_id, order.reserve_flagship_id}
                ],
                spacing=order.spacing,
                heading=heading,
                speed=state.ships[order.leader_id].current_speed,
            )
            formations[formation.id] = formation
            for ship_id in order.ship_ids:
                state.ships[ship_id].formation_id = formation.id
                if _source_position(state, ship_id) is not None:
                    state.ships[ship_id].heading = heading
    for ship_id, position in layouts.items():
        if ship_id in state.contact_reserve_positions and state.ships[ship_id].position is None:
            state.contact_reserve_positions[ship_id] = position
        else:
            state.ships[ship_id].position = position
    state.formations = formations
    for formation in state.formations.values():
        formation.guide_trail = rebuild_guide_trail(state, formation)
        engine._event(
            state, "formation_created", f"{formation.name} 完成编成",
            payload={"secret_side": formation.side.value, "formation_id": formation.id, "ship_ids": formation.ship_ids},
            rule=engine._rule("IBS-R-RC-01", None, "真实模式：编队初设"),
        )


def _edge_distance(position: HexCoord, edge: str) -> int:
    row = int("".join(filter(str.isdigit, position.label))) - 1
    return {
        "west": position.q,
        "east": MAP_COLUMNS - 1 - position.q,
        "north": row,
        "south": MAP_ROWS - 1 - row,
    }[edge]


def choose_withdrawal_edge(state: GameState, ship_id: str) -> str:
    ship = state.ships[ship_id]
    enemies = [item for item in state.ships.values() if item.side != ship.side and item.position and not item.sunk]
    edges = ("north", "east", "south", "west")
    def score(edge: str) -> tuple[float, int, str]:
        # Prefer a short route whose boundary is on the side opposite the enemy mass.
        if not ship.position:
            return (0.0, 0, edge)
        boundary_bonus = 0.0
        for enemy in enemies:
            if not enemy.position:
                continue
            boundary_bonus += _edge_distance(enemy.position, edge)
        return (boundary_bonus, -_edge_distance(ship.position, edge), edge)
    return max(edges, key=score)


def _at_edge(position: HexCoord, edge: str) -> bool:
    return _edge_distance(position, edge) == 0


def _withdrawal_order(engine: "IronBottomEngine", state: GameState, ship) -> MovementOrder:
    if not ship.position or not ship.withdrawal_edge:
        return MovementOrder(ship_id=ship.id, plan="0")
    if _at_edge(ship.position, ship.withdrawal_edge):
        # The ship is removed by after_movement; authorize the zero-length
        # boundary hold even when its damaged speed track normally requires
        # movement.
        return MovementOrder(ship_id=ship.id, plan="0", formation_emergency_stop=True)
    enemies = [item for item in state.ships.values() if item.side != ship.side and item.position and not item.sunk]
    candidates = engine.movement_candidates(state, ship, include_plans=True)["reachable"]
    scored: list[tuple[tuple[float, float, int, str], str]] = []
    for entry in candidates:
        position = HexCoord(q=entry["hex"]["q"], r=entry["hex"]["r"])
        enemy_distance = min((position.distance(enemy.position) for enemy in enemies if enemy.position), default=20)
        enemy_pressure = sum(
            engine.ship_gun_pressure(state, enemy, position=enemy.position, target_hexes=[position])
            for enemy in enemies
        )
        score = (float(enemy_distance), -enemy_pressure, -_edge_distance(position, ship.withdrawal_edge), position.label)
        plans = [entry["plan"]] if entry.get("plan") is not None else []
        for heading in entry["final_headings"]:
            path = engine.movement_path(state, ship, position, heading=heading)
            if path.get("valid") and path["plan"] not in plans:
                plans.append(path["plan"])
        for plan in plans:
            preview = engine.movement_preview(state, ship, plan=plan)
            if preview["commitable"]:
                scored.append((score, plan))
    if not scored:
        # Forced-straight damage can make every target-oriented path invalid
        # even though a plain legal straight programme exists.
        minimum, maximum = engine._legal_speed_range(ship, state.turn)
        for speed in range(maximum, minimum - 1, -1):
            plan = str(speed)
            if engine.movement_preview(state, ship, plan=plan)["commitable"]:
                return MovementOrder(ship_id=ship.id, plan=plan)
        stay = engine.movement_preview(state, ship, plan="0")
        if stay["commitable"]:
            return MovementOrder(ship_id=ship.id, plan="0")
        raise ValueError(f"{ship.id}: withdrawal controller has no legal movement")
    return MovementOrder(ship_id=ship.id, plan=max(scored, key=lambda item: item[0])[1])


def _truncate_plan(engine: "IronBottomEngine", ship_id: str, plan: str, speed: int) -> str:
    commands = engine.movement_commands(MovementOrder(ship_id=ship_id, plan=plan))
    kept: list[str] = []
    cost = 0
    for command in commands:
        delta = int(command == "advance" or command.endswith("120"))
        if cost + delta > speed:
            break
        kept.append(command)
        cost += delta
    return engine.commands_to_plan(kept)


def expand_movement_orders(
    engine: "IronBottomEngine", state: GameState, batch: OrderBatch,
) -> tuple[OrderBatch, list[str], list[str]]:
    """Expand formation orders; return prepared batch, validation errors, detach ids."""
    prepared = batch.model_copy(deep=True)
    errors: list[str] = []
    detach_ids: list[str] = []
    orders = {order.formation_id: order for order in batch.formation_movement}
    owned_formations = [formation for formation in state.formations.values() if formation.side == batch.side and formation.status != "dissolved"]
    expected = {formation.id for formation in owned_formations if any(state.ships[item].position and state.ships[item].command_status == "attached" for item in formation.ship_ids)}
    if set(orders) != expected:
        errors.append(f"Formation movement must cover active formations; missing={sorted(expected-set(orders))}, extra={sorted(set(orders)-expected)}")
        return prepared, errors, detach_ids
    generated: list[MovementOrder] = []
    for formation in owned_formations:
        if formation.id not in orders:
            continue
        order = orders[formation.id]
        members = [state.ships[ship_id] for ship_id in formation.ship_ids if state.ships[ship_id].position and state.ships[ship_id].command_status == "attached" and not state.ships[ship_id].sunk]
        if not members:
            continue
        leader = state.ships.get(formation.leader_id)
        if leader not in members:
            formation_leader = members[0]
            leader = formation_leader
        plan = order.leader_plan
        if formation.disruption_turn == state.turn:
            locked_speed = formation.locked_speed or 0
            # Command disruption repeats last turn's actual speed, except that
            # original-rule damage and collision limits have higher priority.
            # In that case the whole surviving column is truncated to the
            # highest speed every attached member can still make.
            damage_ceiling = min(engine._legal_speed_range(ship, state.turn)[1] for ship in members)
            plan = str(min(locked_speed, damage_ceiling))
        if leader.forced_straight_turns:
            forced_speed = leader.forced_speed if leader.forced_speed is not None else engine.movement_cost(
                plan, engine.movement_commands(MovementOrder(ship_id=leader.id, plan=plan))
            )
            plan = str(min(forced_speed, engine._legal_speed_range(leader, state.turn)[1]))
        leader_cost = engine.movement_cost(plan, engine.movement_commands(MovementOrder(ship_id=leader.id, plan=plan)))
        decision = order.speed_decision
        # Detachment is also the escape hatch for a column that has been
        # physically split by a collision.  Such a ship can have a perfectly
        # legal individual speed range yet be unable to regain its station in
        # this turn.  Honour an explicit permanent detachment before deriving
        # follower routes, rather than limiting detachment to range mismatch.
        if decision is not None and decision.action == "detach":
            requested = set(decision.detach_ship_ids)
            member_ids = {ship.id for ship in members}
            if not requested or not requested <= member_ids:
                errors.append(f"{formation.id}: detach decision must name active formation ships")
                continue
            if not requested <= member_ids:
                errors.append(f"{formation.id}: detach decision contains a non-member ship")
                continue
            detach_ids.extend(sorted(requested))
            members = [ship for ship in members if ship.id not in requested]
            if not members:
                continue
            if leader.id in requested:
                leader = members[0]
                plan = str(min(leader_cost, engine._legal_speed_range(leader, state.turn)[1]))
                leader_cost = engine.movement_cost(plan, engine.movement_commands(MovementOrder(ship_id=leader.id, plan=plan)))
        forced_incompatible = next(
            (ship for ship in members if ship.forced_circle_turns), None
        )
        if forced_incompatible:
            errors.append(
                f"{formation.id}: {forced_incompatible.id} forced movement prevents formation following"
            )
            continue
        incompatible = [ship for ship in members if not (engine._legal_speed_range(ship, state.turn)[0] <= leader_cost <= engine._legal_speed_range(ship, state.turn)[1])]
        emergency_stop = bool(decision and decision.emergency_stop and leader_cost == 0)
        if incompatible and not emergency_stop:
            if decision is None:
                errors.append(f"{formation.id}: speed {leader_cost} is outside member limits; reduce or detach")
                continue
            if decision.action == "reduce":
                if decision.speed is None:
                    errors.append(f"{formation.id}: reduce decision requires speed")
                    continue
                plan = _truncate_plan(engine, leader.id, plan, decision.speed)
                leader_cost = engine.movement_cost(plan, engine.movement_commands(MovementOrder(ship_id=leader.id, plan=plan)))
                if not emergency_stop and any(not (engine._legal_speed_range(ship, state.turn)[0] <= leader_cost <= engine._legal_speed_range(ship, state.turn)[1]) for ship in members):
                    errors.append(f"{formation.id}: reduced speed is not legal for every member")
                    continue
            elif decision.action == "detach":
                errors.append(f"{formation.id}: detach decision leaves incompatible formation ships")
                continue
            else:
                errors.append(f"{formation.id}: unsupported speed decision")
                continue
        generated.append(MovementOrder(ship_id=leader.id, plan=plan, speed=leader_cost, formation_emergency_stop=emergency_stop))
        leader_trajectory, _ = engine.movement_trajectory(leader, plan)
        route = list(formation.guide_trail or rebuild_guide_trail(state, formation))
        if not route or route[-1] != leader.position:
            route = rebuild_guide_trail(state, formation)
        for position, _heading in leader_trajectory:
            if not route or position != route[-1]:
                route.append(position)
        target_spacing = order.spacing or formation.spacing
        for member_index, ship in enumerate(members):
            if ship.id == leader.id:
                continue
            try:
                start_index = max(index for index, position in enumerate(route) if position == ship.position)
            except ValueError:
                errors.append(f"{formation.id}: {ship.name} is no longer on the guide trail")
                continue
            final_index = max(start_index, len(route) - 1 - member_index * target_spacing)
            hex_path = route[start_index + 1:final_index + 1]
            try:
                commands = engine.path_to_commands(ship, hex_path)
                # End bow-on to the next guide segment. A trailing ship that
                # reaches a bend but keeps its old heading would need to turn
                # before its mandatory first advance next turn (illegal under
                # IBS-R-06). A final 60-degree turn is free and preserves the
                # exact wake for the next formation order.
                if final_index + 1 < len(route) and not ship.forced_straight_turns:
                    _program, final_heading = engine._movement_program(ship.position, ship.heading, commands)
                    desired_heading = engine._bearing_between(route[final_index], route[final_index + 1])
                    relative = (desired_heading - final_heading) % 6
                    if relative == 1:
                        commands.append("turn_starboard_60")
                    elif relative == 5:
                        commands.append("turn_port_60")
                if ship.forced_straight_turns and any(command != "advance" for command in commands):
                    errors.append(f"{formation.id}: {ship.id} forced movement prevents formation following")
                    continue
                follower_plan = engine.commands_to_plan(commands)
                follower_cost = engine.movement_cost(follower_plan, commands)
                if commands and commands[0] != "advance":
                    errors.append(f"{formation.id}: {ship.name} cannot follow guide trail before advancing")
                    continue
            except ValueError as error:
                errors.append(f"{formation.id}: {ship.name} cannot follow guide trail: {error}")
                continue
            minimum, maximum = engine._legal_speed_range(ship, state.turn)
            if not minimum <= follower_cost <= maximum:
                errors.append(f"{formation.id}: {ship.name} follower speed {follower_cost} outside {minimum}-{maximum}")
                continue
            generated.append(MovementOrder(ship_id=ship.id, plan=follower_plan, speed=follower_cost, formation_emergency_stop=emergency_stop and follower_cost == 0))
    for ship in state.ships.values():
        if ship.side == batch.side and ship.position and not ship.sunk and ship.command_status == "retreating":
            generated.append(_withdrawal_order(engine, state, ship))
    # Newly detached ships are not mutated until the fully prepared batch has
    # passed classic validation.  Give them their first autonomous withdrawal
    # order now so movement coverage remains total and validation is atomic.
    generated_ids = {order.ship_id for order in generated}
    for ship_id in detach_ids:
        if ship_id not in generated_ids:
            ship = state.ships[ship_id]
            edge = ship.withdrawal_edge or choose_withdrawal_edge(state, ship_id)
            original_edge = ship.withdrawal_edge
            ship.withdrawal_edge = edge
            generated.append(_withdrawal_order(engine, state, ship))
            ship.withdrawal_edge = original_edge
    prepared.movement = generated
    # Formation legality is a batch property: reject same-impulse same-hex and
    # hex swaps before the classic collision table is ever reached.
    paths: dict[str, list[HexCoord]] = {}
    for movement in generated:
        ship = state.ships[movement.ship_id]
        if not ship.position:
            continue
        try:
            trajectory, _heading = engine.movement_trajectory(ship, movement.plan)
        except ValueError:
            continue
        paths[ship.id] = [ship.position] + [position for position, _ in trajectory]
    ids = sorted(paths)
    for left_index, left_id in enumerate(ids):
        for right_id in ids[left_index + 1:]:
            if state.ships[left_id].side != state.ships[right_id].side:
                continue
            left, right = paths[left_id], paths[right_id]
            for impulse in range(max(len(left), len(right)) - 1):
                lb, rb = left[min(impulse, len(left)-1)], right[min(impulse, len(right)-1)]
                la, ra = left[min(impulse+1, len(left)-1)], right[min(impulse+1, len(right)-1)]
                if la == ra or (la == rb and ra == lb):
                    # The simultaneous resolver performs a deterministic
                    # emergency stop for both friendly columns.  Do not route
                    # this through the original collision damage table.
                    break
    return prepared, errors, detach_ids


def apply_detachments(engine: "IronBottomEngine", state: GameState, detach_ids: list[str]) -> None:
    for ship_id in detach_ids:
        ship = state.ships[ship_id]
        ship.command_status = "retreating"
        ship.withdrawal_edge = choose_withdrawal_edge(state, ship_id)  # type: ignore[assignment]
        state.withdrawals[ship_id] = WithdrawalState(ship_id=ship_id, edge=ship.withdrawal_edge)
        formation = state.formations.get(ship.formation_id or "")
        if formation and ship_id in formation.ship_ids:
            formation.ship_ids.remove(ship_id)
            if formation.leader_id == ship_id and formation.ship_ids:
                formation.leader_id = next((
                    candidate_id for candidate_id in formation.ship_ids
                    if state.ships[candidate_id].position and not state.ships[candidate_id].sunk
                    and state.ships[candidate_id].command_status == "attached"
                ), formation.ship_ids[0])
        engine._event(
            state, "ship_detached", f"{ship.name} 脱离编队，向{ship.withdrawal_edge}侧撤退",
            payload={"ship_id": ship.id, "formation_id": ship.formation_id, "edge": ship.withdrawal_edge},
            rule=engine._rule("IBS-R-RC-04", None, "真实模式：受损舰脱队"),
        )


def prepare_gunnery(engine: "IronBottomEngine", state: GameState, batch: OrderBatch) -> OrderBatch:
    prepared = batch.model_copy(deep=True)
    retreating = {ship.id for ship in state.ships.values() if ship.side == batch.side and ship.command_status == "retreating" and ship.position and not ship.sunk}
    prepared.gunnery = [order for order in prepared.gunnery if order.ship_id not in retreating]
    candidates = {item["ship_id"]: item for item in engine._gunnery_candidates(state, batch.side)}
    for ship_id in sorted(retreating):
        targets = candidates.get(ship_id, {}).get("targets", [])
        if not targets:
            continue
        target = max(targets, key=lambda item: (item["expected_hits"], -item["range"], item["target_id"]))
        prepared.gunnery.append(GunneryOrder(
            ship_id=ship_id,
            primary_target=target["target_id"],
            mounts=[GunMountOrder(mount_id=mount_id, target_id=target["target_id"]) for mount_id in target["mount_ids"]],
        ))
    return prepared


def refresh_command_chain(engine: "IronBottomEngine", state: GameState) -> None:
    if not state.options.realistic_command:
        return
    for formation in state.formations.values():
        flagship = state.ships.get(formation.flagship_id)
        unavailable = not flagship or flagship.sunk or flagship.command_status in {"retreating", "withdrawn"} or flagship.captain_status == "killed"
        if not unavailable:
            continue
        candidates = [formation.reserve_flagship_id] + formation.succession_order + formation.ship_ids
        new_flagship = next((ship_id for ship_id in candidates if ship_id != formation.flagship_id and ship_id in state.ships and not state.ships[ship_id].sunk and state.ships[ship_id].captain_status != "killed" and state.ships[ship_id].command_status == "attached"), None)
        if not new_flagship:
            formation.status = "dissolved"
            # A dissolved formation must not leave attached ships without a
            # formation order.  Remaining survivors permanently enter the
            # same deterministic withdrawal controller used for detachments.
            orphaned = [
                ship_id for ship_id in formation.ship_ids
                if state.ships[ship_id].position and not state.ships[ship_id].sunk
                and state.ships[ship_id].command_status == "attached"
            ]
            apply_detachments(engine, state, orphaned)
            formation.status = "dissolved"
            continue
        previous = formation.flagship_id
        formation.flagship_id = new_flagship
        formation.disruption_turn = state.turn + 1
        active = [
            state.ships[ship_id] for ship_id in formation.ship_ids
            if state.ships[ship_id].position and not state.ships[ship_id].sunk
            and state.ships[ship_id].command_status == "attached"
        ]
        leader = state.ships.get(formation.leader_id)
        if leader not in active and active:
            leader = active[0]
            formation.leader_id = leader.id
        # The disruption lock repeats the surviving leader's actual previous speed,
        # never a stale formation cache left behind by a ship that already exited.
        formation.locked_heading = leader.heading if leader else formation.heading
        formation.locked_speed = leader.current_speed if leader else formation.speed
        if leader:
            formation.heading = leader.heading
            formation.speed = leader.current_speed
        state.command_successions.append(CommandSuccession(
            formation_id=formation.id, previous_flagship_id=previous,
            new_flagship_id=new_flagship, effective_turn=state.turn + 1,
        ))
        engine._event(
            state, "formation_command_transferred", f"{formation.name} 指挥权转移至 {state.ships[new_flagship].name}",
            payload={"formation_id": formation.id, "previous_flagship_id": previous, "new_flagship_id": new_flagship, "disruption_turn": state.turn + 1},
            rule=engine._rule("IBS-R-RC-05", None, "真实模式：旗舰继承"),
        )


def after_movement(engine: "IronBottomEngine", state: GameState) -> None:
    for formation in state.formations.values():
        active = [state.ships[ship_id] for ship_id in formation.ship_ids if state.ships[ship_id].position and not state.ships[ship_id].sunk and state.ships[ship_id].command_status == "attached"]
        pending = [
            state.ships[ship_id] for ship_id in formation.ship_ids
            if state.ships[ship_id].position is None and not state.ships[ship_id].sunk
            and state.ships[ship_id].command_status == "attached"
        ]
        if active:
            leader = state.ships.get(formation.leader_id)
            if leader not in active:
                formation.leader_id = active[0].id
                leader = active[0]
            formation.heading = leader.heading
            formation.speed = leader.current_speed
            formation.guide_trail = rebuild_guide_trail(state, formation)
            if formation.disruption_turn == state.turn:
                formation.status = "formed"
                formation.disruption_turn = None
                formation.locked_heading = None
                formation.locked_speed = None
        elif pending:
            # Formations containing only scheduled reinforcements are dormant,
            # not destroyed.  Keep their private command chain so the ships
            # become an active formation when the scenario admits them later.
            formation.status = "assembling"
        elif formation.status != "dissolved":
            formation.status = "dissolved"
    for ship_id, withdrawal in list(state.withdrawals.items()):
        ship = state.ships[ship_id]
        if ship.position and _at_edge(ship.position, withdrawal.edge):
            old = ship.position.label
            ship.position = None
            ship.command_status = "withdrawn"
            withdrawal.status = "withdrawn"
            engine._event(
                state, "ship_withdrawn", f"{ship.name} 从 {old} 安全撤出战场",
                payload={"ship_id": ship.id, "edge": withdrawal.edge, "exit_hex": old},
                rule=engine._rule("IBS-R-RC-06", None, "真实模式：自动撤退"),
            )


class RealisticCommander:
    """Formation-level state-machine AI used only when realistic mode is enabled."""

    model = "realistic-command-v1"

    def __init__(self, profile=None) -> None:
        from .tactical import PROFILES, TacticalCommander
        self.profile = profile or PROFILES["balanced"]
        self.tactical = TacticalCommander(profile=self.profile)

    def choose_plan(self, engine: "IronBottomEngine", game_id: str, side: Side):
        state = engine.get(game_id)
        if not state.options.realistic_command:
            return self.tactical.choose_plan(engine, game_id, side)
        if state.phase == Phase.FORMATION_SETUP:
            batch = OrderBatch(
                side=side, phase=state.phase,
                formation_setup=default_setup_orders(state, side),
            )
            intents = {order.formation_id: "建立纵队、指定旗舰与继承链" for order in batch.formation_setup}
            plan = AIPlanSheet(
                turn=state.turn, phase=state.phase,
                situation_summary="按想定锚点建立受指挥的长纵队。",
                phase_goal="完成编队、旗舰和备用旗舰配置。",
                unit_intents=intents,
                orders=batch.model_dump(mode="json"),
                contingency=["布局冲突时缩短舰间距"],
            )
            return plan, batch, []
        if state.phase == Phase.TORPEDO_PLANNING:
            torpedoes = [
                order for order in self.tactical._plan_torpedoes(engine, state, side)
                if state.ships[order.ship_id].command_status == "attached"
            ]
            batch = OrderBatch(side=side, phase=state.phase, torpedoes=torpedoes)
            intents = {order.ship_id: "编队舰执行近距鱼雷齐射" for order in torpedoes}
            return self.tactical._finalize(engine, state, side, batch, intents)
        if state.phase != Phase.MOVEMENT_PLANNING:
            plan, batch, audits = self.tactical.choose_plan(engine, game_id, side)
            return plan, batch, audits

        observation = engine.observe(game_id, side)
        enemies = [ship for ship in observation.ships if ship.side != side and ship.position and not ship.sunk]
        context = self.tactical._build_movement_context(
            engine, state, side, enemies, self.tactical._ai_rng(state, side)
        )
        # Realistic mode plans only formation leaders at the tactical layer.  Followers
        # are generated by expand_movement_orders from the shared wake; asking the
        # classic per-ship planner to reserve independent follower paths can create a
        # false dead end before formation following is even attempted.
        movement: list[MovementOrder] = []
        reserved: list[tuple[ShipState, MovementOrder]] = []
        for formation in sorted(state.formations.values(), key=lambda item: item.id):
            if formation.side != side or formation.status == "dissolved":
                continue
            leader = state.ships.get(formation.leader_id)
            if not leader or not leader.position or leader.sunk or leader.command_status != "attached":
                leader = next((
                    state.ships[ship_id] for ship_id in formation.ship_ids
                    if state.ships[ship_id].position and not state.ships[ship_id].sunk
                    and state.ships[ship_id].command_status == "attached"
                ), None)
            if leader is None:
                continue
            try:
                order = self.tactical._movement_order_for(engine, state, leader, context, reserved)
            except ValueError:
                # Formation leaders are only provisional at this layer.  If
                # independent leader reservations form a cyclic dead end,
                # choose an individually legal route and let the formation
                # expander/simultaneous resolver perform deterministic
                # formation emergency stops.
                # A zero-cost placeholder may itself be individually
                # uncommitable. That is intentional here: expansion below
                # detects it and replaces it with a common-speed, detachment,
                # or formation-emergency-stop order before submission.
                order = MovementOrder(ship_id=leader.id, plan="0")
            movement.append(order)
            reserved.append((leader, order))
        contact_movement = [
            ContactMovementOrder(marker_id=marker.id, plan="4")
            for marker in observation.markers
            if marker.kind == "contact" and marker.secret_side == side and marker.position
        ]
        visible_enemy = any(ship.side != side for ship in observation.ships)
        search_target = None if visible_enemy else public_search_target(state, side)
        tactical_batch = OrderBatch(
            side=side, phase=state.phase,
            movement=movement, contact_movement=contact_movement,
        )
        audits = []
        by_ship = {order.ship_id: order for order in tactical_batch.movement}
        formation_orders: list[FormationMovementOrder] = []
        intents: dict[str, str] = {}
        for formation in state.formations.values():
            if formation.side != side or formation.status == "dissolved":
                continue
            members = [
                state.ships[ship_id] for ship_id in formation.ship_ids
                if state.ships[ship_id].position and not state.ships[ship_id].sunk
                and state.ships[ship_id].command_status == "attached"
            ]
            if not members:
                continue
            leader = state.ships.get(formation.leader_id)
            if leader not in members:
                leader = members[0]
            leader_plan = by_ship.get(leader.id, MovementOrder(ship_id=leader.id, plan="0")).plan
            if search_target is not None:
                leader_plan = self._search_plan(engine, state, leader, search_target)
            leader_commands = engine.movement_commands(MovementOrder(ship_id=leader.id, plan=leader_plan))
            if any(command.endswith("120") for command in leader_commands):
                # A 120-degree in-place impulse cannot propagate down a spaced
                # column in the same global pulse. The formation AI chooses an
                # equal-cost straight programme; human previews remain free to
                # use 120-degree turns when every follower can reach the bend.
                leader_plan = str(engine.movement_cost(leader_plan, leader_commands))
            minimum = max(engine._legal_speed_range(ship, state.turn)[0] for ship in members)
            maximum = min(engine._legal_speed_range(ship, state.turn)[1] for ship in members)
            if formation.disruption_turn == state.turn:
                leader_plan = str(formation.locked_speed or 0)
                intents[formation.id] = "指挥中断：按上轮航向和航速直航"
            elif minimum <= maximum:
                cost = engine.movement_cost(leader_plan, engine.movement_commands(MovementOrder(ship_id=leader.id, plan=leader_plan)))
                if not minimum <= cost <= maximum:
                    # A straight common-speed order is always simpler and safer than
                    # detaching a healthy ship solely because the tactical scorer chose
                    # a route outside the group intersection.
                    leader_plan = str(maximum)
                intents[formation.id] = "领舰机动，后舰沿共享航迹尾随"
            else:
                leader_min, leader_max = engine._legal_speed_range(leader, state.turn)
                speed = leader_max
                detach = [
                    ship.id for ship in members
                    if not engine._legal_speed_range(ship, state.turn)[0] <= speed <= engine._legal_speed_range(ship, state.turn)[1]
                ]
                leader_plan = str(speed)
                formation_orders.append(FormationMovementOrder(
                    formation_id=formation.id, leader_plan=leader_plan,
                    speed_decision={
                        "formation_id": formation.id, "action": "detach",
                        "detach_ship_ids": detach,
                    },
                ))
                intents[formation.id] = "速度区间断裂：受损舰脱队撤退"
                continue
            formation_orders.append(FormationMovementOrder(
                formation_id=formation.id,
                leader_plan=leader_plan,
                spacing=formation.spacing,
            ))
        batch = OrderBatch(
            side=side, phase=state.phase,
            formation_movement=formation_orders,
            contact_movement=tactical_batch.contact_movement,
        )
        _prepared, expansion_errors, _detach = expand_movement_orders(engine, state, batch)
        if expansion_errors:
            # Tactical routes may cross a trailing station. Retry with a
            # common straight programme, selected from the full formation's
            # legal speed intersection. This is still a formation-level
            # decision and never falls back to independent ship movement.
            safe_orders: list[FormationMovementOrder] = []
            for formation_order in formation_orders:
                formation = state.formations[formation_order.formation_id]
                members = [
                    state.ships[ship_id] for ship_id in formation.ship_ids
                    if state.ships[ship_id].position and not state.ships[ship_id].sunk
                    and state.ships[ship_id].command_status == "attached"
                ]
                minimum = max((engine._legal_speed_range(ship, state.turn)[0] for ship in members), default=0)
                maximum = min((engine._legal_speed_range(ship, state.turn)[1] for ship in members), default=0)
                if minimum <= maximum:
                    speed = max(minimum, min(maximum, formation.speed))
                    safe_orders.append(FormationMovementOrder(
                        formation_id=formation.id,
                        leader_plan=str(speed),
                        spacing=formation.spacing,
                        speed_decision={
                            "formation_id": formation.id,
                            "action": "reduce",
                            "speed": speed,
                        },
                    ))
                else:
                    leader = state.ships.get(formation.leader_id)
                    if leader not in members:
                        leader = members[0]
                    speed = engine._legal_speed_range(leader, state.turn)[1]
                    detach = [
                        ship.id for ship in members
                        if not engine._legal_speed_range(ship, state.turn)[0]
                        <= speed <= engine._legal_speed_range(ship, state.turn)[1]
                    ]
                    safe_orders.append(FormationMovementOrder(
                        formation_id=formation.id,
                        leader_plan=str(speed),
                        spacing=formation.spacing,
                        speed_decision={
                            "formation_id": formation.id,
                            "action": "detach",
                            "detach_ship_ids": detach,
                        },
                    ))
                intents[formation.id] = "航迹冲突：保持纵队直航"
            batch.formation_movement = safe_orders
            # A collision can leave a rear ship several stations away from the
            # shared wake.  First slow only the affected formation.  If the
            # follower still cannot regain station at the formation's minimum
            # legal speed, it is genuinely unable to maintain the column and
            # is permanently detached under IBS-R-RC-04.
            for _attempt in range(16):
                _prepared, retry_errors, _detach = expand_movement_orders(engine, state, batch)
                if not retry_errors:
                    break
                changed = False
                for error in retry_errors:
                    if error.startswith("friendly formation conflict at MF "):
                        try:
                            pair = error.split(": ", 1)[1].split(" / ")
                        except IndexError:
                            pair = []
                        conflict_orders = []
                        for ship_id in pair:
                            formation_id = state.ships.get(ship_id).formation_id if state.ships.get(ship_id) else None
                            candidate = next((item for item in batch.formation_movement if item.formation_id == formation_id), None)
                            if candidate and candidate not in conflict_orders:
                                conflict_orders.append(candidate)
                        # Break simultaneous intersection timing by slowing one
                        # of the two columns, preserving the other formation's
                        # tactical route and avoiding independent ship edits.
                        for candidate in reversed(conflict_orders):
                            formation = state.formations[candidate.formation_id]
                            members = [
                                state.ships[ship_id] for ship_id in formation.ship_ids
                                if state.ships[ship_id].position and not state.ships[ship_id].sunk
                                and state.ships[ship_id].command_status == "attached"
                            ]
                            minimum = max((engine._legal_speed_range(ship, state.turn)[0] for ship in members), default=0)
                            current = int(candidate.leader_plan) if candidate.leader_plan.isdigit() else formation.speed
                            if current > minimum:
                                current -= 1
                                candidate.leader_plan = str(current)
                                candidate.speed_decision = FormationSpeedDecision(
                                    formation_id=formation.id, action="reduce", speed=current,
                                )
                                changed = True
                                break
                            candidate.leader_plan = "0"
                            if candidate.speed_decision and candidate.speed_decision.action == "detach":
                                candidate.speed_decision.emergency_stop = True
                            else:
                                candidate.speed_decision = FormationSpeedDecision(
                                    formation_id=formation.id,
                                    action="reduce",
                                    speed=0,
                                    emergency_stop=True,
                                )
                            changed = True
                            break
                        continue
                    formation_order = next(
                        (item for item in batch.formation_movement if error.startswith(f"{item.formation_id}:")),
                        None,
                    )
                    if formation_order is None:
                        continue
                    formation = state.formations[formation_order.formation_id]
                    members = [
                        state.ships[ship_id] for ship_id in formation.ship_ids
                        if state.ships[ship_id].position and not state.ships[ship_id].sunk
                        and state.ships[ship_id].command_status == "attached"
                    ]
                    minimum = max((engine._legal_speed_range(ship, state.turn)[0] for ship in members), default=0)
                    current = int(formation_order.leader_plan) if formation_order.leader_plan.isdigit() else formation.speed
                    forced_separation = " forced movement prevents formation following" in error
                    if current > minimum and not forced_separation:
                        current -= 1
                        formation_order.leader_plan = str(current)
                        if not (formation_order.speed_decision and formation_order.speed_decision.action == "detach"):
                            formation_order.speed_decision = FormationSpeedDecision(
                                formation_id=formation.id,
                                action="reduce",
                                speed=current,
                            )
                        changed = True
                        continue
                    trail_failure = (
                        " cannot follow guide trail" in error
                        or " is no longer on the guide trail" in error
                    )
                    if " follower speed " in error or trail_failure or forced_separation:
                        follower = next((ship for ship in members if f": {ship.name} " in error or f": {ship.id} " in error), None)
                        if follower and len(members) >= 1 and (forced_separation or current <= minimum):
                            already = set(
                                formation_order.speed_decision.detach_ship_ids
                                if formation_order.speed_decision and formation_order.speed_decision.action == "detach"
                                else []
                            )
                            already.add(follower.id)
                            formation_order.speed_decision = FormationSpeedDecision(
                                formation_id=formation.id,
                                action="detach",
                                detach_ship_ids=sorted(already),
                                emergency_stop=bool(formation_order.speed_decision and formation_order.speed_decision.emergency_stop),
                            )
                            remaining = [ship for ship in members if ship.id not in already]
                            if remaining:
                                common_minimum = max(engine._legal_speed_range(ship, state.turn)[0] for ship in remaining)
                                common_maximum = min(engine._legal_speed_range(ship, state.turn)[1] for ship in remaining)
                                if common_minimum <= common_maximum:
                                    formation_order.leader_plan = str(common_maximum)
                            changed = True
                    elif "detach decision leaves incompatible formation ships" in error:
                        leader = state.ships.get(formation.leader_id)
                        if leader not in members:
                            leader = members[0]
                        speed = engine._legal_speed_range(leader, state.turn)[1]
                        already = set(
                            formation_order.speed_decision.detach_ship_ids
                            if formation_order.speed_decision and formation_order.speed_decision.action == "detach"
                            else []
                        )
                        already.update(
                            ship.id for ship in members
                            if not engine._legal_speed_range(ship, state.turn)[0]
                            <= speed <= engine._legal_speed_range(ship, state.turn)[1]
                        )
                        if already and len(already) < len(members):
                            formation_order.leader_plan = str(speed)
                            formation_order.speed_decision = FormationSpeedDecision(
                                formation_id=formation.id,
                                action="detach",
                                detach_ship_ids=sorted(already),
                            )
                            changed = True
                if not changed:
                    break
        plan = AIPlanSheet(
            turn=state.turn, phase=state.phase,
            situation_summary="按编队指挥链评估共同航速与领舰航路。",
            phase_goal="保持纵队、避免友舰冲突并维持火力态势。",
            unit_intents=intents,
            orders=batch.model_dump(mode="json"),
            contingency=["共同速度不足则降速", "速度区间断裂则受损舰脱队"],
        )
        return plan, batch, audits

    def _search_plan(
        self, engine: "IronBottomEngine", state: GameState, leader, target: HexCoord
    ) -> str:
        """Choose a legal route toward a published zone before first contact."""
        choices: list[tuple[int, int, int, str, str]] = []
        for entry in engine.movement_candidates(state, leader, include_plans=False)["reachable"]:
            hexc = HexCoord(q=entry["hex"]["q"], r=entry["hex"]["r"])
            for heading in entry["final_headings"]:
                plan = self.tactical._path_to(engine, state, leader, hexc, heading)
                if plan is None:
                    continue
                choices.append((
                    hexc.distance(target),
                    -int(entry["cost"]),
                    0 if heading == leader.heading else 1,
                    hexc.label,
                    plan,
                ))
        return min(choices)[-1] if choices else "0"

    def choose_orders(self, engine: "IronBottomEngine", game_id: str, side: Side) -> OrderBatch:
        return self.choose_plan(engine, game_id, side)[1]
