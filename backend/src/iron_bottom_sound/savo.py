"""S-10 source-known reinforcement/exit state machine (PDF 10–11).

Canonical games remain blocked while missing deployment and ship records are
unresolved. Tests of this state machine use explicitly labelled synthetic
fixtures, never invent canonical positions or claim the source gaps are passed.
"""
from .models import HexCoord, Side, Phase, DiceRoll
from .night import config, disc


def enabled(state):
    return state.scenario_id == "IBS-S-10" and state.options.ruleset_version == "night-v2"


def initialize(state):
    from .data import make_ship, load_templates
    from .ship_records import load_ship_records
    from .counter_assets import asset_for
    records = load_ship_records()
    missing = []
    for group, row in config(state)["savo"]["reinforcement_groups"].items():
        for sid in row["ships"]:
            record = records.get(sid)
            if record is None:
                missing.append(sid)
                continue
            state.ships[sid] = make_ship({"id": sid, "name": record.name, "side": "allies",
                "asset": asset_for(sid, record.name, record.ship_type)}, load_templates(), records)
    if missing:
        state.scenario_state.setdefault("rule_blockers", []).append({"id": "IBS-Q-026", "rules": ["IBS-S-10-R20"],
            "text": "增援舰缺少已核验舰船记录，禁止套用其它舰参数：" + "、".join(missing)})


def edge(state, p):
    qend = HexCoord.from_label("HH1").q
    return p.q in (0, qend) or p.r+p.q//2 in (0, 26)


def crossing(engine, state, ship, destination):
    if not enabled(state) or ship.side != Side.AXIS or not ship.position or ship.sunk:
        return False
    previous = ship.position
    row, next_row = previous.r+previous.q//2, destination.r+destination.q//2
    east = previous.q == HexCoord.from_label("HH1").q and destination.q > previous.q and 0 <= row < 16
    south = row == 26 and next_row > row and previous.q <= HexCoord.from_label("HH1").q
    if not (east or south):
        return False
    data = config(state)["savo"]
    exits = state.scenario_state.setdefault("savo_exits", {})
    first = ship.id not in exits
    credited = exits.get(ship.id, {}).get("credited_torpedoes", 0)
    spent = state.scenario_state.get("savo_torpedo_expended", {}).get(ship.id, 0)
    exits[ship.id] = {"turn": state.turn, "position": previous.model_dump(), "kind": "reward_exit" if east else "final_exit", "credited_torpedoes": spent}
    ship.position = None
    # Exit is NOT sunk, NOT a generic withdrawal, and never awards kill VP.
    if east and first:
        state.score["axis"] += data["exit_points"]
    state.score["axis"] += max(0, spent-credited) * data["expenditure_points"]
    engine._event(state, "scenario_ship_exited", f"{ship.name} 从 {previous.label} 剧本离场（未沉没）",
        payload={"ship_id": ship.id, "exit_hex": previous.label, "exit_kind": exits[ship.id]["kind"]},
        rule=engine._scenario_rule("IBS-S-10-R12" if east else "IBS-S-10-R4", 10, "离场"))
    state.scenario_state.setdefault("tulagi_trigger", {"turn": state.turn + data["tulagi_delay"], "position": previous.model_dump()})
    return True


def prepare(engine, state):
    if not enabled(state) or state.phase != Phase.REINFORCEMENT:
        return
    data = config(state)["savo"]
    if state.turn < data["reinforcement_from_turn"] or state.scenario_state.get("savo_roll_turn") == state.turn:
        return
    raw, dice = engine._roll_2d6(state)
    selected = data["reinforcement_table"][str(raw)]
    arrived = state.scenario_state.get("savo_arrived_groups", [])
    groups = [g for g in selected if g not in arrived]
    trigger = state.scenario_state.get("tulagi_trigger")
    if trigger and state.turn >= trigger["turn"] and "tulagi" not in arrived:
        groups.append("tulagi")
    state.scenario_state.update(savo_available_groups=groups, savo_roll_turn=state.turn)
    for group in groups:
        for sid in data["reinforcement_groups"][group]["ships"]:
            if sid in state.ships:
                state.ships[sid].reinforcement_turn = state.turn
    engine._event(state, "savo_reinforcement_roll", f"萨沃岛本回合 2D6 增援检定：{raw}",
        payload={"roll": raw, "groups": groups}, dice=DiceRoll(dice=dice, notation="2D6", raw=raw),
        rule=engine._scenario_rule("IBS-S-10-R20", 11, "逐回合增援"))


def candidates(engine, state, side):
    rows = []
    occupied = {s.position.label for s in state.ships.values() if s.position and not s.sunk}
    data = config(state)["savo"]
    if side == Side.ALLIES:
        for group in state.scenario_state.get("savo_available_groups", []):
            info = data["reinforcement_groups"][group]
            if group == "tulagi":
                center = HexCoord.model_validate(state.scenario_state["tulagi_trigger"]["position"])
                entries = [p for p in disc(state, center, data["tulagi_radius"]) if edge(state, p)]
            else:
                start, end = [HexCoord.from_label(h) for h in info["entry"]]
                entries = engine._hex_line(start, end)
            for sid in info["ships"]:
                if sid in state.ships:
                    ship = state.ships[sid]
                    rows.append({"ship_id": sid, "name": ship.name, "asset": ship.asset, "group": group,
                        "max_speed": ship.max_speed_for_turn(state.turn), "mandatory": True,
                        "entry_hexes": [p.label for p in entries if p.label not in occupied and p.label not in state.land_hexes]})
    else:
        for sid, item in state.scenario_state.get("savo_exits", {}).items():
            ship = state.ships[sid]
            if ship.position or ship.sunk or state.turn < item["turn"] + data["return_delay"] or item["kind"] != "reward_exit":
                continue
            entries = [p for p in disc(state, HexCoord.model_validate(item["position"]), data["return_radius"]) if edge(state, p)]
            rows.append({"ship_id": sid, "name": ship.name, "asset": ship.asset, "mandatory": False,
                "max_speed": ship.max_speed_for_turn(state.turn), "entry_hexes": [p.label for p in entries if p.label not in occupied and p.label not in state.land_hexes]})
    return rows


def validate(engine, state, batch):
    rows = {r["ship_id"]: r for r in candidates(engine, state, batch.side)}
    errors = []
    submitted = {o.ship_id for o in batch.reinforcements}
    required = {sid for sid,r in rows.items() if r["mandatory"]}
    if not required <= submitted:
        errors.append("须部署本回合获准增援组全部舰只")
    for order in batch.reinforcements:
        row = rows.get(order.ship_id)
        if not row or order.entry_hex.label not in row["entry_hexes"] or order.speed > row["max_speed"]:
            errors.append(f"{order.ship_id}: 不合法的萨沃岛增援／返场")
    # Eastern force must enter as a uniform single column, any ship may lead.
    eastern = config(state)["savo"]["reinforcement_groups"]["eastern"]["ships"]
    orders = [o for o in batch.reinforcements if o.ship_id in eastern]
    if orders:
        by_pos = {o.entry_hex.label: o for o in orders}
        if len({o.heading for o in orders}) != 1 or len({o.speed for o in orders}) != 1:
            errors.append("东方部队须以同向同速单纵入场")
        else:
            # Check connectivity and collinearity without imposing a leader identity.
            labels = {o.entry_hex.label for o in orders}
            chain = engine._hex_line(min((o.entry_hex for o in orders), key=lambda p:p.r), max((o.entry_hex for o in orders), key=lambda p:p.r))
            if len(chain) != len(orders) or {p.label for p in chain} != labels:
                errors.append("东方部队必须连续占据单纵队格子")
    return errors


def resolve(engine, state):
    groups = config(state)["savo"]["reinforcement_groups"]
    for batch in engine._sealed_batches(state, Phase.REINFORCEMENT):
        for order in batch.reinforcements:
            ship = state.ships[order.ship_id]
            ship.position, ship.heading = order.entry_hex, order.heading
            ship.current_speed = ship.previous_speed = order.speed
            if ship.side == Side.ALLIES:
                alerted = set(state.scenario_state.get("alerted", [])); alerted.add(ship.id)
                state.scenario_state["alerted"] = sorted(alerted)
            engine._event(state, "scenario_ship_entered", f"{ship.name} 入场／返场至 {order.entry_hex.label}",
                payload={"ship_id": ship.id, "entry_hex": order.entry_hex.label},
                rule=engine._scenario_rule("IBS-S-10-R21" if ship.side == Side.ALLIES else "IBS-S-10-R14", 11 if ship.side == Side.ALLIES else 10, "入场／返场"))
    arrived = set(state.scenario_state.get("savo_arrived_groups", []))
    for group in state.scenario_state.get("savo_available_groups", []):
        if all(sid in state.ships and state.ships[sid].position for sid in groups[group]["ships"]):
            arrived.add(group)
    state.scenario_state["savo_arrived_groups"] = sorted(arrived)


def finish(engine, state):
    living = [s for s in state.ships.values() if s.side == Side.AXIS and not s.sunk]
    exits = state.scenario_state.get("savo_exits", {})
    if any(s.position or exits.get(s.id, {}).get("kind") != "final_exit" for s in living):
        return
    data = config(state)["savo"]
    margin = state.score["axis"]-state.score["allies"]
    ca = sum(s.sunk and s.side == Side.AXIS and s.ship_type == "CA" for s in state.ships.values())
    if ca >= data["allied_decisive_ca"] and margin < 0:
        winner, reason = Side.ALLIES, "盟军决定性胜利：击沉至少3艘日军重巡且分数领先"
    elif margin >= data["decisive_margin"]:
        winner, reason = Side.AXIS, "日军决定性胜利"
    elif margin >= data["tactical_margin"]:
        winner, reason = Side.AXIS, "日军战术胜利"
    else:
        winner, reason = Side.ALLIES, "盟军战术胜利：分差不足16"
    state.phase, state.winner, state.victory_reason = Phase.COMPLETE, winner, reason
    engine._event(state, "victory", reason, payload={"margin": margin}, rule=engine._scenario_rule("IBS-S-10-R15", 10, "胜利条件"))
