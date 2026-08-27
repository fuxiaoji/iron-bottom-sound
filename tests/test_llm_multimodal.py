"""Multimodal LLM contract: side-filtered PNG + provider-neutral OpenAI payload."""

from __future__ import annotations

import base64
import json
from io import BytesIO

import httpx
from PIL import Image

from iron_bottom_sound.api import LLMConnectionConfig, _make_llm_commander
from iron_bottom_sound.engine import IronBottomEngine
from iron_bottom_sound.llm import OpenAICompatibleCommander
from iron_bottom_sound.models import AIPlanSheet, OrderBatch, Phase, Side


def _valid_plan(side: Side) -> AIPlanSheet:
    batch = OrderBatch(side=side, phase=Phase.REINFORCEMENT)
    return AIPlanSheet(
        turn=1,
        phase=Phase.REINFORCEMENT,
        situation_summary="无增援，确认阶段。",
        phase_goal="合法确认",
        orders=batch.model_dump(mode="json"),
    )


def test_zhipu_vision_payload_contains_filtered_png_and_no_deepseek_fields() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json={
            "id": "zhipu-test-request",
            "choices": [{"message": {"content": _valid_plan(Side.AXIS).model_dump_json()}}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5},
        })

    engine = IronBottomEngine()
    state = engine.reset("IBS-S-03", 1)
    client = httpx.Client(transport=httpx.MockTransport(handler))
    commander = OpenAICompatibleCommander(
        endpoint="https://open.bigmodel.cn/api/paas/v4",
        model="glm-5.3-flash",
        api_key="runtime-only-placeholder",
        vision_enabled=True,
        supports_thinking=False,
        client=client,
    )
    plan, batch, audits = commander.choose_plan(engine, state.game_id, Side.AXIS)

    assert plan.turn == 1 and batch.side == Side.AXIS and audits[-1].valid
    request = requests[-1]
    assert str(request.url) == "https://open.bigmodel.cn/api/paas/v4/chat/completions"
    payload = json.loads(request.content)
    assert payload["model"] == "glm-5.3-flash"
    assert "thinking" not in payload and "reasoning_effort" not in payload
    content = payload["messages"][-1]["content"]
    assert [part["type"] for part in content] == ["text", "image_url"]
    prompt = json.loads(content[0]["text"])
    assert prompt["world_state"]["side"] == "axis"
    image_url = content[1]["image_url"]["url"]
    assert image_url.startswith("data:image/png;base64,")
    png = base64.b64decode(image_url.split(",", 1)[1])
    assert png.startswith(b"\x89PNG\r\n\x1a\n")
    with Image.open(BytesIO(png)) as image:
        assert image.format == "PNG" and image.width > 1000 and image.height > 1000
    serialized = json.dumps(audits[-1].model_dump(mode="json"))
    assert "runtime-only-placeholder" not in serialized


def test_visible_map_is_side_specific_and_deterministic() -> None:
    engine = IronBottomEngine()
    state = engine.reset("IBS-S-03", 17)
    axis = OpenAICompatibleCommander._visible_map_data_url(state, engine, Side.AXIS)
    allies = OpenAICompatibleCommander._visible_map_data_url(state, engine, Side.ALLIES)
    assert axis != allies
    assert axis == OpenAICompatibleCommander._visible_map_data_url(state, engine, Side.AXIS)


def test_provider_factory_maps_zhipu_without_silent_model_substitution() -> None:
    config = LLMConnectionConfig(
        provider="zhipu", model="glm-5.3-flash", vision_enabled=True
    )
    commander = _make_llm_commander(
        timeout=12, thinking_enabled=True, api_key="placeholder", config=config
    )
    assert commander.endpoint == "https://open.bigmodel.cn/api/paas/v4"
    assert commander.api_key_env == "ZHIPU_API_KEY"
    assert commander.model == "glm-5.3-flash"
    assert commander.vision_enabled is True
    assert commander.thinking_enabled is False
    assert commander.supports_thinking is False
