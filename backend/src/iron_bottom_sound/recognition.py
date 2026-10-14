"""Engine-owned discovery/identification extension, frozen per new game.

World ids never become public contact ids. The private planner scope preserves
canonical command ids inside trusted deterministic code, while observation still
removes unknown identity/capabilities. Model prompts never enter that scope.
"""
from contextvars import ContextVar
from functools import wraps
from copy import deepcopy
import hashlib
import re
from inspect import signature
from uuid import uuid4

from .models import Side, OrderBatch, RuleReference

_planner = ContextVar("ibs_private_recognition_planner", default=None)
_replay = ContextVar("ibs_recognition_replay", default=False)


def enabled(state):
    return (state.options.ruleset_version == "night-v2" and state.options.night_recognition
            and state.scenario_id in state.rule_snapshot.get("night", {}).get("night_scenarios", [])
            and "recognition" in state.rule_snapshot.get("night", {}))


def data(state):
    return state.rule_snapshot["night"]["recognition"]


def initialize(state):
    if enabled(state):
        state.scenario_state["recognition_secret"] = uuid4().hex


def validate_snapshot(state):
    if enabled(state) and not re.fullmatch(r"[0-9a-f]{32}", str(state.scenario_state.get("recognition_secret", ""))):
        raise ValueError("存档缺少识别接触所需的信息，无法保证接触编号一致；请使用完整存档")


def private(side):
    return _planner.get() == side


def contact_id(state, side, ship_id):
    if state.ships[ship_id].side == side:
        return ship_id
    secret = state.scenario_state["recognition_secret"]
    return "contact-" + hashlib.sha256(f"{secret}:{side.value}:{ship_id}".encode()).hexdigest()[:14]


def label(state, side, ship_id):
    return "未识别接触 " + contact_id(state, side, ship_id)[-4:].upper()


def fleet_observers(state, side):
    own = [s for s in state.ships.values() if s.side == side and s.position and not s.sunk]
    if state.options.command_delay_mode:
        mode = state.command_delay
        authority = mode.authorities.get(side.value) if mode else None
        formation = state.formations.get(authority.fleet_formation_id) if authority else None
        own = [s for s in own if formation and s.id in formation.ship_ids and s.command_status == 'attached']
    return own


def identified(engine, state, side, ship, observers=None):
    if not enabled(state) or ship.side == side:
        return True
    if ship.sunk and any(e.type == 'ship_sunk' and ship.id in e.payload.get('identified_ship_ids', {}).get(side.value, []) for e in state.events):
        return True
    if not ship.position:
        return False
    from . import night
    observers = observers if observers is not None else fleet_observers(state, side)
    now = any(night.optical(engine, state, s.position, ship.position) and (
        s.position.distance(ship.position) <= min(data(state)["unlit_hexes"], state.visibility[side.value])
        or night.illuminated(state, ship)) for s in observers)
    if now or state.options.command_delay_mode:
        return now
    # Keep a tracked identity after the light goes out; losing contact breaks
    # the association. Historical reports remain in memory, never live truth.
    for event in reversed(state.events):
        if event.type == "night_contact_changed" and event.payload.get("secret_side") == side.value and event.payload.get("ship_id") == ship.id:
            return (event.payload["status"] == "identified" and
                    engine._visible_to(state, ship, side, [s.position for s in observers]))
    return False


def class_asset(state, ship):
    nation = next((n for n in data(state)["class_counters"] if ship.id.startswith(f"IBS-U-{n}-")), None)
    return data(state)["class_counters"].get(nation, {}).get(ship.ship_type, ship.asset)


def project_value(engine, state, side, value, known=None, aliases=True):
    """Identifiers/names in all public structures, including nested audit ids.

`known` may be the event-time identification set. Never reveal an old event's
unknown identity just because the ship has been identified later.
"""
    if not enabled(state):
        return deepcopy(value)
    unknown = {s.id for s in state.ships.values() if s.side != side and (
        s.id not in known if known is not None else not identified(engine, state, side, s))}
    replacements = [(s.id, contact_id(state, side, s.id)) for s in state.ships.values() if s.side != side] if aliases else []
    replacements.sort(key=lambda pair: len(pair[0]), reverse=True)
    def visit(v):
        if isinstance(v, str):
            for old, new in replacements:
                v = v.replace(old, new)
            for sid in sorted(unknown):
                name = state.ships[sid].name
                replacement = label(state, side, sid)
                # The destroyer 电 must not turn 电台 into a contact label.
                if v == name:
                    v = replacement
                elif len(name) > 1:
                    v = v.replace(name, replacement)
                else:
                    v = re.sub(r"(?<!\w)" + re.escape(name) + r"(?!\w)", replacement, v)
            return v
        if isinstance(v, list):
            return [visit(x) for x in v]
        if isinstance(v, tuple):
            return tuple(visit(x) for x in v)
        if isinstance(v, dict):
            return {visit(k): visit(x) for k, x in v.items() if k not in (
                "recognition_secret", "identified_ship_ids", "known_ship_ids", "initial_state", "upgrade_state")}
        return v
    return visit(value)


def decode_target(engine, state, side, target, allow_internal=False, observers=None, require_visible=True):
    if not target or not enabled(state):
        return target
    if target in state.ships and (state.ships[target].side == side or allow_internal or private(side) or _replay.get()):
        return target
    own_positions = [s.position for s in (observers if observers is not None else fleet_observers(state, side))]
    for ship in state.ships.values():
        if ship.side != side and contact_id(state, side, ship.id) == target and (
            not require_visible or engine._visible_to(state, ship, side, own_positions)):
            return ship.id
    raise ValueError("目标接触代号无效或当前尚未发现；不能用真实舰船编号指定隐藏目标")


def decode_orders(engine, state, batch, allow_internal=False):
    if not enabled(state):
        return batch
    result = batch.model_copy(deep=True)
    for gun in result.gunnery:
        for key in ("primary_target", "secondary_target", "searchlight_target"):
            setattr(gun, key, decode_target(engine, state, batch.side, getattr(gun, key), allow_internal))
        for mount in gun.mounts:
            mount.target_id = decode_target(engine, state, batch.side, mount.target_id, allow_internal)
    for order in [*result.searchlights, *result.torpedoes]:
        order.target_id = decode_target(engine, state, batch.side, order.target_id, allow_internal)
    for directive in result.target_priorities:
        observers = None
        if state.options.command_delay_mode:
            formation = state.formations.get(directive.formation_id)
            observers = [state.ships[sid] for sid in formation.ship_ids if state.ships[sid].position and not state.ships[sid].sunk] if formation and formation.side == batch.side else []
        # A remembered priority is not a firing order. The selector intersects
        # it with CURRENT legal shots, so losing contact needn't reject a plan.
        directive.target_id = decode_target(engine, state, batch.side, directive.target_id, allow_internal, observers, require_visible=False)
    return result


def public_result(func):
    """Project engine helpers at their public boundary, also for model tools."""
    sig = signature(func)
    @wraps(func)
    def run(self, *args, **kwargs):
        bound = sig.bind(self, *args, **kwargs)
        params = bound.arguments
        state = params.get("state") or self.get(params["game_id"])
        side = params.get("side", params.get("viewer"))
        if not enabled(state):
            return func(*bound.args, **bound.kwargs)
        for key in ("target_id", "ship_id"):
            if params.get(key):
                params[key] = decode_target(self, state, side, params[key])
        if params.get("assigned"):
            params["assigned"] = [dict(row, target_id=decode_target(self, state, side, row.get("target_id"))) for row in params["assigned"]]
        result = func(*bound.args, **bound.kwargs)
        def project(item):
            raw = item.model_dump(mode="json") if hasattr(item, "model_dump") else item
            raw = project_value(self, state, side, raw, aliases=not private(side))
            return type(item).model_validate(raw) if hasattr(item, "model_dump") else raw
        return [project(item) for item in result] if isinstance(result, list) else project(result)
    return run


def replaying(func):
    @wraps(func)
    def run(*args, **kwargs):
        token = _replay.set(True)
        try:
            return func(*args, **kwargs)
        finally:
            _replay.reset(token)
    return run


def local_projection(func):
    """Command Delay views use only the embarked/local lookouts."""
    @wraps(func)
    def run(engine, state, side, *args, **kwargs):
        view = func(engine, state, side, *args, **kwargs)
        if not enabled(state):
            return view
        raw = view.model_dump(mode="json")
        members = raw.get("embarked", {}).get("ship_ids") or [s["ship_id"] for s in raw.get("formation_state", {}).get("ships", [])]
        observers = [state.ships[sid] for sid in members if state.ships[sid].position and not state.ships[sid].sunk]
        known = {s.id for s in state.ships.values() if s.side == side or identified(engine, state, side, s, observers)}
        for row in raw.get("contacts", raw.get("local_contacts", [])):
            row["identified"] = row["ship_id"] in known
            if not row["identified"]:
                row["name"], row["ship_type"] = label(state, side, row["ship_id"]), "UNKNOWN"
        for row in raw.get("legal_target_priority_options", []):
            if row["target_id"] not in known:
                row["target_class"] = "UNKNOWN"
        return type(view).model_validate(project_value(engine, state, side, raw, known=known, aliases=not private(side)))
    return run


def project_event(engine, state, event, side):
    result = event.model_copy(deep=True)
    known = set(event.payload.get("identified_ship_ids", {}).get(side.value, []))
    # Source-free global receipts carry no identities; recursive projection
    # still strips their authoritative initial snapshot from player logs.
    result.payload = project_value(engine, state, side, result.payload, known=known, aliases=not private(side))
    result.message = project_value(engine, state, side, result.message, known=known, aliases=not private(side))
    unknown = {s.id for s in state.ships.values() if s.side != side and s.id not in known}
    attacker = event.payload.get("attacker") or event.payload.get("launcher_ship_id")
    target = event.payload.get("target") or event.payload.get("ship_id")
    if attacker in unknown:
        for key in ("mount_id", "launcher_id", "caliber", "firepower", "torpedo_type", "modifier", "modifier_breakdown"):
            result.payload.pop(key, None)
        # Detailed attack text can include caliber, mount groups and ship type.
        if event.type in ("gun_mount_attack", "gunnery_result", "torpedo_attack", "torpedo_result"):
            result.message = f"{label(state, side, attacker)}：观察到攻击"
    if target in unknown:
        for key in ("ship_type", "displacement_band", "vp", "armor", "hull", "hull_lost", "damage", "modifier", "modifier_breakdown"):
            result.payload.pop(key, None)
        if event.type in ("gun_mount_attack", "gunnery_result", "special_damage", "ship_sunk"):
            result.message = f"{label(state, side, target)}：{'观察到沉没' if event.type == 'ship_sunk' else '观察到交战'}"
    if (attacker in unknown or target in unknown) and event.type in ("gun_mount_attack", "gunnery_result", "torpedo_attack", "torpedo_result", "special_damage", "ship_sunk"):
        result.payload = {k:v for k,v in result.payload.items() if k in ("ship_id", "attacker", "target", "target_id", "position", "status", "observed_by", "secret_side", "track_id")}
        result.dice = None
    return result


def project_observation(engine, state, view, debug=False):
    if not enabled(state) or debug:
        return view
    aliases = not private(view.side)
    from . import night
    observers = [state.ships[s.id] for s in view.ships if s.side == view.side and s.position and not s.sunk]
    for public in view.ships:
        actual = state.ships[public.id]
        public.identified = identified(engine, state, view.side, actual, observers)
        if public.identified:
            public.asset = class_asset(state, actual)
        else:
            public.name, public.ship_type = label(state, view.side, actual.id), "UNKNOWN"
            public.asset = data(state)["optical_counter"] if any(night.optical_ship(engine, state, s, actual) for s in observers) else data(state)["radar_counter"]
            public.hull = public.max_hull = None
            public.vp = 0
            public.primary_armor = public.secondary_armor = public.belt_armor = public.bridge_armor = None
            public.gun_mounts, public.torpedo_launchers = [], []
            public.combat_history = []
    value = project_value(engine, state, view.side, view.model_dump(mode="json"), aliases=aliases)
    # Unknown displacement/type cannot enter the loss histogram.
    foe = value.get("battle_losses", {}).get(view.side.opponent.value)
    if foe:
        known_ids = {s.id for s in state.ships.values() if s.side != view.side and identified(engine, state, view.side, s, observers)}
        foe["sunk"] = [s for s in foe["sunk"] if s["id"] in {contact_id(state, view.side, sid) if aliases else sid for sid in known_ids}]
        foe["damaged"] = [s for s in foe["damaged"] if s["id"] in {contact_id(state, view.side, sid) if aliases else sid for sid in known_ids}]
        foe["by_type"] = {t:sum(s["ship_type"] == t for s in foe["sunk"]) for t in {s["ship_type"] for s in foe["sunk"]}}
        foe["by_displacement"] = {b:sum(s["displacement_band"] == b for s in foe["sunk"]) for b in "ABCDEFGHI"}
    env = value.setdefault("environment", {})
    env.update(recognition_enabled=True, identification_hexes=data(state)["unlit_hexes"], light_counter=data(state)["light_counter"])
    env.setdefault("effect_notes", {})["visibility"] = (f"光学视程 {state.visibility[view.side.value]} 格只表示发现接触；未识别接触统一显示敌舰算子。"
        f"近距 {data(state)['unlit_hexes']} 格内或有效探照灯／照明弹且光学视线畅通时，识别舰名与舰型。"
        "近距阈值为用户授权的可调历史补充参数。雷达全图发现而不自动识别，保留陆地4格排除与遮挡；蓝色虚线圈为仅雷达接触。连续跟踪保留已识别身份，失去接触后重新确认。")
    return type(view).model_validate(value)


def planner(func):
    @wraps(func)
    def run(self, engine, game_id, side, *args, **kwargs):
        state = engine.get(game_id)
        if not enabled(state) or private(side):
            return func(self, engine, game_id, side, *args, **kwargs)
        token = _planner.set(side)
        try:
            plan, batch, audits = func(self, engine, game_id, side, *args, **kwargs)
        finally:
            _planner.reset(token)
        public_batch = OrderBatch.model_validate(project_value(engine, state, side, batch.model_dump(mode="json")))
        public_plan = type(plan).model_validate(project_value(engine, state, side, plan.model_dump(mode="json")))
        public_plan.orders = public_batch.model_dump(mode="json")
        public_audits = [type(audit).model_validate(project_value(engine, state, side, audit.model_dump(mode="json"))) for audit in audits]
        return public_plan, public_batch, public_audits
    return run


def refresh(engine, state):
    """Executed contact changes form their own deterministic replay audit."""
    if not enabled(state):
        return
    previous = {}
    for event in state.events:
        if event.type == "night_contact_changed":
            previous[(event.payload["secret_side"], event.payload["ship_id"])] = event.payload["status"]
    for side in Side:
        positions = [s.position for s in fleet_observers(state, side)]
        for ship in state.ships.values():
            if ship.side == side:
                continue
            visible = engine._visible_to(state, ship, side, positions)
            status = "identified" if visible and identified(engine, state, side, ship) else "detected" if visible else "lost"
            if status == previous.get((side.value, ship.id), "lost"):
                continue
            name = ship.name if status == "identified" else label(state, side, ship.id)
            engine._event(state, "night_contact_changed", f"{name}：{'已识别' if status=='identified' else '发现接触' if status=='detected' else '失去接触'}",
                payload={"secret_side":side.value, "ship_id":ship.id, "status":status},
                rule=RuleReference(rule_id=data(state)["rule_id"], document="docs/rules/night-identification-20261013.md", section="用户授权的历史补充参数"))
