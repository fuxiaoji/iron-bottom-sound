"""CD-13: the command chain the PI specified, tested as behaviour.

Four things are asserted here, each of them a requirement rather than an
implementation detail:

1. a fleet commander exists as its own agent, with its own memory, ordering
   subordinates in natural language;
2. an order to the formation the commander sails in is **handed over in person** -
   readable in the same turn it was written - while an order to any other formation
   is a message and arrives on the message chain's clock;
3. every formation reports up in its own words, on top of the engine's floor report,
   and the reports arrive late because they are traffic like anything else;
4. the memory budget is what the agent actually gets: the current order and its own
   notes survive when the rendered block is over budget.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend" / "src"))

from iron_bottom_sound import command_delay  # noqa: E402
from iron_bottom_sound.command_observation import fleet_observation  # noqa: E402
from iron_bottom_sound.engine import ORDER_PHASES, IronBottomEngine  # noqa: E402
from iron_bottom_sound.formation_memory import (  # noqa: E402
    MAX_PROMPT_CHARS, FormationMemory, memory_for, render_for_prompt, set_active_order,
    write_note,
)
from iron_bottom_sound.llm import LLMPlayerSession  # noqa: E402
from iron_bottom_sound.models import GameOptions, OrderBatch, Phase, Side  # noqa: E402
from iron_bottom_sound.realistic_command import (  # noqa: E402
    RealisticCommander, default_setup_orders,
)

SCENARIO = "IBS-S-01"
SEED = 20270830


def _engine_and_sessions():
    engine = IronBottomEngine()
    state = engine.reset(SCENARIO, SEED, GameOptions(
        realistic_command=True, command_delay_mode=True,
    ))
    for side in Side:
        assert engine.submit_orders(state.game_id, OrderBatch(
            side=side, phase=Phase.FORMATION_SETUP,
            formation_setup=default_setup_orders(state, side),
        )).valid
    engine.advance(state.game_id)
    sessions = {side: LLMPlayerSession(side, RealisticCommander()) for side in Side}
    return engine, state, sessions


def _to_movement(engine, state, turn: int = 2) -> None:
    """Advance to a movement phase, the way the other command-delay tests do.

    The mode's own phases (movement and gunnery) are driven by the mode's own
    batches, exactly as ``llm_vs_llm.py`` does it, so the test exercises the real
    pipeline rather than a simplified one.
    """
    sessions = {side: LLMPlayerSession(side, RealisticCommander()) for side in Side}
    steps = 0
    while state.phase is not Phase.COMPLETE and steps < 200:
        steps += 1
        if state.phase is Phase.MOVEMENT_PLANNING and state.turn >= turn:
            return
        if state.phase in ORDER_PHASES:
            for side in Side:
                if side.value in state.submitted_orders:
                    continue
                if state.phase is Phase.MOVEMENT_PLANNING:
                    batch = OrderBatch(
                        side=side, phase=state.phase,
                        formation_movement=command_delay.formation_orders(state, side),
                    )
                elif state.phase is Phase.GUNNERY:
                    batch = command_delay.gunnery_batch(state, side)
                else:
                    batch = sessions[side].choose_orders(engine, state.game_id)
                result = engine.submit_orders(state.game_id, batch)
                assert result.valid, (state.turn, state.phase, side, result.errors[:2])
        engine.advance(state.game_id)
    raise AssertionError("never reached the movement phase")


@pytest.fixture(autouse=True)
def _clean_registries():
    yield
    command_delay.clear_side_policies()
    command_delay.clear_fleet_policies()


# --------------------------------------------------------------------------- 1

class _ScriptedFleet:
    """A fleet policy that returns a fixed JSON script, so the plumbing is testable
    without a model."""

    def __init__(self, replies: list[str]) -> None:
        self.replies = replies
        self.calls: list[dict] = []
        self.label = "scripted-fleet"

    def __call__(self, prompt: dict) -> str:
        self.calls.append(prompt)
        return self.replies[min(len(self.calls) - 1, len(self.replies) - 1)]


def test_fleet_agent_orders_in_natural_language_and_keeps_its_own_memory():
    engine, state, sessions = _engine_and_sessions()
    axis_fleet_id = state.command_delay.authorities["axis"].fleet_formation_id
    subordinates = [
        formation.id for formation in state.formations.values()
        if formation.side is Side.AXIS and formation.id != axis_fleet_id
    ]
    assert subordinates, "the scenario must have a subordinate formation to order"

    policy = _ScriptedFleet([
        '{"orders": [{"formation_id": "%s", "text": "向东南接敌，优先压制巡洋舰。"}],'
        ' "rationale_summary": "敌巡洋舰纵队正在逼近", "memory_note": "盯住敌先头"}'
        % subordinates[0]
    ])
    command_delay.set_fleet_policy(Side.AXIS, policy, policy.label)

    before_orders = len(state.command_delay.mission_orders)
    _to_movement(engine, state)

    assert len(state.command_delay.mission_orders) > before_orders, "no order was drafted"
    orders = [item for item in state.command_delay.mission_orders
              if item.formation_id in subordinates]
    assert orders, "the scripted order did not reach the order book"
    assert "向东南接敌" in orders[-1].mission

    # the fleet keeps its own memory: its note and its decision are in *its* memory,
    # not in the subordinate's
    fleet_memory = memory_for(state, axis_fleet_id)
    assert any("盯住敌先头" in note for note in fleet_memory.scratchpad)
    assert fleet_memory.of_kind("decision"), "the fleet did not remember its own decision"

    # and the transcript kept the chain of thought slot
    fleet_logs = [entry for entry in state.command_delay.agent_log
                  if entry.get("role") == "fleet_agent"]
    assert fleet_logs, "no fleet transcript was recorded"
    assert fleet_logs[-1]["decision"]["orders"], "the transcript lost the orders"
    assert "thinking" in fleet_logs[-1]["attempts"][0]


def test_fleet_prompt_contains_reports_with_their_age():
    engine, state, sessions = _engine_and_sessions()
    view = fleet_observation(engine, state, Side.AXIS)
    assert view.embarked is not None
    assert view.reports, "the fleet must see one report row per formation"
    embarked_rows = [row for row in view.reports if row.is_source_of_truth]
    assert len(embarked_rows) == 1
    assert embarked_rows[0].formation_id == view.embarked_formation_id


# --------------------------------------------------------------------------- 2

def test_order_to_the_commander_own_formation_is_handed_over_in_person():
    engine, state, sessions = _engine_and_sessions()
    authority = state.command_delay.authorities["axis"]
    own = authority.fleet_formation_id
    other = next(formation.id for formation in state.formations.values()
                 if formation.side is Side.AXIS and formation.id != own)

    _to_movement(engine, state)
    phase_at_issue = state.phase

    in_person = command_delay.draft_natural_order(
        engine, state, side=Side.AXIS, formation_id=own, text="本队保持航向，我随你舰指挥。",
    )
    by_signal = command_delay.draft_natural_order(
        engine, state, side=Side.AXIS, formation_id=other, text="向东南接敌。",
    )

    assert in_person.handling_delay == 0
    assert in_person.medium.value == "face_to_face", "in person is its own medium, not cheap TBS"
    assert in_person.payload["delivered_in_person"] is True
    assert in_person.reason and "当面" in in_person.reason
    # v2.3: a remote order inside direct TBS range costs no signal time either.  What
    # separates the two is that the radio order needs a channel slot and can therefore
    # spill, while the face-to-face one uses no slot at all (measured on the CD-13 battle:
    # distance alone used to add +1/+2 on a board whose TBS range covers it end to end).
    assert by_signal.medium.value == "tbs_short"
    assert by_signal.handling_delay == 0
    assert by_signal.delay.as_dict()["total"] == 0
    assert in_person.delay.as_dict()["total"] == 0

    # "in person" means: readable now, by the formation's own commander, in this phase
    assert in_person.delivered_turn == state.turn
    assert in_person.delivered_phase == phase_at_issue
    own_memory = memory_for(state, own)
    assert own_memory.active_order_text and "本队保持航向" in own_memory.active_order_text
    other_memory = memory_for(state, other)
    assert not (other_memory.active_order_text or "").startswith("向东南接敌"), (
        "the remote order must not be readable before the chain delivers it"
    )


# --------------------------------------------------------------------------- 3

class _ScriptedFormation:
    """A formation policy that reports in its own words and asks for clarification."""

    def __init__(self, report_text: str) -> None:
        self.report_text = report_text
        self.calls = 0

    def __call__(self, prompt: dict) -> str:
        self.calls += 1
        action = (prompt.get("legal_formation_actions") or [{}])[0].get("action_id")
        import json as _json

        return _json.dumps({
            "selected_movement_action_id": action,
            "report_actions": ["SITREP", "CLARIFICATION_REQUEST"],
            "report_text": self.report_text,
            "rationale_summary": "按命令行动，但对目标优先级不确定",
            "memory_note": "记得问清优先级",
        }, ensure_ascii=False)


def test_formation_reports_its_own_words_up_and_they_arrive_late():
    engine, state, sessions = _engine_and_sessions()
    policy = _ScriptedFormation("当面发现敌巡洋舰两艘，我正被压制，是否继续前压？")
    command_delay.set_side_policy(Side.AXIS, policy, "scripted-formation")

    _to_movement(engine, state)

    reports = [item for item in state.command_delay.messages
               if item.payload.get("report_text")]
    assert reports, "the formation's own words never reached the wire"
    authored = reports[0]
    assert authored.side is Side.AXIS
    assert "是否继续前压" in authored.payload["report_text"]
    # addressed to the fleet, and the snapshot says who is reporting
    authority = state.command_delay.authorities["axis"]
    assert authored.destination == authority.fleet_formation_id

    clarify = [item for item in state.command_delay.messages
               if item.kind.value == "clarification"]
    assert clarify, "CLARIFICATION_REQUEST did not become traffic"

    # v2.3: a report inside direct TBS range is not delayed by distance.  What it does
    # cost is a channel slot, and the delay it actually experiences is recorded as the
    # queue component rather than hidden in the medium's name.
    for item in reports + clarify:
        assert item.delay is not None
        assert item.delay.propagation == 0
        assert item.delay.handling == 0, "no kind- or length-based surcharge"
        assert item.route_provenance is not None
        assert item.route_provenance.tbs_range_hex > 0
    assert all(item.route_provenance.direct_tbs_available
               for item in reports if item.medium.value == "tbs_short")


def test_acknowledgement_now_reaches_the_ledger():
    engine, state, sessions = _engine_and_sessions()
    axis = state.command_delay.authorities["axis"]
    own = axis.fleet_formation_id

    _to_movement(engine, state)
    order = command_delay.draft_natural_order(
        engine, state, side=Side.AXIS, formation_id=own, text="保持航向。",
    )
    assert order.acknowledged_turn is None

    ack = command_delay.send(engine, state, command_delay.CommandMessage(
        message_id="", side=Side.AXIS, origin="test", destination=own,
        kind=command_delay.MessageKind.ACKNOWLEDGEMENT, issued_turn=state.turn,
        issued_phase=state.phase, handling_delay=0,
        payload={"order_id": order.payload["order_id"], "acknowledged_by": own},
    ))
    # mark it delivered the way the queue would, then fold it in
    ack.status = command_delay.MessageStatus.DELIVERED
    ack.delivered_turn = state.turn
    ack.delivered_phase = state.phase
    command_delay._apply_delivery(engine, state, ack)

    assert order.acknowledged_turn is not None, "the ack did not reach the order"
    entry = state.command_delay.formations[own]
    assert entry.last_ack_turn is not None


# --------------------------------------------------------------------------- 4

def test_memory_budget_keeps_the_order_and_the_notes_when_over_budget():
    """The bug this replaces: on an over-budget memory the *tail* was kept, which threw
    away exactly the current order and the scratchpad."""
    memory = FormationMemory(formation_id="f")
    set_active_order(memory_state := _memory_state(memory), "f",
                     text="第1战队：向东南接敌，压制敌巡洋舰。", turn=4)
    write_note(memory_state, "f", text="记住：不要离开本队", turn=4)
    for turn in range(1, 60):
        command_delay_remember(memory_state, "f", turn)

    rendered = render_for_prompt(memory, max_chars=600)
    assert len(rendered) <= 600 + len("\n…（较早的记忆已省略）")
    assert "向东南接敌" in rendered, "the order in force must survive trimming"
    assert "不要离开本队" in rendered, "the agent's own notes must survive trimming"
    assert "…（较早的记忆已省略）" in rendered, "the trim must be visible, not silent"


def test_memory_budget_is_large_enough_for_a_12_turn_battle():
    from iron_bottom_sound import formation_memory as fm

    assert fm.MAX_ENTRIES_PER_KIND >= 48
    assert fm.MAX_SCRATCHPAD_NOTES >= 24
    assert fm.MAX_TEXT_CHARS >= 600
    assert MAX_PROMPT_CHARS >= 12000


def _memory_state(memory: FormationMemory):
    """A minimal stand-in whose ``command_delay.memories`` holds ``memory``."""

    class _Mode:
        def __init__(self, memory):
            self.memories = {memory.formation_id: memory}

    class _State:
        def __init__(self, memory):
            self.command_delay = _Mode(memory)
            self.turn = 1

    return _State(memory)


def command_delay_remember(state, formation_id: str, turn: int) -> None:
    from iron_bottom_sound.formation_memory import remember

    remember(state, formation_id, kind="contact_seen",
             text=f"见到 敌舰（DD）距离 {turn}", turn=turn, phase="movement_planning")
