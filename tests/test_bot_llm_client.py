"""Hermetic HTTP contract and failure boundaries: no actual model calls."""
import json

import httpx
import pytest

from iron_bottom_sound.bot.llm_client import (
    BotLLMClient, BotLLMError, BotLLMSettings, MAX_CONTENT_BYTES, MAX_CONTEXT_BYTES,
    MAX_DEPTH, MAX_RESPONSE_BYTES,
)
from iron_bottom_sound.llm_providers import DEFAULT_MODELS


KEY = "fixture-key-never-real"
CONTEXT = {"side": "allies", "phase": "movement_planning", "observation": {"ships": []}}


def settings(**changes):
    return BotLLMSettings(provider="deepseek", api_key=KEY, **changes)


def envelope(result=None, **changes):
    data = {"model": "untrusted-returned-model", "choices": [{
        "finish_reason": "stop", "message": {
            "role": "assistant", "content": json.dumps(result if result is not None else {
                "report": "当前无已识别敌舰。", "advice": ["继续观察。"]}, ensure_ascii=False),
            "reasoning_content": "SECRET-PRIVATE-REASONING",
        },
    }], "usage": {"prompt_tokens": 13, "completion_tokens": 9, "total_tokens": 22,
                   "reasoning_content": "SECRET-USAGE", "provider_secret": KEY}}
    data.update(changes)
    return data


def client_for(response=None, handler=None):
    calls = []

    def handle(request):
        calls.append(request)
        if handler:
            return handler(request)
        return response if response is not None else httpx.Response(200, json=envelope())

    return BotLLMClient(settings(), transport=httpx.MockTransport(handle)), calls


def assert_error(client, code, **kwargs):
    with pytest.raises(BotLLMError) as caught:
        client.generate(task="report", context=CONTEXT, **kwargs)
    assert caught.value.code == code
    assert KEY not in str(caught.value) and "SECRET" not in repr(caught.value)
    return caught.value


@pytest.fixture
def clean_env(monkeypatch):
    # Replace getenv's namespace so the test neither reads nor borrows real keys.
    monkeypatch.setattr("iron_bottom_sound.bot.llm_client.os.environ", {})
    return monkeypatch


def test_default_disabled_and_no_borrowed_key(clean_env, monkeypatch):
    monkeypatch.setitem(__import__("os").environ, "DEEPSEEK_API_KEY", "unrelated-key")
    config = BotLLMSettings.from_env()
    assert not config.enabled
    assert config.timeout == 45
    never = httpx.MockTransport(lambda _: pytest.fail("Disabled client attempted a request"))
    assert_error(BotLLMClient(config, transport=never), "disabled")
    assert KEY not in repr(settings())


@pytest.mark.parametrize("provider", ["deepseek", "zhipu", "compatible"])
def test_provider_env_defaults_and_override(clean_env, monkeypatch, provider):
    for key, value in {"PROVIDER": provider, "API_KEY": KEY, "TIMEOUT": "51", "MAX_TOKENS": "2048"}.items():
        monkeypatch.setitem(__import__("os").environ, "IBS_BOT_LLM_" + key, value)
    if provider == "compatible":
        monkeypatch.setitem(__import__("os").environ, "IBS_BOT_LLM_BASE_URL", "https://llm.example.com/v1/")
        monkeypatch.setitem(__import__("os").environ, "IBS_BOT_LLM_MODEL", "fixture-model")
    config = BotLLMSettings.from_env()
    assert config.enabled and config.timeout == 51 and config.max_tokens == 2048
    expected_models = {"deepseek": "deepseek-flash", "zhipu": DEFAULT_MODELS["zhipu"],
                       "compatible": "fixture-model"}
    assert config.model == expected_models[provider]
    assert not config.base_url.endswith("/") and KEY not in repr(config)
    monkeypatch.setitem(__import__("os").environ, "IBS_BOT_LLM_MODEL", "explicit-model")
    assert BotLLMSettings.from_env().model == "explicit-model"


@pytest.mark.parametrize("change", [
    {"provider": "other"}, {"provider": []}, {"api_key": "bad\nSECRET"},
    {"timeout": 61}, {"timeout": 0}, {"timeout": float("nan")},
    {"max_tokens": 8193}, {"max_tokens": True}, {"model": "model\nSECRET"},
    {"base_url": "http://api.deepseek.com"}, {"base_url": "https://evil.example.com"},
])
def test_invalid_settings_are_safe(change):
    values = dict(provider="deepseek", api_key=KEY)
    values.update(change)
    with pytest.raises(BotLLMError) as caught:
        BotLLMSettings(**values)
    assert caught.value.code == "config" and "SECRET" not in str(caught.value)


@pytest.mark.parametrize("url", [
    "http://llm.example.com/v1", "https://user:password@llm.example.com/v1",
    "https://127.0.0.1/v1", "https://[::1]/v1", "https://localhost/v1",
    "https://169.254.169.254/v1", "https://api.local/v1", "https://api.internal/v1",
    "https://llm.example.com:444/v1", "https://llm.example.com/v1?key=SECRET",
    "https://llm.example.com/v1#SECRET", "https://llm.example.com/v1/../admin",
    "https://llm.example.com/%2e%2e/admin", "https://llm.example.com\\@evil.example.com",
])
def test_compatible_rejects_untrusted_url(url):
    with pytest.raises(BotLLMError, match="配置"):
        BotLLMSettings(provider="compatible", model="fixture", base_url=url, api_key=KEY)


@pytest.mark.parametrize("field,value", [("TIMEOUT", "oops"), ("MAX_TOKENS", "NaN")])
def test_bad_env_numeric_fields_are_safe(clean_env, monkeypatch, field, value):
    monkeypatch.setitem(__import__("os").environ, "IBS_BOT_LLM_" + field, value)
    with pytest.raises(BotLLMError) as caught:
        BotLLMSettings.from_env()
    assert caught.value.code == "config"


def test_request_shape_single_call_and_only_content_usage_returns():
    client, calls = client_for()
    result = client.generate(task="report", context=CONTEXT, instruction="请报告")
    assert len(calls) == 1
    request = calls[0]
    assert request.method == "POST" and str(request.url) == "https://api.deepseek.com/chat/completions"
    assert request.headers["Authorization"] == "Bearer " + KEY
    body = json.loads(request.content)
    assert set(body) == {"model", "stream", "messages", "max_tokens", "response_format", "thinking"}
    assert body["thinking"] == {"type": "disabled"}
    assert body["model"] == "deepseek-flash" and body["stream"] is False
    assert body["response_format"] == {"type": "json_object"} and body["max_tokens"] == 2000
    assert [m["role"] for m in body["messages"]] == ["system", "user"]
    assert "不可信" in body["messages"][0]["content"] and "未授权" in body["messages"][0]["content"]
    assert json.loads(body["messages"][1]["content"])["context"] == CONTEXT
    assert KEY not in request.content.decode()
    assert result == {"report": "当前无已识别敌舰。", "advice": ["继续观察。"],
                      "model": "deepseek-flash",
                      "usage": {"prompt_tokens": 13, "completion_tokens": 9, "total_tokens": 22}}
    assert "SECRET" not in json.dumps(result)


@pytest.mark.parametrize("provider", ["deepseek", "zhipu", "compatible"])
def test_only_deepseek_disables_thinking_and_prompts_bound_reports_and_authorized_rules(provider):
    calls = []

    def handle(request):
        calls.append(request)
        return httpx.Response(200, json=envelope())

    options = {"model": "fixture", "base_url": "https://llm.example.com/v1"} if provider == "compatible" else {}
    client = BotLLMClient(BotLLMSettings(provider=provider, api_key=KEY, **options),
                          transport=httpx.MockTransport(handle))
    client.generate(task="report", context=CONTEXT)
    body = json.loads(calls[0].content)
    assert len(calls) == 1
    if provider == "deepseek":
        assert body["thinking"] == {"type": "disabled"}
    else:
        assert "thinking" not in body
    system = body["messages"][0]["content"]
    assert all(part in system for part in ["1000字", "最多3条", "120字", "1360字", "最近已发现敌舰", "距离相同"])


def test_http_client_disables_proxy_and_redirects(monkeypatch):
    real = httpx.Client
    options = []

    def factory(**kwargs):
        options.append(kwargs)
        return real(**kwargs)

    monkeypatch.setattr("iron_bottom_sound.bot.llm_client.httpx.Client", factory)
    client, _ = client_for()
    client.generate(task="report", context=CONTEXT)
    assert options[0]["trust_env"] is False and options[0]["follow_redirects"] is False
    assert options[0]["timeout"] == 45


@pytest.mark.parametrize("status", [301, 307, 401, 429, 500, 503])
def test_status_errors_and_redirects_never_retry_or_expose_body(status):
    client, calls = client_for(httpx.Response(status, text="SECRET-body " + KEY,
                                             headers={"Location": "https://evil.example.com"}))
    assert_error(client, "provider")
    assert len(calls) == 1


@pytest.mark.parametrize("error,code", [(httpx.ReadTimeout, "timeout"), (httpx.ConnectError, "network")])
def test_timeout_network_safe_and_one_call(error, code):
    def handler(request):
        raise error("SECRET-response " + KEY, request=request)

    client, calls = client_for(handler=handler)
    assert_error(client, code)
    assert len(calls) == 1


@pytest.mark.parametrize("finish", ["length", "content_filter", "tool_calls", "aborted", None])
def test_incomplete_finish_reason_rejected_even_with_valid_json(finish):
    data = envelope()
    data["choices"][0]["finish_reason"] = finish
    client, calls = client_for(httpx.Response(200, json=data))
    assert_error(client, "truncated")
    assert len(calls) == 1


@pytest.mark.parametrize("content", [
    "", "SECRET", "```json\n{}\n```", '{"report":"ok","report":"duplicate","advice":[]}',
    '{"report":"ok","advice":[],"nan":NaN}', '[[[[[]]]]]',
])
def test_invalid_json_duplicate_keys_and_nonobject_rejected(content):
    data = envelope()
    data["choices"][0]["message"]["content"] = content
    client, _ = client_for(httpx.Response(200, json=data))
    with pytest.raises(BotLLMError) as caught:
        client.generate(task="report", context=CONTEXT)
    assert caught.value.code in {"response", "schema"}
    assert "SECRET" not in str(caught.value)


@pytest.mark.parametrize("result", [
    {"report": "ok", "advice": [], "extra": "SECRET"},
    {"report": "x" * 1001, "advice": []}, {"report": " ", "advice": []},
    {"report": "ok", "advice": ["a", "b", "c", "d"]},
    {"report": "ok", "advice": ["x" * 121]}, {"report": "ok", "advice": [1]},
    {"report": 1, "advice": []}, {"report": "ok"},
])
def test_report_schema_is_strict_and_reply_bounded(result):
    client, _ = client_for(httpx.Response(200, json=envelope(result)))
    assert_error(client, "schema")


@pytest.mark.parametrize("orders,clarification,expected", [
    ({"movement": [{"ship_id": "own", "plan": "1"}]}, "", {"movement": [{"ship_id": "own", "plan": "1"}]}),
    ({"movement": [{"ship_id": "own", "plan": "1"}]}, "需要明确目标", None),
    (None, "需要明确目标", None), (None, "", None),
])
def test_orders_validate_without_filling_defaults_and_clarifications_never_execute(orders, clarification, expected):
    client, _ = client_for(httpx.Response(200, json=envelope({"orders": orders, "clarification": clarification})))
    result = client.generate(task="orders", context=CONTEXT, instruction="own前进1格")
    assert result["orders"] == expected
    assert result["clarification"] == clarification
    if expected:
        assert "side" not in result["orders"] and "confirmation" not in result["orders"]


@pytest.mark.parametrize("orders", [
    {"side": "axis"}, {"phase": "gunnery"}, {"unknown": []},
    {"movement": [{"ship_id": "own", "plan": "1", "SECRET": True}]},
    {"movement": [{"ship_id": 3, "plan": "1"}]},
    {"movement": [{"plan": "1"}]},
    {"confirmation": {"ready": True, "SECRET": True}},
    {}, {"side": "allies", "phase": "movement_planning"},
    {"confirmation": {}}, {"movement": []},
])
def test_orders_reject_identity_phase_and_nested_unknown_or_invalid_fields(orders):
    client, _ = client_for(httpx.Response(200, json=envelope({"orders": orders, "clarification": ""})))
    with pytest.raises(BotLLMError) as caught:
        client.generate(task="orders", context=CONTEXT, instruction="明确命令")
    assert caught.value.code == "schema"


def test_envelope_size_and_content_size_limits_are_explicit():
    for response in [httpx.Response(200, content=b" " * (MAX_RESPONSE_BYTES + 1)),
                     httpx.Response(200, json=envelope({"report": "x" * MAX_CONTENT_BYTES, "advice": []}))]:
        client, calls = client_for(response)
        assert_error(client, "response_size")
        assert len(calls) == 1


def test_context_size_depth_and_nonjson_input_fail_without_request():
    deep = {}
    for _ in range(MAX_DEPTH + 1):
        deep = {"nested": deep}
    for context in [{"text": "中" * MAX_CONTEXT_BYTES}, deep, {"bad": object()}, {"bad": float("inf")}]:
        client, calls = client_for()
        with pytest.raises(BotLLMError) as caught:
            client.generate(task="report", context=context)
        assert caught.value.code == "input_size" and calls == []


def test_large_complete_legal_context_is_not_truncated():
    # Legal menus can exceed 58k characters; preserving the full menu is required.
    context = {**CONTEXT, "legal_actions": [{"kind": "movement", "schema_hint": "格" * 1500}] * 35}
    client, calls = client_for()
    client.generate(task="report", context=context)
    sent = json.loads(json.loads(calls[0].content)["messages"][1]["content"])
    assert sent["context"] == context and len(calls[0].content) > 150000


def test_reasoning_is_never_used_as_fallback_and_tool_calls_rejected():
    for changes in [{"content": None, "reasoning_content": '{"report":"SECRET","advice":[]}'},
                    {"tool_calls": [{"function": {"name": "SECRET-tool"}}]}]:
        data = envelope()
        data["choices"][0]["message"].update(changes)
        client, _ = client_for(httpx.Response(200, json=data))
        assert_error(client, "response")


def test_usage_only_accepts_nonnegative_plain_integers():
    client, _ = client_for(httpx.Response(200, json=envelope(usage={
        "prompt_tokens": True, "completion_tokens": -1, "total_tokens": "SECRET",
        "prompt_cache_hit_tokens": 3, "prompt_cache_miss_tokens": 10**10,
    })))
    assert client.generate(task="report", context=CONTEXT)["usage"] == {"prompt_cache_hit_tokens": 3}


def test_exception_message_cannot_echo_external_text():
    error = BotLLMError("provider", "SECRET-key " + KEY)
    assert "SECRET" not in str(error) and KEY not in repr(error)


def referee_result(action="clarify", **changes):
    data = dict(action=action, match_id=None, create=None, changes=None, steps=1,
                message="请说明操作")
    if action == "create":
        data["create"] = dict(mode="formation", opponent="pve", scenario_id="IBS-S-03",
                              side="allies", seed=1)
        data["message"] = "拟创建默认编队PVE对局"
    elif action == "patch":
        data["changes"] = {"ships": [{"ship_id": "标枪", "fields": {
            "position": {"q": 15, "r": 7}, "hull": 4,
        }}], "game": {"visibility": {"allies": 8}}}
        data["message"] = "拟调整标枪的位置与损伤"
    elif action == "advance":
        data["message"] = "拟推进1个阶段"
    elif action == "undo":
        data["message"] = "拟撤销上次裁判修改"
    elif action == "report":
        data["message"] = "当前处于机动规划阶段"
    data.update(changes)
    return data


@pytest.mark.parametrize("action", ["create", "advance", "patch", "undo", "report", "clarify"])
def test_referee_actions_are_structured_only_single_call_and_keep_original_protocol(action):
    expected = referee_result(action)
    client, calls = client_for(httpx.Response(200, json=envelope(expected)))
    result = client.generate(task="referee", context={"matches": [], "current": CONTEXT},
                             instruction="推进阶段" if action == "advance" else "明确管理员操作")
    assert len(calls) == 1
    assert {key: result[key] for key in expected} == expected
    assert set(result) == set(expected) | {"model", "usage"}
    request = json.loads(calls[0].content)
    assert request["thinking"] == {"type": "disabled"} and request["model"] == "deepseek-flash"
    assert request["stream"] is False and request["response_format"] == {"type": "json_object"}
    assert json.loads(request["messages"][1]["content"])["task"] == "referee"
    system = request["messages"][0]["content"]
    for part in ["只识别用户操作", "六个字段必须齐全", "formation/pve/IBS-S-03/allies/1",
                 "steps=1", "状态纠错", "不能声称", "800字", "action=clarify", "完整舰名"]:
        assert part in system
    assert "SECRET" not in json.dumps(result)


@pytest.mark.parametrize("missing", ["action", "match_id", "create", "changes", "steps", "message"])
def test_referee_requires_every_fixed_field(missing):
    expected = referee_result()
    del expected[missing]
    client, calls = client_for(httpx.Response(200, json=envelope(expected)))
    with pytest.raises(BotLLMError) as caught:
        client.generate(task="referee", context={})
    assert caught.value.code == "schema" and len(calls) == 1


@pytest.mark.parametrize("change", [
    {"extra": True}, {"action": "shell"}, {"steps": 0}, {"steps": 7}, {"steps": True},
    {"steps": "1"}, {"message": "x" * 801}, {"message": None}, {"match_id": 12},
    {"create": {}}, {"changes": {}},
])
def test_referee_rejects_extra_fields_wrong_types_and_bounds(change):
    client, _ = client_for(httpx.Response(200, json=envelope(referee_result(**change))))
    with pytest.raises(BotLLMError) as caught:
        client.generate(task="referee", context={})
    assert caught.value.code == "schema"


@pytest.mark.parametrize("create", [
    None, {}, {"mode": "formation", "opponent": "pve", "scenario_id": "IBS-S-03", "side": "allies"},
    {"mode": "formation", "opponent": "pve", "scenario_id": "IBS-S-03", "side": "allies", "seed": True},
    {"mode": "formation", "opponent": "pve", "scenario_id": "IBS-S-03", "side": "allies", "seed": 1, "secret": True},
    {"mode": "bad", "opponent": "pve", "scenario_id": "IBS-S-03", "side": "allies", "seed": 1},
])
def test_referee_create_schema_does_not_guess_missing_model_fields(create):
    client, _ = client_for(httpx.Response(200, json=envelope(referee_result("create", create=create))))
    with pytest.raises(BotLLMError) as caught:
        client.generate(task="referee", context={}, instruction="建局")
    assert caught.value.code == "schema"


@pytest.mark.parametrize("changes", [
    None, {}, {"ships": []}, {"game": {}}, {"ships": [], "game": {}, "extra": True},
    {"ships": [{"ship_id": "标枪", "fields": {}, "extra": True}], "game": {}},
    {"ships": [{"ship_id": "标枪"}], "game": {}},
    {"ships": [{"ship_id": "标枪", "fields": []}], "game": {}},
    {"ships": [{"ship_id": 1, "fields": {}}], "game": {}},
])
def test_referee_patch_nested_schema_is_strict_but_leaves_editable_fields_to_service(changes):
    client, _ = client_for(httpx.Response(200, json=envelope(referee_result("patch", changes=changes))))
    with pytest.raises(BotLLMError) as caught:
        client.generate(task="referee", context={}, instruction="修正标枪")
    assert caught.value.code == "schema"


def test_referee_patch_preserves_json_fields_and_empty_collections_without_execution():
    changes = {"ships": [], "game": {}}
    client, calls = client_for(httpx.Response(200, json=envelope(referee_result("patch", changes=changes))))
    result = client.generate(task="referee", context={}, instruction="明确修正值")
    assert result["changes"] == changes and len(calls) == 1
    assert result["steps"] == 1 and result["action"] == "patch"


def test_referee_incomplete_response_never_retries_and_safe_errors_hide_payload():
    data = envelope(referee_result("advance", message="SECRET-user-instruction"))
    data["choices"][0]["finish_reason"] = "length"
    client, calls = client_for(httpx.Response(200, json=data))
    with pytest.raises(BotLLMError) as caught:
        client.generate(task="referee", context={}, instruction="SECRET-user-instruction")
    assert caught.value.code == "truncated" and len(calls) == 1
    assert "SECRET" not in str(caught.value)
