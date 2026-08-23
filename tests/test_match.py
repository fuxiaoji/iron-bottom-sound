import json

import httpx
import pytest

from iron_bottom_sound.engine import IronBottomEngine
from iron_bottom_sound.llm import OpenAICompatibleCommander
from iron_bottom_sound.match import main, make_session, run_match
from iron_bottom_sound.models import AIPlanSheet, GameOptions, OptionalRules, OrderBatch, Phase, Side


@pytest.mark.parametrize("scenario_id", ["IBS-S-03", "IBS-S-01"])
@pytest.mark.parametrize("all_optional", [False, True])
def test_two_isolated_deterministic_sessions_finish_both_scenarios(
    scenario_id: str, all_optional: bool
) -> None:
    options = GameOptions(
        mode="llm",
        optional_rules=OptionalRules(**{
            name: all_optional for name in OptionalRules.model_fields
        }),
    )
    report, engine, sessions = run_match(scenario_id, seed=1, options=options)
    assert report.passed and report.completed
    assert report.fallback_count == 0
    assert report.manual_state_changes == 0
    assert report.request_count <= 128
    assert report.axis_plan_count == len(sessions[Side.AXIS].plan_sheets)
    assert report.allies_plan_count == len(sessions[Side.ALLIES].plan_sheets)
    assert sessions[Side.AXIS] is not sessions[Side.ALLIES]
    assert all(plan.orders["side"] == "axis" for plan in sessions[Side.AXIS].plan_sheets)
    assert all(plan.orders["side"] == "allies" for plan in sessions[Side.ALLIES].plan_sheets)
    assert engine.get(report.game_id).phase == Phase.COMPLETE


def test_match_artifacts_keep_private_plans_in_side_specific_files(tmp_path) -> None:
    report, _, _ = run_match("IBS-S-03", artifact_dir=tmp_path)
    assert report.passed
    public = json.loads((tmp_path / "match-report.json").read_text(encoding="utf-8"))
    axis = json.loads((tmp_path / "axis-private.json").read_text(encoding="utf-8"))
    allies = json.loads((tmp_path / "allies-private.json").read_text(encoding="utf-8"))
    assert "plans" not in public
    assert axis["side"] == "axis" and allies["side"] == "allies"
    assert all(plan["orders"]["side"] == "axis" for plan in axis["plans"])
    assert all(plan["orders"]["side"] == "allies" for plan in allies["plans"])


def test_deepseek_adapter_requires_environment_key_without_fallback(monkeypatch) -> None:
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    engine = IronBottomEngine()
    state = engine.reset("IBS-S-03", 1)
    with pytest.raises(RuntimeError, match="DEEPSEEK_API_KEY is not configured"):
        OpenAICompatibleCommander().choose_plan(engine, state.game_id, Side.AXIS)


def test_deepseek_adapter_retries_invalid_json_then_self_corrects(monkeypatch) -> None:
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-only-placeholder")
    requests: list[httpx.Request] = []
    valid_batch = OrderBatch(side=Side.AXIS, phase=Phase.REINFORCEMENT)
    valid_plan = AIPlanSheet(
        turn=1,
        phase=Phase.REINFORCEMENT,
        situation_summary="己方无增援。",
        phase_goal="确认阶段",
        orders=valid_batch.model_dump(mode="json"),
    )

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        content = "{}" if len(requests) == 1 else valid_plan.model_dump_json()
        return httpx.Response(
            200,
            json={
                "id": f"request-{len(requests)}",
                "choices": [{"message": {"content": content}}],
                "usage": {"prompt_tokens": 10, "completion_tokens": 5},
            },
        )

    client = httpx.Client(transport=httpx.MockTransport(handler))
    engine = IronBottomEngine()
    state = engine.reset("IBS-S-03", 1)
    commander = OpenAICompatibleCommander(client=client)
    plan, batch, audits = commander.choose_plan(engine, state.game_id, Side.AXIS)
    assert plan == valid_plan and batch == valid_batch
    assert [audit.valid for audit in audits] == [False, True]
    assert len(requests) == 2
    payload = json.loads(requests[-1].content)
    assert payload["model"] == "deepseek-v4-flash"
    assert payload["thinking"] == {"type": "disabled"}
    assert payload["response_format"] == {"type": "json_object"}
    assert payload["temperature"] == 0 and payload["max_tokens"] == 1200
    assert "test-only-placeholder" not in "".join(audit.model_dump_json() for audit in audits)


def test_match_runner_enforces_request_limit_and_player_names() -> None:
    report, _, _ = run_match("IBS-S-03", request_limit=0)
    assert not report.passed
    assert report.failure_reason == "LLM request limit 0 reached"
    assert make_session(Side.AXIS, "deepseek").side == Side.AXIS
    with pytest.raises(ValueError, match="Unknown player"):
        make_session(Side.AXIS, "unknown")


def test_match_cli_writes_acceptance_artifacts(monkeypatch, tmp_path, capsys) -> None:
    artifacts = tmp_path / "cli-match"
    monkeypatch.setattr(
        "sys.argv",
        [
            "iron_bottom_sound.match",
            "--scenario", "IBS-S-03",
            "--seed", "9",
            "--all-optional",
            "--artifacts", str(artifacts),
        ],
    )
    assert main() == 0
    printed = json.loads(capsys.readouterr().out)
    assert printed["passed"] is True
    assert (artifacts / "event-replay.json").exists()
