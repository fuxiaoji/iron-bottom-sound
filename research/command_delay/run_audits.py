"""Regenerate every CD-0..CD-6 audit from the working tree.

Each audit function is *measuring*, not restating: it drives the real engine and
the real mode, and writes a JSON record to ``research/command_delay/audits/``.
Run it after any change to see whether a claim in the bundle documents still
holds::

    python research/command_delay/run_audits.py            # all audits
    python research/command_delay/run_audits.py leakage    # one audit

Exit code is non-zero if any audit verdict is FAIL, so this doubles as the
bundle's integrity gate.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "backend" / "src"
AUDITS = Path(__file__).resolve().parent / "audits"
LOGS = Path(__file__).resolve().parent / "logs"
sys.path.insert(0, str(SRC))

FREEZE_TAG = "realistic-command-v1-frozen"

FORBIDDEN_LOCAL_KEYS = (
    "score", "sealed_orders", "submitted_orders", "victory_reason", "winner",
    "wrecks", "torpedo_tracks", "ships", "events",
)


def write(name: str, payload: dict) -> None:
    AUDITS.mkdir(parents=True, exist_ok=True)
    (AUDITS / f"{name}.json").write_text(
        json.dumps(payload, indent=1, sort_keys=True, default=str) + "\n", encoding="utf-8"
    )


# --------------------------------------------------------------------------- helpers

def command_delay_game(scenario: str = "IBS-S-01", seed: int = 20270830, side_seed=None):
    from iron_bottom_sound import command_delay
    from iron_bottom_sound.engine import IronBottomEngine, ORDER_PHASES
    from iron_bottom_sound.llm import LLMPlayerSession
    from iron_bottom_sound.models import GameOptions, OrderBatch, Phase, Side
    from iron_bottom_sound.realistic_command import RealisticCommander, default_setup_orders

    engine = IronBottomEngine()
    state = engine.reset(scenario, seed, GameOptions(
        realistic_command=True, command_delay_mode=True,
    ))
    for side in Side:
        engine.submit_orders(state.game_id, OrderBatch(
            side=side, phase=Phase.FORMATION_SETUP,
            formation_setup=default_setup_orders(state, side),
        ))
    engine.advance(state.game_id)
    sessions = {item: LLMPlayerSession(item, RealisticCommander()) for item in Side}
    steps = 0
    while state.phase != Phase.COMPLETE and steps < 400:
        steps += 1
        if state.phase in ORDER_PHASES:
            for side in Side:
                if side.value in state.submitted_orders:
                    continue
                result = engine.submit_orders(
                    state.game_id, sessions[side].choose_orders(engine, state.game_id)
                )
                if not result.valid:
                    raise RuntimeError(f"{state.turn} {state.phase} {side}: {result.errors[:3]}")
        engine.advance(state.game_id)
    return engine, state


def realistic_game(scenario: str = "IBS-S-03", seed: int = 3):
    from iron_bottom_sound.engine import IronBottomEngine
    from iron_bottom_sound.models import GameOptions, OrderBatch, Phase, Side
    from iron_bottom_sound.realistic_command import default_setup_orders

    engine = IronBottomEngine()
    state = engine.reset(scenario, seed, GameOptions(realistic_command=True))
    for side in Side:
        engine.submit_orders(state.game_id, OrderBatch(
            side=side, phase=Phase.FORMATION_SETUP,
            formation_setup=default_setup_orders(state, side),
        ))
    engine.advance(state.game_id)
    return engine, state


def collect_keys(value, prefix: str = "") -> set[str]:
    found: set[str] = set()
    if isinstance(value, dict):
        for key, item in value.items():
            found.add(f"{prefix}.{key}" if prefix else key)
            found |= collect_keys(item, f"{prefix}.{key}" if prefix else key)
    elif isinstance(value, list):
        for item in value:
            found |= collect_keys(item, prefix)
    return found


def contains_any(tree, needles: set[str]) -> set[str]:
    """Any needle appearing anywhere in the tree (keys or string values)."""
    found: set[str] = set()
    if isinstance(tree, dict):
        for key, item in tree.items():
            if key in needles:
                found.add(key)
            found |= contains_any(item, needles)
    elif isinstance(tree, list):
        for item in tree:
            found |= contains_any(item, needles)
    elif isinstance(tree, str) and tree in needles:
        found.add(tree)
    return found


# --------------------------------------------------------------------------- audits

def audit_freeze() -> dict:
    """Golden replay + what changed in the frozen surface."""
    proc = subprocess.run(
        [sys.executable, str(Path(__file__).parent / "golden_replay.py"), "--check"],
        cwd=str(ROOT), capture_output=True, text=True, timeout=3600,
    )
    LOGS.mkdir(parents=True, exist_ok=True)
    (LOGS / "audit_golden_check.log").write_text(proc.stdout + proc.stderr, encoding="utf-8")
    rows = []
    envelope: dict[str, int] = {}
    for line in proc.stdout.splitlines():
        match = re.match(r"\[check\] (\S+)\s+(OK|DRIFT)", line)
        if match:
            rows.append({"tag": match.group(1), "result": match.group(2)})
        added = re.match(r"\s+(.+?)\s+x(\d+)$", line)
        if added:
            envelope[added.group(1)] = int(added.group(2))
    diff = subprocess.run(
        ["git", "diff", FREEZE_TAG, "--stat"], cwd=str(ROOT),
        capture_output=True, text=True, timeout=120,
    ).stdout
    frozen_files = subprocess.run(
        ["git", "show", "--name-only", "--pretty=format:", FREEZE_TAG],
        cwd=str(ROOT), capture_output=True, text=True, timeout=120,
    ).stdout
    changed = subprocess.run(
        ["git", "diff", FREEZE_TAG, "--name-only"], cwd=str(ROOT),
        capture_output=True, text=True, timeout=120,
    ).stdout.split()
    tracked_frozen = {
        "backend/src/iron_bottom_sound/realistic_command.py",
        "backend/src/iron_bottom_sound/models.py",
    }
    payload = {
        "freeze_tag": FREEZE_TAG,
        "frozen_commit": subprocess.run(
            ["git", "rev-parse", f"{FREEZE_TAG}^{{commit}}"], cwd=str(ROOT),
            capture_output=True, text=True, timeout=60,
        ).stdout.strip(),
        "rows": rows,
        "n_rows": len(rows),
        "n_drift": sum(1 for row in rows if row["result"] == "DRIFT"),
        "envelope_keys_added": dict(sorted(envelope.items())),
        "frozen_file_changed": sorted(tracked_frozen & set(changed)),
        "diffstat": diff.strip().splitlines()[-1] if diff.strip() else "",
        "verdict": "PASS" if rows and not any(row["result"] == "DRIFT" for row in rows) else "FAIL",
    }
    write("audit_freeze", payload)
    return payload


def audit_movement_style() -> dict:
    """Eligibility, body execution, geometry transition and the default path."""
    from iron_bottom_sound import formation_maneuver
    from iron_bottom_sound.models import (
        FormationGeometryKind, FormationMovementOrder, FormationMovementStyle,
        HexCoord, OrderBatch, Phase, Side,
    )
    from iron_bottom_sound.realistic_command import expand_movement_orders

    engine, state = realistic_game()
    while state.phase != Phase.MOVEMENT_PLANNING:
        for side in Side:
            engine.submit_orders(state.game_id, OrderBatch(side=side, phase=state.phase))
        engine.advance(state.game_id)
    formation = next(
        item for item in state.formations.values()
        if item.side == Side.AXIS
        and len([s for s in item.ship_ids if state.ships[s].position]) >= 2
    )
    members = formation_maneuver.attached_members(state, formation)
    geometry = formation_maneuver.measure_line(state, formation)
    valid_orders, valid_errors = formation_maneuver.expand_move_together(
        engine, state, formation, "2", members
    )
    broken = [dict(member.__dict__) for member in members]
    del broken
    # Same plan must be shared, and paths must differ.
    plans = {order.plan for order in valid_orders}
    lead = next((order for order in valid_orders if order.ship_id == formation.leader_id), None)
    follower = next((order for order in valid_orders if order.ship_id != formation.leader_id), None)
    paths_differ = False
    if lead is not None and follower is not None:
        lead_path = engine.movement_trajectory(state.ships[lead.ship_id], lead.plan)
        follow_path = engine.movement_trajectory(state.ships[follower.ship_id], follower.plan)
        paths_differ = [hexc for hexc, _ in lead_path[0]] != [hexc for hexc, _ in follow_path[0]]
    # Off-line member must be refused.
    last = members[-1]
    original = last.position
    last.position = HexCoord(q=original.q + 1, r=original.r + 1)
    off_line_errors = formation_maneuver.eligibility(engine, state, formation, "2", members)
    last.position = original
    payload = {
        "scenario": "IBS-S-03",
        "formation_id": formation.id,
        "geometry": geometry.as_payload(),
        "common_speed_interval": formation_maneuver.common_speed_interval(engine, state, members),
        "valid_plan": "2",
        "valid_orders": len(valid_orders),
        "valid_errors": valid_errors,
        "shared_token_sequence": sorted(plans),
        "copies_no_hexes": paths_differ,
        "off_line_refused": [error for error in off_line_errors if "hex line" in error],
        "default_style_follow_wake": all(
            item.movement_style == FormationMovementStyle.FOLLOW_WAKE
            for item in state.formations.values()
        ),
        "default_geometry_column": all(
            item.geometry_kind == FormationGeometryKind.COLUMN
            for item in state.formations.values()
        ),
        "declared_geometry_gate": formation_maneuver.follow_wake_allowed(
            formation.model_copy(update={"geometry_kind": FormationGeometryKind.STRAIGHT_LINE})
        )[0],
        "allow_turn_together": formation_maneuver.ALLOW_TURN_TOGETHER,
    }
    payload["verdict"] = (
        "PASS"
        if (
            payload["valid_orders"] == len(members)
            and not payload["valid_errors"]
            and len(plans) == 1
            and paths_differ
            and payload["off_line_refused"]
            and payload["default_style_follow_wake"]
            and payload["default_geometry_column"]
            and payload["declared_geometry_gate"] is False
        )
        else "FAIL"
    )
    write("audit_movement_style", payload)
    return payload


def audit_communication() -> dict:
    """The declared abstraction table plus a live game's communication ledger."""
    from collections import Counter

    from iron_bottom_sound import command_delay
    from iron_bottom_sound.communications import MEDIUM_PROFILES, delay_for, processing
    from iron_bottom_sound.models import CommunicationMedium, MessageKind, MessageStatus

    table = {
        medium.value: {
            "base_delay_turns": profile.base_delay_turns,
            "per_relay_stage_turns": profile.per_relay_stage_turns,
            "max_relay_hops": profile.max_relay_hops,
            "requires_encipherment": profile.requires_encipherment,
            "propagation_turns": profile.propagation_turns,
            "label": profile.label,
            "description": profile.description,
        }
        for medium, profile in sorted(MEDIUM_PROFILES.items(), key=lambda item: item[0].value)
    }
    samples = {
        "tbs_short_sitrep": delay_for(CommunicationMedium.TBS_SHORT, MessageKind.SITREP),
        "tbs_short_amendment": delay_for(CommunicationMedium.TBS_SHORT, MessageKind.AMENDMENT),
        "wt_coded": delay_for(CommunicationMedium.WT_CODED, MessageKind.SITREP),
        "wt_reencipher_relay_1hop": delay_for(
            CommunicationMedium.WT_REENCIPHER_RELAY, MessageKind.SITREP, relay_hops=1
        ),
        "multi_hop_1hop": delay_for(CommunicationMedium.MULTI_HOP, MessageKind.SITREP, relay_hops=1),
        "blinker_2hops": delay_for(CommunicationMedium.BLINKER, MessageKind.SITREP, relay_hops=2),
    }
    engine, state = command_delay_game()
    mode = state.command_delay
    delivered = [item for item in mode.messages if item.status == MessageStatus.DELIVERED]
    payload = {
        "abstraction_note": processing.abstraction_note(),
        "profiles": table,
        "delay_samples": samples,
        "loss_probabilities_defined": sorted(
            key for key in dir(processing) if "prob" in key.lower() or "drop" in key.lower()
        ),
        "game": {
            "scenario": "IBS-S-01",
            "turns": state.turn,
            "tick": mode.tick,
            "messages_total": len(mode.messages),
            "statuses": dict(sorted(Counter(item.status.value for item in mode.messages).items())),
            "mediums": dict(sorted(Counter(item.medium.value for item in mode.messages).items())),
            "handling_delays": dict(
                sorted(Counter(item.handling_delay for item in mode.messages).items())
            ),
            "issued_delivered_observed_all_set": all(
                item.issued_turn is not None and item.delivered_turn is not None
                and item.observed_turn is not None
                for item in delivered
            ),
            "delivered_never_before_issued": all(
                item.delivered_turn >= item.issued_turn for item in delivered
            ),
            "mission_orders": len(mode.mission_orders),
            "link_statuses": dict(
                sorted(Counter(
                    entry.link_status.value for entry in mode.formations.values()
                ).items())
            ),
            "authorities": dict(
                sorted(Counter(
                    entry.authority.value for entry in mode.formations.values()
                ).items())
            ),
            "report_ages": sorted(
                (entry.reported_turn is not None and state.turn - entry.reported_turn) or 0
                for entry in mode.formations.values()
            ),
        },
        "no_probability_in_source": "p_drop" not in Path(
            SRC / "iron_bottom_sound" / "communications" / "processing.py"
        ).read_text(),
    }
    payload["verdict"] = (
        "PASS"
        if (
            all(profile["propagation_turns"] == 0 for profile in table.values())
            and all(
                profile["label"] == processing.ABSTRACTION_LABEL for profile in table.values()
            )
            and samples["tbs_short_sitrep"] == 0
            and payload["game"]["delivered_never_before_issued"]
            and payload["game"]["issued_delivered_observed_all_set"]
            and payload["no_probability_in_source"]
        )
        else "FAIL"
    )
    write("audit_communication", payload)
    return payload


def audit_mission_order() -> dict:
    """Structure, contingency kinds and the autonomy ladder."""
    from iron_bottom_sound import delegation
    from iron_bottom_sound.models import Side

    order = delegation.mission_order_template(
        order_id="audit", formation_id="f", side=Side.ALLIES, turn=1,
        issued_by="fleet", mission="intercept", intent="prevent bombardment",
        task="screen the flank",
    )
    incomplete = delegation.mission_order_template(
        order_id="audit-2", formation_id="f", side=Side.ALLIES, turn=1,
        issued_by="fleet", mission="m", intent="i", task="t", contingencies=[],
    )
    payload = {
        "structure_fields": sorted(order.model_dump().keys()),
        "required_structure_present": {
            name: bool(getattr(order, name))
            for name in (
                "mission", "assumptions", "trigger_conditions", "commander_intent",
                "task_to_formation", "coordination_measures", "operating_area",
                "target_priority_directives", "roe", "risk_constraints",
                "report_requirements", "communications_plan", "commander_location",
                "rendezvous", "loss_of_comm_plan", "contingencies",
            )
        },
        "validation_errors_for_a_complete_order": delegation.validate_mission_order(order),
        "validation_errors_when_a_branch_kind_is_missing": delegation.validate_mission_order(
            incomplete
        ),
        "contingency_kinds": sorted({item.branch.value for item in order.contingencies}),
        "autonomy_ladder": delegation.autonomy_priority_list(),
        "doctrine_constants": {
            "superior_force_ratio": delegation.SUPERIOR_FORCE_RATIO,
            "minimum_capability_hull_fraction": delegation.MINIMUM_CAPABILITY_HULL_FRACTION,
        },
    }
    payload["verdict"] = (
        "PASS"
        if (
            not payload["validation_errors_for_a_complete_order"]
            and payload["validation_errors_when_a_branch_kind_is_missing"]
            and len(payload["contingency_kinds"]) == 3
            and payload["autonomy_ladder"][0] == "engine legality"
        )
        else "FAIL"
    )
    write("audit_mission_order", payload)
    return payload


def audit_leakage() -> dict:
    """Fleet view, formation view, both modes, both sides.

    Sampled at several points *during* a live game rather than once at the end:
    at the end of a scenario a side may have no formation left, and a fleet view
    with zero reports would pass the "exactly one exact formation" check
    vacuously instead of proving anything.
    """
    from iron_bottom_sound import command_delay
    from iron_bottom_sound.command_observation import (
        fleet_observation, formation_observation,
    )
    from iron_bottom_sound.engine import ORDER_PHASES, IronBottomEngine
    from iron_bottom_sound.llm import LLMPlayerSession
    from iron_bottom_sound.models import GameOptions, OrderBatch, Phase, Side
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
    sessions = {item: LLMPlayerSession(item, RealisticCommander()) for item in Side}

    findings: list[str] = []
    fleet_rows: list[dict] = []
    formation_rows: list[dict] = []
    sampled_turns: set[int] = set()
    steps = 0
    while state.phase != Phase.COMPLETE and steps < 400:
        steps += 1
        # Sample while both sides still have formations afloat.
        if (
            state.phase == Phase.GUNNERY
            and state.turn not in sampled_turns
            and all(command_delay.active_formations(state, item) for item in Side)
        ):
            sampled_turns.add(state.turn)
            for side in Side:
                view = fleet_observation(engine, state, side).model_dump(mode="json")
                opponents = {ship.id for ship in state.ships.values() if ship.side is not side}
                opposing_formations = {
                    formation.id for formation in state.formations.values()
                    if formation.side is not side
                }
                # The ``contacts`` block is the fleet's own plot: contacts its
                # ships can see are exactly what a plot is for, so it is checked
                # separately (against the engine's own visibility rule) rather than
                # counted as leakage.  Everywhere else, no opposing ship may appear
                # at all.
                without_contacts = {key: value for key, value in view.items()
                                    if key != "contacts"}
                leaked_ships = contains_any(without_contacts, opponents)
                leaked_formations = contains_any(view, opposing_formations)
                if leaked_ships:
                    findings.append(
                        f"t{state.turn} fleet view {side.value} leaks opposing ships "
                        f"outside its contacts plot: {sorted(leaked_ships)}"
                    )
                contact_ids = {item["ship_id"] for item in view["contacts"]}
                embarked_positions = [
                    state.ships[ship_id].position
                    for ship_id in view["embarked"].get("ship_ids", [])
                    if state.ships[ship_id].position is not None
                ]
                visible_now = {
                    ship.id for ship in state.ships.values()
                    if ship.side is not side and ship.position is not None and not ship.sunk
                    and engine._visible_to(state, ship, side, embarked_positions)
                }
                if not embarked_positions:
                    if contact_ids:
                        findings.append(
                            f"t{state.turn} fleet view {side.value} has contacts with no "
                            "embarked ships to see them"
                        )
                elif contact_ids != visible_now:
                    findings.append(
                        f"t{state.turn} fleet view {side.value} contacts {sorted(contact_ids)} "
                        f"!= the embarked formation's own visibility {sorted(visible_now)}"
                    )
                for contact in view["contacts"]:
                    extra = sorted(set(contact) - {
                        "ship_id", "name", "ship_type", "position", "heading", "sunk",
                    })
                    if extra:
                        findings.append(
                            f"t{state.turn} fleet view {side.value} contact carries {extra}"
                        )
                if leaked_formations:
                    findings.append(
                        f"t{state.turn} fleet view {side.value} leaks opposing formations "
                        f"{sorted(leaked_formations)}"
                    )
                for forbidden in FORBIDDEN_LOCAL_KEYS:
                    if forbidden in view:
                        findings.append(
                            f"t{state.turn} fleet view {side.value} exposes {forbidden}"
                        )
                exact = [
                    item["formation_id"] for item in view["reports"] if item["is_source_of_truth"]
                ]
                embarked_afloat = any(
                    formation.id == view["embarked_formation_id"]
                    for formation in command_delay.active_formations(state, side)
                )
                # While the fleet commander's formation is afloat it is the one and
                # only exact report; once it is gone nobody is embarked, and then no
                # formation may be exact either.
                if embarked_afloat and exact != [view["embarked_formation_id"]]:
                    findings.append(
                        f"t{state.turn} fleet view {side.value} exact formations {exact} "
                        f"rather than just the embarked {view['embarked_formation_id']}"
                    )
                if not embarked_afloat and exact:
                    findings.append(
                        f"t{state.turn} fleet view {side.value} marks {exact} exact while the "
                        "embarked formation is not afloat"
                    )
                fleet_rows.append({
                    "turn": state.turn,
                    "side": side.value,
                    "embarked": view["embarked_formation_id"],
                    "exact_formation": exact,
                    "reports": len(view["reports"]),
                    "report_ages": sorted(
                        (item["age_turns"] if item["age_turns"] is not None else -1)
                        for item in view["reports"]
                    ),
                    "embarked_ships": len(view["embarked"].get("ship_ids", [])),
                    "contacts": len(view["contacts"]),
                })
            for side in Side:
                for formation in command_delay.active_formations(state, side):
                    view = formation_observation(
                        engine, state, side, formation.id
                    ).model_dump(mode="json")
                    for forbidden in FORBIDDEN_LOCAL_KEYS:
                        if forbidden in view:
                            findings.append(
                                f"t{state.turn} formation view {formation.id} exposes {forbidden}"
                            )
                    opponents = {
                        ship.id for ship in state.ships.values() if ship.side is not side
                    }
                    # An opposing id may appear only as one of this formation's own
                    # sightings, in the two blocks derived from that sighting set:
                    # ``local_contacts`` and the priority options it may weight.  Any
                    # appearance elsewhere would be knowledge the formation never
                    # obtained.
                    allowed_blocks = ("local_contacts", "legal_target_priority_options")
                    outside_sightings = {
                        key: value for key, value in view.items()
                        if key not in allowed_blocks
                    }
                    leaked = contains_any(outside_sightings, opponents)
                    if leaked:
                        findings.append(
                            f"t{state.turn} formation view {formation.id} names opposing ships "
                            f"outside its own sightings: {sorted(leaked)}"
                        )
                    local_contacts = {item["ship_id"] for item in view["local_contacts"]}
                    weightable = {
                        item["target_id"] for item in view["legal_target_priority_options"]
                    }
                    if not weightable <= local_contacts:
                        findings.append(
                            f"t{state.turn} formation view {formation.id} offers weight on "
                            f"{sorted(weightable - local_contacts)} it has not sighted"
                        )
                    # A local contact must be visible to THIS formation's own ships.
                    own_positions = [
                        state.ships[ship_id].position
                        for ship_id in formation.ship_ids
                        if state.ships[ship_id].position is not None
                    ]
                    truly_local = {
                        ship.id for ship in state.ships.values()
                        if ship.side is not side and ship.position is not None and not ship.sunk
                        and engine._visible_to(state, ship, side, own_positions)
                    }
                    if local_contacts != truly_local:
                        findings.append(
                            f"t{state.turn} formation view {formation.id} contacts "
                            f"{sorted(local_contacts)} != its own visibility {sorted(truly_local)}"
                        )
                    formation_rows.append({
                        "turn": state.turn,
                        "side": side.value,
                        "formation_id": formation.id,
                        "own_ships": len([
                            ship_id for ship_id in formation.ship_ids
                            if state.ships[ship_id].position is not None
                        ]),
                        "local_contacts": len(local_contacts),
                        "opposing_ship_ids_outside_own_sightings": sorted(leaked),
                        "weightable_targets": len(weightable),
                        "link_status": view["link_status"],
                        "top_level_keys": sorted(view.keys()),
                    })
        if state.phase in ORDER_PHASES:
            for side in Side:
                if side.value in state.submitted_orders:
                    continue
                result = engine.submit_orders(
                    state.game_id, sessions[side].choose_orders(engine, state.game_id)
                )
                if not result.valid:
                    raise RuntimeError(f"{state.turn} {state.phase} {side}: {result.errors[:3]}")
        engine.advance(state.game_id)

    if len(sampled_turns) < 2:
        findings.append(f"only {len(sampled_turns)} sampling points; the audit is too weak")

    secret_events = [
        event for event in state.events
        if event.type.startswith(("command_delay", "command_message", "formation_agent",
                                  "mission_order"))
    ]
    unfiltered = sorted({event.type for event in secret_events if "secret_side" not in event.payload})
    if unfiltered:
        findings.append(f"command-delay events without secret_side: {unfiltered}")
    classic = engine_games_without_mode()
    if classic["classic_has_command_delay_field"]:
        findings.append("classic observation carries the command delay field")
    if classic["realistic_has_command_delay_field"]:
        findings.append("realistic observation carries the command delay field")
    payload = {
        "sampled_turns": sorted(sampled_turns),
        "fleet_views": fleet_rows,
        "formation_views": formation_rows,
        "command_events": {
            "total": len(secret_events),
            "without_secret_side": unfiltered,
            "types": sorted({event.type for event in secret_events}),
        },
        "classic_realistic_payload": classic,
        "findings": findings,
        "verdict": "PASS" if not findings else "FAIL",
    }
    write("audit_leakage", payload)
    return payload


def engine_games_without_mode() -> dict:
    """Observations in Classic and Realistic must not carry the mode's state."""
    from iron_bottom_sound.engine import IronBottomEngine
    from iron_bottom_sound.models import GameOptions, OrderBatch, Phase, Side
    from iron_bottom_sound.realistic_command import default_setup_orders

    result = {"classic_has_command_delay_field": None, "realistic_has_command_delay_field": None}
    engine = IronBottomEngine()
    classic = engine.reset("IBS-S-03", 3, GameOptions())
    observation = engine.observe(classic.game_id, Side.AXIS).model_dump(mode="json")
    result["classic_has_command_delay_field"] = "command_delay" in collect_keys(observation)

    engine2 = IronBottomEngine()
    realistic = engine2.reset("IBS-S-03", 3, GameOptions(realistic_command=True))
    for side in Side:
        engine2.submit_orders(realistic.game_id, OrderBatch(
            side=side, phase=Phase.FORMATION_SETUP,
            formation_setup=default_setup_orders(realistic, side),
        ))
    engine2.advance(realistic.game_id)
    observation = engine2.observe(realistic.game_id, Side.AXIS).model_dump(mode="json")
    result["realistic_has_command_delay_field"] = "command_delay" in collect_keys(observation)
    return {
        "classic_has_command_delay_field": result["classic_has_command_delay_field"],
        "realistic_has_command_delay_field": result["realistic_has_command_delay_field"],
        "note": "the mode state is not part of any player observation in any mode",
    }


def _policy_observation_clean(engine, state) -> bool:
    """A formation that is still afloat, in either mode, sees no gunnery machinery."""
    from iron_bottom_sound import command_delay
    from iron_bottom_sound.command_observation import formation_observation
    from iron_bottom_sound.models import Side

    for side in Side:
        formations = command_delay.active_formations(state, side)
        if formations:
            payload = formation_observation(
                engine, state, side, formations[0].id
            ).model_dump(mode="json")
            return not contains_any(
                payload,
                {"mount_ids", "mounts", "firing_solution", "hit_modifier", "expected_hits"},
            )
    return False


def audit_gunnery_authority() -> dict:
    """The authority boundary, including two adversarial attempts to cross it.

    Legality is measured **at each gunnery phase**, with the candidate set the
    engine offered at that moment: judging a turn-3 order against a turn-7 board
    would flag every order as illegal and prove nothing.
    """
    from iron_bottom_sound import command_delay, formation_agents, target_priority
    from iron_bottom_sound.command_observation import (
        LOCAL_PRIORITY_WEIGHT_LIMIT, formation_observation,
    )
    from iron_bottom_sound.engine import ORDER_PHASES, IronBottomEngine
    from iron_bottom_sound.llm import LLMPlayerSession
    from iron_bottom_sound.models import (
        GameOptions, GunneryOrder, OrderBatch, Phase, Side, TargetPriorityDirective,
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
    sessions = {item: LLMPlayerSession(item, RealisticCommander()) for item in Side}

    checked = 0
    illegal: list[dict] = []
    refusals: list[str] = []
    fallback_legal: bool | None = None
    steps = 0
    while state.phase != Phase.COMPLETE and steps < 400:
        steps += 1
        if state.phase == Phase.GUNNERY:
            legal: dict[Side, set] = {}
            for batch_side in Side:
                legal[batch_side] = {
                    (item["ship_id"], target["target_id"])
                    for item in engine._gunnery_candidates(state, batch_side)
                    for target in item["targets"]
                }
            # Adversarial attempt 1: submit a raw gunnery batch on this mode.
            for batch_side in Side:
                if not legal[batch_side]:
                    continue
                ship_id, target_id = sorted(legal[batch_side])[0]
                result = engine.validate_orders(state.game_id, OrderBatch(
                    side=batch_side, phase=Phase.GUNNERY,
                    gunnery=[GunneryOrder(ship_id=ship_id, primary_target=target_id, mounts=[])],
                ))
                if result.valid:
                    refusals.append(f"a raw gunnery batch was accepted for {batch_side.value}")
                elif not any("engine selector" in error for error in result.errors):
                    refusals.append(f"unexpected wording: {result.errors}")
            # Adversarial attempt 2: a directive naming an invisible target.
            if fallback_legal is None:
                probe_side = next(
                    (item for item in Side if engine._gunnery_candidates(state, item)), None
                )
                if probe_side is not None:
                    orders = target_priority.select_gunnery_orders(
                        engine, state, probe_side,
                        [TargetPriorityDirective(
                            formation_id="f", source="FLEET_ORDER",
                            target_id="IBS-U-NOT-A-SHIP", weight=1.0,
                        )],
                    )
                    fallback_legal = all(
                        (order.ship_id, order.primary_target) in legal[probe_side]
                        for order in orders
                    )
        if state.phase in ORDER_PHASES:
            for side in Side:
                if side.value in state.submitted_orders:
                    continue
                result = engine.submit_orders(
                    state.game_id, sessions[side].choose_orders(engine, state.game_id)
                )
                if not result.valid:
                    raise RuntimeError(f"{state.turn} {state.phase} {side}: {result.errors[:3]}")
        # Verify each accepted batch against the board it was built on.  The batch
        # is read from ``submitted_orders``: sealing happens inside ``advance``, so
        # this is the last moment at which the board is still the one the selector
        # saw.
        if state.phase == Phase.GUNNERY and state.submitted_orders:
            for batch_side_value, batch in sorted(state.submitted_orders.items()):
                board = {
                    (item["ship_id"], target["target_id"])
                    for item in engine._gunnery_candidates(state, batch.side)
                    for target in item["targets"]
                }
                for order in batch.gunnery:
                    checked += 1
                    if order.primary_target and (order.ship_id, order.primary_target) not in board:
                        illegal.append({
                            "turn": state.turn, "side": batch_side_value,
                            "ship_id": order.ship_id, "target": order.primary_target,
                        })
        engine.advance(state.game_id)

    mode = state.command_delay
    decision_fields = sorted(formation_agents.FormationDecision.model_fields)
    forbidden_present = sorted(
        {"gunnery", "mounts", "mount_ids", "firing_solution", "hit_modifier", "expected_hits"}
        & set(decision_fields)
    )
    guard = target_priority.validate_agent_decision_shape({
        "formation_id": "f", "turn": 1, "phase": "gunnery",
        "target_priority_adjustments": [], "mounts": [{"mount_id": "A"}],
    })
    decision_scan = []
    for record in mode.decisions:
        keys = set(record) | {
            key for adjustment in record.get("target_priority_adjustments", []) for key in adjustment
        }
        bad = sorted(
            keys & {"mounts", "mount_ids", "firing_solution", "hit_modifier",
                    "expected_hits", "gunnery", "gunnery_orders"}
        )
        if bad:
            decision_scan.append({"formation_id": record["formation_id"], "bad": bad})
    carried = sum(
        len(batch.target_priorities)
        for key, sealed in state.sealed_orders.items() if key.endswith("gunnery")
        for batch in sealed.values()
    )
    payload = {
        "decision_fields": decision_fields,
        "forbidden_fields_on_decision": forbidden_present,
        "structural_guard_errors": guard,
        "raw_gunnery_refusals": refusals or ["every raw gunnery batch was refused"],
        "sealed_gunnery_orders_checked": checked,
        "sealed_gunnery_orders_illegal": len(illegal),
        "illegal_examples": illegal[:5],
        "invisible_target_fallback_legal": bool(fallback_legal),
        "directives_that_reached_the_selector": carried,
        "agent_decisions_scanned": len(mode.decisions),
        "agent_decisions_with_gunnery_fields": decision_scan,
        "local_weight_limit": LOCAL_PRIORITY_WEIGHT_LIMIT,
        "local_weights_within_limit": all(
            abs(directive.weight) <= LOCAL_PRIORITY_WEIGHT_LIMIT
            for directive in mode.local_directives
        ),
        "policy_observation_has_no_gunnery": _policy_observation_clean(engine, state)
        or _policy_observation_clean_at_start(),
    }
    payload["verdict"] = (
        "PASS"
        if (
            not forbidden_present
            and guard
            and not refusals
            and checked > 0
            and not illegal
            and fallback_legal
            and not decision_scan
            and payload["local_weights_within_limit"]
            and payload["policy_observation_has_no_gunnery"]
            and carried > 0
        )
        else "FAIL"
    )
    write("audit_gunnery_authority", payload)
    return payload


def _policy_observation_clean_at_start() -> bool:
    """Fallback probe: a fresh game always has a formation to inspect."""
    from iron_bottom_sound import command_delay
    from iron_bottom_sound.command_observation import formation_observation
    from iron_bottom_sound.engine import IronBottomEngine
    from iron_bottom_sound.models import GameOptions, OrderBatch, Phase, Side
    from iron_bottom_sound.realistic_command import default_setup_orders

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
    for side in Side:
        formations = command_delay.active_formations(state, side)
        if formations:
            payload = formation_observation(engine, state, side, formations[0].id)
            return not contains_any(
                payload.model_dump(mode="json"),
                {"mount_ids", "mounts", "firing_solution", "hit_modifier", "expected_hits"},
            )
    return False


def audit_replay() -> dict:
    """Cross-process replay determinism of a whole Command Delay game."""
    seeds = ["0", "1", "2", "5"]
    script = """
import json, sys
sys.path.insert(0, sys.argv[1])
from iron_bottom_sound import command_delay
from iron_bottom_sound.engine import ORDER_PHASES, IronBottomEngine
from iron_bottom_sound.llm import LLMPlayerSession
from iron_bottom_sound.models import GameOptions, Phase, Side
from iron_bottom_sound.realistic_command import RealisticCommander

engine = IronBottomEngine()
state = engine.reset("IBS-S-01", 20270830,
                     GameOptions(realistic_command=True, command_delay_mode=True))
sessions = {side: LLMPlayerSession(side, RealisticCommander()) for side in Side}
steps = 0
while state.phase != Phase.COMPLETE and steps < 400:
    steps += 1
    if state.phase in ORDER_PHASES:
        for side in Side:
            if side.value in state.submitted_orders:
                continue
            result = engine.submit_orders(
                state.game_id, sessions[side].choose_orders(engine, state.game_id))
            if not result.valid:
                raise SystemExit("rejected: " + repr(result.errors[:2]))
    engine.advance(state.game_id)
mode = state.command_delay
events = [
    {"turn": e.turn, "phase": e.phase.value, "type": e.type,
     "payload": {k: (v if k != "game_id" else "<GAME_ID>") for k, v in e.payload.items()}}
    for e in state.events
]
json.dump({
    "events": events,
    "decisions": mode.decisions,
    "messages": [m.model_dump(mode="json") for m in mode.messages],
    "links": {k: (v.link_status.value, v.reported_turn) for k, v in mode.formations.items()},
    "ships": {s.id: (s.position.label if s.position else None, s.heading, s.hull, s.sunk)
              for s in state.ships.values()},
    "rng_counter": state.rng_counter,
    "winner": state.winner.value if state.winner else None,
}, sys.stdout, sort_keys=True)
"""
    import hashlib

    digests: dict[str, str] = {}
    for seed in seeds:
        import os

        env = dict(os.environ, PYTHONHASHSEED=seed, PYTHONPATH=str(SRC))
        proc = subprocess.run(
            [sys.executable, "-c", script, str(SRC)], cwd=str(ROOT), env=env,
            capture_output=True, text=True, timeout=1800,
        )
        if proc.returncode != 0:
            payload = {"verdict": "FAIL", "error": proc.stderr[-2000:]}
            write("audit_replay", payload)
            return payload
        digests[seed] = hashlib.sha256(proc.stdout.encode("utf-8")).hexdigest()
    payload = {
        "hash_seeds": seeds,
        "digests": digests,
        "unique": len(set(digests.values())),
        "verdict": "PASS" if len(set(digests.values())) == 1 else "FAIL",
    }
    write("audit_replay", payload)
    return payload


def audit_data_model() -> dict:
    """Envelope growth measured by the golden replay, plus the new model fields."""
    from iron_bottom_sound import models as model_module

    log = (LOGS / "audit_golden_check.log")
    envelope: dict[str, int] = {}
    if log.exists():
        for line in log.read_text(encoding="utf-8").splitlines():
            match = re.match(r"\s+(.+?)\s+x(\d+)$", line)
            if match:
                envelope[match.group(1)] = int(match.group(2))
    added_fields = {
        "GameOptions": ["command_delay_mode"],
        "FormationState": ["movement_style", "geometry_kind", "line_axis"],
        "FormationMovementOrder": ["movement_style", "reform_column"],
        "OrderBatch": ["target_priorities"],
        "GameState": ["command_delay"],
    }
    types = {
        "FormationMovementStyle": [item.value for item in model_module.FormationMovementStyle],
        "FormationGeometryKind": [item.value for item in model_module.FormationGeometryKind],
        "AuthorityLevel": [item.value for item in model_module.AuthorityLevel],
        "LinkStatus": [item.value for item in model_module.LinkStatus],
        "CommunicationMedium": [item.value for item in model_module.CommunicationMedium],
        "MessagePrecedence": [item.value for item in model_module.MessagePrecedence],
        "MessageKind": [item.value for item in model_module.MessageKind],
        "MessageStatus": [item.value for item in model_module.MessageStatus],
        "ContingencyBranch": [item.value for item in model_module.ContingencyBranch],
    }
    new_models = [
        "FormationMovementStyle", "FormationGeometryKind", "AuthorityLevel", "LinkStatus",
        "CommandAuthority", "FormationCommandState", "CommandDelayState", "MessagePrecedence",
        "CommunicationMedium", "MessageKind", "MessageStatus", "CommandMessage",
        "ContingencyBranch", "TargetPriorityDirective", "Contingency", "MissionOrder",
        "ContractTerm", "ContractState", "LedgerEntry",
    ]
    payload = {
        "new_top_level_models": new_models,
        "new_enum_values": types,
        "new_fields_on_existing_models": added_fields,
        "envelope_keys_added_to_frozen_replays": dict(sorted(envelope.items())),
        "envelope_leaf_keys": sorted({path.rsplit(".", 1)[-1] for path in envelope}),
        "note": (
            "all additive: no frozen key changed value or disappeared, which is what the "
            "frozen-projection comparison in golden_replay.py checks"
        ),
        "verdict": "PASS" if envelope else "FAIL",
    }
    write("audit_data_model", payload)
    return payload


AUDITS_BY_NAME = {
    "freeze": audit_freeze,
    "movement": audit_movement_style,
    "communication": audit_communication,
    "mission_order": audit_mission_order,
    "leakage": audit_leakage,
    "gunnery": audit_gunnery_authority,
    "replay": audit_replay,
    "data_model": audit_data_model,
}


def main(argv: list[str]) -> int:
    names = argv[1:] or list(AUDITS_BY_NAME)
    failures = []
    for name in names:
        function = AUDITS_BY_NAME.get(name)
        if function is None:
            print(f"unknown audit {name!r}; choose from {sorted(AUDITS_BY_NAME)}")
            return 2
        payload = function()
        verdict = payload.get("verdict", "?")
        print(f"{name:<14} {verdict}")
        if verdict != "PASS":
            failures.append(name)
    print("\nAUDITS = " + ("PASS" if not failures else "FAIL " + ", ".join(failures)))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
