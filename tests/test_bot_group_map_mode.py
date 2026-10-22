"""The room cannot choose a different PVE seat or weaken PVP visibility."""
import pytest

from iron_bottom_sound.bot.service import BattleService
from iron_bottom_sound.models import Side


@pytest.mark.parametrize("side", ["axis", "allies"])
def test_pve_group_map_selects_only_non_bot_seat(tmp_path, monkeypatch, side):
    service = BattleService(tmp_path / "map.sqlite3")
    try:
        state = service.create("agent:owner", "room", opponent="pve", side=side, request_id="create")
        called = []
        monkeypatch.setattr("iron_bottom_sound.bot.public_view.pve_public_png",
                            lambda engine, game, player: called.append(player) or b"PVE-PNG")
        monkeypatch.setattr("iron_bottom_sound.bot.public_view.public_png",
                            lambda *args: pytest.fail("PVE accidentally used intersection"))
        assert service.public_screenshot(state["match_id"], "room") == b"PVE-PNG"
        assert called == [Side(side)]
        public = service.public_status(state["match_id"], "room")
        assert public["map_view"] == "pve_player" and public["view_side"] == side
        assert "observation" not in public and "orders" not in public
    finally:
        service.close()


def test_pvp_group_map_always_keeps_intersection(tmp_path, monkeypatch):
    service = BattleService(tmp_path / "map.sqlite3")
    try:
        state = service.create("agent:a", "room", opponent="pvp", request_id="create")
        service.join(state["match_id"], "agent:b", "room", request_id="join")
        monkeypatch.setattr("iron_bottom_sound.bot.public_view.pve_public_png",
                            lambda *args: pytest.fail("PVP cannot expose one player's view"))
        monkeypatch.setattr("iron_bottom_sound.bot.public_view.public_png", lambda *args: b"PVP-PNG")
        assert service.public_screenshot(state["match_id"], "room") == b"PVP-PNG"
        public = service.public_status(state["match_id"], "room")
        assert public["map_view"] == "shared" and public["view_side"] is None
    finally:
        service.close()
