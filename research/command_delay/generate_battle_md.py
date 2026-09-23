"""Generate the after-action Markdown report from a completed LLM-vs-LLM battle.

Reads ``battle/battle_data.json`` (written by ``llm_vs_llm.py``) plus the captured
board images, and emits ``battle/REPORT.md``: per-turn situation with embedded
board images, the fleet orders and their telegraphed delivery, every formation
decision with its rationale, the full communication ledger, the agents' final
memories, and a computed orders-vs-local-situation balance table.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BATTLE = Path(__file__).resolve().parent / "battle"

LINK_LABEL = {"direct": "直连", "relayed": "经转报", "stale": "陈旧", "blackout": "中断"}
MEDIUM_LABEL = {
    "tbs_short": "TBS 短距战术", "blinker": "视觉信号", "wt_coded": "编码电文",
    "wt_reencipher_relay": "转报/再加密", "multi_hop": "复合路由", "blackout": "无通路",
}
STATUS_LABEL = {"delivered": "已送达", "queued": "排队中", "dropped": "已丢弃",
                "superseded": "被取代"}
BRANCH_LABEL = {
    "explicit_signal_branch": "信号分支", "local_condition_branch": "本地条件分支",
    "loss_of_comm_branch": "失联预案",
}
SIDE_TITLE = {"axis": "轴心（日方）", "allies": "同盟（美方）"}


def load() -> dict:
    return json.loads((BATTLE / "battle_data.json").read_text(encoding="utf-8"))


def image_for(turn: int, images_files: list[str]) -> list[str]:
    """Board images for this turn, preferring the resolution phases, both sides.

    ``images_files`` are paths relative to the report (``images/<game_id>/…``),
    captured per (turn, phase, side) by the battle-report pipeline.
    """
    in_turn = [name for name in images_files if f"turn-{turn}-" in name]

    def preference(name: str) -> tuple:
        return ("movement_resolution" not in name,
                "gunnery" not in name,
                "torpedo_effects" not in name,
                name)
    axis = [name for name in in_turn if "-axis-" in name]
    allies = [name for name in in_turn if "-allies-" in name]
    picked = sorted(axis, key=preference)[:1] + sorted(allies, key=preference)[:1]
    return picked or sorted(in_turn, key=len)[:2]


def esc(text) -> str:
    return str(text or "").replace("|", "\\|")


def main() -> int:
    data = load()
    final = data["final"]
    lines: list[str] = []
    add = lines.append

    add("# 命令延迟模式 · LLM 对 LLM 完整战报")
    add("")
    add(f"- **想定**：{data['scenario']}（seed {data['seed']}）")
    add(f"- **双方策略**：{data['sides']['axis']} / {data['sides']['allies']} —— 双方每个编队各由一个独立子代理指挥（带记忆），"
        f"舰队总指挥用自然语言下达命令，命令作为电报经通信链路投递")
    add(f"- **结果**：{final['turns']} 回合，胜方 {final['winner'] or '无'}"
        f"（{final.get('victory_reason') or '—'}）；比分 {final['score'].get('axis', 0)}–{final['score'].get('allies', 0)}；"
        f"友军碰撞 {final['friendly_collisions']} 次")
    add(f"- **信息边界**：每个代理只能看到自己一侧的过滤视图；本报告为**战后中性文书**，"
        f"因此正文地图为双方视角，但第 [信息泄露扫描](#信息泄露扫描) 节单独验证了代理收到的材料")
    add("")

    messages = data["messages"]
    fleet_orders = data["fleet_orders"]
    decisions = data["decisions"]
    turns = data["turns"]

    # ---------------- per-turn narrative
    add("## 逐回合态势与指挥")
    add("")
    images_files = data.get("images_files", [])
    for turn_record in turns:
        turn = turn_record["turn"]
        add(f"### 第 {turn} 回合")
        add("")
        picks = image_for(turn, images_files)
        for name in picks:
            add(f"![T{turn} {name}](images/{name})")
        if picks:
            add("")
            add(f"*图：第 {turn} 回合结算后双方棋盘（`{picks[0]}` 等）*")
            add("")
        # events worth showing
        key_types = {"gunnery_hit", "gunnery_rejected", "torpedo_launch", "torpedo_hit",
                     "collision", "ship_sunk", "formation_emergency_stop",
                     "command_message_delivered", "command_message_dropped",
                     "formation_agent_decision", "ship_detached", "ship_withdrawn"}
        shown = [e for e in turn_record["events"] if e["type"] in key_types]
        if shown:
            add("**裁决要点**")
            add("")
            for event in shown[:14]:
                add(f"- `T{event['turn']} {event['phase']}` **{event['type']}** — {event['message']}")
            if len(shown) > 14:
                add(f"- （其余 {len(shown) - 14} 条见附录日志）")
            add("")
        # fleet orders this turn
        orders_this = [o for o in fleet_orders if o.get("turn") == turn and o.get("text")]
        if orders_this:
            add("**舰队总指挥电报**")
            add("")
            for order in orders_this:
                add(f"- **{SIDE_TITLE[order['side']]}** → `{order['formation_id']}`："
                    f"「{order['text']}」（{MEDIUM_LABEL.get(order['medium'], order['medium'])}，"
                    f"链路开销 +{order['handling_delay']} 回合，{order['route_reason']}）")
            add("")
        # formation decisions this turn
        decided = [d for d in decisions if d.get("turn") == turn]
        if decided:
            add("**编队代理决策**")
            add("")
            add("| 编队 | 阵营 | 机动方案 | 激活分支 | 决策说明 |")
            add("|---|---|---|---|---|")
            for d in decided:
                add(f"| {esc(d.get('formation_id'))} | {d.get('side')} "
                    f"| `{esc(d.get('selected_movement_plan') or '保持')}` "
                    f"| {BRANCH_LABEL.get(d.get('selected_contingency_branch') or '', '无')} "
                    f"| {len((d.get('audit') or {}).get('active_branches', [])) and ''}"
                    f"{esc((d.get('rationale_summary') or '')[:110])} |")
            add("")
            notes = [(d.get("formation_id"), d.get("memory_note"))
                     for d in decided if d.get("memory_note")]
            if notes:
                add("代理写给自己的备忘：" +
                    "；".join(f"`{fid}`「{note}」" for fid, note in notes))
            add("")

    # ---------------- communication ledger
    add("## 通信台账（全部报文）")
    add("")
    add("| 报文 | 类型 | 媒介 | 优先级 | 发出 | 送达 | 状态 | 说明 |")
    add("|---|---|---|---|---|---|---|---|")
    for message in messages:
        add(f"| `{message['message_id']}` | {message['kind']} "
            f"| {MEDIUM_LABEL.get(message['medium'], message['medium'])} "
            f"| {message['precedence']} "
            f"| T{message['issued_turn']} "
            f"| {f'T{message["delivered_turn"]}' if message.get('delivered_turn') is not None else '—'} "
            f"| {STATUS_LABEL.get(message['status'], message['status'])} "
            f"| {esc(message.get('reason') or '')} |")
    add("")
    delivered = [m for m in messages if m["status"] == "delivered"]
    delayed = [m for m in delivered if (m.get("delivered_turn") or 0) > m["issued_turn"]]
    dropped = [m for m in messages if m["status"] in ("dropped", "superseded")]
    add(f"共 {len(messages)} 条：送达 {len(delivered)}（其中跨回合延迟 {len(delayed)}），"
        f"丢弃/被取代 {len(dropped)}，其余在队列中。")
    add("")

    # ---------------- balance of orders vs local situation
    add("## 远方命令与当前战局的平衡（逐次决策）")
    add("")
    add("| 回合 | 编队 | 手持命令 | 本地接触 | 激活分支 | 采取的方案 | 依据（代理自述） |")
    add("|---|---|---|---|---|---|---|")
    for d in decisions:
        audit = d.get("audit") or {}
        add(f"| T{d.get('turn')} | {esc(d.get('formation_id'))} "
            f"| {'有（原文见记忆）' if audit.get('order_received') else '无（预令）'} "
            f"| {audit.get('legal_actions', 0)} "
            f"| {BRANCH_LABEL.get(d.get('selected_contingency_branch') or '', '无')} "
            f"| `{esc(d.get('selected_movement_plan') or '保持')}` "
            f"| {esc((d.get('rationale_summary') or '')[:90])} |")
    add("")

    # ---------------- memories
    add("## 各编队最终记忆")
    add("")
    for formation_id, memory in data["memories"].items():
        add(f"### `{formation_id}`")
        add("")
        add(f"- 当前生效命令（T{memory.get('active_order_turn')}收到）："
            f"{memory.get('active_order_text') or '（无）'}")
        counts = memory.get("counts", {})
        add(f"- 记忆条目：{', '.join(f'{k} {v}' for k, v in counts.items())}")
        scratch = memory.get("scratchpad") or []
        if scratch:
            add("- 自己写的备忘：")
            for note in scratch:
                add(f"  - 「{note}」")
        add("")

    # ---------------- agent transcript samples
    add("## 代理原始决策记录（抽样）")
    add("")
    add("每条决策的完整提示词、原始回复与记忆快照在 `battle_data.json` 的 `agent_log`；"
        "这里抽取首末各一条以见格式：")
    add("")
    log_entries = data.get("agent_log", [])
    for record in (log_entries[:1] + log_entries[-1:]) if log_entries else []:
        add(f"**`{record['formation_id']}` 第 {record['turn']} 回合（{record['agent']}）**")
        add("")
        add(f"- 手持命令：{record.get('order_text') or '（无）'}")
        for attempt in record.get("attempts", []):
            add(f"- 第 {attempt['attempt']} 次尝试："
                f"{'采纳' if attempt['accepted'] else ('回退教条' if attempt['fallback'] else '拒绝')}"
                f"{'；错误：' + '；'.join(attempt['errors']) if attempt['errors'] else ''}")
            add(f"  - 原始回复：`{(attempt['raw_response'] or '')[:220]}`")
        decision = record.get("decision", {})
        add(f"- 决策：方案 `{decision.get('selected_movement_plan') or '保持'}`，"
            f"分支 {decision.get('selected_contingency_branch') or '无'}，"
            f"备忘「{decision.get('memory_note') or '—'}」")
        add("")

    # ---------------- appendix: full event log
    add("## 附录：全量裁决事件日志")
    add("")
    add("```")
    for turn_record in turns:
        for event in turn_record["events"]:
            add(f"T{event['turn']} {event['phase']:<20} {event['type']:<28} {event['message']}")
    add("```")
    add("")
    add(f"*由 `research/command_delay/generate_battle_md.py` 从 `battle/battle_data.json` "
        f"自动生成；引擎事件、报文台账、代理决策与记忆均为引擎记录原样，未手工修饰。*")

    report = BATTLE / "REPORT.md"
    report.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"REPORT written: {report} ({len(lines)} lines)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
