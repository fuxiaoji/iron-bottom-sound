from __future__ import annotations

import os
from pathlib import Path
from typing import Annotated

from fastapi import FastAPI, Header, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .engine import IronBottomEngine
from .data import ROOT
from .llm import DeterministicCommander
from .models import GameOptions, OrderBatch, Side
from .storage import GameRepository


class CreateGame(BaseModel):
    scenario_id: str = "IBS-S-03"
    seed: int = 1
    options: GameOptions = Field(default_factory=GameOptions)


engine = IronBottomEngine()
_default_db = Path(__file__).resolve().parents[3] / "backend" / "iron-bottom-sound.sqlite3"
repository = GameRepository(os.environ.get("IBS_DB_PATH", str(_default_db)))
app = FastAPI(title="铁底湾的回响 IV", version="0.1.0")
app.mount(
    "/assets/counters",
    StaticFiles(directory=ROOT / "resources" / "originals" / "assets" / "images"),
    name="counter-assets",
)


def side_from_header(value: str | None) -> Side:
    if value is None:
        raise HTTPException(400, "X-Player-Side is required")
    try:
        return Side(value)
    except ValueError as error:
        raise HTTPException(400, "X-Player-Side must be axis or allies") from error


def get_game(game_id: str):
    try:
        return engine.get(game_id)
    except KeyError:
        try:
            state = repository.load(game_id)
        except KeyError as error:
            raise HTTPException(404, str(error)) from error
        engine.games[game_id] = state
        return state


@app.get("/scenarios")
def scenarios():
    return engine.scenarios()


@app.post("/games", status_code=201)
def create_game(request: CreateGame):
    try:
        state = engine.reset(request.scenario_id, request.seed, request.options)
    except (KeyError, ValueError) as error:
        raise HTTPException(422, str(error)) from error
    repository.save(state)
    return {"game_id": state.game_id, "scenario_id": state.scenario_id, "phase": state.phase}


@app.get("/games/{game_id}/view")
def view_game(game_id: str, x_player_side: Annotated[str | None, Header()] = None):
    get_game(game_id)
    return engine.observe(game_id, side_from_header(x_player_side))


@app.get("/games/{game_id}/legal-actions")
def legal_actions(game_id: str, x_player_side: Annotated[str | None, Header()] = None):
    get_game(game_id)
    return engine.legal_actions(game_id, side_from_header(x_player_side))


@app.get("/games/{game_id}/suggested-orders")
def suggested_orders(game_id: str, x_player_side: Annotated[str | None, Header()] = None):
    """Return an editable, engine-validated starting batch without exposing enemy data."""
    get_game(game_id)
    side = side_from_header(x_player_side)
    try:
        return DeterministicCommander().choose_orders(engine, game_id, side)
    except ValueError as error:
        raise HTTPException(409, str(error)) from error


@app.post("/games/{game_id}/tutorial-opponent")
def tutorial_opponent(game_id: str, x_player_side: Annotated[str | None, Header()] = None):
    """Submit the isolated instructor side without returning its private order batch."""
    state = get_game(game_id)
    player_side = side_from_header(x_player_side)
    if state.options.mode != "tutorial" or player_side != Side.AXIS:
        raise HTTPException(403, "Tutorial instructor is available only to the axis tutorial player")
    if Side.AXIS.value not in state.submitted_orders:
        raise HTTPException(409, "Submit the player's tutorial orders first")
    if Side.ALLIES.value in state.submitted_orders:
        return {"valid": True, "instructor_submitted": True}
    try:
        batch = DeterministicCommander().choose_orders(engine, game_id, Side.ALLIES)
    except ValueError as error:
        raise HTTPException(409, str(error)) from error
    result = engine.submit_orders(game_id, batch)
    if not result.valid:
        raise HTTPException(409, result.errors)
    repository.save(engine.get(game_id))
    return {"valid": True, "instructor_submitted": True}


@app.post("/games/{game_id}/orders")
def orders(game_id: str, batch: OrderBatch, x_player_side: Annotated[str | None, Header()] = None):
    state = get_game(game_id)
    side = side_from_header(x_player_side)
    if batch.side != side:
        raise HTTPException(403, "A side may submit only its own orders")
    result = engine.submit_orders(game_id, batch)
    if not result.valid:
        raise HTTPException(422, result.errors)
    repository.save(engine.get(game_id))
    return {
        **result.model_dump(mode="json"),
        "both_submitted": set(state.submitted_orders) == {Side.AXIS.value, Side.ALLIES.value},
        "phase": state.phase.value,
    }


@app.post("/games/{game_id}/handoff")
def handoff(game_id: str):
    get_game(game_id)
    return {"locked": True, "clear_sensitive_state": True}


@app.post("/games/{game_id}/advance")
def advance(game_id: str):
    get_game(game_id)
    try:
        events = engine.advance(game_id)
    except ValueError as error:
        raise HTTPException(409, str(error)) from error
    repository.save(engine.get(game_id))
    return events


@app.get("/games/{game_id}/events")
def events(game_id: str, after: int = Query(default=0, ge=0), x_player_side: Annotated[str | None, Header()] = None):
    state = get_game(game_id)
    side = side_from_header(x_player_side)
    return [
        event for event in state.events
        if event.sequence > after
        and event.payload.get("secret_side") in (None, side.value)
        and not engine._hidden_damage_event(state, event, side)
    ]


@app.websocket("/games/{game_id}")
async def websocket(game_id: str, websocket: WebSocket, side: Side = Query()):
    get_game(game_id)
    await websocket.accept()
    try:
        await websocket.send_json(engine.observe(game_id, side).model_dump(mode="json"))
        while True:
            await websocket.receive_text()
            await websocket.send_json(engine.observe(game_id, side).model_dump(mode="json"))
    except WebSocketDisconnect:
        return
