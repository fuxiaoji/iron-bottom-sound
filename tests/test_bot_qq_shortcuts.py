"""Signed QQ shortcut routing through the existing offline platform fixture.

Seat binding itself is covered by the service identity tests. Here the service
enumeration is stubbed to expose only the private actor's already-owned seats.
"""
import pytest

from test_bot_qq_official import bot, event, messages, post


def texts(seen):
    return "\n".join(m.get("content", "") for m in messages(seen) if m.get("msg_type") == 0)


def uploads(seen):
    return [url for url, _, _ in seen if url.endswith("/files")]


def snapshots(service, **changes):
    original = service.snapshot
    service.snapshot = lambda match="match1": {**original(match), **changes}


def owned_matches(service, identifiers):
    def matches(**kwargs):
        service.calls.append(("matches", kwargs))
        return [service.snapshot(match) for match in identifiers]
    service.matches = matches


@pytest.mark.parametrize("command,mode,opponent", [
    ("/编队人机", "formation", "pve"),
    ("/普通人机", "classic", "pve"),
    ("/编队对战", "formation", "pvp"),
    ("/普通对战", "classic", "pvp"),
])
def test_group_presets_create_expected_mode_without_private_data(bot, command, mode, opponent):
    client, service, seen, _ = bot
    reply = post(client, event("<@12345> " + command))
    assert reply.status_code == 200 and service.mutations == 1
    name, args = service.calls[0]
    assert name == "create" and args["mode"] == mode and args["opponent"] == opponent
    assert args["actor_id"] == "qqbot:12345:member:GROUP:MEMBER"
    assert args["room_id"] == "qqbot:12345:GROUP"
    assert "绑定" in texts(seen) and "下一步" in texts(seen)
    assert "NEVER_PUBLIC" not in texts(seen) and "OWN" not in texts(seen)
    assert not uploads(seen)


@pytest.mark.parametrize("private", [False, True])
@pytest.mark.parametrize("command", ["/", "/帮助", "/帮助 快速开始", "/帮助 推进", "/帮助 手动", "/帮助 PVP", "/帮助 绑定"])
def test_slash_and_help_topics_are_read_only_without_seat_lookup(bot, private, command):
    client, service, seen, _ = bot
    assert post(client, event(command, private=private)).status_code == 200
    assert service.calls == [] and service.mutations == 0
    assert "铁底湾" in texts(seen) and len(messages(seen)) == 1
    assert not uploads(seen)


def test_private_short_situation_after_binding_uses_authenticated_alias_and_png(bot):
    client, service, seen, _ = bot
    post(client, event("铁底湾 GROUP match1 绑定 盟军", private=True, message_id="issue"))
    post(client, event("/绑定 PRIVATE_BINDING_CODE", message_id="claim"))
    assert [call[0] for call in service.calls[:2]] == ["issue_identity_link", "claim_identity_link"]
    seen.clear()
    assert post(client, event("/态势", private=True, message_id="situation")).status_code == 200
    lookup = next(args for name, args in service.calls if name == "matches")
    assert lookup == {"actor_id": "qqbot:12345:c2c:MEMBER", "room_id": "qqbot:12345:GROUP"}
    status = next(args for name, args in service.calls if name == "status")
    assert status["match_id"] == "match1" and status["actor_id"] == lookup["actor_id"]
    assert uploads(seen) == ["https://api.sgroup.qq.com/v2/users/MEMBER/files"]
    assert "机动规划" in texts(seen) and "/自动 2 match1" in texts(seen)
    assert "PRIVATE_C2C_ID" not in texts(seen)


def test_next_steps_is_read_only_and_never_uploads_image(bot):
    client, service, seen, _ = bot
    post(client, event("/下一步", private=True))
    assert service.mutations == 0 and not uploads(seen)
    assert "/自动 2 match1" in texts(seen) and "版本2" in texts(seen)
    assert all(name not in {"auto", "submit", "screenshot"} for name, _ in service.calls)


def test_short_auto_has_fixed_actor_current_revision_and_event_idempotency(bot):
    client, service, seen, _ = bot
    payload = event("/自动 2 match1", private=True)
    assert post(client, payload).status_code == 200
    delivered = len(messages(seen))
    assert post(client, payload).status_code == 200
    assert service.mutations == 1 and len(messages(seen)) == delivered
    name, args = next(call for call in service.calls if call[0] == "auto")
    assert name == "auto" and args["expected_revision"] == 2
    assert args["match_id"] == "match1" and args["actor_id"] == "qqbot:12345:c2c:MEMBER"
    assert args["room_id"] == "qqbot:12345:GROUP"
    assert len(uploads(seen)) == 1


@pytest.mark.parametrize("command", ["/自动", "/确认", "/推进"])
def test_versionless_mutation_shortcuts_only_explain_current_step(bot, command):
    client, service, seen, _ = bot
    post(client, event(command, private=True))
    assert service.mutations == 0 and not uploads(seen)
    assert "尚未提交任何命令" in texts(seen) and "/自动 2 match1" in texts(seen)
    assert all(name not in {"auto", "submit"} for name, _ in service.calls)


@pytest.mark.parametrize("command", ["/态势", "/下一步", "/自动 2"])
def test_unbound_actor_cannot_get_private_map_or_submit(bot, command):
    client, service, seen, _ = bot
    owned_matches(service, [])
    post(client, event(command, private=True))
    assert "绑定" in texts(seen) and service.mutations == 0
    assert not uploads(seen)
    assert all(name not in {"status", "screenshot", "auto", "submit"} for name, _ in service.calls)


@pytest.mark.parametrize("command", ["/态势", "/下一步", "/自动 2", "/确认 2"])
def test_multiple_active_matches_are_not_guessed(bot, command):
    client, service, seen, _ = bot
    owned_matches(service, ["match1", "match2"])
    post(client, event(command, private=True))
    assert "多个对局" in texts(seen) and "/态势 match1" in texts(seen) and "/态势 match2" in texts(seen)
    assert service.mutations == 0 and not uploads(seen)
    assert all(name not in {"status", "auto", "submit"} for name, _ in service.calls)


@pytest.mark.parametrize("command,operation", [("/态势 match2", "status"), ("/自动 2 match2", "auto")])
def test_explicit_owned_match_selects_correct_seat_when_multiple_exist(bot, command, operation):
    client, service, seen, _ = bot
    owned_matches(service, ["match1", "match2"])
    post(client, event(command, private=True))
    args = next(args for name, args in service.calls if name == operation)
    assert args["match_id"] == "match2" and args["actor_id"] == "qqbot:12345:c2c:MEMBER"
    assert len(uploads(seen)) == 1


def test_explicit_unknown_match_is_rejected_without_arbitrary_status_lookup(bot):
    client, service, seen, _ = bot
    post(client, event("/态势 other-persons-match", private=True))
    assert "没有找到" in texts(seen) and not uploads(seen)
    assert all(name != "status" for name, _ in service.calls)


@pytest.mark.parametrize("finished", [False, True])
def test_private_waiting_or_finished_guidance_has_no_submission_command(bot, finished):
    client, service, seen, _ = bot
    snapshots(service, side="allies", ready=["allies"], complete=finished,
              phase="complete" if finished else "movement_planning")
    post(client, event("/下一步", private=True))
    text = texts(seen)
    assert ("本局已结束" if finished else "等待对手") in text
    assert "/自动" not in text and "/提交" not in text and "/确认" not in text
    assert service.mutations == 0 and not uploads(seen)


@pytest.mark.parametrize("command", ["/我的对局", "/战况 match1", "/下一步 match1"])
def test_public_shortcut_output_never_contains_private_fields(bot, command):
    client, service, seen, _ = bot
    snapshots(service, side="allies", summary="PRIVATE_SUMMARY", actor_id="PRIVATE_ACTOR",
              secret_orders="PRIVATE_ORDERS")
    post(client, event(command))
    text = texts(seen)
    assert "match1" in text
    assert all(marker not in text for marker in ("OWN", "NEVER_PUBLIC", "PRIVATE_SUMMARY", "PRIVATE_ACTOR", "PRIVATE_ORDERS"))
    assert service.mutations == 0
    assert all(name not in {"status", "screenshot", "auto", "submit"} for name, _ in service.calls)


@pytest.mark.parametrize("command", ["/自动 -1", "/自动 abc", "/自动 2 match1 extra", "/自动 2.5", "/确认 2 extra extra"])
def test_invalid_auto_parameters_do_not_mutate_or_upload(bot, command):
    client, service, seen, _ = bot
    post(client, event(command, private=True))
    assert "用法" in texts(seen)
    assert service.mutations == 0 and not uploads(seen)
    assert all(name not in {"status", "auto", "submit"} for name, _ in service.calls)


def test_multiple_match_explicit_manual_submission_preserves_json(bot):
    client, service, seen, _ = bot
    owned_matches(service, ["match1", "match2"])
    post(client, event('/提交 2 match2 {"movement":[]}', private=True))
    args = next(args for name, args in service.calls if name == "submit")
    assert args["match_id"] == "match2" and args["expected_revision"] == 2
    assert args["orders"] == {"movement": []} and service.mutations == 1


def test_selected_match_ship_filter_does_not_parse_ship_as_another_match(bot):
    client, service, seen, _ = bot
    owned_matches(service, ["match1", "match2"])
    post(client, event("/行动 match2 ship1", private=True))
    args = next(args for name, args in service.calls if name == "manual_actions")
    assert args["match_id"] == "match2" and "ship1" in texts(seen)
    assert args["unit"] == "ship1" and args["page"] == 1
    assert service.mutations == 0 and not uploads(seen)
