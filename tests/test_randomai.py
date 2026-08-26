"""乱打 AI（randomai.RandomCommander）：随机合法选择、确定性、兜底不失败。

全走引擎只读候选接口产订单；每局提交前 `validate_orders` 复核合法。
无 LLM、无战报、无落盘；conftest 已删 DEEPSEEK_API_KEY。
"""

from __future__ import annotations

from iron_bottom_sound.engine import IronBottomEngine
from iron_bottom_sound.match import run_match
from iron_bottom_sound.models import Phase, Side
from iron_bottom_sound.randomai import RandomCommander


def test_random_commander_orders_always_legal() -> None:
    """乱打 AI 在剧本一（含增援 + 想定禁射）与剧本三全流程产出的订单全部合法。"""
    for scenario in ("IBS-S-01", "IBS-S-03"):
        engine = IronBottomEngine()
        state = engine.reset(scenario, 1)
        commander = RandomCommander()
        while state.phase != Phase.COMPLETE:
            if state.phase in {Phase.CONTACT_SETUP, Phase.REINFORCEMENT,
                               Phase.MOVEMENT_PLANNING, Phase.TORPEDO_PLANNING, Phase.GUNNERY}:
                for side in Side:
                    batch = commander.choose_orders(engine, state.game_id, side)
                    result = engine.submit_orders(state.game_id, batch)
                    assert result.valid, f"{scenario} {state.phase} {side}: {result.errors}"
            engine.advance(state.game_id)
            state = engine.get(state.game_id)


def test_random_match_runs_to_completion() -> None:
    """乱打 AI 对乱打 AI 在剧本一打满 7 回合不崩溃不卡死；结果要么有胜方要么平局。"""
    for seed in (1, 2):
        report, engine, _ = run_match(
            scenario_id="IBS-S-01", axis="random", allies="random", seed=seed,
        )
        state = engine.get(report.game_id)
        assert report.completed and report.passed
        assert state.turn == 7
        # 想定一允许平局：胜利点差<4 时引擎不设胜方（victory_reason=平局）。
        assert report.winner in {Side.AXIS, Side.ALLIES} or (
            report.winner is None and report.victory_reason and "平局" in report.victory_reason
        )


def test_random_match_deterministic_across_players() -> None:
    """乱打 AI 对战术 AI：同 seed 两遍逐局完全一致（AI RNG 纯整数派生）。"""
    kwargs = dict(scenario_id="IBS-S-01", axis="random", allies="tactical",
                  allies_profile="cautious", seed=11)
    first = run_match(**kwargs)
    second = run_match(**kwargs)

    def outcome(run):
        state = run[1].get(run[0].game_id)
        return (run[0].winner, run[0].victory_reason, state.reinforcement_available,
                sorted((s.id, s.position.label if s.position else None)
                       for s in state.ships.values()))

    assert outcome(first) == outcome(second)


def test_random_contacts_empty_without_reserve() -> None:
    """现役想定无 contact_reserve_positions → 随机隐蔽编队返回空（不产非法订单）。"""
    engine = IronBottomEngine()
    state = engine.reset("IBS-S-03", 1)
    assert not state.contact_reserve_positions
    commander = RandomCommander()
    for side in Side:
        orders = commander._random_contacts(engine, state.game_id, side, commander._rng(state, side))
        assert orders == []
