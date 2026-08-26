"""风格状态机对战基准（bench.py）：组合构造 / 轮转分布 / 小规模并行 / 确定性。

全用 tactical 状态机，无 LLM、无战报、无落盘；conftest 已删 DEEPSEEK_API_KEY。
"""

from __future__ import annotations

from collections import Counter

from iron_bottom_sound import bench
from iron_bottom_sound.tactical import PROFILES


def test_ordered_matchups_exclude_mirror() -> None:
    profiles = list(PROFILES)
    pairs = bench.ordered_matchups(profiles)
    assert len(pairs) == len(profiles) * (len(profiles) - 1)
    assert all(a != b for a, b in pairs)
    assert set(pairs) == set(
        (a, b) for a in profiles for b in profiles if a != b
    )


def test_build_games_distributes_round_robin() -> None:
    profiles = list(PROFILES)  # 6 种 → 30 个有序组合；50 局 → 各组 1~2 局
    pairs = bench.ordered_matchups(profiles)
    games = bench.build_games("IBS-S-03", profiles, total_games=50, seed_base=1)
    assert len(games) == 50
    by_pair: Counter[tuple[str, str]] = Counter()
    for _scenario, seed, a, b in games:
        by_pair[(a, b)] += 1
        assert seed in {1, 2}  # 同组合共享连续 seed 集
    assert len(by_pair) == len(pairs) == 30
    counts = list(by_pair.values())
    assert max(counts) - min(counts) <= 1  # 余数轮转，最多差 1
    assert sum(counts) == 50
    assert sum(1 for k in counts if k == 2) == 20 and sum(1 for k in counts if k == 1) == 10
    # 每组的 seed 集连续从 seed_base+1 起
    for (a, b), k in by_pair.items():
        seeds = sorted(g for _s, g, aa, bb in games if (aa, bb) == (a, b))
        assert seeds == list(range(1, k + 1))


def test_build_games_per_pair_exact() -> None:
    """--per-pair N：每对有序组合精确 N 局，seed 取 seed_base+1..seed_base+N。"""
    profiles = [*PROFILES, "random"]  # 7 种 → 42 个有序组合
    games = bench.build_games("IBS-S-01", profiles, total_games=0, seed_base=1, per_pair=30)
    assert len(games) == 42 * 30 == 1260
    by_pair: Counter[tuple[str, str]] = Counter()
    for _scenario, seed, a, b in games:
        by_pair[(a, b)] += 1
        assert seed in range(1, 31)
    assert len(by_pair) == 42
    assert set(by_pair.values()) == {30}
    for (a, b), k in by_pair.items():
        seeds = sorted(g for _s, g, aa, bb in games if (aa, bb) == (a, b))
        assert seeds == list(range(1, k + 1))  # 每对共享 seed 1..30


def test_run_benchmark_small_parallel() -> None:
    data = bench.run_benchmark(
        "IBS-S-03", profiles=["brawl", "cautious"],
        total_games=4, workers=2, seed_base=1,
    )
    assert data["meta"]["total_games"] == 4
    assert data["summary"] == {"games_attempted": 4, "games_completed": 4, "games_failed": 0}
    for p in ("brawl", "cautious"):
        s = data["stats"][p]
        assert s["axis_games"] == 2 and s["allies_games"] == 2
        assert s["total_games"] == 4
        for rate in (s["axis_win_rate"], s["allies_win_rate"], s["overall_win_rate"]):
            assert rate is None or 0.0 <= rate <= 1.0
    # 4 局各有胜者（状态机对局必分胜负），raw 全含 winner
    assert all(r.get("winner") in {"axis", "allies"} for r in data["raw"])
    # 矩阵两格合计 == 总局数
    matrix = data["matrix"]
    assert sum(sum(cell.values()) for cell in matrix.values()) == 4


def test_bench_deterministic_serial() -> None:
    """同 (scenario, profiles, games, seed_base) 串行跑两遍，逐局胜者完全一致。"""
    kwargs = dict(
        scenario="IBS-S-03", profiles=["brawl", "cautious"],
        total_games=2, workers=0, seed_base=1,
    )
    first = bench.run_benchmark(**kwargs)
    second = bench.run_benchmark(**kwargs)
    key = lambda r: (r["seed"], r["axis_profile"], r["allies_profile"], r["winner"])
    assert sorted(map(key, first["raw"])) == sorted(map(key, second["raw"]))


def test_markdown_report_renders() -> None:
    data = bench.run_benchmark(
        "IBS-S-03", profiles=["brawl", "cautious"],
        total_games=2, workers=0, seed_base=1,
    )
    md = bench._markdown_report(data)
    assert "# 风格状态机对战基准" in md
    assert "| 风格 |" in md and "| 轴\\盟 |" in md
    for p in data["stats"]:
        assert f"| {p} |" in md


def test_bench_with_random_profile() -> None:
    """random（乱打 AI）可作为 profile 参与基准；小规模跑通且逐局有胜负。"""
    data = bench.run_benchmark(
        "IBS-S-03",
        profiles=["balanced", "random"],
        total_games=4, workers=2, seed_base=1,
    )
    assert data["summary"]["games_attempted"] == 4
    assert data["summary"]["games_failed"] == 0
    assert all(r.get("winner") in {"axis", "allies"} for r in data["raw"])
    for p in ("balanced", "random"):
        s = data["stats"][p]
        assert s["total_games"] == 4
    assert "random" in data["meta"]["profiles"]


def test_bench_reinforcement_observed_on_s01() -> None:
    """IBS-S-01 增援观察：检定成功才可用；同一对组合 seed 覆盖两分支（成功/失败）。"""
    data = bench.run_benchmark(
        "IBS-S-01",
        profiles=["balanced", "cautious"],
        total_games=2, workers=0, seed_base=1,
    )
    ref = data["reinforcement"]
    assert ref is not None and ref["games"] == 2
    assert ref["roll_done"] == 2  # 第 3 回合必掷
    assert 0 <= ref["available"] <= 2
    # available 分支（若成功）入场数为 1..8；失败分支入场 0。
    for r in data["raw"]:
        rein = r["reinforcement"]
        assert rein["roll_done"] is True
        if rein["available"]:
            assert rein["entered"] >= 1
        else:
            assert rein["entered"] == 0


def test_bench_serial_no_reinforcement_on_s03() -> None:
    """IBS-S-03 无增援：reinforcement 字段为 None，报告不含增援节。"""
    data = bench.run_benchmark(
        "IBS-S-03", profiles=["brawl", "cautious"],
        total_games=2, workers=0, seed_base=1,
    )
    assert data["reinforcement"] is None
    assert "增援观察" not in bench._markdown_report(data)
