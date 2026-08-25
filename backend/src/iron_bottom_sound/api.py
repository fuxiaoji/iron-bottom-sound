from __future__ import annotations

import os
from pathlib import Path
from typing import Annotated

from fastapi import FastAPI, Header, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .engine import IronBottomEngine
from .data import ROOT
from .state_export import export_frame, render_board
from .tactical import PROFILES, TacticalCommander
from .models import GameOptions, GunneryAssistRequest, MovementPreviewRequest, MovementTrajectoriesRequest, OrderBatch, Phase, Side, TorpedoAssistRequest
from .storage import GameRepository


class CreateGame(BaseModel):
    scenario_id: str = "IBS-S-03"
    seed: int = 1
    options: GameOptions = Field(default_factory=GameOptions)


class FieldOfFireRequest(BaseModel):
    ship_id: str | None = None
    target_speed: int = 4


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
def view_game(
    game_id: str,
    x_player_side: Annotated[str | None, Header()] = None,
    debug: bool = False,
):
    get_game(game_id)
    return engine.observe(game_id, side_from_header(x_player_side), debug=debug)


@app.get("/games/{game_id}/legal-actions")
def legal_actions(game_id: str, x_player_side: Annotated[str | None, Header()] = None):
    get_game(game_id)
    return engine.legal_actions(game_id, side_from_header(x_player_side))


@app.get("/games/{game_id}/export")
def game_export(game_id: str, x_player_side: Annotated[str | None, Header()] = None):
    """投影一导出：JSONL 世界态帧 + cell-aligned ASCII 棋盘。纯只读，全部从
    `engine.observe` 可见集派生（战争迷雾一致），绝不落盘。"""
    state = get_game(game_id)
    side = side_from_header(x_player_side)
    return {"frame": export_frame(state, engine, side), "board": render_board(state, engine, side)}


@app.get("/games/{game_id}/suggested-orders")
def suggested_orders(game_id: str, x_player_side: Annotated[str | None, Header()] = None):
    """Return an editable, engine-validated starting batch without exposing enemy data."""
    get_game(game_id)
    side = side_from_header(x_player_side)
    try:
        return TacticalCommander().choose_orders(engine, game_id, side)
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
        batch = TacticalCommander().choose_orders(engine, game_id, Side.ALLIES)
    except ValueError as error:
        raise HTTPException(409, str(error)) from error
    result = engine.submit_orders(game_id, batch)
    if not result.valid:
        raise HTTPException(409, result.errors)
    repository.save(engine.get(game_id))
    return {"valid": True, "instructor_submitted": True}


class AIOpponentRequest(BaseModel):
    profile: str = "balanced"


@app.post("/games/{game_id}/ai-opponent")
def ai_opponent(game_id: str, request: AIOpponentRequest | None = None, x_player_side: Annotated[str | None, Header()] = None):
    """人机大战：提交玩家对侧的 AI 订单（按 X-Player-Side 求对侧、风格 profile
    可选），不返回其私有订单。通用（不限 mode/阵营）；玩家须先提交本阶段，AI 侧
    已提交则幂等短路。订单仍由规则引擎 `submit_orders` 校验，AI 不直接改状态。"""
    state = get_game(game_id)
    player_side = side_from_header(x_player_side)
    ai_side = player_side.opponent
    profile_name = request.profile if request is not None and request.profile else "balanced"
    if profile_name not in PROFILES:
        raise HTTPException(422, f"Unknown AI profile {profile_name}")
    if player_side.value not in state.submitted_orders:
        raise HTTPException(409, "Submit the player's orders first")
    if ai_side.value in state.submitted_orders:
        return {"valid": True, "ai_submitted": True}
    try:
        batch = TacticalCommander(profile=PROFILES[profile_name]).choose_orders(engine, game_id, ai_side)
    except ValueError as error:
        raise HTTPException(409, str(error)) from error
    result = engine.submit_orders(game_id, batch)
    if not result.valid:
        raise HTTPException(409, result.errors)
    repository.save(engine.get(game_id))
    return {"valid": True, "ai_submitted": True}


@app.post("/games/{game_id}/movement-preview")
def movement_preview(game_id: str, request: MovementPreviewRequest, x_player_side: Annotated[str | None, Header()] = None):
    """Pure read-only preview of a movement prefix for an owned ship; never saves."""
    state = get_game(game_id)
    side = side_from_header(x_player_side)
    if state.phase != Phase.MOVEMENT_PLANNING:
        raise HTTPException(409, "Movement preview is available only during movement planning")
    ship = state.ships.get(request.ship_id)
    if not ship or ship.side != side:
        raise HTTPException(403, "Movement preview is restricted to owned ships")
    return engine.movement_preview(
        state,
        ship,
        commands=request.commands or None,
        plan=request.plan,
        hexes=request.hexes or None,
    )


@app.post("/games/{game_id}/movement-trajectories")
def movement_trajectories(game_id: str, request: MovementTrajectoriesRequest, x_player_side: Annotated[str | None, Header()] = None):
    """Pure read-only planned-movement trajectories for the side's own draft plans; never saves."""
    state = get_game(game_id)
    side = side_from_header(x_player_side)
    if state.phase != Phase.MOVEMENT_PLANNING:
        raise HTTPException(409, "Movement trajectories are available only during movement planning")
    return engine.movement_plan_trajectories(
        state, side, [entry.model_dump() for entry in request.plans]
    )


@app.get("/games/{game_id}/sealed-trajectories")
def sealed_trajectories(game_id: str, x_player_side: Annotated[str | None, Header()] = None, debug: bool = False):
    """Replay this turn's sealed movement plans as trajectories (kept visible during
    torpedo planning). Own side always; enemy plans only when debug=true."""
    state = get_game(game_id)
    side = side_from_header(x_player_side)
    if state.phase != Phase.TORPEDO_PLANNING:
        raise HTTPException(409, "Sealed trajectories are available only during torpedo planning")
    return engine.sealed_movement_trajectories(state, side, debug=debug)


@app.post("/games/{game_id}/torpedo-assist")
def torpedo_assist(game_id: str, request: TorpedoAssistRequest, x_player_side: Annotated[str | None, Header()] = None):
    """Pure read-only torpedo recommendation (visible-info extrapolation); never saves."""
    state = get_game(game_id)
    side = side_from_header(x_player_side)
    if state.phase != Phase.TORPEDO_PLANNING:
        raise HTTPException(409, "Torpedo assist is available only during torpedo planning")
    return engine.torpedo_assist(state, side, target_id=request.target_id, launch=request.launch)


@app.post("/games/{game_id}/field-of-fire")
def field_of_fire(game_id: str, request: FieldOfFireRequest | None = None, x_player_side: Annotated[str | None, Header()] = None):
    """Pure read-only field-of-fire heatmap overlay (both sides, or one ship via body.ship_id); never saves."""
    state = get_game(game_id)
    return engine.field_of_fire_heatmap(
        state, side_from_header(x_player_side),
        ship_id=request.ship_id if request else None,
        target_speed=request.target_speed if request else 4,
    )


@app.post("/games/{game_id}/gunnery-assist")
def gunnery_assist(game_id: str, request: GunneryAssistRequest, x_player_side: Annotated[str | None, Header()] = None):
    """Pure read-only gunnery scheduling recommendation (most mounts, best modifier, spread); never saves."""
    state = get_game(game_id)
    side = side_from_header(x_player_side)
    if state.phase != Phase.GUNNERY:
        raise HTTPException(409, "Gunnery assist is available only during gunnery")
    return engine.gunnery_assist(state, side, assigned=request.assigned)


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
def advance(game_id: str, x_player_side: Annotated[str | None, Header()] = None):
    state = get_game(game_id)
    side = side_from_header(x_player_side)
    try:
        events = engine.advance(game_id)
    except ValueError as error:
        raise HTTPException(409, str(error)) from error
    repository.save(engine.get(game_id))
    return [
        event for event in events
        if event.payload.get("secret_side") in (None, side.value)
        and not engine._hidden_damage_event(state, event, side)
    ]


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
