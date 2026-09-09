"""大战场（92×78）副本生成器：为既有自定义剧本做一张「大地图」重排副本。

规则：只重排初始舰坐标。保留 ships 顺序与每舰 id/side/heading/speed/asset/
flagship/name；只改 position。每个编队按真实模式的 resolve 同款推导重排——
领舰锚定新坐标、跟从舰沿「正尾」（opposite heading）每格 astern 一步，与
``realistic_command._layout_for_order``（spacing=1）逐字节一致，保证「存档坐标
== resolve 首回合队形」。

布局：轴舰队整体西移、同盟舰队整体东移；正面间距 G（列）是可调旋钮。行向把
每侧编队按原领舰显示行次序分配到 92×78 中区、两军隔条交错（轴=偶数槽、
盟=奇数槽），槽位间距保证**同侧轴向 r 行互不重合**（resolve 链固定轴向 r，两
链只要 r 不同就绝不重叠）。两侧留海 buffer。

产物是一份合法 CustomScenarioInput payload（新 id、标题后缀、新 map 尺寸）。
源剧本（IBS-CUSTOM-21E8908FE969 等）绝不被写入或修改。生成后应经
``validate_definition`` 校验并在 92×78 上跑冒烟局。
"""

from __future__ import annotations

import argparse
import json
from copy import deepcopy
from pathlib import Path
from typing import Any

from .custom_scenarios import (
    CustomScenarioInput,
    new_id,
    validate_definition,
    with_engine_default_formations,
)
from .data import register_custom_scenario, unregister_custom_scenario
from .models import HexCoord
from .storage import GameRepository

# 大地图尺寸（46×39 各乘二）。列/行容量上限在 models 里远大于此。
BIG_MAP_COLUMNS = 92
BIG_MAP_ROWS = 78

# 持久化用的稳定副本 id：重复运行（标定换 G 重存）只覆盖同一条，不堆副本。
BIG_MAP_SCENARIO_ID = "IBS-CUSTOM-BIG-GRAND"

_TITLE_SUFFIX = " · 大战场 92×78"


class RefitError(ValueError):
    """重排失败：几何不满足约束（间距超出棋盘、行碰撞等）。"""


def _opposite_heading(heading: int) -> int:
    return ((heading + 2) % 6) + 1


def _display_index(coord: HexCoord) -> int:
    return coord.r + (coord.q - (coord.q & 1)) // 2


def _hex_at(display_index: int, q: int) -> HexCoord:
    return HexCoord(q=q, r=display_index - (q - (q & 1)) // 2)


def _chain_hexes(orders: list[dict], ship_by_id: dict[str, dict], *, columns: int, rows: int) -> list[list[HexCoord]]:
    """按真实 resolve 语义重放每编队初始链：领舰坐标 + astern spacing=1。

    orders：顶层 ``formations[side]``（每项 ship_ids 领舰在前）。链按 order
    ship_ids 顺序；任何一艘无坐标都会直接抛错（本剧本全布置）。
    """
    chains: list[list[HexCoord]] = []
    for order in orders:
        members = [sid for sid in (order.get("ship_ids") or []) if sid in ship_by_id]
        if not members:
            chains.append([])
            continue
        leader_entry = ship_by_id[members[0]]
        if not leader_entry.get("position"):
            raise RefitError(f"{members[0]}（{order.get('formation_id')} 领舰）没有初始坐标")
        heading = int(order.get("heading") or leader_entry.get("heading") or 1)
        astern = _opposite_heading(heading)
        cursor = HexCoord.from_label(str(leader_entry["position"]).upper())
        chain = [cursor]
        for sid in members[1:]:
            if not ship_by_id[sid].get("position"):
                raise RefitError(f"{sid}（{order.get('formation_id')} 跟随舰）没有初始坐标")
            cursor = cursor.neighbor(astern, columns=columns, rows=rows)
            chain.append(cursor)
        chains.append(chain)
    return chains


def _envelope(chains: list[list[HexCoord]]) -> tuple[int, int]:
    qs = [hex_.q for chain in chains for hex_ in chain]
    return (min(qs), max(qs)) if qs else (0, -1)


def _min_opposing_distance(
    axis_chains: list[list[HexCoord]], allies_chains: list[list[HexCoord]]
) -> int:
    """实测最近敌对舰对距离（轴向 hex 距离，即最小移动步数）。"""
    best: int | None = None
    for a in axis_chains:
        for b in allies_chains:
            for ha in a:
                for hb in b:
                    d = ha.distance(hb)
                    if best is None or d < best:
                        best = d
    return int(best if best is not None else -1)


def _row_slots(n_axis: int, n_allies: int, *, lo: int, hi: int) -> tuple[list[int], list[int]]:
    """把两军编队隔条交错分到 [lo, hi] 显示行窗。

    轴=偶数槽、盟=奇数槽；同侧槽距 ≈ 2*step，保证 leader 显示行错开 >7 行，
    同侧轴向 r 必不重合（q 只差 ≤ ~10 → floor(q/2) 差 ≤5，显示行差 ≥7 已足够）。
    """
    total = n_axis + n_allies
    if total < 2:
        return ([int((lo + hi) / 2)] * n_axis, [int((lo + hi) / 2)] * n_allies)
    step = (hi - lo) / (total - 1)
    rows = {k: int(round(lo + k * step)) for k in range(total)}
    axis_rows = [rows[2 * i] for i in range(n_axis)]
    allies_rows = [rows[2 * i + 1] for i in range(n_allies)]
    return axis_rows, allies_rows


def build_big_map_copy(
    source_definition: dict[str, Any],
    *,
    columns: int = BIG_MAP_COLUMNS,
    rows: int = BIG_MAP_ROWS,
    gap: int = 24,
    west_buffer: int = 8,
    east_buffer: int = 8,
    row_buffer: int = 10,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """由源定义生成大战场 payload。

    返回 (payload, stats)。payload 可直接 ``CustomScenarioInput.model_validate``；
    stats 记录几何审计（每侧行/列跨度、正面间距 G、实测最近敌对舰距离等），
    供标定与报告使用。不改动 ``source_definition``。
    """
    if gap < 0 or west_buffer < 0 or east_buffer < 0 or row_buffer < 0:
        raise RefitError(f"Invalid refit parameters gap={gap}")
    copy = deepcopy(source_definition)
    copy.pop("id", None)

    ships = copy.setdefault("ships", [])
    ship_by_id = {entry["id"]: entry for entry in ships}
    orders_by_side: dict[str, list[dict]] = {}
    for side in ("axis", "allies"):
        side_orders = (copy.get("formations") or {}).get(side) or []
        present = [o for o in side_orders if o.get("ship_ids")]
        orders_by_side[side] = present
        if not present:
            raise RefitError(f"side {side} has no authored formations to refit")
        for order in present:
            for sid in order["ship_ids"]:
                entry = ship_by_id.get(sid)
                if entry is None:
                    raise RefitError(f"{sid} referenced by formation but missing from ships")
                if entry["side"] != side:
                    raise RefitError(f"{sid}: side mismatch with formation {order.get('formation_id')}")

    # ── 原几何度量：队形链（领舰坐标 + astern spacing=1）与包络 ──────────────
    chains_orig: dict[str, list[list[HexCoord]]] = {}
    for side, orders in orders_by_side.items():
        chains_orig[side] = _chain_hexes(orders, ship_by_id, columns=columns, rows=rows)

    axis_chains, allies_chains = chains_orig["axis"], chains_orig["allies"]
    axis_min, axis_max = _envelope(axis_chains)
    allies_min, allies_max = _envelope(allies_chains)
    axis_width = axis_max - axis_min
    allies_width = allies_max - allies_min

    # ── 列向：两军对称留边摆放，正面间距 gap（列）可调 ──────────────────────
    used = axis_width + allies_width + gap + 1
    avail = columns - west_buffer - east_buffer
    if used > avail:
        raise RefitError(
            f"gap={gap} too wide: fleets need {used} columns, only {avail} available "
            f"inside buffers ({west_buffer}+{east_buffer})"
        )
    extra = avail - used
    axis_min_new = west_buffer + extra // 2
    dq_axis = axis_min_new - axis_min
    axis_max_new = axis_max + dq_axis
    allies_min_new = axis_max_new + gap + 1
    dq_allies = allies_min_new - allies_min
    allies_max_new = allies_max + dq_allies
    if allies_max_new > columns - 1 - east_buffer:
        raise RefitError("Allies envelope does not fit inside east buffer")

    # ── 行向：每侧按原领舰显示行升序排到隔条槽位 ────────────────────────────
    lo, hi = row_buffer, rows - 1 - row_buffer
    axis_rank = sorted(range(len(axis_chains)), key=lambda i: _display_index(axis_chains[i][0]))
    allies_rank = sorted(range(len(allies_chains)), key=lambda i: _display_index(allies_chains[i][0]))
    axis_rows, allies_rows = _row_slots(len(axis_chains), len(allies_chains), lo=lo, hi=hi)
    rows_of = {"axis": dict(zip(axis_rank, axis_rows)), "allies": dict(zip(allies_rank, allies_rows))}
    dq = {"axis": dq_axis, "allies": dq_allies}

    # ── 逐队重排：领舰新坐标 + astern spacing=1 重放 ────────────────────────
    chains_new: dict[str, list[list[HexCoord]]] = {}
    for side, orders in orders_by_side.items():
        rebuilt: list[list[HexCoord]] = []
        for index, (order, chain) in enumerate(zip(orders, chains_orig[side])):
            if not chain:
                rebuilt.append([])
                continue
            leader_orig = chain[0]
            leader_id = order["ship_ids"][0]
            heading = int(order.get("heading") or ship_by_id[leader_id].get("heading") or 1)
            astern = _opposite_heading(heading)
            q_new = leader_orig.q + dq[side]
            disp_new = rows_of[side][index]
            leader_new = _hex_at(disp_new, q_new)
            if not (0 <= leader_new.q < columns and 0 <= _display_index(leader_new) < rows):
                raise RefitError(f"{order.get('formation_id')} leader lands off-map {leader_new.label}")
            cursor = leader_new
            line = [cursor]
            for _ in chain[1:]:
                cursor = cursor.neighbor(astern, columns=columns, rows=rows)
                line.append(cursor)
            rebuilt.append(line)
        chains_new[side] = rebuilt

    # 同侧轴向 r 行必须互不重合（resolve 链沿固定 r，r 相同才会碰撞）。
    for side, rebuilt in chains_new.items():
        r_used: set[int] = set()
        for line in rebuilt:
            if not line:
                continue
            if line[0].r in r_used:
                raise RefitError(f"{side}: two formations share axial row r={line[0].r}")
            r_used.add(line[0].r)

    # ── 写回 ships 位置 + 顶层 formations 对齐（heading/spacing/领舰）────────
    label_of: dict[str, str] = {}
    for side, orders in orders_by_side.items():
        for order, line in zip(orders, chains_new[side]):
            order["spacing"] = 1
            order["heading"] = int(ship_by_id[order["ship_ids"][0]].get("heading") or 1)
            order["leader_id"] = order["ship_ids"][0]
            for sid, hex_ in zip(order["ship_ids"], line):
                if label_of.setdefault(sid, hex_.label) != hex_.label:
                    raise RefitError(f"{sid} appears in two formations")
                ship_by_id[sid]["position"] = hex_.label
            order["ship_ids"] = order["ship_ids"][: len(line)]

    # ── 元信息：尺寸 + 标题后缀 ──────────────────────────────────────────────
    copy["title"] = f"{copy.get('title', '')}{_TITLE_SUFFIX}"
    copy["map_columns"] = columns
    copy["map_rows"] = rows
    copy["printed_columns"] = columns
    copy["printed_rows"] = rows
    copy.pop("id", None)

    # ── 几何审计 stats（基于新几何）──────────────────────────────────────────
    def span(side: str) -> dict[str, Any]:
        lo_, hi_ = _envelope(chains_new[side])
        rows_ = [_display_index(line[0]) for line in chains_new[side] if line]
        return {
            "n_ships": sum(len(line) for line in chains_new[side]),
            "n_formations": sum(1 for line in chains_new[side] if line),
            "q_min": lo_,
            "q_max": hi_,
            "leader_row_min": min(rows_) if rows_ else None,
            "leader_row_max": max(rows_) if rows_ else None,
        }

    stats = {
        "columns": columns,
        "rows": rows,
        "gap_front_columns": gap,
        "axis": span("axis"),
        "allies": span("allies"),
        "front_clearance": gap,
        "min_opposing_distance": _min_opposing_distance(
            chains_new["axis"], chains_new["allies"]
        ),
        "unique_hexes": sum(len(line) for line in chains_new["axis"])
        + sum(len(line) for line in chains_new["allies"]),
    }
    return copy, stats


def save_big_map_copy(
    source_id: str,
    *,
    repository: GameRepository | None = None,
    gap: int = 24,
    columns: int = BIG_MAP_COLUMNS,
    rows: int = BIG_MAP_ROWS,
    scenario_id: str = BIG_MAP_SCENARIO_ID,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """从仓库源剧本建大战场副本 → 校验 → 持久化（稳定 id，可覆盖重存）。"""
    repository = repository or GameRepository()
    source = repository.custom_scenario(source_id)
    payload, stats = build_big_map_copy(source, gap=gap, columns=columns, rows=rows)
    validated = CustomScenarioInput.model_validate(payload)
    definition = with_engine_default_formations(validated.model_dump(mode="json"))
    definition["id"] = scenario_id
    errors = validate_definition(scenario_id, definition)
    if errors:
        unregister_custom_scenario(scenario_id)
        raise RefitError("Validation failed: " + " | ".join(errors))
    try:
        repository.delete_custom_scenario(scenario_id)
    except KeyError:
        pass
    repository.save_custom_scenario(scenario_id, definition)
    register_custom_scenario(definition)
    return definition, stats


def main() -> int:
    parser = argparse.ArgumentParser(description="Build and persist the 92×78 big-map copy of a custom scenario")
    parser.add_argument("--source", required=True, help="源自定义剧本 id，如 IBS-CUSTOM-21E8908FE969")
    parser.add_argument("--gap", type=int, default=24, help="正面间距（列），标定旋钮")
    parser.add_argument("--save", action="store_true", help="校验通过后持久化到 sqlite 并注册")
    parser.add_argument("--db", default=None, help="GameRepository DB 路径（默认工作目录 iron-bottom-sound.sqlite3）")
    parser.add_argument("--out", default=None, help="审计报告输出文件（UTF-8）")
    args = parser.parse_args()

    repository = GameRepository(args.db) if args.db else GameRepository()
    if args.save:
        definition, stats = save_big_map_copy(args.source, repository=repository, gap=args.gap)
        scenario_id = definition["id"]
        mode = "saved"
    else:
        source = repository.custom_scenario(args.source)
        _, stats = build_big_map_copy(source, gap=args.gap)
        scenario_id = "(dry-run)"
        mode = "dry-run"
    report = {"mode": mode, "scenario_id": scenario_id, "source": args.source, "stats": stats}
    text = json.dumps(report, ensure_ascii=False, indent=2)
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
    print(json.dumps(report, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
