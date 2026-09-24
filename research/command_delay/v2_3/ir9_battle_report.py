"""IR-9 (part 2): the validation battle's report, with the plan's assertions attached.

The report must expose, per message: route reason, distance, selected medium, delay
decomposition, issued/observed/received turns, order revision and provenance ids.  The
assertions it must carry are the ones the plan names:

    zero causal information leaks
    zero unit conversion violations
    zero unsupported CONFIRMED enemy-state claims
    zero subordinate GunneryOrder submissions
    no repetitive mission-order spam when no mission changed
    replay PASS
    Classic/Realistic regression PASS

Everything here is derived from the battle record; nothing is asserted from memory.

Usage::

    .venv/bin/python research/command_delay/v2_3/ir9_battle_report.py --battle battle_v2_3
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "backend" / "src"))

from iron_bottom_sound import claims  # noqa: E402
from iron_bottom_sound.models import KnowledgeItem  # noqa: E402

SIDE_CN = {"axis": "日方", "allies": "美方"}
MEDIUM_CN = {
    "face_to_face": "当面交办", "tbs_short": "TBS 直连", "blinker": "视觉信号",
    "wt_coded": "编码电文", "wt_reencipher_relay": "转报再加密", "multi_hop": "复合路由",
    "blackout": "无通路",
}
GUNNERY_FIELDS = ("gunnery", "gunnery_orders", "mounts", "mount_ids", "firing_solution",
                  "hit_modifier", "expected_hits")


def load(battle_dir: Path) -> dict:
    record = json.loads((battle_dir / "battle_data.json").read_text(encoding="utf-8"))
    calls = [json.loads(line) for line in (battle_dir / "calls.jsonl").read_text(
        encoding="utf-8").splitlines() if line.strip()]
    record["_calls"] = calls
    return record


def knowledge_from_record(record: dict) -> dict[str, list[KnowledgeItem]]:
    """Rebuild each formation's knowledge ledger from the record.

    The live run keeps the ledger in engine state; the record keeps the two things it is
    built from - what each formation could see (the per-phase views) and what was
    delivered to it (the message ledger) - so the ledger is reconstructed rather than
    trusted from a summary.
    """
    ledgers: dict[str, list[KnowledgeItem]] = {}
    for view in record.get("three_views", []):
        turn = int(view["turn"])
        for side_payload in (view.get("sides") or {}).values():
            for formation_id, observation in (side_payload.get("formations") or {}).items():
                bucket = ledgers.setdefault(formation_id, [])
                for contact in observation.get("local_contacts") or []:
                    if not contact.get("ship_id"):
                        continue
                    for field, value in (("POSITION", contact.get("position")),
                                         ("HEADING", contact.get("heading")),
                                         ("SPEED", contact.get("speed"))):
                        if value is None:
                            continue
                        if any(item.subject_id == contact["ship_id"] and item.field == field
                               for item in bucket):
                            continue
                        bucket.append(KnowledgeItem(
                            subject_id=contact["ship_id"], field=field, value=value,
                            observed_turn=turn, received_turn=turn,
                            source_kind="LOCAL_OBSERVATION", source_id=formation_id,
                            confidence="CONFIRMED",
                        ))
    for message in record.get("messages", []):
        if message.get("delivered_turn") is None:
            continue
        payload = message.get("payload") or {}
        snapshot = payload.get("report") or {}
        reporter = snapshot.get("reporting_formation_id")
        holder = message.get("destination")
        if not reporter or not holder:
            continue
        bucket = ledgers.setdefault(holder, [])
        position = snapshot.get("guide_position")
        label = position.get("label") if isinstance(position, dict) else position
        for field, value in (("POSITION", label), ("HEADING", snapshot.get("guide_heading")),
                             ("SPEED", snapshot.get("guide_speed"))):
            if value is None:
                continue
            bucket.append(KnowledgeItem(
                subject_id=reporter, field=field, value=value,
                observed_turn=int(message["issued_turn"]),
                received_turn=message["delivered_turn"],
                source_kind="DELIVERED_MESSAGE", source_id=reporter,
                message_id=message["message_id"], confidence="REPORTED",
            ))
        text = str(payload.get("report_text") or "").strip()
        if text:
            bucket.append(KnowledgeItem(
                subject_id=reporter, field="REPORT_TEXT", value=text[:600],
                observed_turn=int(message["issued_turn"]),
                received_turn=message["delivered_turn"],
                source_kind="DELIVERED_MESSAGE", source_id=reporter,
                message_id=message["message_id"], confidence="REPORTED",
            ))
    return ledgers


def enemy_ids(record: dict) -> set[str]:
    view = next(iter(record.get("three_views", [])), None)
    if not view:
        return set()
    return {ship_id for ship_id, row in view["god"]["ships"].items()
            if row["side"] != "axis"} | {
        ship_id for ship_id, row in view["god"]["ships"].items() if row["side"] == "axis"}


# ------------------------------------------------------------------ assertions

def assert_causal_leaks(record: dict) -> dict:
    """The scanner's verdict, run on this battle (it needs the views, which the record has)."""
    scanner = ROOT / "research" / "battle_video" / "scan_provider_battle.py"
    completed = subprocess.run(
        [sys.executable, str(scanner), "--battle", "battle_v2_3"],
        capture_output=True, text=True, cwd=str(ROOT / "research" / "command_delay"),
    )
    payload = json.loads(completed.stdout) if completed.stdout.strip().startswith("{") else {}
    return {"verdict": payload.get("verdict", "UNKNOWN"),
            "calls_scanned": payload.get("calls_scanned"),
            "findings": payload.get("findings", [])[:5],
            "criterion": payload.get("criterion")}


def assert_unit_violations(record: dict) -> list[str]:
    """Prose that states a contact's hex distance as nautical miles.

    Decidable per prompt: the prompt carries the contact's engine-computed range_hex, so a
    sentence repeating that number with 海里 is the v2.2 error.
    """
    findings: list[str] = []
    for call in record.get("_calls", []):
        if call.get("transport_error"):
            continue
        prompt = call.get("prompt") or {}
        contacts = prompt.get("local_contacts") or []
        ranges = {int(contact["range_hex"]) for contact in contacts
                  if isinstance(contact, dict) and contact.get("range_hex") is not None}
        if not ranges:
            continue
        text = json.dumps(prompt, ensure_ascii=False)
        for match in re.finditer(r"(\d{1,3})\s*[至\-~]?\s*(\d{1,3})?\s*海里", text):
            numbers = {int(value) for value in match.groups() if value}
            offending = numbers & ranges
            if offending:
                findings.append(
                    f"{call.get('role')} {call.get('side')}: 把 {sorted(offending)} 格写成海里："
                    f"「{match.group(0)}」"
                )
    return findings


def assert_unsupported_confirmed(record: dict, ledgers: dict) -> list[str]:
    """Confirmed enemy-state claims with nothing in the speaker's ledger to support them."""
    findings: list[str] = []
    all_enemy = enemy_ids(record)
    texts: list[tuple[str, str]] = []
    for record_row in record.get("decisions", []):
        texts.append((record_row.get("formation_id") or "", record_row.get("rationale_summary") or ""))
        texts.append((record_row.get("formation_id") or "", record_row.get("memory_note") or ""))
    for entry in record.get("agent_log", []):
        for attempt in entry.get("attempts", []):
            texts.append((entry.get("formation_id") or "", str(attempt.get("raw_response") or "")))
            texts.append((entry.get("formation_id") or "", str(attempt.get("thinking") or "")))
    for holder, text in texts:
        if not text:
            continue
        ledger = ledgers.get(holder, [])
        for claim in claims.unsupported_confirmed(text, subject_ids=all_enemy, knowledge=ledger):
            findings.append(f"{holder}: {claim.text[:80]}")
    return findings


def assert_no_subordinate_gunnery(record: dict) -> list[str]:
    findings: list[str] = []
    for entry in record.get("agent_log", []):
        for attempt in entry.get("attempts", []):
            raw = str(attempt.get("raw_response") or "")
            if not raw:
                continue
            try:
                body = json.loads(raw)
            except ValueError:
                continue
            if isinstance(body, dict):
                present = sorted(set(GUNNERY_FIELDS) & set(body))
                if present:
                    findings.append(f"{entry.get('formation_id')}: {present}")
    for decision in record.get("decisions", []):
        present = sorted(set(GUNNERY_FIELDS) & set(decision))
        if present:
            findings.append(f"{decision.get('formation_id')}: {present}")
    return findings


def assert_no_order_spam(record: dict) -> dict:
    """No formation receives two orders in one turn, and no order restates the standing one.

    The orders are read from the **message ledger**, which is where they live: the engine
    writes each order as a message (that is the mode's input channel), and the message
    payload carries the order event, revision and lineage.
    """
    from iron_bottom_sound.command_delay import _normalised

    orders = [message for message in record.get("messages", [])
              if message.get("kind") == "mission_order"]
    by_turn: dict[tuple[int, str], list[dict]] = {}
    for message in orders:
        by_turn.setdefault((int(message["issued_turn"]), message["destination"]), []).append(message)
    duplicates = [f"T{turn} {destination}" for (turn, destination), rows in by_turn.items()
                  if len(rows) > 1]
    lineages: dict[str, list[str]] = {}
    for message in orders:
        lineages.setdefault(message["destination"], []).append(
            (message.get("payload") or {}).get("order_text") or ""
        )
    # The engine's rule is "an order identical to the one *in force* is not a new order", so
    # that is what is checked: for each formation, an order may not repeat the text of the
    # latest order that had been delivered to it by the time this one was issued.
    # a withdrawn order is not "in force", so the engine would allow its text again
    cancelled = {
        (message.get("payload") or {}).get("amends_order_id")
        for message in orders
        if (message.get("payload") or {}).get("order_event") == "CANCEL_ORDER"
    }
    restatements = 0
    for destination, rows in (
        (destination, [message for message in orders if message["destination"] == destination])
        for destination in lineages
    ):
        for message in rows:
            issued = int(message["issued_turn"])
            in_force = [
                other for other in rows
                if other is not message
                and (other.get("payload") or {}).get("order_id") not in cancelled
                and other.get("delivered_turn") is not None
                and int(other["delivered_turn"]) <= issued
                and int(other["issued_turn"]) < issued
            ]
            if not in_force:
                continue
            latest = max(in_force, key=lambda other: int(other["issued_turn"]))
            if _normalised((latest.get("payload") or {}).get("order_text")) == _normalised(
                (message.get("payload") or {}).get("order_text")
            ):
                restatements += 1
    revisions = sorted({int((message.get("payload") or {}).get("revision") or 1)
                        for message in orders})
    return {
        "orders": len(orders),
        "revisions_seen": revisions,
        "duplicate_orders_in_one_turn": duplicates[:5],
        "restated_orders": restatements,
        "per_formation": {destination: len(texts) for destination, texts in lineages.items()},
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--battle", default="battle_v2_3")
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args()
    battle_dir = ROOT / "research" / "command_delay" / args.battle
    out_path = args.out or (battle_dir / "REPORT_V2_3.md")
    record = load(battle_dir)
    ledgers = knowledge_from_record(record)
    messages = record.get("messages", [])

    causal = assert_causal_leaks(record)
    units = assert_unit_violations(record)
    unconfirmed = assert_unsupported_confirmed(record, ledgers)
    gunnery = assert_no_subordinate_gunnery(record)
    spam = assert_no_order_spam(record)
    replay = json.loads((battle_dir / "replay_verification.json").read_text(encoding="utf-8")) \
        if (battle_dir / "replay_verification.json").exists() else {"verdict": "NOT RUN"}

    lines: list[str] = []
    add = lines.append
    add("# 命令延迟 v2.3 · 实机对局战报（IR-9）")
    add("")
    add(f"- 想定 / seed：`{record.get('scenario')}` / {record.get('seed')}")
    add(f"- 模型：编队级 `{record.get('formation_policy')}`，舰队级 `{record.get('fleet_policy')}`，"
        f"思维链{'开启' if record.get('thinking_enabled') else '关闭'}")
    final = record.get("final", {})
    add(f"- 结果：{final.get('turns')} 回合 · {final.get('victory_reason') or '未分胜负'}；"
        f"比分 轴心 {final.get('score', {}).get('axis', 0)} : {final.get('score', {}).get('allies', 0)}")
    add("")
    add("## 断言")
    add("")
    add("| 断言 | 结果 | 证据 |")
    add("|---|---|---|")
    add(f"| 零因果信息泄漏 | {'PASS' if causal.get('verdict') == 'PASS' else 'FAIL'} "
        f"| 扫描 {causal.get('calls_scanned')} 条提示词，{len(causal.get('findings', []))} 处发现 |")
    add(f"| 零单位换算违规 | {'PASS' if not units else 'FAIL'} | {len(units)} 处 |")
    add(f"| 零无据 CONFIRMED 敌情断言 | {'PASS' if not unconfirmed else 'FAIL'} | {len(unconfirmed)} 处 |")
    add(f"| 零下级提交炮击令 | {'PASS' if not gunnery else 'FAIL'} | {len(gunnery)} 处 |")
    add(f"| 无重复下达同一命令 | "
        f"{'PASS' if not spam['duplicate_orders_in_one_turn'] and not spam['restated_orders'] else 'FAIL'} "
        f"| 命令 {spam['orders']} 条、修订 {spam['revisions_seen']}、重述 {spam['restated_orders']} |")
    add(f"| 重演一致 | {replay.get('verdict')} | "
        f"{replay.get('phases_compared', '—')} 阶段 / {replay.get('phase_mismatches', '—')} 不一致 |")
    add("")

    add("## 报文台账（逐条含路由出处与延迟分解）")
    add("")
    add("| 报文 | 类型 | 阵营 | 媒介 | 距离(格) | TBS可达 | 延迟分解 h/e/r/re/q/c | 合计 | 发出 | 送达 | 路由理由 |")
    add("|---|---|---|---|---|---|---|---|---|---|---|")
    for message in messages:
        provenance = message.get("route_provenance") or {}
        delay = message.get("delay") or {}
        decomposition = "/".join(str(delay.get(key, 0)) for key in
                                 ("handling", "encoding", "relay", "reencipher", "queue",
                                  "clarification"))
        total = sum(int(delay.get(key, 0)) for key in
                    ("handling", "encoding", "relay", "reencipher", "queue", "clarification"))
        delivered = message.get("delivered_turn")
        add(f"| `{message.get('message_id')}` | {message.get('kind')} | {SIDE_CN.get(message.get('side'), '')} "
            f"| {MEDIUM_CN.get(message.get('medium'), message.get('medium'))} "
            f"| {provenance.get('distance_hex', '—')} "
            f"| {'是' if provenance.get('direct_tbs_available') else '否'} "
            f"| {decomposition} | {total} "
            f"| T{message.get('issued_turn')} "
            f"| {('T' + str(delivered)) if delivered is not None else '—'} "
            f"| {(message.get('reason') or '')[:60]} |")
    add("")

    if units:
        add("### 单位违规明细")
        add("")
        for item in units[:20]:
            add(f"- {item}")
        add("")
    if unconfirmed:
        add("### 无据断言明细")
        add("")
        for item in unconfirmed[:20]:
            add(f"- {item}")
        add("")
    add("## 命令修订线")
    add("")
    add("| 命令 | 编队 | 事件 | 修订 | 修订自 | 签发回合 |")
    add("|---|---|---|---|---|---|")
    for message in [item for item in messages if item.get("kind") == "mission_order"]:
        payload = message.get("payload") or {}
        add(f"| `{payload.get('order_id')}` | {message.get('destination')} "
            f"| {payload.get('order_event')} | {payload.get('revision')} "
            f"| {payload.get('amends_order_id') or '—'} | T{message.get('issued_turn')} |")
    add("")
    out_path.write_text("\n".join(lines), encoding="utf-8")
    summary = {
        "report": str(out_path.relative_to(ROOT)),
        "assertions": {
            "causal_information": causal.get("verdict"),
            "unit_violations": len(units),
            "unsupported_confirmed": len(unconfirmed),
            "subordinate_gunnery": len(gunnery),
            "order_spam": spam,
            "replay": replay.get("verdict"),
        },
    }
    (battle_dir / "ir9_assertions.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
