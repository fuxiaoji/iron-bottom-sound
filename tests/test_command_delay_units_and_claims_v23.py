"""IR-6: the engine owns units, and a claim's certainty comes from its source.

Two regressions from the v2.2 battle are reproduced here as tests, because both were
things the record *looked* fine about:

* a report said an enemy ship was 12-15 海里 away when the fact was 12-15 **hex**
  (about 3.5-4.4 nautical miles);
* a claim that an enemy heavy cruiser was "confirmed sunk" - with nothing in the
  formation's record to confirm it, because a model's inference had been written down as
  an operational fact.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend" / "src"))

from iron_bottom_sound import claims, command_delay  # noqa: E402
from iron_bottom_sound.communications.processing import range_units  # noqa: E402
from iron_bottom_sound.command_observation import formation_observation  # noqa: E402
from iron_bottom_sound.engine import ORDER_PHASES, IronBottomEngine  # noqa: E402
from iron_bottom_sound.formation_knowledge import KnowledgeItem  # noqa: E402
from iron_bottom_sound.llm import LLMPlayerSession  # noqa: E402
from iron_bottom_sound.models import (  # noqa: E402
    GameOptions, OrderBatch, Phase, Side,
)
from iron_bottom_sound.realistic_command import (  # noqa: E402
    RealisticCommander, default_setup_orders,
)

SCENARIO = "IBS-S-EM-01"
SEED = 19440619


def _game_to_movement(turn: int = 2):
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
    steps = 0
    while state.phase is not Phase.COMPLETE and steps < 200:
        steps += 1
        if state.turn >= turn and state.phase is Phase.MOVEMENT_PLANNING:
            return engine, state
        if state.phase in ORDER_PHASES:
            for side in Side:
                if side.value in state.submitted_orders:
                    continue
                if state.phase is Phase.MOVEMENT_PLANNING:
                    batch = OrderBatch(side=side, phase=state.phase,
                                       formation_movement=command_delay.formation_orders(state, side))
                elif state.phase is Phase.GUNNERY:
                    batch = command_delay.gunnery_batch(state, side)
                else:
                    batch = sessions[side].choose_orders(engine, state.game_id)
                result = engine.submit_orders(state.game_id, batch)
                if not result.valid and state.phase is Phase.MOVEMENT_PLANNING:
                    _, fallback, _ = RealisticCommander().choose_plan(engine, state.game_id, side)
                    result = engine.submit_orders(state.game_id, fallback)
                assert result.valid, result.errors[:2]
        engine.advance(state.game_id)
    raise AssertionError("never reached the movement phase")


# --------------------------------------------------------------------- units

def test_units_are_computed_by_the_engine_not_the_model() -> None:
    """Whatever contacts a formation has, each carries the engine's own unit conversion."""
    engine, state = _game_to_movement(turn=6)
    view = formation_observation(engine, state, Side.AXIS,
                                command_delay.active_formations(state, Side.AXIS)[0].id)
    for contact in view.local_contacts:
        assert {"range_hex", "range_yards", "range_nmi"} <= set(contact)
        if contact["range_hex"] is None:
            continue
        expected = range_units(contact["range_hex"])
        assert contact["range_nmi"] == expected["range_nmi"]
        assert contact["range_yards"] == contact["range_hex"] * 600


def test_the_old_twelve_hex_twelve_miles_error_is_caught() -> None:
    """The regression: 12-15 hex written as 12-15 海里 must be flagged, and the honest
    rendering of that range must not be."""
    bad = "发现敌巡洋舰两艘，距离 12 至 15 海里。"
    assert claims.miles_claimed_for_hexes(bad, distance_hex=12)
    assert claims.miles_claimed_for_hexes(bad, distance_hex=15)
    honest = f"发现敌巡洋舰两艘，{claims.range_prose(12)}。"
    assert "3.55 海里" in honest and "12 格" in honest
    assert not claims.miles_claimed_for_hexes(honest, distance_hex=12)
    # and a distance where the two genuinely agree is not a false positive
    assert not claims.miles_claimed_for_hexes("距离 1 海里", distance_hex=1)


# --------------------------------------------------------------------- provenance

def test_an_ungrounded_confirmed_sunk_claim_is_caught() -> None:
    """The 'Iowa confirmed sunk' regression: with no supporting record, a confirmed claim
    is ungrounded - and the check says so instead of letting it into the report."""
    knowledge = [
        KnowledgeItem(subject_id="IBS-U-USN-ERMA-IOWA", field="POSITION", value="V14",
                      observed_turn=3, received_turn=3, source_kind="LOCAL_OBSERVATION",
                      source_id="axis-battle-line", confidence="CONFIRMED"),
    ]
    subjects = {"IBS-U-USN-ERMA-IOWA"}
    ungrounded = "衣阿华已被确认击沉。"
    findings = claims.unsupported_confirmed(ungrounded, subject_ids=subjects,
                                            knowledge=knowledge)
    assert findings, "a confirmed sinking with no SUNK fact in the ledger must be rejected"
    assert findings[0].certainty == "SUSPECTED"
    assert not findings[0].is_supported

    # the same sentence is fine when the formation watched it sink
    witnessed = knowledge + [
        KnowledgeItem(subject_id="IBS-U-USN-ERMA-IOWA", field="SUNK", value=True,
                      observed_turn=4, received_turn=4, source_kind="LOCAL_OBSERVATION",
                      source_id="axis-battle-line", confidence="CONFIRMED"),
    ]
    assert not claims.unsupported_confirmed(ungrounded, subject_ids=subjects,
                                            knowledge=witnessed)
    # ... or when a delivered report carried it (that is a REPORTED claim, not CONFIRMED)
    reported = knowledge + [
        KnowledgeItem(subject_id="IBS-U-USN-ERMA-IOWA", field="SUNK", value=True,
                      observed_turn=4, received_turn=5, source_kind="DELIVERED_MESSAGE",
                      source_id="axis-destroyer-line", message_id="MSG-00042",
                      confidence="REPORTED"),
    ]
    graded = claims.grade(ungrounded, subject_ids=subjects, knowledge=reported)
    assert graded and graded[0].certainty == "REPORTED", (
        "a delivered report supports the fact, but it is a REPORTED claim: the word "
        "'confirmed' in the sentence cannot raise it"
    )
    assert graded[0].message_id == "MSG-00042"
    # so it is not an *ungrounded* claim - the plan's branch A - while the unaided
    # sentence over the same ledger would have been branch B
    assert not claims.unsupported_confirmed(ungrounded, subject_ids=subjects,
                                            knowledge=reported)
    assert claims.unsupported_confirmed(ungrounded, subject_ids=subjects, knowledge=[])


def test_certainty_is_graded_by_source_not_by_wording() -> None:
    """A confident sentence over an empty ledger is SUSPECTED; a hedged sentence over a
    witnessed fact is CONFIRMED.  The wording never decides."""
    subjects = {"IBS-U-USN-ERMA-IOWA"}
    loud = claims.grade("确认击沉衣阿华！", subject_ids=subjects, knowledge=[])
    assert loud and loud[0].certainty == "SUSPECTED"

    witnessed = [
        KnowledgeItem(subject_id="IBS-U-USN-ERMA-IOWA", field="SUNK", value=True,
                      observed_turn=4, received_turn=4, source_kind="LOCAL_OBSERVATION",
                      source_id="f", confidence="CONFIRMED"),
    ]
    hedged = claims.grade("衣阿华可能已经沉没。", subject_ids=subjects, knowledge=witnessed)
    assert hedged and hedged[0].certainty == "CONFIRMED"
