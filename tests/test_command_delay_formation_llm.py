"""CD-5: the LLM local-agent adapter — action ids only, no gunnery, audited.

The model is a *policy callable*, injected.  Nothing in this repository calls a
paid provider for these tests: the fixtures are stub callables and recorded
responses, which is also what makes an LLM game replayable at zero cost.

The adversarial tests here are the ones that matter: an invented action id, an
out-of-bounds weight, an unknown report action, a gunnery field, and a
non-JSON response are each rejected, retried, and finally converted into the
deterministic doctrine with every attempt recorded.
"""
from __future__ import annotations

import json

import pytest

from iron_bottom_sound import command_delay, formation_llm
from iron_bottom_sound.command_observation import (
    LOCAL_PRIORITY_WEIGHT_LIMIT,
    formation_observation,
)
from iron_bottom_sound.engine import ORDER_PHASES, IronBottomEngine
from iron_bottom_sound.models import GameOptions, OrderBatch, Phase, Side
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


def observation_at(scenario: str = "IBS-S-01", seed: int = 20270830):
    engine, state = start(scenario, seed)
    for _ in range(12):
        if state.phase == Phase.MOVEMENT_PLANNING:
            break
        if state.phase == Phase.COMPLETE:
            break
        if state.phase in ORDER_PHASES:
            from iron_bottom_sound.llm import LLMPlayerSession

            for side in Side:
                if side.value in state.submitted_orders:
                    continue
                assert engine.submit_orders(
                    state.game_id,
                    LLMPlayerSession(side, RealisticCommander()).choose_orders(
                        engine, state.game_id
                    ),
                ).valid
        engine.advance(state.game_id)
    formation = command_delay.active_formations(state, Side.AXIS)[0]
    return engine, state, formation_observation(engine, state, Side.AXIS, formation.id)


# --------------------------------------------------------------------------- prompt

def test_prompt_carries_exactly_the_local_input_list() -> None:
    engine, state, observation = observation_at()
    prompt = formation_llm.build_prompt(observation, None)
    for key in ("formation_state", "local_map", "local_contacts",
                "active_mission_order", "received_messages", "comm_state",
                "stale_external_reports", "legal_formation_actions",
                "legal_target_priority_options", "report_actions"):
        assert key in prompt, key
    for forbidden in ("score", "sealed_orders", "submitted_orders", "wrecks",
                      "torpedo_tracks", "winner", "all_ships", "side_plot"):
        assert forbidden not in prompt
    assert prompt["formation_id"] == observation.formation_id
    assert prompt["turn"] == observation.turn


def test_prompt_does_not_leak_a_rule_formula() -> None:
    engine, state, observation = observation_at()
    text = json.dumps(formation_llm.build_prompt(observation, None), ensure_ascii=False)
    for formula in ("expected_hits", "D66", "modifier", "firepower", "caliber",
                    "gunnery_assist", "hit_table"):
        assert formula not in text, f"{formula} must not be shown to the model"


# --------------------------------------------------------------------------- parsing

def decision_payload(**overrides) -> str:
    payload = {
        "selected_movement_action_id": None,
        "selected_contingency_branch": None,
        "target_priority_adjustments": [],
        "report_actions": ["SITREP"],
        "acknowledgement": False,
        "rationale_summary": "stub",
    }
    payload.update(overrides)
    return json.dumps(payload)


def test_a_valid_response_parses_into_a_bounded_decision() -> None:
    engine, state, observation = observation_at()
    legal = observation.legal_formation_actions
    action_id = legal[0]["action_id"] if legal else None
    raw = decision_payload(
        selected_movement_action_id=action_id,
        target_priority_adjustments=[
            {"target_id": None, "target_class": "DD", "weight": 0.25, "reason": "stub"}
        ],
    )
    decision, errors = formation_llm.parse_response(raw, observation)
    assert errors == [] and decision is not None
    if action_id is not None:
        assert decision.selected_movement_action_id == action_id
        assert decision.selected_movement_plan == legal[0]["plan"]


def test_an_invented_action_id_is_rejected() -> None:
    engine, state, observation = observation_at()
    decision, errors = formation_llm.parse_response(
        decision_payload(selected_movement_action_id="MOVE:9S9S9P"), observation
    )
    assert decision is None
    assert any("not in the legal action list" in error for error in errors)


def test_a_raw_movement_plan_is_rejected_outright() -> None:
    engine, state, observation = observation_at()
    decision, errors = formation_llm.parse_response(
        decision_payload(movement_plan="3S2S"), observation
    )
    assert decision is None
    assert any("may not decide" in error for error in errors)


def test_gunnery_fields_are_rejected() -> None:
    engine, state, observation = observation_at()
    for field in ("gunnery", "mounts", "mount_ids", "firing_solution",
                  "hit_modifier", "expected_hits"):
        decision, errors = formation_llm.parse_response(
            decision_payload(**{field: []}), observation
        )
        assert decision is None, field
        assert any("may not decide" in error for error in errors), field


def test_an_out_of_bounds_weight_is_rejected() -> None:
    engine, state, observation = observation_at()
    decision, errors = formation_llm.parse_response(
        decision_payload(target_priority_adjustments=[
            {"target_id": None, "weight": 5.0, "reason": "too strong"}
        ]), observation,
    )
    assert decision is None
    assert any("exceeds the local limit" in error for error in errors)
    assert LOCAL_PRIORITY_WEIGHT_LIMIT < 5.0


def test_a_target_the_formation_cannot_see_is_rejected() -> None:
    engine, state, observation = observation_at()
    decision, errors = formation_llm.parse_response(
        decision_payload(target_priority_adjustments=[
            {"target_id": "IBS-U-INVISIBLE", "weight": 0.1}
        ]), observation,
    )
    assert decision is None
    assert any("not a locally visible contact" in error for error in errors)


def test_an_unknown_report_action_is_rejected() -> None:
    engine, state, observation = observation_at()
    decision, errors = formation_llm.parse_response(
        decision_payload(report_actions=["NUKE_THEM"]), observation
    )
    assert decision is None
    assert any("unknown report actions" in error for error in errors)


def test_a_non_json_response_is_rejected() -> None:
    engine, state, observation = observation_at()
    decision, errors = formation_llm.parse_response("I will turn to port", observation)
    assert decision is None
    assert any("not valid JSON" in error for error in errors)


# --------------------------------------------------------------------------- retry / fallback / audit

def test_a_bad_response_triggers_a_retry_then_succeeds() -> None:
    engine, state, observation = observation_at()
    calls: list[dict] = []

    def policy(prompt):
        calls.append(prompt)
        if len(calls) == 1:
            return decision_payload(selected_movement_action_id="MOVE:invented")
        return decision_payload(report_actions=["SITREP"])

    agent = formation_llm.FormationLLMAgent(policy, max_retries=2)
    decision = agent.act(observation)
    assert len(calls) == 2
    assert decision.audit.get("parsed") is True
    assert [attempt.accepted for attempt in agent.attempts] == [False, True]
    assert agent.attempts[0].errors
    # The retry prompt says what was wrong, so the model can correct it.
    assert "previous_response_rejected" in calls[1]
    assert "被拒绝" in calls[1]["instruction"]


def test_a_persistently_bad_response_falls_back_to_doctrine_with_the_audit_kept() -> None:
    engine, state, observation = observation_at()
    calls: list[dict] = []

    def policy(prompt):
        calls.append(prompt)
        return decision_payload(gunnery=[{"mount_id": "A"}])

    agent = formation_llm.FormationLLMAgent(policy, max_retries=1)
    decision = agent.act(observation)
    assert len(calls) == 2, "one initial call plus one retry"
    assert decision.audit["llm_fallback"] is True
    assert decision.audit["llm_attempts"] == 2
    assert decision.audit["llm_errors"]
    assert agent.attempts[-1].fallback is True
    assert all(not attempt.accepted for attempt in agent.attempts)
    # The fallback is the doctrine decision, so the game still proceeds legally.
    assert target_is_legal(decision, observation)


def target_is_legal(decision, observation) -> bool:
    if decision.selected_movement_action_id is None:
        return True
    allowed = {action["action_id"] for action in observation.legal_formation_actions}
    return decision.selected_movement_action_id in allowed


def test_every_attempt_is_recorded_with_its_raw_response() -> None:
    engine, state, observation = observation_at()

    def policy(prompt):
        return decision_payload(selected_movement_action_id="MOVE:nope")

    agent = formation_llm.FormationLLMAgent(policy, max_retries=0)
    agent.act(observation)
    assert len(agent.attempts) == 1
    record = agent.attempts[0]
    assert record.raw_response.startswith("{")
    assert record.errors and record.accepted is False
    assert record.turn == observation.turn and record.formation_id == observation.formation_id
    assert record.prompt["formation_id"] == observation.formation_id


# --------------------------------------------------------------------------- replay

def test_a_recorded_llm_game_replays_without_calling_the_model() -> None:
    """A captured response is enough to reproduce an LLM decision exactly."""
    engine, state, observation = observation_at()
    legal = observation.legal_formation_actions
    payload = decision_payload(
        selected_movement_action_id=legal[0]["action_id"] if legal else None,
        target_priority_adjustments=[{"target_id": None, "target_class": "DD",
                                      "weight": 0.2, "reason": "recorded"}],
    )
    records = {(observation.formation_id, observation.turn): payload}
    agent = formation_llm.FormationLLMAgent(
        formation_llm.RecordedPolicy(records), max_retries=0
    )
    first = agent.act(observation)
    second = agent.act(observation)
    assert first.model_dump() == second.model_dump()
    assert first.target_priority_adjustments[0].weight == 0.2


def test_the_recorder_keys_on_identity_and_surfaces_a_missing_response() -> None:
    engine, state, observation = observation_at()
    policy = formation_llm.RecordedPolicy({})
    with pytest.raises(KeyError):
        policy({"formation_id": observation.formation_id, "turn": observation.turn})
    records: dict[tuple[str, int], str] = {}
    decision, _errors = formation_llm.parse_response(decision_payload(), observation)
    formation_llm.record_response(records, decision, decision_payload())
    assert records[(decision.formation_id, decision.turn)] == decision_payload()


def test_the_llm_agent_satisfies_the_same_protocol_as_the_deterministic_one() -> None:
    from iron_bottom_sound.formation_agents import (
        DeterministicFormationAgent,
        FormationPolicy,
    )

    stub = formation_llm.FormationLLMAgent(lambda prompt: decision_payload(), max_retries=0)
    assert isinstance(stub, FormationPolicy)
    assert isinstance(DeterministicFormationAgent(), FormationPolicy)
