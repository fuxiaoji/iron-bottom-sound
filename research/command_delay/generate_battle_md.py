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
from collections import Counter
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


def _read_json(path: Path) -> dict | None:
    """Read an audit artefact if it is there; the report still renders without it."""
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None


def image_for(turn: int, images_files: list[str]) -> list[str]:
    """Board images for this turn, both sides, at movement and fire resolution.

    ``images_files`` are paths relative to the report (``images/<game_id>/…``),
    captured per (turn, phase, side) by the battle-report pipeline, so each entry is
    the link target verbatim.  Four are picked per turn — movement and gunnery for
    each side — so a reader can follow every turn's geometry, not just one snapshot.
    """
    in_turn = [name for name in images_files if f"turn-{turn}-" in name]

    def pick(side: str) -> list[str]:
        side_files = [name for name in in_turn if f"-{side}-" in name]
        chosen: list[str] = []
        for phase in ("movement_resolution", "gunnery", "fire_end", "torpedo_effects"):
            match = sorted(name for name in side_files if f"-{phase}-" in name)
            if match:
                chosen.append(match[0])
            if len(chosen) == 2:
                break
        return chosen

    picked = pick("axis") + pick("allies")
    if picked:
        return picked
    return sorted(in_turn)[:2]


def esc(text) -> str:
    return str(text or "").replace("|", "\\|")


def main() -> int:
    data = load()
    final = data["final"]
    lines: list[str] = []
    add = lines.append

    messages = data["messages"]
    fleet_orders = data["fleet_orders"]
    decisions = data["decisions"]
    turns = data["turns"]

    add("# 命令延迟模式 · LLM 对 LLM 完整战报")
    add("")
    add(f"- **想定**：{data['scenario']}（seed {data['seed']}）")
    add(f"- **双方策略**：{data['sides']['axis']} / {data['sides']['allies']} —— 双方每个编队各由一个独立子代理指挥（带记忆），"
        f"舰队总指挥用自然语言下达命令，命令作为电报经通信链路投递")
    add(f"- **结果**：{final['turns']} 回合，胜方 {final['winner'] or '无'}"
        f"（{final.get('victory_reason') or '—'}）；比分 {final['score'].get('axis', 0)}–{final['score'].get('allies', 0)}；"
        f"友军碰撞 {final['friendly_collisions']} 次")
    add(f"- **代理执行面**：{len(fleet_orders)} 次舰队总指挥电报、{len(decisions)} 次编队代理决策；"
        f"其中 {len(data.get('substitutions', []))} 次代理方案被引擎合法性检查驳回并回退确定性指挥官"
        f"（详见 [代理自主性与回退披露](#代理自主性与回退披露)）")
    add(f"- **信息边界**：每个代理只能看到自己一侧的过滤视图；本报告为**战后中性文书**，"
        f"因此正文地图为双方视角，但第 [信息泄露与证据核验](#信息泄露与证据核验) 节单独验证了"
        f"代理实际收到的材料，并在同节披露该项检查自身的方法与局限")
    add("")

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
            label = Path(name).stem.split(f"turn-{turn}-")[-1]
            # A cropped copy (crop_battle_images.py) zooms into the action and keeps
            # the hex rulers; prefer it when present, else link the raw capture.
            cropped = str(Path(name).with_name(f"crop-{Path(name).name}"))
            target = cropped if (BATTLE / cropped).exists() else name
            add(f"![T{turn} {label}]({target})")
        if picks:
            add("")
            add(f"*图：第 {turn} 回合各结算阶段的棋盘（裁剪至行动区域、保留六角标尺），"
                f"双方视角各取机动结算与炮击结算"
                f"（`{', '.join(Path(p).name for p in picks)}`）*")
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
    # The order actually in hand is read from the agent-log entry for the same
    # (turn, formation): that is the text the prompt carried, so it is evidence,
    # not an inference from the decision's own audit block.
    order_in_hand = {
        (record["turn"], record["formation_id"]): (record.get("order_text") or "")
        for record in data.get("agent_log", [])
    }
    add("## 远方命令与当前战局的平衡（逐次决策）")
    add("")
    add("| 回合 | 编队 | 手持命令 | 合法机动选项 | 激活分支 | 采取的方案 | 依据（代理自述） |")
    add("|---|---|---|---|---|---|---|")
    for d in decisions:
        audit = d.get("audit") or {}
        in_hand = order_in_hand.get((d.get("turn"), d.get("formation_id")), "")
        add(f"| T{d.get('turn')} | {esc(d.get('formation_id'))} "
            f"| {'有（原文见记忆节）' if in_hand else '无（自派任务）'} "
            f"| {audit.get('legal_actions', 0)} "
            f"| {BRANCH_LABEL.get(d.get('selected_contingency_branch') or '', '无')} "
            f"| `{esc(d.get('selected_movement_plan') or '保持')}` "
            f"| {esc((d.get('rationale_summary') or '')[:90])} |")
    add("")
    add(f"「合法机动选项」列是该回合引擎交给代理的机动选项数（`legal_formation_actions`），"
        f"即它在本地几何约束下真实拥有的选择空间；「依据」列是代理自己写下的理由原句，"
        f"可据此判断它是按远方命令行动，还是按眼前战局行动。")
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

    # ---------------- multi-agent collaboration
    add("## 多代理指挥协作")
    add("")
    kinds = Counter(m["kind"] for m in messages)
    relayed = [m for m in messages if m.get("relay_hops")]
    urgent = [m for m in messages if m.get("precedence") == "urgent"]
    queued_at_end = sum(1 for m in messages if m["status"] == "queued")
    reports_sent = Counter(
        action
        for d in decisions for action in (d.get("report_actions") or [])
    )
    add(f"- **指挥方向是双向的，但两个方向由不同机制驱动。** 上级方向：{len(fleet_orders)} 条"
        f"自然语言任务命令由舰队总指挥（子代理）拟制并按电报投递，另有 2 条由引擎在 T2 拟制的"
        f"初始委派（结构式任务/意图/协同，不含打法）；下级方向："
        f"{kinds.get('contact_report', 0)} 条接触报告 + {kinds.get('sitrep', 0)} 条态势报告，"
        f"由引擎在每个阶段边界**自动**起草（有接触则升为 urgent 优先级的接触报告）。")
    mission_orders = [m for m in messages if m["kind"] == "mission_order"]
    if mission_orders:
        add("")
        add("**任务命令的延迟（电报投递实证）**")
        add("")
        add("| 报文 | 阵营 | 发信人 | 收件编队 | 媒介 | 拟制回合 | 送达回合 | 链路开销 | 命令原文 |")
        add("|---|---|---|---|---|---|---|---|---|")
        for message in mission_orders:
            payload = message.get("payload") or {}
            text = str(payload.get("order_text") or payload.get("mission") or "")
            origin_note = "舰队总指挥（子代理）" if payload.get("order_text") else "引擎初始委派"
            delivered = message.get("delivered_turn")
            add(f"| `{message['message_id']}` | {SIDE_TITLE.get(message['side'], message['side'])} "
                f"| {origin_note} | `{message['destination']}` "
                f"| {MEDIUM_LABEL.get(message['medium'], message['medium'])} "
                f"| T{message['issued_turn']} "
                f"| {'T' + str(delivered) if delivered is not None else '—'} "
                f"| +{message.get('handling_delay', 0)} 回合 "
                f"| {esc(text)[:70] or '（结构式）'} |")
        add("")
        add("两条由子代理拟制的命令都是在 T3 写下、**T4 才被编队读到**：编队指挥官在写命令的"
            "同一个回合里无法依据它行动，这正是命令延迟模式要建模的东西。"
            "同表可见，编队自己的接触报告走 TBS 时开销为 0（同回合送达）、"
            "被排到再加密转报队列时为 +2 回合。")
        add("")
    add(f"- **代理自己的报告动作已记录、但尚未接线。** 代理逐次选择了报告动作："
        + "、".join(f"{k} {v} 次" for k, v in reports_sent.most_common())
        + f"；其中 {sum(1 for d in decisions if d.get('acknowledgement'))} 次决策标记了确认。"
        f"这些选择进入决策记录与本地记忆（`report_sent` 条目），**但不生成、也不改变任何报文**——"
        f"见文末 [未接线与缺陷披露](#未接线与缺陷披露)。")
    same_turn = sum(1 for m in messages if m["status"] == "delivered"
                    and m.get("delivered_turn") == m["issued_turn"])
    add(f"- **信道与延迟**：全部 {len(messages)} 条报文中 {len(urgent)} 条按 urgent 优先级排队，"
        f"{len(relayed)} 条经转报（relay）路由，{same_turn} 条同回合送达、"
        f"{len(messages) - same_turn - queued_at_end} 条跨回合送达，"
        f"{queued_at_end} 条在停战时仍在队列里；"
        f"媒介由双方旗舰距离相对想定自身光学地平线选择（直连/视觉/编码电文/转报），"
        f"距离只决定走哪条信道，不缩放延迟本身。")
    add("")

    # ---------------- autonomy and fallback disclosure
    add("## 代理自主性与回退披露")
    add("")
    substitutions = data.get("substitutions", [])
    movement_turns = sorted({d["turn"] for d in decisions})
    side_turns = len(movement_turns) * 2
    attempts = [a for record in data.get("agent_log", []) for a in record.get("attempts", [])]
    first_try = sum(1 for a in attempts if a["attempt"] == 1 and a["accepted"])
    retried = sum(1 for a in attempts if a["attempt"] > 1 and a["accepted"])
    add(f"- **代理方案实际执行率**：{side_turns} 个「回合×阵营」机动批次中，"
        f"{len(substitutions)} 个被引擎合法性检查整批驳回，退回确定性指挥官执行教条方案；"
        f"其余 {side_turns - len(substitutions)} 个执行的是代理自己的方案。")
    add(f"- **回复格式反馈回路**：{first_try} 次首次回复即被采纳，{retried} 次首次被拒后"
        f"带着具体错误原因重发并获采纳（例如 `unknown contingency branch "
        f"'superior enemy force in local contact'`——代理引用了不存在的预案分支名）。"
        f"引擎拒绝的是**格式与合法性**，不是战术选择。")
    if substitutions:
        add("")
        add("| 回合 | 阵营 | 驳回原因（引擎原文，截断） |")
        add("|---|---|---|")
        for item in substitutions:
            reason = "；".join(item["errors"])[:220]
            add(f"| T{item['turn']} | {SIDE_TITLE.get(item['side'], item['side'])} | {esc(reason)} |")
    add("")
    add("回退**不改变双方的信息边界**：确定性指挥官与代理读的是同一侧过滤视图，"
        "回退只是把该阵营这一回合的机动决策权收回引擎。因此本报告中「代理自主性」的结论"
        "必须按上述执行率打折——被驳回的回合里，编队的动作出自教条，代理的机动意图未被执行。")
    add("")

    # ---------------- leakage scan and evidence
    add("## 信息泄露与证据核验")
    add("")
    scan = _read_json(BATTLE / "leakage_scan.json")
    control = _read_json(BATTLE / "self_test.json")
    if scan:
        content = scan["content_provenance"]
        add("**判据。** 本扫描不检查「代理是否知道敌方舰名」——在该想定里这个判据是空转的："
            "双方自第 1 回合起就在光学距离内（轴心可见全部 9 艘美舰、同盟可见全部 5 艘日舰，"
            f"`vacuous_in_this_scenario: {scan['identity']['vacuous_in_this_scenario']}`），"
            "任何时刻敌方舰名都合法可见。真正能泄露的是**文本的出处**，所以判据定为："
            "提示词里的每一个特征串，都必须对它的读者有合法出处——读者自己编队更早回合写下的内容，"
            "或已经投递给它的一封舰队命令。敌方的文字、友邻编队的决策文字、以及**任何晚于当时的回合**"
            "的文字，都不合法（最后一条同时覆盖「敌方计划泄露」与「读到明天的报纸」两种情形）。")
        add("")
        add(f"**结果。** 核验 {scan['request_files_scanned']} 条传输记录（`requests/` 下每一份"
            f"实际交给子代理的请求），检查 {content['tokens_examined']} 个特征串，其中 "
            f"{content['tokens_with_provenance']} 个确有出处可溯；"
            f"内容出处违规 {len(content['findings'])} 条，"
            f"报文台账违规 {len(scan['message_ledger']['findings'])} 条，"
            f"字段归属违规 {len(scan['field_ownership']['findings'])} 条。"
            f"判定 **{scan['verdict']}**。")
        add("")
        add("报文台账一项是精确检查、不需重放：每条 `received_messages[*].message_id` 都必须在"
            "引擎台账里存在、属于同一阵营、且收件人是该编队。上一轮发现的两个跨阵营缺陷"
            "（编队命令批次与火力优先级混入对方）正是这类检查会拦下的。")
    if control:
        add("")
        add("**正对照（PASS 之所以算证据）。** 一个不可能失败的检查不是证据，所以对同一份数据做了"
            "注入试验：把**本局真实存在**的敌方字符串塞进一份真实的轴心方请求，扫描器必须报错。")
        add("")
        add("| 注入内容 | 注入串（截断） | 是否被抓 |")
        add("|---|---|---|")
        labels = {"enemy_fleet_order": "敌方舰队命令原文",
                  "enemy_decision_prose": "敌方编队决策理由原文",
                  "enemy_message_ledger_entry": "敌方报文台账条目"}
        for key, label in labels.items():
            item = control.get(key) or {}
            add(f"| {label} | `{esc(str(item.get('injected'))[:60])}` "
                f"| {'是' if item.get('caught') else '否'} |")
        add("")
        add(f"基线（未注入）发现数 {control.get('baseline_findings')}，三项注入全部被抓，"
            f"自检判定 **{control.get('verdict')}**。")
    add("")
    add("**本扫描未覆盖的范围（如实列出）。**")
    add("")
    add("- 审计对象是**传输面**：实际交给代理的记录。代理从合法材料里「推断」出什么，"
        "不在本检查范围内，本检查也不能证明它没推断。")
    add("- 可见性包络（`identity` 子项）靠**确定性指挥官重放**重建，而非本局的代理决策——"
        "驱动没有持久化被采纳的指令批次，所以该子项只是近似；内容出处与台账两项不依赖重放。")
    add("- 本局**不可从产物逐位重放**：没有保存被采纳的指令批次，因此这份战报是"
        "「记录审计」，不是「可复现实验」。")
    add("- 本报告本身是战后中性文书，含双方视角；它**不得**作为任何代理的输入。"
        "本局最后一次代理调用发生在报告生成之前。")
    add("")

    # ---------------- unwired and defects
    add("## 未接线与缺陷披露")
    add("")
    add("本局暴露的两处「记录得到、但没接线」的缺口，均由代码位置确认，未在本轮修改"
        "（它们属于冻结模式的语义，改动会使黄金重放基线漂移，需要 PI 决定）：")
    add("")
    add("1. **代理的确认不进报文台账。** `backend/src/iron_bottom_sound/command_delay.py` "
        "在 `_apply_delivery` 里对 `MessageKind.ACKNOWLEDGEMENT` 直接 `return`，"
        "而 `CommandMessage.acknowledged_turn`（`models.py`）全仓库没有任何写入点，"
        "本局台账因此 0 条确认记录，尽管代理在 "
        f"{sum(1 for d in decisions if d.get('acknowledgement'))} 次决策里明确确认，"
        "且有 2 次选择发出 `ACKNOWLEDGEMENT`。另需注意 `MissionOrder.confirmed_turn` "
        "在送达时即被写成送达回合——它记的是「送达」，不是「确认」，两件事在台账里被合并了。")
    add("2. **代理的报告动作不影响通信。** 代理逐次选择 `report_actions`"
        "（SITREP / CONTACT_REPORT / ACKNOWLEDGEMENT 等），这些选择只落到本地记忆条目"
        "（`report_sent`）与决策记录里；台账中的 68 条接触报告与态势报告全部由 "
        "`draft_reports` 在每个阶段边界自动起草，与代理的选择无关。也就是说："
        "**下级上报目前是引擎的自动参谋作业，代理还不能决定何时、向谁、报告什么。**")
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
