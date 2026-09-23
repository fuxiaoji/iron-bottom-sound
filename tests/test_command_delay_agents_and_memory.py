"""CD-10: formation agents with memory, natural-language orders, and the agent log.

The user's acceptance points for this stage:

* every formation is commanded by its **own** agent, and that agent has memory;
* the fleet commander's input channel is a natural-language order, written in the
  movement phase and **telegraphed** — subject to the same link delay and loss as
  any other signal;
* the lobby offers no state machine for the mode: its formations run an LLM policy,
  and when no model is available the label says doctrine rather than pretending;
* debug mode can show each agent's prompt, raw response and memory.

The model itself is never called here: ``ProviderPolicy`` is exercised with an
injected stub client, so the transport code is tested without a network or a key.
"""
from __future__ import annotations

import json

import pytest

from iron_bottom_sound import command_delay, formation_llm, formation_memory
from iron_bottom_sound.engine import ORDER_PHASES, IronBottomEngine
from iron_bottom_sound.llm import LLMPlayerSession
from iron_bottom_sound.models import (
    CommunicationMedium,
    GameOptions,
    MessageStatus,
    OrderBatch,
    Phase,
    Side,
)
from iron_bottom_sound.realistic_command import RealisticCommander, default_setup_orders

CD = GameOptions(realistic_command=True, command_delay_mode=True)


def start(scenario: str = "IBS-S-01", seed: int = 20270830):
    engine = IronBottomEngine()
    state = engine.reset(scenario, seed, CD)
    for side in Side:
        assert engine.submit_orders(state.game_id, OrderBatch(
            side=side, phase=Phase.FORMATION_SETUP,
            formation_setup=default_setup_orders(state, side),
        )).valid
    engine.advance(state.game_id)
    return engine, state


def play(engine, state, hook=None, max_steps: int = 400) -> None:
    sessions = {side: LLMPlayerSession(side, RealisticCommander()) for side in Side}
    steps = 0
    while state.phase != Phase.COMPLETE and steps < max_steps:
        steps += 1
        if hook is not None:
            hook(engine, state)
        if state.phase in ORDER_PHASES:
            for side in Side:
                if side.value in state.submitted_orders:
                    continue
                result = engine.submit_orders(
                    state.game_id, sessions[side].choose_orders(engine, state.game_id)
                )
                assert result.valid, (state.turn, state.phase, side, result.errors[:2])
        engine.advance(state.game_id)


def to_movement(engine, state, turn: int = 2) -> None:
    sessions = {side: LLMPlayerSession(side, RealisticCommander()) for side in Side}
    steps = 0
    while state.phase != Phase.COMPLETE and steps < 200:
        steps += 1
        if state.phase == Phase.MOVEMENT_PLANNING and state.turn >= turn:
            return
        if state.phase in ORDER_PHASES:
            for side in Side:
                if side.value in state.submitted_orders:
                    continue
                assert engine.submit_orders(
                    state.game_id, sessions[side].choose_orders(engine, state.game_id)
                ).valid
        engine.advance(state.game_id)
    raise AssertionError("never reached the movement phase")


# --------------------------------------------------------------------------- memory

def test_every_formation_gets_its_own_memory() -> None:
    engine, state = start()
    play(engine, state)
    mode = state.command_delay
    formations = {
        formation.id for formation in state.formations.values()
    }
    assert set(mode.memories) <= formations
    assert mode.memories, "the agents ran, so memories must exist"
    # One memory object per formation, and never shared.
    assert len({id(memory) for memory in mode.memories.values()}) == len(mode.memories)


def test_memory_records_what_the_formation_experienced() -> None:
    engine, state = start()
    play(engine, state)
    memory = state.command_delay.memories[sorted(state.command_delay.memories)[0]]
    counts = formation_memory.memory_payload(memory)["counts"]
    assert counts["decision"] > 0, "a formation remembers what it decided"
    assert counts["report_sent"] > 0
    assert counts["order_received"] > 0
    for entry in memory.entries:
        assert entry.kind in formation_memory.MEMORY_KINDS


def test_memory_is_bounded() -> None:
    engine, state = start()
    memory = formation_memory.memory_for(state, "probe")
    for index in range(formation_memory.MAX_ENTRIES_PER_KIND * 3):
        formation_memory.remember(
            state, "probe", kind="decision", text=f"decision {index}",
            turn=1, phase="movement_planning",
        )
    assert len(memory.of_kind("decision")) == formation_memory.MAX_ENTRIES_PER_KIND
    for index in range(formation_memory.MAX_SCRATCHPAD_NOTES * 3):
        formation_memory.write_note(state, "probe", text=f"note {index}", turn=1)
    assert len(memory.scratchpad) == formation_memory.MAX_SCRATCHPAD_NOTES
    # The newest survive, the oldest are dropped.
    assert memory.scratchpad[-1].endswith(str(formation_memory.MAX_SCRATCHPAD_NOTES * 3 - 1))


def test_memory_only_ever_holds_local_material() -> None:
    """A formation's memory must not contain anything it never observed."""
    engine, state = start()
    play(engine, state)
    for side in Side:
        opponents = {
            ship.id for ship in state.ships.values() if ship.side is not side
        }
        for formation in command_delay.active_formations(state, side):
            memory = state.command_delay.memories.get(formation.id)
            if memory is None:
                continue
            text = json.dumps(memory_payload_json(memory), ensure_ascii=False)
            own = {
                ship_id for ship_id in formation.ship_ids
            }
            # Opposing ship ids may appear only if that formation sighted them.
            seen = {
                entry.meta.get("ship_id")
                for entry in memory.of_kind("contact_seen")
            }
            leaked = [ship_id for ship_id in opponents
                      if ship_id in text and ship_id not in seen]
            assert not leaked, f"{formation.id} remembers unseen enemies {leaked}"
            del own


def memory_payload_json(memory):
    return formation_memory.memory_payload(memory)


def test_render_for_prompt_shows_the_current_order_and_trims_from_the_oldest() -> None:
    engine, state = start()
    formation_memory.set_active_order(
        state, "probe", text="向东拉开距离", turn=4, order_id="o1",
    )
    for index in range(40):
        formation_memory.remember(
            state, "probe", kind="contact_seen", text=f"接触 {index}",
            turn=1, phase="movement_planning",
        )
    rendered = formation_memory.render_for_prompt(
        formation_memory.memory_for(state, "probe"), max_chars=600,
    )
    assert "向东拉开距离" in rendered, "the order in force survives trimming"
    assert len(rendered) <= 600 + 20


# --------------------------------------------------------------------------- orders

def test_a_natural_language_order_is_telegraphed_and_remembered() -> None:
    engine, state = start()
    to_movement(engine, state)
    target = next(
        formation for formation in command_delay.active_formations(state, Side.ALLIES)
        if formation.id != command_delay.authority_for(state, Side.ALLIES).fleet_formation_id
    )
    text = "敌轻巡已出现在西北，你部向东拉开距离保持接触；优先打掉对方的驱逐舰。"
    message = command_delay.draft_natural_order(
        engine, state, side=Side.ALLIES, formation_id=target.id, text=text,
        priority_classes=["DD", "CL"],
    )
    assert message.kind.value == "mission_order"
    assert message.payload["order_text"] == text
    assert message.medium != CommunicationMedium.BLACKOUT, message.reason

    steps = 0
    while state.phase != Phase.COMPLETE and steps < 200 and message.status != MessageStatus.DELIVERED:
        steps += 1
        to_movement(engine, state, turn=state.turn + 1)
    assert message.status == MessageStatus.DELIVERED, message.reason
    memory = state.command_delay.memories[target.id]
    assert memory.active_order_text == text, "the formation holds the words it was sent"
    assert memory.active_order_turn == message.delivered_turn
    assert memory.of_kind("order_received")


def test_an_order_to_a_formation_that_is_not_yours_is_refused() -> None:
    engine, state = start()
    opponent = command_delay.active_formations(state, Side.ALLIES)[0]
    with pytest.raises(ValueError, match="unknown formation"):
        command_delay.draft_natural_order(
            engine, state, side=Side.AXIS, formation_id=opponent.id, text="投降",
        )


def test_an_empty_order_is_refused() -> None:
    engine, state = start()
    target = command_delay.active_formations(state, Side.AXIS)[0]
    with pytest.raises(ValueError, match="needs text"):
        command_delay.draft_natural_order(
            engine, state, side=Side.AXIS, formation_id=target.id, text="   ",
        )


def test_the_order_text_is_what_the_agent_reads() -> None:
    engine, state = start()
    to_movement(engine, state)
    target = next(
        formation for formation in command_delay.active_formations(state, Side.AXIS)
        if formation.id != command_delay.authority_for(state, Side.AXIS).fleet_formation_id
    )
    text = "保持与主力相对位置，向北规避鱼雷"
    command_delay.draft_natural_order(
        engine, state, side=Side.AXIS, formation_id=target.id, text=text,
    )
    # deliver it directly through the queue rather than waiting for the link
    message = next(
        item for item in state.command_delay.messages
        if item.payload.get("order_text") == text
    )
    message.status = MessageStatus.QUEUED
    command_delay._apply_delivery(engine, state, message.model_copy(update={
        "status": MessageStatus.DELIVERED, "delivered_turn": state.turn,
        "observed_turn": state.turn, "delivered_phase": state.phase,
    }))
    memory = state.command_delay.memories[target.id]
    assert memory.active_order_text == text


def test_formation_orders_come_from_the_agents_not_from_a_plotter() -> None:
    engine, state = start()
    to_movement(engine, state)
    orders = command_delay.formation_orders(state, Side.AXIS)
    decided = {
        record["formation_id"]: record["selected_movement_plan"]
        for record in state.command_delay.decisions
        if record.get("turn") == state.turn
    }
    assert orders, "the agents decided, so orders exist"
    for order in orders:
        assert order.leader_plan == decided[order.formation_id]


# --------------------------------------------------------------------------- model path

class StubResponse:
    def __init__(self, payload: dict) -> None:
        self._payload = payload
        self.status_code = 200

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return self._payload


class StubClient:
    """Records the requests and replays a canned model reply."""

    def __init__(self, content: str) -> None:
        self.content = content
        self.requests: list[dict] = []

    def post(self, url, headers=None, json=None):  # noqa: A002 - httpx signature
        self.requests.append({"url": url, "headers": headers, "payload": json})
        return StubResponse({
            "id": "stub-1",
            "choices": [{"message": {"content": self.content}, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5},
        })


def test_the_provider_policy_sends_the_memory_and_order_and_parses_the_reply() -> None:
    content = json.dumps({
        "selected_movement_action_id": None,
        "selected_contingency_branch": "loss_of_comm_branch",
        "target_priority_adjustments": [],
        "report_actions": ["SITREP"],
        "acknowledgement": True,
        "rationale_summary": "保持接触",
        "memory_note": "记住：敌轻巡在西北",
    })
    client = StubClient(content)
    policy = formation_llm.ProviderPolicy(
        endpoint="https://example.invalid/v1", model="stub-model",
        api_key="stub-key", client=client,
    )
    engine, state = start()
    to_movement(engine, state)
    from iron_bottom_sound.command_observation import formation_observation

    target = command_delay.active_formations(state, Side.ALLIES)[0]
    observation = formation_observation(engine, state, Side.ALLIES, target.id)
    memory_text = "【当前生效命令】向东拉开距离"
    decision = formation_llm.FormationLLMAgent(policy, max_retries=0).act(
        observation, None, observation.comm_state,
        observation.legal_formation_actions, observation.legal_target_priority_options,
        memory_text=memory_text, order_text="向东拉开距离",
    )
    sent = client.requests[0]
    assert sent["url"].endswith("/chat/completions")
    assert sent["headers"]["Authorization"] == "Bearer stub-key"
    user = json.loads(sent["payload"]["messages"][1]["content"])
    assert user["your_memory"] == memory_text
    assert user["order_text"] == "向东拉开距离"
    assert decision.memory_note == "记住：敌轻巡在西北"
    assert decision.selected_contingency_branch == "loss_of_comm_branch"


def test_make_policy_reports_why_there_is_no_model() -> None:
    policy, label = formation_llm.make_policy(provider="deepseek", api_key="")
    assert policy is None
    assert "no API key" in label
    policy, label = formation_llm.make_policy(provider="deepseek", api_key="k")
    assert policy is not None and label.startswith("llm:")


def test_a_side_without_a_policy_runs_doctrine_and_says_so() -> None:
    from iron_bottom_sound.formation_agents import DeterministicFormationAgent

    command_delay.clear_side_policies()
    agent, label = command_delay.side_agent(Side.AXIS)
    assert isinstance(agent, DeterministicFormationAgent)
    assert label == "deterministic-formation-v1"
    stub = formation_llm.ProviderPolicy(
        endpoint="https://example.invalid/v1", model="m", api_key="k",
        client=StubClient("{}"),
    )
    command_delay.set_side_policy(Side.AXIS, stub, stub.label)
    try:
        agent, label = command_delay.side_agent(Side.AXIS)
        assert isinstance(agent, formation_llm.FormationLLMAgent)
        assert label == stub.label
    finally:
        command_delay.clear_side_policies()


def test_an_agent_log_entry_exists_for_every_decision() -> None:
    engine, state = start()
    play(engine, state)
    mode = state.command_delay
    assert mode.agent_log, "the debug view needs a transcript"
    for record in mode.agent_log:
        for key in ("turn", "phase", "formation_id", "agent", "prompt",
                    "attempts", "decision", "memory"):
            assert key in record, key
        assert record["prompt"]["formation_id"] == record["formation_id"]
        assert record["memory"]["formation_id"] == record["formation_id"]
    assert mode.policy_labels, "each side's policy must be labelled"


def test_the_agent_log_endpoint_never_crosses_sides() -> None:
    """The transcript is per side: an opponent's prompt is its command chain.

    The engine keeps both sides' records so a replay can be audited; the *endpoint*
    is what must filter, so that is what is tested.
    """
    from fastapi.testclient import TestClient

    from iron_bottom_sound.api import app, engine as api_engine

    client = TestClient(app)
    created = client.post("/games", json={
        "scenario_id": "IBS-S-01", "seed": 20270830,
        "options": {"mode": "hotseat", "realistic_command": True,
                    "command_delay_mode": True},
    })
    assert created.status_code == 201, created.text
    game_id = created.json()["game_id"]
    state = api_engine.get(game_id)
    play(api_engine, state)

    for side in Side:
        own = {
            formation.id for formation in state.formations.values()
            if formation.side is side
        }
        response = client.get(f"/games/{game_id}/command-delay/agent-log",
                              headers={"X-Player-Side": side.value})
        assert response.status_code == 200, response.text
        body = response.json()
        assert set(body["formations"]) == own
        assert set(body["memories"]) <= own
        for entry in body["entries"]:
            assert entry["formation_id"] in own
            assert entry["side"] == side.value
        # And the opponent's formations and memories are absent entirely.
        opponent = {
            formation.id for formation in state.formations.values()
            if formation.side is not side
        }
        text = json.dumps(body, ensure_ascii=False)
        for formation_id in opponent:
            # Only allowed if this side also has a formation with that exact id,
            # which cannot happen: ids are side-prefixed.
            assert formation_id not in text, f"{formation_id} reached {side.value}"


def test_the_order_endpoint_and_formation_orders_round_trip() -> None:
    from fastapi.testclient import TestClient

    from iron_bottom_sound.api import app, engine as api_engine

    client = TestClient(app)
    game_id = client.post("/games", json={
        "scenario_id": "IBS-S-01", "seed": 20270830,
        "options": {"mode": "hotseat", "realistic_command": True,
                    "command_delay_mode": True},
    }).json()["game_id"]
    state = api_engine.get(game_id)
    sessions = {side: LLMPlayerSession(side, RealisticCommander()) for side in Side}
    for side in Side:
        assert api_engine.submit_orders(game_id, OrderBatch(
            side=side, phase=Phase.FORMATION_SETUP,
            formation_setup=default_setup_orders(state, side),
        )).valid
    client.post(f"/games/{game_id}/advance", headers={"X-Player-Side": "axis"})
    steps = 0
    while not (state.phase == Phase.MOVEMENT_PLANNING and state.turn >= 2) and steps < 200:
        steps += 1
        if state.phase in ORDER_PHASES:
            for side in Side:
                if side.value in state.submitted_orders:
                    continue
                assert api_engine.submit_orders(
                    game_id, sessions[side].choose_orders(api_engine, game_id)
                ).valid
        client.post(f"/games/{game_id}/advance", headers={"X-Player-Side": "axis"})

    target = next(
        formation.id for formation in command_delay.active_formations(state, Side.ALLIES)
        if formation.id != command_delay.authority_for(state, Side.ALLIES).fleet_formation_id
    )
    sent = client.post(
        f"/games/{game_id}/command-delay/order",
        headers={"X-Player-Side": "allies"},
        json={"formation_id": target, "text": "向东拉开距离，保持接触",
              "priority_classes": ["DD"]},
    )
    assert sent.status_code == 200, sent.text
    body = sent.json()
    assert body["message_id"] and body["issued_turn"] == state.turn
    assert body["expected_delivery_turn"] >= body["issued_turn"]

    orders = client.get(f"/games/{game_id}/command-delay/formation-orders",
                        headers={"X-Player-Side": "axis"})
    assert orders.status_code == 200, orders.text
    for order in orders.json()["orders"]:
        assert order["leader_plan"]

    # Armies incompatible with the mode are refused.
    for path, method, body in (
        ("/command-delay/order", "post", {"formation_id": target, "text": "x"}),
        ("/command-delay/agent-log", "get", None),
        ("/command-delay/formation-orders", "get", None),
    ):
        realistic = client.post("/games", json={
            "scenario_id": "IBS-S-01", "seed": 3,
            "options": {"mode": "hotseat", "realistic_command": True},
        }).json()["game_id"]
        call = getattr(client, method)
        kwargs = {"headers": {"X-Player-Side": "axis"}}
        if body is not None:
            kwargs["json"] = body
        assert call(f"/games/{realistic}{path}", **kwargs).status_code == 409


def test_formation_orders_and_gunnery_priorities_never_cross_sides() -> None:
    """CD12-F2 regression: each side's batch must carry only its own material.

    The live battle caught both: movement batches containing the opponent's
    formations (engine refused, driver silently fell back to doctrine), and
    gunnery priorities from the other side's agents reaching this side's selector.
    """
    engine, state = start()
    play(engine, state)
    for side in Side:
        own = {
            formation.id for formation in state.formations.values()
            if formation.side is side
        }
        for order in command_delay.formation_orders(state, side):
            assert order.formation_id in own
        mode = state.command_delay
        for order in mode.mission_orders:
            if order.side is side and order.confirmed_turn is not None:
                for directive in order.target_priority_directives:
                    assert directive.formation_id in own
        for directive in mode.local_directives:
            assert directive.formation_id in own, (
                f"allies directive {directive.formation_id} reached the axis selector"
                if side is Side.AXIS else
                f"axis directive {directive.formation_id} reached the allies selector"
            )
