from iron_bottom_sound.engine import IronBottomEngine
from iron_bottom_sound.models import GameOptions, Phase, Side
from iron_bottom_sound.realistic_command import RealisticCommander
from iron_bottom_sound.tutorials import ERMA_SPEED_CASUALTY, SPEED_CRISIS_FLAG, coach_suggested_orders


def _submit_both(engine: IronBottomEngine, game_id: str) -> None:
    commander = RealisticCommander()
    for side in Side:
        batch = commander.choose_orders(engine, game_id, side)
        result = engine.submit_orders(game_id, batch)
        assert result.valid, result.errors


def _reach_second_turn(engine: IronBottomEngine, game_id: str) -> None:
    assert engine.get(game_id).phase == Phase.FORMATION_SETUP
    _submit_both(engine, game_id)
    engine.advance(game_id)
    assert engine.get(game_id).phase == Phase.GUNNERY
    _submit_both(engine, game_id)
    engine.advance(game_id)
    engine.advance(game_id)
    engine.advance(game_id)


def test_erma_tutorial_stages_replayable_speed_crisis_only_after_first_fire_end() -> None:
    engine = IronBottomEngine()
    state = engine.reset(
        "IBS-S-EM-01",
        seed=71,
        options=GameOptions(
            mode="tutorial",
            realistic_command=True,
            tutorial_script="erma_grand_fleet",
        ),
    )
    before = state.ships[ERMA_SPEED_CASUALTY].max_speed_for_turn(2)
    assert SPEED_CRISIS_FLAG not in state.tutorial_flags

    _reach_second_turn(engine, state.game_id)

    current = engine.get(state.game_id)
    casualty = current.ships[ERMA_SPEED_CASUALTY]
    assert current.turn == 2
    assert current.phase == Phase.REINFORCEMENT
    assert SPEED_CRISIS_FLAG in current.tutorial_flags
    assert casualty.max_speed_for_turn(2) == 3 < before
    event = next(item for item in current.events if item.type == "tutorial_speed_crisis")
    assert event.rule and event.rule.rule_id == "IBS-TUT-EM-05"
    assert event.payload["teaching_choices"] == ["reduce", "detach"]

    replayed = engine.replay(current.events)
    assert replayed.ships[ERMA_SPEED_CASUALTY].speed_damage_crossed == casualty.speed_damage_crossed
    assert replayed.tutorial_flags == current.tutorial_flags


def test_formal_erma_game_never_receives_tutorial_script_damage() -> None:
    engine = IronBottomEngine()
    state = engine.reset(
        "IBS-S-EM-01",
        seed=71,
        options=GameOptions(realistic_command=True),
    )
    _reach_second_turn(engine, state.game_id)
    current = engine.get(state.game_id)
    assert SPEED_CRISIS_FLAG not in current.tutorial_flags
    assert not any(item.type == "tutorial_speed_crisis" for item in current.events)


def test_erma_tutorial_opens_with_a_real_visible_grand_fleet_salvo() -> None:
    engine = IronBottomEngine()
    state = engine.reset(
        "IBS-S-EM-01",
        seed=70,
        options=GameOptions(mode="tutorial", realistic_command=True, tutorial_script="erma_grand_fleet"),
    )
    _submit_both(engine, state.game_id)
    engine.advance(state.game_id)
    batch = RealisticCommander().choose_orders(engine, state.game_id, Side.AXIS)
    assert batch.gunnery
    assert any(order.mounts for order in batch.gunnery)
    assert engine.validate_orders(state.game_id, batch).valid
    assert any(item.type == "tutorial_deployment_staged" for item in engine.get(state.game_id).events)


def test_erma_tutorial_coach_exposes_an_explicit_editable_reduce_choice() -> None:
    engine = IronBottomEngine()
    state = engine.reset(
        "IBS-S-EM-01",
        seed=72,
        options=GameOptions(mode="tutorial", realistic_command=True, tutorial_script="erma_grand_fleet"),
    )
    _reach_second_turn(engine, state.game_id)
    _submit_both(engine, state.game_id)
    engine.advance(state.game_id)
    draft = RealisticCommander().choose_orders(engine, state.game_id, Side.AXIS)
    coached = coach_suggested_orders(engine.get(state.game_id), draft)
    casualty = engine.get(state.game_id).ships[ERMA_SPEED_CASUALTY]
    order = next(item for item in coached.formation_movement if item.formation_id == casualty.formation_id)
    assert order.leader_plan == "5"
    assert order.speed_decision and order.speed_decision.action == "reduce"
    assert order.speed_decision.speed == 3
    assert engine.validate_orders(state.game_id, coached).valid


def test_erma_tutorial_script_rejects_wrong_scenario_or_non_tutorial_mode() -> None:
    engine = IronBottomEngine()
    for scenario, options in (
        ("IBS-S-03", GameOptions(mode="tutorial", realistic_command=True, tutorial_script="erma_grand_fleet")),
        ("IBS-S-EM-01", GameOptions(mode="hotseat", realistic_command=True, tutorial_script="erma_grand_fleet")),
        ("IBS-S-EM-01", GameOptions(mode="tutorial", realistic_command=False, tutorial_script="erma_grand_fleet")),
    ):
        try:
            engine.reset(scenario, options=options)
        except ValueError:
            pass
        else:
            raise AssertionError("invalid tutorial option combination was accepted")
