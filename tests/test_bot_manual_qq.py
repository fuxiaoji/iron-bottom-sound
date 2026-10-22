"""QQ manual menus stay short and stage choices before explicit submission."""
import pytest

from test_bot_qq_official import bot, event, messages, post


@pytest.mark.parametrize("command,unit,page", [
    ("/行动", None, 1), ("/行动 match1 页2", None, 2),
    ("/行动 ship1 页3", "ship1", 3), ("/行动 match1 ship1 页2", "ship1", 2),
])
def test_actions_are_paged_human_text_without_whole_legal_schema(bot, command, unit, page):
    client, service, seen, _ = bot
    post(client, event(command, private=True))
    args = next(args for op, args in service.calls if op == "manual_actions")
    assert args == {"match_id": "match1", "actor_id": "qqbot:12345:c2c:MEMBER",
                    "room_id": "qqbot:12345:GROUP", "page": page, "unit": unit}
    replies = messages(seen)
    assert len(replies) == 1 and "编号" in replies[0]["content"]
    assert "完整JSON未发送" not in replies[0]["content"] and "order_schema" not in replies[0]["content"]
    assert service.mutations == 0


def test_select_only_changes_draft_and_duplicate_callback_is_not_reapplied(bot):
    client, service, seen, _ = bot
    payload = event("/选择 2 move1 match1", private=True)
    post(client, payload)
    post(client, payload)
    calls = [args for op, args in service.calls if op == "manual_choose"]
    assert len(calls) == 1 and calls[0]["expected_revision"] == 2
    assert calls[0]["choice_id"] == "move1" and calls[0]["match_id"] == "match1"
    assert service.mutations == 0 and len(messages(seen)) == 1
    assert not any(url.endswith("/files") for url, _, _ in seen)


def test_submit_without_json_submits_existing_draft_with_version_and_png(bot):
    client, service, seen, _ = bot
    post(client, event("/提交 2 match1", private=True))
    call = next(args for op, args in service.calls if op == "manual_submit")
    assert call["expected_revision"] == 2 and call["actor_id"] == "qqbot:12345:c2c:MEMBER"
    assert service.mutations == 1 and len(messages(seen)) == 2
    assert any(url.endswith("/users/MEMBER/files") for url, _, _ in seen)


@pytest.mark.parametrize("command,operation", [("/草稿 match1", "manual_draft"), ("/清空 2 match1", "manual_clear")])
def test_draft_inspection_or_clearing_never_advances_game(bot, command, operation):
    client, service, seen, _ = bot
    post(client, event(command, private=True))
    assert any(op == operation for op, _ in service.calls)
    assert service.mutations == 0 and not any(url.endswith("/files") for url, _, _ in seen)


@pytest.mark.parametrize("command", ["/选择", "/清空", "/提交"])
def test_incomplete_menu_commands_never_change_draft_or_submit(bot, command):
    client, service, seen, _ = bot
    post(client, event(command, private=True))
    assert not any(op in {"manual_choose", "manual_clear", "manual_submit", "submit"} for op, _ in service.calls)
    assert service.mutations == 0 and messages(seen)


@pytest.mark.parametrize("command", ["/选择 2 move1", "/草稿", "/清空 2", "/行动"])
def test_manual_orders_are_never_exposed_in_group(bot, command):
    client, service, seen, _ = bot
    post(client, event(command))
    assert service.calls == [] and "私聊" in messages(seen)[0]["content"]
