from __future__ import annotations

import os
from pathlib import Path
from typing import Annotated

from fastapi import BackgroundTasks, FastAPI, Header, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .battle_report import (
    build_report_data,
    build_report_markdown,
    capture_after_advance,
    capture_phase_snapshot,
)
from .engine import IronBottomEngine
from .data import ROOT
from .llm import OpenAICompatibleCommander
from .state_export import export_frame, render_board
from .tactical import PROFILES, TacticalCommander
from .models import GameOptions, GunneryAssistRequest, MovementPreviewRequest, MovementTrajectoriesRequest, OrderBatch, Phase, ResearchConsent, Side, TorpedoAssistRequest
from .notify import notify_research_consent
from .storage import GameRepository


class CreateGame(BaseModel):
    scenario_id: str = "IBS-S-03"
    seed: int = 1
    options: GameOptions = Field(default_factory=GameOptions)
    # 用户主动提供的 LLM 密钥：仅按局存进程内存（_user_llm_keys），绝不落库/落盘。
    llm_api_key: str | None = None
    # 科研论文用途同意（可留称呼）：落库 research_consent 表 + 通知。
    research_consent: ResearchConsent | None = None


class FieldOfFireRequest(BaseModel):
    ship_id: str | None = None
    target_speed: int = 4


_frontend_dist = Path(__file__).resolve().parents[3] / "frontend" / "dist"

engine = IronBottomEngine()
_default_db = Path(__file__).resolve().parents[3] / "backend" / "iron-bottom-sound.sqlite3"
repository = GameRepository(os.environ.get("IBS_DB_PATH", str(_default_db)))
_default_reports_dir = Path(__file__).resolve().parents[3] / "backend" / "reports"
reports_root = os.environ.get("IBS_REPORTS_DIR", str(_default_reports_dir))
narrative_commander_factory = lambda: OpenAICompatibleCommander(timeout=30, max_tokens=800)
# 用户主动提供的 LLM 密钥（按 game_id）：进程内存，重启即清空，绝不写盘/写库。
_user_llm_keys: dict[str, str] = {}
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


if _frontend_dist.is_dir():
    # 生产式单进程托管：/api 前缀剥离（复刻 vite 代理 rewrite）+ 静态挂载 dist。
    # 开发期前端由 vite dev（:5173）代理 /api → :8000；构建后由本后端直接服务。
    @app.middleware("http")
    async def _strip_api_prefix(request, call_next):
        path = request.url.path
        if path.startswith("/api"):
            request.scope["path"] = path[4:] or "/"
            if request.scope.get("raw_path") is not None:
                request.scope["raw_path"] = request.scope["path"].encode()
        return await call_next(request)


@app.get("/scenarios")
def scenarios():
    return engine.scenarios()


@app.post("/games", status_code=201)
def create_game(request: CreateGame, background_tasks: BackgroundTasks):
    try:
        state = engine.reset(request.scenario_id, request.seed, request.options)
    except (KeyError, ValueError) as error:
        raise HTTPException(422, str(error)) from error
    repository.save(state)
    if request.llm_api_key:
        _user_llm_keys[state.game_id] = request.llm_api_key  # 仅内存，绝不落盘
    consent = request.research_consent
    if consent is not None:
        try:
            repository.save_research_consent(
                state.game_id, consent.allow, consent.handle, state.scenario_id
            )
        except Exception:
            pass  # 同意落库失败不影响建局
        if consent.allow:
            # 异步推送，建局不受通知延迟影响；失败静默。
            background_tasks.add_task(
                notify_research_consent, state.game_id, True, consent.handle, state.scenario_id
            )
    if state.options.battle_report:
        try:
            capture_phase_snapshot(repository, reports_root, state, engine,
                                   state.turn, state.phase.value)
        except Exception:
            pass  # 战报失败绝不影响对局
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


class LLMOpponentRequest(BaseModel):
    timeout: float = Field(default=90, gt=0)
    thinking_enabled: bool = False
    api_key: str | None = None  # 用户主动提供的密钥（可省略：优先用开局时注入的）


def _make_llm_commander(
    timeout: float, thinking_enabled: bool, api_key: str | None = None
) -> OpenAICompatibleCommander:
    return OpenAICompatibleCommander(
        timeout=timeout, thinking_enabled=thinking_enabled, api_key=api_key
    )


# 测试可注入 mock 指挥官的小工厂（保持端点默认走真实 DeepSeek）。
llm_commander_factory = _make_llm_commander


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


def _public_audit(audit) -> dict:
    """audits 公开子集：不含订单/计划等私有内容，只有耗时/令牌/校验/思考预览。"""
    return {
        "side": audit.side.value,
        "turn": audit.turn,
        "phase": audit.phase.value,
        "attempt": audit.attempt,
        "model": audit.model,
        "elapsed_ms": audit.elapsed_ms,
        "input_tokens": audit.input_tokens,
        "output_tokens": audit.output_tokens,
        "valid": audit.valid,
        "validation_errors": audit.validation_errors,
        "reasoning_preview": audit.reasoning_preview,
    }


@app.post("/games/{game_id}/llm-opponent")
def llm_opponent(
    game_id: str,
    request: LLMOpponentRequest | None = None,
    x_player_side: Annotated[str | None, Header()] = None,
):
    """LLM 模式：提交玩家对侧的 DeepSeek 订单（按 X-Player-Side 求对侧）。

    保持同步 def（FastAPI 线程池，不阻塞事件循环）。守卫顺序：
    404 → 403（非 llm mode）→ 400（缺 header）→ 503（无 DEEPSEEK_API_KEY，
    在一切 LLM 调用前）→ 409（玩家未提交）→ 幂等短路（对侧已提交）。
    订单仍由 `submit_orders` 校验，AI 不直接改状态；返回 audits 公开子集，
    不返回私有订单。
    """
    state = get_game(game_id)
    if state.options.mode != "llm":
        raise HTTPException(403, "LLM opponent is available only in llm mode")
    player_side = side_from_header(x_player_side)
    ai_side = player_side.opponent
    # 用户主动提供的密钥（本次请求 > 开局时注入）> 服务器环境变量。
    key = (request.api_key if request is not None else None) or _user_llm_keys.get(game_id)
    if not key and not os.environ.get("DEEPSEEK_API_KEY"):
        raise HTTPException(503, "请先提供你自己的 LLM API 密钥（开局时或在本次请求中传入 api_key）")
    if player_side.value not in state.submitted_orders:
        raise HTTPException(409, "Submit the player's orders first")
    if ai_side.value in state.submitted_orders:
        return {"valid": True, "ai_submitted": True, "audits": []}
    timeout = request.timeout if request is not None else 90
    thinking = request.thinking_enabled if request is not None else False
    commander = llm_commander_factory(timeout=timeout, thinking_enabled=thinking, api_key=key)
    try:
        _, batch, audits = commander.choose_plan(engine, game_id, ai_side)
    except ValueError as error:
        raise HTTPException(409, str(error)) from error
    result = engine.submit_orders(game_id, batch)
    if not result.valid:
        raise HTTPException(409, result.errors)
    repository.save(engine.get(game_id))
    return {
        "valid": True,
        "ai_submitted": True,
        "audits": [_public_audit(audit) for audit in audits],
    }


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
    prev_phase = state.phase  # advance 原地改 phase，须在推进前记下
    try:
        events = engine.advance(game_id)
    except ValueError as error:
        raise HTTPException(409, str(error)) from error
    next_state = engine.get(game_id)
    if next_state.options.battle_report:
        try:
            # 用户主动提供的密钥优先；无用户密钥时用服务器 env（无 env 则确定性回退）。
            key = _user_llm_keys.get(game_id)
            commander = (
                OpenAICompatibleCommander(api_key=key, timeout=30, max_tokens=800)
                if key else narrative_commander_factory()
            )
            capture_after_advance(repository, reports_root, next_state, engine,
                                  prev_phase, commander=commander)
        except Exception:
            pass  # 战报失败绝不影响对局
    repository.save(next_state)
    return [
        event for event in events
        if event.payload.get("secret_side") in (None, side.value)
        and not engine._hidden_damage_event(next_state, event, side)
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


def _report_entries(game_id: str) -> list[dict]:
    """battle_report 表行 → dict（build_report_data 输入格式）。"""
    return [entry.model_dump(mode="json") for entry in repository.battle_entries(game_id)]


@app.get("/games/{game_id}/battle-report")
def battle_report(game_id: str):
    """战报 JSON（中立历史文档，无需 side 头）。纯只读，不参与裁决。"""
    state = get_game(game_id)
    return build_report_data(state, engine, _report_entries(game_id))


@app.get("/games/{game_id}/battle-report/image/{rel_path:path}")
def battle_report_image(game_id: str, rel_path: str):
    """返回战报截图 PNG。路径穿越守卫：解析后必须落在该局的报告目录内。"""
    get_game(game_id)
    base = (Path(reports_root) / game_id).resolve()
    target = (base / rel_path).resolve()
    if not target.is_relative_to(base) or not target.is_file():
        raise HTTPException(404, "Not found")
    return FileResponse(str(target), media_type="image/png")


@app.get("/games/{game_id}/battle-report.md")
def battle_report_markdown(game_id: str):
    """自包含 MD 战报下载（截图以 base64 内嵌，可直接分享）。"""
    state = get_game(game_id)
    data = build_report_data(state, engine, _report_entries(game_id))
    #  BOM 前缀：UTF-8 带 BOM，中文 Windows 编辑器才不会误判成 GBK 显示乱码。
    content = "﻿" + build_report_markdown(reports_root, data, game_id)
    filename = f"{game_id}-battle-report.md"
    return Response(
        content=content,
        media_type="text/markdown; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


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


# 静态前端：挂在最后，仅接管未被 API/资产路由匹配的路径（/、/assets/index-*.js 等）。
if _frontend_dist.is_dir():
    app.mount(
        "/",
        StaticFiles(directory=str(_frontend_dist), html=True),
        name="frontend-dist",
    )
