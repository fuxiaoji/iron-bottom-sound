"""Deterministic tutorial choreography, isolated from normal adjudication.

The script never replaces an order or a rules table.  It may stage a labelled
teaching incident, after which the normal realistic-command validator forces
the player to resolve the resulting formation crisis.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from .models import FormationSpeedDecision, GameState, HexCoord, OrderBatch, Phase, RuleReference, Side, index_to_column

if TYPE_CHECKING:
    from .engine import IronBottomEngine


ERMA_SCRIPT = "erma_grand_fleet"
ERMA_SPEED_CASUALTY = "IBS-U-IJN-ERMA-ISHIKARI"
SPEED_CRISIS_FLAG = "erma_speed_crisis_staged"
DEPLOYMENT_FLAG = "erma_close_action_deployment"


def validate_tutorial_options(state: GameState) -> None:
    script = state.options.tutorial_script
    if script is None:
        return
    if state.options.mode != "tutorial":
        raise ValueError("Tutorial scripts require tutorial mode")
    if script == ERMA_SCRIPT and (
        state.scenario_id != "IBS-S-EM-01" or not state.options.realistic_command
    ):
        raise ValueError("erma_grand_fleet requires IBS-S-EM-01 realistic command")


def prepare_tutorial_state(state: GameState) -> None:
    """Move both free-deployment fleets into a legal, visible teaching engagement."""
    if state.options.tutorial_script != ERMA_SCRIPT:
        return
    for ship in state.ships.values():
        if not ship.position:
            continue
        label = ship.position.label
        row = int("".join(filter(str.isdigit, label)))
        delta_q, delta_row = ((4, 5) if ship.side == Side.AXIS else (-4, -5))
        ship.position = HexCoord.from_label(
            f"{index_to_column(ship.position.q + delta_q)}{row + delta_row}"
        )
    state.tutorial_flags.add(DEPLOYMENT_FLAG)


def record_tutorial_start(engine: "IronBottomEngine", state: GameState) -> None:
    if state.options.tutorial_script != ERMA_SCRIPT:
        return
    engine._event(
        state,
        "tutorial_deployment_staged",
        "教学部署：双方主力舰队已进入可观察的远程炮战距离",
        payload={
            "script_id": "IBS-TUT-EM-01",
            "axis_translation": {"columns": 4, "rows": 5},
            "allies_translation": {"columns": -4, "rows": -5},
        },
        rule=RuleReference(
            rule_id="IBS-TUT-EM-01",
            document="tutorial-script-erma-grand-fleet",
            section="教学部署：远程炮战接触",
        ),
    )


def apply_checkpoint(engine: "IronBottomEngine", state: GameState, checkpoint: str) -> None:
    """Apply a checkpoint once; replay reaches the same checkpoint naturally."""
    if (
        state.options.tutorial_script != ERMA_SCRIPT
        or checkpoint != "after_turn_1_fire"
        or state.turn != 1
        or SPEED_CRISIS_FLAG in state.tutorial_flags
    ):
        return
    ship = state.ships[ERMA_SPEED_CASUALTY]
    before_track = tuple(ship.speed_damage_crossed)
    before_max = ship.max_speed_for_turn(2)
    crossed = list(before_track)
    row = ship.speed_damage_track[1]
    target_max = 3
    crossed[1] = next(
        (index for index, speed in enumerate(row) if speed <= target_max),
        len(row),
    )
    ship.speed_damage_crossed = tuple(crossed)  # type: ignore[assignment]
    after_max = ship.max_speed_for_turn(2)
    state.tutorial_flags.add(SPEED_CRISIS_FLAG)
    engine._event(
        state,
        "tutorial_speed_crisis",
        f"教学战情：{ship.name}轮机舱受创，下回合最高航速降至 {after_max} MF",
        payload={
            "script_id": "IBS-TUT-EM-05",
            "ship_id": ship.id,
            "before_speed_track": list(before_track),
            "after_speed_track": list(ship.speed_damage_crossed),
            "before_turn_2_max_speed": before_max,
            "after_turn_2_max_speed": after_max,
            "teaching_choices": ["reduce", "detach"],
        },
        rule=RuleReference(
            rule_id="IBS-TUT-EM-05",
            document="tutorial-script-erma-grand-fleet",
            section="固定事件：共同航速危机",
        ),
    )


def coach_suggested_orders(state: GameState, batch: OrderBatch) -> OrderBatch:
    """Make the speed-crisis choice visible in the editable teaching draft."""
    if (
        state.options.tutorial_script != ERMA_SCRIPT
        or state.phase != Phase.MOVEMENT_PLANNING
        or batch.side != Side.AXIS
        or SPEED_CRISIS_FLAG not in state.tutorial_flags
    ):
        return batch
    casualty = state.ships[ERMA_SPEED_CASUALTY]
    if casualty.command_status != "attached" or not casualty.formation_id:
        return batch
    coached = batch.model_copy(deep=True)
    formation = state.formations[casualty.formation_id]
    order = next(
        (item for item in coached.formation_movement if item.formation_id == formation.id),
        None,
    )
    if order is None:
        return batch
    legal_speed = min(
        state.ships[ship_id].max_speed_for_turn(state.turn)
        for ship_id in formation.ship_ids
        if state.ships[ship_id].position and state.ships[ship_id].command_status == "attached"
    )
    order.leader_plan = str(max(formation.speed, legal_speed))
    order.speed_decision = FormationSpeedDecision(
        formation_id=formation.id,
        action="reduce",
        speed=legal_speed,
    )
    return coached
