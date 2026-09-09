from __future__ import annotations

from fastapi.testclient import TestClient

import iron_bottom_sound.api as api
from iron_bottom_sound.storage import GameRepository


def _body(entries, realistic: bool = False):
    ships = []
    for index, entry in enumerate(entries):
        side = "axis" if index < len(entries) // 2 else "allies"
        ships.append({
            "id": entry["id"], "side": side, "position": (f"H{5+index}" if side == "axis" else f"X{20+index}"),
            "heading": 1 if side == "axis" else 4, "speed": 1, "asset": entry["asset"],
        })
    formations = {"axis": [], "allies": []}
    if realistic:
        for side in ("axis", "allies"):
            members = [ship["id"] for ship in ships if ship["side"] == side]
            formations[side] = [{
                "formation_id": f"{side}-1", "name": f"{side} formation", "ship_ids": members,
                "leader_id": members[0], "flagship_id": members[0], "reserve_flagship_id": members[1],
                "spacing": 1, "heading": 1,
            }]
    return {"title": "测试自定义剧本", "turns": 4, "visibility": {"axis": 4, "allies": 4},
            "optional_rules": [], "ships": ships, "formations": formations}


def test_custom_scenario_crud_and_game_creation(tmp_path, monkeypatch):
    repository = GameRepository(tmp_path / "custom.sqlite3")
    monkeypatch.setattr(api, "repository", repository)
    client = TestClient(api.app)
    catalog = client.get("/ship-catalog").json()
    entries = [entry for entry in catalog if entry["complete"]][:4]
    created = client.post("/custom-scenarios", json=_body(entries, realistic=True))
    assert created.status_code == 201, created.text
    scenario_id = created.json()["id"]
    assert client.get(f"/custom-scenarios/{scenario_id}").status_code == 200
    assert any(item["id"] == scenario_id for item in client.get("/custom-scenarios").json())
    game = client.post("/games", json={"scenario_id": scenario_id, "seed": 3,
                                       "options": {"mode": "hotseat", "realistic_command": True}})
    assert game.status_code == 201, game.text
    assert game.json()["phase"] == "formation_setup"
    updated = client.put(f"/custom-scenarios/{scenario_id}", json=_body(entries, realistic=False))
    assert updated.status_code == 200, updated.text
    assert client.delete(f"/custom-scenarios/{scenario_id}").status_code == 204


def test_custom_scenario_rejects_duplicate_position_and_missing_asset(tmp_path, monkeypatch):
    monkeypatch.setattr(api, "repository", GameRepository(tmp_path / "custom.sqlite3"))
    client = TestClient(api.app)
    entries = [entry for entry in client.get("/ship-catalog").json() if entry["complete"]][:2]
    body = _body(entries)
    body["ships"][1]["position"] = body["ships"][0]["position"]
    body["ships"][1]["asset"] = "不存在.png"
    response = client.post("/custom-scenarios", json=body)
    assert response.status_code == 422
    assert "Ships may not overlap" in str(response.json())
    assert "missing counter asset" in str(response.json())


def test_custom_scenario_recommended_mode_round_trip(tmp_path, monkeypatch):
    monkeypatch.setattr(api, "repository", GameRepository(tmp_path / "custom.sqlite3"))
    client = TestClient(api.app)
    entries = [entry for entry in client.get("/ship-catalog").json() if entry["complete"]][:2]
    body = _body(entries)
    body["description"] = "一场快速夜战练习"
    body["recommended_mode"] = "pvp"
    created = client.post("/custom-scenarios", json=body)
    assert created.status_code == 201, created.text
    scenario_id = created.json()["id"]
    assert created.json()["description"] == "一场快速夜战练习"
    assert created.json()["recommended_mode"] == "pvp"
    stored = client.get(f"/custom-scenarios/{scenario_id}").json()
    assert stored["description"] == "一场快速夜战练习"
    assert stored["recommended_mode"] == "pvp"
    body["recommended_mode"] = "pve"
    body["description"] = "改为人机推荐"
    updated = client.put(f"/custom-scenarios/{scenario_id}", json=body)
    assert updated.status_code == 200, updated.text
    assert updated.json()["recommended_mode"] == "pve"
    assert client.get(f"/custom-scenarios/{scenario_id}").json()["recommended_mode"] == "pve"


def test_custom_scenario_seeds_engine_formations(tmp_path, monkeypatch):
    monkeypatch.setattr(api, "repository", GameRepository(tmp_path / "custom.sqlite3"))
    client = TestClient(api.app)
    entries = [entry for entry in client.get("/ship-catalog").json() if entry["complete"]][:4]
    created = client.post("/custom-scenarios", json=_body(entries, realistic=True))
    assert created.status_code == 201, created.text
    scenario_id = created.json()["id"]
    stored = client.get(f"/custom-scenarios/{scenario_id}").json()
    axis = [ship["id"] for ship in stored["ships"] if ship["side"] == "axis"]
    seeds = stored["setup"]["engine_default_formations"]["axis"]
    assert seeds == [{"id": "axis-1", "role": "authored", "ships": axis}]
    flagged = {ship["id"] for ship in stored["ships"] if ship.get("flagship")}
    allies_first = [ship["id"] for ship in stored["ships"] if ship["side"] == "allies"][0]
    assert flagged == {axis[0], allies_first}
    game = client.post("/games", json={"scenario_id": scenario_id, "seed": 3,
                                       "options": {"mode": "hotseat", "realistic_command": True}})
    assert game.status_code == 201, game.text
    game_id = game.json()["game_id"]
    for side, members in (("axis", axis), ("allies", [ship["id"] for ship in stored["ships"] if ship["side"] == "allies"])):
        suggestion = client.get(f"/games/{game_id}/suggested-orders?profile=balanced",
                                headers={"x-player-side": side}).json()
        assert suggestion["formation_setup"], "expected a formation proposal"
        proposed = [sid for order in suggestion["formation_setup"] for sid in order["ship_ids"]]
        assert set(proposed) == set(members)
        assert proposed == members, "proposal must preserve the authored leader-first order"


def test_builtin_scenarios_expose_editable_templates(tmp_path, monkeypatch):
    monkeypatch.setattr(api, "repository", GameRepository(tmp_path / "custom.sqlite3"))
    client = TestClient(api.app)
    em01 = client.get("/builtin-scenarios/IBS-S-EM-01/template")
    assert em01.status_code == 200, em01.text
    body = em01.json()
    assert len(body["ships"]) == 24
    assert body["formations"]["axis"] and body["formations"]["allies"]
    assert all(flagship != reserve
               for orders in body["formations"].values() for order in orders
               for flagship, reserve in [(order["flagship_id"], order["reserve_flagship_id"])])
    assert body["warnings"]
    s03 = client.get("/builtin-scenarios/IBS-S-03/template")
    assert s03.status_code == 200, s03.text
    assert all(len(orders) == 1 for orders in s03.json()["formations"].values())
    # 全部内置想定现均已可玩（IBS-S-02 已录入）；不存在编号仍应 404。
    missing = client.get("/builtin-scenarios/IBS-S-99/template")
    assert missing.status_code == 404


def test_ship_catalog_surfaces_record_only_extension_ships(tmp_path, monkeypatch):
    """扩展剧本（二马 24 舰）只在 ship-records/extensions 与剧本里建档、
    未进 catalog.yaml——工坊的候选列表必须把它们并进来，否则永远选不到。"""
    monkeypatch.setattr(api, "repository", GameRepository(tmp_path / "custom.sqlite3"))
    client = TestClient(api.app)
    catalog = client.get("/ship-catalog").json()
    by_id = {entry["id"]: entry for entry in catalog}
    yamato = by_id.get("IBS-U-IJN-ERMA-YAMATO")
    iowa = by_id.get("IBS-U-USN-ERMA-IOWA")
    assert yamato and yamato["complete"] and yamato["asset"]
    assert iowa and iowa["complete"] and iowa["asset"]
    erma = [entry for entry in catalog if "-ERMA-" in entry["id"]]
    assert len(erma) == 24
    assert all(entry["complete"] and entry["asset"] for entry in erma)


def test_ship_catalog_dedupes_catalog_aliases_and_binds_locked_ship_art(tmp_path, monkeypatch):
    """名录里同名同型的“目录替身”（如弗莱彻/大和）不再单列——同一艘舰只保留有
    完整档案的那条可选；仍锁定的“未建档”舰照常返回，若有棋子图则一并绑定。"""
    monkeypatch.setattr(api, "repository", GameRepository(tmp_path / "custom.sqlite3"))
    client = TestClient(api.app)
    by_id = {entry["id"]: entry for entry in client.get("/ship-catalog").json()}
    # 同名同型替身已去重：目录版弗莱彻、大和不再重复出现，其记录版仍可选。
    assert "IBS-U-USN-UNNAMED-T01-R77" not in by_id        # 弗莱彻（目录）→ FLETCHER 记录
    assert by_id["IBS-U-USN-FLETCHER"]["complete"]
    assert "IBS-U-IJN-YAMATO" not in by_id                  # 大和（目录）→ 二马大和记录
    assert by_id["IBS-U-IJN-ERMA-YAMATO"]["complete"]
    # 舰级卡扩展（class-cards.yaml）解锁后：北卡罗来纳经 BB北卡罗来纳级卡建档，complete 且有棋子图。
    north_carolina = by_id["IBS-U-USN-UNNAMED-T01-R03"]
    assert north_carolina["complete"] and north_carolina["asset"]
    # 没有对应棋子图的锁定船仍无 asset。
    south_dakota = by_id["IBS-U-USN-UNNAMED-T01-R05"]
    assert not south_dakota["complete"] and not south_dakota["asset"]
