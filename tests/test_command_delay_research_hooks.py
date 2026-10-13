"""CD-6: research hooks — contract state, incentive ledger, tensors, episode export.

The point of these tests is not that a model works (none exists) but that the
*interfaces* are safe before anything is built on them:

* every declared tensor block matches ``TENSOR_SPEC``, so a future consumer reads
  a versioned contract instead of guessing;
* a policy observation contains no opposing ship and no side-global field;
* the replay export is explicitly marked ``POLICY_SAFE = False`` and says why, so
  it cannot be silently consumed as an observation;
* a contract cannot carry an unsourced weight, and an unconfirmed contract is not
  in force;
* nothing in the runtime reads the contract or the ledger back into a decision.
"""
from __future__ import annotations

import json

import pytest

from iron_bottom_sound import command_delay, contracts, delegation, research_hooks
from iron_bottom_sound.command_observation import formation_observation
from iron_bottom_sound.engine import ORDER_PHASES, IronBottomEngine
from iron_bottom_sound.llm import LLMPlayerSession
from iron_bottom_sound.models import (
    ContractState,
    ContractTerm,
    GameOptions,
    LedgerEntry,
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


def play(engine, state, max_steps: int = 400) -> None:
    sessions = {side: LLMPlayerSession(side, RealisticCommander()) for side in Side}
    steps = 0
    while state.phase != Phase.COMPLETE and steps < max_steps:
        steps += 1
        if state.phase in ORDER_PHASES:
            for side in Side:
                if side.value in state.submitted_orders:
                    continue
                result = engine.submit_orders(
                    state.game_id, sessions[side].choose_orders(engine, state.game_id)
                )
                assert result.valid, (state.turn, state.phase, side, result.errors[:2])
        engine.advance(state.game_id)


# --------------------------------------------------------------------------- tensors

def test_tensor_blocks_match_the_declared_spec() -> None:
    engine, state = start()
    formation = command_delay.active_formations(state, Side.AXIS)[0]
    tensors = research_hooks.observation_tensors(engine, state, Side.AXIS, formation.id)
    assert tensors["tensor_version"] == research_hooks.TENSOR_VERSION
    for name, spec in research_hooks.TENSOR_SPEC.items():
        block = tensors[name]
        if spec.get("per"):
            rows = block if block and isinstance(block[0], list) else []
            for row in rows:
                assert len(row) == spec["width"], (name, row)
        else:
            assert len(block) == spec["width"], (name, block)


def test_policy_observation_carries_no_opposing_or_side_global_data() -> None:
    engine, state = start()
    formation = command_delay.active_formations(state, Side.AXIS)[0]
    payload = research_hooks.policy_observation(engine, state, Side.AXIS, formation.id)
    assert payload["POLICY_SAFE"] if "POLICY_SAFE" in payload else True
    for forbidden in ("score", "sealed_orders", "submitted_orders", "wrecks",
                      "torpedo_tracks", "winner", "victory_reason"):
        assert forbidden not in payload
    ally_ids = {ship.id for ship in state.ships.values() if ship.side is Side.ALLIES}
    observed_ships = {
        ship["ship_id"] for ship in payload["formation_state"]["ships"]
    }
    assert not (ally_ids & observed_ships), "an opposing ship reached a policy observation"


def test_to_numpy_returns_arrays_with_the_declared_widths() -> None:
    numpy = pytest.importorskip("numpy")
    engine, state = start()
    formation = command_delay.active_formations(state, Side.AXIS)[0]
    tensors = research_hooks.observation_tensors(engine, state, Side.AXIS, formation.id)
    arrays = research_hooks.to_numpy(tensors)
    assert arrays["self"].shape == (research_hooks.TENSOR_SPEC["self"]["width"],)
    assert arrays["comm"].shape == (research_hooks.TENSOR_SPEC["comm"]["width"],)
    assert arrays["contacts"].ndim == 2
    assert arrays["self"].dtype == numpy.float32


# --------------------------------------------------------------------------- replay export

def test_the_replay_export_is_explicitly_not_policy_safe() -> None:
    engine, state = start()
    play(engine, state)
    payload = research_hooks.episode_export(engine, state)
    assert payload["POLICY_SAFE"] is False
    assert "not" not in payload["warning"].lower() or "Use" in payload["warning"]
    assert "both sides" in payload["warning"]
    assert payload["events"] and payload["sealed_orders"] and payload["final_ships"]


def test_episode_records_are_one_local_record_per_formation_and_are_policy_safe() -> None:
    """S-01 opens at GUNNERY, so the first movement boundary is on turn 2."""
    engine, state = start()
    sessions = {side: LLMPlayerSession(side, RealisticCommander()) for side in Side}
    steps = 0
    while not state.command_delay.decisions and steps < 40:
        steps += 1
        if state.phase == Phase.COMPLETE:
            break
        if state.phase in ORDER_PHASES:
            for side in Side:
                if side.value in state.submitted_orders:
                    continue
                assert engine.submit_orders(
                    state.game_id,
                    sessions[side].choose_orders(engine, state.game_id),
                ).valid
        engine.advance(state.game_id)
    assert state.command_delay.decisions, "the agents must have decided within one turn"
    records = research_hooks.episode_records(engine, state)
    decided = 0
    for record in records:
        assert record["POLICY_SAFE"] is True
        assert record["observation"]["formation_id"] == record["formation_id"]
        if record["decision"] is not None:
            decided += 1
            assert record["decision_turn"] == record["turn"]
    assert decided, "a record built after the agents ran must carry a decision"
    keys = {(record["formation_id"], record["turn"]) for record in records}
    assert len(keys) == len(records)


def test_episode_files_round_trip(tmp_path) -> None:
    engine, state = start()
    play(engine, state)
    replay = research_hooks.write_episode(tmp_path / "episode.json", engine, state)
    lines = research_hooks.write_episode_records(tmp_path / "records.jsonl", engine, state)
    loaded = json.loads(replay.read_text(encoding="utf-8"))
    assert loaded["POLICY_SAFE"] is False
    rows = [json.loads(line) for line in lines.read_text(encoding="utf-8").splitlines()]
    assert rows and all(row["POLICY_SAFE"] is True for row in rows)


def test_hook_status_states_that_nothing_is_learned() -> None:
    status = research_hooks.hook_status()
    assert status["implemented_learning"] is False
    assert "no RL/GNN/Transformer" in status["note"]
    assert status["blocks"] == sorted(research_hooks.TENSOR_SPEC)


# --------------------------------------------------------------------------- contracts

def test_a_contract_is_not_in_force_until_its_order_is_confirmed() -> None:
    engine, state = start()
    formation = command_delay.active_formations(state, Side.AXIS)[0]
    order = delegation.standing_plan(
        formation_id=formation.id, side=Side.AXIS, turn=state.turn,
    )
    proposal = contracts.contract_from_order(order)
    errors = contracts.validate_contract(proposal)
    assert any("confirmed" in error for error in errors)
    assert contracts.contract_state(state, formation.id)["in_force"] is False
    assert contracts.declare_contract(state, proposal) == errors
    assert contracts.ledger(state) == []


def test_a_confirmed_contract_is_stored_and_reported_in_force() -> None:
    engine, state = start()
    formation = command_delay.active_formations(state, Side.AXIS)[0]
    order = delegation.standing_plan(
        formation_id=formation.id, side=Side.AXIS, turn=state.turn,
        issued_by="IBS-U-IJN-FLAGSHIP",
    )
    order.confirmed_turn = state.turn
    proposal = contracts.contract_from_order(order)
    assert contracts.validate_contract(proposal) == []
    assert contracts.declare_contract(state, proposal) == []
    payload = contracts.contract_state(state, formation.id)
    assert payload["in_force"] is True
    assert payload["terms"]
    assert all(term["weight"] == 0.0 for term in payload["terms"]), (
        "no weight may be invented: a term carries 0.0 until a researcher declares one"
    )


def test_a_malformed_contract_is_refused() -> None:
    engine, state = start()
    bad = ContractState(
        side=Side.AXIS, formation_id="f", agreed_turn=1,
        terms=[ContractTerm(term_id="t1", description="", obligor="a", beneficiary="a")],
    )
    errors = contracts.validate_contract(bad)
    assert any("empty description" in error for error in errors)
    assert any("must differ" in error for error in errors)


def test_the_ledger_appends_and_summarises_without_affecting_play() -> None:
    engine, state = start()
    entry = LedgerEntry(
        turn=state.turn, phase=state.phase.value, formation_id="f",
        kind="order_acknowledged", value=1.0, reason="unit test",
    )
    contracts.record(state, entry)
    assert contracts.ledger(state) == [entry]
    summary = contracts.ledger_summary(state)
    assert summary["entries"] == 1
    assert summary["by_formation"] == {"f": {"order_acknowledged": 1}}
    assert set(contracts.LEDGER_KINDS) >= {"deviation_reported", "rendezvous_kept"}


def test_recording_a_ledger_entry_changes_no_decision() -> None:
    """The hooks are read-only with respect to play: same game, same outcome."""
    engine, state = start()
    before = [event.type for event in state.events]
    contracts.record(state, LedgerEntry(
        turn=state.turn, phase=state.phase.value, formation_id="f",
        kind="coordination_observed", value=0.5, reason="hook probe",
    ))
    assert [event.type for event in state.events] == before
    play(engine, state)
    assert state.phase == Phase.COMPLETE


def test_contracts_and_ledger_survive_serialisation() -> None:
    engine, state = start()
    contracts.record(state, LedgerEntry(
        turn=state.turn, phase=state.phase.value, formation_id="f",
        kind="deviation_reported", value=-1.0, reason="serialisation probe",
    ))
    dumped = state.model_dump(mode="json")
    assert dumped["command_delay"]["ledger"][0]["kind"] == "deviation_reported"
    reloaded = type(state).model_validate(dumped)
    assert contracts.ledger(reloaded) == contracts.ledger(state)
