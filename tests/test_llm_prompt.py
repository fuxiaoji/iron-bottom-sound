"""LLM 提示词工程测试：棋盘/世界态帧/few-shot/反过度思考纪律/推理采集。

全部用 MockTransport 捕获实际发给 DeepSeek 的 payload，断言 prompt 结构与
few-shot 占位符纪律，绝不发出真实 HTTP 请求。
"""

import json

import httpx

from iron_bottom_sound.engine import IronBottomEngine
from iron_bottom_sound.llm import OpenAICompatibleCommander
from iron_bottom_sound.models import (
    AIPlanSheet,
    GameOptions,
    OptionalRules,
    OrderBatch,
    Phase,
    Side,
)


def _valid_plan(turn: int = 1, phase: Phase = Phase.REINFORCEMENT, side: Side = Side.AXIS) -> AIPlanSheet:
    batch = OrderBatch(side=side, phase=phase)
    return AIPlanSheet(
        turn=turn, phase=phase, situation_summary="己方无增援。", phase_goal="确认阶段",
        orders=batch.model_dump(mode="json"),
    )


def _commander(handler, **kwargs) -> OpenAICompatibleCommander:
    client = httpx.Client(transport=httpx.MockTransport(handler))
    return OpenAICompatibleCommander(client=client, **kwargs)


def _captured_prompt(request_payload: dict) -> dict:
    payload = json.loads(request_payload["messages"][1]["content"])
    assert "board" in payload and "world_state" in payload
    return payload


def _mock_once(captured: dict, plan: AIPlanSheet, reasoning: str | None = None):
    def handler(request: httpx.Request) -> httpx.Response:
        captured["payload"] = json.loads(request.content)
        message = {"content": plan.model_dump_json()}
        if reasoning is not None:
            message["reasoning_content"] = reasoning
        return httpx.Response(
            200, json={"id": "r1", "choices": [{"message": message}], "usage": {}},
        )
    return handler


def test_prompt_contains_board_frame_schema_and_discipline(monkeypatch) -> None:
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-only-placeholder")
    captured: dict = {}
    engine = IronBottomEngine()
    state = engine.reset("IBS-S-03", 1)
    _commander(_mock_once(captured, _valid_plan())).choose_plan(engine, state.game_id, Side.AXIS)
    system = captured["payload"]["messages"][0]["content"]
    assert "【思考纪律】" in system
    assert "六角格轴向距离" in system and "|Δq|" in system
    assert "SAMPLE-" in system  # 照抄占位符会被引擎判非法
    prompt = _captured_prompt(captured["payload"])
    assert "legal_actions" in prompt
    assert "order_batch_json_schema" in prompt and "plan_sheet_json_schema" in prompt
    assert "A  B  C" in prompt["board"]
    assert "..=海" in prompt["board"]
    karl = next(s for s in prompt["world_state"]["ships"] if s["side"] == "axis")
    assert karl["id"].startswith("IBS-U-") and karl["hex"] == "O14"


def test_few_shot_uses_only_sample_placeholders(monkeypatch) -> None:
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-only-placeholder")
    captured: dict = {}
    engine = IronBottomEngine()
    state = engine.reset("IBS-S-03", 1)
    _commander(_mock_once(captured, _valid_plan())).choose_plan(engine, state.game_id, Side.AXIS)
    prompt = _captured_prompt(captured["payload"])
    example = json.dumps(prompt["few_shot_example_output"], ensure_ascii=False)
    assert "SAMPLE-" in example
    assert "IBS-U-" not in example  # 不把真实 id 塞进示范，防止照抄


def test_few_shot_injects_current_turn_phase_and_side(monkeypatch) -> None:
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-only-placeholder")
    captured: dict = {}
    engine = IronBottomEngine()
    state = engine.reset("IBS-S-03", 1)
    state.turn = 3  # 模板写死 turn=1，注入必须覆盖为当前值
    _commander(_mock_once(captured, _valid_plan(turn=3, side=Side.ALLIES))).choose_plan(
        engine, state.game_id, Side.ALLIES
    )
    prompt = _captured_prompt(captured["payload"])
    example = prompt["few_shot_example_output"]
    assert example["turn"] == 3 and example["phase"] == "reinforcement"
    assert example["orders"]["side"] == "allies"


def test_reasoning_preview_none_when_absent(monkeypatch) -> None:
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-only-placeholder")
    captured: dict = {}
    engine = IronBottomEngine()
    state = engine.reset("IBS-S-03", 1)
    _, _, audits = _commander(_mock_once(captured, _valid_plan())).choose_plan(
        engine, state.game_id, Side.AXIS
    )
    assert audits[-1].reasoning_preview is None


def test_default_payload_thinking_disabled_and_max_tokens_2400(monkeypatch) -> None:
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-only-placeholder")
    captured: dict = {}
    engine = IronBottomEngine()
    state = engine.reset("IBS-S-03", 1)
    _commander(_mock_once(captured, _valid_plan())).choose_plan(engine, state.game_id, Side.AXIS)
    payload = captured["payload"]
    assert payload["thinking"] == {"type": "disabled"}
    assert payload["max_tokens"] == 2400
    assert "reasoning_effort" not in payload


def test_prompt_leaks_no_enemy_private_damage(monkeypatch) -> None:
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-only-placeholder")
    captured: dict = {}
    options = GameOptions(mode="llm", optional_rules=OptionalRules(hidden_damage=True))
    engine = IronBottomEngine()
    state = engine.reset("IBS-S-03", 1, options)
    _commander(_mock_once(captured, _valid_plan())).choose_plan(engine, state.game_id, Side.AXIS)
    prompt = _captured_prompt(captured["payload"])
    for ship in prompt["world_state"]["ships"]:
        if ship["side"] == "allies":
            # 隐藏损伤下敌舰血量/炮数一律 None，不泄露私有状态
            assert ship["hull"] is None and ship["guns_usable"] is None
