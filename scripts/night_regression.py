"""Isolated, seeded night-v2 smoke matrix, not a strength benchmark."""
import argparse
import json
import time
from pathlib import Path

from iron_bottom_sound.engine import IronBottomEngine
from iron_bottom_sound.models import GameOptions, OptionalRules, Side
from iron_bottom_sound.realistic_command import RealisticCommander
from iron_bottom_sound.tactical import PROFILES
from iron_bottom_sound.engine import ORDER_PHASES


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--output",required=True)
    parser.add_argument("--turns",type=int,default=2)
    parser.add_argument("--mode",choices=("classic","realistic","both"),default="both")
    parser.add_argument("--scenarios",nargs="+",default=["04","06","08","10","FM-01"])
    parser.add_argument("--profiles",nargs="+",default=["rc_coordinated","rc_t_hunter","rc_torpedo_wings","rc_screen","rc_pincer"])
    parser.add_argument("--seeds",nargs="+",type=int,default=[1,13])
    args=parser.parse_args()
    results=[]
    cases=[(mode,scenario) for mode in (False,True) if args.mode=="both" or mode==(args.mode=="realistic") for scenario in args.scenarios]
    for realistic,scenario in cases:
        for profile in args.profiles:
            for seed in args.seeds:
                for side in Side:
                    engine=IronBottomEngine()
                    scenario_id="IBS-S-"+scenario
                    started=time.monotonic()
                    state=engine.reset(scenario_id,seed,GameOptions(ruleset_version="night-v2",realistic_command=realistic,
                        optional_rules=OptionalRules(radar=True,star_shells=True,searchlights=True,squalls=True,smoke=True),squall_hexes=["TT20"]))
                    result={"mode":"realistic" if realistic else "classic","scenario":scenario_id,"profile":profile,"seed":seed,"side":side.value,"turns":0,"phases":0,
                            "night_orders":{},"status":"passed"}
                    if state.scenario_state.get("rule_blockers"):
                        result.update(status="source_blocked",blockers=state.scenario_state["rule_blockers"])
                    else:
                        commanders={side:RealisticCommander(PROFILES[profile]),side.opponent:RealisticCommander(PROFILES["balanced"])}
                        try:
                            while state.turn<=args.turns and state.phase.value!="complete":
                                if state.phase in ORDER_PHASES:
                                    for which in Side:
                                        _,batch,_=commanders[which].choose_plan(engine,state.game_id,which)
                                        validation=engine.validate_orders(state.game_id,batch)
                                        if not validation.valid:
                                            raise ValueError(validation.errors)
                                        for key in ("illumination","searchlights","smoke_ships","torpedoes"):
                                            result["night_orders"][key]=result["night_orders"].get(key,0)+len(getattr(batch,key))
                                        engine.submit_orders(state.game_id,batch)
                                engine.advance(state.game_id)
                                result["phases"]+=1
                            result["turns"]=state.turn-1
                            result["friendly_collisions"]=sum(e.type=="collision_check" and len({state.ships[sid].side for sid in e.payload.get("ships",[])})==1 for e in state.events)
                            if result["friendly_collisions"]:
                                result.update(status="failed",error="friendly collision in seeded regression")
                        except (ValueError,KeyError,RuntimeError,StopIteration) as error:
                            result.update(status="failed",error=str(error),turn=state.turn,phase=state.phase.value)
                    result["elapsed_s"]=round(time.monotonic()-started,2)
                    results.append(result)
                    print(len(results),scenario_id,profile,seed,side.value,result["status"],result["elapsed_s"],flush=True)
                    Path(args.output).write_text(json.dumps({"kind":"two-turn legal smoke, NOT strength","results":results},ensure_ascii=False,indent=2),encoding="utf-8")


if __name__=="__main__":
    main()
