import csv
from pathlib import Path

import yaml

from iron_bottom_sound.engine import IronBottomEngine


ROOT = Path(__file__).resolve().parents[1]
RULES = ROOT / "resources" / "derived" / "structured" / "rules"


def load_yaml(name: str):
    return yaml.safe_load((RULES / name).read_text(encoding="utf-8"))


def test_armour_penetration_table_has_all_source_rows_and_ranges() -> None:
    with (RULES / "armour-penetration-table.csv").open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    ranges = ["1-2", "3-5", "6-7", "8-10", "11-13", "14-17", "18-20", "21-25"]
    assert len(rows) == 27
    assert all(all(row[distance] for distance in ranges) for row in rows)
    by_id = {row["gun_id"]: row for row in rows}
    assert [by_id["us-16-45"][distance] for distance in ranges] == [str(value) for value in range(25, 17, -1)]
    assert by_id["jp-18.1"]["1-2"] == "26"
    assert by_id["jp-18.1"]["21-25"] == "19"
    assert by_id["de-3.5-us-jp-3"]["18-20"] == "-"


def test_fire_and_malfunction_tables_cover_every_2d6_result() -> None:
    fire = load_yaml("fire-table.yaml")["results"]
    malfunction = load_yaml("malfunction-table.yaml")["results"]
    assert set(fire) == {2, 3, 4, "5-6", 7, "8-9", 10, 11, 12}
    assert set(malfunction) == {2, 3, 4, 5, "6-8", 9, 10, 11, 12}
    assert fire[11] == {"hull": 1, "secondary": 1, "speed_loss": 1}
    assert malfunction[12] == {"destroy_random_primary": 1, "special_damage": True}


def test_gunnery_result_table_has_complete_d66_domain() -> None:
    results = load_yaml("gunnery-results.yaml")["results"]
    assert len(results) == 36
    assert results[25]["hull_by_ship_type"] == {"BB_BC": 3, "AV_CA_CL": 2, "other": 1}
    assert results[33]["fire_check_for_jp_de_4.7_or_5"] is True
    assert results["66+"] == "miss"


def test_modifier_tables_preserve_source_exceptions() -> None:
    modifiers = load_yaml("modifiers.yaml")
    torpedo_ranges = modifiers["range_modifier"]["torpedo"]
    assert torpedo_ranges[-2] == {"min": 11, "max": 15, "value": 0, "non_japanese_additional": -1}
    assert modifiers["gunnery_caliber_target_modifier"]["rows"]["3-5.1"] == [18, 6, 6, 0]
    assert modifiers["torpedo_hit"]["broadside"]["13+"] == 2
    assert modifiers["collision_modifier"]["rows"]["DD_APD"] == [-4, -3, -2, -1]
    assert modifiers["optional"]["through_smoke"] == 6


def test_special_damage_direct_and_displacement_domains_are_complete() -> None:
    table = load_yaml("special-damage-table.yaml")
    assert set(table["direct_results"]) == {"11", "12", "13", "14", "15", "16", "21", "22", "23", "24", "25", "26", "31", "32", "33-36", "41", "42", "43", "66"}
    assert table["direct_results"]["43"]["sunk"] is True
    assert table["direct_results"]["16"]["torpedo_launcher_hit"] == 1
    assert len(table["results"]) == 14


def test_rule_data_uses_national_range_and_penetration_exceptions() -> None:
    rules = IronBottomEngine().rules
    assert rules.range_modifier("torpedo", 11, japanese=True) == 0
    assert rules.range_modifier("torpedo", 11, japanese=False) == -1
    assert rules.target_speed_modifier("gunnery", 1) == -9
    assert rules.target_speed_modifier("torpedo", 0) == 4
    assert rules.penetration("US", 8, 2) == 13
    assert rules.penetration("UK", 4.7, 21) == 3
    assert rules.penetration("DE", 5, 2) == 0
    assert rules.gunnery_result(66) == "miss"


def test_special_damage_lookup_uses_displacement_band() -> None:
    rules = IronBottomEngine().rules
    assert rules.special_damage_result(44, "A")["effect"] == "1H/-2MF"
    assert rules.special_damage_result(44, "I")["effect"] == "2H/-1MF"
    assert rules.special_damage_result(54, "G")["additional"] == "primary_1_secondary_1"
    assert rules.special_damage_result(43, "A")["sunk"] is True
