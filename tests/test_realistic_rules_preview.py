from pathlib import Path

from fastapi.testclient import TestClient

from iron_bottom_sound.api import app


ROOT = Path(__file__).resolve().parents[1]
RULES = ROOT / "docs" / "rules" / "realistic-command.md"


def test_realistic_rules_endpoint_serves_single_markdown_source() -> None:
    response = TestClient(app).get("/rules/realistic-command")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/markdown")
    assert response.text == RULES.read_text(encoding="utf-8")


def test_realistic_rules_explain_original_boundary_and_every_extension() -> None:
    text = RULES.read_text(encoding="utf-8")

    assert "不是原版规则勘误" in text
    assert "特殊损伤 31" in text
    assert "特殊损伤 42" in text
    for number in range(1, 8):
        assert f"IBS-R-RC-{number:02d}" in text
    assert "编队初设" in text
    assert "自主撤退" in text
    assert "战争迷雾" in text


def test_realistic_rules_route_has_no_user_selected_file_path() -> None:
    paths = {route.path for route in app.routes}

    assert "/rules/realistic-command" in paths
    assert not any("{path" in path for path in paths if path.startswith("/rules/"))
