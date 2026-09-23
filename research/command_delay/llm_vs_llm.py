"""LLM vs LLM Command Delay battle driver (CD-12).

Both sides are commanded entirely by sub-agents: every formation has its own agent
(with its own memory), and each side's fleet commander writes natural-language
orders that travel as telegraphed signals.  The driver never calls a model itself —
it writes one request file per decision and waits for a response file, so the
orchestration layer (here: the ZCode workflow serving loop) supplies the models.

Honesty rules the driver keeps:
* a request that is not answered in time returns a sentinel that the adapter parses
  as invalid, so the recorded outcome is "transport timeout -> doctrine fallback",
  never a fabricated model decision;
* if the engine refuses an agent-derived movement batch, the driver falls back to
  the deterministic commander for that phase and records the substitution.
"""
from __future__ import annotations

import json
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend" / "src"))

from iron_bottom_sound import battle_report, command_delay  # noqa: E402
from iron_bottom_sound.command_observation import fleet_observation  # noqa: E402
from iron_bottom_sound.engine import ORDER_PHASES, IronBottomEngine  # noqa: E402
from iron_bottom_sound.llm import LLMPlayerSession  # noqa: E402
from iron_bottom_sound.models import (  # noqa: E402
    GameOptions,
    MessageStatus,
    OrderBatch,
    Phase,
    Side,
)
from iron_bottom_sound.realistic_command import (  # noqa: E402
    RealisticCommander,
    default_setup_orders,
)

SCENARIO = "IBS-S-01"
SEED = 20270830
EXCHANGE_TIMEOUT_S = 1800
FLEET_ORDER_TURNS = {1, 3}
TURN_CAP = 12


class BridgePolicy:
    """Transport over request/response files; the model lives outside this process.

    Every driver run stamps its files with a run id, so a restart can never have a
    stale sub-agent answer a different run's request.
    """

    def __init__(self, bridge_dir: Path, label: str) -> None:
        self.requests = bridge_dir / "requests"
        self.responses = bridge_dir / "responses"
        self.label = label
        self.run_id = str(int(time.time()))[-6:]
        self.counter = 0

    def __call__(self, prompt: dict) -> str:
        from iron_bottom_sound.formation_llm import compact_local_map

        self.counter += 1
        name = f"{self.run_id}-{self.counter:03d}"
        request_path = self.requests / f"req-{name}.request.json"
        response_path = self.responses / f"req-{name}.response.json"
        payload = compact_local_map(prompt)
        payload["bridge"] = {
            "request_id": name,
            "policy": self.label,
            "instruction_to_orchestrator": (
                "你是该编队的指挥官本人。只依据材料决策，输出仅一个 JSON 对象，"
                "不要 markdown 代码块、不要解释文字。"
            ),
        }
        request_path.write_text(
            json.dumps(payload, ensure_ascii=False, sort_keys=True), encoding="utf-8"
        )
        stamp = time.strftime("%H:%M:%S")
        print(f"[{stamp}] BRIDGE REQUEST {name} "
              f"({request_path.parent.resolve()})", flush=True)
        deadline = time.time() + EXCHANGE_TIMEOUT_S
        while time.time() < deadline:
            if response_path.exists():
                body = json.loads(response_path.read_text(encoding="utf-8"))
                content = str(body.get("content", "")).strip()
                print(f"[{time.strftime('%H:%M:%S')}] BRIDGE RESPONSE {name} "
                      f"({len(content)} chars)", flush=True)
                return content
            time.sleep(2)
        print(f"BRIDGE TIMEOUT {name} -> sentinel (doctrine fallback will be recorded)",
              flush=True)
        return "__BRIDGE_TIMEOUT__"


def strip_fences(text: str) -> str:
    return re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip(), flags=re.S)


def fleet_exchange(engine, state, side: Side, bridge: BridgePolicy, out: dict) -> None:
    """The fleet commander writes one natural-language order, telegraphed."""
    view = fleet_observation(engine, state, side)
    remote = [report for report in view.reports if not report.is_source_of_truth]
    if not remote:
        out["fleet_orders"].append({
            "turn": state.turn, "side": side.value, "skipped": "no remote formation",
        })
        return
    prompt = {
        "role": "fleet_commander",
        "turn": state.turn,
        "phase": state.phase.value,
        "side": side.value,
        "your_embarked_formation": {
            "name": view.embarked.get("name"),
            "ships": len(view.embarked.get("ship_ids", []) or []),
            "geometry": view.embarked.get("geometry_kind"),
        },
        "reports_on_your_formations": [
            {
                "formation_id": report.formation_id,
                "name": report.name,
                "position": (
                    report.guide_position.label if report.guide_position else None
                ),
                "reported_turn": report.reported_turn,
                "age_turns": report.age_turns,
                "ship_count": report.ship_count,
                "link": report.link_status.value,
            }
            for report in view.reports
        ],
        "contacts_seen_by_your_embarked_formation": view.contacts,
        "task": (
            "你是舰队总指挥。写一道自然语言命令给一支**非你所在**的编队（formation_id "
            "必须从上面 reports 里非精确编队中选）。只依据你收到的报告与接触——你可能"
            "只有几回合前的旧情报。命令要具体：给方向/距离/接敌或规避意图与火力优先级。"
            "输出仅一个 JSON 对象："
            '{"formation_id":"...","text":"...（≤140字）","priority_classes":["DD",...]}. '
            "不要 markdown，不要解释。"
        ),
    }
    content = bridge(prompt)
    text = strip_fences(content)
    try:
        parsed = json.loads(text)
        formation_id = str(parsed["formation_id"])
        order_text = str(parsed["text"]).strip()
        classes = [str(c) for c in parsed.get("priority_classes", [])][:4]
        assert formation_id in {report.formation_id for report in remote}
        assert order_text
    except Exception as error:  # noqa: BLE001 - recorded, battle continues
        out["fleet_orders"].append({
            "turn": state.turn, "side": side.value,
            "skipped": f"unusable fleet response: {error}",
            "raw": text[:200],
        })
        return
    message = command_delay.draft_natural_order(
        engine, state, side=side, formation_id=formation_id,
        text=order_text, priority_classes=classes or None,
    )
    out["fleet_orders"].append({
        "turn": state.turn,
        "side": side.value,
        "formation_id": formation_id,
        "text": order_text,
        "priority_classes": classes,
        "message_id": message.message_id,
        "medium": message.medium.value,
        "handling_delay": message.handling_delay,
        "issued_turn": message.issued_turn,
        "route_reason": message.reason,
    })
    print(
        f"FLEET ORDER {side.value} -> {formation_id}: {order_text[:40]}… "
        f"({message.medium.value}, +{message.handling_delay}t)", flush=True,
    )


def main() -> int:
    out_dir = Path(__file__).resolve().parent / "battle"
    (out_dir / "requests").mkdir(parents=True, exist_ok=True)
    (out_dir / "responses").mkdir(parents=True, exist_ok=True)
    images = out_dir / "images"
    images.mkdir(exist_ok=True)
    for old in (out_dir / "requests").glob("*"):
        old.unlink()
    for old in (out_dir / "responses").glob("*"):
        old.unlink()

    engine = IronBottomEngine()
    state = engine.reset(SCENARIO, SEED, GameOptions(
        realistic_command=True, command_delay_mode=True, battle_report=True,
    ))
    bridge = BridgePolicy(out_dir, "zcode-subagent")
    for side in Side:
        command_delay.set_side_policy(side, bridge, bridge.label)

    sessions = {side: LLMPlayerSession(side, RealisticCommander()) for side in Side}
    battle: dict = {
        "scenario": SCENARIO, "seed": SEED,
        "sides": {side.value: bridge.label for side in Side},
        "turns": [], "fleet_orders": [], "substitutions": [],
        "images_root": "images",
    }

    def capture(prev_phase) -> None:
        try:
            battle_report.capture_after_advance(
                None, images, state, engine, prev_phase,
            )
        except Exception as error:  # noqa: BLE001 - 报告失败不中断对局
            print(f"capture failed: {error}", flush=True)

    def submit(batch: OrderBatch, side: Side) -> tuple[bool, list[str]]:
        result = engine.submit_orders(state.game_id, batch)
        return result.valid, list(result.errors)

    # 编成
    for side in Side:
        assert engine.submit_orders(state.game_id, OrderBatch(
            side=side, phase=Phase.FORMATION_SETUP,
            formation_setup=default_setup_orders(state, side),
        )).valid
    prev = state.phase
    engine.advance(state.game_id)
    capture(prev)

    turn_records: dict[int, dict] = {}
    steps = 0
    while state.phase != Phase.COMPLETE and state.turn <= TURN_CAP and steps < 400:
        steps += 1
        if state.phase in ORDER_PHASES:
            for side in Side:
                if side.value in state.submitted_orders:
                    continue
                if state.phase == Phase.MOVEMENT_PLANNING:
                    if state.turn in FLEET_ORDER_TURNS:
                        fleet_exchange(engine, state, side, bridge, battle)
                    orders = command_delay.formation_orders(state, side)
                    valid, errors = submit(OrderBatch(
                        side=side, phase=state.phase, formation_movement=orders,
                    ), side)
                    if not valid:
                        # 代理方案被引擎拒绝：如实记录，退回确定性指挥官的方案。
                        battle["substitutions"].append({
                            "turn": state.turn, "side": side.value, "errors": errors[:3],
                        })
                        _, fallback, _ = RealisticCommander().choose_plan(
                            engine, state.game_id, side,
                        )
                        valid, errors = submit(fallback, side)
                        assert valid, errors[:3]
                elif state.phase == Phase.GUNNERY:
                    valid, errors = submit(command_delay.gunnery_batch(state, side), side)
                    assert valid, (state.turn, side, errors[:3])
                else:
                    planner = sessions[side].choose_orders(engine, state.game_id)
                    trimmed = OrderBatch(
                        side=side, phase=state.phase,
                        torpedoes=planner.torpedoes,
                        contacts=planner.contacts,
                        contact_movement=planner.contact_movement,
                        reinforcements=planner.reinforcements,
                    )
                    valid, errors = submit(trimmed, side)
                    assert valid, (state.turn, state.phase, side, errors[:3])
        record = turn_records.setdefault(state.turn, {
            "turn": state.turn, "events": [], "images": [],
        })
        before = len(state.events)
        prev = state.phase
        engine.advance(state.game_id)
        capture(prev)
        record["events"].extend(
            {"turn": event.turn, "phase": event.phase.value, "type": event.type,
             "message": event.message,
             "payload": {k: v for k, v in event.payload.items()
                         if k != "order_batch"}}
            for event in state.events[before:]
        )
        record["images"].append(str(prev.value))
        print(f"advanced to {state.phase.value} (turn {state.turn})", flush=True)

    # 终局数据：消息台账、代理决策、记忆、代理日志、图像清单
    mode = state.command_delay
    battle["final"] = {
        "complete": state.phase == Phase.COMPLETE,
        "turns": state.turn,
        "winner": state.winner.value if state.winner else None,
        "victory_reason": state.victory_reason,
        "score": state.score,
        "friendly_collisions": sum(
            1 for event in state.events
            if event.type == "collision" and event.payload.get("friendly")
        ),
    }
    battle["messages"] = [message.model_dump(mode="json") for message in mode.messages]
    battle["decisions"] = mode.decisions
    battle["policy_labels"] = dict(mode.policy_labels)
    battle["images_files"] = sorted(
        str(path.relative_to(out_dir)) for path in images.rglob("*")
        if path.suffix == ".png"
    )
    from iron_bottom_sound.formation_memory import memory_payload

    battle["memories"] = {
        formation_id: memory_payload(memory)
        for formation_id, memory in sorted(mode.memories.items())
    }
    battle["agent_log"] = [
        {
            "turn": record["turn"], "phase": record["phase"],
            "side": record["side"], "formation_id": record["formation_id"],
            "formation_name": record["formation_name"], "agent": record["agent"],
            "order_text": record["order_text"], "memory_text": record["memory_text"],
            "attempts": record["attempts"],
            "decision": record["decision"],
        }
        for record in mode.agent_log
    ]
    (out_dir / "battle_data.json").write_text(
        json.dumps(battle, ensure_ascii=False, indent=1, default=str), encoding="utf-8"
    )
    print(f"BATTLE COMPLETE turns={state.turn} winner={state.winner}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
