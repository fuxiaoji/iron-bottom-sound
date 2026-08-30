import {useEffect,useRef,useState} from "react";
import {movementPreview} from "./api";
import {HexMap} from "./HexMap";
import {hexDistance,hexLabel} from "./hexGeometry";
import type {HexCoord,MovementPreview,Observation,Ship,Side} from "./types";

type PostBody={commands?:string[];hexes?:HexCoord[]};

// 逐格推进编辑器：点击相邻格推进、Q/E/A/D 调舰首、拖拽棋子画路径、Backspace 回退。
// 每一步都调用引擎只读 movement-preview 取回快照；确认时把 plan+cost 写回草稿。
export function HexMoveEditor({game,side,view,ship,onSelect,onCommit,onExit,showVisibility=false}:{
 game:string;side:Side;view:Observation;ship:Ship;
 onSelect:(ship:Ship)=>void;
 onCommit:(plan:string,speed:number)=>void;
 onExit:()=>void;
 showVisibility?:boolean;
}){
 const [history,setHistory]=useState<MovementPreview[]>([]);
 const [loading,setLoading]=useState(false);
 const [error,setError]=useState("");
 const [notice,setNotice]=useState("");
 const step=history[history.length-1];
 // 键盘/拖拽回调经 ref 桥接，避免闭包捕获过期 state。
 const stepRef=useRef<MovementPreview|undefined>(step);
 const postRef=useRef<(body:PostBody)=>Promise<void>>(async()=>{});
 const undoRef=useRef<()=>void>(()=>{});
 const commitRef=useRef<()=>void>(()=>{});
 const exitRef=useRef<()=>void>(onExit);
 stepRef.current=step;
 exitRef.current=onExit;

 const post=async(body:PostBody)=>{
  setLoading(true);setError("");setNotice("");
  try{
   const preview=await movementPreview(game,side,{ship_id:ship.id,...body});
   setHistory(current=>[...current,preview]);
   if(!preview.valid&&preview.errors.length>0)setError(preview.errors.join("；"));
  }catch(e){setError(String(e))}finally{setLoading(false)}
 };
 const undo=()=>{
  if(history.length<=1){onExit();return}
  setHistory(current=>current.slice(0,-1));
 };
 const commit=()=>{if(step?.commitable)onCommit(step.plan,step.cost)};
 postRef.current=post;
 undoRef.current=undo;
 commitRef.current=commit;

 // 首帧取空计划快照（同时下发可达格叠加）。
 useEffect(()=>{post({commands:[]})},[ship.id]);
 // 按键：Q/E=±60°、A/D=±120°（仅当引擎允许追加）、Backspace/U=回退、Enter=确认、Esc=退出。
 useEffect(()=>{
  const onKey=(event:KeyboardEvent)=>{
   const target=event.target as HTMLElement|null;
   if(target&&["INPUT","TEXTAREA","SELECT"].includes(target.tagName))return;
   const current=stepRef.current;
   const turns=current?.next_options.turns??[];
   const legal=(action:string)=>turns.some(turn=>turn.action===action&&turn.legal);
   const push=(action:string)=>postRef.current({commands:[...(current?.commands??[]),action]});
   switch(event.key){
    case "q":case "Q":if(legal("turn_port_60"))push("turn_port_60");break;
    case "e":case "E":if(legal("turn_starboard_60"))push("turn_starboard_60");break;
    case "a":case "A":if(legal("turn_port_120"))push("turn_port_120");break;
    case "d":case "D":if(legal("turn_starboard_120"))push("turn_starboard_120");break;
    case "Backspace":case "u":case "U":event.preventDefault();undoRef.current();break;
    case "Enter":if(current?.commitable)commitRef.current();break;
    case "Escape":event.preventDefault();exitRef.current();break;
   }
  };
  window.addEventListener("keydown",onKey);
  return()=>window.removeEventListener("keydown",onKey);
 },[]);

 const onHexClick=(hex:HexCoord)=>{
  if(!step?.current_hex)return;
  if(hexDistance(step.current_hex,hex)!==1){setNotice("只能逐格点击相邻格；先用 Q/E/A/D 调舰首，或拖拽棋子画整段路径。");return}
  post({commands:step.commands,hexes:[hex]});
 };
 const onDragPath=(path:HexCoord[])=>{
  if(path.length===0||!stepRef.current)return;
  post({commands:stepRef.current.commands,hexes:path});
 };

 if(!step){
  return <div className="map-frame move-loading"><p>正在读取可达格……</p></div>;
 }
 const turns=step.next_options.turns.filter(turn=>turn.legal);
 const advance=step.next_options.advance[0]?.label;
 const turnLabel=(action:string)=>action==="turn_port_60"?"左转60°":action==="turn_starboard_60"?"右转60°":action==="turn_port_120"?"左转120°":"右转120°";
 return <div className="move-editor">
  <HexMap ships={view.ships} torpedoTracks={view.torpedo_tracks} markers={view.markers} onSelect={onSelect} viewerSide={side} visibility={view.visibility} showVisibility={showVisibility}
   moveMode={{shipId:ship.id,reachable:step.reachable,currentHex:step.current_hex??{q:0,r:0},currentHeading:step.current_heading??ship.heading,nextAdvance:step.next_options.advance[0]?.hex??null,trajectory:step.trajectory,onHexClick,onDragPath}}/>
  <aside className="move-editor-panel">
   <b>{ship.name}</b> · 舰首 {step.current_heading??"?"} · 当前 {step.current_label??"—"}
   <div className="move-plan">航路 <code>{step.plan}</code> · {step.cost} MF · 合法区间 {step.min_cost}–{step.max_cost} MF{!step.valid&&<span className="move-invalid">非法</span>}</div>
   <div className="move-hints">下一步：{advance??"—"}{turns.length>0&&` · ${turns.map(turn=>turnLabel(turn.action)).join(" / ")}`}</div>
   <div className="move-keys">点击相邻格推进 1 格 · 拖拽棋子画路径 · Q/E 转 60° · A/D 转 120° · Backspace 回退 · Enter 确认 · Esc 退出</div>
   {loading&&<div className="move-loading-note">计算中…</div>}
   {error&&<div className="move-error">{error}</div>}
   {notice&&<div className="move-notice">{notice}</div>}
   <div className="move-actions">
    <button type="button" onClick={undo} disabled={history.length<=1}>回退</button>
    <button type="button" data-tutorial="movement-confirm" onClick={commit} disabled={!step.commitable} className={step.commitable?"ready":""}>确认 {step.plan}</button>
    <button type="button" onClick={onExit}>退出</button>
   </div>
  </aside>
 </div>;
}
