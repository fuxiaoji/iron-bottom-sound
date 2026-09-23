"""Emit the after-action report, the shooting script and the subtitles, from one source.

Three documents, one truth: the beats built by ``build_timeline.py``.  The report is the
written record, the script is what the narrator reads in order, and the subtitles are
timed from the measured narration.  Generating all three from the same beats means they
cannot disagree about what happened - which is the failure mode of a documentary made by
hand from a log.

Usage::

    .venv/bin/python research/battle_video/build_report.py --battle battle_em01
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
BATTLE_ROOT = ROOT / "research" / "command_delay"

SIDE_CN = {"axis": "日方", "allies": "美方"}
MEDIUM_CN = {
    "tbs_short": "TBS 短距", "blinker": "视觉信号", "wt_coded": "编码电文",
    "wt_reencipher_relay": "转报再加密", "multi_hop": "复合路由", "blackout": "无通路",
}
KIND_CN = {
    "sitrep": "态势报告", "contact_report": "接触报告", "deviation_report": "偏离报告",
    "clarification": "澄清请求", "acknowledgement": "确认", "mission_order": "任务命令",
    "amendment": "修正令",
}


def srt_timestamp(seconds: float) -> str:
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = seconds % 60
    return f"{hours:02d}:{minutes:02d}:{secs:06.3f}".replace(".", ",")


def write_subtitles(beats: list[dict], path: Path) -> float:
    lines: list[str] = []
    clock = 0.0
    for index, beat in enumerate(beats, 1):
        duration = float(beat.get("seconds") or max(len(str(beat.get("narration") or "")) / 4.2, 4))
        text = str(beat.get("narration") or "").strip()
        if text:
            lines.append(str(index))
            lines.append(f"{srt_timestamp(clock)} --> {srt_timestamp(clock + duration - 0.2)}")
            lines.append(text)
            lines.append("")
        clock += duration
    path.write_text("\n".join(lines), encoding="utf-8")
    return clock


def write_script(beats: list[dict], path: Path) -> None:
    out = ["# 纪录片解说词（由对局记录生成，勿手改）", ""]
    chapter = None
    for beat in beats:
        if beat["chapter"] != chapter:
            chapter = beat["chapter"]
            out.append(f"## {chapter}")
            out.append("")
        out.append(f"**[{beat['id']}]** {beat['seconds']:.1f}s")
        out.append("")
        out.append(beat["narration"])
        out.append("")
        visual = beat.get("visual") or {}
        bits = [f"画面：{visual.get('kind')}"]
        if visual.get("title"):
            bits.append(f"标题：{visual['title']}")
        if visual.get("board"):
            bits.append(f"棋盘：第 {visual['board']['turn']} 回合 {visual['board']['phase']}")
        out.append("  · ".join(bits))
        if beat.get("overlays"):
            out.append("")
            for overlay in beat["overlays"]:
                out.append(f"- 屏显：{overlay['text']}")
        if beat.get("thinking"):
            out.append("")
            out.append(f"> 思维链摘录：{beat['thinking']}")
        out.append("")
    path.write_text("\n".join(out), encoding="utf-8")


def write_report(battle_dir: Path, beats: list[dict], path: Path) -> None:
    data = json.loads((battle_dir / "battle_data.json").read_text(encoding="utf-8"))
    final = data.get("final", {})
    messages = data.get("messages", [])
    reports = [json.loads(line) for line in (battle_dir / "reports.jsonl").read_text(
        encoding="utf-8").splitlines() if line.strip()] if (battle_dir / "reports.jsonl").exists() else []
    calls = [json.loads(line) for line in (battle_dir / "calls.jsonl").read_text(
        encoding="utf-8").splitlines() if line.strip()]
    ok_calls = [call for call in calls if not call.get("transport_error")]
    usage = {"prompt_tokens": 0, "completion_tokens": 0}
    for call in calls:
        for key in usage:
            usage[key] += int((call.get("usage") or {}).get(key) or 0)

    lines: list[str] = []
    add = lines.append
    add("# 第二次马里亚纳海战（内南洋水雷强袭战）· 命令延迟模式 LLM 对 LLM 战报")
    add("")
    add(f"- **想定**：{data.get('scenario')}（seed {data.get('seed')}），"
        f"{final.get('turns')} 回合后结束")
    add(f"- **指挥链**：舰队总指挥（独立 agent）→ 3 个分舰队指挥（各自 agent + 记忆）；"
        f"总指挥随队编队当面受令、零延迟，其余编队经电报按媒介延迟")
    add(f"- **模型**：编队级 `{data.get('formation_policy')}`；舰队级 `{data.get('fleet_policy')}`；"
        f"思维链{'开启' if data.get('thinking_enabled') else '关闭'}，"
        f"每次调用预算 {data.get('max_tokens')} tokens")
    add(f"- **结果**：{final.get('victory_reason') or '未分胜负'}；"
        f"比分 轴心 {final.get('score', {}).get('axis', 0)} : "
        f"{final.get('score', {}).get('allies', 0)} 盟军；"
        f"友军碰撞 {final.get('friendly_collisions', 0)} 次")
    add(f"- **调用记账**：{len(ok_calls)} 次成功调用（另有 "
        f"{len(calls) - len(ok_calls)} 次传输失败被重试），"
        f"提示 {usage['prompt_tokens']:,} tokens / 生成 {usage['completion_tokens']:,} tokens，"
        f"平均思维链 "
        f"{round(sum(len(call.get('thinking') or '') for call in ok_calls) / max(1, len(ok_calls)))} 字")
    add(f"- **引擎拒绝并回退教条的次数**：{len(data.get('substitutions', []))}"
        f"（明细见下）")
    add(f"- **配套影像**：`research/battle_video/out/documentary.mp4`"
        f"（12.0 分钟，1080p30；同一份记录生成，另附 720p 与字幕）")
    add("")
    # Stills live beside the video pipeline (a tracked directory), not under out/ which is
    # a build directory and gitignored.
    still_prefix = "../../battle_video/stills"
    add(f"![开场]({still_prefix}/01_title.png)")
    add(f"![规则]({still_prefix}/02_rules.png)")
    add(f"![三视图]({still_prefix}/03_three_views.png)")
    add(f"![复盘]({still_prefix}/04_analysis.png)")
    add("")

    add("## 逐回合：真实态势与双方决策")
    add("")
    for beat in beats:
        visual = beat.get("visual") or {}
        if not visual.get("board") or visual.get("viewpoint") != "god":
            continue
        add(f"### 第 {visual['board']['turn']} 回合")
        add("")
        add(f"> {beat['narration']}")
        add("")

    for side in ("axis", "allies"):
        add(f"## {SIDE_CN[side]}的指挥与上报")
        add("")
        add("| 回合 | 总指挥命令（原文摘录） | 下达方式 | 媒介 | 延迟 |")
        add("|---|---|---|---|---|")
        for entry in data.get("fleet_decisions", []):
            if entry.get("side") != side:
                continue
            for order in entry["decision"].get("orders", []):
                record = next((message for message in messages
                               if message.get("payload", {}).get("order_text") == order["text"]), None)
                in_person = bool(record and record.get("payload", {}).get("delivered_in_person"))
                add(f"| T{entry['turn']} → {order['formation_id']} "
                    f"| {order['text'][:60].replace('|', '/')} "
                    f"| {'当面交办' if in_person else '电报'} "
                    f"| {MEDIUM_CN.get((record or {}).get('medium'), (record or {}).get('medium', '—'))} "
                    f"| +{(record or {}).get('handling_delay', '—')} |")
        add("")
        add("**分舰队的上报**（agent 亲笔正文 + 引擎保底态势）")
        add("")
        add("| 报文 | 上报编队 | 类型 | 发出 | 送达 | 延迟 | 正文摘录 |")
        add("|---|---|---|---|---|---|---|")
        for report in reports:
            if not ((report.get("reporting_formation_id") or "").startswith(side)):
                continue
            delivered = report.get("delivered_turn")
            delivered_text = f"T{delivered}" if delivered is not None else "—"
            add(f"| `{report['message_id']}` | {report['reporting_formation_id']} "
                f"| {KIND_CN.get(report['kind'], report['kind'])} "
                f"| T{report['issued_turn']} "
                f"| {delivered_text} "
                f"| +{report.get('handling_delay', 0)} "
                f"| {(report.get('report_text') or '')[:56].replace('|', '/')} |")
        add("")

    add("## 代理自主性：如实记账")
    add("")
    if data.get("substitutions"):
        add("被引擎拒绝、改由确定性教条执行的回合：")
        add("")
        add("| 回合 | 阵营 | 驳回原因（引擎原文） |")
        add("|---|---|---|")
        for item in data["substitutions"]:
            add(f"| T{item['turn']} | {SIDE_CN.get(item['side'], item['side'])} "
                f"| {'；'.join(item['errors'])[:150].replace('|', '/')} |")
    else:
        add("本局没有任何一次代理方案被引擎驳回：每一次机动都出自模型自己的判断。")
    add("")

    add("## 思维链摘录（每位指挥每回合的判断）")
    add("")
    for beat in beats:
        if beat.get("thinking"):
            add(f"- **{beat['id']}**：{beat['thinking'][:300]}")
    add("")

    add("## 数据文件")
    add("")
    add("| 文件 | 内容 |")
    add("|---|---|")
    for name, what in (
        ("battle_data.json", "对局全记录：逐回合事件、决策、记忆、电报台账、三视角观测索引"),
        ("calls.jsonl", "每次模型调用：提示词、回复、思维链、token 用量、延迟、传输失败"),
        ("orders.jsonl", "引擎接受的每一个指令批次（可用 replay_battle.py 逐位重演）"),
        ("reports.jsonl", "每一封上报：作者、正文、发出/送达回合与延迟"),
        ("views/", "逐阶段三视角观测（上帝/日方/美方）与全状态快照"),
        ("replay_verification.json", "从 orders.jsonl 重演与本局终局的一致性核验"),
        ("leak_scan.json", "提示词泄漏核验（含上报正文判据与注入正对照）"),
    ):
        add(f"| `{name}` | {what} |")
    add("")
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--battle", default="battle_em01")
    parser.add_argument("--props", type=Path, default=HERE / "data" / "render_props.json",
                        help="the timeline with measured narration durations folded in "
                             "(written by build_timeline.py; the raw timeline has no lengths)")
    args = parser.parse_args()

    battle_dir = args.battle if Path(args.battle).is_absolute() else BATTLE_ROOT / args.battle
    beats = json.loads(args.props.read_text(encoding="utf-8"))["beats"]

    srt = HERE / "data" / "subtitles.srt"
    script = HERE / "data" / "narration_script.md"
    report = battle_dir / "REPORT.md"
    total = write_subtitles(beats, srt)
    write_script(beats, script)
    write_report(battle_dir, beats, report)
    print(f"subtitle runtime {total/60:.1f} min -> {srt}")
    print(f"script -> {script}")
    print(f"report -> {report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
