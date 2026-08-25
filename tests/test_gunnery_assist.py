"""Batch G: gunnery auto-schedule assist — engine-calculated per-target range/modifier
in gunnery_candidates, the greedy spread recommendation, the read-only API, and the
PublicShip fire-control/crew fields surfaced to the owner only."""

import pytest
from fastapi.testclient import TestClient

from iron_bottom_sound.api import app, engine as api_engine
from iron_bottom_sound.engine import GUNNERY_ASSIST_BAND, IronBottomEngine
from iron_bottom_sound.models import OrderBatch, Phase, Side


def gunnery_state(engine: IronBottomEngine, seed: int = 3, game_id: str = "gun-assist"):
    """Default IBS-S-03 state forced into the gunnery phase."""
    state = engine.reset("IBS-S-03", seed=seed, game_id=game_id)
    state.phase = Phase.GUNNERY
    return state


def test_gunnery_target_options_carry_expected_hits() -> None:
    """每舰全部合法目标都带引擎计算的 `expected_hits`，且 = 该目标炮位组的期望命中
    之和（命中公式唯一在引擎 `expected_gunnery_hits`，AI/前端不复制）。"""
    engine = IronBottomEngine()
    state = gunnery_state(engine)
    candidates = engine.gunnery_target_options(state, Side.AXIS)
    assert any(candidate["targets"] for candidate in candidates)
    for candidate in candidates:
        attacker = state.ships[candidate["ship_id"]]
        for target in candidate["targets"]:
            assert target["expected_hits"] > 0
            independent = sum(
                engine.expected_gunnery_hits(mount.firepower, target["range"])
                for mount in attacker.gun_mounts
                if mount.id in target["mount_ids"]
            )
            assert target["expected_hits"] == pytest.approx(independent)


def test_gunnery_assist_recommendation_exposes_expected_hits() -> None:
    """gunnery_assist 的推荐（前端可显示）透传所选目标的 expected_hits。"""
    engine = IronBottomEngine()
    state = gunnery_state(engine)
    assist = engine.gunnery_assist(state, Side.AXIS)
    assert assist["recommendations"]
    for rec in assist["recommendations"]:
        assert "expected_hits" in rec and rec["expected_hits"] > 0


def test_observe_exposes_vp_for_both_sides() -> None:
    """VP 是公开船籍价值，不是隐藏损伤：hidden_damage 下敌方 hull=None 但 vp 正常下发。"""
    engine = IronBottomEngine()
    state = engine.reset("IBS-S-03", seed=3, game_id="observe-vp")
    karl = state.ships["IBS-U-KM-KARL-GALSTER"]  # 轴心舰
    jersey = next(ship for ship in state.ships.values() if ship.side == Side.ALLIES and ship.position)
    assert karl.vp > 0 and jersey.vp > 0
    # 未开启 hidden_damage：双方 hull/vp 均可见
    axis_obs = engine.observe(state.game_id, Side.AXIS)
    ally_obs = engine.observe(state.game_id, Side.ALLIES)
    axis_seen = next(ship for ship in ally_obs.ships if ship.id == karl.id)
    ally_seen = next(ship for ship in axis_obs.ships if ship.id == jersey.id)
    assert axis_seen.hull == karl.hull and axis_seen.vp == karl.vp
    assert ally_seen.hull == jersey.hull and ally_seen.vp == jersey.vp
    # 开启 hidden_damage：敌方 hull 被隐藏（各侧对彼方舰），但 vp（船籍价值）仍下发
    state.options.optional_rules.hidden_damage = True
    axis_obs2 = engine.observe(state.game_id, Side.AXIS)
    ally_obs2 = engine.observe(state.game_id, Side.ALLIES)
    axis_seen2 = next(ship for ship in ally_obs2.ships if ship.id == karl.id)
    ally_seen2 = next(ship for ship in axis_obs2.ships if ship.id == jersey.id)
    assert axis_seen2.hull is None and axis_seen2.vp == karl.vp
    assert ally_seen2.hull is None and ally_seen2.vp == jersey.vp


def test_gunnery_candidates_carry_range_and_intrinsic_modifier() -> None:
    engine = IronBottomEngine()
    state = gunnery_state(engine)
    candidates = engine._gunnery_candidates(state, Side.AXIS)
    assert any(candidate["targets"] for candidate in candidates)
    for candidate in candidates:
        attacker = state.ships[candidate["ship_id"]]
        for target in candidate["targets"]:
            assert target["range"] >= 1
            expected_caliber = max(
                (mount.caliber for mount in attacker.gun_mounts if mount.id in target["mount_ids"]),
                default=attacker.primary.caliber,
            )
            assert target["modifier"] == engine._gunnery_modifier(
                state, attacker, state.ships[target["target_id"]], target["range"],
                1, expected_caliber, 1,
            )
    # the modifier must be the intrinsic single-attacker value: a second attacker on
    # the same target must not change the candidate (the penalty is resolved at fire time)
    attacker = state.ships[candidates[0]["ship_id"]]
    chosen = candidates[0]["targets"][0]
    target = state.ships[chosen["target_id"]]
    assert engine._gunnery_modifier(state, attacker, target, chosen["range"], 2, 5.0, 1) != chosen["modifier"]


def test_gunnery_assist_prefers_most_mounts_then_best_modifier() -> None:
    engine = IronBottomEngine()
    state = gunnery_state(engine)
    assist = engine.gunnery_assist(state, Side.AXIS)
    assert assist["excluded"] == []
    assert len(assist["recommendations"]) == 3
    for candidate in engine._gunnery_candidates(state, Side.AXIS):
        recommendation = next(
            item for item in assist["recommendations"] if item["ship_id"] == candidate["ship_id"]
        )
        tier = candidate["targets"]
        max_mounts = max(len(target["mount_ids"]) for target in tier)
        # priority 1: most bearing mounts
        assert len(recommendation["mount_ids"]) == max_mounts
        # priority 2: within the engine band of the best modifier. The D66 hit table is
        # low-is-good (11 hits at firepower 1, 13+ misses), so a negative modifier is a
        # BONUS: the best target is the smallest (most negative) modifier.
        best_modifier = min(target["modifier"] for target in tier)
        assert recommendation["modifier"] <= best_modifier + GUNNERY_ASSIST_BAND
    # LODY's clearly best tier is -20 (JERSEY/JACKAL/JUPITER vs JAVELIN/KASHMIR at -12):
    # the assist must take a -20 target, not the worse -12 one
    lody = next(item for item in assist["recommendations"] if item["ship_id"] == "IBS-U-KM-HANS-LODY")
    assert lody["modifier"] == -20
    assert lody["target_id"] == "IBS-U-RN-JERSEY"


def test_gunnery_assist_spreads_equal_quality_targets() -> None:
    engine = IronBottomEngine()
    state = gunnery_state(engine)
    assist = engine.gunnery_assist(state, Side.AXIS)
    by_ship = {item["ship_id"]: item for item in assist["recommendations"]}
    # GALSTER is processed first (fewest options) and takes JAVELIN; BEITZEN has JAVELIN
    # as an equal-quality option (-20, 5 mounts) but spreads to KASHMIR instead.
    galster = by_ship["IBS-U-KM-KARL-GALSTER"]
    beitzen = by_ship["IBS-U-KM-RICHARD-BEITZEN"]
    assert galster["target_id"] == "IBS-U-RN-JAVELIN"
    assert beitzen["target_id"] == "IBS-U-RN-KASHMIR"
    assert galster["target_id"] != beitzen["target_id"]
    # spreading must not sacrifice quality: KASHMIR is in BEITZEN's band (equal modifier)
    assert beitzen["modifier"] == -20


def test_gunnery_assist_most_constrained_first() -> None:
    engine = IronBottomEngine()
    state = gunnery_state(engine)
    assist = engine.gunnery_assist(state, Side.AXIS)
    # constrained ships (fewest target options) are recommended first so they keep their pick
    assert [item["ship_id"] for item in assist["recommendations"]] == [
        "IBS-U-KM-KARL-GALSTER", "IBS-U-KM-RICHARD-BEITZEN", "IBS-U-KM-HANS-LODY",
    ]


def test_gunnery_assist_assigned_ships_excluded_and_seed_load() -> None:
    engine = IronBottomEngine()
    state = gunnery_state(engine)
    # an already-scheduled ship is not recommended again, and its target counts as loaded
    assist = engine.gunnery_assist(state, Side.AXIS, assigned=[
        {"ship_id": "IBS-U-KM-KARL-GALSTER", "target_id": "IBS-U-RN-JAVELIN"},
    ])
    ship_ids = {item["ship_id"] for item in assist["recommendations"]}
    assert "IBS-U-KM-KARL-GALSTER" not in ship_ids
    # the seeded load on JAVELIN pushes BEITZEN to KASHMIR even without GALSTER's earlier choice
    assert {item["target_id"] for item in assist["recommendations"] if item["ship_id"] == "IBS-U-KM-RICHARD-BEITZEN"} == {"IBS-U-RN-KASHMIR"}
    # with only BEITZEN pre-assigned to JAVELIN, GALSTER must avoid the loaded JAVELIN
    assist2 = engine.gunnery_assist(state, Side.AXIS, assigned=[
        {"ship_id": "IBS-U-KM-RICHARD-BEITZEN", "target_id": "IBS-U-RN-JAVELIN"},
    ])
    galster = next(item for item in assist2["recommendations"] if item["ship_id"] == "IBS-U-KM-KARL-GALSTER")
    assert galster["target_id"] == "IBS-U-RN-KASHMIR"


def test_gunnery_assist_excludes_blocked_ships() -> None:
    engine = IronBottomEngine()
    state = gunnery_state(engine)
    state.ships["IBS-U-KM-HANS-LODY"].guns_disabled_turns = 1
    assist = engine.gunnery_assist(state, Side.AXIS)
    assert all(item["ship_id"] != "IBS-U-KM-HANS-LODY" for item in assist["recommendations"])
    lody_excluded = next(item for item in assist["excluded"] if item["ship_id"] == "IBS-U-KM-HANS-LODY")
    assert lody_excluded["reason"] == "本回合全部火炮失效"


def test_gunnery_assist_recommendations_are_engine_legal() -> None:
    engine = IronBottomEngine()
    state = gunnery_state(engine)
    assist = engine.gunnery_assist(state, Side.AXIS)
    for recommendation in assist["recommendations"]:
        attacker = state.ships[recommendation["ship_id"]]
        target = state.ships[recommendation["target_id"]]
        assert engine._can_see(state, attacker, target)
        for mount_id in recommendation["mount_ids"]:
            mount = next(item for item in attacker.gun_mounts if item.id == mount_id)
            assert not mount.destroyed and not mount.fired_this_phase
            assert engine._mount_can_bear(attacker, target, mount.arcs)


def test_gunnery_assist_api_shape_read_only_and_wrong_phase() -> None:
    client = TestClient(app)
    created = client.post("/games", json={"scenario_id": "IBS-S-03", "seed": 3}).json()
    game_id = created["game_id"]
    state = api_engine.get(game_id)
    state.phase = Phase.GUNNERY
    before = len(api_engine.get(game_id).events)
    response = client.post(
        f"/games/{game_id}/gunnery-assist",
        headers={"X-Player-Side": "axis"},
        json={"assigned": [{"ship_id": "IBS-U-KM-KARL-GALSTER", "target_id": "IBS-U-RN-JAVELIN"}]},
    )
    assert response.status_code == 200
    body = response.json()
    assert len(body["recommendations"]) == 2  # GALSTER was excluded
    for key in ("ship_id", "target_id", "mount_ids", "range", "modifier"):
        assert key in body["recommendations"][0]
    assert len(api_engine.get(game_id).events) == before  # pure read-only

    # wrong phase is rejected
    api_engine.get(game_id).phase = Phase.TORPEDO_PLANNING
    rejected = client.post(
        f"/games/{game_id}/gunnery-assist",
        headers={"X-Player-Side": "axis"},
        json={},
    )
    assert rejected.status_code == 409


def test_public_ship_exposes_fire_control_only_to_owner() -> None:
    engine = IronBottomEngine()
    state = gunnery_state(engine)
    karl = state.ships["IBS-U-KM-KARL-GALSTER"]
    karl.mfc_destroyed = True
    karl.radar_destroyed = True
    karl.bridge_destroyed = False
    karl.rudder_destroyed = True
    karl.captain_status = "wounded"
    axis_ship = next(ship for ship in engine.observe(state.game_id, Side.AXIS).ships if ship.id == karl.id)
    ally_ship = next(ship for ship in engine.observe(state.game_id, Side.ALLIES).ships if ship.id == karl.id)
    assert axis_ship.mfc_destroyed is True
    assert axis_ship.radar_destroyed is True
    assert axis_ship.bridge_destroyed is False
    assert axis_ship.rudder_destroyed is True
    assert axis_ship.captain_status == "wounded"
    # the enemy never sees internal fire-control/crew state
    assert ally_ship.mfc_destroyed is False
    assert ally_ship.radar_destroyed is False
    assert ally_ship.rudder_destroyed is False
    assert ally_ship.captain_status is None
