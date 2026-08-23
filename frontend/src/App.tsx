import {useEffect,useState} from "react";
import {advance,createGame,handoff,submitOrders,suggestedOrders,viewGame} from "./api";
import {HexMap} from "./HexMap";
import type {Observation,Ship,Side} from "./types";
import "./style.css";

const phaseNames:Record<string,string>={contact_setup:"隐蔽标记部署",reinforcement:"增援",movement_planning:"移动计划",torpedo_planning:"鱼雷计划",movement_resolution:"同步移动",gunnery:"炮击",torpedo_effects:"鱼雷效果",fire_end:"起火与回合结束",complete:"想定结束"};
const orderPhases=new Set(["contact_setup","reinforcement","movement_planning","torpedo_planning","gunnery"]);

function defaultBatch(view:Observation,side:Side){
 const own=view.ships.filter(ship=>ship.side===side&&!ship.sunk&&ship.position);
 return {
  side,phase:view.phase,reinforcements:[],contacts:[],contact_movement:[],
  movement:view.phase==="movement_planning"?own.map(ship=>({ship_id:ship.id,plan:"0"})):[],
  gunnery:[],torpedoes:[],smoke_ships:[],smoke:[],illumination:[],searchlights:[],confirmation:{ready:true}
 };
}

export default function App(){
 const [game,setGame]=useState<string>();const [view,setView]=useState<Observation>();const [side,setSide]=useState<Side>("axis");const [locked,setLocked]=useState(false);const [selected,setSelected]=useState<Ship>();const [error,setError]=useState("");const [draft,setDraft]=useState("");
 const refresh=async(id=game,s=side)=>{if(id)setView(await viewGame(id,s))};
 useEffect(()=>{let active=true;if(view&&game&&orderPhases.has(view.phase)){suggestedOrders(game,side).then(batch=>{if(active)setDraft(JSON.stringify(batch,null,2))}).catch(()=>{if(active)setDraft(JSON.stringify(defaultBatch(view,side),null,2))})}else setDraft("");return()=>{active=false}},[view,side,game]);
 const start=async(scenario_id:string)=>{try{const g=await createGame(scenario_id,1);setGame(g.game_id);setSide("axis");setView(await viewGame(g.game_id,"axis"));setError("")}catch(e){setError(String(e))}};
 const clearAndLock=async()=>{if(game)await handoff(game);setView(undefined);setSelected(undefined);setDraft("");setLocked(true)};
 const act=async()=>{if(!game||!view)return;try{
  if(orderPhases.has(view.phase)){
   const batch=JSON.parse(draft);const result=await submitOrders(game,side,batch);
   if(result.both_submitted)await advance(game);
   await clearAndLock();
  }else{await advance(game);await refresh()}
  setError("");
 }catch(e){setError(String(e))}};
 const unlock=async()=>{if(!game)return;const next:Side=side==="axis"?"allies":"axis";setSide(next);setView(await viewGame(game,next));setSelected(undefined);setLocked(false)};
 if(!game)return <main className="landing"><p className="eyebrow">AUDITABLE NAVAL WARGAME</p><h1>铁底湾的回响 IV</h1><p>确定性裁决 · 规则出处 · 同机交接</p><div className="scenario-grid"><button onClick={()=>start("IBS-S-03")}><b>想定 3</b><span>通道行动 · 4 回合</span></button><button onClick={()=>start("IBS-S-01")}><b>想定 1</b><span>埃斯佩兰斯角海战 · 7 回合</span></button></div>{error&&<pre>{error}</pre>}</main>;
 if(locked)return <main className="handoff"><div><p>上一方观察、草稿和选择已销毁</p><h1>请交给另一方</h1><button onClick={unlock}>确认无人旁观，进入 {side==="axis"?"同盟":"轴心"} 方</button></div></main>;
 if(!view)return null;
 return <main className="game"><header><div><p className="eyebrow">{view.scenario_id}</p><h1>{view.scenario_title}</h1></div><div className="turn">第 {view.turn}/{view.max_turns} 回合<br/><b>{phaseNames[view.phase]}</b></div><button onClick={act}>{orderPhases.has(view.phase)?"校验、封存并交接":"执行引擎裁决"}</button></header><section className="workspace"><HexMap ships={view.ships} onSelect={setSelected}/><aside><h2>{side==="axis"?"轴心":"同盟"}方观察</h2>{selected&&<article><h3>{selected.name}</h3><p>{selected.ship_type} · 航速 {selected.current_speed}</p><p>舰体 {selected.hull??"隐藏"}/{selected.max_hull??"隐藏"} · 火灾 {selected.fire_markers}</p></article>}{orderPhases.has(view.phase)&&<section className="order-editor"><h2>本阶段秘密订单</h2><p>已载入引擎验证过的合法起始订单；可编辑后提交，规则核心会再次严格校验。</p><textarea aria-label="本阶段秘密订单 JSON" value={draft} onChange={event=>setDraft(event.target.value)} spellCheck={false}/></section>}<h2>裁决日志</h2><ol className="events">{[...view.recent_events].reverse().map(e=><li key={e.sequence}><span>T{e.turn} · {phaseNames[e.phase]}</span>{e.message}{e.dice&&<small>{e.dice.notation}: {e.dice.raw}{e.dice.adjusted!==undefined&&` → ${e.dice.adjusted}`}</small>}{e.rule&&<code>{e.rule.rule_id} · p.{e.rule.pdf_page}</code>}</li>)}</ol></aside></section>{error&&<div className="error">{error}</div>}</main>;
}
