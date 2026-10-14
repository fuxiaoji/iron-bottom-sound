"""Night-v2 boundaries; relocated fleets below are SYNTHETIC rule fixtures.

Blocked canonical S-04/S-10 are asserted as source blockers, not playtest wins.
"""
from copy import deepcopy
import json
import pytest
from fastapi.testclient import TestClient
from iron_bottom_sound import night, savo, ai_memory
from iron_bottom_sound.engine import IronBottomEngine
from iron_bottom_sound.models import GameOptions, OptionalRules, OrderBatch, Phase, Side, HexCoord, IlluminationOrder, MarkerState, SearchlightOrder, AIPlanSheet
from iron_bottom_sound.storage import GameRepository
from iron_bottom_sound.savegame import build_save_bundle, validate_save_bundle, clone_imported_game, _checksum


@pytest.fixture
def fixture():
    engine = IronBottomEngine()
    state = engine.reset("IBS-S-03", options=GameOptions(ruleset_version="night-v2", optional_rules=OptionalRules(
        radar=True, star_shells=True, searchlights=True, smoke=True, squalls=True)))
    a = next(s for s in state.ships.values() if s.side == Side.AXIS)
    b = next(s for s in state.ships.values() if s.side == Side.ALLIES)
    for ship in state.ships.values():
        ship.position = None
    a.position, b.position = HexCoord.from_label("M12"), HexCoord.from_label("P12")
    a.heading, b.heading = 6, 6
    state.visibility = {"axis": 4, "allies": 4}
    state.phase = Phase.GUNNERY
    return engine, state, a, b


@pytest.mark.parametrize("key", list(OptionalRules.model_fields))
@pytest.mark.parametrize("on", [False, True])
def test_switches_are_snapshotted_observed_and_legacy_unaffected(key, on):
    engine = IronBottomEngine()
    state = engine.reset("IBS-S-03", options=GameOptions(ruleset_version="night-v2", optional_rules=OptionalRules(**{key:on})))
    view = engine.observe(state.game_id, Side.AXIS)
    assert (key in view.enabled_optional_rules) == on
    assert state.rule_snapshot["sources"] and state.rule_snapshot["adjudication"]
    old = engine.reset("IBS-S-03", options=GameOptions())
    assert old.options.ruleset_version == "legacy-v1" and not old.rule_snapshot and not old.land_hexes


@pytest.mark.parametrize("scenario,anchor,blocked", [("02","A27",False),("04","H6",True),("06","U6",False),("08","B26",False),("10","A20",True)])
def test_canonical_overlay_anchors_clipping_and_source_blockers(scenario, anchor, blocked):
    engine = IronBottomEngine()
    state = engine.reset(f"IBS-S-{scenario}", options=GameOptions(ruleset_version="night-v2"))
    assert night.config(state)["terrain"][state.scenario_id]["at"] == anchor
    assert state.land_hexes and state.coast_hexes
    assert all(night.on_map(state, HexCoord.from_label(h)) for h in state.land_hexes | state.coast_hexes)
    assert bool(state.scenario_state.get("rule_blockers")) == blocked
    if blocked:
        with pytest.raises(ValueError, match="IBS-Q-"):
            engine.advance(state.game_id)


def test_illumination_is_private_delayed_and_reserves_mount(fixture, monkeypatch):
    engine,state,a,b = fixture
    row = night.candidates(engine,state,Side.AXIS)["illumination"][0]
    batch = OrderBatch(side=Side.AXIS, phase=state.phase, illumination=[IlluminationOrder(ship_id=a.id,mount_id=row["mount_id"],target_hex=b.position)])
    assert engine.validate_orders(state.game_id,batch).valid
    engine.submit_orders(state.game_id,batch)
    engine.submit_orders(state.game_id,OrderBatch(side=Side.ALLIES,phase=state.phase))
    engine.advance(state.game_id)
    assert not any(m.kind=="star_shell" for m in state.markers)
    assert state.scenario_state["pending_illumination"][0]["turn"] == 2
    assert all(e.type!="illumination_planned" for e in engine.observe(state.game_id,Side.ALLIES).recent_events)
    assert all(m.fired_this_phase for m in a.gun_mounts if m.id in row["occupied_mount_ids"])
    monkeypatch.setattr(engine,"_roll_d6",lambda state:(6,6))
    state.turn=2
    night.after_movement(engine,state)
    assert any(m.kind=="star_shell" and m.expires_turn==2 for m in state.markers)
    assert not state.scenario_state["pending_illumination"]


@pytest.mark.parametrize("nation,date,roll,success", [("IJN","1942-08-09",4,True),("KM","1940-01-01",3,False),("USN","1942-08-09",5,False),("USN","1942-08-09",6,True),("USN","1942-09-01",5,True),("RN","1942-08-09",4,False)])
def test_illumination_national_date_failure_boundaries(fixture,monkeypatch,nation,date,roll,success):
    engine,state,a,b=fixture
    del state.ships[a.id];a.id=f"IBS-U-{nation}-FIXTURE";state.ships[a.id]=a
    state.rule_snapshot["scenario"]["date"]=date
    state.scenario_state["pending_illumination"]=[{"turn":state.turn,"ship_id":a.id,"position":b.position.model_dump()}]
    monkeypatch.setattr(engine,"_roll_d6",lambda state:(roll,roll))
    night.after_movement(engine,state)
    assert state.events[-1].payload["success"] is success
    assert any(m.kind=="star_shell" for m in state.markers) is success


def test_searchlight_los_year_range_and_user_exposure(fixture):
    engine,state,a,b=fixture
    state.rule_snapshot["scenario"]["date"]="1927-01-01"
    assert night.searchlight_range(state,a)==10
    state.rule_snapshot["scenario"]["date"]="1928-01-01"
    assert night.searchlight_range(state,a)==14
    batch=OrderBatch(side=Side.AXIS,searchlights=[SearchlightOrder(ship_id=a.id,target_id=b.id)])
    assert not night.validate(engine,state,batch)
    night.prepare_gunnery(engine,state,[batch])
    assert night.illuminated(state,a) and night.illuminated(state,b)
    assert engine.observe(state.game_id,Side.AXIS).environment["beams"]
    state.land_hexes.add(engine._hex_line(a.position,b.position)[1].label)
    assert night.validate(engine,state,batch)


@pytest.mark.parametrize("roll,distance", [(1,0),(2,1),(3,1),(4,1),(5,1),(6,2)])
def test_squalls_single_die_all_centers_and_seven_hexes(fixture,monkeypatch,roll,distance):
    engine,state,a,b=fixture
    state.markers=[MarkerState(id="rain1",kind="squall",position=HexCoord.from_label("T20")),MarkerState(id="rain2",kind="squall",position=HexCoord.from_label("X20"))]
    before=[m.position for m in state.markers]
    calls=[]
    monkeypatch.setattr(engine,"_roll_d6",lambda state:(calls.append(1) or roll,roll))
    night.move_squalls(engine,state)
    assert len(calls)==1
    assert all(p.distance(m.position)==distance for p,m in zip(before,state.markers))
    areas=engine.observe(state.game_id,Side.AXIS).environment["areas"]
    assert all(len(row["hexes"])==7 for row in areas)


def test_rain_no_random_generation_invalid_configuration_and_radar(fixture):
    engine,state,a,b=fixture
    assert not any(m.kind=="squall" for m in state.markers)
    for centers in (["ZZ99"],["K12","K12"]):
        with pytest.raises(ValueError):
            engine.reset("IBS-S-03",options=GameOptions(ruleset_version="night-v2",optional_rules=OptionalRules(squalls=True),squall_hexes=centers))
    a.radar=True
    state.markers=[MarkerState(id="rain",kind="squall",position=a.position)]
    assert not night.radar_contact(engine,state,a,b)
    assert not night.candidates(engine,state,Side.AXIS)["illumination"]


def test_smoke_actual_path_bidirectional_and_only_once(fixture):
    engine,state,a,b=fixture
    path=engine._hex_line(a.position,b.position)
    state.scenario_state["turn_paths"]={a.id:[p.model_dump() for p in path]}
    night.prepare_gunnery(engine,state,[OrderBatch(side=Side.AXIS,smoke_ships=[a.id])])
    assert {m.position.label for m in state.markers if m.kind=="smoke"}=={p.label for p in path}
    assert night.smoke_crossed(engine,state,a,b) and night.smoke_crossed(engine,state,b,a)
    assert engine._gunnery_modifiers(state,a,b,a.position.distance(b.position),1,5,1)["through_smoke"]==6
    assert engine._gunnery_modifiers(state,b,a,a.position.distance(b.position),1,5,1)["through_smoke"]==6


def test_losses_do_not_count_exit_reserve_and_unseen_sinking(fixture):
    engine,state,a,b=fixture
    b.position=HexCoord.from_label("AA30")
    engine._damage_hull(state,b,b.hull,"fixture")
    own=engine.observe(state.game_id,Side.AXIS)
    assert own.battle_losses["allies"]["sunk_count"]==0
    assert engine.observe(state.game_id,Side.AXIS,debug=True).battle_losses["allies"]["sunk_count"]==1
    a.position=None;a.command_status="withdrawn"
    assert night.losses(state,Side.AXIS,{a.id},state.events)["axis"]["sunk_count"]==0


def test_memory_is_read_only_until_accept_idempotent_private_and_stale(fixture):
    engine,state,a,b=fixture
    batch=OrderBatch(side=Side.AXIS)
    plan=AIPlanSheet(turn=state.turn,phase=state.phase,situation_summary="fixture",phase_goal="test",orders=batch.model_dump(mode="json"))
    before=deepcopy(state.ai_memory)
    ai_memory.prompt_memory(state,Side.AXIS)
    assert state.ai_memory==before
    engine.submit_orders(state.game_id,batch)
    ai_memory.accepted(engine,state,Side.AXIS,plan,batch)
    ai_memory.accepted(engine,state,Side.AXIS,plan,batch)
    assert state.ai_memory["axis"]["revision"]==1 and len(state.ai_traces)==1
    assert not state.ai_memory.get("allies")
    state.turn+=3
    data=json.loads(ai_memory.prompt_memory(state,Side.AXIS))
    assert data["contacts"][b.id]["age_turns"]==3 and data["contacts"][b.id]["is_current"] is False
    assert ai_memory.sanitize({"reasoning_content":"private","x":"sk-123456789SECRET","authorization":"Bearer secret"})=={"x":"[secret removed]"}


def test_v2_memory_journal_freeze_portable_legacy_import(fixture,tmp_path):
    engine,state,a,b=fixture
    repo=GameRepository(tmp_path/"isolated.sqlite3")
    ai_memory.record_trace(state,Side.AXIS,{"status":"fixture","reasoning_content":"private"})
    repo.save(state)
    bundle=build_save_bundle(repo,state)
    loaded,snapshots=validate_save_bundle(json.loads(json.dumps(bundle)))
    clone,snapshots=clone_imported_game(loaded,snapshots);repo.import_game(clone,snapshots)
    assert repo.ai_debug(clone.game_id)[0]["status"]=="fixture"
    another=IronBottomEngine();another.games[clone.game_id]=clone
    assert engine._gunnery_modifiers(state,a,b,3,1,5,1)==another._gunnery_modifiers(clone,clone.ships[a.id],clone.ships[b.id],3,1,5,1)
    bundle["version"]=1;bundle.pop("ai_debug");bundle["state"]["options"].pop("ruleset_version")
    bundle["state"]["rule_snapshot"]={};bundle["checksum"]=_checksum(bundle)
    assert validate_save_bundle(bundle)[0].options.ruleset_version=="legacy-v1"
    repo.close()


@pytest.mark.parametrize("roll",range(2,13))
def test_savo_all_2d6_outcomes_once_per_turn(fixture,monkeypatch,roll):
    engine,state,a,b=fixture
    state.scenario_id="IBS-S-10";state.turn=2;state.phase=Phase.REINFORCEMENT
    monkeypatch.setattr(engine,"_roll_2d6",lambda state:(roll,[1,roll-1]))
    savo.prepare(engine,state);before=len(state.events);savo.prepare(engine,state)
    assert len(state.events)==before
    assert state.scenario_state["savo_available_groups"]==night.config(state)["savo"]["reinforcement_table"][str(roll)]


def test_savo_exit_return_tulagi_bonus_not_sunk_and_no_30_turn_timeout(fixture):
    engine,state,a,b=fixture
    state.scenario_id="IBS-S-10";a.position=HexCoord.from_label("HH5")
    state.scenario_state["savo_torpedo_expended"]={a.id:2}
    assert savo.crossing(engine,state,a,HexCoord.from_label("II5"))
    assert not a.sunk and state.score["axis"]==9
    assert state.scenario_state["tulagi_trigger"]["turn"]==3
    assert not savo.candidates(engine,state,Side.AXIS)
    state.turn=2
    assert any(r["ship_id"]==a.id for r in savo.candidates(engine,state,Side.AXIS))
    a.position=HexCoord.from_label("HH5")
    savo.crossing(engine,state,a,HexCoord.from_label("II5"))
    assert state.score["axis"]==9
    state.turn=30
    engine._check_victory(state)
    assert state.phase!=Phase.COMPLETE  # Other canonical fleet units still haven't exited.


def test_read_only_briefing_debug_gate_upgrade_preserves_original(tmp_path,monkeypatch):
    from iron_bottom_sound import api
    monkeypatch.setattr(api,"engine",IronBottomEngine())
    monkeypatch.setattr(api,"repository",GameRepository(tmp_path/"api.sqlite3"))
    client=TestClient(api.app)
    game=client.post("/games",json={"scenario_id":"IBS-S-03","options":{"ruleset_version":"night-v2"}}).json()["game_id"]
    before=api.engine.get(game).model_dump_json()
    assert client.get(f"/games/{game}/briefing").json()["runtime"]["ruleset_version"]=="night-v2"
    assert client.get(f"/games/{game}/ai-debug").status_code==403
    assert client.get(f"/games/{game}/ai-debug?debug=true").status_code==200
    assert api.engine.get(game).model_dump_json()==before
    remote = TestClient(api.app, client=("198.51.100.10", 54321))
    api.engine.get(game).phase = Phase.TORPEDO_PLANNING
    assert remote.get(f"/games/{game}/view?debug=true").status_code == 403
    assert remote.get(f"/games/{game}/sealed-trajectories?debug=true").status_code == 403
    assert remote.get(f"/games/{game}/sealed-trajectories", headers={"X-Player-Side":"axis"}).status_code == 200
    assert client.get(f"/games/{game}/sealed-trajectories?debug=true", headers={"X-Player-Side":"axis"}).status_code == 200
    old=client.post("/games",json={"scenario_id":"IBS-S-03","options":{"ruleset_version":"legacy-v1"}}).json()["game_id"]
    old_before=api.engine.get(old).model_dump_json()
    copy=client.post(f"/games/{old}/upgrade-copy")
    assert copy.status_code==201 and copy.json()["game_id"]!=old
    assert api.engine.get(old).model_dump_json()==old_before
    api.engine.get(old).submitted_orders["axis"]=OrderBatch(side=Side.AXIS)
    assert client.post(f"/games/{old}/upgrade-copy").status_code==409
    old_savo = client.post("/games", json={"scenario_id":"IBS-S-10", "options":{"ruleset_version":"legacy-v1"}}).json()["game_id"]
    runtime = client.get(f"/games/{old_savo}/briefing").json()["runtime"]
    assert not runtime["unlimited_turns"]
    assert "30" in runtime["ending_condition"]
    assert "旧局" in runtime["reinforcement_status"]
    new_savo = client.post("/games", json={"scenario_id":"IBS-S-10"}).json()["game_id"]
    assert client.get(f"/games/{new_savo}/briefing").json()["runtime"]["unlimited_turns"]
    summaries = {s["game_id"]:s for s in client.get("/games").json()}
    assert summaries[new_savo]["unlimited_turns"] and not summaries[old_savo]["unlimited_turns"]


@pytest.mark.parametrize("scenario,real_count", [("03",2),("08",1)])
def test_hidden_contact_setup_uses_source_year_and_does_not_reveal_truth(scenario,real_count):
    from iron_bottom_sound.llm import DeterministicCommander
    engine=IronBottomEngine()
    state=engine.reset("IBS-S-"+scenario,options=GameOptions(ruleset_version="night-v2",optional_rules=OptionalRules(hidden_contacts=True)))
    own=[m for m in state.markers if m.secret_side==Side.AXIS]
    assert sum(m.contact_truth=="real" for m in own)==real_count
    assert len(own)==2*real_count
    for side in Side:
        batch=DeterministicCommander().choose_orders(engine,state.game_id,side)
        assert engine.submit_orders(state.game_id,batch).valid
    engine.advance(state.game_id)
    assert all(m.contact_truth is None for m in engine.observe(state.game_id,Side.ALLIES).markers if m.secret_side==Side.AXIS)
    assert not any(s.side==Side.AXIS for s in engine.observe(state.game_id,Side.ALLIES).ships)


@pytest.mark.parametrize("year,nation,exception,allowed", [(1942,"USN",False,False),(1943,"USN",False,True),(1942,"USN",True,True),(1943,"RN",False,False)])
def test_radar_detection_does_not_imply_permission_to_fire(fixture,year,nation,exception,allowed):
    engine,state,a,b=fixture
    del state.ships[a.id];a.id="IBS-U-USN-HELENA" if exception else f"IBS-U-{nation}-FIXTURE";state.ships[a.id]=a
    a.radar=True;state.rule_snapshot["scenario"]["date"]=f"{year}-08-09"
    state.visibility={"axis":1,"allies":1}
    assert night.radar_contact(engine,state,a,b)
    assert night.can_fire(engine,state,a,b) is allowed
    state.options.optional_rules.radar=False
    assert not night.radar_contact(engine,state,a,b) and not night.can_fire(engine,state,a,b)


def test_radar_variant_nearest_first_turn_shore_shadow_and_penetration_limit(fixture):
    from iron_bottom_sound.models import GunneryOrder
    engine,state,a,b=fixture
    del state.ships[a.id];a.id="IBS-U-USN-FIXTURE";state.ships[a.id]=a
    state.rule_snapshot["scenario"]["date"]="1942-08-09"
    state.visibility={"axis":1,"allies":1};a.radar=True
    c=b.model_copy(deep=True);c.id="FAR-FIXTURE";c.position=HexCoord.from_label("R12");state.ships[c.id]=c
    state.options.radar_1942_variant=True
    assert night.can_fire(engine,state,a,b) and not night.can_fire(engine,state,a,c)
    state.scenario_state["radar_first_fire"]={a.id:state.turn-1}
    assert night.can_fire(engine,state,a,c)
    for distance,blocked in ((4,True),(5,False)):
        state.land_hexes={HexCoord(q=b.position.q,r=b.position.r+distance).label}
        assert engine._terrain_blocks_sight(state,a.position,b.position,radar=True) is blocked
    state.land_hexes.clear()
    c.position=HexCoord(q=a.position.q+26,r=a.position.r-13)
    assert night.radar_contact(engine,state,a,c) and not night.can_fire(engine,state,a,c)
    assert all(t["target_id"]!=c.id for row in engine._gunnery_candidates(state,Side.AXIS) for t in row["targets"])
    batch=OrderBatch(side=Side.AXIS,gunnery=[GunneryOrder(ship_id=a.id,primary_target=c.id)])
    assert any("IBS-Q-021" in e for e in night.validate(engine,state,batch))
    with pytest.raises(ValueError,match="IBS-Q-021"):
        engine.rules.penetration("US",5,26)
    assert engine.rules.penetration("US",5,25)>=0


@pytest.mark.parametrize("rule,field", [("star_shells","illumination"),("searchlights","searchlights"),("smoke","smoke_ships")])
def test_disabled_night_actions_are_rejected(fixture,rule,field):
    engine,state,a,b=fixture
    row=night.candidates(engine,state,Side.AXIS)["illumination"][0]
    orders={"illumination":[{"ship_id":a.id,"mount_id":row["mount_id"],"broadside":row["broadside"],"target_hex":b.position}],
            "searchlights":[{"ship_id":a.id,"target_id":b.id}],"smoke_ships":[a.id]}
    setattr(state.options.optional_rules,rule,False)
    assert not engine.validate_orders(state.game_id,OrderBatch(side=Side.AXIS,**{field:orders[field]})).valid


@pytest.mark.parametrize("on",[False,True])
def test_raw_66_malfunction_switch_executes_after_modifier(fixture,monkeypatch,on):
    from iron_bottom_sound.models import GunneryOrder,GunMountOrder
    engine,state,a,b=fixture;state.options.optional_rules.malfunction_66=on
    row=engine._gunnery_candidates(state,Side.AXIS)[0]["targets"][0]
    batch=OrderBatch(side=Side.AXIS,gunnery=[GunneryOrder(ship_id=a.id,mounts=[GunMountOrder(mount_id=row["mount_ids"][0],target_id=b.id)])])
    engine.submit_orders(state.game_id,batch);engine.submit_orders(state.game_id,OrderBatch(side=Side.ALLIES));
    monkeypatch.setattr(engine,"_roll_d66",lambda s:(66,[6,6]));monkeypatch.setattr(engine,"_roll_2d6",lambda s:(6,[3,3]))
    engine.advance(state.game_id)
    attack=next(e for e in state.events if e.type=="gun_mount_attack")
    assert attack.dice.raw==66 and attack.dice.adjusted!=66
    assert any(e.type=="malfunction" for e in state.events) is on


def test_silhouettes_use_executed_shots_and_not_enemy_sealed_plans(fixture):
    from iron_bottom_sound.models import GunneryOrder
    engine,state,a,b=fixture
    state.options.optional_rules.silhouettes=True;state.visibility={"axis":0,"allies":0}
    a.position=HexCoord.from_label("M10");b.position=HexCoord.from_label("M12")
    c=b.model_copy(deep=True);c.id="FURTHER-FIXTURE";c.position=HexCoord.from_label("M14");state.ships[c.id]=c
    state.sealed_orders[f"{state.turn}:gunnery"]={"axis":OrderBatch(side=Side.AXIS,gunnery=[GunneryOrder(ship_id=a.id,primary_target=c.id)])}
    assert not engine._silhouetted(state,b)
    engine._event(state,"gun_mount_attack","synthetic executed shot",payload={"attacker":a.id,"target":c.id})
    assert engine._silhouetted(state,b) and night.optical_ship(engine,state,a,b)
    state.options.optional_rules.silhouettes=False
    assert not night.optical_ship(engine,state,a,b)
    state.turn+=1;state.options.optional_rules.silhouettes=True
    assert not engine._silhouetted(state,b)


def test_hidden_damage_and_unconfirmed_wrecks_do_not_leak(fixture):
    engine,state,a,b=fixture
    state.options.optional_rules.hidden_damage=True;b.hull-=1
    view=engine.observe(state.game_id,Side.AXIS)
    assert next(s for s in view.ships if s.id==b.id).hull is None
    assert not view.battle_losses["allies"]["damaged"]
    b.position=HexCoord.from_label("AA30")
    engine._damage_hull(state,b,b.hull,"synthetic unseen sinking")
    view=engine.observe(state.game_id,Side.AXIS)
    assert not any(w.source_ship_id==b.id for w in view.wrecks)
    assert not any(m.ship_id==b.id for m in view.markers)
    assert b.id not in view.model_dump_json()
    assert engine.observe(state.game_id,Side.AXIS,debug=True).battle_losses["allies"]["sunk_count"]==1


def test_blind_torpedo_event_projection_and_explicit_reveal(fixture):
    from iron_bottom_sound.models import TorpedoTrack
    engine,state,a,b=fixture
    state.options.optional_rules.blind_torpedoes=True
    t=TorpedoTrack(id="PRIVATE-TRACK",side=Side.AXIS,launcher_ship_id=a.id,torpedo_type=a.torpedo_type,position=a.position,
                   heading=1,speed_cycle=(8,8,2),range_remaining=12,launched_turn=1,hidden=True)
    state.torpedo_tracks=[t]
    engine._event(state,"torpedo_moved","private route",payload={"track_id":t.id,"launcher_ship_id":a.id,"path":["M12"]})
    assert "PRIVATE-TRACK" not in engine.observe(state.game_id,Side.ALLIES).model_dump_json()
    state.phase=Phase.TORPEDO_PLANNING
    batch=OrderBatch(side=Side.AXIS,blind_torpedo_reveals=[t.id])
    assert engine.submit_orders(state.game_id,batch).valid
    engine.submit_orders(state.game_id,OrderBatch(side=Side.ALLIES));engine.advance(state.game_id)
    assert not t.hidden
    assert "PRIVATE-TRACK" in engine.observe(state.game_id,Side.ALLIES).model_dump_json()
    assert not any(e.type=="torpedo_moved" for e in engine.public_events(state,Side.ALLIES,state.events))


def test_unknown_attacker_redacted_in_events_and_memory(fixture):
    engine,state,a,b=fixture
    b.position=HexCoord.from_label("AA30")
    ai_memory.accepted(engine,state,Side.AXIS,None,OrderBatch(side=Side.AXIS))
    e=engine._event(state,"gunnery_result",f"{b.name} hits {a.name}",payload={"attacker":b.id,"target":a.id})
    projection=engine.public_events(state,Side.AXIS,[e])[0]
    assert b.id not in projection.model_dump_json() and b.name not in projection.message
    ai_memory.record_results(engine,state)
    assert b.name not in ai_memory.prompt_memory(state,Side.AXIS)
    assert b.id in e.model_dump_json()  # Raw deterministic history is preserved.


def test_public_track_only_event_does_not_reveal_unseen_launcher(fixture):
    from iron_bottom_sound.models import TorpedoTrack
    engine, state, observer, launcher = fixture
    launcher.position = HexCoord.from_label("AA30")
    track = TorpedoTrack(id=f"TT-1-{launcher.id}-TT1-1", side=launcher.side,
        launcher_ship_id=launcher.id, torpedo_type=launcher.torpedo_type,
        position=observer.position, heading=1, speed_cycle=(8,8,2),
        range_remaining=12, launched_turn=1, hidden=False)
    state.torpedo_tracks.append(track)
    event = engine._event(state, "torpedo_terrain_hit", f"鱼雷 {track.id} 触岸",
        payload={"track_id":track.id, "land_hex":observer.position.label})
    assert launcher.id in event.model_dump_json()
    assert launcher.id not in engine.public_events(state, observer.side, [event])[0].model_dump_json()


@pytest.mark.parametrize("margin,ca,winner,reason",[(15,0,Side.ALLIES,"战术"),(16,0,Side.AXIS,"战术"),(49,0,Side.AXIS,"战术"),(50,0,Side.AXIS,"决定性"),(-1,3,Side.ALLIES,"决定性"),(0,3,Side.ALLIES,"战术")])
def test_savo_victory_tier_boundaries(fixture,margin,ca,winner,reason):
    engine,state,a,b=fixture;state.scenario_id="IBS-S-10"
    for ship in state.ships.values():
        if ship.side==Side.AXIS:
            ship.position=None;state.scenario_state.setdefault("savo_exits",{})[ship.id]={"kind":"final_exit"}
    for index in range(ca):
        ship=a.model_copy(deep=True);ship.id=f"SYNTHETIC-SUNK-{index}";ship.ship_type="CA";ship.sunk=True;state.ships[ship.id]=ship
    state.score={"axis":max(0,margin),"allies":max(0,-margin)}
    savo.finish(engine,state)
    assert state.phase==Phase.COMPLETE and state.winner==winner and reason in state.victory_reason


def test_savo_actual_movement_exit_reinforcement_and_aircraft_do_not_count_as_kills(fixture):
    from iron_bottom_sound.models import MovementOrder,ReinforcementOrder
    engine,state,a,b=fixture;state.scenario_id="IBS-S-10";state.turn=2
    a.position=HexCoord.from_label("HH5");a.heading=2;a.current_speed=a.previous_speed=1
    state.phase=Phase.MOVEMENT_RESOLUTION
    state.sealed_orders["2:movement_planning"]={"axis":OrderBatch(side=Side.AXIS,movement=[MovementOrder(ship_id=a.id,plan="2")]),"allies":OrderBatch(side=Side.ALLIES)}
    engine.advance(state.game_id)
    assert a.position is None and not a.sunk and state.score["axis"]==1
    assert any(e.type=="scenario_ship_exited" for e in state.events)
    state.turn=1;state.phase=Phase.GUNNERY
    light=OrderBatch(side=Side.AXIS,aircraft_illumination=[b.position])
    assert not night.validate(engine,state,light)
    night.prepare_gunnery(engine,state,[light])
    assert night.illuminated(state,b) and night.validate(engine,state,light)
    state.turn=4;state.phase=Phase.REINFORCEMENT
    state.scenario_state["savo_available_groups"]=["tulagi"]
    for sid in night.config(state)["savo"]["reinforcement_groups"]["tulagi"]["ships"]:
        ship=b.model_copy(deep=True);ship.id=sid;ship.position=None;state.ships[sid]=ship
    assert all(row["entry_hexes"] for row in savo.candidates(engine,state,Side.ALLIES))


def test_debug_formation_pagination_filters_before_limit(fixture,tmp_path):
    engine,state,a,b=fixture;repo=GameRepository(tmp_path/"paging.sqlite3")
    for index in range(15):
        ai_memory.record_trace(state,Side.AXIS,{"plan":{"unit_intents":{"wanted" if index%4==0 else "other":"test"}}})
    repo.save(state)
    first=repo.ai_debug(state.game_id,side="axis",limit=2,formation_id="wanted")
    second=repo.ai_debug(state.game_id,side="axis",before=first[-1]["id"],limit=2,formation_id="wanted")
    assert [e["id"] for e in first+second]==[13,9,5,1]
    assert repo.ai_debug(state.game_id,side="allies",formation_id="wanted")==[]
    repo.close()


@pytest.mark.parametrize("side", list(Side))
def test_classic_screen_fleet_can_continue_two_turns_without_hold_chain_collision(side):
    """Ayanami/Nagara/Shirayuki previously sealed an inescapable T2 chain.

    Exercise the public planner, validator and synchronous engine, rather
    than restating the planner's lookahead algorithm in a unit test.
    """
    from iron_bottom_sound.engine import ORDER_PHASES
    from iron_bottom_sound.realistic_command import RealisticCommander
    from iron_bottom_sound.tactical import PROFILES

    engine = IronBottomEngine()
    state = engine.reset("IBS-S-06", 1, GameOptions(
        ruleset_version="night-v2",
        optional_rules=OptionalRules(radar=True, star_shells=True,
            searchlights=True, squalls=True, smoke=True),
        squall_hexes=["TT20"],
    ))
    commanders = {
        side: RealisticCommander(PROFILES["rc_screen"]),
        side.opponent: RealisticCommander(PROFILES["balanced"]),
    }
    while state.turn <= 2 and state.phase != Phase.COMPLETE:
        if state.phase in ORDER_PHASES:
            for which in Side:
                _, batch, _ = commanders[which].choose_plan(engine, state.game_id, which)
                assert engine.submit_orders(state.game_id, batch).valid
        engine.advance(state.game_id)
    assert state.turn == 3
    assert not any(
        event.type == "collision_check"
        and len({state.ships[sid].side for sid in event.payload.get("ships", [])}) == 1
        for event in state.events
    )


@pytest.mark.parametrize("profile", ["rc_coordinated", "rc_t_hunter", "rc_torpedo_wings", "rc_screen", "rc_pincer"])
def test_each_state_machine_profile_protects_disabled_damaged_screen_with_smoke(fixture,profile):
    from iron_bottom_sound.tactical import PROFILES, TacticalCommander
    engine, state, ship, target = fixture
    ship.hull = 1
    for mount in ship.gun_mounts:
        mount.destroyed = True
    _, batch, _ = TacticalCommander(PROFILES[profile]).choose_plan(engine, state.game_id, ship.side)
    assert ship.id in batch.smoke_ships
    assert not any(order.ship_id == ship.id for order in batch.gunnery)
    assert engine.submit_orders(state.game_id, batch).valid
    engine.submit_orders(state.game_id, OrderBatch(side=ship.side.opponent))
    engine.advance(state.game_id)
    assert any(e.type == "smoke_released" and e.payload["ship_id"] == ship.id for e in state.events)
