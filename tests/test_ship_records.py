from pathlib import Path

import yaml

from iron_bottom_sound.engine import IronBottomEngine
from iron_bottom_sound.counter_assets import all_asset_bindings, validate_asset_bindings
from iron_bottom_sound.models import FiringArc
from iron_bottom_sound.ship_records import load_ship_catalog, load_ship_records


ROOT = Path(__file__).resolve().parents[1]
STRUCTURED = ROOT / "resources" / "derived" / "structured"


def test_all_playable_and_reinforcement_ships_have_verified_records() -> None:
    records = load_ship_records()
    required: set[str] = set()
    for number in (1, 3):
        scenario = yaml.safe_load((STRUCTURED / "scenarios" / f"scenario-{number:02d}.yaml").read_text(encoding="utf-8"))
        required.update(ship["id"] for ship in scenario["ships"])
        required.update(ship["id"] for ship in scenario.get("reinforcements", {}).get("ships", []))
    assert len(records) == 180
    assert required <= set(records)
    assert all(1 <= record.source_page <= 24 for record in records.values())


def test_complete_ship_list_catalog_is_migrated_without_promoting_unverified_stats() -> None:
    catalog = load_ship_catalog()
    assert len(catalog) == 204
    assert len(catalog) == len(set(catalog))
    assert {entry["ship_type"] for entry in catalog.values()} >= {"BB", "BC", "CA", "CL", "DD", "APD", "AV"}
    assert sum(1 for entry in catalog.values() if entry.get("unresolved")) == 4


def test_every_complete_record_has_a_verified_counter_asset_binding() -> None:
    records = load_ship_records()
    bindings = all_asset_bindings(records)
    assert len(bindings) == len(records) == 180
    assert not validate_asset_bindings(records)


def test_ship_record_mounts_and_tracks_match_source_examples() -> None:
    records = load_ship_records()
    aoba = records["IBS-U-IJN-AOBA"]
    helena = records["IBS-U-USN-HELENA"]
    akizuki = records["IBS-U-IJN-AKIZUKI"]
    karl = records["IBS-U-KM-KARL-GALSTER"]
    javelin = records["IBS-U-RN-JAVELIN"]
    assert aoba.hull_boxes == 11
    assert aoba.maximum_speed_cycle == (6, 5, 5)
    assert sum(mount.firepower for mount in aoba.guns if mount.kind == "primary") == 16
    assert aoba.torpedo_type == "jp-24-type93"
    assert [launcher.torpedoes for launcher in aoba.torpedo_launchers] == [2, 2]
    assert sum(launcher.reloads for launcher in aoba.torpedo_launchers) == 2
    assert helena.hull_boxes == 14
    assert helena.radar
    assert sum(mount.firepower for mount in helena.guns if mount.kind == "primary") == 32
    assert helena.armour.secondary == 1
    assert akizuki.hull_boxes == 7 and akizuki.maximum_speed_cycle == (6, 5, 5)
    assert [launcher.torpedoes for launcher in akizuki.torpedo_launchers] == [2]
    assert karl.hull_boxes == 6 and karl.maximum_speed_cycle == (6, 6, 6)
    assert [launcher.torpedoes for launcher in karl.torpedo_launchers] == [2, 2]
    assert javelin.hull_boxes == 5 and javelin.maximum_speed_cycle == (6, 6, 5)
    assert [launcher.torpedoes for launcher in javelin.torpedo_launchers] == [2, 2]
    assert [launcher.torpedoes for launcher in records["IBS-U-USN-FARENHOLT"].torpedo_launchers] == [2, 1]
    assert [launcher.torpedoes for launcher in records["IBS-U-IJN-FUBUKI"].torpedo_launchers] == [2, 2]
    assert [launcher.torpedoes for launcher in records["IBS-U-IJN-ASAGUMO"].torpedo_launchers] == [3, 3]


def test_every_mount_and_launcher_has_a_legal_source_arc() -> None:
    for record in load_ship_records().values():
        ids = [mount.id for mount in record.guns] + [launcher.id for launcher in record.torpedo_launchers]
        assert len(ids) == len(set(ids))
        assert all(mount.arcs for mount in record.guns)
        assert all(set(launcher.arcs) <= {FiringArc.PORT, FiringArc.STARBOARD} for launcher in record.torpedo_launchers)


def test_torpedo_characteristics_table_matches_source_cells() -> None:
    data = yaml.safe_load((STRUCTURED / "rules" / "torpedoes.yaml").read_text(encoding="utf-8"))
    types = data["types"]
    assert len(types) == 10
    assert types["us-21-mk15-1942"]["settings"][-1] == {"speed": [5, 4, 4], "range": 25}
    assert types["jp-24-type90"]["settings"] == [
        {"speed": [8, 7, 7], "range": 12},
        {"speed": [7, 7, 7], "range": 18},
        {"speed": [6, 6, 6], "range": 27},
    ]
    assert types["jp-24-type93"]["damage_modifier"] == 1
    assert types["jp-21"]["damage_modifier"] == -1
    assert types["de-nl-21"]["settings"][1] == {"speed": [7, 7, 7], "range": 14}
    referenced = {record.torpedo_type for record in load_ship_records().values() if record.torpedo_type}
    assert referenced <= set(types)


def test_engine_initial_state_uses_individual_records_not_generic_templates() -> None:
    scenario_one = IronBottomEngine().reset("IBS-S-01", seed=11)
    assert scenario_one.ships["IBS-U-IJN-AOBA"].max_hull == 11
    assert scenario_one.ships["IBS-U-USN-SAN-FRANCISCO"].max_hull == 12
    assert scenario_one.ships["IBS-U-USN-BOISE"].max_hull == 13
    assert scenario_one.ships["IBS-U-USN-HELENA"].max_hull == 14
    assert scenario_one.ships["IBS-U-USN-HELENA"].primary.firepower == 32
    scenario_three = IronBottomEngine().reset("IBS-S-03", seed=11)
    assert scenario_three.ships["IBS-U-KM-KARL-GALSTER"].max_hull == 6
    assert scenario_three.ships["IBS-U-RN-JAVELIN"].max_hull == 5
