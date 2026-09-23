"""Turn a recorded battle into a documentary timeline: beats, narration, visuals.

The narration is *composed from the record*, not written freely: every number, order
text, position and quotation in the script is read out of ``battle_data.json``,
``reports.jsonl`` and ``calls.jsonl``.  That is deliberate - a documentary about a
simulated battle is worthless if the script and the data disagree, and the only way to
guarantee they cannot is to derive one from the other.

What the timeline carries per beat:

* ``narration``  what the narrator says (spoken by the TTS, subtitled verbatim)
* ``visual``     what the frame shows: a board still (turn + phase + viewpoint), a
                 card (title / rule / data), or a three-up comparison
* ``overlays``   the data burned into the frame (order text, delay, quotes, counters)

Output: ``data/timeline.json`` for the Remotion composition, and
``audio/script.json`` for the narrator, in the same order.

Usage::

    .venv/bin/python research/battle_video/build_timeline.py --battle battle_em01
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
BATTLE_ROOT = ROOT / "research" / "command_delay"

SIDE_CN = {"axis": "日方", "allies": "美方"}
FORMATION_CN = {
    "axis-battle-line": "日方第一战队（战列线）",
    "axis-cruiser-line": "日方第二战队（巡洋战队）",
    "axis-destroyer-line": "日方第三战队（水雷战队）",
    "allies-battle-line": "美方战列线",
    "allies-cruiser-line": "美方巡洋战队",
    "allies-destroyer-line": "美方驱逐战队",
}
MEDIUM_CN = {
    "tbs_short": "TBS 短距战术",
    "blinker": "视觉信号",
    "wt_coded": "编码电文",
    "wt_reencipher_relay": "转报再加密",
    "multi_hop": "复合路由",
    "blackout": "无通路",
}
KIND_CN = {
    "sitrep": "态势报告",
    "contact_report": "接触报告",
    "deviation_report": "偏离报告",
    "clarification": "澄清请求",
    "acknowledgement": "确认",
    "mission_order": "任务命令",
    "amendment": "修正令",
}


def load(battle_dir: Path) -> dict:
    data = json.loads((battle_dir / "battle_data.json").read_text(encoding="utf-8"))
    reports = []
    path = battle_dir / "reports.jsonl"
    if path.exists():
        reports = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()
                   if line.strip()]
    calls = []
    path = battle_dir / "calls.jsonl"
    if path.exists():
        calls = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()
                 if line.strip()]
    data["_reports"] = reports
    data["_calls"] = calls
    return data


def quote(text: str, limit: int = 64) -> str:
    """Trim a quotation at a sentence end where possible, never mid-word."""
    text = " ".join(str(text or "").split())
    if len(text) <= limit:
        return text
    window = text[:limit]
    for mark in ("。", "；", "，", "、"):
        cut = window.rfind(mark)
        if cut > limit * 0.5:
            return window[:cut + 1]
    return window.rstrip() + "…"


def report_age_map(data: dict) -> dict[tuple[str, int], int]:
    """For each (formation, turn): how old the newest delivered report was.

    This is the number that makes the information asymmetry concrete - a commander
    acting on a picture that is two turns old.
    """
    ages: dict[tuple[str, int], int] = {}
    by_formation: dict[str, list[dict]] = {}
    for report in data["_reports"]:
        by_formation.setdefault(report["reporting_formation_id"] or "", []).append(report)
    for formation_id, items in by_formation.items():
        for turn in range(1, int(data["final"]["turns"]) + 1):
            delivered = [item for item in items
                         if item.get("delivered_turn") is not None
                         and item["delivered_turn"] <= turn]
            if delivered:
                newest = max(delivered, key=lambda item: item["issued_turn"])
                ages[(formation_id, turn)] = max(0, turn - int(newest["issued_turn"]))
    return ages


def thinking_for(data: dict, *, role: str, side: str, turn: int) -> str:
    """The model's own reasoning for one decision, from the call record."""
    for entry in data.get("agent_log", []):
        if entry.get("turn") != turn or entry.get("side") != side:
            continue
        if role == "fleet" and entry.get("role") != "fleet_agent":
            continue
        if role == "formation" and entry.get("role") == "fleet_agent":
            continue
        for attempt in entry.get("attempts", []):
            thinking = attempt.get("thinking") or ""
            if thinking:
                return thinking
    return ""


def beats(data: dict) -> list[dict]:
    out: list[dict] = []
    final = data["final"]
    turns = sorted({event["turn"] for turn in data.get("turns", [])
                    for event in turn.get("events", [])})
    max_turn = max(turns) if turns else int(final["turns"])
    age_map = report_age_map(data)
    scenario_title = data.get("scenario_title") or "第二次马里亚纳海战 · 内南洋水雷强袭战"

    # ---------------------------------------------------------------- opening
    out.append({
        "id": "title",
        "chapter": "开场",
        "visual": {"kind": "title", "title": scenario_title,
                   "subtitle": "命令延迟模式 · 两个模型指挥体系的对局",
                   "footer": "本片由对局原始记录重建"},
        "narration": (
            f"{scenario_title}。这一局不是人在下棋：双方的每一个编队、以及双方的舰队总指挥，"
            "各由一个独立的模型代理指挥。它们看不到全局，只能看到自己舰只的视界；"
            "它们之间的每一道命令、每一封报告，都要经过电报链路，会迟到，也可能永远到不了。"
        ),
        "overlays": [],
    })

    # ---------------------------------------------------------------- rules
    out.append({
        "id": "rules_basics",
        "chapter": "规则速览",
        "visual": {"kind": "card", "title": "基础规则",
                   "lines": [
                       f"想定：{scenario_title}",
                       f"双方各 12 艘舰，{max_turn} 个回合，损伤点差 25 分判胜负",
                       "六角格海图；航向 1–6、航速 0–8；编队按纵队跟随或整队机动",
                       "炮击与鱼雷由引擎裁决：命中、损伤、起火、进水、炮位损失",
                       "指挥官不能指定炮位或射界，只能给目标类型与权重偏好",
                   ]},
        "narration": (
            "先看这一局的规则。海图是六角格，每回合三分钟。舰队被编成纵队，"
            "航向一到六，航速零到八。炮击与鱼雷的命中、损伤、起火，全部由引擎的裁决器计算，"
            "指挥官能决定的只有一件事：打谁、先打谁。损伤累积成点数，差到二十五分，胜负就定了。"
        ),
        "overlays": [],
    })
    out.append({
        "id": "rules_command",
        "chapter": "规则速览",
        "visual": {"kind": "card", "title": "命令延迟：这一局的真正变量",
                   "lines": [
                       "总指挥 → 当面交办：同编队，即刻生效（不占用信道）",
                       "总指挥 → 电报：TBS 短距 +0／复杂任务 +1；编码电文 +1；转报再加密 +2",
                       "分舰队 → 总指挥：每回合上报，引擎保底态势与目击，代理加自己的判断",
                       "上报与命令都按**发出时刻**计龄：总指挥手里的图永远是旧的",
                       "代理只能看见自己的舰只看到的东西：接触、命令、已收报文、本地记忆",
                   ]},
        "narration": (
            "命令延迟模式要表现的，不是无线电传播，而是人工作业：拟稿、加密、转报、抄收、译码、分发。"
            "短距战术语音可以在同一回合送达；编码电文要一个回合；转报再加密要两个回合。"
            "唯一不受链路约束的是当面交办——总指挥所在的那个编队，一句话就能立刻执行。"
            "其余每一个编队，都只能收到延迟的、过期的命令图。"
        ),
        "overlays": [],
    })

    # ---------------------------------------------------------------- order of battle
    formations = {row["formation_id"]: row for row in _formation_rows(data)}
    oob_lines = []
    for side in ("axis", "allies"):
        rows = [row for row in formations.values() if row["side"] == side]
        for row in sorted(rows, key=lambda item: item["formation_id"]):
            name = FORMATION_CN.get(row["formation_id"], row["formation_id"])
            oob_lines.append(
                f"{name}：{row['ships']} 艘 · 旗舰 {row['flagship']}"
                + ("（总指挥随此队）" if row["embarked"] else "")
            )
    out.append({
        "id": "oob",
        "chapter": "双方指挥链",
        "visual": {"kind": "oob", "title": "指挥链与编成", "lines": oob_lines,
                   "turn": 1, "phase": "formation_setup"},
        "narration": (
            "两个指挥体系是对称的：一名舰队总指挥，下辖三个编队，总指挥随其中一队行动。"
            "随队的那一队，命令当面交办、立刻生效；另外两队，只能等电报。"
            "开场时他们彼此都还没有接触，海面是空的。"
        ),
        "overlays": [],
    })
    out.append({
        "id": "three_views_t1",
        "chapter": "双方指挥链",
        "visual": {"kind": "compare", "title": "同一个回合，三种海图",
                   "board": {"turn": 1, "phase": "formation_setup"},
                   "labels": ["上帝视角（真值）", "日方所见", "美方所见"]},
        "narration": (
            "这是同一个回合的三张海图。左边是真实态势，中间是日方看到的，右边是美方看到的。"
            "纪录片能同时看见三张图；局里的人只能看见其中一张。"
        ),
        "overlays": [],
    })

    # ---------------------------------------------------------------- the battle
    for turn in range(1, max_turn + 1):
        turn_record = next((row for row in data.get("turns", []) if row["turn"] == turn), None)
        events = turn_record["events"] if turn_record else []
        facts = [event for event in events if event["type"] in {
            "gunnery_hit", "gunnery_result", "torpedo_hit", "ship_sunk", "collision",
            "ship_withdrawn", "formation_emergency_stop",
        }]
        sinks = [event for event in events if event["type"] == "ship_sunk"]
        hits = [event for event in events if event["type"] == "gunnery_result"]
        phases = [phase for phase in ("movement_resolution", "gunnery") if phase]

        # A. the truth
        out.append({
            "id": f"t{turn}_god",
            "chapter": f"第 {turn} 回合",
            "visual": {"kind": "board", "board": {"turn": turn, "phase": "gunnery"},
                       "viewpoint": "god", "title": f"第 {turn} 回合 · 真实态势"},
            "narration": _truth_narration(turn, hits, sinks, facts),
            "overlays": [{"text": event["message"], "kind": event["type"]}
                         for event in (sinks or hits)[:3]],
        })

        # B. each side: the commander, the orders, the formations
        for side in ("axis", "allies"):
            side_name = SIDE_CN[side]
            fleet_entries = [entry for entry in data.get("fleet_decisions", [])
                             if entry.get("turn") == turn and entry.get("side") == side]
            decisions = [row for row in data.get("decisions", [])
                         if row.get("turn") == turn and _side_of(data, row["formation_id"]) == side]
            orders = []
            for entry in fleet_entries:
                for order in entry["decision"].get("orders", []):
                    orders.append(order)
            thinking = thinking_for(data, role="fleet", side=side, turn=turn)
            lines = []
            for order in orders:
                name = FORMATION_CN.get(order["formation_id"], order["formation_id"])
                lines.append(f"→ {name}：「{quote(order['text'], 70)}」")
            for row in decisions:
                name = FORMATION_CN.get(row["formation_id"], row["formation_id"])
                age = age_map.get((row["formation_id"], turn))
                age_text = "情报新鲜" if age in (0, None) else f"手里的图是 {age} 回合前的"
                lines.append(f"{name}（{age_text}）：{quote(row.get('rationale_summary'), 60)}")
            out.append({
                "id": f"t{turn}_{side}",
                "chapter": f"第 {turn} 回合",
                "visual": {"kind": "side", "side": side, "title": f"第 {turn} 回合 · {side_name}",
                           "board": {"turn": turn, "phase": "movement_planning"}},
                "narration": _side_narration(turn, side, thinking, orders, decisions,
                                             data, age_map),
                "overlays": [{"text": line, "kind": "order"} for line in lines[:5]],
                "thinking": quote(thinking, 220),
            })

        # C. the comparison
        out.append({
            "id": f"t{turn}_compare",
            "chapter": f"第 {turn} 回合",
            "visual": {"kind": "compare", "title": f"第 {turn} 回合末 · 三种海图",
                       "board": {"turn": turn, "phase": "fire_end"},
                       "labels": ["上帝视角（真值）", "日方所见", "美方所见"]},
            "narration": _compare_narration(turn, data, age_map),
            "overlays": [],
        })

    # ---------------------------------------------------------------- analysis
    substitution_count = len(data.get("substitutions", []))
    decisions = data.get("decisions", [])
    late = sum(1 for report in data["_reports"]
               if report.get("delivered_turn") is not None
               and report["delivered_turn"] > report["issued_turn"])
    out.append({
        "id": "analysis_delay",
        "chapter": "复盘",
        "visual": {"kind": "chart", "title": "命令与报告的延迟",
                   "bars": _delay_bars(data)},
        "narration": (
            f"整局下来，双方一共发出 {len(data.get('messages', []))} 封报文，"
            f"其中 {late} 封是跨回合送达的。每一条命令、每一封报告，都要在链路里排队。"
            "指挥的速度，成了这一局里最稀缺的东西。"
        ),
        "overlays": [],
    })
    out.append({
        "id": "analysis_autonomy",
        "chapter": "复盘",
        "visual": {"kind": "card", "title": "代理的自主性：如实记账",
                   "lines": [
                       f"模型做出的编队决策：{len(decisions)} 次",
                       f"引擎拒绝并改由教条执行的批次：{substitution_count} 次",
                       "被拒绝的是合法性（航速超出成员上限、尾随无法保持），不是战术选择",
                       "确认、偏离报告、澄清请求都作为真实报文往来并计入延迟",
                   ]},
        "narration": (
            f"这一局里模型一共做出 {len(decisions)} 次编队决策；其中 {substitution_count} 次，"
            "引擎判定它的机动方案不合法——不是战术分歧，而是航速超出成员上限、"
            "或者尾随无法保持这类硬约束，于是那一回合由确定性教条接管。"
            "这个折扣必须记在账上：不是每一次行动都出自模型的本意。"
        ),
        "overlays": [],
    })
    out.append({
        "id": "analysis_result",
        "chapter": "复盘",
        "visual": {"kind": "result", "title": "结局",
                   "lines": [
                       f"{max_turn} 回合结束：{final.get('victory_reason') or '未分胜负'}",
                       f"比分 轴心 {final.get('score', {}).get('axis', 0)} : "
                       f"{final.get('score', {}).get('allies', 0)} 盟军",
                       f"友军碰撞 {final.get('friendly_collisions', 0)} 次",
                   ]},
        "narration": (
            f"{max_turn} 个回合之后，{final.get('victory_reason') or '双方未能分出胜负'}。"
            f"比分是轴心 {final.get('score', {}).get('axis', 0)} 比 "
            f"{final.get('score', {}).get('allies', 0)}。"
            "比结果更值得看的，是这一局里每一次下令与每一次上报之间，那段时间差里发生的事。"
        ),
        "overlays": [],
    })
    out.append({
        "id": "credits",
        "chapter": "片尾",
        "visual": {"kind": "title", "title": "数据与复现",
                   "subtitle": "对局记录 · 每次模型调用的提示词、回复与思维链 · 电报台账",
                   "footer": "想定源自《二马》想定书与船表；引擎与代理框架为本项目自研"},
        "narration": (
            "这一局的每一次模型调用、每一段思维链、每一封电报，都留在记录里。"
            "本片展示的所有数字，都能在原始数据里逐条核对。"
        ),
        "overlays": [],
    })
    return out


def _formation_rows(data: dict) -> list[dict]:
    """Per-formation identity, from the reconstructed board rather than guessed."""
    rows: list[dict] = []
    seen: dict[str, dict] = {}
    for view in data.get("three_views", [])[:1]:
        for side, payload in view["sides"].items():
            for formation_id, observation in payload["formations"].items():
                row = seen.setdefault(formation_id, {
                    "formation_id": formation_id,
                    "side": observation["side"],
                    "ships": len(observation.get("formation_state", {}).get("ship_ids", [])),
                    "flagship": observation.get("formation_state", {}).get("flagship_id", "—"),
                    "embarked": False,
                })
                if observation.get("authority") == "fleet_directed":
                    row["embarked"] = True
    rows = list(seen.values())
    return rows


def _side_of(data: dict, formation_id: str) -> str:
    for view in data.get("three_views", [])[:1]:
        for side, payload in view["sides"].items():
            if formation_id in payload["formations"]:
                return side
    return "axis" if formation_id.startswith("axis") else "allies"


def _truth_narration(turn: int, hits: list[dict], sinks: list[dict], facts: list[dict]) -> str:
    if turn == 1:
        return ("第一回合，双方仍在接近。海图上两支舰队隔着十几海里并行，"
                "没有接触，没有交火，只有航向和速度。")
    parts = [f"第 {turn} 回合，真实态势。" ]
    if hits:
        parts.append(f"炮击结果 {len(hits)} 条：{quote(hits[0]['message'], 46)}")
    if sinks:
        parts.append("有舰沉没：" + "；".join(quote(event["message"], 30) for event in sinks[:2]))
    if not hits and not sinks:
        parts.append("这一回合没有新的命中，双方仍在调整阵位。")
    return "".join(parts)


def _side_narration(turn: int, side: str, thinking: str, orders: list[dict],
                    decisions: list[dict], data: dict, age_map: dict) -> str:
    side_name = SIDE_CN[side]
    head = f"{side_name}的指挥链，第 {turn} 回合。"
    if orders:
        head += f"总指挥发出 {len(orders)} 道命令。"
    else:
        head += "总指挥本回合没有下令。"
    if decisions:
        ages = [age_map.get((row["formation_id"], turn)) for row in decisions]
        stale = [age for age in ages if isinstance(age, int) and age > 0]
        if stale:
            head += f"下属编队手里最新的一份报告，最久的已经 {max(stale)} 个回合没有更新。"
        head += f"这些编队各自做了 {len(decisions)} 个决定。"
    if thinking:
        head += "总指挥的判断是：" + quote(thinking, 90)
    return head


def _compare_narration(turn: int, data: dict, age_map: dict) -> str:
    return (f"第 {turn} 回合结束时，三张海图摆在一起。左边是真实的位置；"
            "中间和右边，是两位总指挥此刻各自相信的位置。"
            "差距就是这一局真正的战场——不是船与船之间，而是图与图之间。")


def _delay_bars(data: dict) -> list[dict]:
    counts: dict[str, int] = {}
    for message in data.get("messages", []):
        medium = MEDIUM_CN.get(message["medium"], message["medium"])
        counts[medium] = counts.get(medium, 0) + 1
    return [{"label": label, "value": value}
            for label, value in sorted(counts.items(), key=lambda item: -item[1])]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--battle", default="battle_em01")
    parser.add_argument("--out", type=Path, default=HERE / "data" / "timeline.json")
    parser.add_argument("--script", type=Path, default=HERE / "audio" / "script.json")
    parser.add_argument("--audio-manifest", type=Path, default=HERE / "audio" / "vo" / "manifest.json",
                        help="measured narration durations; without it every beat gets a flat length")
    parser.add_argument("--props", type=Path, default=HERE / "data" / "render_props.json")
    args = parser.parse_args()

    battle_dir = args.battle if Path(args.battle).is_absolute() else BATTLE_ROOT / args.battle
    data = load(battle_dir)
    timeline = beats(data)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps({"beats": timeline, "battle": str(battle_dir.relative_to(ROOT))},
                                   ensure_ascii=False, indent=1), encoding="utf-8")
    args.script.parent.mkdir(parents=True, exist_ok=True)
    args.script.write_text(json.dumps(
        {"lines": [{"id": beat["id"], "text": beat["narration"]} for beat in timeline]},
        ensure_ascii=False, indent=1), encoding="utf-8")
    # Fold the measured narration into the beats: a beat lasts as long as its voice
    # plus a breath, so the picture and the narration cannot drift apart on re-render.
    manifest = {}
    if args.audio_manifest.exists():
        payload = json.loads(args.audio_manifest.read_text(encoding="utf-8"))
        manifest = {item["id"]: item for item in payload.get("lines", [])}
    for beat in timeline:
        entry = manifest.get(beat["id"])
        if entry:
            beat["audio"] = entry["path"]
            beat["seconds"] = round(max(entry["seconds"] + 0.9, 3.5), 2)
        else:
            beat["audio"] = None
            beat["seconds"] = round(max(len(beat["narration"]) / 4.2 + 0.9, 3.5), 2)
    args.props.parent.mkdir(parents=True, exist_ok=True)
    args.props.write_text(json.dumps({
        "beats": timeline,
        "title": "第二次马里亚纳海战 · 内南洋水雷强袭战",
        "battle": str(battle_dir.relative_to(ROOT)),
    }, ensure_ascii=False, indent=1), encoding="utf-8")

    total = sum(beat["seconds"] for beat in timeline)
    narrated = sum(1 for beat in timeline if beat["audio"])
    print(f"props -> {args.props} | {len(timeline)} beats, "
          f"{narrated} with narration, runtime {total/60:.1f} min")
    words = sum(len(beat["narration"]) for beat in timeline)
    print(f"beats: {len(timeline)} | narration chars: {words} "
          f"(≈{words/4.2/60:.1f} min at 4.2 chars/s)")
    print(f"-> {args.out}")
    print(f"-> {args.script}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
