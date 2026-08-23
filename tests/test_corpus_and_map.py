from pathlib import Path

import yaml

from iron_bottom_sound.models import HexCoord, column_to_index, index_to_column


ROOT = Path(__file__).resolve().parents[1]


def test_map_has_34_source_labels() -> None:
    data = yaml.safe_load((ROOT / "resources/derived/structured/maps/main-map.yaml").read_text(encoding="utf-8"))
    labels = data["columns"]["labels"]
    assert data["columns"]["count"] == 34 == len(labels)
    assert labels[:2] == ["A", "B"]
    assert labels[-2:] == ["GG", "HH"]
    assert [index_to_column(index) for index in range(34)] == labels
    assert [column_to_index(label) for label in labels] == list(range(34))


def test_far_map_corner_round_trip_and_distance() -> None:
    assert HexCoord.from_label("HH27").label == "HH27"
    assert HexCoord.from_label("A1").distance(HexCoord.from_label("HH27")) > 0


def test_fts_expression_quotes_rule_numbers() -> None:
    from importlib.util import module_from_spec, spec_from_file_location

    path = ROOT / "skills/iron-bottom-sound-rules/scripts/query_rules.py"
    spec = spec_from_file_location("query_rules", path)
    assert spec and spec.loader
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.fts_expression("9.1 9.10 可选规则") == '"9.1" AND "9.10" AND "可选规则"'


def test_scenario_01_source_order_of_battle_and_special_rules() -> None:
    data = yaml.safe_load((ROOT / "resources/derived/structured/scenarios/scenario-01.yaml").read_text(encoding="utf-8"))
    ships = {ship["id"]: ship for ship in data["ships"]}
    assert len(ships) == 14
    assert ships["IBS-U-USN-FARENHOLT"]["position"] == "V12"
    assert ships["IBS-U-USN-SAN-FRANCISCO"]["position"] == "V14"
    assert ships["IBS-U-USN-HELENA"]["position"] == "Y13"
    assert ships["IBS-U-USN-MCCALLA"]["position"] == "AA12"
    assert ships["IBS-U-USN-DUNCAN"]["position"] == "X8"
    assert data["initial_phase"] == "gunnery"
    assert "shore_bombardment" not in data["victory"]
    assert len(data["reinforcements"]["ships"]) == 8
    assert data["reinforcements"]["trigger"] == {"turn": 3, "roll": "1d6", "succeeds_on": [1]}


def test_special_damage_matrix_is_complete() -> None:
    data = yaml.safe_load((ROOT / "resources/derived/structured/rules/special-damage-table.yaml").read_text(encoding="utf-8"))
    bands = data["displacement_bands"]
    assert bands == list("ABCDEFGHI")
    assert set(data["results"]) == {"44", "45", "46", "51", "52", "53", "54", "55", "56", "61", "62", "63", "64", "65"}
    for result in data["results"].values():
        assert all(band in result for band in bands)
    assert data["results"]["44"]["I"] == "2H/-1MF"
    assert data["results"]["54"]["additional"] == "primary_1_secondary_1"
    assert data["results"]["65"]["G"] == "3H/-50%"
