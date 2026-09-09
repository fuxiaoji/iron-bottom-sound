#!/usr/bin/env python3
"""生成虚构大剧本 IBS-S-FM-01「铁底湾的回响 · 午夜舰队决战」。

编队设计参考历史雷击编队：
- 日军挺身攻击队（第二次瓜达尔卡纳尔岛海战，阿部弘毅：战列舰先行夜战突入）
- 日军第一游击部队本队（苏里高/萨马之余波推演：大和级为中心的战列纵队）
- 日军东京快车驱逐突击队（田中赖三：多梯队雷击队）
- 盟军 TF34 快速战列纵队（李少将：衣阿华级单纵）
- 盟军第 23 驱逐舰中队（伯克上校「31 节伯克」五舰单纵）
- 盟军巡洋舰纵队（安斯沃思 TF36.1：驱逐前卫-巡洋舰-驱逐后卫）

本脚本只生成想定数据（YAML）；部署坐标用引擎 HexCoord 编解码计算，
一般模式与真实模式（编队提案）都可直接开局。
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend" / "src"))

import yaml

from iron_bottom_sound.counter_assets import asset_for
from iron_bottom_sound.models import HexCoord
from iron_bottom_sound.ship_records import load_ship_records

REPO = Path(__file__).resolve().parents[1]
OUT = REPO / "resources" / "derived" / "structured" / "scenarios" / "scenario-fm01.yaml"

records = load_ship_records()

# ---- 编队定义（ships 顺序 = 纵队前后；第一个是领舰） ------------------------
AXIS_FORMATIONS = [
    ("axis-standby-strike", "挺身夜战战队（阿部弘毅式：高速战巡先行突入）",
     ["IBS-U-IJN-HIEI", "IBS-U-IJN-KIRISHIMA", "IBS-U-IJN-OWARI", "IBS-U-IJN-AMAGI", "IBS-U-IJN-AKAGI"]),
    ("axis-main-battle-line", "第一游击部队本队（大和级为中心的战列纵队）",
     ["IBS-U-IJN-ERMA-YAMATO", "IBS-U-IJN-ERMA-MUSASHI", "IBS-U-IJN-ERMA-SHINANO", "IBS-U-IJN-NAGATO", "IBS-U-IJN-MUTSU"]),
    ("axis-heavy-cruiser-line", "重巡战队（直卫警戒列）",
     ["IBS-U-IJN-ATAGO", "IBS-U-IJN-TAKAO", "IBS-U-IJN-NACHI", "IBS-U-IJN-MYOKO", "IBS-U-IJN-HAGURO", "IBS-U-IJN-CHOKAI"]),
    ("axis-light-cruiser-screen", "轻巡警戒队",
     ["IBS-U-IJN-AGANO", "IBS-U-IJN-JINTSU-I", "IBS-U-IJN-SENDAI", "IBS-U-IJN-NAGARA"]),
    ("axis-torpedo-squadron-1", "第一雷击队（岛风领雷，东京快车突击队式）",
     ["IBS-U-IJN-ERMA-SHIMAKAZE", "IBS-U-IJN-YUKIKAZE", "IBS-U-IJN-SHIGURE", "IBS-U-IJN-NAGANAMI", "IBS-U-IJN-MAKINAMI"]),
    ("axis-torpedo-squadron-2", "第二雷击队",
     ["IBS-U-IJN-YUGUMO", "IBS-U-IJN-AKIGUMO", "IBS-U-IJN-KAZEKUMO", "IBS-U-IJN-TAKANAMI", "IBS-U-IJN-ASAGUMO"]),
    ("axis-old-cruiser-feint", "第三梯队（旧式巡洋舰佯动队）",
     ["IBS-U-IJN-FURUTAKA", "IBS-U-IJN-KAKO-I", "IBS-U-IJN-AOBA", "IBS-U-IJN-KINUGASA", "IBS-U-IJN-YUBARI", "IBS-U-IJN-TENRYU", "IBS-U-IJN-TATSUTA"]),
    ("axis-akizuki-rear", "秋月型殿后队（对空警戒/诱饵）",
     ["IBS-U-IJN-AKIZUKI", "IBS-U-IJN-TERUZUKI", "IBS-U-IJN-NIIZUKI", "IBS-U-IJN-WAKATSUKI"]),
]

ALLIES_FORMATIONS = [
    ("allies-fast-battle-line", "TF34 快速战列纵队（李式单纵）",
     ["IBS-U-USN-ERMA-IOWA", "IBS-U-USN-ERMA-NEW-JERSEY", "IBS-U-USN-ERMA-MISSOURI", "IBS-U-USN-ERMA-WISCONSIN",
      "IBS-U-USN-UNNAMED-T01-R03", "IBS-U-USN-WASHINGTON", "IBS-U-USN-SOUTH-DAKOTA"]),
    ("allies-old-battle-line", "旧战列分队（殿后火力线）",
     ["IBS-U-USN-COLORADO", "IBS-U-USN-WEST-VIRGINIA"]),
    ("allies-big-cruiser-scout", "大巡侦察战队（阿拉斯加级+列克星敦级）",
     ["IBS-U-USN-UNNAMED-T01-R06", "IBS-U-USN-UNNAMED-T01-R07", "IBS-U-USN-UNNAMED-T01-R08",
      "IBS-U-USN-ERMA-ALASKA", "IBS-U-USN-ERMA-GUAM"]),
    ("allies-heavy-cruiser-north", "北线重巡队",
     ["IBS-U-USN-SAN-FRANCISCO", "IBS-U-USN-MINNEAPOLIS", "IBS-U-USN-NEW-ORLEANS",
      "IBS-U-USN-UNNAMED-T01-R12", "IBS-U-USN-UNNAMED-T01-R13", "IBS-U-USN-UNNAMED-T01-R20"]),
    ("allies-heavy-cruiser-south", "南线重巡队（含澳舰，呼应萨沃岛之夜）",
     ["IBS-U-USN-PENSACOLA", "IBS-U-USN-SALT-LAKE-CITY", "IBS-U-USN-NORTHAMPTON",
      "IBS-U-USN-VINCENNES", "IBS-U-USN-QUINCY", "IBS-U-USN-ASTORIA",
      "IBS-U-RAN-CANBERRA", "IBS-U-RAN-AUSTRALIA"]),
    ("allies-light-cruiser-line", "轻巡纵列（布鲁克林/克利夫兰/亚特兰大级）",
     ["IBS-U-USN-HELENA", "IBS-U-USN-ST-LOUIS", "IBS-U-USN-HONOLULU", "IBS-U-USN-BOISE",
      "IBS-U-USN-UNNAMED-T01-R23", "IBS-U-USN-UNNAMED-T01-R24", "IBS-U-USN-UNNAMED-T01-R25",
      "IBS-U-USN-UNNAMED-T01-R26", "IBS-U-USN-UNNAMED-T01-R27", "IBS-U-USN-UNNAMED-T01-R28", "IBS-U-USN-UNNAMED-T01-R29"]),
    ("allies-desron-23", "第 23 驱逐舰中队（伯克「31 节」五舰单纵）",
     ["IBS-U-USN-CF-AUSBURNE", "IBS-U-USN-CLAXTON", "IBS-U-USN-DYSON", "IBS-U-USN-CONVERSE", "IBS-U-USN-SPENCE"]),
    ("allies-desron-screen", "警戒驱逐队（前哨/鱼雷反击）",
     ["IBS-U-USN-NICHOLAS", "IBS-U-USN-OBANNON", "IBS-U-USN-TAYLOR", "IBS-U-USN-LA-VALLETTE",
      "IBS-U-USN-UNNAMED-T01-R51", "IBS-U-USN-UNNAMED-T01-R52"]),
]

FLAGSHIPS = {"axis": "IBS-U-IJN-ERMA-YAMATO", "allies": "IBS-U-USN-ERMA-IOWA"}

# 初始航速：主力 5，巡洋 5，驱逐 5-6（按记录速度轨最高值-1，未超标则 5）
SPEED_OVERRIDES = {
    "IBS-U-IJN-ERMA-SHIMAKAZE": 6,
}


def display_label(q: int, display_row: int) -> str:
    """把（0 基列号, 1 基显示行号）转成引擎六边形标签。"""
    axial = display_row - 1 - (q - (q & 1)) // 2
    return HexCoord(q=q, r=axial).label


def formation_positions(base_col: int, rows: int, count: int, heading: int) -> list[str]:
    """把编队按 1 格间距排成纵队：领舰在 rows，后舰向舰尾方向逐格排列。"""
    step = -1 if heading == 2 else 1  # 日军向东南（航向2），纵队向西北收拢；盟军相反
    return [display_label(base_col, rows + step * index) for index in range(count)]


ships: list[dict] = []

for side, formations, heading, start_col, lead_row in (
    ("axis", AXIS_FORMATIONS, 2, 4, 20),
    ("allies", ALLIES_FORMATIONS, 5, 48, 60),
):
    for index, (formation_id, note, member_ids) in enumerate(formations):
        col = start_col + index * 5
        labels = formation_positions(col, lead_row, len(member_ids), heading)
        for ship_id, label in zip(member_ids, labels):
            record = records[ship_id]
            ships.append({
                "id": ship_id,
                "name": record.name,
                "side": side,
                "position": label,
                "heading": heading,
                "speed": SPEED_OVERRIDES.get(ship_id, min(5, record.maximum_speed_cycle[0])),
                "asset": asset_for(ship_id, record.name, record.ship_type),
                "flagship": ship_id == FLAGSHIPS[side],
            })

# 真实模式默认编队（与部署一致）
engine_default_formations = {
    "axis": [{"id": fid, "role": "line_ahead", "ships": members, "note": note}
             for fid, note, members in AXIS_FORMATIONS],
    "allies": [{"id": fid, "role": "line_ahead", "ships": members, "note": note}
               for fid, note, members in ALLIES_FORMATIONS],
}

definition = {
    "id": "IBS-S-FM-01",
    "number": "FM-01",
    "title": "铁底湾的回响·午夜舰队决战（虚构想定）",
    "date": "1944-10-25",
    "status": "playable",
    "source": {
        "document": "user_commissioned_fictional_scenario",
        "status": "design",
        "design_notes": (
            "虚构推演：参考1942-1944所罗门夜战与莱特湾海战编成；"
            "编队参考历史雷击编队（挺身攻击队/东京快车/31节伯克/李式战列纵队）。"
            "舰船数据全部来自已核验记录（记录手册/舰级卡/二马扩展）。"
        ),
    },
    "map_columns": 92,
    "map_rows": 78,
    "printed_columns": 92,
    "printed_rows": 78,
    "turns": 14,
    "visibility": {"axis": 18, "allies": 22},
    "optional_rules": [],
    "available_optional_rules": [hidden_contacts := "hidden_contacts", "radar", "star_shells",
                                 "searchlights", "malfunction_66", "squalls", "smoke",
                                 "silhouettes", "hidden_damage", "blind_torpedoes"],
    "setup": {
        "mode": "scenario_positions",
        "engine_default_note": "engine_default_formations 参考历史雷击编队（见各编队注记），仅为真实模式直接开局的默认提案。",
        "engine_default_formations": engine_default_formations,
    },
    "victory": {
        "kind": "victory_points",
        "points_per_three_hull_lost": 1,
        "leader_margin": 15,
        "draw_if_margin_below": 15,
        "evaluated_at": "end_of_turn_14",
    },
    "special_rules": [
        {"id": "IBS-S-FM-01-R1", "text": "本想定为虚构推演（不属于官方想定手册）：1944 年 10 月 25 日夜，联合舰队倾主力突入铁底湾炮击亨德森机场，盟军以全部可用主力舰封锁峡口。"},
        {"id": "IBS-S-FM-01-R2", "text": "双方旗舰：联合舰队大和（第一游击部队本队），盟军衣阿华（TF34 快速战列纵队）。"},
        {"id": "IBS-S-FM-01-R3", "text": "战场为 92×78 大战场海图；能见度日军 18 格、盟军 22 格（盟军雷达优势）。"},
        {"id": "IBS-S-FM-01-R4", "text": "编队提案参考历史雷击编队：日军挺身夜战战队（阿部 弘毅式）、第一/第二雷击队（田中赖三东京快车式）；盟军 TF34 战列纵队（李 式）、第 23 驱逐舰中队（伯克「31 节」单纵）。"},
        {"id": "IBS-S-FM-01-R5", "text": "14 回合结束时统计胜利分：每造成 3 点船体损失计入 1 分；领先 15 分或更多为胜利者，其他结果为平局。"},
    ],
    "ships": ships,
}

OUT.write_text(yaml.safe_dump(definition, allow_unicode=True, sort_keys=False, width=120), encoding="utf-8")
print(f"wrote {OUT} with {len(ships)} ships")
# 位置唯一性检查
labels = [s["position"] for s in ships]
assert len(labels) == len(set(labels)), "重复位置"
print("positions unique OK")
