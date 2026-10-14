"""Controlled provider responses: no network credentials or live model claims."""
from copy import deepcopy
import json
import httpx
import pytest
from fastapi.testclient import TestClient
from iron_bottom_sound import api, ai_memory
from iron_bottom_sound.engine import IronBottomEngine
from iron_bottom_sound.llm import OpenAICompatibleCommander
from iron_bottom_sound.models import GameOptions, Side, Phase
from iron_bottom_sound.realistic_command import RealisticCommander
from iron_bottom_sound.storage import GameRepository
from iron_bottom_sound.savegame import build_save_bundle, validate_save_bundle, clone_imported_game


@pytest.mark.parametrize("realistic",[False,True])
def test_llm_retry_accept_results_restart_export_and_new_game(realistic,tmp_path,monkeypatch):
    engine=IronBottomEngine();repo=GameRepository(tmp_path/"llm.sqlite3")
    monkeypatch.setattr(api,"engine",engine);monkeypatch.setattr(api,"repository",repo)
    state=engine.reset("IBS-S-03",options=GameOptions(ruleset_version="night-v2",mode="llm",realistic_command=realistic))
    deterministic=RealisticCommander();calls=[]
    def handler(request):
        calls.append(json.loads(request.content))
        plan,_,_=deterministic.choose_plan(engine,state.game_id,Side.ALLIES)
        value=plan.model_dump(mode="json")
        if len(calls)==1:
            value["orders"]["side"]="axis"
        return httpx.Response(200,json={"choices":[{"message":{"content":json.dumps(value),"reasoning_content":"PRIVATE-MODEL-REASONING"}}]})
    commander=OpenAICompatibleCommander(api_key="fixture-only-secret",client=httpx.Client(transport=httpx.MockTransport(handler)))
    monkeypatch.setattr(api,"llm_commander_factory",lambda **kwargs:commander)
    client=TestClient(api.app)
    steps=4 if realistic else 3
    from iron_bottom_sound.engine import ORDER_PHASES
    for step in range(steps):
        _,batch,_=deterministic.choose_plan(engine,state.game_id,Side.AXIS)
        assert engine.submit_orders(state.game_id,batch).valid
        response=client.post(f"/games/{state.game_id}/llm-opponent",headers={"X-Player-Side":"axis"},json={"api_key":"fixture-only-secret"})
        assert response.status_code==200,response.text
        revision=state.ai_memory["allies"]["revision"]
        assert client.post(f"/games/{state.game_id}/llm-opponent",headers={"X-Player-Side":"axis"},json={"api_key":"fixture-only-secret"}).status_code==200
        assert state.ai_memory["allies"]["revision"]==revision
        engine.advance(state.game_id);repo.save(state)
        while state.phase not in ORDER_PHASES and state.phase!=Phase.COMPLETE:
            engine.advance(state.game_id);repo.save(state)
    assert state.ai_memory["allies"]["revision"]==steps and not state.ai_memory.get("axis")
    first=repo.ai_debug(state.game_id,side="allies")[-1]
    assert len(first["details"]["attempts"])==2
    assert first["details"]["attempts"][0]["errors"] and not first["details"]["attempts"][0]["valid"]
    assert first["details"]["attempts"][1]["valid"] and "elapsed_ms" in first["details"]["attempts"][1]
    assert first.get("execution_memory") and state.ai_memory["allies"]["results"]
    if realistic:
        assert state.ai_memory["allies"].get("formations")
    assert "PRIVATE-MODEL-REASONING" not in state.model_dump_json()
    assert "fixture-only-secret" not in state.model_dump_json()
    assert "ai_memory" not in engine.observe(state.game_id,Side.AXIS).model_dump()
    assert not client.get(f"/games/{state.game_id}/ai-memory").is_success
    assert client.get(f"/games/{state.game_id}/ai-memory?debug=true&side=allies").is_success
    assert client.get(f"/games/{state.game_id}/battle-report").status_code==409
    assert client.get(f"/games/{state.game_id}/battle-report.md").status_code==409
    memory_before=deepcopy(state.ai_memory)
    commander.choose_plan(engine,state.game_id,Side.ALLIES)  # Guidance is read-only.
    assert state.ai_memory==memory_before
    assert json.loads(calls[-1]["messages"][-1]["content"])["same_game_memory"]==ai_memory.prompt_memory(state,Side.ALLIES)
    bundle=build_save_bundle(repo,state);loaded,snapshots=validate_save_bundle(bundle)
    copied,snapshots=clone_imported_game(loaded,snapshots);repo.import_game(copied,snapshots)
    restarted=repo.load(copied.game_id)
    assert restarted.ai_memory==state.ai_memory and restarted.rule_snapshot==state.rule_snapshot
    assert len(repo.ai_debug(copied.game_id,side="allies"))==steps
    engine.games[copied.game_id]=copied
    # The portable journal can be longer than the engine's rolling debug cache.
    copied.ai_traces=copied.ai_traces[-32:]
    assert engine.replay(copied.game_id).model_dump()==copied.model_dump()
    assert not engine.reset("IBS-S-03",options=GameOptions(ruleset_version="night-v2")).ai_memory
    repo.close()


def test_timeout_three_attempts_records_failure_without_committing_memory(tmp_path,monkeypatch):
    engine=IronBottomEngine();repo=GameRepository(tmp_path/"timeout.sqlite3")
    monkeypatch.setattr(api,"engine",engine);monkeypatch.setattr(api,"repository",repo)
    state=engine.reset("IBS-S-03",options=GameOptions(ruleset_version="night-v2",mode="llm"))
    _,batch,_=RealisticCommander().choose_plan(engine,state.game_id,Side.AXIS);engine.submit_orders(state.game_id,batch)
    def handler(request):
        raise httpx.ReadTimeout("fixture timeout",request=request)
    commander=OpenAICompatibleCommander(api_key="fixture-key",client=httpx.Client(transport=httpx.MockTransport(handler)))
    monkeypatch.setattr(api,"llm_commander_factory",lambda **kwargs:commander)
    response=TestClient(api.app).post(f"/games/{state.game_id}/llm-opponent",headers={"X-Player-Side":"axis"},json={"api_key":"fixture-key"})
    assert response.status_code==409
    assert not state.ai_memory and "allies" not in state.submitted_orders
    trace=repo.ai_debug(state.game_id,side="allies")[0]
    assert trace["status"]=="rejected" and len(trace["details"]["attempts"])==3
    assert all(a["errors"]==["ReadTimeout"] and "elapsed_ms" in a for a in trace["details"]["attempts"])
    assert engine.replay(state.game_id).model_dump() == state.model_dump()
    assert engine.replay(state.events).model_dump() == state.model_dump()
    assert any(e.type == 'ai_decision_rejected' for e in state.events)
    assert 'ai_decision_rejected' not in engine.observe(state.game_id, Side.AXIS).model_dump_json()
    repo.close()


def test_early_night_rejected_audit_cache_is_preserved_without_inventing_events():
    engine = IronBottomEngine()
    state = engine.reset('IBS-S-03', options=GameOptions(ruleset_version='night-v2'))
    ai_memory.record_trace(state, Side.ALLIES, {'status': 'rejected', 'error': 'ReadTimeout'})
    events_before = state.model_dump()['events']
    assert engine.replay(state.game_id).model_dump() == state.model_dump()
    assert state.model_dump()['events'] == events_before
    assert not state.ai_memory  # Receipt preservation cannot promote failed plans.


def test_night_snapshot_replay_uses_frozen_parameters_and_resumes_rng(tmp_path):
    from iron_bottom_sound.engine import ORDER_PHASES
    engine=IronBottomEngine();state=engine.reset("IBS-S-06",seed=13,options=GameOptions(ruleset_version="night-v2"))
    commander=RealisticCommander()
    while state.turn==1:
        if state.phase in ORDER_PHASES:
            for side in Side:
                _,batch,_=commander.choose_plan(engine,state.game_id,side)
                assert engine.submit_orders(state.game_id,batch).valid
        engine.advance(state.game_id)
    resumed=IronBottomEngine();resumed.games[state.game_id]=state.model_copy(deep=True)
    frozen=deepcopy(state.rule_snapshot)
    resumed._base_rules.modifiers["optional"]["through_smoke"]=999
    while state.turn==2:
        if state.phase in ORDER_PHASES:
            for side in Side:
                _,left,_=commander.choose_plan(engine,state.game_id,side)
                _,right,_=commander.choose_plan(resumed,state.game_id,side)
                assert left==right
                engine.submit_orders(state.game_id,left);resumed.submit_orders(state.game_id,right)
        engine.advance(state.game_id);resumed.advance(state.game_id)
    assert state.model_dump()==resumed.get(state.game_id).model_dump()
    assert state.rule_snapshot==frozen
    replayed=engine.replay(state.game_id)
    assert replayed.model_dump()==state.model_dump()


def test_accepted_memory_and_upgrade_copy_have_deterministic_event_replay(tmp_path,monkeypatch):
    from iron_bottom_sound.models import OrderBatch
    engine=IronBottomEngine();repo=GameRepository(tmp_path/"upgrade.sqlite3")
    monkeypatch.setattr(api,"engine",engine);monkeypatch.setattr(api,"repository",repo)
    state=engine.reset("IBS-S-03",options=GameOptions(ruleset_version="night-v2"))
    for side in Side:
        batch=OrderBatch(side=side)
        engine.submit_orders(state.game_id,batch);ai_memory.accepted(engine,state,side,None,batch)
    engine.advance(state.game_id)
    assert engine.replay(state.game_id).model_dump()==state.model_dump()
    assert not any(e.type=="ai_decision_accepted" for e in engine.observe(state.game_id,Side.AXIS).recent_events)
    assert "initial_state" not in engine.observe(state.game_id,Side.AXIS).model_dump_json()
    old=engine.reset("IBS-S-03");repo.save(old)
    response=TestClient(api.app).post(f"/games/{old.game_id}/upgrade-copy")
    assert response.status_code==201
    copied=engine.get(response.json()["game_id"])
    assert engine.replay(copied.game_id).model_dump()==copied.model_dump()
    assert "upgrade_state" not in engine.observe(copied.game_id,Side.AXIS).model_dump_json()
    repo.close()
