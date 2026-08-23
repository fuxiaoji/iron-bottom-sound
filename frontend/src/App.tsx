import {useState} from "react";
import {advance,createGame,handoff,submitStanding,viewGame} from "./api";
import {HexMap} from "./HexMap";
import type {Observation,Ship,Side} from "./types";
import "./style.css";
const phaseNames:Record<string,string>={reinforcement:"增援",movement_planning:"移动计划",torpedo_planning:"鱼雷计划",movement_resolution:"同步移动",gunnery:"炮击",torpedo_effects:"鱼雷效果",fire_end:"起火与回合结束",complete:"想定结束"};
export default function App(){
 const [game,setGame]=useState<string>();const [view,setView]=useState<Observation>();const [side,setSide]=useState<Side>("axis");const [locked,setLocked]=useState(false);const [selected,setSelected]=useState<Ship>();const [error,setError]=useState("");
 const refresh=async(id=game,s=side)=>{if(id)setView(await viewGame(id,s))};
 const start=async(scenario_id:string)=>{try{const g=await createGame(scenario_id,1);setGame(g.game_id);setSide("axis");setView(await viewGame(g.game_id,"axis"));}catch(e){setError(String(e))}};
 const act=async()=>{if(!game||!view)return;try{if(view.phase==="movement_planning"){await submitStanding(game,side,view.ships.filter(s=>s.side===side&&!s.sunk).map(s=>s.id));await handoff(game);setView(undefined);setSelected(undefined);setLocked(true)}else{await advance(game);await refresh()}}catch(e){setError(String(e))}};
 const unlock=async()=>{if(!game)return;const next:Side=side==="axis"?"allies":"axis";setSide(next);setView(await viewGame(game,next));setLocked(false)};
 if(!game)return <main className="landing"><p className="eyebrow">AUDITABLE NAVAL WARGAME</p><h1>铁底湾的回响 IV</h1><p>确定性裁决 · 规则出处 · 同机交接</p><div className="scenario-grid"><button onClick={()=>start("IBS-S-03")}><b>想定 3</b><span>通道行动 · 4 回合</span></button><button onClick={()=>start("IBS-S-01")}><b>想定 1</b><span>埃斯佩兰斯角海战 · 7 回合</span></button></div>{error&&<pre>{error}</pre>}</main>;
 if(locked)return <main className="handoff"><div><p>本方情报已从界面清除</p><h1>请交给另一方</h1><button onClick={unlock}>确认无人旁观，进入 {side==="axis"?"同盟":"轴心"} 方</button></div></main>;
 if(!view)return null;
 return <main className="game"><header><div><p className="eyebrow">{view.scenario_id}</p><h1>{view.scenario_title}</h1></div><div className="turn">第 {view.turn}/{view.max_turns} 回合<br/><b>{phaseNames[view.phase]}</b></div><button onClick={act}>{view.phase==="movement_planning"?"封存本方停止计划":"推进阶段"}</button></header><section className="workspace"><HexMap ships={view.ships} onSelect={setSelected}/><aside><h2>{side==="axis"?"轴心":"同盟"}方观察</h2>{selected&&<article><h3>{selected.name}</h3><p>{selected.ship_type} · 航速 {selected.current_speed}</p><p>舰体 {selected.hull??"隐藏"}/{selected.max_hull??"隐藏"} · 火灾 {selected.fire_markers}</p></article>}<h2>裁决日志</h2><ol className="events">{[...view.recent_events].reverse().map(e=><li key={e.sequence}><span>T{e.turn} · {phaseNames[e.phase]}</span>{e.message}{e.dice&&<small>{e.dice.notation}: {e.dice.raw}{e.dice.adjusted!==undefined&&` → ${e.dice.adjusted}`}</small>}{e.rule&&<code>{e.rule.rule_id} · p.{e.rule.pdf_page}</code>}</li>)}</ol></aside></section>{error&&<div className="error">{error}</div>}</main>
}
