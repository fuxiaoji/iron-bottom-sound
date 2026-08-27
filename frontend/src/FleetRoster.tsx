import {useState} from "react";
import type {Ship,Side} from "./types";
import {hexLabel} from "./hexGeometry";

// 左侧「舰队总览」：简要列出双方所有可见舰船状况。
// 数据全部来自 view.ships（已按可见性过滤、owner-only 字段敌方为 null），
// 只读展示，不产生订单；行点击复用 App 的 onSelect 联动地图与右侧记录卡。
export function FleetRoster({ships,viewerSide,selectedId,onSelect}:{ships:Ship[];viewerSide:Side;selectedId?:string;onSelect:(ship:Ship)=>void}){
 const [open,setOpen]=useState<Record<Side,boolean>>({axis:true,allies:true});
 const groups:Side[]=["axis","allies"];
 return <section className="roster" aria-label="舰队总览">
  <h2>舰队总览</h2>
  {groups.map(sideKey=>{
   const list=ships.filter(ship=>ship.side===sideKey);
   const sunk=list.filter(ship=>ship.sunk).length;
   const own=sideKey===viewerSide;
   return <div key={sideKey} className="roster-group">
    <button className="roster-group-toggle" onClick={()=>setOpen(prev=>({...prev,[sideKey]:!prev[sideKey]}))} title={own?"我方舰船":"敌方舰船（可见部分）"}>
     <span className={`roster-side-dot ${sideKey}`}/>
     <b>{sideKey==="axis"?"轴心":"同盟"}{own?"（我方）":"（敌方）"}</b>
     <small>{list.length} 艘 · 沉没 {sunk}</small>
    </button>
    {open[sideKey]&&<div className="roster-rows">
     {list.map(ship=><div key={ship.id} className={`roster-row${ship.id===selectedId?" selected":""}${ship.sunk?" sunk":""}`} role="button" tabIndex={0} onClick={()=>onSelect(ship)} onKeyDown={event=>{if(event.key==="Enter"||event.key===" "){event.preventDefault();onSelect(ship)}}}>
      <div className="roster-row-head">
       <b>{ship.name}</b>
       <span className={`readiness ${ship.sunk?"bad":ship.fired?"fired":""}`}>{ship.sunk?"沉没":ship.fired?"已开火":"可行动"}</span>
      </div>
      <div className="roster-row-meta">
       <span>{ship.ship_type}</span>
       <span>{ship.position?hexLabel(ship.position):ship.sunk?"—":"?"}</span>
       <span>航向 {ship.heading||"?"}</span>
       <span>速 {ship.current_speed}</span>
       {ship.formation_id&&<span>编队 {ship.formation_id}</span>}
       {ship.command_status&&ship.command_status!=="attached"&&<span className="damage-chip flag">{ship.command_status==="retreating"?"自主撤退":ship.command_status==="withdrawn"?"已撤出":"正在脱队"}</span>}
       <span>{ship.hull!=null&&ship.max_hull!=null?`船体 ${ship.hull}/${ship.max_hull}`:"船体 ?"}</span>
       {ship.fire_markers>0&&<span className="damage-chip fire">起火×{ship.fire_markers}</span>}
      </div>
     </div>)}
    </div>}
   </div>;
  })}
 </section>;
}
