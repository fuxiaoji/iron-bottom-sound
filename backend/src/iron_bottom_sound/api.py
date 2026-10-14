from __future__ import annotations

import json
import hashlib
import os
from pathlib import Path
from typing import Annotated, Literal

from fastapi import BackgroundTasks, FastAPI, Header, HTTPException, Query, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, PlainTextResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, field_validator

from .battle_report import (
    build_report_data,
    build_report_markdown,
    capture_after_advance,
    capture_ai_action,
    capture_phase_snapshot,
)
from .engine import IronBottomEngine
from .data import ROOT, load_scenario, register_custom_scenario, unregister_custom_scenario
from .llm import OpenAICompatibleCommander
from .llm_providers import DEFAULT_MODELS, provider_runtime
from .state_export import export_frame, render_board
from .champions import CHAMPIONS
from .tactical import PROFILES, TacticalCommander
from .torpedo_tactics import AdaptiveTorpedoPlanner
from .models import FormationMovementOrder, FormationSetupOrder, GameOptions, GunneryAssistRequest, MovementPreviewRequest, MovementTrajectoriesRequest, OrderBatch, Phase, ResearchConsent, Side, TorpedoAssistRequest
from .realistic_command import RealisticCommander, expand_movement_orders, validate_setup
# Load cooperative planning together with the engine, never from a later version
# of the files in a still-running, non-reloading server.
from . import formation_tactics as _formation_tactics  # noqa: F401
from .notify import notify_research_consent
from .storage import GameRepository
from .savegame import build_save_bundle, clone_imported_game, validate_save_bundle
from .custom_scenarios import (
    CustomScenarioInput,
    builtin_as_editable_template,
    new_id,
    validate_definition,
    with_engine_default_formations,
)
from .counter_assets import asset_for
from .ship_records import load_ship_catalog, load_ship_records


class LLMConnectionConfig(BaseModel):
    provider: Literal["deepseek", "zhipu"] = "deepseek"
    model: str = Field(default=DEFAULT_MODELS["deepseek"], min_length=1, max_length=120,
                       pattern=r"^[A-Za-z0-9._:/-]+$")
    vision_enabled: bool = False


class CreateGame(BaseModel):
    scenario_id: str = "IBS-S-03"
    seed: int = 1
    options: GameOptions = Field(default_factory=lambda: GameOptions(ruleset_version="night-v2", night_recognition=True))
    # 用户主动提供的 LLM 密钥：仅按局存进程内存（_user_llm_keys），绝不落库/落盘。
    llm_api_key: str | None = None
    llm_config: LLMConnectionConfig | None = None
    # 科研论文用途同意（可留称呼）：落库 research_consent 表 + 通知。
    research_consent: ResearchConsent | None = None

    @field_validator("options", mode="before")
    @classmethod
    def new_game_version(cls, value):
        if isinstance(value, dict):
            return {"ruleset_version": "night-v2", "night_recognition": True, **value}
        return value


class FieldOfFireRequest(BaseModel):
    ship_id: str | None = None
    target_speed: int = 4


class FormationPreviewRequest(BaseModel):
    formations: list[FormationSetupOrder]


class FormationMovementPreviewRequest(BaseModel):
    formations: list[FormationMovementOrder]


_frontend_dist = Path(__file__).resolve().parents[3] / "frontend" / "dist"

engine = IronBottomEngine()
_default_db = Path(__file__).resolve().parents[3] / "backend" / "iron-bottom-sound.sqlite3"
repository = GameRepository(os.environ.get("IBS_DB_PATH", str(_default_db)))
for _definition in repository.custom_scenarios():
    register_custom_scenario(_definition)
_default_reports_dir = Path(__file__).resolve().parents[3] / "backend" / "reports"
reports_root = os.environ.get("IBS_REPORTS_DIR", str(_default_reports_dir))
narrative_commander_factory = lambda: OpenAICompatibleCommander(timeout=30, max_tokens=800)
# 用户主动提供的 LLM 密钥（按 game_id）：进程内存，重启即清空，绝不写盘/写库。
_user_llm_keys: dict[str, str] = {}
# Non-secret per-game runtime selection. Kept beside the key so persisted GameState and
# reports remain provider-neutral and old saves continue to load unchanged.
_user_llm_configs: dict[str, "LLMConnectionConfig"] = {}
app = FastAPI(title="铁底湾的回响 IV", version="0.1.0")


def source_revision() -> str:
    digest = hashlib.sha256()
    source = Path(__file__).resolve().parent
    for path in sorted(source.rglob("*.py")):
        digest.update(path.relative_to(source).as_posix().encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()


_loaded_revision = source_revision()


@app.get("/health")
def health():
    current = source_revision()
    payload = {"status": "ready" if current == _loaded_revision else "restart_required",
               "pid": os.getpid(), "loaded_revision": _loaded_revision,
               "source_revision": current}
    return Response(json.dumps(payload), media_type="application/json",
                    status_code=200 if current == _loaded_revision else 503)

app.mount(
    "/assets/counters",
    StaticFiles(directory=ROOT / "resources" / "originals" / "assets" / "images"),
    name="counter-assets",
)


def _custom_definition(scenario_id: str) -> dict:
    try:
        definition = repository.custom_scenario(scenario_id)
    except KeyError as error:
        raise HTTPException(404, str(error)) from error
    definition["id"] = scenario_id
    register_custom_scenario(definition)
    return definition


@app.get("/custom-scenarios")
def custom_scenarios():
    return repository.custom_scenarios()


@app.post("/custom-scenarios", status_code=201)
def create_custom_scenario(request: CustomScenarioInput):
    scenario_id = new_id()
    definition = with_engine_default_formations(request.model_dump(mode="json"))
    definition["id"] = scenario_id
    errors = validate_definition(scenario_id, definition)
    if errors:
        unregister_custom_scenario(scenario_id)
        raise HTTPException(422, {"errors": errors})
    repository.save_custom_scenario(scenario_id, definition)
    return definition


@app.get("/custom-scenarios/{scenario_id}")
def get_custom_scenario(scenario_id: str):
    return _custom_definition(scenario_id)


@app.put("/custom-scenarios/{scenario_id}")
def update_custom_scenario(scenario_id: str, request: CustomScenarioInput):
    _custom_definition(scenario_id)
    definition = with_engine_default_formations(request.model_dump(mode="json"))
    definition["id"] = scenario_id
    errors = validate_definition(scenario_id, definition)
    if errors:
        raise HTTPException(422, {"errors": errors})
    repository.save_custom_scenario(scenario_id, definition)
    register_custom_scenario(definition)
    return definition


@app.delete("/custom-scenarios/{scenario_id}", status_code=204)
def delete_custom_scenario(scenario_id: str):
    try:
        repository.delete_custom_scenario(scenario_id)
    except KeyError as error:
        raise HTTPException(404, str(error)) from error
    unregister_custom_scenario(scenario_id)


@app.get("/ship-catalog")
def ship_catalog():
    records = load_ship_records()
    catalog = load_ship_catalog()
    # 取“名录 ∪ 记录”：场景扩展（如二马 24 舰）只在 records/剧本里建档，
    # 未进 catalog.yaml——不并进来的话工坊永远选不到它们。
    # 名录里“已有同名同型完整记录的替身”去重：同一艘舰只列一条（有完整档案那条）。
    record_by_name_type = {(record.name, record.ship_type) for record in records.values()}

    def entry(ship_id: str) -> dict | None:
        record = records.get(ship_id)
        base = catalog.get(ship_id, {})
        if record is None:
            name, ship_type = base.get("name"), base.get("ship_type")
            if (name, ship_type) in record_by_name_type:
                return None  # 该名录舰已有可用的完整记录：去掉这份替身，只留那条记录。
        else:
            name, ship_type = record.name, record.ship_type
        # 棋子图：记录舰与锁定（未建档）舰都解析——锁定的查 counter-assets.json 的
        # catalog 绑定（有图即有棋子预览），没有图的锁定舰保持 None。
        asset = None
        if name and ship_type:
            asset = asset_for(ship_id, str(name), str(ship_type))
        return {
            "id": ship_id,
            "name": record.name if record else base.get("name", ship_id),
            "ship_type": record.ship_type if record else base.get("ship_type"),
            "displacement_band": record.displacement_band if record else None,
            "vp": record.vp if record else None,
            "asset": asset,
            "class_name": base.get("class_name"),
            "complete": record is not None,
        }

    rows: list[dict] = []
    for ship_id in sorted(set(catalog) | set(records)):
        item = entry(ship_id)
        if item is not None:
            rows.append(item)
    return rows


@app.get("/builtin-scenarios/{scenario_id}/template")
def builtin_scenario_template(scenario_id: str):
    try:
        return builtin_as_editable_template(scenario_id)
    except KeyError as error:
        raise HTTPException(404, str(error)) from error

_realistic_rules_path = ROOT / "docs" / "rules" / "realistic-command.md"


@app.get("/rules/realistic-command", response_class=PlainTextResponse)
def realistic_command_rules() -> PlainTextResponse:
    """Serve the audited player rules from their single repository source."""
    return PlainTextResponse(
        _realistic_rules_path.read_text(encoding="utf-8"),
        media_type="text/markdown",
    )


def _register_formation_policies(state, api_key: str | None, config: "LLMConnectionConfig | None") -> dict:
    """Point the mode's formation agents at a model, or record why they are not.

    The key is used from process memory only.  Registering it for both sides is
    deliberate: in this mode *every* formation is commanded by an agent, and the
    player commands fleets by writing orders, so both sides' formations run the same
    kind of policy.  With no key the formations still fight, on doctrine, and the
    label says so — no output is ever presented as a model's when it is not.
    """
    from .command_delay import set_side_policy
    from .formation_llm import make_policy
    from .models import Side

    key = api_key
    provider = "deepseek"
    model = None
    if config is not None:
        provider, model = config.provider, config.model
    policy, label = make_policy(provider=provider, model=model, api_key=key)
    for side in Side:
        set_side_policy(side, policy, label, game_id=state.game_id)
    return {"policy": label, "sides": [side.value for side in Side]}


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


@app.get("/scenarios/{scenario_id}/briefing")
def scenario_briefing(scenario_id: str):
    """想定简报：等同印刷想定手册的公开信息。

    双方编制、初始布阵（位置/方向/航速）、援军、回合数、能见度、特殊规则与
    胜利条件都是手册里双方开局前共知的纸面数据，不含秘密计划、隐藏部署或
    未落地的对局状态；自定义想定同样只投影其定义数据。
    """
    try:
        definition = load_scenario(scenario_id)
    except KeyError as error:
        raise HTTPException(404, str(error)) from error
    return briefing_definition(scenario_id, definition)


def briefing_definition(scenario_id: str, definition: dict):
    records = load_ship_records()

    def ship_row(entry: dict) -> dict:
        record = records.get(entry["id"])
        return {
            "id": entry["id"],
            "name": entry["name"],
            "side": entry["side"],
            "ship_type": record.ship_type if record else None,
            "vp": record.vp if record else None,
            "recorded": record is not None,
            "position": entry.get("position"),
            "heading": entry.get("heading"),
            "speed": entry.get("speed"),
            "flagship": bool(entry.get("flagship")),
            "asset": entry.get("asset"),
        }

    reinforcements = definition.get("reinforcements")
    ai_stats = definition.get("ai_stats")
    payload = {
        "id": definition.get("id", scenario_id),
        "number": definition.get("number"),
        "title": definition.get("title"),
        "date": definition.get("date"),
        "turns": definition.get("turns"),
        "visibility": definition.get("visibility", {}),
        "victory": definition.get("victory", {}),
        "special_rules": definition.get("special_rules", []),
        "setup_note": definition.get("setup", {}).get("engine_default_note"),
        "formations": definition.get("setup", {}).get("engine_default_formations"),
        "ships": [ship_row(entry) for entry in definition.get("ships", [])],
        "ai_stats": ai_stats,
        "reinforcements": None
        if not reinforcements
        else {
            "trigger": reinforcements.get("trigger", {}),
            "arrival": reinforcements.get("arrival", {}),
            "ships": [ship_row(entry) for entry in reinforcements.get("ships", [])],
        },
    }
    return payload


@app.get("/games/{game_id}/briefing")
def game_briefing(game_id: str):
    from .night import unlimited_turns
    state = get_game(game_id)
    definition = state.rule_snapshot.get("scenario") or load_scenario(state.scenario_id)
    payload = briefing_definition(state.scenario_id, definition)
    if state.options.ruleset_version == "legacy-v1":
        reinforcement_status = "沿用旧局增援流程"
    elif state.scenario_id == "IBS-S-10":
        reinforcement_status = "第2回合起逐回合2D6，图拉吉按离场条件触发"
    elif state.reinforcement_arrival_turn:
        reinforcement_status = f"入场回合 {state.reinforcement_arrival_turn}；{'检定已完成' if state.reinforcement_roll_done else '尚待检定'}"
    else:
        reinforcement_status = "无后续增援"
    payload["runtime"] = {
        "ruleset_version": state.options.ruleset_version, "turn": state.turn, "phase": state.phase.value,
        "visibility": state.visibility, "enabled_rules": [k for k,v in state.options.optional_rules.model_dump().items() if v],
        "forced_rules": definition.get("optional_rules", []), "alerted_count": len(state.scenario_state.get("alerted", [])),
        "unlimited_turns": unlimited_turns(state),
        "blockers": state.scenario_state.get("rule_blockers", []),
        "special_status": "来源阻断，已知特例可单独验收" if state.scenario_state.get("rule_blockers") else
                          ("新版特例裁决就绪" if state.options.ruleset_version=="night-v2" else "沿用旧局裁决"),
        "reinforcement_status": reinforcement_status,
        "ending_condition": (next((r["text"] for r in definition.get("special_rules",[]) if r["id"]=="IBS-S-10-R4"), "") if state.scenario_id=="IBS-S-10" and state.options.ruleset_version=="night-v2" else f"第{state.max_turns}回合结算想定胜利条件"),
    }
    return payload


def local_debug(request: Request, explicit: bool):
    if not explicit or not request.client or request.client.host not in ("127.0.0.1", "::1", "localhost", "testclient"):
        raise HTTPException(403, "AI 详细记录仅允许显式本地调试读取")


@app.get("/games/{game_id}/ai-debug")
def ai_debug(game_id: str, request: Request, debug: bool = False, side: Side = Side.AXIS,
             turn: int | None = None, phase: Phase | None = None, formation_id: str | None = None,
             before: int | None = None, limit: int = Query(default=12, ge=1, le=48)):
    local_debug(request, debug)
    state = get_game(game_id)
    from .ai_memory import debug_payload, sanitize
    rows = repository.ai_debug(game_id, side.value, turn, phase.value if phase else None, before, limit, formation_id)
    cd = []
    if state.command_delay:
        cd = [r for r in state.command_delay.agent_log if r.get("side") == side.value
              and (turn is None or r.get("turn") == turn) and (phase is None or r.get("phase") == phase.value)
              and (formation_id is None or r.get("formation_id") == formation_id)]
    return sanitize({"entries": rows, "next_before": rows[-1]["id"] if len(rows) == limit else None,
                     "memory": debug_payload(state, side), "command_delay": cd[-limit:]})


@app.get("/games/{game_id}/ai-memory")
def ai_memory_export(game_id: str, request: Request, debug: bool = False, side: Side = Side.AXIS):
    local_debug(request, debug)
    from .ai_memory import debug_payload
    state = get_game(game_id)
    payload = {"format": "ibs-ai-memory", "game_id": game_id, "side": side.value,
               "turn": state.turn, "memory": debug_payload(state, side)}
    return Response(json.dumps(payload, ensure_ascii=False), media_type="application/json",
                    headers={"Content-Disposition": f'attachment; filename="ibs-memory-{side.value}.json"'})


@app.post("/games/{game_id}/upgrade-copy", status_code=201)
def upgrade_copy(game_id: str):
    from . import night
    from .rules_snapshot import pack
    from uuid import uuid4
    state = get_game(game_id)
    if state.options.ruleset_version != "legacy-v1" or state.phase != Phase.REINFORCEMENT or state.submitted_orders or any(k.startswith(f"{state.turn}:") for k in state.sealed_orders):
        raise HTTPException(409, "仅旧局无封存命令的回合起点可另存为新版；原局不会改变")
    if state.markers or state.contact_formations or state.command_delay:
        raise HTTPException(409, "当前隐蔽／环境／命令延迟状态无法安全转换，请新建新版对局")
    copied = state.model_copy(deep=True)
    copied.game_id = str(uuid4())
    copied.options.ruleset_version = "night-v2"
    copied.sealed_orders = {}  # Only historical batches: keep them in old archive, never execute them again.
    try:
        night.initialize(copied)
    except ValueError as error:
        raise HTTPException(409, str(error)) from error
    if copied.scenario_state.get("rule_blockers"):
        raise HTTPException(409, "；".join(b["text"] for b in copied.scenario_state["rule_blockers"]))
    copied.rule_snapshot["adjudication"] = pack(vars(engine._base_rules))
    copied.rule_snapshot["tables_hash"] = hashlib.sha256(json.dumps(copied.rule_snapshot["adjudication"], sort_keys=True).encode()).hexdigest()
    copied.events[0].payload["game_id"] = copied.game_id
    engine._event(copied, "rules_upgraded_copy", "旧局另存为新版，未重裁历史",
                  payload={"source_game_id": state.game_id, "upgrade_state": copied.model_dump(mode="json", exclude={"events"})})
    repository.import_game(copied, [(len(copied.events), copied)])
    engine.games[copied.game_id] = copied
    return {"game_id": copied.game_id}


@app.get("/games")
def saved_games():
    """Resume-card metadata only; never include units or sealed orders."""
    return repository.game_summaries()


@app.post("/games", status_code=201)
def create_game(request: CreateGame, background_tasks: BackgroundTasks):
    if request.llm_config is not None:
        try:
            provider_runtime(
                request.llm_config.provider,
                request.llm_config.model,
                vision_enabled=request.llm_config.vision_enabled,
            )
        except ValueError as error:
            raise HTTPException(422, str(error)) from error
    try:
        if request.scenario_id.startswith("IBS-CUSTOM-"):
            _custom_definition(request.scenario_id)
        state = engine.reset(request.scenario_id, request.seed, request.options)
    except (KeyError, ValueError) as error:
        raise HTTPException(422, str(error)) from error
    repository.save(state)
    if request.llm_api_key:
        _user_llm_keys[state.game_id] = request.llm_api_key  # 仅内存，绝不落盘
    if request.llm_config:
        _user_llm_configs[state.game_id] = request.llm_config
    if state.options.command_delay_mode:
        _register_formation_policies(state, request.llm_api_key, request.llm_config)
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


@app.post("/games/import", status_code=201)
def import_game(bundle: dict):
    try:
        state, snapshots = validate_save_bundle(bundle)
    except (KeyError, TypeError, ValueError) as error:
        raise HTTPException(422, str(error)) from error

    custom_definition = bundle.get("custom_scenario")
    if state.scenario_id.startswith("IBS-CUSTOM-"):
        if not isinstance(custom_definition, dict):
            raise HTTPException(422, "自定义想定存档缺少想定定义")
        if custom_definition.get("id") != state.scenario_id:
            raise HTTPException(422, "自定义想定标识与存档不一致")
        try:
            existing = repository.custom_scenario(state.scenario_id)
        except KeyError:
            errors = validate_definition(state.scenario_id, custom_definition)
            if errors:
                unregister_custom_scenario(state.scenario_id)
                raise HTTPException(422, {"errors": errors})
            repository.save_custom_scenario(state.scenario_id, custom_definition)
        else:
            if json.dumps(existing, sort_keys=True) != json.dumps(custom_definition, sort_keys=True):
                raise HTTPException(409, "服务器上同名自定义想定与存档不同，已拒绝覆盖")
        register_custom_scenario(custom_definition)

    imported, imported_snapshots = clone_imported_game(state, snapshots)
    try:
        repository.import_game(imported, imported_snapshots)
    except ValueError as error:
        raise HTTPException(409, str(error)) from error
    engine.games[imported.game_id] = imported
    return {
        "game_id": imported.game_id,
        "source_game_id": state.game_id,
        "scenario_id": imported.scenario_id,
        "scenario_title": imported.scenario_title,
        "turn": imported.turn,
        "phase": imported.phase.value,
        "mode": imported.options.mode,
        "ai_profile": imported.options.ai_profile,
        "battle_report": imported.options.battle_report,
        "realistic_command": imported.options.realistic_command,
        "command_delay_mode": imported.options.command_delay_mode,
    }


@app.get("/games/{game_id}/view")
def view_game(
    game_id: str,
    request: Request,
    x_player_side: Annotated[str | None, Header()] = None,
    debug: bool = False,
):
    state = get_game(game_id)
    if debug and state.options.ruleset_version=="night-v2":
        local_debug(request, True)
    return engine.observe(game_id, side_from_header(x_player_side), debug=debug)


@app.get("/games/{game_id}/legal-actions")
def legal_actions(game_id: str, x_player_side: Annotated[str | None, Header()] = None):
    state = get_game(game_id)
    return engine.legal_actions(game_id, side_from_header(x_player_side))


@app.post("/games/{game_id}/night-preview")
def night_preview(game_id: str, batch: OrderBatch, x_player_side: Annotated[str | None, Header()] = None):
    from . import night, recognition
    state = get_game(game_id)
    side = side_from_header(x_player_side)
    if batch.side != side or state.phase != Phase.GUNNERY or not night.enabled(state):
        raise HTTPException(409, "仅本方新版炮击阶段可预览夜战命令")
    validation = engine.validate_orders(game_id, batch)
    if not validation.valid:
        raise HTTPException(422, validation.errors)
    copied = state.model_copy(deep=True)
    night.prepare_gunnery(engine, copied, [recognition.decode_orders(engine, state, batch)])
    view = engine.observe(game_id, side)
    for ship in view.ships:
        ship.id = recognition.decode_target(engine, state, side, ship.id)
    environment = {**view.environment, **night.observation(engine, copied, side, view.ships, view.recent_events, False)["environment"]}
    environment["effect_notes"] = view.environment.get("effect_notes", {})
    environment["preview"] = True
    return recognition.project_value(engine, state, side, environment)


@app.get("/games/{game_id}/export")
def game_export(game_id: str, x_player_side: Annotated[str | None, Header()] = None):
    """投影一导出：JSONL 世界态帧 + cell-aligned ASCII 棋盘。纯只读，全部从
    `engine.observe` 可见集派生（战争迷雾一致），绝不落盘。"""
    state = get_game(game_id)
    side = side_from_header(x_player_side)
    return {"frame": export_frame(state, engine, side), "board": render_board(state, engine, side)}


@app.get("/games/{game_id}/save")
def download_save(game_id: str):
    """Download the authoritative state plus audit trail and historical snapshots."""
    state = get_game(game_id)
    custom_definition = None
    if state.scenario_id.startswith("IBS-CUSTOM-"):
        try:
            custom_definition = repository.custom_scenario(state.scenario_id)
        except KeyError as error:
            raise HTTPException(409, "该对局的自定义想定定义已丢失，无法生成可移植存档") from error
    try:
        bundle = build_save_bundle(repository, state, custom_definition)
    except (UnicodeError, ValueError) as error:
        raise HTTPException(409, "该存档含旧版损坏快照，未修改原记录；请保留数据库备份后单独修复") from error
    filename = f"iron-bottom-sound-{game_id}.ibs-save.json"
    return Response(
        content=json.dumps(bundle, ensure_ascii=False, separators=(",", ":")),
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.get("/games/{game_id}/replay/checkpoints")
def replay_checkpoints(game_id: str):
    get_game(game_id)
    try:
        snapshots = repository.snapshots(game_id)
    except (KeyError, UnicodeError, ValueError) as error:
        raise HTTPException(404, str(error)) from error
    return [
        {
            "sequence": sequence,
            "turn": snapshot.turn,
            "phase": snapshot.phase.value,
            "event_type": snapshot.events[-1].type if snapshot.events else None,
            "event_message": snapshot.events[-1].message if snapshot.events else None,
        }
        for sequence, snapshot in snapshots
    ]


@app.get("/games/{game_id}/replay")
def replay_view(
    game_id: str,
    sequence: int | None = Query(default=None, ge=0),
    x_player_side: Annotated[str | None, Header()] = None,
):
    get_game(game_id)
    side = side_from_header(x_player_side)
    try:
        checkpoint_sequence, snapshot = repository.snapshot(game_id, sequence)
    except KeyError as error:
        raise HTTPException(404, str(error)) from error
    replay_engine = IronBottomEngine()
    replay_engine.games[game_id] = snapshot
    return {
        "checkpoint_sequence": checkpoint_sequence,
        "view": replay_engine.observe(game_id, side),
    }


@app.get("/games/{game_id}/suggested-orders")
def suggested_orders(
    game_id: str,
    profile: str = "balanced",
    x_player_side: Annotated[str | None, Header()] = None,
):
    """Return an editable, engine-validated starting batch without exposing enemy data.

    profile 选择状态机 AI 风格（内置 PROFILES / 进化冠军 CHAMPIONS，与 ai-opponent 一致）：
    半自动指导——按所选风格生成建议订单，人类在编辑器里确认/手改后再提交。
    """
    state = get_game(game_id)
    side = side_from_header(x_player_side)
    style = CHAMPIONS.get(profile, PROFILES.get(profile))
    if style is None:
        raise HTTPException(422, f"Unknown AI profile {profile}")
    try:
        commander = RealisticCommander(profile=style) if state.options.realistic_command else TacticalCommander(profile=style)
        batch = commander.choose_orders(engine, game_id, side)
        from .tutorials import coach_suggested_orders
        return coach_suggested_orders(state, batch)
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
        commander = RealisticCommander() if state.options.realistic_command else TacticalCommander()
        batch = commander.choose_orders(engine, game_id, Side.ALLIES)
    except ValueError as error:
        raise HTTPException(409, str(error)) from error
    result = engine.submit_orders(game_id, batch)
    if not result.valid:
        raise HTTPException(409, result.errors)
    repository.save(engine.get(game_id))
    return {"valid": True, "instructor_submitted": True}


class AIOpponentRequest(BaseModel):
    profile: str = "adaptive"


class LLMOpponentRequest(BaseModel):
    timeout: float = Field(default=90, gt=0)
    thinking_enabled: bool = False
    api_key: str | None = None  # 用户主动提供的密钥（可省略：优先用开局时注入的）
    config: LLMConnectionConfig | None = None


def _provider_runtime(config: LLMConnectionConfig) -> dict[str, object]:
    runtime = provider_runtime(
        config.provider, config.model, vision_enabled=config.vision_enabled
    )
    return {
        "endpoint": runtime.endpoint,
        "api_key_env": runtime.api_key_env,
        "supports_thinking": runtime.supports_thinking,
        "thinking_required": runtime.thinking_required,
        "supports_vision": runtime.supports_vision,
        "plan_max_tokens": runtime.plan_max_tokens,
    }


def _make_llm_commander(
    timeout: float, thinking_enabled: bool, api_key: str | None = None,
    config: LLMConnectionConfig | None = None,
) -> OpenAICompatibleCommander:
    config = config or LLMConnectionConfig()
    runtime = _provider_runtime(config)
    return OpenAICompatibleCommander(
        timeout=timeout,
        max_tokens=int(runtime["plan_max_tokens"]),
        thinking_enabled=thinking_enabled and bool(runtime["supports_thinking"]),
        api_key=api_key,
        endpoint=str(runtime["endpoint"]),
        api_key_env=str(runtime["api_key_env"]),
        model=config.model,
        vision_enabled=config.vision_enabled,
        supports_thinking=bool(runtime["supports_thinking"]),
        thinking_required=bool(runtime["thinking_required"]),
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
    profile_name = request.profile if request is not None and request.profile else "adaptive"
    profile = CHAMPIONS.get(profile_name, PROFILES.get(profile_name))
    if profile is None:
        raise HTTPException(422, f"Unknown AI profile {profile_name}")
    if player_side.value not in state.submitted_orders:
        raise HTTPException(409, "Submit the player's orders first")
    if ai_side.value in state.submitted_orders:
        return {"valid": True, "ai_submitted": True}
    try:
        commander = RealisticCommander(profile=profile) if state.options.realistic_command else TacticalCommander(profile=profile)
        plan, batch, audits = commander.choose_plan(engine, game_id, ai_side)
    except ValueError as error:
        raise HTTPException(409, str(error)) from error
    result = engine.submit_orders(game_id, batch)
    if not result.valid:
        raise HTTPException(409, result.errors)
    if state.options.battle_report:
        try:
            capture_ai_action(
                repository, game_id, state.turn, state.phase.value, ai_side.value,
                plan, None, audits, state,
            )
        except Exception:
            pass  # 战报失败绝不影响对局
    from .ai_memory import accepted
    accepted(engine, state, ai_side, plan, batch, audits)
    repository.save(state)
    return {"valid": True, "ai_submitted": True}


@app.get("/games/{game_id}/torpedo-tactics")
def torpedo_tactics(
    game_id: str, profile: str = "adaptive",
    x_player_side: Annotated[str | None, Header()] = None,
):
    """Side-filtered, read-only tactical analysis for AI assistance and replay tools."""
    state = get_game(game_id)
    side = side_from_header(x_player_side)
    style = CHAMPIONS.get(profile, PROFILES.get(profile))
    if style is None:
        raise HTTPException(422, f"Unknown AI profile {profile}")
    return AdaptiveTorpedoPlanner(style).analyze(engine, state, side)


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
        "reasoning_preview": None,
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
    # 用户主动提供的配置/密钥（本次请求 > 开局时注入）> 服务器环境变量。
    if state.options.command_delay_mode:
        # Formation policies have already run on their local observations. Do
        # not call the fleet-wide LLM commander, which would bypass that boundary
        # and generate forbidden raw gunnery orders.
        if player_side.value not in state.submitted_orders:
            raise HTTPException(409, "Submit the player's orders first")
        if ai_side.value in state.submitted_orders:
            return {"valid": True, "ai_submitted": True, "audits": []}
        if request is not None and request.api_key:
            _user_llm_keys[game_id] = request.api_key
            if request.config is not None:
                _user_llm_configs[game_id] = request.config
            _register_formation_policies(state, request.api_key, _user_llm_configs.get(game_id))
        plan, batch, audits = RealisticCommander().choose_plan(engine, game_id, ai_side)
        result = engine.submit_orders(game_id, batch)
        if not result.valid:
            raise HTTPException(409, result.errors)
        repository.save(state)
        return {"valid": True, "ai_submitted": True, "audits": []}
    config = (
        request.config if request is not None and request.config is not None
        else _user_llm_configs.get(game_id, LLMConnectionConfig())
    )
    try:
        runtime = _provider_runtime(config)
    except ValueError as error:
        raise HTTPException(422, str(error)) from error
    key = (request.api_key if request is not None else None) or _user_llm_keys.get(game_id)
    if not key and not os.environ.get(str(runtime["api_key_env"])):
        raise HTTPException(503, "请先提供你自己的 LLM API 密钥（开局时或在本次请求中传入 api_key）")
    if player_side.value not in state.submitted_orders:
        raise HTTPException(409, "Submit the player's orders first")
    if ai_side.value in state.submitted_orders:
        return {"valid": True, "ai_submitted": True, "audits": []}
    timeout = request.timeout if request is not None else 90
    thinking = request.thinking_enabled if request is not None else False
    commander = llm_commander_factory(
        timeout=timeout, thinking_enabled=thinking, api_key=key, config=config
    )
    try:
        plan, batch, audits = commander.choose_plan(engine, game_id, ai_side)
    except ValueError as error:
        from .ai_memory import rejected
        rejected(engine, state, ai_side, {"details": getattr(commander, "last_trace", {}),
                                         "error": str(error)[:500]})
        repository.save(state)
        raise HTTPException(409, str(error)) from error
    result = engine.submit_orders(game_id, batch)
    if not result.valid:
        raise HTTPException(409, result.errors)
    if state.options.battle_report:
        try:
            reasoning = None
            capture_ai_action(
                repository, game_id, state.turn, state.phase.value, ai_side.value,
                plan, reasoning, audits, state,
            )
        except Exception:
            pass  # 战报失败绝不影响对局
    from .ai_memory import accepted
    accepted(engine, state, ai_side, plan, batch, audits, getattr(commander, "last_trace", {}))
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


@app.get("/rules/command-delay", response_class=PlainTextResponse)
def command_delay_rules() -> PlainTextResponse:
    """Serve the Command Delay player rules from their single repository source."""
    path = ROOT / "docs" / "rules" / "command-delay.md"
    if not path.exists():
        raise HTTPException(404, "Command Delay rules are not bundled")
    return PlainTextResponse(path.read_text(encoding="utf-8"), media_type="text/markdown")


@app.get("/games/{game_id}/command-delay/fleet-view")
def command_delay_fleet_view(
    game_id: str, x_player_side: Annotated[str | None, Header()] = None,
):
    """The fleet commander's plot: exact only for the formation it is embarked in.

    Every other own-side formation is returned as a *report* with its age, and no
    opposing formation appears at all.  Available only in Command Delay mode.
    """
    state = get_game(game_id)
    side = side_from_header(x_player_side)
    if not state.options.command_delay_mode:
        raise HTTPException(409, "Fleet view is available only in command delay mode")
    from .command_observation import fleet_observation
    return fleet_observation(engine, state, side)


@app.get("/games/{game_id}/command-delay/formation-view/{formation_id}")
def command_delay_formation_view(
    game_id: str, formation_id: str, x_player_side: Annotated[str | None, Header()] = None,
):
    """One formation's local view for its own agent: local contacts only."""
    state = get_game(game_id)
    side = side_from_header(x_player_side)
    if not state.options.command_delay_mode:
        raise HTTPException(409, "Formation view is available only in command delay mode")
    formation = state.formations.get(formation_id)
    if formation is None or formation.side != side:
        raise HTTPException(404, f"Unknown formation {formation_id}")
    from .command_observation import formation_observation
    return formation_observation(engine, state, side, formation_id)


class CommandDelayOrderRequest(BaseModel):
    """舰队总指挥用自然语言写的一道命令。"""
    formation_id: str
    text: str = Field(min_length=1, max_length=400)
    priority_classes: list[str] = Field(default_factory=list, max_length=6)
    roe: list[str] = Field(default_factory=list, max_length=6)
    deadline_turn: int | None = Field(default=None, ge=1, le=200)


@app.post("/games/{game_id}/command-delay/order")
def command_delay_order(
    game_id: str, request: CommandDelayOrderRequest,
    x_player_side: Annotated[str | None, Header()] = None,
):
    """下达一道自然语言命令：它是一项信号，会按通信链路延迟或丢失。"""
    state = get_game(game_id)
    side = side_from_header(x_player_side)
    if not state.options.command_delay_mode:
        raise HTTPException(409, "Orders by signal are available only in command delay mode")
    from .command_delay import draft_natural_order

    try:
        message = draft_natural_order(
            engine, state, side=side, formation_id=request.formation_id,
            text=request.text, priority_classes=request.priority_classes,
            roe=request.roe, deadline_turn=request.deadline_turn,
        )
    except ValueError as error:
        raise HTTPException(422, str(error)) from error
    repository.save(state)
    return {
        "message_id": message.message_id,
        "medium": message.medium.value,
        "handling_delay": message.handling_delay,
        "relay_hops": message.relay_hops,
        "expected_delivery_turn": message.issued_turn + message.handling_delay,
        "route_reason": message.reason,
        "issued_turn": message.issued_turn,
    }


@app.get("/games/{game_id}/command-delay/formation-orders")
def command_delay_formation_orders(
    game_id: str, x_player_side: Annotated[str | None, Header()] = None,
):
    """本侧各编队代理本回合选定的机动方案（提交前给玩家过目）。"""
    state = get_game(game_id)
    side = side_from_header(x_player_side)
    if not state.options.command_delay_mode:
        raise HTTPException(409, "Formation orders are available only in command delay mode")
    from .command_delay import formation_orders

    orders = formation_orders(state, side)
    return {
        "phase": state.phase.value,
        "turn": state.turn,
        "orders": [order.model_dump(mode="json") for order in orders],
    }


@app.get("/games/{game_id}/command-delay/agent-log")
def command_delay_agent_log(
    game_id: str, formation_id: str | None = None, limit: int = 12,
    x_player_side: Annotated[str | None, Header()] = None,
):
    """调试视图：本侧各编队代理的提示词、原始回复、解析结果与记忆。

    只能读自己一侧；对方的提示词与记忆属于其指挥链。
    """
    state = get_game(game_id)
    side = side_from_header(x_player_side)
    if not state.options.command_delay_mode:
        raise HTTPException(409, "The agent log is available only in command delay mode")
    mode = state.command_delay
    if mode is None:
        raise HTTPException(409, "The agent log is available only in command delay mode")
    known = {
        formation.id for formation in state.formations.values() if formation.side == side
    }
    entries = [
        record for record in mode.agent_log
        if record.get("side") == side.value
        and (formation_id is None or record.get("formation_id") == formation_id)
    ]
    payload = []
    for record in entries[-max(1, min(limit, 48)):]:
        formation = state.formations.get(record.get("formation_id") or "")
        payload.append({
            **record,
            "own_formation": (record.get("formation_id") in known),
            "formation_status": formation.status if formation else None,
        })
    memories = {}
    for fid in sorted(known):
        memory = mode.memories.get(fid)
        if memory is not None:
            from .formation_memory import memory_payload

            memories[fid] = memory_payload(memory)
    return {
        "policy_labels": dict(mode.policy_labels),
        "formations": sorted(known),
        "memories": memories,
        "entries": payload,
    }


@app.post("/games/{game_id}/formation-preview")
def formation_preview(game_id: str, request: FormationPreviewRequest, x_player_side: Annotated[str | None, Header()] = None):
    """Validate an editable formation setup without mutating or exposing the opponent."""
    state = get_game(game_id)
    side = side_from_header(x_player_side)
    if not state.options.realistic_command or state.phase != Phase.FORMATION_SETUP:
        raise HTTPException(409, "Formation preview is available only during realistic setup")
    batch = OrderBatch(side=side, phase=state.phase, formation_setup=request.formations)
    errors = validate_setup(engine, state, batch)
    return {"valid": not errors, "errors": errors}


@app.get("/games/{game_id}/movement-style-options")
def movement_style_options(
    game_id: str, x_player_side: Annotated[str | None, Header()] = None,
):
    """每种机动方式的当前可用性，附引擎给出的原因（真实模式与命令延迟模式通用）。

    此处返回的原因与展开器稍后执行的是同一次判定，因此界面显示的就是将会被执行的。
    """
    state = get_game(game_id)
    side = side_from_header(x_player_side)
    if not state.options.realistic_command:
        raise HTTPException(409, "Movement styles are available only in realistic or command delay mode")
    from .formation_maneuver import movement_style_options as options

    return {
        "phase": state.phase.value,
        "turn": state.turn,
        "styles": ["follow_wake", "move_together"],
        "formations": options(engine, state, side),
    }


@app.post("/games/{game_id}/formation-movement-preview")
def formation_movement_preview(game_id: str, request: FormationMovementPreviewRequest, x_player_side: Annotated[str | None, Header()] = None):
    """Expand leader orders to private per-ship trajectories without saving them."""
    state = get_game(game_id)
    side = side_from_header(x_player_side)
    if not state.options.realistic_command or state.phase != Phase.MOVEMENT_PLANNING:
        raise HTTPException(409, "Formation movement preview is available only during realistic movement")
    batch = OrderBatch(side=side, phase=state.phase, formation_movement=request.formations)
    prepared, errors, detach_ids = expand_movement_orders(engine, state, batch)
    return {
        "valid": not errors,
        "errors": errors,
        "detach_ship_ids": detach_ids,
        **engine.movement_plan_trajectories(
            state, side, [order.model_dump(mode="json") for order in prepared.movement]
        ),
    }


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
def sealed_trajectories(game_id: str, request: Request, x_player_side: Annotated[str | None, Header()] = None, debug: bool = False):
    """Replay this turn's sealed movement plans as trajectories (kept visible during
    torpedo planning). Own side always; enemy plans only when debug=true."""
    state = get_game(game_id)
    if debug and state.options.ruleset_version == "night-v2":
        local_debug(request, True)
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
    try:
        return engine.torpedo_assist(state, side, target_id=request.target_id, launch=request.launch)
    except ValueError as error:
        raise HTTPException(422, str(error)) from error


@app.post("/games/{game_id}/field-of-fire")
def field_of_fire(game_id: str, request: FieldOfFireRequest | None = None, x_player_side: Annotated[str | None, Header()] = None):
    """Pure read-only field-of-fire heatmap overlay (both sides, or one ship via body.ship_id); never saves."""
    state = get_game(game_id)
    try:
        return engine.field_of_fire_heatmap(
            state, side_from_header(x_player_side),
            ship_id=request.ship_id if request else None,
            target_speed=request.target_speed if request else 4,
        )
    except ValueError as error:
        raise HTTPException(422, str(error)) from error


@app.post("/games/{game_id}/gunnery-assist")
def gunnery_assist(game_id: str, request: GunneryAssistRequest, x_player_side: Annotated[str | None, Header()] = None):
    """Pure read-only gunnery scheduling recommendation (most mounts, best modifier, spread); never saves."""
    state = get_game(game_id)
    side = side_from_header(x_player_side)
    if state.phase != Phase.GUNNERY:
        raise HTTPException(409, "Gunnery assist is available only during gunnery")
    try:
        return engine.gunnery_assist(state, side, assigned=request.assigned)
    except ValueError as error:
        raise HTTPException(422, str(error)) from error


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
            config = _user_llm_configs.get(game_id, LLMConnectionConfig())
            runtime = _provider_runtime(config)
            commander = (
                OpenAICompatibleCommander(
                    api_key=key, timeout=30, max_tokens=800, model=config.model,
                    endpoint=str(runtime["endpoint"]),
                    api_key_env=str(runtime["api_key_env"]),
                    supports_thinking=bool(runtime["supports_thinking"]),
                    thinking_required=bool(runtime["thinking_required"]),
                )
                if key or game_id in _user_llm_configs else narrative_commander_factory()
            )
            capture_after_advance(repository, reports_root, next_state, engine,
                                  prev_phase, commander=commander)
        except Exception:
            pass  # 战报失败绝不影响对局
    repository.save(next_state)
    return engine.public_events(next_state, side, events)


@app.get("/games/{game_id}/events")
def events(game_id: str, after: int = Query(default=0, ge=0), x_player_side: Annotated[str | None, Header()] = None):
    state = get_game(game_id)
    side = side_from_header(x_player_side)
    return engine.public_events(state, side, [e for e in state.events if e.sequence > after])


def _report_entries(game_id: str) -> list[dict]:
    """battle_report 表行 → dict（build_report_data 输入格式）。"""
    return [entry.model_dump(mode="json") for entry in repository.battle_entries(game_id)]


@app.get("/games/{game_id}/battle-report")
def battle_report(game_id: str):
    """战报 JSON（中立历史文档，无需 side 头）。纯只读，不参与裁决。"""
    state = get_game(game_id)
    if state.options.ruleset_version == "night-v2" and state.phase != Phase.COMPLETE:
        raise HTTPException(409, "完整双方战报在对局结束后开放；局内请使用事件、双方战损或显式本地 AI 调试")
    return build_report_data(state, engine, _report_entries(game_id))


@app.get("/games/{game_id}/battle-report/image/{rel_path:path}")
def battle_report_image(game_id: str, rel_path: str):
    """返回战报截图 PNG。路径穿越守卫：解析后必须落在该局的报告目录内。"""
    state = get_game(game_id)
    if state.options.ruleset_version == "night-v2" and state.phase != Phase.COMPLETE:
        raise HTTPException(409, "完整双方战报在对局结束后开放")
    base = (Path(reports_root) / game_id).resolve()
    target = (base / rel_path).resolve()
    if not target.is_relative_to(base) or not target.is_file():
        raise HTTPException(404, "Not found")
    return FileResponse(str(target), media_type="image/png")


@app.get("/games/{game_id}/battle-report.md")
def battle_report_markdown(game_id: str):
    """自包含 MD 战报下载（截图以 base64 内嵌，可直接分享）。"""
    state = get_game(game_id)
    if state.options.ruleset_version == "night-v2" and state.phase != Phase.COMPLETE:
        raise HTTPException(409, "完整双方战报在对局结束后开放")
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
