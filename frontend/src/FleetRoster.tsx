import {useState} from "react";
import type {Formation,Ship,Side} from "./types";
import {hexLabel} from "./hexGeometry";

// 左侧「舰队总览」：简要列出双方所有可见舰船状况。
// 数据全部来自 view.ships（已按可见性过滤、owner-only 字段敌方为 null），
// 只读展示，不产生订单；行点击复用 App 的 onSelect 联动地图与右侧记录卡。
export function FleetRoster({ships,formations,viewerSide,selectedId,onSelect}:{ships:Ship[];formations:Formation[];viewerSide:Side;selectedId?:string;onSelect:(ship:Ship)=>void}){
 const [open,setOpen]=useState<Record<string,boolean>>({axis:true,allies:true});
 const groups:Side[]=["axis","allies"];
 const shipRow=(ship:Ship)=><div key={ship.id} className={`roster-row${ship.id===selectedId?" selected":""}${ship.sunk?" sunk":""}`} role="button" tabIndex={0} onClick={()=>onSelect(ship)} onKeyDown={event=>{if(event.key==="Enter"||event.key===" "){event.preventDefault();onSelect(ship)}}}>
  <div className="roster-row-head">
   <b>{ship.name}</b>
   <span className={`readiness ${ship.sunk?"bad":ship.fired?"fired":""}`}>{ship.sunk?"沉没":ship.fired?"已开火":"可行动"}</span>
  </div>
  <div className="roster-row-meta">
   <span>{ship.ship_type}</span><span>{ship.position?hexLabel(ship.position):ship.sunk?"—":"?"}</span><span>航向 {ship.heading||"?"}</span><span>速 {ship.current_speed}</span>
   {ship.command_status&&ship.command_status!=="attached"&&<span className="damage-chip flag">{ship.command_status==="retreating"?"自主撤退":ship.command_status==="withdrawn"?"已撤出":"正在脱队"}</span>}
   <span>{ship.hull!=null&&ship.max_hull!=null?`船体 ${ship.hull}/${ship.max_hull}`:"船体 ?"}</span>
   {ship.fire_markers>0&&<span className="damage-chip fire">起火×{ship.fire_markers}</span>}
  </div>
 </div>;
 return <section className="roster" aria-label="舰队总览">
  <h2>舰队与编队状态</h2>
  {groups.map(sideKey=>{
   const list=ships.filter(ship=>ship.side===sideKey);
   const sunk=list.filter(ship=>ship.sunk).length;
   const own=sideKey===viewerSide;
   const sideFormations=own?formations.filter(formation=>formation.side===sideKey):[];
   const assigned=new Set(sideFormations.flatMap(formation=>formation.ship_ids));
   const detached=list.filter(ship=>!assigned.has(ship.id)||ship.command_status!=="attached");
   return <div key={sideKey} className="roster-group">
    <button className="roster-group-toggle" onClick={()=>setOpen(prev=>({...prev,[sideKey]:!prev[sideKey]}))} title={own?"我方舰船":"敌方舰船（可见部分）"}>
     <span className={`roster-side-dot ${sideKey}`}/>
     <b>{sideKey==="axis"?"轴心":"同盟"}{own?"（我方）":"（敌方）"}</b>
     <small>{list.length} 艘 · 沉没 {sunk}</small>
    </button>
    {open[sideKey]&&<div className="roster-rows">{sideFormations.length>0?<>
     {sideFormations.map(formation=>{const formationShips=list.filter(ship=>formation.ship_ids.includes(ship.id)&&ship.command_status==="attached");const key=`formation:${formation.id}`;return <section className="roster-formation" key={formation.id}>
      <button className="roster-formation-toggle" onClick={()=>setOpen(prev=>({...prev,[key]:prev[key]===false}))}>
       <b>{formation.name}</b><small>{formationShips.length} 艘 · 间距 {formation.spacing} 格</small><span>{formation.status==="command_disrupted"?"指挥中断":formation.status==="dissolved"?"已解散":"编队完整"}</span>
      </button>
      <div className="formation-command-strip"><span>领舰：{ships.find(ship=>ship.id===formation.leader_id)?.name??"—"}</span><span>旗舰：{ships.find(ship=>ship.id===formation.flagship_id)?.name??"—"}</span><span>备用：{ships.find(ship=>ship.id===formation.reserve_flagship_id)?.name??"—"}</span></div>
      {open[key]!==false&&formationShips.map(ship=><div className="formation-ship" key={ship.id}><span className="formation-role">{ship.id===formation.leader_id?"领":ship.id===formation.flagship_id?"旗":ship.id===formation.reserve_flagship_id?"备":"·"}</span>{shipRow(ship)}</div>)}
     </section>})}
     {detached.length>0&&<section className="roster-formation detached"><div className="roster-formation-toggle static"><b>脱队／直属舰</b><small>{detached.length} 艘</small></div>{detached.map(ship=>shipRow(ship))}</section>}
    </>:list.map(ship=>shipRow(ship))}</div>}
   </div>;
  })}
 </section>;
}
