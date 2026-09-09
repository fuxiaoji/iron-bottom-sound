import {useEffect,useState} from "react";
import {replayCheckpoints,replayView} from "./api";
import type {ReplayCheckpoint} from "./api";
import {HexMap} from "./HexMap";
import type {Observation,Side} from "./types";

const phaseNames:Record<string,string>={formation_setup:"编队初设",contact_setup:"隐蔽标记部署",reinforcement:"增援",movement_planning:"移动计划",torpedo_planning:"鱼雷计划",movement_resolution:"同步移动",gunnery:"炮击",torpedo_effects:"鱼雷效果",fire_end:"起火与回合结束",complete:"想定结束"};

export function ReplayModal({game,side,onClose}:{game:string;side:Side;onClose:()=>void}){
 const [checkpoints,setCheckpoints]=useState<ReplayCheckpoint[]>([]);
 const [index,setIndex]=useState(0);
 const [view,setView]=useState<Observation>();
 const [error,setError]=useState("");
 useEffect(()=>{let live=true;replayCheckpoints(game).then(items=>{if(!live)return;setCheckpoints(items);setIndex(Math.max(0,items.length-1))}).catch(e=>setError(String(e)));return()=>{live=false}},[game]);
 useEffect(()=>{const checkpoint=checkpoints[index];if(!checkpoint)return;let live=true;replayView(game,side,checkpoint.sequence).then(result=>{if(live){setView(result.view);setError("")}}).catch(e=>{if(live)setError(String(e))});return()=>{live=false}},[game,side,checkpoints,index]);
 const checkpoint=checkpoints[index];
 return <div className="replay-backdrop" role="dialog" aria-modal="true" aria-label="对局复盘">
  <section className="replay-modal">
   <header><div><p className="eyebrow">AFTER ACTION REPLAY</p><h2>对局复盘 · {side==="axis"?"轴心":"同盟"}视角</h2></div><button onClick={onClose}>返回战局</button></header>
   {checkpoint&&<div className="replay-controls"><button disabled={index===0} onClick={()=>setIndex(value=>value-1)}>← 上一步</button><label><span>第 {index+1}/{checkpoints.length} 个存档点</span><input type="range" min={0} max={Math.max(0,checkpoints.length-1)} value={index} onChange={event=>setIndex(Number(event.target.value))}/></label><button disabled={index===checkpoints.length-1} onClick={()=>setIndex(value=>value+1)}>下一步 →</button><b>第 {checkpoint.turn} 回合 · {phaseNames[checkpoint.phase]??checkpoint.phase}</b></div>}
   {view&&<div className="replay-body"><div className="replay-map"><HexMap dims={view} ships={view.ships} torpedoTracks={view.torpedo_tracks} markers={view.markers} onSelect={()=>undefined} viewerSide={side} visibility={view.visibility}/></div><aside><h3>截至此刻的裁决</h3><ol className="events">{[...view.recent_events].reverse().map(event=><li key={event.sequence}><span>#{event.sequence} · T{event.turn} · {phaseNames[event.phase]}</span>{event.message}{event.rule&&<code>{event.rule.rule_id} · p.{event.rule.pdf_page}</code>}</li>)}</ol></aside></div>}
   {!checkpoints.length&&!error&&<p className="replay-empty">正在读取复盘快照…</p>}
   {error&&<div className="error">{error}</div>}
  </section>
 </div>;
}
