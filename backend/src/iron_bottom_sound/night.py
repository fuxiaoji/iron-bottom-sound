"""Versioned IBS night rules. Called only by the adjudication engine.

All rule parameters come from the per-game frozen source snapshot; this module
does not read enemy plans to build observation, candidates or tactical proposals.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import date
import hashlib
import json

from .data import STRUCTURED, ROOT, read_yaml, load_scenario
from .models import HexCoord, MarkerState, Side, Phase, DiceRoll


def enabled(state):
    return state.options.ruleset_version == "night-v2"


def config(state):
    return state.rule_snapshot.get("night", {})


def unlimited_turns(state):
    from .savo import enabled as savo_enabled
    return savo_enabled(state) and bool(config(state)["savo"]["infinite_turns"])


def snapshot(state):
    data = read_yaml(STRUCTURED / "rules/night-v2.yaml")
    overlay = read_yaml(STRUCTURED / "maps/terrain-overlays.yaml")
    state.rule_snapshot = json.loads(json.dumps({
        "night": data, "overlays": overlay, "scenario": load_scenario(state.scenario_id),
        "sources": {
            path: hashlib.sha256((ROOT / path).read_bytes()).hexdigest()
            for path in (
                "resources/originals/rules/iron-bottom-sound-iv-rules-zh.pdf",
                "resources/originals/rules/player-aid-tables-zh.pdf",
                "resources/originals/scenarios/scenario-book-zh.pdf",
                "resources/originals/records/ship-record-manual-1.1-zh.pdf",
                "resources/originals/assets/images/岛屿.jpg",
            )
        },
    }, default=str, ensure_ascii=False))
    from .scenario_rules import scenario_rules
    state.rule_snapshot["gunnery_extension"] = list(scenario_rules(state.scenario_id).gunnery_extension)


def initialize(state):
    if not enabled(state):
        return
    snapshot(state)
    from . import recognition
    recognition.initialize(state)
    placement = config(state)["terrain"].get(state.scenario_id)
    if placement:
        overlay = state.rule_snapshot["overlays"]["overlays"][placement["overlay"]]
        aq, ar = overlay["anchors"][placement["anchor"]]
        ar -= aq // 2
        target = HexCoord.from_label(placement["at"])
        for kind, destination in (("land", state.land_hexes), ("coast", state.coast_hexes)):
            for cell in overlay["cells"][kind]:
                q, row = map(int, cell.split(","))
                tq, tr = q - aq + target.q, row - q // 2 - ar + target.r
                dr = tr + tq // 2
                if 0 <= tq < state.map_columns and 0 <= dr < state.map_rows:
                    coord = HexCoord(q=tq, r=tr)
                    destination.add(coord.label)
        overlaps = [s.name for s in state.ships.values() if s.position and s.position.label in state.land_hexes]
        if overlaps:
            state.scenario_state.setdefault("rule_blockers", []).append({"id": "IBS-Q-025", "rules": [placement["rule_id"]],
                "text": "现有岛屿校准平移与原典初始部署冲突，拒绝自动搬船；需核验覆盖图朝向：" + "、".join(overlaps)})
    if len(set(state.options.squall_hexes)) != len(state.options.squall_hexes):
        raise ValueError("雨飑中心不能重复")
    if state.options.squall_hexes and not state.options.optional_rules.squalls:
        raise ValueError("配置雨飑位置必须启用规则9.6")
    for index, label in enumerate(state.options.squall_hexes):
        pos = HexCoord.from_label(label)
        if not on_map(state, pos):
            raise ValueError("雨飑位置越界：" + label)
        state.markers.append(MarkerState(id=f"SQ-{index+1}", kind="squall", position=pos))
    if state.scenario_id == "IBS-S-10":
        state.scenario_state.setdefault("rule_blockers", []).extend(deepcopy(config(state)["savo"]["blockers"]))
        from .savo import initialize as initialize_savo
        initialize_savo(state)
    # Scenario deployment overrides free-edge hidden-marker deployment.
    if state.scenario_id == "IBS-S-10" and state.options.optional_rules.hidden_contacts:
        raise ValueError("萨沃岛固定奇袭部署优先于9.1自由地图边缘部署；请关闭隐藏标记")


def on_map(state, p):
    return 0 <= p.q < state.map_columns and 0 <= p.r + p.q // 2 < state.map_rows


def scenario_date(state):
    value = state.rule_snapshot.get("scenario", {}).get("date", "1942-01-01")
    return date.fromisoformat(str(value))


def searchlight_range(state, ship):
    data = config(state)["searchlights"]
    return data["from_1928" if scenario_date(state).year >= 1928 else "before_1928"][ship.side.value]


def optical(engine, state, origin, target):
    if not origin or not target or engine._weather_blocked(state, origin) or engine._weather_blocked(state, target):
        return False
    return not engine._terrain_blocks_sight(state, origin, target)


def illuminated(state, ship):
    return any(
        (m.kind == "star_shell" and m.expires_turn == state.turn and m.position
         and ship.position and m.position.distance(ship.position) <= config(state)["illumination"]["radius"])
        or (m.kind == "searchlight" and ship.id in (m.target_ship_id, m.ship_id))
        for m in state.markers
    )


def optical_ship(engine, state, observer, target):
    if not optical(engine, state, observer.position, target.position):
        return False
    return (observer.position.distance(target.position) <= state.visibility[observer.side.value]
            or illuminated(state, target) or bool(target.fire_markers)
            or (state.options.optional_rules.silhouettes and engine._silhouetted(state, target)))


def radar_contact(engine, state, observer, target):
    return bool(state.options.optional_rules.radar and observer.radar and not observer.radar_destroyed
                and observer.position and target.position and not target.sunk
                and not engine._weather_blocked(state, observer.position)
                and not engine._weather_blocked(state, target.position)
                and not engine._terrain_blocks_sight(state, observer.position, target.position, radar=True))


def can_fire(engine, state, observer, target):
    if target.sunk or not target.position or not observer.position:
        return False
    if observer.position.distance(target.position) > config(state)["penetration_coverage"]["max_distance"]:
        return False  # Source-blocked adjudication, NOT a fabricated weapon range.
    if optical_ship(engine, state, observer, target):
        return True
    radar = config(state)["radar"]
    allowed = (observer.id.startswith("IBS-U-USN-") and
               (scenario_date(state).year >= radar["us_fire_from_year"] or observer.id in radar["early_us_exceptions"]))
    if state.options.radar_1942_variant and observer.id.startswith("IBS-U-USN-") and scenario_date(state).year == 1942:
        first = state.scenario_state.get("radar_first_fire", {}).get(observer.id)
        if first is None or first == state.turn:
            targets = [s for s in state.ships.values() if s.side != observer.side and radar_contact(engine,state,observer,s)]
            nearest = min((observer.position.distance(s.position) for s in targets), default=-1)
            return observer.position.distance(target.position) == nearest and radar_contact(engine,state,observer,target)
        allowed = True
    return bool(allowed and radar_contact(engine, state, observer, target))


def candidates(engine, state, side):
    result = {"illumination": [], "searchlights": [], "smoke": [], "aircraft_illumination": [], "blind_torpedo_reveals": []}
    if enabled(state) and state.phase == Phase.TORPEDO_PLANNING and state.options.optional_rules.blind_torpedoes:
        result["blind_torpedo_reveals"] = [{"track_id": t.id, "position": t.position.label} for t in state.torpedo_tracks if t.side == side and t.hidden]
    if not enabled(state) or state.phase != Phase.GUNNERY:
        return result
    own = [s for s in state.ships.values() if s.side == side and s.position and not s.sunk
           and not engine._weather_blocked(state, s.position)]
    # Only side-visible opponents may be used in a proposal or target selector.
    enemies = [s for s in state.ships.values() if s.side != side and s.position and not s.sunk
               and any(optical_ship(engine, state, o, s) or radar_contact(engine, state, o, s) for o in own)]
    for ship in own:
        if state.options.optional_rules.star_shells and not ship.mfc_destroyed and not ship.guns_disabled_turns:
            groups = []
            for kind in ("secondary", "tertiary"):
                for broadside in ("port", "starboard"):
                    group = [m for m in ship.gun_mounts if m.kind == kind and broadside in m.arcs and not m.destroyed and not m.fired_this_phase]
                    if group:
                        groups.append((group, broadside))
            if not groups:
                group = [m for m in ship.gun_mounts if m.kind == "primary" and not m.destroyed and not m.fired_this_phase]
                groups.extend(([m], None) for m in group)
            for group, broadside in groups:
                result["illumination"].append({"ship_id": ship.id, "mount_id": group[0].id,
                    "broadside": broadside,
                    "occupied_mount_ids": [m.id for m in group], "valid_from_turn": state.turn + config(state)["illumination"]["delay_turns"],
                    "suggested_hexes": [s.position.model_dump(mode="json") for s in enemies]})
        if state.options.optional_rules.searchlights and not ship.mfc_destroyed:
            for target in enemies:
                if optical(engine, state, ship.position, target.position) and ship.position.distance(target.position) <= searchlight_range(state, ship):
                    result["searchlights"].append({"ship_id": ship.id, "target_id": target.id})
        if state.options.optional_rules.smoke and ship.ship_type in config(state)["smoke"]["ship_types"]:
            result["smoke"].append({"ship_id": ship.id})
    if state.scenario_id == "IBS-S-10" and side == Side.AXIS and state.turn == config(state)["savo"]["aircraft_turn"]:
        result["aircraft_illumination"] = [{"count": config(state)["savo"]["aircraft_count"], "available": True}]
    return result


def validate(engine, state, batch):
    errors = []
    legal = candidates(engine, state, batch.side)
    reveals = {c["track_id"] for c in legal["blind_torpedo_reveals"]}
    if len(set(batch.blind_torpedo_reveals)) != len(batch.blind_torpedo_reveals) or not set(batch.blind_torpedo_reveals) <= reveals:
        errors.append("只能在移动计划完成后揭示本方尚未公开的隐蔽鱼雷")
    illumination = {(c["ship_id"], c["mount_id"], c["broadside"]): c for c in legal["illumination"]}
    taken = set()
    for order in batch.illumination:
        row = illumination.get((order.ship_id, order.mount_id, order.broadside))
        if not row:
            errors.append(f"{order.ship_id}: 非法照明弹炮组")
            continue
        mounts = {(order.ship_id, mid) for mid in row["occupied_mount_ids"]}
        if taken & mounts:
            errors.append("照明弹炮组重复占用")
        taken |= mounts
        if not on_map(state, order.target_hex):
            errors.append("照明弹目标越界")
    for order in batch.gunnery:
        ship = state.ships.get(order.ship_id)
        targets = {m.target_id for m in order.mounts} | {t for t in (order.primary_target, order.secondary_target) if t}
        for tid in targets:
            target = state.ships.get(tid)
            if ship and target and ship.position and target.position and ship.position.distance(target.position)>config(state)["penetration_coverage"]["max_distance"]:
                errors.append("IBS-Q-021: 炮击进入原穿甲表未覆盖距离，阻断自动裁决（不是最大射程裁定）")
        ids = [m.mount_id for m in order.mounts]
        if not ids and ship:
            ids = [m.id for m in ship.gun_mounts if (m.kind == "primary" and order.primary_target)
                   or (m.kind != "primary" and order.secondary_target)]
        if any((order.ship_id, mid) in taken for mid in ids):
            errors.append("照明弹占用炮组不能同时炮击")
    lights = {(c["ship_id"], c["target_id"]) for c in legal["searchlights"]}
    active = set()
    for order in batch.searchlights:
        if order.active and ((order.ship_id, order.target_id) not in lights or order.ship_id in active):
            errors.append(f"{order.ship_id}: 探照灯目标不在光学视线／使用范围内或重复")
        active.add(order.ship_id)
    if batch.aircraft_illumination and (not legal["aircraft_illumination"] or state.scenario_state.get("aircraft_illumination_used")):
        errors.append("本阶段没有可投放的飞机照明弹")
    if any(not on_map(state, h) for h in batch.aircraft_illumination):
        errors.append("飞机照明弹目标越界")
    if state.scenario_state.get("rule_blockers"):
        errors.extend(f"{b['id']}: {b['text']}" for b in state.scenario_state["rule_blockers"])
    return errors


def blocked_gunnery(engine, state, side):
    result=[]
    for ship in state.ships.values():
        if ship.side!=side or ship.sunk or not ship.position:
            continue
        for target in state.ships.values():
            if target.side!=side and not target.sunk and target.position and ship.position.distance(target.position)>config(state)["penetration_coverage"]["max_distance"] and (optical_ship(engine,state,ship,target) or radar_contact(engine,state,ship,target)):
                result.append({"ship_id":ship.id,"target_id":target.id,"id":"IBS-Q-021","text":config(state)["penetration_coverage"]["reason"]})
    return result


def prepare_gunnery(engine, state, batches):
    data = config(state)
    for batch in batches:
        legal = candidates(engine, state, batch.side)
        groups = {(c["ship_id"], c["mount_id"], c["broadside"]): c for c in legal["illumination"]}
        for order in batch.illumination:
            ship = state.ships[order.ship_id]
            for m in ship.gun_mounts:
                if m.id in groups[(ship.id, order.mount_id, order.broadside)]["occupied_mount_ids"]:
                    m.fired_this_phase = True
            # Preserve pending targets privately until their NEXT-turn resolution.
            state.scenario_state.setdefault("pending_illumination", []).append({
                "side": batch.side.value, "ship_id": ship.id, "position": order.target_hex.model_dump(),
                "turn": state.turn + data["illumination"]["delay_turns"],
            })
            engine._event(state, "illumination_planned", f"{ship.name} 计划下回合照明弹",
                payload={"secret_side": batch.side.value, "ship_id": ship.id, "target_hex": order.target_hex.label},
                rule=engine._rule("IBS-R-09.3", 13, "9.3 预先计划"))
        for pos in batch.aircraft_illumination:
            state.scenario_state["aircraft_illumination_used"] = True
            state.markers.append(MarkerState(id=f"AIR-STAR-{state.turn}", kind="star_shell", position=pos, expires_turn=state.turn))
            engine._event(state, "aircraft_illumination", "日军飞机投放照明弹", payload={"position": pos.label},
                rule=engine._scenario_rule("IBS-S-10-R11", 10, "飞机照明弹"))
        for order in batch.searchlights:
            if order.active and order.target_id:
                state.markers.append(MarkerState(id=f"SEARCH-{state.turn}-{order.ship_id}", kind="searchlight",
                    ship_id=order.ship_id, target_ship_id=order.target_id, expires_turn=state.turn))
                engine._event(state, "searchlight_activated", "开启探照灯",
                    payload={"ship_id": order.ship_id, "target_id": order.target_id}, rule=engine._rule("IBS-R-09.4", 13, "9.4"))
        smoke_ids = set(batch.smoke_ships) | {o.ship_id for o in batch.smoke if o.deploy}
        for sid in sorted(smoke_ids):
            ship = state.ships[sid]
            path = state.scenario_state.get("turn_paths", {}).get(sid, [])
            positions = {HexCoord.model_validate(p).label: HexCoord.model_validate(p) for p in path}
            if ship.position:
                positions[ship.position.label] = ship.position
            for label, pos in positions.items():
                state.markers.append(MarkerState(id=f"SMOKE-{state.turn}-{sid}-{label}", kind="smoke", position=pos, expires_turn=state.turn))
            engine._event(state, "smoke_released", f"{ship.name} 沿航迹释放烟幕",
                payload={"ship_id": sid, "hexes": list(positions)}, rule=engine._rule("IBS-R-09.7", 14, "9.7"))
    from .recognition import refresh
    refresh(engine, state)


def after_movement(engine, state):
    pending = state.scenario_state.get("pending_illumination", [])
    remain = []
    for order in pending:
        if order["turn"] != state.turn:
            remain.append(order)
            continue
        ship = state.ships[order["ship_id"]]
        roll, die = engine._roll_d6(state)
        data = config(state)["illumination"]
        if ship.id.startswith(("IBS-U-IJN-", "IBS-U-KM-")):
            modifier = data["japanese_german_modifier"]
        elif ship.id.startswith("IBS-U-USN-") and scenario_date(state) < date.fromisoformat(data["early_us_before"]):
            modifier = data["early_us_modifier"]
        else:
            modifier = data["other_modifier"]
        success = roll + modifier >= data["successful_modified_roll"]
        pos = HexCoord.model_validate(order["position"])
        if success:
            state.markers.append(MarkerState(id=f"STAR-{state.turn}-{ship.id}", kind="star_shell", position=pos, expires_turn=state.turn))
        engine._event(state, "star_shell_fired", f"{ship.name} 照明弹检定{roll}{modifier:+}：{'生效' if success else '失效'}",
            payload={"ship_id": ship.id, "success": success, "position": pos.label},
            rule=engine._rule("IBS-R-09.3", 13, "9.3 下回合移动后检定"),
            dice=DiceRoll(dice=[die], notation="1D6", raw=roll, adjusted=roll+modifier))
    state.scenario_state["pending_illumination"] = remain


def move_squalls(engine, state):
    markers = [m for m in state.markers if m.kind == "squall" and m.position]
    if not markers:
        return
    data = config(state)["squalls"]
    roll, die = engine._roll_d6(state)
    distance = data["movement"][str(roll)]
    for marker in markers:
        for _ in range(distance):
            try:
                marker.position = marker.position.neighbor(data["heading"], columns=state.map_columns, rows=state.map_rows)
            except ValueError:
                marker.position = None
                break
    engine._event(state, "squalls_moved", f"所有雨飑统一移动{distance}格",
        payload={"distance": distance, "marker_ids": [m.id for m in markers]},
        rule=engine._rule("IBS-R-09.6", 13, "9.6 统一骰"), dice=DiceRoll(dice=[die], notation="1D6", raw=roll))
    state.markers = [m for m in state.markers if m.kind != "squall" or m.position]


def smoke_crossed(engine, state, attacker, target):
    if not state.options.optional_rules.smoke or not attacker.position or not target.position:
        return False
    cells = {m.position.label for m in state.markers if m.kind == "smoke" and m.position}
    return any(p.label in cells for p in engine._hex_line(attacker.position, target.position))


def project_event(state, event, side):
    """Project using knowledge at event time, never today's newly seen enemies."""
    known = event.payload.get("known_ship_ids")
    if known is None:
        return event.model_copy(deep=True)
    referenced = set().union(*(set(ids) for ids in known.values()))
    hidden = referenced - set(known.get(side.value, []))
    def redact(value):
        if isinstance(value, str):
            for sid in hidden:
                value = value.replace(sid, "unidentified-ship").replace(state.ships[sid].name, "未识别舰")
            return value
        if isinstance(value, list):
            return [redact(v) for v in value]
        if isinstance(value, dict):
            return {redact(k): redact(v) for k,v in value.items() if k not in ("known_ship_ids", "initial_state", "upgrade_state")}
        return value
    result = event.model_copy(deep=True)
    result.payload = redact(result.payload)
    result.message = redact(result.message)
    return result


def losses(state, side, visible_ids, safe_events, debug=False):
    full = debug or state.phase == Phase.COMPLETE
    confirmed = {e.payload.get("ship_id") for e in safe_events if e.type == "ship_sunk"}
    from . import recognition
    if recognition.enabled(state):
        aliases = {recognition.contact_id(state, side, s.id):s.id for s in state.ships.values()}
        confirmed = {aliases.get(sid,sid) for sid in confirmed}
    result = {}
    for which in Side:
        known = [s for s in state.ships.values() if s.side == which and
                 (full or (which == side and not state.options.command_delay_mode) or s.id in visible_ids or s.id in confirmed)]
        sunk = [s for s in known if s.sunk and (full or which == side or s.id in confirmed)]
        damaged = [s for s in known if not s.sunk and s.position and s.hull < s.max_hull
                   and (full or which == side or not state.options.optional_rules.hidden_damage)]
        result[which.value] = {"scope": "complete" if full or (which == side and not state.options.command_delay_mode) else "confirmed",
            "sunk_count": len(sunk), "by_type": {t: sum(s.ship_type == t for s in sunk) for t in sorted({s.ship_type for s in sunk})},
            "by_displacement": {b: sum(s.displacement_band == b for s in sunk) for b in "ABCDEFGHI"},
            "sunk": [{"id": s.id, "name": s.name, "ship_type": s.ship_type, "displacement_band": s.displacement_band} for s in sunk],
            "damaged": [{"id": s.id, "name": s.name, "hull_lost": s.max_hull-s.hull} for s in damaged]}
    return result


def observation(engine, state, side, ships, safe_events, debug):
    if state.options.command_delay_mode and not debug and state.phase != Phase.COMPLETE:
        from .command_observation import fleet_observation
        fleet = fleet_observation(engine, state, side)
        ids = set(fleet.embarked.get("ship_ids", []))
        # No global damage precision for non-embarked formations.
        ships = [s for s in ships if s.side != side or s.id in ids]
        safe_events = [e for e in safe_events if e.payload.get("ship_id") in ids]
    if not enabled(state):
        return {"ruleset_version": state.options.ruleset_version, "battle_losses": losses(state, side, {s.id for s in ships}, safe_events, debug)}
    visible_own = {s.id for s in ships if s.side == side}
    own = [s for s in state.ships.values() if s.side == side and s.id in visible_own and s.position and not s.sunk]
    cache = getattr(engine, "_night_view_cache", {})
    engine._night_view_cache = cache
    key = (state.game_id, side.value, state.visibility[side.value], tuple((o.id, o.position.label) for o in own),
           tuple((m.kind, m.position.label if m.position else None) for m in state.markers), tuple(sorted(state.land_hexes)))
    if key not in cache:
        cells = set()
        for observer in own:
            for pos in disc(state, observer.position, state.visibility[side.value]):
                if pos.label not in cells and optical(engine, state, observer.position, pos):
                    cells.add(pos.label)
        if len(cache) > 64:
            cache.clear()
        cache[key] = sorted(cells)
    cells = cache[key]
    # Illumination is visible beyond the unlit horizon only across a legal LOS.
    lit_cells = set(cells)
    for marker in state.markers:
        if marker.kind == "star_shell" and marker.position and marker.expires_turn == state.turn:
            for p in disc(state, marker.position, config(state)["illumination"]["radius"]):
                if any(optical(engine, state, o.position, p) for o in own):
                    lit_cells.add(p.label)
    contacts = {}
    for target in ships:
        if target.side == side:
            continue
        actual = state.ships[target.id]
        contacts[target.id] = "optical" if any(optical_ship(engine, state, o, actual) for o in own) else "radar"
        if contacts[target.id] == "optical" and target.position:
            lit_cells.add(target.position.label)
    areas = []
    for marker in state.markers:
        if marker.position and marker.kind in ("star_shell", "squall", "storm", "smoke"):
            if marker.kind == "smoke" and not debug and not any(optical(engine, state, o.position, marker.position) and
                    o.position.distance(marker.position) <= state.visibility[side.value] for o in own):
                continue
            radius = config(state)["illumination"]["radius"] if marker.kind == "star_shell" else (config(state)["squalls"]["radius"] if marker.kind in ("squall", "storm") else 0)
            area = [p.label for p in disc(state, marker.position, radius)]
            areas.append({"id": f"area-{len(areas)}", "kind": marker.kind, "hexes": area,
                          "center": marker.position.label, "expires_turn": marker.expires_turn})
    beams = []
    public_ids = {s.id for s in ships}
    for marker in state.markers:
        if marker.kind == "searchlight" and marker.ship_id in public_ids and marker.target_ship_id in public_ids:
            user, target = state.ships[marker.ship_id], state.ships[marker.target_ship_id]
            if user.position and target.position:
                beams.append({"id": marker.id, "ship_id": user.id, "target_id": target.id,
                              "hexes": [p.label for p in engine._hex_line(user.position, target.position)]})
    # Own future illumination remains private, including in fleet-local command
    # delay views. Previewing a plan never changes the live optical mask.
    pending = [{"ship_id": p["ship_id"], "center": HexCoord.model_validate(p["position"]).label,
                "turn": p["turn"], "hexes": [h.label for h in disc(state, HexCoord.model_validate(p["position"]), config(state)["illumination"]["radius"])]}
               for p in state.scenario_state.get("pending_illumination", [])
               if p.get("side") == side.value and p["ship_id"] in visible_own]
    optional = engine.rules.modifiers["optional"]
    notes = {
        "visibility": f"未照明海域的光学视程为 {state.visibility[side.value]} 格；亮海面为本方可视，蓝色虚线圈为仅雷达接触。陆地和雨区会阻挡接触。",
        "searchlights": f"探照灯本回合照射单舰，并使开灯舰自身可见。依玩家辅助表，炮击被照射目标修正 {optional['target_searchlit']:+}，开灯舰炮击修正 {optional['searchlight_user']:+}；同一目标多束灯不叠加。",
        "star_shells": f"照明弹占用所选炮组，提前 {config(state)['illumination']['delay_turns']} 回合计划；下回合移动后检定，成功照亮中心周围 {config(state)['illumination']['radius']} 格，至该回合炮击结束。照明弹／雷达炮击修正 {optional['star_shell_or_radar_illumination']:+}。",
        "squalls": f"雨飑需在开局指定中心，留空就没有雨区；范围为中心周围 {config(state)['squalls']['radius']} 格，按统一骰移动。雨区阻挡雷达；区内舰不能射击、发射鱼雷或被炮击。",
        "torpedoes": "鱼雷按发射航向逐格推进，进入舰船航迹后检定命中；接触不等于命中。橙色尾迹为已走航迹，箭头为航向，数字为齐射枚数。",
    }
    return {"ruleset_version": "night-v2", "enabled_optional_rules": [k for k,v in state.options.optional_rules.model_dump().items() if v],
        "environment": {"lighting": "night" if state.scenario_id in config(state)["night_scenarios"] else "standard",
                        "optical_hexes": sorted(lit_cells), "contacts": contacts, "areas": areas, "beams": beams,
                        "pending_illumination": pending, "effect_notes": notes, "unlimited_turns": unlimited_turns(state)},
        "terrain": {"land_hexes": sorted(state.land_hexes), "coast_hexes": sorted(state.coast_hexes)},
        "battle_losses": losses(state, side, {s.id for s in ships}, safe_events, debug),
        "rule_blockers": deepcopy(state.scenario_state.get("rule_blockers", []))}


def disc(state, center, radius):
    for q in range(max(0, center.q-radius), min(state.map_columns, center.q+radius+1)):
        for r in range(center.r-radius, center.r+radius+1):
            if 0 <= r+q//2 < state.map_rows:
                pos = HexCoord(q=q, r=r)
                if center.distance(pos) <= radius:
                    yield pos


def tactical_orders(engine, state, side, batch, intents):
    """AI preferences over public, engine-generated candidates, never new rules."""
    from .models import IlluminationOrder, SearchlightOrder
    legal = candidates(engine, state, side)
    view = engine.observe(state.game_id, side)
    enemies = [s for s in view.ships if s.side != side and s.position and not s.sunk]
    if not enemies:
        return
    # Cover only badly damaged screen ships; indiscriminate smoke would spoil
    # friendly gunnery as well as incoming fire.
    firing = {o.ship_id for o in batch.gunnery}
    for row in legal["smoke"]:
        ship = state.ships[row["ship_id"]]
        if ship.hull / ship.max_hull < .35 and ship.id not in firing:
            batch.smoke_ships.append(ship.id)
            intents[ship.id] = "沿实际航迹布烟掩护受损舰"
    reserved = set()
    # One planned area covers a cluster; do not spend every ship's gun group
    # on the same next-turn patch of sea. Only own accepted plans are consulted.
    planned = [HexCoord.model_validate(p["position"]) for p in state.scenario_state.get("pending_illumination", [])
               if p.get("side") == side.value and p["turn"] == state.turn + config(state)["illumination"]["delay_turns"]]
    for row in legal["illumination"]:
        ship = state.ships[row["ship_id"]]
        if ship.id in reserved or (state.options.realistic_command and ship.command_status != "attached"):
            continue
        target = min(enemies, key=lambda s: (ship.position.distance(s.position), s.id))
        if any(center.distance(target.position) <= config(state)["illumination"]["radius"] for center in planned):
            continue
        if target.identified and view.environment.get("contacts", {}).get(target.id) != "radar" and ship.position.distance(target.position) < view.visibility-2:
            continue
        used = {m.mount_id for o in batch.gunnery if o.ship_id == ship.id for m in o.mounts}
        if used.intersection(row["occupied_mount_ids"]):
            # Sacrifice a low-calibre group only when planning for a radar-only contact.
            if view.environment.get("contacts", {}).get(target.id) != "radar" or next(m for m in ship.gun_mounts if m.id==row["mount_id"]).kind == "primary":
                continue
            for order in batch.gunnery:
                if order.ship_id == ship.id:
                    order.mounts = [m for m in order.mounts if m.mount_id not in row["occupied_mount_ids"]]
            batch.gunnery = [o for o in batch.gunnery if o.mounts]
        batch.illumination.append(IlluminationOrder(ship_id=ship.id, mount_id=row["mount_id"], target_hex=target.position, broadside=row["broadside"]))
        reserved.add(ship.id)
        planned.append(target.position)
        intents[ship.id] = "预先计划照明，历史接触不作为实时坐标"
    # Coordinate AFTER reserving illumination mounts: the light must support
    # an actual remaining shot. Each source and each target is used once by
    # this policy (players may still legally choose several lights per target).
    shot_targets = {}
    for order in batch.gunnery:
        targets = {m.target_id for m in order.mounts} | {t for t in (order.primary_target, order.secondary_target) if t}
        for target_id in targets:
            shot_targets.setdefault(target_id, set()).add(order.ship_id)
    sources = {o.ship_id for o in batch.searchlights if o.active}
    lit = {o.target_id for o in batch.searchlights if o.active} | {
        m.target_ship_id for m in state.markers if m.kind == "searchlight" and m.expires_turn == state.turn}
    for target_id in sorted(shot_targets, key=lambda tid: (-len(shot_targets[tid]), tid)):
        if target_id in lit:
            continue
        rows = [r for r in legal["searchlights"] if r["target_id"] == target_id
                and r["ship_id"] in shot_targets[target_id] and r["ship_id"] not in sources]
        if not rows:
            continue
        # Own hull and public positions only; no enemy damage or sealed orders.
        target = next((s for s in enemies if s.id == target_id), None)
        if not target:
            continue
        row = min(rows, key=lambda r: (-state.ships[r["ship_id"]].hull / state.ships[r["ship_id"]].max_hull,
                                      state.ships[r["ship_id"]].position.distance(target.position), r["ship_id"]))
        batch.searchlights.append(SearchlightOrder(**row))
        sources.add(row["ship_id"])
        lit.add(target_id)
        intents[row["ship_id"]] = intents.get(row["ship_id"], "") + f"；单舰照射{target.name}，同目标不重复开灯"
    if legal["aircraft_illumination"]:
        batch.aircraft_illumination = [enemies[0].position]
