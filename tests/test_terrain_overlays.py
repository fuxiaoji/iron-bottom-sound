from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
MAPS = ROOT / "resources" / "derived" / "structured" / "maps"


def test_verified_overlay_cells_partition_the_local_grids() -> None:
    data = yaml.safe_load((MAPS / "terrain-overlays.yaml").read_text(encoding="utf-8"))
    assert data["classification"] == {"land_min_fraction": 0.5, "coast_min_fraction": 0.08}
    for overlay in data["overlays"].values():
        assert overlay["verification"] == "verified_source"
        cells = overlay["cells"]
        combined = cells["land"] + cells["coast"] + cells["sea"]
        assert len(combined) == 182
        assert len(set(combined)) == 182
        assert set(combined) == set(overlay["land_fraction_by_cell"])


def test_overlay_anchor_calibration_matches_qa_review() -> None:
    overlays = yaml.safe_load((MAPS / "terrain-overlays.yaml").read_text(encoding="utf-8"))["overlays"]
    assert overlays["savo_island"]["anchors"] == {"X": [4, 0], "Y": [6, 13]}
    assert overlays["guadalcanal_coast"]["anchors"] == {"Z": [7, 9]}
    assert "4,0" in overlays["savo_island"]["cells"]["coast"]
    assert "6,13" in overlays["savo_island"]["cells"]["coast"]
    assert "7,9" in overlays["guadalcanal_coast"]["cells"]["coast"]


def test_release_scenarios_use_the_pure_sea_main_map() -> None:
    for number in (1, 3):
        scenario = yaml.safe_load(
            (ROOT / "resources" / "derived" / "structured" / "scenarios" / f"scenario-{number:02d}.yaml").read_text(
                encoding="utf-8"
            )
        )
        assert "terrain_overlays" not in scenario
