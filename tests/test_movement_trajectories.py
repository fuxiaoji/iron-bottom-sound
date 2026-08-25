"""Batch movement trajectories: the read-only planned-path overlay for the map
(polyline through the ship's own plan + destination counter)."""

from fastapi.testclient import TestClient

from iron_bottom_sound.api import app, engine as api_engine
from iron_bottom_sound.engine import IronBottomEngine
from iron_bottom_sound.models import MovementOrder, OrderBatch, Phase, Side


def axis_ship(engine: IronBottomEngine, game_id: str):
    return next(
        ship
        for ship in engine.get(game_id).ships.values()
        if ship.side.value == "axis" and ship.position is not None
    )


def game_in_movement_planning(client, seed: int = 5) -> str:
    created = client.post("/games", json={"scenario_id": "IBS-S-03", "seed": seed}).json()
    game_id = created["game_id"]
    api_engine.submit_orders(game_id, OrderBatch(side=Side.AXIS, phase=Phase.REINFORCEMENT))
    api_engine.submit_orders(game_id, OrderBatch(side=Side.ALLIES, phase=Phase.REINFORCEMENT))
    api_engine.advance(game_id)
    assert api_engine.get(game_id).phase == Phase.MOVEMENT_PLANNING
    return game_id


def test_trajectories_match_movement_preview_per_ship() -> None:
    engine = IronBottomEngine()
    state = engine.reset("IBS-S-03", seed=7, game_id="traj-preview")
    ship = axis_ship(engine, state.game_id)
    plan = "1S1"
    preview = engine.movement_preview(state, ship, plan=plan)
    result = engine.movement_plan_trajectories(
        state, Side.AXIS, [{"ship_id": ship.id, "plan": plan}]
    )
    entry = result["trajectories"][0]
    assert entry["ship_id"] == ship.id
    assert entry["cost"] == preview["cost"]
    assert entry["valid"] is preview["valid"]
    assert entry["commitable"] is preview["commitable"]
    assert entry["errors"] == preview["errors"]
    assert entry["trajectory"] == preview["trajectory"]
    assert entry["end_hex"] == preview["current_label"]
    assert entry["end_heading"] == preview["current_heading"]
    assert entry["trajectory"][-1]["label"] == entry["end_hex"]


def test_trajectories_empty_plan_is_stationary() -> None:
    engine = IronBottomEngine()
    state = engine.reset("IBS-S-03", seed=7, game_id="traj-stationary")
    ship = axis_ship(engine, state.game_id)
    result = engine.movement_plan_trajectories(
        state, Side.AXIS, [{"ship_id": ship.id, "plan": "0"}]
    )
    entry = result["trajectories"][0]
    assert entry["valid"] is True
    assert entry["trajectory"] == []
    assert entry["end_hex"] == ship.position.label


def test_trajectories_non_owned_ship_is_invalid_entry() -> None:
    engine = IronBottomEngine()
    state = engine.reset("IBS-S-03", seed=7, game_id="traj-enemy")
    enemy = next(
        ship for ship in state.ships.values()
        if ship.side == Side.ALLIES and ship.position is not None
    )
    result = engine.movement_plan_trajectories(
        state, Side.AXIS, [{"ship_id": enemy.id, "plan": "2"}]
    )
    entry = result["trajectories"][0]
    assert entry["ship_id"] == enemy.id
    assert entry["valid"] is False
    assert entry["commitable"] is False
    assert entry["trajectory"] == []
    assert entry["end_hex"] is None
    assert entry["errors"]


def test_trajectories_unpositioned_owned_ship_is_invalid_entry() -> None:
    engine = IronBottomEngine()
    state = engine.reset("IBS-S-03", seed=7, game_id="traj-unpositioned")
    ship = axis_ship(engine, state.game_id)
    ship.position = None  # simulate a pending reinforcement / not-yet-entered ship
    result = engine.movement_plan_trajectories(
        state, Side.AXIS, [{"ship_id": ship.id, "plan": "1"}]
    )
    entry = result["trajectories"][0]
    assert entry["valid"] is False
    assert entry["end_hex"] is None


def test_trajectories_api_shape_and_wrong_phase() -> None:
    client = TestClient(app)
    game_id = game_in_movement_planning(client)
    ship = axis_ship(api_engine, game_id)
    response = client.post(
        f"/games/{game_id}/movement-trajectories",
        headers={"X-Player-Side": "axis"},
        json={"plans": [{"ship_id": ship.id, "plan": "1"}]},
    )
    assert response.status_code == 200
    trajectories = response.json()["trajectories"]
    assert len(trajectories) == 1
    entry = trajectories[0]
    assert entry["ship_id"] == ship.id
    assert entry["valid"] is True
    assert entry["trajectory"][-1]["label"] == entry["end_hex"]
    assert entry["end_heading"] == ship.heading
    # enemy plan is returned as an invalid entry (batch endpoint, never leaks data)
    enemy = next(
        ship for ship in api_engine.get(game_id).ships.values()
        if ship.side.value == "allies" and ship.position is not None
    )
    enemy_plan = client.post(
        f"/games/{game_id}/movement-trajectories",
        headers={"X-Player-Side": "axis"},
        json={"plans": [{"ship_id": enemy.id, "plan": "1"}]},
    )
    assert enemy_plan.status_code == 200
    assert enemy_plan.json()["trajectories"][0]["trajectory"] == []
    # wrong phase is rejected
    api_engine.submit_orders(game_id, full_movement_batch(game_id, Side.AXIS))
    api_engine.submit_orders(game_id, full_movement_batch(game_id, Side.ALLIES))
    api_engine.advance(game_id)
    assert api_engine.get(game_id).phase == Phase.TORPEDO_PLANNING
    wrong_phase = client.post(
        f"/games/{game_id}/movement-trajectories",
        headers={"X-Player-Side": "axis"},
        json={"plans": [{"ship_id": ship.id, "plan": "1"}]},
    )
    assert wrong_phase.status_code == 409


def full_movement_batch(game_id: str, side: Side) -> OrderBatch:
    own = [
        ship for ship in api_engine.get(game_id).ships.values()
        if ship.side == side and ship.position is not None
    ]
    return OrderBatch(
        side=side,
        phase=Phase.MOVEMENT_PLANNING,
        movement=[MovementOrder(ship_id=ship.id, plan="0") for ship in own],
    )
