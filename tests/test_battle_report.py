"""战报系统测试：几何/渲染迷雾/捕获持久化/回合叙事/LLM 路径/回退/Markdown/API/无泄漏/match。

- conftest autouse 删 DEEPSEEK_API_KEY 并把 api.reports_root 指 tmp → 无真实网络、无仓库污染。
- API 测试用 TestClient 打真实端点（战报钩子随 advance 运行）；渲染/迷雾测试直接驱动引擎。
"""

import json
import math
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

from iron_bottom_sound import api, battle_report as br
from iron_bottom_sound.api import app
from iron_bottom_sound.engine import IronBottomEngine
from iron_bottom_sound.llm import OpenAICompatibleCommander
from iron_bottom_sound.match import run_match
from iron_bottom_sound.models import (
    AIPlanSheet,
    GameOptions,
    HexCoord,
    LLMCallAudit,
    OptionalRules,
    OrderBatch,
    Phase,
    Side,
)
from iron_bottom_sound.storage import GameRepository

_ORDER_PHASES = {"reinforcement", "movement_planning", "torpedo_planning", "gunnery"}


def _engine_and_state(seed: int = 1, options: GameOptions | None = None):
    engine = IronBottomEngine()
    state = engine.reset("IBS-S-03", seed, options)
    return engine, state


def _create_battle_report_game(client: TestClient, seed: int = 31) -> str:
    created = client.post(
        "/games",
        json={
            "scenario_id": "IBS-S-03", "seed": seed,
            "options": {"mode": "hotseat", "battle_report": True},
        },
    )
    assert created.status_code == 201, created.text
    return created.json()["game_id"]


def _play_until_turn(client: TestClient, game_id: str, turn: int, max_iters: int = 40) -> dict:
    """打牌到 view.turn >= turn（含自动阶段；每阶段推进一次）。"""
    for _ in range(max_iters):
        view = client.get(f"/games/{game_id}/view", headers={"X-Player-Side": "axis"}).json()
        if view["phase"] == "complete" or view["turn"] >= turn:
            return view
        if view["phase"] in _ORDER_PHASES:
            for side in ("axis", "allies"):
                suggestion = client.get(
                    f"/games/{game_id}/suggested-orders", headers={"X-Player-Side": side}
                )
                assert suggestion.status_code == 200, suggestion.text
                response = client.post(
                    f"/games/{game_id}/orders",
                    headers={"X-Player-Side": side}, json=suggestion.json(),
                )
                assert response.status_code == 200, response.text
        advance = client.post(f"/games/{game_id}/advance", headers={"X-Player-Side": "axis"})
        assert advance.status_code == 200, advance.text
    raise AssertionError(f"did not reach turn {turn}")


# ---------------------------------------------------------------------------
# 几何（与前端 hexGeometry 一致）。
# ---------------------------------------------------------------------------
def test_hex_geometry_matches_frontend() -> None:
    assert br.hex_center(0, 0) == (94.0, 79.0)
    x, y = br.hex_center(1, 0)
    assert x == pytest.approx(130.0)
    assert y == pytest.approx(79.0 + 24 * math.sqrt(3) / 2)  # B1 = A1 + (36, √3·24/2)
    # 与前端 hexCenter 逐字一致：第二参数是轴向行 r（不是显示行），任意列都成立。
    # 旧实现按显示行解释 r，缺 floor(q/2) 行 → 东侧舰船整体偏高（回归守卫）。
    for q, r in [(0, 0), (1, 0), (6, 7), (16, 7), (17, 7), (28, 2), (33, 10)]:
        x, y = br.hex_center(q, r)
        assert x == pytest.approx(94.0 + q * 24 * 1.5)
        assert y == pytest.approx(79.0 + (r + q / 2) * 24 * math.sqrt(3))
    # 标签往返：R16（q17，轴向 r7）落在显示行 16 的中心，CC17 落在显示行 17。
    r16 = HexCoord.from_label("R16")
    _, y16 = br.hex_center(r16.q, r16.r)
    assert y16 == pytest.approx(79.0 + 15.5 * 24 * math.sqrt(3))
    cc17 = HexCoord.from_label("CC17")
    _, ycc = br.hex_center(cc17.q, cc17.r)
    assert ycc == pytest.approx(79.0 + 16 * 24 * math.sqrt(3))
    cx, cy = br.hex_center(0, 0)
    vertices = br.hex_vertices(0, 0)
    assert len(vertices) == 6
    for vx, vy in vertices:
        assert math.hypot(vx - cx, vy - cy) == pytest.approx(24)  # HEX_SIZE=外接圆半径


# ---------------------------------------------------------------------------
# 渲染 / 迷雾。
# ---------------------------------------------------------------------------
def test_render_map_image_size_and_sides_differ() -> None:
    engine, state = _engine_and_state()
    axis = br.render_map_image(state, engine, Side.AXIS)
    allies = br.render_map_image(state, engine, Side.ALLIES)
    assert axis.size == (br.IMAGE_WIDTH, br.IMAGE_HEIGHT)
    assert axis.mode == "RGB"
    assert axis.tobytes() != allies.tobytes()  # 双方视角不同


def test_render_is_purely_observation_driven() -> None:
    engine, state = _engine_and_state()
    ship = next(s for s in state.ships.values() if s.position is not None)
    img1 = br.render_map_image(state, engine, Side.AXIS)
    ship.hull = ship.max_hull  # 私有字段：健康（不跨 0.35 残血阈值）→ 渲染不变
    assert br.render_map_image(state, engine, Side.AXIS).tobytes() == img1.tobytes()
    ship.heading = (ship.heading % 6) + 1  # 公开字段：航向 → 渲染必变
    assert br.render_map_image(state, engine, Side.AXIS).tobytes() != img1.tobytes()


def test_hidden_damage_hides_enemy_cripple_star() -> None:
    options = GameOptions(optional_rules=OptionalRules(hidden_damage=True))
    engine, state = _engine_and_state(options=options)
    ally = next(s for s in state.ships.values() if s.side == Side.ALLIES)
    ally.hull = 1  # 敌方残血
    axis_obs = engine.observe(state.game_id, Side.AXIS)
    ally_obs = next(s for s in axis_obs.ships if s.id == ally.id)
    assert ally_obs.hull is None  # 迷雾：敌方血量不可见
    grid, _, _ = br._board_cells(state, engine, Side.AXIS)
    assert not any("*" in token for row in grid for token in row)  # 不画敌方残血星
    # 关闭隐藏损伤后同一局面应显示残血星
    state.options.optional_rules.hidden_damage = False
    grid2, _, _ = br._board_cells(state, engine, Side.AXIS)
    assert any("*" in token for row in grid2 for token in row)


# ---------------------------------------------------------------------------
# 存储层幂等。
# ---------------------------------------------------------------------------
def test_save_battle_entry_replace_is_idempotent(tmp_path) -> None:
    repository = GameRepository(tmp_path / "r.sqlite3")
    try:
        repository.save_battle_entry("g1", 5, 1, "reinforcement", "axis", "capture", image_path="p.png")
        repository.save_battle_entry("g1", 5, 1, "reinforcement", "axis", "capture", image_path="p.png")
        assert len(repository.battle_entries("g1")) == 1
    finally:
        repository.close()


def test_battle_narrative_exists_gate(tmp_path) -> None:
    repository = GameRepository(tmp_path / "r.sqlite3")
    try:
        assert repository.battle_narrative_exists("g1", 1) is False
        repository.save_battle_entry("g1", 10, 1, "summary", "both", "narrative", content="x")
        assert repository.battle_narrative_exists("g1", 1) is True
        assert repository.battle_narrative_exists("g1", 1, "gunnery") is False
    finally:
        repository.close()


# ---------------------------------------------------------------------------
# 捕获持久化 + 回合叙事（真实 API 钩子）。
# ---------------------------------------------------------------------------
def test_create_captures_initial_and_advance_persists() -> None:
    client = TestClient(app)
    game_id = _create_battle_report_game(client)
    entries = api.repository.battle_entries(game_id)
    assert len(entries) == 2  # 开局双视角
    assert all(entry.kind == "capture" for entry in entries)
    assert {entry.side for entry in entries} == {"axis", "allies"}
    for entry in entries:
        png = Path(api.reports_root) / game_id / entry.image_path
        assert png.is_file()
        assert png.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"

    _play_until_turn(client, game_id, 2)
    entries = api.repository.battle_entries(game_id)
    captures = [entry for entry in entries if entry.kind == "capture"]
    assert len(captures) >= 14  # 至少 7 个结算后阶段 × 2 侧
    narratives = [entry for entry in entries if entry.kind == "narrative"]
    summaries = [entry for entry in narratives if entry.phase == "summary"]
    assert len(summaries) == 1 and summaries[0].turn == 1
    assert "第 1 回合" in summaries[0].content  # 无密钥 → 确定性回退
    # 每个阶段都有文字叙述（含自动阶段），且阶段叙述与回合总结分开落库。
    phase_narratives = [entry for entry in narratives if entry.phase != "summary"]
    assert len(phase_narratives) >= 3
    assert any("第 1 回合" in entry.content for entry in phase_narratives)
    assert {entry.phase for entry in phase_narratives} <= set(br.PHASE_ORDER)


def test_battle_report_off_writes_nothing() -> None:
    client = TestClient(app)
    created = client.post("/games", json={"scenario_id": "IBS-S-03", "seed": 41}).json()
    game_id = created["game_id"]
    assert api.repository.battle_entries(game_id) == []
    data = client.get(f"/games/{game_id}/battle-report").json()
    assert data["meta"]["turn"] == 1
    assert not any(turn["phases"] for turn in data["turns"])


# ---------------------------------------------------------------------------
# 叙事：回退 / LLM 路径。
# ---------------------------------------------------------------------------
class BrokenCommander:
    def write_narrative(self, system, user):
        raise RuntimeError("boom")


def test_write_turn_narrative_falls_back_on_commander_failure() -> None:
    engine, state = _engine_and_state()
    for side in Side:
        assert engine.submit_orders(
            state.game_id, OrderBatch(side=side, phase=Phase.REINFORCEMENT)
        ).valid
    engine.advance(state.game_id)
    narrative = br.write_turn_narrative(state, engine, 1, BrokenCommander())
    assert "第 1 回合" in narrative
    assert "比分" in narrative


def test_write_narrative_raises_without_key(monkeypatch) -> None:
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    with pytest.raises(RuntimeError):
        OpenAICompatibleCommander().write_narrative("sys", "user")


def test_narrative_llm_path_no_response_format_and_no_leak(monkeypatch) -> None:
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-only-placeholder")
    captured: dict = {}
    fixed = "黎明前，两支舰队在铁底湾水道交错。"

    def handler(request: httpx.Request) -> httpx.Response:
        captured["payload"] = json.loads(request.content)
        return httpx.Response(
            200, json={"id": "n1", "choices": [{"message": {"content": fixed}}], "usage": {}},
        )

    commander = OpenAICompatibleCommander(
        client=httpx.Client(transport=httpx.MockTransport(handler)),
        timeout=30, max_tokens=800,
    )
    monkeypatch.setattr(api, "narrative_commander_factory", lambda: commander)

    client = TestClient(app)
    game_id = _create_battle_report_game(client)
    _play_until_turn(client, game_id, 2)

    payload = captured["payload"]
    assert "response_format" not in payload  # 纯文本，非 JSON 对象
    assert payload["temperature"] == 0.7
    assert payload["max_tokens"] == 800
    user = payload["messages"][1]["content"]
    assert "orders_submitted" not in user
    assert "submitted" not in user and "order_batch" not in user  # 不喂私有订单
    narratives = [entry for entry in api.repository.battle_entries(game_id) if entry.kind == "narrative"]
    # 每阶段一段 + 回合总结，mock 恒定文本 → 全部等于 fixed。
    assert len(narratives) > 1
    assert all(entry.content == fixed for entry in narratives)
    assert any(entry.phase == "summary" for entry in narratives)
    assert any(entry.phase in br.PHASE_ORDER for entry in narratives)


def test_public_events_exclude_orders_submitted() -> None:
    engine, state = _engine_and_state()
    for side in Side:
        engine.submit_orders(state.game_id, OrderBatch(side=side, phase=Phase.REINFORCEMENT))
    engine.advance(state.game_id)
    events = br.public_events_for_turn(state, engine, 1)
    assert all(event.type not in {"orders_submitted", "phase_changed", "game_created"} for event in events)
    _, user = br.build_narrative_prompt(state, engine, 1)
    assert "orders_submitted" not in user and "submitted" not in user


# ---------------------------------------------------------------------------
# Markdown / API 端点。
# ---------------------------------------------------------------------------
def test_battle_report_md_self_contained() -> None:
    client = TestClient(app)
    game_id = _create_battle_report_game(client)
    _play_until_turn(client, game_id, 2)
    captures = [entry for entry in api.repository.battle_entries(game_id) if entry.kind == "capture"]

    response = client.get(f"/games/{game_id}/battle-report.md")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/markdown")
    assert "attachment" in response.headers.get("content-disposition", "")
    body = response.text
    # UTF-8 带 BOM：中文 Windows 编辑器才不会误判成 GBK 显示乱码。
    assert response.content.startswith(b"\xef\xbb\xbf")
    assert body.startswith("﻿")
    assert "# 铁底湾的回响 IV" in body
    narrative = next(
        entry.content for entry in api.repository.battle_entries(game_id) if entry.kind == "narrative"
    )
    assert narrative in body
    assert body.count("data:image/png;base64,") == len(captures)


def test_battle_report_json_shape_and_image_endpoint() -> None:
    client = TestClient(app)
    game_id = _create_battle_report_game(client)
    _play_until_turn(client, game_id, 2)

    data = client.get(f"/games/{game_id}/battle-report").json()
    assert data["meta"]["game_id"] == game_id
    assert data["meta"]["mode"] == "hotseat"
    assert data["meta"]["turn"] >= 2
    assert len(data["turns"]) == data["meta"]["turn"]
    turn1 = data["turns"][0]
    assert turn1["narrative"]
    assert turn1["phases"]
    for phase in turn1["phases"]:
        assert len(phase["captures"]) >= 2  # 开局快照 + 结算后快照
        assert {cap["side"] for cap in phase["captures"]} == {"axis", "allies"}
        for cap in phase["captures"]:
            assert cap["image_path"]
        assert phase["narrative"]  # 每阶段都有文字
        assert phase["ai_actions"] == {}  # 纯热座局无 AI 计划表
    for event in turn1["events"]:
        assert set(event) <= {"sequence", "phase", "type", "message"}  # 不携带私有 payload

    img_path = turn1["phases"][0]["captures"][0]["image_path"]
    image = client.get(f"/games/{game_id}/battle-report/image/{img_path}")
    assert image.status_code == 200
    assert image.headers["content-type"] == "image/png"
    assert image.content[:8] == b"\x89PNG\r\n\x1a\n"


def test_battle_report_image_path_traversal_blocked() -> None:
    client = TestClient(app)
    game_id = _create_battle_report_game(client)
    for bad in ("../iron-bottom-sound.sqlite3", "..%2F..%2F..%2Fetc%2Fpasswd", "../../../../Windows/win.ini"):
        response = client.get(f"/games/{game_id}/battle-report/image/{bad}")
        assert response.status_code == 404, bad


# ---------------------------------------------------------------------------
# AI-vs-AI（match.py）。
# ---------------------------------------------------------------------------
def test_match_battle_report_artifacts_and_default_off(tmp_path) -> None:
    artifact = tmp_path / "match"
    report, _, _ = run_match("IBS-S-03", seed=5, artifact_dir=artifact, battle_report=True)
    md = artifact / f"{report.game_id}-battle-report.md"
    assert md.is_file()
    data = json.loads((artifact / f"{report.game_id}-battle-report.json").read_text(encoding="utf-8"))
    assert data["meta"]["game_id"] == report.game_id
    assert any(turn["narrative"] for turn in data["turns"])
    assert list(artifact.glob(f"{report.game_id}/*.png"))  # 每阶段双视角 PNG 落盘
    md_text = md.read_text(encoding="utf-8")
    assert md_text.startswith("﻿")  # UTF-8 带 BOM，编辑器才不会误判 GBK 乱码
    assert "data:image/png;base64," in md_text
    # 对战战报已嵌入双方 AI 计划表（match.py run_match 调 capture_ai_action）：
    # 含订单的阶段都有 axis+allies 的 ai_action，plan 带态势判断；战术司令无思考（reasoning=None）。
    actions = [
        (phase["phase"], side, action)
        for turn in data["turns"] for phase in turn["phases"]
        for side, action in phase["ai_actions"].items()
    ]
    assert actions
    assert {side for _, side, _ in actions} == {"axis", "allies"}
    assert all(action["plan"].get("situation_summary") for _, _, action in actions)
    assert all(action["reasoning"] is None for _, _, action in actions)
    assert "计划表" in md_text

    artifact_off = tmp_path / "match-off"
    run_match("IBS-S-03", seed=5, artifact_dir=artifact_off, battle_report=False)
    assert not list(artifact_off.glob("*-battle-report.md"))


# ---------------------------------------------------------------------------
# AI 计划表（capture_ai_action）+ 渲染器注入。
# ---------------------------------------------------------------------------
def test_capture_ai_action_persists_plan_and_reasoning(tmp_path) -> None:
    repository = GameRepository(tmp_path / "r.sqlite3")
    engine, state = _engine_and_state()
    ship_id = next(iter(state.ships))
    batch = OrderBatch(side=Side.AXIS, phase=Phase.REINFORCEMENT)
    plan = AIPlanSheet(
        turn=1, phase=Phase.REINFORCEMENT, situation_summary="确认无增援",
        phase_goal="确认阶段", unit_intents={ship_id: "保持阵位"},
        orders=batch.model_dump(mode="json"), contingency=["入口被占则顺延"],
    )
    entry = br.capture_ai_action(
        repository, state.game_id, 1, "reinforcement", "axis",
        plan, reasoning="先评估入口格，本回合无增援。", audits=[], state=state,
    )
    assert entry is not None and entry["kind"] == "ai_action"
    assert state.ships[ship_id].name in entry["content"]  # 单元意图已映射为舰名

    data = br.build_report_data(state, engine, repository.battle_entries(state.game_id))
    turn1 = data["turns"][0]
    phase = next(p for p in turn1["phases"] if p["phase"] == "reinforcement")
    ai = phase["ai_actions"]["axis"]
    assert ai["plan"]["situation_summary"] == "确认无增援"
    assert ai["plan"]["unit_intents"]
    assert ai["reasoning"] == "先评估入口格，本回合无增援。"
    assert ai["model"] == "unknown"


def test_capture_ai_action_idempotent_replaces(tmp_path) -> None:
    repository = GameRepository(tmp_path / "r.sqlite3")
    engine, state = _engine_and_state()
    batch = OrderBatch(side=Side.AXIS, phase=Phase.REINFORCEMENT)
    plan = AIPlanSheet(turn=1, phase=Phase.REINFORCEMENT, situation_summary="v1",
                       phase_goal="确认", orders=batch.model_dump(mode="json"))
    br.capture_ai_action(repository, state.game_id, 1, "reinforcement", "axis", plan, "r1")
    plan2 = plan.model_copy(update={"situation_summary": "v2"})
    br.capture_ai_action(repository, state.game_id, 1, "reinforcement", "axis", plan2, "r2")
    entries = repository.battle_entries(state.game_id)
    assert len([entry for entry in entries if entry.kind == "ai_action"]) == 1
    data = br.build_report_data(state, engine, entries)
    phase = next(p for p in data["turns"][0]["phases"] if p["phase"] == "reinforcement")
    assert phase["ai_actions"]["axis"]["plan"]["situation_summary"] == "v2"


def test_capture_phase_snapshot_uses_renderer_injection(tmp_path) -> None:
    repository = GameRepository(tmp_path / "r.sqlite3")
    engine, state = _engine_and_state()
    written: dict[str, str] = {}

    def fake_renderer(state, engine, side, path) -> None:
        written[side.value] = str(path)
        path.write_bytes(b"UI-PNG")

    entries = br.capture_phase_snapshot(
        repository, tmp_path / "reports", state, engine, 1, "gunnery",
        sequence=7, renderer=fake_renderer,
    )
    assert {entry["side"] for entry in entries} == {"axis", "allies"}
    assert written["axis"] and written["allies"]
    for entry in entries:
        png = tmp_path / "reports" / state.game_id / entry["image_path"]
        assert png.read_bytes() == b"UI-PNG"


def test_markdown_contains_plan_table_and_reasoning(tmp_path) -> None:
    repository = GameRepository(tmp_path / "r.sqlite3")
    engine, state = _engine_and_state()
    for side, model, reasoning in [
        (Side.AXIS, "evolved", None),
        (Side.ALLIES, "deepseek-v4-pro", "先评估入口格，再确认无增援，选保守动作。"),
    ]:
        batch = OrderBatch(side=side, phase=Phase.REINFORCEMENT)
        plan = AIPlanSheet(turn=1, phase=Phase.REINFORCEMENT, situation_summary="确认无增援",
                           phase_goal="确认阶段", orders=batch.model_dump(mode="json"))
        audits = [LLMCallAudit(
            side=side, turn=1, phase=Phase.REINFORCEMENT, attempt=1,
            model=model, elapsed_ms=5, valid=True,
        )]
        br.capture_ai_action(repository, state.game_id, 1, "reinforcement", side.value,
                             plan, reasoning, audits=audits)
    br.capture_phase_snapshot(repository, tmp_path / "reports", state, engine, 1, "reinforcement")
    data = br.build_report_data(state, engine, repository.battle_entries(state.game_id))
    md = br.build_report_markdown(tmp_path / "reports", data, state.game_id)
    assert "**轴心计划表**" in md and "**同盟计划表**" in md
    assert "deepseek-v4-pro" in md
    assert "**同盟思考过程**" in md and "先评估入口格" in md
    assert "| 态势判断 | 确认无增援 |" in md
    assert "第 1 回合" in md
