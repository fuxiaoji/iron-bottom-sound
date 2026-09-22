"""CD-6 research hooks: ML observation tensors and episode export.

Interfaces only
---------------
No RL, GNN or Transformer is implemented here, and none of the existing modes
consume these functions.  They exist so a future research mode has a fixed,
auditable shape to consume — and so the *leakage* properties of that shape can be
tested now rather than after a model is built on top of them.

Two exports, deliberately different
-----------------------------------
``policy_observation`` (and ``observation_tensors``) is what a policy may see: one
formation's own local view, exactly the ``FormationObservation`` the local agent
already gets.  Nothing side-global can enter, because the tensor builder takes the
observation as its only game input.

``episode_export`` is the *research replay* record: both sides, all orders, all
messages, all decisions, for auditing a game after the fact.  It is emphatically
**not** a policy observation — ``POLICY_SAFE = False`` is written into the record
so a training script cannot quietly consume it as one.

Tensor shape
------------
Declared, versioned, and small enough to read: ``TENSOR_SPEC`` names every block
and its width.  Values are plain nested lists, so the module imports and the tests
run without numpy; ``to_numpy`` converts on demand and says so if numpy is missing.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, TYPE_CHECKING

from . import command_delay, contracts
from .command_observation import formation_observation
from .models import GameState, Phase, Side

if TYPE_CHECKING:
    from .engine import IronBottomEngine

TENSOR_VERSION = "cd-tensor-v1"

# Every block of the policy observation, with its width.  A future model reads this
# spec instead of guessing, and a change to it is a visible version bump.
TENSOR_SPEC: dict[str, dict[str, Any]] = {
    "self": {"width": 6, "fields": ["hull_fraction", "ship_count", "heading_sin",
                                    "heading_cos", "speed", "is_leader"]},
    "ships": {"width": 5, "fields": ["hull_fraction", "max_hull", "heading_sin",
                                     "heading_cos", "speed"], "per": "own ship"},
    "contacts": {"width": 5, "fields": ["distance", "absolute_bearing_sin",
                                        "absolute_bearing_cos", "is_priority_class",
                                        "class_rank"],
                 "per": "local contact"},
    "comm": {"width": 4, "fields": ["link_rank", "authority_rank", "messages_received",
                                    "reports_age"]},
    "objective": {"width": 3, "fields": ["has_waypoint", "has_order",
                                        "declared_contingencies"]},
}
LINK_RANK = {"direct": 1.0, "relayed": 0.75, "stale": 0.4, "blackout": 0.0}
AUTHORITY_RANK = {"fleet_directed": 1.0, "delegated": 0.6, "local_autonomy": 0.2}
CLASS_RANK = {"DD": 1, "DE": 1, "CL": 2, "AV": 2, "CA": 3, "CB": 3, "BC": 4, "BB": 5}


def _heading_sin_cos(heading: int | None) -> tuple[float, float]:
    if heading is None:
        return 0.0, 0.0
    import math

    angle = math.radians((heading - 1) * 60)
    return round(math.sin(angle), 6), round(math.cos(angle), 6)


# Axial deltas of the six IBS compass directions, indexed by heading 1..6.
_AXIAL_DELTA = {1: (1, -1), 2: (1, 0), 3: (0, 1), 4: (-1, 1), 5: (-1, 0), 6: (0, -1)}


def _axial_of(observation: dict, label: str | None) -> tuple[int, int] | None:
    """Axial coordinates of a hex label, resolved through the local map."""
    if not label:
        return None
    for cell in observation.get("local_map", []):
        if cell["hex"] == label:
            return (int(cell["q"]), int(cell["r"]))
    return None


def _guide_axial(observation) -> tuple[int, int] | None:
    """The formation guide's own hex, taken from the local formation state."""
    ships = {
        ship["ship_id"]: ship for ship in observation.formation_state.get("ships", [])
    }
    leader = ships.get(observation.formation_state.get("leader_id"))
    if leader is None and observation.formation_state.get("ships"):
        leader = observation.formation_state["ships"][0]
    payload = observation.model_dump(mode="json")
    return _axial_of(payload, leader.get("position") if leader else None)


def _contact_axial(observation, label: str | None) -> tuple[int, int] | None:
    return _axial_of(observation.model_dump(mode="json"), label)


def _bearing_direction(
    origin: tuple[int, int] | None, target: tuple[int, int] | None,
) -> int | None:
    """Absolute compass direction 1..6 from origin to target, or ``None``.

    Uses the same axial lattice the engine moves on, so the number is a real
    direction.  It is deliberately **absolute**, not relative to the observer's
    heading: the observer's own heading is already in the ``self`` block, so a
    policy can derive the engine's relative aspect (0 = bow, as in
    ``IronBottomEngine._relative_aspect``) itself without this module re-inventing
    a second convention.
    """
    if origin is None or target is None:
        return None
    dq = target[0] - origin[0]
    dr = target[1] - origin[1]
    if (dq, dr) == (0, 0):
        return None
    for direction, (step_q, step_r) in sorted(_AXIAL_DELTA.items()):
        for sign in (1, -1):
            if (step_q * sign, step_r * sign) == (dq, dr):
                return direction if sign == 1 else ((direction + 2) % 6) + 1
    # Not on an exact lattice line: nearest of the six directions.
    return min(
        _AXIAL_DELTA,
        key=lambda direction: abs(dq - _AXIAL_DELTA[direction][0])
        + abs(dr - _AXIAL_DELTA[direction][1]),
    )


def policy_observation(
    engine: "IronBottomEngine", state: GameState, side: Side, formation_id: str,
) -> dict[str, Any]:
    """The policy-safe observation: one formation's local view, nothing else."""
    observation = formation_observation(engine, state, side, formation_id)
    return json.loads(observation.model_dump_json())


def observation_tensors(
    engine: "IronBottomEngine", state: GameState, side: Side, formation_id: str,
) -> dict[str, Any]:
    """Build the declared tensor blocks for one formation's local view."""
    observation = formation_observation(engine, state, side, formation_id)
    ships = observation.formation_state.get("ships", [])
    total_hull = sum(int(ship.get("max_hull") or 0) for ship in ships) or 1
    hull_fraction = sum(int(ship.get("hull") or 0) for ship in ships) / total_hull
    leader_id = observation.formation_state.get("leader_id")
    heading = observation.formation_state.get("heading")
    sin_h, cos_h = _heading_sin_cos(heading)
    priority_classes = set()
    if observation.active_mission_order is not None:
        priority_classes = {
            directive.target_class
            for directive in observation.active_mission_order.target_priority_directives
            if directive.target_class
        }
    objective = observation.active_mission_order
    self_block = [
        round(hull_fraction, 6),
        float(len(ships)),
        sin_h,
        cos_h,
        float(observation.formation_state.get("speed") or 0),
        1.0 if leader_id in {ship.get("ship_id") for ship in ships} else 0.0,
    ]
    ship_rows = [
        [
            round((int(ship.get("hull") or 0) / (int(ship.get("max_hull") or 1))), 6),
            float(int(ship.get("max_hull") or 0)),
            *_heading_sin_cos(ship.get("heading")),
            float(observation.formation_state.get("speed") or 0),
        ]
        for ship in sorted(ships, key=lambda item: str(item.get("ship_id")))
    ]
    guide_axial = _guide_axial(observation)
    contact_rows = []
    for contact in sorted(observation.local_contacts, key=lambda item: item["ship_id"]):
        target_class = contact.get("ship_type")
        contact_axial = _contact_axial(observation, contact.get("position"))
        bearing = _bearing_direction(guide_axial, contact_axial)
        contact_rows.append([
            float(contact.get("range") if contact.get("range") is not None else -1),
            *_heading_sin_cos(bearing),
            1.0 if target_class in priority_classes else 0.0,
            float(CLASS_RANK.get(target_class or "", 0)),
        ])
    comm_block = [
        LINK_RANK.get(observation.link_status.value, 0.0),
        AUTHORITY_RANK.get(observation.authority.value, 0.0),
        float(len(observation.received_messages)),
        float(
            max((report.age_turns or 0) for report in observation.stale_external_reports)
            if observation.stale_external_reports else 0
        ),
    ]
    objective_block = [
        1.0 if objective is not None and objective.waypoint is not None else 0.0,
        1.0 if objective is not None else 0.0,
        # Declared, not activated: which branch is active is the agent's own
        # decision and belongs in the decision record, not in the observation.
        float(len(objective.contingencies) if objective is not None else 0),
    ]
    return {
        "tensor_version": TENSOR_VERSION,
        "formation_id": formation_id,
        "turn": state.turn,
        "phase": state.phase.value,
        "self": self_block,
        "ships": ship_rows,
        "contacts": contact_rows,
        "comm": comm_block,
        "objective": objective_block,
    }


def to_numpy(tensors: dict[str, Any]):
    """Convert the ragged blocks to arrays; numpy is imported only on demand."""
    try:
        import numpy as np
    except ImportError as error:  # pragma: no cover - numpy is present in this env
        raise RuntimeError(
            "numpy is required for to_numpy(); the tensors themselves are plain lists"
        ) from error

    def block(value):
        if isinstance(value, list) and value and isinstance(value[0], list):
            return np.asarray(value, dtype="float32")
        return np.asarray(value, dtype="float32")

    return {
        key: block(tensors[key])
        for key in ("self", "ships", "contacts", "comm", "objective")
    }


# --------------------------------------------------------------------------- episode export

def episode_records(
    engine: "IronBottomEngine", state: GameState,
) -> list[dict[str, Any]]:
    """Per-formation, per-turn local records — the policy-safe episode form."""
    records: list[dict[str, Any]] = []
    mode = getattr(state, "command_delay", None)
    if mode is None:
        return records
    decisions = {
        (record.get("formation_id"), record.get("turn")): record
        for record in mode.decisions
    }
    for side in Side:
        for formation in command_delay.active_formations(state, side):
            record = decisions.get((formation.id, state.turn))
            records.append({
                "turn": state.turn,
                "phase": state.phase.value,
                "side": side.value,
                "formation_id": formation.id,
                "POLICY_SAFE": True,
                "observation": policy_observation(engine, state, side, formation.id),
                # ``None`` before this turn's movement-planning boundary: the agent
                # has not decided yet, and a fabricated placeholder would be worse
                # than an honest absence.
                "decision": record,
                "decision_turn": (record or {}).get("turn"),
                "messages_received": [
                    {
                        "message_id": message.message_id,
                        "kind": message.kind.value,
                        "issued_turn": message.issued_turn,
                        "delivered_turn": message.delivered_turn,
                    }
                    for message in mode.messages
                    if message.destination == formation.id
                    and message.delivered_turn is not None
                ],
            })
    return sorted(records, key=lambda item: (item["turn"], item["side"], item["formation_id"]))


def episode_export(
    engine: "IronBottomEngine", state: GameState, *, max_events: int = 2000,
) -> dict[str, Any]:
    """The full auditable episode, for research replay — NOT a policy input.

    ``POLICY_SAFE`` is written as ``False`` and a warning string is included,
    because this record contains both sides' orders and every message: feeding it
    to a policy as an observation would be an information leak, and the flag makes
    that mistake impossible to make silently.
    """
    mode = getattr(state, "command_delay", None)
    return {
        "POLICY_SAFE": False,
        "warning": (
            "research replay record: contains both sides' orders and all messages. "
            "Use episode_records()/policy_observation() for policy input."
        ),
        "tensor_version": TENSOR_VERSION,
        "game_id": state.game_id,
        "scenario_id": state.scenario_id,
        "seed": state.seed,
        "turn": state.turn,
        "phase": state.phase.value,
        "options": state.options.model_dump(mode="json"),
        "events": [
            {"sequence": event.sequence, "turn": event.turn, "phase": event.phase.value,
             "type": event.type, "message": event.message, "payload": event.payload,
             "rule": event.rule.rule_id if event.rule else None}
            for event in state.events[-max_events:]
        ],
        "sealed_orders": {
            key: {side: batch.model_dump(mode="json") for side, batch in sealed.items()}
            for key, sealed in sorted(state.sealed_orders.items())
        },
        "messages": (
            [message.model_dump(mode="json") for message in mode.messages] if mode else []
        ),
        "mission_orders": (
            [order.model_dump(mode="json") for order in mode.mission_orders] if mode else []
        ),
        "agent_decisions": list(mode.decisions) if mode else [],
        "contracts": (
            [item.model_dump(mode="json") for item in mode.contracts] if mode else []
        ),
        "ledger": [item.model_dump(mode="json") for item in contracts.ledger(state)],
        "final_ships": {
            ship.id: {
                "side": ship.side.value,
                "position": ship.position.label if ship.position else None,
                "heading": ship.heading,
                "hull": ship.hull,
                "sunk": ship.sunk,
                "formation_id": ship.formation_id,
                "command_status": ship.command_status,
            }
            for ship in state.ships.values()
        },
        "rng_counter": state.rng_counter,
        "winner": state.winner.value if state.winner else None,
    }


def write_episode(
    path: str | Path, engine: "IronBottomEngine", state: GameState,
) -> Path:
    """Write one episode as JSON, creating the parent directory if needed."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = episode_export(engine, state)
    target.write_text(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n",
                      encoding="utf-8")
    return target


def write_episode_records(
    path: str | Path, engine: "IronBottomEngine", state: GameState,
) -> Path:
    """Append the policy-safe records as JSONL, one line per formation-turn."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("a", encoding="utf-8") as handle:
        for record in episode_records(engine, state):
            handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
    return target


def hook_status() -> dict[str, Any]:
    """One line each on what CD-6 exposes and what it deliberately does not."""
    return {
        "tensor_version": TENSOR_VERSION,
        "blocks": sorted(TENSOR_SPEC),
        "policy_safe_form": "episode_records() / policy_observation()",
        "replay_form": "episode_export() (POLICY_SAFE=False)",
        "contract_state": "contracts.contract_state() -- empty until declared",
        "incentive_ledger": list(contracts.LEDGER_KINDS),
        "implemented_learning": False,
        "note": "interfaces only: no RL/GNN/Transformer is implemented at this stage",
    }
