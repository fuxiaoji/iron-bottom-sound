from pathlib import Path

from iron_bottom_sound.data import load_scenario, scenario_catalog
from iron_bottom_sound.engine import IronBottomEngine
from iron_bottom_sound.match import run_match
from iron_bottom_sound.models import Side
from iron_bottom_sound.scenario_rules import scenario_rules
from iron_bottom_sound.ship_records import load_ship_records
from iron_bottom_sound.tactical import TacticalCommander


ROOT = Path(__file__).resolve().parents[1]


def test_erma_catalog_definition_and_counter_assets_are_complete() -> None:
    assert any(item["id"] == "IBS-S-EM-01" and item["status"] == "playable" for item in scenario_catalog())
    scenario = load_scenario("IBS-S-EM-01")
    assert scenario["turns"] == 8
    assert scenario["visibility"] == {"axis": 15, "allies": 13}
    assert scenario["setup"]["zones"]["axis"] == {
        "from": "A14", "to": "Q1", "side": "northwest", "include_line": False,
    }
    assert len(scenario["ships"]) == 24
    assert all((ROOT / "resources" / "originals" / "assets" / "images" / ship["asset"]).is_file() for ship in scenario["ships"])


def test_erma_ship_records_preserve_large_hulls_tertiary_guns_and_torpedo_salvos() -> None:
    records = load_ship_records()
    erma = {key: value for key, value in records.items() if "-ERMA-" in key}
    assert len(erma) == 24
    yamato = erma["IBS-U-IJN-ERMA-YAMATO"]
    assert yamato.hull_rows == (9, 9, 9)
    assert yamato.hull_boxes == 27
    assert sum(mount.firepower for mount in yamato.guns if mount.kind == "tertiary") == 30
    assert [launcher.torpedoes for launcher in erma["IBS-U-IJN-ERMA-KURAMA"].torpedo_launchers] == [3, 1, 3, 3, 1]
    assert [launcher.reloads for launcher in erma["IBS-U-IJN-ERMA-KAZEGUMO"].torpedo_launchers] == [2, 2]
    assert [launcher.torpedoes for launcher in erma["IBS-U-USN-ERMA-COOPER"].torpedo_launchers] == [3, 3]


def test_erma_scenario_rule_table_penetration_and_damage_scoring() -> None:
    rules = scenario_rules("IBS-S-EM-01")
    assert rules.gunnery_hits(lambda _firepower, _roll: -1, 101, 11) == 8
    assert rules.gunnery_hits(lambda _firepower, _roll: -1, 120, 35) == 0
    assert rules.gunnery_hits(lambda _firepower, _roll: -1, 121, 35) == 1
    assert rules.penetration_caliber("IBS-U-IJN-ERMA-AZUMA", 3.9) == 3.0
    assert rules.penetration_caliber("IBS-U-USN-ERMA-IOWA", 3.9) == 3.9

    engine = IronBottomEngine()
    state = engine.reset("IBS-S-EM-01", seed=7)
    iowa = state.ships["IBS-U-USN-ERMA-IOWA"]
    state.hull_damage_taken[Side.ALLIES.value] = 3
    iowa.mfc_destroyed = True
    iowa.radar_destroyed = True
    next(mount for mount in iowa.gun_mounts if mount.kind == "primary").destroyed = True
    iowa.speed_damage_crossed = (1, 1, 0)
    rules.refresh_score(state)
    assert state.score[Side.AXIS.value] == 5


def test_existing_state_machine_ai_produces_valid_erma_orders() -> None:
    engine = IronBottomEngine()
    state = engine.reset("IBS-S-EM-01", seed=9)
    commander = TacticalCommander()
    for side in Side:
        _plan, batch, _audits = commander.choose_plan(engine, state.game_id, side)
        result = engine.submit_orders(state.game_id, batch)
        assert result.valid, result.errors


def test_erma_state_machine_ai_match_completes_without_fallback() -> None:
    report, engine, _sessions = run_match(
        "IBS-S-EM-01", axis="tactical", allies="tactical", seed=23, request_limit=128
    )
    assert report.passed, report.failure_reason
    assert report.completed
    assert report.request_count == 58
    assert report.fallback_count == 0
    final_state = engine.get(report.game_id)
    assert final_state.score == {"axis": 42, "allies": 13}
    assert engine.replay(report.game_id).model_dump(mode="json") == final_state.model_dump(mode="json")
