"""交互层支撑接口：发报预判、代理策略接入、对局列表标记。

这三个接口存在的理由只有一个：让玩家在按下按钮**之前**就能看懂会发生什么。
* 预判必须来自引擎自己的路由与延迟计算，且**只读**（不发报、不占序号、不改状态）；
* 密钥只在进程内存里，撤销后如实回到教条标签，绝不落盘；
* 列表必须能标出这是命令延迟对局（否则首页上认不出来）。

因此这里断言的是「没有副作用」「标签诚实」「退役后回教条」，而不是文案。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend" / "src"))

from iron_bottom_sound import command_delay  # noqa: E402
from iron_bottom_sound.engine import IronBottomEngine  # noqa: E402
from iron_bottom_sound.models import GameOptions, Side  # noqa: E402

SCENARIO = "IBS-S-01"
SEED = 20270830


def _client():
    from fastapi.testclient import TestClient

    from iron_bottom_sound.api import app

    return TestClient(app)


def _command_delay_game(client, *, to_movement_planning: bool = True) -> str:
    """建一局；指挥链在编成阶段结束后才存在，所以默认推到第一个机动阶段。

    推进方式沿用 v2.3 测试的驱动：机动阶段交编队代理方案、炮击阶段交引擎生成的批次，
    其余阶段用真实模式指挥官 —— 不绕过任何校验，也不替引擎选方案。
    """
    from iron_bottom_sound.api import engine as api_engine
    from iron_bottom_sound.engine import ORDER_PHASES
    from iron_bottom_sound.llm import LLMPlayerSession
    from iron_bottom_sound.models import OrderBatch, Phase
    from iron_bottom_sound.realistic_command import RealisticCommander, default_setup_orders

    created = client.post("/games", json={
        "scenario_id": SCENARIO, "seed": SEED,
        "options": {"mode": "hotseat", "realistic_command": True,
                    "command_delay_mode": True},
    })
    assert created.status_code == 201, created.text
    game_id = created.json()["game_id"]
    if not to_movement_planning:
        return game_id
    state = api_engine.get(game_id)
    for side in Side:
        setup = default_setup_orders(state, side)
        assert api_engine.submit_orders(game_id, OrderBatch(
            side=side, phase=Phase.FORMATION_SETUP, formation_setup=setup,
        )).valid
    api_engine.advance(game_id)
    sessions = {side: LLMPlayerSession(side, RealisticCommander()) for side in Side}
    steps = 0
    while state.phase is not Phase.MOVEMENT_PLANNING and steps < 40:
        steps += 1
        if state.phase in ORDER_PHASES:
            for side in Side:
                if side.value in state.submitted_orders:
                    continue
                if state.phase is Phase.MOVEMENT_PLANNING:
                    batch = OrderBatch(
                        side=side, phase=state.phase,
                        formation_movement=command_delay.formation_orders(state, side),
                    )
                elif state.phase is Phase.GUNNERY:
                    batch = command_delay.gunnery_batch(state, side)
                else:
                    batch = sessions[side].choose_orders(api_engine, game_id)
                result = api_engine.submit_orders(game_id, batch)
                if not result.valid and state.phase is Phase.MOVEMENT_PLANNING:
                    _, fallback, _ = RealisticCommander().choose_plan(
                        api_engine, game_id, side)
                    result = api_engine.submit_orders(game_id, fallback)
                assert result.valid, result.errors[:2]
        api_engine.advance(game_id)
    assert state.phase is Phase.MOVEMENT_PLANNING, state.phase
    assert state.command_delay is not None, "指挥链必须在机动阶段前建立"
    return game_id


@pytest.fixture(autouse=True)
def _clean_policies():
    """策略注册表是进程级的，测试之间必须互不残留。"""
    yield
    command_delay.clear_side_policies()
    command_delay.clear_fleet_policies()


def test_the_preview_never_changes_the_game() -> None:
    """预判是只读的：玩家还没按发送，任何状态（含报文序号与命令簿）都不能动。"""
    from iron_bottom_sound.api import engine as api_engine

    client = _client()
    game_id = _command_delay_game(client)
    state = api_engine.get(game_id)
    before = state.model_dump_json()
    sequence_before = state.command_delay.next_sequence if state.command_delay else 0
    recipient = next(
        formation.id for formation in state.formations.values()
        if formation.side is Side.AXIS
    )
    response = client.post(
        f"/games/{game_id}/command-delay/order/preview",
        headers={"X-Player-Side": "axis"},
        json={"formation_id": recipient, "text": "向东拉开距离保持接触"},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert set(body) >= {
        "reason_code", "medium", "total_delay", "distance_hex", "tbs_range_hex",
        "slot_cost", "link_status",
    }
    # 距离与射程都由引擎给，前端不需要换算
    assert body["tbs_range_hex"] > 0
    assert body["reason_code"] in {
        "face_to_face", "tbs_short", "blinker", "wt_coded", "recipient_not_on_board",
        "fleet_flagship_not_on_board", "no_fleet_formation", "no_chain_yet",
    }
    state_after = api_engine.get(game_id)
    assert state_after.model_dump_json() == before, "预览改动了游戏状态"
    assert state_after.command_delay.next_sequence == sequence_before, "预览消耗了报文序号"


def test_the_preview_never_builds_the_command_chain_it_is_previewing() -> None:
    """模式状态为空时（推进之前存档的老对局就是如此），预判如实回答而不是创建状态。

    新建的对局在第一次推进前既没有编队也没有指挥链，所以这条路径在真实存档里存在：
    只要在对局开始时存过档，`command_delay` 就是 null。
    """
    from iron_bottom_sound.api import engine as api_engine

    client = _client()
    fresh = _command_delay_game(client, to_movement_planning=False)
    assert api_engine.get(fresh).command_delay is None, "刚建局时不该有指挥链状态"

    game_id = _command_delay_game(client)
    state = api_engine.get(game_id)
    without_chain = state.model_copy(deep=True)
    without_chain.command_delay = None
    recipient = next(
        formation.id for formation in without_chain.formations.values()
        if formation.side is Side.AXIS
    )
    before = without_chain.model_dump_json()
    preview = command_delay.preview_order_delivery(
        api_engine, without_chain, side=Side.AXIS, formation_id=recipient, text="先等编成结束",
    )
    assert preview["reason_code"] == "no_chain_yet"
    assert preview["medium"] == "blackout"
    assert without_chain.command_delay is None, "预判创建了模式状态"
    assert without_chain.model_dump_json() == before


def test_the_preview_prices_a_long_order_as_more_than_one_slot() -> None:
    """长命令按引擎自己的时隙规则计价（>240 字＝2 个时隙），并如实标注。"""
    from iron_bottom_sound.api import engine as api_engine

    client = _client()
    game_id = _command_delay_game(client)
    state = api_engine.get(game_id)
    recipient = next(
        formation.id for formation in state.formations.values()
        if formation.side is Side.AXIS
    )
    short = client.post(
        f"/games/{game_id}/command-delay/order/preview",
        headers={"X-Player-Side": "axis"},
        json={"formation_id": recipient, "text": "保持接触"},
    ).json()
    long = client.post(
        f"/games/{game_id}/command-delay/order/preview",
        headers={"X-Player-Side": "axis"},
        json={"formation_id": recipient, "text": "向东拉开距离保持接触" * 30},
    ).json()
    assert short["slot_cost"] == 1 and short["long_order"] is False
    assert long["slot_cost"] == 2 and long["long_order"] is True


def test_the_preview_warns_when_the_order_restates_the_standing_one() -> None:
    """重复现行命令会被引擎记为 NO_NEW_ORDER；预判必须先说出来。"""
    from iron_bottom_sound.api import engine as api_engine

    client = _client()
    game_id = _command_delay_game(client)
    state = api_engine.get(game_id)
    recipient = next(
        formation.id for formation in state.formations.values()
        if formation.side is Side.AXIS
    )
    text = "向东拉开距离保持接触，不要进入主力火线前方"
    sent = client.post(
        f"/games/{game_id}/command-delay/order",
        headers={"X-Player-Side": "axis"},
        json={"formation_id": recipient, "text": text},
    )
    assert sent.status_code == 200, sent.text
    preview = client.post(
        f"/games/{game_id}/command-delay/order/preview",
        headers={"X-Player-Side": "axis"},
        json={"formation_id": recipient, "text": text},
    ).json()
    assert preview["restates_active_order"] is True
    different = client.post(
        f"/games/{game_id}/command-delay/order/preview",
        headers={"X-Player-Side": "axis"},
        json={"formation_id": recipient, "text": "改为向西南撤离并保持无线电沉默"},
    ).json()
    assert different["restates_active_order"] is False


def test_a_key_can_be_attached_to_a_running_game_and_is_never_persisted() -> None:
    """已在进行的对局也能接上模型；密钥只进内存，撤销后如实回到教条。"""
    from iron_bottom_sound.api import engine as api_engine

    client = _client()
    game_id = _command_delay_game(client)
    initial = client.get(
        f"/games/{game_id}/command-delay/agent-policy",
        headers={"X-Player-Side": "axis"},
    ).json()
    assert initial["models_configured"] is False
    assert not initial["formation_labels"]["axis"].startswith("llm:"), (
        "建局时没有密钥：标签必须如实说明，而不是写成模型"
    )

    attached = client.post(
        f"/games/{game_id}/command-delay/agent-policy",
        headers={"X-Player-Side": "axis"},
        json={
            "api_key": "unit-test-key", "sides": ["axis"], "fleet": True,
            "config": {"provider": "deepseek", "model": "deepseek-chat",
                       "vision_enabled": False},
        },
    )
    assert attached.status_code == 200, attached.text
    body = attached.json()
    assert body["configured"] is True
    assert body["formation_labels"]["axis"].startswith("llm:deepseek/")
    assert body["fleet_labels"]["axis"].startswith("llm:deepseek/"), "舰队代理也要接上"
    assert not body["formation_labels"]["allies"].startswith("llm:"), (
        "只给本侧接模型时，另一侧必须保持教条"
    )
    assert body["keys_are_memory_only"] is True

    revoked = client.post(
        f"/games/{game_id}/command-delay/agent-policy",
        headers={"X-Player-Side": "axis"},
        json={"api_key": None, "sides": ["axis"]},
    ).json()
    assert revoked["configured"] is False
    assert not revoked["formation_labels"]["axis"].startswith("llm:"), (
        "撤销后必须回到没有模型的标签"
    )
    assert not revoked["fleet_labels"]["axis"].startswith("llm:"), (
        "撤销后舰队层也必须回到没有代理的标签"
    )

    # 存档里绝不能出现密钥：它只在进程内存。
    from iron_bottom_sound.api import repository

    with repository.connection as connection:
        row = connection.execute(
            "SELECT state_json FROM games WHERE game_id = ?", (game_id,)
        ).fetchone()
    assert "unit-test-key" not in row["state_json"]
    assert api_engine.get(game_id).command_delay.policy_labels is not None


def test_a_fleet_agent_is_opt_in_only() -> None:
    """舰队层代理必须显式勾选：默认只接编队，否则模型会在玩家自己那一侧下单。"""
    client = _client()
    game_id = _command_delay_game(client)
    plain = client.post(
        f"/games/{game_id}/command-delay/agent-policy",
        headers={"X-Player-Side": "axis"},
        json={"api_key": "unit-test-key", "sides": ["axis"],
              "config": {"provider": "deepseek", "model": "deepseek-chat",
                         "vision_enabled": False}},
    ).json()
    assert plain["formation_labels"]["axis"].startswith("llm:")
    assert plain["fleet_labels"]["axis"] == "no-fleet-agent", (
        "没勾选舰队代理时，舰队层必须不动"
    )
    assert plain["fleet_registered"] == []

    with_fleet = client.post(
        f"/games/{game_id}/command-delay/agent-policy",
        headers={"X-Player-Side": "axis"},
        json={"api_key": "unit-test-key", "sides": ["allies"], "fleet": True},
    ).json()
    assert with_fleet["fleet_labels"]["allies"].startswith("llm:")
    assert with_fleet["fleet_labels"]["axis"] == "no-fleet-agent", (
        "只给另一侧勾选时，本侧舰队层不受影响"
    )

    revoked = client.post(
        f"/games/{game_id}/command-delay/agent-policy",
        headers={"X-Player-Side": "axis"},
        json={"api_key": None, "sides": ["allies"]},
    ).json()
    assert revoked["fleet_labels"]["allies"] == "no-fleet-agent", (
        "撤销必须把舰队层一起清掉，否则界面说教条而模型还在下令"
    )


def test_the_opponent_cannot_read_or_change_our_policy() -> None:
    """代理政策属于本方指挥链：换一侧 header 读不到刚才接入的标签。"""
    from iron_bottom_sound.api import engine as api_engine

    client = _client()
    game_id = _command_delay_game(client)
    client.post(
        f"/games/{game_id}/command-delay/agent-policy",
        headers={"X-Player-Side": "axis"},
        json={"api_key": "unit-test-key", "sides": ["axis"]},
    )
    other = client.get(
        f"/games/{game_id}/command-delay/agent-policy",
        headers={"X-Player-Side": "allies"},
    ).json()
    assert not other["formation_labels"]["allies"].startswith("llm:")
    state = api_engine.get(game_id)
    assert "unit-test-key" not in json.dumps(state.model_dump(mode="json"), default=str)


def test_the_saved_game_list_marks_a_command_delay_game() -> None:
    """首页要认得出这是命令延迟对局：列表摘要必须带上该标记。"""
    client = _client()
    game_id = _command_delay_game(client)
    listed = [item for item in client.get("/games").json() if item["game_id"] == game_id]
    assert listed, "刚创建的对局必须出现在列表里"
    assert listed[0]["command_delay_mode"] is True


def test_the_preview_reports_a_recipient_that_is_not_on_the_board_yet() -> None:
    """旗舰不在图上的收件人（未到场或旗舰已损失）不能收到电报：预判要说明原因。

    这个判据不能靠"某个想定开局刚好有预备队"来碰运气，所以直接把一份状态的领舰位置
    清空来构造 —— 引擎自己的判据是"领舰不在图上"，与想定无关。
    """
    from iron_bottom_sound.api import engine as api_engine
    from iron_bottom_sound.models import Side

    client = _client()
    game_id = _command_delay_game(client)
    state = api_engine.get(game_id)
    authority = command_delay.authority_for(state, Side.AXIS)
    # 取一个**非**当面受令的编队：被搭载的编队按定义是当面交办，与是否到场无关。
    formation = next(
        item for item in state.formations.values()
        if item.side is Side.AXIS
        and (authority is None or item.id != authority.fleet_formation_id)
    )
    staged = state.model_copy(deep=True)
    staged.ships[formation.leader_id].position = None
    preview = command_delay.preview_order_delivery(
        api_engine, staged, side=Side.AXIS, formation_id=formation.id, text="集合",
    )
    assert preview["reason_code"] == "recipient_not_on_board"
    assert preview["medium"] == "blackout"
    assert preview["formation_arrived_hex"] is None
    # 而同一个引擎在真实状态上给的是可投递的链路：说明预判读的是状态，不是常量。
    live = command_delay.preview_order_delivery(
        api_engine, state, side=Side.AXIS, formation_id=formation.id, text="集合",
    )
    assert live["reason_code"] != "recipient_not_on_board"
