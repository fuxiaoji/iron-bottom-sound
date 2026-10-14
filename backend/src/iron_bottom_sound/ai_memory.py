"""Side-private, same-game factual memory and sanitized decision audit.

Model reasoning is never an input to this module. Facts come from a non-debug
observation and accepted plans, with timestamps so old contacts cannot become
current intelligence. The long journal is stored separately by GameRepository.
"""
from copy import deepcopy
import json
import re

from .models import Side
from .recognition import decode_target


def sanitize(value, secrets=()):
    if isinstance(value, dict):
        return {k: sanitize(v, secrets) for k,v in value.items()
                if not any(x in k.lower() for x in ("api_key", "authorization", "reasoning_content", "reasoning_preview", "access_token"))}
    if isinstance(value, list):
        return [sanitize(v, secrets) for v in value]
    if isinstance(value, str):
        for secret in secrets:
            if secret:
                value = value.replace(secret, "[secret removed]")
        value = re.sub(r"<think>.*?</think>", "[private reasoning removed]", value, flags=re.S|re.I)
        return re.sub(r"(?:sk-[A-Za-z0-9_-]{8,}|Bearer\s+\S+)", "[secret removed]", value)[:20000]
    return value


def memory(state, side):
    return deepcopy(state.ai_memory.get(side.value, {"contacts": {}, "decisions": [], "results": [], "formation_intents": {}, "revision": 0}))


def prompt_memory(state, side):
    data = memory(state, side)
    for contact in data["contacts"].values():
        contact["age_turns"] = max(0, state.turn-contact["seen_turn"])
        contact["is_current"] = False
    for formation in data.get("formations", {}).values():
        for contact in formation.get("contacts", {}).values():
            contact["age_turns"] = max(0, state.turn-contact["seen_turn"])
            contact["is_current"] = False
    # Read only; prospective observations are not committed by a guidance call.
    # Bound entire records, never chop JSON or promote stale coordinates to facts.
    data["contacts"] = dict(sorted(data["contacts"].items(), key=lambda pair: pair[1]["seen_turn"], reverse=True)[:24])
    data["decisions"] = data["decisions"][-4:]
    data["results"] = data["results"][-8:]
    while len(json.dumps(data, ensure_ascii=False)) > 6000 and data["contacts"]:
        data["contacts"].pop(next(reversed(data["contacts"])))
    for field in ("results", "decisions", "formations", "formation_intents", "own_losses"):
        while len(json.dumps(data, ensure_ascii=False)) > 6000 and data.get(field):
            if isinstance(data[field], list):
                data[field].pop(0)
            elif isinstance(data[field], dict):
                data[field].pop(next(iter(data[field])))
    return json.dumps(data, ensure_ascii=False, separators=(",", ":"))


def record_trace(state, side, payload):
    entry = sanitize(deepcopy(payload))
    state.ai_trace_counter += 1
    entry.update(id=state.ai_trace_counter, side=side.value, turn=state.turn, phase=state.phase.value)
    state.ai_traces.append(entry)
    state.ai_traces = state.ai_traces[-32:]
    return entry


def rejected(engine, state, side, payload):
    """Retain failed-call audit for replay without committing gameplay memory."""
    entry = record_trace(state, side, {**payload, "status": "rejected"})
    if state.options.ruleset_version == "night-v2":
        engine._event(state, "ai_decision_rejected", "AI 未接受的决策审计检查点",
                      payload={"secret_side": side.value, "debug_only": True,
                               "trace": deepcopy(entry)})
    return entry


def accepted(engine, state, side, plan, batch, audits=(), detail=None):
    if plan is None:
        from .models import AIPlanSheet
        plan = AIPlanSheet(turn=state.turn, phase=state.phase, situation_summary="已接受阶段命令（无模型摘要）",
                          phase_goal="执行已校验命令", orders=batch.model_dump(mode="json"))
    key = f"{state.turn}:{state.phase.value}"
    previous = memory(state, side)
    if previous.get("last_accepted_key") == key:
        return
    before = deepcopy(previous)
    observation = engine.observe(state.game_id, side)
    for ship in observation.ships:
        if ship.side != side and ship.position and not ship.sunk:
            previous["contacts"][ship.id] = {"name": ship.name, "ship_type": ship.ship_type,
                "position": ship.position.model_dump(), "seen_turn": state.turn, "seen_phase": state.phase.value}
    decision = {"turn": state.turn, "phase": state.phase.value, "summary": plan.situation_summary,
                "goal": plan.phase_goal, "unit_intents": dict(plan.unit_intents)}
    previous["decisions"] = (previous["decisions"]+[decision])[-12:]
    previous["formation_intents"].update(plan.unit_intents)
    if state.options.realistic_command and not state.options.command_delay_mode:
        formations = previous.setdefault("formations", {})
        for fid, formation in state.formations.items():
            if formation.side != side:
                continue
            positions = [state.ships[sid].position for sid in formation.ship_ids if state.ships[sid].position and not state.ships[sid].sunk]
            facts = formations.setdefault(fid, {"contacts": {}, "decisions": []})
            for ship in observation.ships:
                if ship.side != side and ship.position and engine._visible_to(state, state.ships[
                    decode_target(engine, state, side, ship.id)], side, positions):
                    facts["contacts"][ship.id] = deepcopy(previous["contacts"][ship.id])
            facts["decisions"] = (facts["decisions"] + [{"turn":state.turn,"phase":state.phase.value,"task":plan.unit_intents.get(fid, "本队执行已接受的阶段命令")}])[-6:]
    previous["revision"] += 1
    previous["last_accepted_key"] = key
    previous["last_event"] = len(state.events)
    state.ai_memory[side.value] = sanitize(previous)
    entry = record_trace(state, side, {
        "status": "accepted", "summary": plan.situation_summary,
        "model": audits[-1].model if audits else "state-machine",
        "plan": plan.model_dump(mode="json"), "submitted_orders": batch.model_dump(mode="json"),
        "attempts": [sanitize(a.model_dump(mode="json")) for a in audits],
        "memory_before": before,
        "memory_after": deepcopy(state.ai_memory[side.value]), "details": detail or {},
    })
    if state.options.ruleset_version == "night-v2":
        engine._event(state, "ai_decision_accepted", "AI 已接受的决策与阵营记忆检查点",
                      payload={"secret_side":side.value, "debug_only":True,
                               "memory":deepcopy(state.ai_memory[side.value]), "trace":deepcopy(entry)})


def memory_from_detail(detail, state, side):
    return (detail or {}).get("memory_before", {})


def record_results(engine, state):
    for which in Side:
        if which.value not in state.ai_memory:
            continue
        data = state.ai_memory[which.value]
        last = data.get("last_event", 0)
        observation = engine.observe(state.game_id, which)
        events = engine.public_events(state, which, [e for e in state.events if e.sequence > last
                                     and e.type not in ("orders_submitted", "phase_changed")])
        for event in events:
            data["results"].append({"turn": event.turn, "phase": event.phase.value, "sequence": event.sequence,
                                    "type": event.type, "summary": event.message})
        data["results"] = data["results"][-12:]
        data["last_event"] = len(state.events)
        data["own_losses"] = observation.battle_losses.get(which.value, {})
        for entry in reversed(state.ai_traces):
            if entry["side"] == which.value and entry.get("status") == "accepted":
                entry["execution_memory"] = deepcopy(data)
                break


def debug_payload(state, side):
    result = memory(state, side)
    if state.command_delay:
        from .formation_memory import memory_payload
        result["command_delay_formations"] = {fid: memory_payload(m) for fid,m in state.command_delay.memories.items()
            if fid in state.formations and state.formations[fid].side == side}
    return sanitize(result)
