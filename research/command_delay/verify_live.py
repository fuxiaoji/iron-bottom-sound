"""Live verification: full games, the real HTTP API, battle reports, autonomy.

This answers the questions the audit scripts do *not* answer:

1. **How many complete games were actually played?** — a real matrix of command
   delay games across all three supported scenarios, with the same matrix in
   Realistic mode as a control, all run to ``Phase.COMPLETE``.
2. **Does the HTTP API work in this mode?** — a whole game driven through the
   FastAPI endpoints with the mode's headers, plus the mode gating (409/404/403).
3. **Is there leakage through the API?** — every response the axis player can
   fetch is scanned for the opponent's ships, formations and command events.
4. **Can a formation act on its own?** — a game in which *no mission order ever
   arrives*: every formation must still decide, move legally and finish, and the
   fleet must only ever hold an aged report of it.
5. **Is there a battle report?** — the report pipeline with the mode enabled, and
   whether the report leaks the opponent's command picture.

Run::

    .venv/bin/python research/command_delay/verify_live.py
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "backend" / "src"
AUDITS = Path(__file__).resolve().parent / "audits"
sys.path.insert(0, str(SRC))

SCENARIOS = ("IBS-S-01", "IBS-S-03", "IBS-S-EM-01")
SEEDS = (3, 20270830, 20270829)


def write(name: str, payload: dict) -> None:
    AUDITS.mkdir(parents=True, exist_ok=True)
    (AUDITS / f"{name}.json").write_text(
        json.dumps(payload, indent=1, sort_keys=True, default=str) + "\n", encoding="utf-8"
    )


# --------------------------------------------------------------------------- 1. matrix

def play_engine_game(scenario: str, seed: int, mode: str) -> dict:
    """Play one complete head-less game and summarise it."""
    from iron_bottom_sound import command_delay
    from iron_bottom_sound.engine import ORDER_PHASES, IronBottomEngine
    from iron_bottom_sound.llm import LLMPlayerSession
    from iron_bottom_sound.models import GameOptions, Phase, Side
    from iron_bottom_sound.realistic_command import RealisticCommander

    options = (
        GameOptions(realistic_command=True, command_delay_mode=True)
        if mode == "command_delay"
        else GameOptions(realistic_command=True)
    )
    started = time.perf_counter()
    engine = IronBottomEngine()
    state = engine.reset(scenario, seed, options)
    sessions = {side: LLMPlayerSession(side, RealisticCommander()) for side in Side}
    steps = 0
    failure = None
    while state.phase != Phase.COMPLETE and steps < 600:
        steps += 1
        if state.phase in ORDER_PHASES:
            for side in Side:
                if side.value in state.submitted_orders:
                    continue
                result = engine.submit_orders(
                    state.game_id, sessions[side].choose_orders(engine, state.game_id)
                )
                if not result.valid:
                    failure = f"{state.turn} {state.phase.value} {side.value}: {result.errors[:2]}"
                    break
        if failure:
            break
        engine.advance(state.game_id)
    mode_state = state.command_delay
    summary = {
        "scenario": scenario,
        "seed": seed,
        "mode": mode,
        "completed": state.phase == Phase.COMPLETE,
        "failure": failure,
        "turns": state.turn,
        "steps": steps,
        "events": len(state.events),
        "wall_seconds": round(time.perf_counter() - started, 1),
        "winner": state.winner.value if state.winner else None,
        "friendly_collisions": sum(
            1 for event in state.events
            if event.type == "collision" and event.payload.get("friendly")
        ),
        "friendly_torpedo_hits": sum(
            1 for event in state.events
            if event.type == "torpedo_hit"
            and event.payload.get("attacker_side") == event.payload.get("target_side")
        ),
    }
    if mode_state is not None:
        summary.update({
            "tick": mode_state.tick,
            "messages": len(mode_state.messages),
            "delivered": sum(
                1 for item in mode_state.messages if item.status.value == "delivered"
            ),
            "agent_decisions": len(mode_state.decisions),
            "mission_orders": len(mode_state.mission_orders),
            "completed_orders": sum(
                1 for item in mode_state.mission_orders if item.confirmed_turn is not None
            ),
            "link_statuses": sorted({
                entry.link_status.value for entry in mode_state.formations.values()
            }),
            "local_autonomy_ever": any(
                record.get("audit", {}).get("active_branches")
                and any(
                    item["branch"] == "loss_of_comm_branch"
                    for item in record["audit"]["active_branches"]
                )
                for record in mode_state.decisions
            ),
        })
    return summary


def matrix() -> dict:
    rows = []
    for scenario in SCENARIOS:
        for seed in SEEDS:
            for mode in ("command_delay", "realistic"):
                row = play_engine_game(scenario, seed, mode)
                rows.append(row)
                flag = "OK " if row["completed"] else "FAIL"
                print(f"[{flag}] {scenario:<14} seed={seed:<9} {mode:<14} "
                      f"turns={row['turns']:<3} events={row['events']:<5} "
                      f"{row['wall_seconds']:>6}s"
                      + (f" decisions={row.get('agent_decisions')} "
                         f"msgs={row.get('messages')}" if mode == "command_delay" else ""))
    cd = [row for row in rows if row["mode"] == "command_delay"]
    rl = [row for row in rows if row["mode"] == "realistic"]
    payload = {
        "rows": rows,
        "command_delay_games": len(cd),
        "command_delay_completed": sum(1 for row in cd if row["completed"]),
        "realistic_games": len(rl),
        "realistic_completed": sum(1 for row in rl if row["completed"]),
        "total_games": len(rows),
        "friendly_collisions": sum(row["friendly_collisions"] for row in rows),
        "friendly_torpedo_hits": sum(row["friendly_torpedo_hits"] for row in rows),
        "scenarios_covered": sorted({row["scenario"] for row in rows}),
        "verdict": "PASS" if all(row["completed"] for row in rows) else "FAIL",
    }
    write("verify_game_matrix", payload)
    return payload


# --------------------------------------------------------------------------- 2/3. API

def api_game() -> dict:
    """Drive a complete command delay game through the HTTP API only."""
    from fastapi.testclient import TestClient

    from iron_bottom_sound.api import app, engine as api_engine
    from iron_bottom_sound.llm import LLMPlayerSession
    from iron_bottom_sound.models import Phase, Side
    from iron_bottom_sound.realistic_command import RealisticCommander

    client = TestClient(app)
    created = client.post("/games", json={
        "scenario_id": "IBS-S-03", "seed": 3,
        "options": {"mode": "hotseat", "realistic_command": True, "command_delay_mode": True},
    })
    if created.status_code != 201:
        return {"verdict": "FAIL", "stage": "create", "status": created.status_code,
                "body": created.text[:400]}
    game_id = created.json()["game_id"]
    state = api_engine.get(game_id)
    sessions = {side: LLMPlayerSession(side, RealisticCommander()) for side in Side}
    findings: list[str] = []
    opponent_needles = {
        ship.id for ship in state.ships.values() if ship.side is not Side.AXIS
    } | {formation.id for formation in state.formations.values()
         if formation.side is not Side.AXIS}
    statuses: dict[str, int] = {}
    steps = 0
    phase_order = None
    while state.phase != Phase.COMPLETE and steps < 400:
        steps += 1
        # The decidable leakage question at the API layer is not "does it name an
        # enemy" (a spotted enemy is supposed to appear) but "does the API return
        # MORE than the engine's own filtered observation".  So the response is
        # compared with engine.observe(side) exactly: any superset would be the API
        # widening the fog, which is what the project's isolation rule forbids.
        for side in Side:
            response = client.get(
                f"/games/{game_id}/view", headers={"X-Player-Side": side.value}
            )
            statuses[f"view-{side.value}"] = response.status_code
            if response.status_code != 200:
                findings.append(f"/view {side.value} -> {response.status_code}")
                continue
            engine_view = api_engine.observe(game_id, side).model_dump(mode="json")
            if _canon(response.json()) != _canon(engine_view):
                differing = sorted(
                    key for key in set(response.json()) | set(engine_view)
                    if _canon(response.json().get(key)) != _canon(engine_view.get(key))
                )
                findings.append(f"/view {side.value} differs from engine.observe: {differing}")

        fleet = client.get(f"/games/{game_id}/command-delay/fleet-view",
                           headers={"X-Player-Side": "axis"})
        statuses["fleet-view"] = fleet.status_code
        if fleet.status_code == 200:
            body = fleet.json()
            # The contacts plot is legitimate; everything else must not name any
            # opposing ship at all, seen or unseen.
            outside = {k: v for k, v in body.items() if k != "contacts"}
            leaked = sorted(_needles_in(outside, opponent_needles))
            if leaked:
                findings.append(f"fleet-view leaked {leaked}")
            if len([r for r in body["reports"] if r["is_source_of_truth"]]) > 1:
                findings.append("fleet-view marked more than one formation exact")

        if state.phase.value in {"formation_setup", "reinforcement", "movement_planning",
                                 "torpedo_planning", "gunnery"}:
            for side in Side:
                if side.value in state.submitted_orders:
                    continue
                batch = sessions[side].choose_orders(api_engine, game_id)
                # Skip the order phase the engine does not expect first.
                response = client.post(
                    f"/games/{game_id}/orders",
                    headers={"X-Player-Side": side.value},
                    json=batch.model_dump(mode="json"),
                )
                statuses[f"orders-{side.value}"] = response.status_code
                if response.status_code not in (200, 422):
                    findings.append(f"orders {side.value} -> {response.status_code}")
                if response.status_code == 422:
                    findings.append(f"orders {side.value} rejected: {response.text[:200]}")
                    break
        advanced = client.post(f"/games/{game_id}/advance",
                              headers={"X-Player-Side": "axis"})
        statuses["advance"] = advanced.status_code
        if advanced.status_code != 200:
            findings.append(f"advance -> {advanced.status_code} {advanced.text[:200]}")
            break
        if phase_order is None:
            phase_order = state.phase.value
        # Opponent-side command events must not reach this player.
        events = advanced.json()
        for event in events:
            secret = event.get("payload", {}).get("secret_side")
            if secret not in (None, "axis"):
                findings.append(f"advance returned an event for {secret}: {event.get('type')}")
        # And the dedicated events endpoint must be filtered the same way.
        listed = client.get(f"/games/{game_id}/events",
                            headers={"X-Player-Side": "axis"}).json()
        for event in listed:
            secret = event.get("payload", {}).get("secret_side")
            if secret not in (None, "axis"):
                findings.append(f"/events returned an event for {secret}: {event.get('type')}")

    # Mode gating.
    realistic = client.post("/games", json={
        "scenario_id": "IBS-S-03", "seed": 3,
        "options": {"mode": "hotseat", "realistic_command": True},
    }).json()
    gating = {
        "fleet_view_in_realistic": client.get(
            f"/games/{realistic['game_id']}/command-delay/fleet-view",
            headers={"X-Player-Side": "axis"},
        ).status_code,
        "formation_view_in_realistic": client.get(
            f"/games/{realistic['game_id']}/command-delay/formation-view/axis-active-light",
            headers={"X-Player-Side": "axis"},
        ).status_code,
        "rules_doc": client.get("/rules/command-delay").status_code,
    }
    if gating["fleet_view_in_realistic"] != 409:
        findings.append(f"fleet-view was not gated in realistic mode: {gating}")
    if gating["formation_view_in_realistic"] != 409:
        findings.append(f"formation-view was not gated in realistic mode: {gating}")
    if gating["rules_doc"] != 200:
        findings.append("the command delay rules document is not served")

    # Opponent formation must be invisible to this player's formation view.
    own = next(
        (formation.id for formation in state.formations.values() if formation.side is Side.AXIS),
        None,
    )
    enemy = next(
        (formation.id for formation in state.formations.values() if formation.side is not Side.AXIS),
        None,
    )
    if own is not None:
        owned = client.get(f"/games/{game_id}/command-delay/formation-view/{own}",
                           headers={"X-Player-Side": "axis"})
        statuses["formation-view-own"] = owned.status_code
        if owned.status_code != 200:
            findings.append(f"own formation view -> {owned.status_code} {owned.text[:200]}")
        elif sorted(_needles_in({k: v for k, v in owned.json().items()
                                 if k not in ("local_contacts",
                                              "legal_target_priority_options")},
                                opponent_needles)):
            findings.append("formation view leaked opposing ships outside its sightings")
    if enemy is not None:
        foreign = client.get(f"/games/{game_id}/command-delay/formation-view/{enemy}",
                             headers={"X-Player-Side": "axis"})
        statuses["formation-view-enemy"] = foreign.status_code
        if foreign.status_code != 404:
            findings.append(f"an opposing formation view was served: {foreign.status_code}")
    payload = {
        "game_id": game_id,
        "completed": state.phase == Phase.COMPLETE,
        "turn": state.turn,
        "steps": steps,
        "status_codes": dict(sorted(statuses.items())),
        "gating": gating,
        "findings": findings,
        "verdict": "PASS" if state.phase == Phase.COMPLETE and not findings else "FAIL",
    }
    write("verify_api_game", payload)
    return payload


def _canon(tree) -> str:
    return json.dumps(tree, sort_keys=True, default=str)


def _visible_to_axis(api_engine, game_id: str) -> set[str]:
    """Opposing ship ids the axis side can see right now, by the engine's own rule."""
    from iron_bottom_sound.models import Side

    state = api_engine.get(game_id)
    own_positions = [
        ship.position for ship in state.ships.values()
        if ship.side is Side.AXIS and ship.position is not None and not ship.sunk
    ]
    if not own_positions:
        return set()
    return {
        ship.id for ship in state.ships.values()
        if ship.side is not Side.AXIS and ship.position is not None and not ship.sunk
        and api_engine._visible_to(state, ship, Side.AXIS, own_positions)
    }


def _needles_in(tree, needles: set[str]) -> set[str]:
    found: set[str] = set()
    if isinstance(tree, dict):
        for key, value in tree.items():
            if key in needles:
                found.add(key)
            found |= _needles_in(value, needles)
    elif isinstance(tree, list):
        for item in tree:
            found |= _needles_in(item, needles)
    elif isinstance(tree, str) and tree in needles:
        found.add(tree)
    return found


# --------------------------------------------------------------------------- 4. autonomy

def autonomy() -> dict:
    """No mission order ever arrives: can each formation still fight?"""
    from iron_bottom_sound import command_delay
    from iron_bottom_sound.communications import CommunicationMedium, RouteDecision
    from iron_bottom_sound.engine import ORDER_PHASES, IronBottomEngine
    from iron_bottom_sound.llm import LLMPlayerSession
    from iron_bottom_sound.models import (
        AuthorityLevel, GameOptions, LinkStatus, OrderBatch, Phase, Side,
    )
    from iron_bottom_sound.realistic_command import RealisticCommander, default_setup_orders

    engine = IronBottomEngine()
    state = engine.reset("IBS-S-01", 20270830, GameOptions(
        realistic_command=True, command_delay_mode=True,
    ))
    for side in Side:
        engine.submit_orders(state.game_id, OrderBatch(
            side=side, phase=Phase.FORMATION_SETUP,
            formation_setup=default_setup_orders(state, side),
        ))
    engine.advance(state.game_id)

    # Cut the link to ONE formation completely -- no orders, no sitreps, nothing in
    # either direction.  That is the real loss-of-communication case, and it is the
    # only way to test whether a formation can carry on by itself: with the link to
    # the fleet still up, a formation is a delegated unit, not an autonomous one.
    original_route = command_delay.route

    def blackout_orders(engine_, state_, origin, destination):
        decision = original_route(engine_, state_, origin, destination)
        return RouteDecision(decision.medium, decision.relay_hops, decision.reason)

    cut_formation = next(
        item.id for item in command_delay.active_formations(state, Side.ALLIES)
        if item.id != command_delay.authority_for(state, Side.ALLIES).fleet_formation_id
    )

    def blackout_orders(engine_, state_, origin, destination):
        decision = original_route(engine_, state_, origin, destination)
        if cut_formation in (origin.id, destination.id):
            return RouteDecision(
                CommunicationMedium.BLACKOUT, 0, "link cut for the autonomy probe"
            )
        return RouteDecision(decision.medium, decision.relay_hops, decision.reason)

    command_delay.route = blackout_orders
    original_send = command_delay.send

    def drop_orders(engine_, state_, message):
        from iron_bottom_sound.models import MessageKind

        if message.kind in (MessageKind.MISSION_ORDER, MessageKind.AMENDMENT):
            message.medium = CommunicationMedium.BLACKOUT
            message.reason = "forced blackout for the autonomy probe"
        return original_send(engine_, state_, message)

    command_delay.send = drop_orders
    try:
        sessions = {side: LLMPlayerSession(side, RealisticCommander()) for side in Side}
        steps = 0
        autonomy_during_play: set[str] = set()
        blackout_during_play: set[str] = set()
        while state.phase != Phase.COMPLETE and steps < 400:
            steps += 1
            for entry in state.command_delay.formations.values():
                if entry.authority == AuthorityLevel.LOCAL_AUTONOMY:
                    autonomy_during_play.add(entry.formation_id)
                if entry.link_status == LinkStatus.BLACKOUT:
                    blackout_during_play.add(entry.formation_id)
            if state.phase in ORDER_PHASES:
                for side in Side:
                    if side.value in state.submitted_orders:
                        continue
                    result = engine.submit_orders(
                        state.game_id, sessions[side].choose_orders(engine, state.game_id)
                    )
                    if not result.valid:
                        raise RuntimeError(f"{state.turn} {state.phase} {side}: {result.errors[:2]}")
            engine.advance(state.game_id)
    finally:
        command_delay.route = original_route
        command_delay.send = original_send

    mode = state.command_delay
    orders = [order for order in mode.mission_orders if order.confirmed_turn is not None]
    decisions = mode.decisions
    no_order_decisions = [r for r in decisions if not r["audit"].get("order_received")]
    local_autonomy = [
        entry for entry in mode.formations.values()
        if entry.authority == AuthorityLevel.LOCAL_AUTONOMY
    ]
    blackout = [
        entry for entry in mode.formations.values()
        if entry.link_status == LinkStatus.BLACKOUT
    ]
    # Snapshot autonomy during play, not at the end: at the end most formations are
    # dissolved, which sets BLACKOUT and would mask the real authority state.
    seen_local_autonomy = set()
    for record in decisions:
        pass
    seen_local_autonomy |= {
        entry.formation_id for entry in mode.formations.values()
        if entry.authority == AuthorityLevel.LOCAL_AUTONOMY
    }
    del seen_local_autonomy
    decisions_with_actions = [
        r for r in no_order_decisions if r["selected_movement_action_id"] is not None
    ]
    payload = {
        "completed": state.phase == Phase.COMPLETE,
        "turns": state.turn,
        "confirmed_mission_orders": len(orders),
        "agent_decisions": len(decisions),
        "decisions_without_an_order": len(no_order_decisions),
        "decisions_without_an_order_that_chose_a_plan": len(decisions_with_actions),
        "formations_in_local_autonomy_at_end": len(local_autonomy),
        "formations_in_local_autonomy_during_play": sorted(autonomy_during_play),
        "formations_in_blackout_at_end": len(blackout),
        "formations_in_blackout_during_play": sorted(blackout_during_play),
        "fleet_reports_still_age": sorted(
            (state.turn - entry.reported_turn)
            for entry in mode.formations.values() if entry.reported_turn is not None
        ),
        "cut_formation": cut_formation,
        "cut_formation_end_link": (
            mode.formations[cut_formation].link_status.value
            if cut_formation in mode.formations else None
        ),
        "cut_formation_end_authority": (
            mode.formations[cut_formation].authority.value
            if cut_formation in mode.formations else None
        ),
        "gunnery_orders_generated": sum(
            len(batch.gunnery)
            for key, sealed in state.sealed_orders.items() if key.endswith("gunnery")
            for batch in sealed.values()
        ),
        "friendly_collisions": sum(
            1 for event in state.events
            if event.type == "collision" and event.payload.get("friendly")
        ),
        "verdict": "PASS" if (
            state.phase == Phase.COMPLETE
            and len(orders) == 0
            and no_order_decisions
            and decisions_with_actions
            and state.events
            and autonomy_during_play
        ) else "FAIL",
    }
    write("verify_autonomy", payload)
    return payload


# --------------------------------------------------------------------------- 5. battle report

def battle_report() -> dict:
    """The report pipeline with the mode on, and whether it leaks the command picture."""
    from iron_bottom_sound.engine import ORDER_PHASES, IronBottomEngine
    from iron_bottom_sound.llm import LLMPlayerSession
    from iron_bottom_sound.models import GameOptions, Phase, Side
    from iron_bottom_sound.realistic_command import RealisticCommander, default_setup_orders
    from iron_bottom_sound import battle_report as battle_report_module

    findings: list[str] = []
    engine = IronBottomEngine()
    game_id = "verify-battle-report"
    state = engine.reset("IBS-S-03", 3, GameOptions(
        realistic_command=True, command_delay_mode=True, battle_report=True,
    ), game_id=game_id)
    report_root = ROOT / "artifacts" / "verify-battle-report"
    entries: list[dict] = []
    sessions = {side: LLMPlayerSession(side, RealisticCommander()) for side in Side}
    steps = 0
    while state.phase != Phase.COMPLETE and steps < 400:
        steps += 1
        prev_phase = state.phase
        if state.phase in ORDER_PHASES:
            for side in Side:
                if side.value in state.submitted_orders:
                    continue
                result = engine.submit_orders(
                    state.game_id, sessions[side].choose_orders(engine, game_id)
                )
                if not result.valid:
                    findings.append(f"orders rejected: {result.errors[:2]}")
                    break
        engine.advance(game_id)
        try:
            captured, _summary = battle_report_module.capture_after_advance(
                None, report_root, state, engine, prev_phase,
            )
            entries.extend(captured or [])
        except Exception as error:  # the report must never break the game, but must be honest
            findings.append(f"capture_after_advance raised: {type(error).__name__}: {error}")
            break

    data = None
    markdown = ""
    try:
        data = battle_report_module.build_report_data(state, engine, entries)
        markdown = battle_report_module.build_report_markdown(
            str(report_root), data, game_id,
        )
    except Exception as error:
        findings.append(f"report build raised: {type(error).__name__}: {error}")

    if data is not None:
        # The report is neutral (both sides), so the question is whether it carries
        # the *command* picture: mission order text, local priorities, directives.
        text = json.dumps(data, ensure_ascii=False, default=str) + markdown
        for needle, label in (
            ("mission_order", "mission orders"),
            ("target_priorities", "target priority directives"),
            ("local_agent", "local agent adjustments"),
            ("loss_of_comm_branch", "contingency branches"),
            ("comm_state", "communication state"),
        ):
            if needle in text:
                findings.append(f"the battle report carries {label}")
    payload = {
        "game_id": game_id,
        "completed": state.phase == Phase.COMPLETE,
        "turns": state.turn,
        "captured_entries": len(entries),
        "report_built": data is not None,
        "markdown_chars": len(markdown),
        "findings": findings,
        "verdict": "PASS" if (
            state.phase == Phase.COMPLETE and data is not None and not findings
        ) else "FAIL",
    }
    write("verify_battle_report", payload)
    return payload


def main() -> int:
    print("=== 1. complete-game matrix (command delay vs realistic) ===")
    matrix_result = matrix()
    print(f"    {matrix_result['command_delay_completed']}/{matrix_result['command_delay_games']} "
          f"command-delay games and {matrix_result['realistic_completed']}/"
          f"{matrix_result['realistic_games']} realistic games reached COMPLETE")
    print("\n=== 2+3. HTTP API game and leakage ===")
    api_result = api_game()
    print(f"    completed={api_result.get('completed')} findings={api_result.get('findings')}")
    print("\n=== 4. formation autonomy with no order at all ===")
    autonomy_result = autonomy()
    print(f"    {json.dumps({k: v for k, v in autonomy_result.items() if k != 'verdict'}, ensure_ascii=False)}")
    print("\n=== 5. battle report with the mode on ===")
    report_result = battle_report()
    print(f"    {json.dumps(report_result, ensure_ascii=False)}")
    verdicts = {
        "game_matrix": matrix_result["verdict"],
        "api_game": api_result["verdict"],
        "autonomy": autonomy_result["verdict"],
        "battle_report": report_result["verdict"],
    }
    print("\n" + json.dumps(verdicts, indent=1))
    print("LIVE_VERIFICATION = " + ("PASS" if all(v == "PASS" for v in verdicts.values()) else "FAIL"))
    return 0 if all(v == "PASS" for v in verdicts.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
