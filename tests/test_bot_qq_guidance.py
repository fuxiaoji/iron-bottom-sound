"""QQ help and phase guidance privacy/turn-taking contracts."""
import pytest

from iron_bottom_sound.bot.qq_guidance import help_text, next_steps, status_text
from iron_bottom_sound.models import Phase


def snapshot(**updates):
    return {"match_id": "match-123", "revision": 1, "turn": 1, "phase": "reinforcement",
            "side": "allies", "mode": "formation", "opponent": "pve", "ready": [],
            "started": True, "complete": False, **updates}


@pytest.mark.parametrize("scope", ["group", "c2c"])
def test_entry_help_fits_one_text_reply_and_gives_progression(scope):
    text = help_text(scope)
    assert len(text) < 1400
    assert "/下一步" in text and "/自动 版本号" in text
    assert "离线状态机" in text and "不是LLM" in text
    assert "私聊" in text and "验证码" not in text  # Detailed binding is a focused topic.


@pytest.mark.parametrize("topic", ["快速开始", "推进", "手动", "PVP", "绑定"])
def test_focused_help_is_available_without_long_reply(topic):
    text = help_text("c2c", topic)
    assert len(text) < 1400 and len(text) > 100
    assert "铁底湾｜" in text


def test_manual_help_distinguishes_empty_confirmation_from_automatic_orders():
    text = help_text("c2c", "手动")
    assert "/确认 版本号" in text and "空命令" in text and "引擎认可" in text
    assert "这一步不结算" in text and "/草稿" in text
    assert "无需JSON" in text and "不会用AI补齐" in text


def test_progression_help_explains_multiple_phases_and_version_refresh():
    text = help_text("c2c", "推进")
    assert "一个回合包含多个阶段" in text and "回合数可能不变" in text
    assert "/自动 1" in text and "不能一直重复旧版本" in text
    assert "不会提交命令" in text


def test_private_phase_hint_gives_exact_current_revision_without_advancing_it():
    value = snapshot()
    text = next_steps(value, private=True)
    assert "增援阶段" in text and "/自动 1 match-123" in text
    assert "/自动 2" not in text and value["revision"] == 1
    assert "/提交 1 match-123" in text and "无需JSON" in text


def test_pvp_sealed_seat_only_waits_and_refreshes():
    text = next_steps(snapshot(opponent="pvp", ready=["allies"]), private=True)
    assert "等待对手" in text and "/态势 match-123" in text
    assert "/自动" not in text and "/提交" not in text and "/确认" not in text


def test_unsealed_pvp_opponent_can_submit_current_version():
    text = next_steps(snapshot(opponent="pvp", ready=["axis"]), private=True)
    assert "/自动 1" in text


def test_unstarted_match_requests_other_player_instead_of_submission():
    text = next_steps(snapshot(opponent="pvp", started=False), private=True)
    assert "/加入 match-123" in text and "暂不能推进" in text
    assert "/自动" not in text and "/提交" not in text


@pytest.mark.parametrize("updates", [{"complete": True}, {"phase": "complete"}])
def test_finished_match_never_offers_another_submission(updates):
    text = next_steps(snapshot(**updates), private=True)
    assert "本局已结束" in text and "/态势 match-123" in text
    assert "/自动" not in text and "/提交" not in text


@pytest.mark.parametrize("phase", list(Phase))
def test_every_actual_engine_phase_has_a_chinese_label(phase):
    text = status_text(snapshot(phase=phase.value), private=True)
    assert "未知阶段" not in text and phase.value not in text


@pytest.mark.parametrize("phase", ["movement_resolution", "torpedo_effects", "fire_end"])
def test_automatic_phase_has_no_player_action(phase):
    text = next_steps(snapshot(phase=phase), private=True)
    assert "引擎自动结算" in text and "/态势" in text
    assert "/自动" not in text and "/提交" not in text


def test_public_next_steps_only_offer_private_guidance_and_public_map():
    text = next_steps(snapshot(), private=False)
    assert "/下一步 match-123" in text and "/战况 match-123" in text
    assert "/自动" not in text and "/提交" not in text


@pytest.mark.parametrize("renderer", [status_text, next_steps])
@pytest.mark.parametrize("private", [False, True])
def test_only_approved_metadata_can_reach_guidance(renderer, private):
    value = snapshot(observation={"ships": "PRIVATE_SHIP"}, summary="PRIVATE_EVENT",
                     orders="PRIVATE_ORDER", member_openid="PRIVATE_MEMBER", room_id="PRIVATE_ROOM")
    text = renderer(value, private=private)
    assert not any(secret in text for secret in ("PRIVATE_SHIP", "PRIVATE_EVENT", "PRIVATE_ORDER", "PRIVATE_MEMBER", "PRIVATE_ROOM"))
    assert ("你执盟军" in text) is (private and renderer is status_text)


def test_invalid_or_missing_revision_does_not_offer_mutation():
    for revision in (None, -1, True, "1"):
        text = next_steps(snapshot(revision=revision), private=True)
        assert "缺少有效版本号" in text
        assert "/自动" not in text and "/提交" not in text


def test_unknown_phase_and_untrusted_identifier_are_not_echoed():
    value = snapshot(phase="PRIVATE_PHASE", match_id="PRIVATE\nIDENTITY")
    assert "PRIVATE" not in status_text(value)
    assert "PRIVATE" not in next_steps(value, private=True)
    assert "/自动" not in next_steps(value, private=True)


def test_missing_match_identifier_does_not_offer_ambiguous_submission():
    text = next_steps(snapshot(match_id=None), private=True)
    assert "/我的对局" in text and "/自动" not in text
