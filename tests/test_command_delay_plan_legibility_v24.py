"""机动方案的可读性与「所见即所执行」：三个缺陷的回归测试。

起因（用户实测）：从机动阶段进入鱼雷阶段，同一个编队的机动方案看起来被改了。查下来是两件事：

1. **显示与提交不同源**：机动阶段那张计划表和地图画的是 ``/suggested-orders`` 的建议草稿；
   命令延迟模式下它会把代理选的方案替换成"等价消耗的直行方案"（120° 与超速两个改写），
   而交接时提交的是代理方案原文 —— 于是"你看到的"和"会执行的"分家。
2. **代理读不懂记号**：``1SS1S2`` 是「前进 1 格→右转 120°→…」的调头，模型在理由里写"保持航向2、
   继续直线前进"。提示词此前只给了 ``final_headings``（那是**该格可到达的航向集合**，直行方案也报
   [1,2,3]），没有任何记号说明，也没有每条方案自己的结束航向。

因此这里断言的是：草稿＝代理方案原文（含 120° 方案）、每条方案自带可读的机动说明与结束航向、
以及模型提示词里确实写清了记号读法与挤停风险。
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend" / "src"))

from iron_bottom_sound.command_observation import (  # noqa: E402
    legal_formation_actions, manoeuvre_summary, heading_change_steps,
)
from iron_bottom_sound.command_delay import formation_orders  # noqa: E402
from iron_bottom_sound.engine import ORDER_PHASES, IronBottomEngine  # noqa: E402
from iron_bottom_sound.formation_llm import INSTRUCTION  # noqa: E402
from iron_bottom_sound.llm import LLMPlayerSession  # noqa: E402
from iron_bottom_sound.models import (  # noqa: E402
    GameOptions, MovementOrder, OrderBatch, Phase, Side,
)
from iron_bottom_sound.realistic_command import (  # noqa: E402
    RealisticCommander, default_setup_orders, expand_movement_orders,
)

SCENARIO = "IBS-S-EM-01"
SEED = 19440619


def _to_movement_phase(command_delay: bool = True, scenario: str = SCENARIO):
    """Drive a real game into a movement phase (doctrine agents; no model calls)."""
    engine = IronBottomEngine()
    state = engine.reset(scenario, SEED, GameOptions(
        realistic_command=True, command_delay_mode=command_delay,
    ))
    for side in Side:
        assert engine.submit_orders(state.game_id, OrderBatch(
            side=side, phase=Phase.FORMATION_SETUP,
            formation_setup=default_setup_orders(state, side),
        )).valid
    sessions = {side: LLMPlayerSession(side, RealisticCommander()) for side in Side}
    steps = 0
    while state.phase is not Phase.MOVEMENT_PLANNING and state.phase is not Phase.COMPLETE and steps < 40:
        steps += 1
        if state.phase in ORDER_PHASES:
            for side in Side:
                if side.value in state.submitted_orders:
                    continue
                if state.phase is Phase.MOVEMENT_PLANNING:
                    batch = OrderBatch(side=side, phase=state.phase,
                                       formation_movement=formation_orders(state, side))
                elif state.phase is Phase.GUNNERY:
                    from iron_bottom_sound.command_delay import gunnery_batch

                    batch = gunnery_batch(state, side)
                else:
                    batch = sessions[side].choose_orders(engine, state.game_id)
                result = engine.submit_orders(state.game_id, batch)
                if not result.valid and state.phase is Phase.MOVEMENT_PLANNING:
                    _, fallback, _ = RealisticCommander().choose_plan(engine, state.game_id, side)
                    result = engine.submit_orders(state.game_id, fallback)
                assert result.valid, result.errors[:2]
        engine.advance(state.game_id)
    assert state.phase is Phase.MOVEMENT_PLANNING, state.phase
    return engine, state


# --------------------------------------------------------------------------- ① 显示＝提交

def test_what_the_sheet_shows_is_what_the_engine_seals() -> None:
    """计划表/地图画的（建议草稿）必须就是交接时封存执行的方案 —— 所见即所执行。

    This is the defect the player hit: the sheet showed 4 / 5 for formations whose agents had
    chosen 1SS1S1 / 1SS1S2, and the engine sealed the agents' plans.  The invariant is stated
    against the engine itself (submit the draft, read the sealed batch) so it also covers the
    one remaining case where the engine adjusts a batch: two formations' plans clashing.
    """
    engine, state = _to_movement_phase()
    for side in Side:
        _, batch, _ = RealisticCommander().choose_plan(engine, state.game_id, side)
        draft = {order.formation_id: order.leader_plan for order in batch.formation_movement}
        if not draft:
            continue
        agents = {order.formation_id: order.leader_plan for order in formation_orders(state, side)}
        prepared, errors, _ = expand_movement_orders(engine, state, batch)
        if not errors and engine.validate_orders(state.game_id, prepared, _prepared=True).valid:
            assert draft == agents, (
                f"{side.value}: 无冲突时草稿必须就是代理方案：草稿={draft} 代理={agents}"
            )
        result = engine.submit_orders(state.game_id, batch)
        assert result.valid, (side.value, result.errors[:2])
        # 封存发生在推进时；此刻即将被封存的就是这份提交，两者必须一致。
        sealed = state.submitted_orders[side.value]
        assert {order.formation_id: order.leader_plan for order in sealed.formation_movement} == draft, (
            f"{side.value}: 即将执行的方案与界面显示的方案不一致"
        )
        # 一局里每方每阶段只提交一次；把这份还回去，让下一个 side 独立判断
        state.submitted_orders.pop(side.value, None)


def test_a_120_degree_agent_plan_is_shown_and_submitted_verbatim() -> None:
    """含 120° 的代理方案必须原样出现（不再被"等价直行方案"顶替），且引擎接受它。

    不靠代理碰巧选中 120° 方案来撞测试：这里直接把一条 120° 决策写进模式状态
    （就是用户那局发生的：LLM 代理选了 1SS1S1），再看界面草稿与提交路径是否一致。
    """
    engine, state = _to_movement_phase()
    formation = next(
        item for item in state.formations.values() if item.side is Side.AXIS
    )
    actions = legal_formation_actions(engine, state, formation)
    jam_plan = next((action["plan"] for action in actions
                     if action["jams_spaced_column"]), None)
    if jam_plan is None:
        pytest.skip("该编队此刻没有含原地 120° 的合法方案")

    # 直接把这条"代理决策"写进模式状态（与 run_formation_agents 写入的形状一致）
    state.command_delay.decisions.append({
        "formation_id": formation.id, "turn": state.turn,
        "phase": state.phase.value, "selected_movement_plan": jam_plan,
        "selected_movement_action_id": f"MOVE:{jam_plan}",
    })
    agents = {order.formation_id: order.leader_plan for order in formation_orders(state, Side.AXIS)}
    assert agents.get(formation.id) == jam_plan

    _, batch, _ = RealisticCommander().choose_plan(engine, state.game_id, Side.AXIS)
    draft = {order.formation_id: order.leader_plan for order in batch.formation_movement}
    assert draft.get(formation.id) == jam_plan, (
        f"{formation.id} 的 120° 方案被草稿改写了：{jam_plan} → {draft.get(formation.id)}"
    )

    prepared, errors, _ = expand_movement_orders(engine, state, OrderBatch(
        side=Side.AXIS, phase=state.phase,
        formation_movement=formation_orders(state, Side.AXIS),
    ))
    assert errors == [], errors[:2]
    assert engine.validate_orders(state.game_id, prepared, _prepared=True).valid


# --------------------------------------------------------------------------- ② 记号可读

def test_every_action_says_what_it_does_to_the_heading() -> None:
    """每条合法机动都自带中文机动说明与结束航向 —— 不必让模型解析 1SS1S2。"""
    _, state = _to_movement_phase()
    for formation in state.formations.values():
        if formation.side is not Side.AXIS:
            continue
        actions = legal_formation_actions(IronBottomEngine(), state, formation)
        if not actions:
            continue
        leader_heading = state.ships[formation.leader_id].heading
        for action in actions:
            assert isinstance(action["manoeuvre"], str) and action["manoeuvre"]
            assert action["heading_now"] == leader_heading
            assert 1 <= int(action["ends_heading"]) <= 6
            assert isinstance(action["keeps_heading"], bool)
            assert isinstance(action["jams_spaced_column"], bool)
            # 说明与转向步数必须自洽
            assert action["keeps_heading"] == (action["heading_change_steps"] == 0)
            # 记号里 SS/PP 就是原地 120°：标旗必须与之严格一致
            assert action["jams_spaced_column"] is ("SS" in action["plan"] or "PP" in action["plan"])
        return
    pytest.skip("本局没有轴心编队可枚举")


def test_the_legend_and_the_jam_warning_reach_the_model() -> None:
    """提示词本身必须写清记号读法、结束航向字段与 120° 挤停风险。"""
    for fragment in ("S＝右转 60°", "SS＝右转 120°", "ends_heading", "keeps_heading",
                     "jams_spaced_column", "manoeuvre"):
        assert fragment in INSTRUCTION, f"提示词缺少 {fragment}"


def test_manoeuvre_text_and_turn_steps_are_right_for_known_plans() -> None:
    """记号翻译的单元级核对（含直行、单转、原地 120°）。"""
    engine = IronBottomEngine()
    cases = {
        "5": ("前进 5 格", 0),
        "5S": ("前进 5 格 → 右转 60°", 1),
        "3P3S": ("前进 3 格 → 左转 60° → 前进 3 格 → 右转 60°", 0),
        "1SS1S1": ("前进 1 格 → 右转 120°（原地调头一步） → 前进 1 格 → 右转 60° → 前进 1 格", 3),
    }
    for plan, (text, steps) in cases.items():
        commands = engine.movement_commands(MovementOrder(ship_id="x", plan=plan))
        assert manoeuvre_summary(commands) == text, plan
        assert heading_change_steps(commands) == steps, plan


# --------------------------------------------------------------------------- ③ 冻结面不漂移

def test_the_state_machine_keeps_its_own_straightening() -> None:
    """经典/真实模式的建议器行为不变：只有代理自己的方案才免于那两个改写。

    Realistic semantics are frozen - the straightening exists for the state machine's own
    routes, and this test pins that it still applies when no agent chose the plan.
    """
    engine, state = _to_movement_phase(command_delay=False)
    for side in Side:
        _, batch, _ = RealisticCommander().choose_plan(engine, state.game_id, side)
        for order in batch.formation_movement:
            commands = engine.movement_commands(
                MovementOrder(ship_id=state.formations[order.formation_id].leader_id,
                              plan=order.leader_plan))
            assert not any(command.endswith("120") for command in commands), (
                f"{side.value}/{order.formation_id}: 非命令延迟模式下仍须避免 120° 方案"
            )
