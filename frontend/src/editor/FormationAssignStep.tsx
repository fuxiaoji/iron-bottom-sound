// 剧本工坊第 2 步：把本侧舰船拖进「编队井」。散舰托盘的棋子可拖入任一井（追加到队尾），
// 井内用 ◀▶ 调整领舰次序、可把某舰拆成新队、可整队并入上一队。领舰恒为 index0。
import {useState} from "react";
import type {Side} from "../types";
import {counterAssetUrl} from "../assets";
import {MAX_WELLS_PER_SIDE,shipById,sideLabel} from "./scenario";
import type {EditorColumn,EditorState} from "./scenario";

const DND_SHIP="text/x-ibs-ship-id";

function chipLabel(id:string,state:EditorState){
 const ship=shipById(state,id);
 return ship?`${ship.name} · ${ship.ship_type}`:id;
}

export function FormationAssignStep({side,state,onMoveShip,onSplit,onMergeUp,onAutoAssign,onPairWell,onReorder,onPatch,onFlag}:{
 side:Side;
 state:EditorState;
 onMoveShip:(shipId:string,targetColumnId:string|null)=>void;
 onSplit:(columnId:string,shipId:string)=>void;
 onMergeUp:(columnId:string)=>void;
 onAutoAssign:()=>void;
 onPairWell:(leadId:string,followerId:string)=>void;
 onReorder:(columnId:string,shipId:string,direction:-1|1)=>void;
 onPatch:(columnId:string,patch:Partial<EditorColumn>)=>void;
 onFlag:(columnId:string,field:"flagshipId"|"reserveId",shipId:string)=>void;
}){
 const [dragging,setDragging]=useState<string|null>(null);
 const columns=state.columns[side];
 const solo=columns.filter(column=>column.shipIds.length===1);
 const wells=columns.filter(column=>column.shipIds.length>=2);
 const shipCount=columns.reduce((total,column)=>total+column.shipIds.length,0);
 const overLimit=wells.length>MAX_WELLS_PER_SIDE;

 const readShip=(event:React.DragEvent)=>{const value=event.dataTransfer.getData(DND_SHIP);return value||null};
 const dropAt=(handler:(shipId:string)=>void)=>(event:React.DragEvent)=>{
  event.preventDefault();
  const shipId=readShip(event);
  if(shipId)handler(shipId);
  setDragging(null);
 };

 return <div className={`formation-assign ${side}`}>
  <div className="editor-side-head"><h3>{sideLabel(side)}方 · {shipCount}艘</h3>
   <div className="editor-head-actions">
    <button className="quiet" onClick={()=>{if(solo.length>=2)onPairWell(solo[0].shipIds[0],solo[1].shipIds[0])}}
      disabled={solo.length<2||wells.length>=MAX_WELLS_PER_SIDE}
      title="用最先两艘散舰开一列新编队（也可直接把一艘散舰拖到另一艘上）">＋ 新建分队</button>
    <button className="quiet" onClick={onAutoAssign} title="清空分组，全舰合并成一列">自动合并成一路纵队</button>
   </div>
  </div>
  {overLimit&&<p className="editor-inline-warning">编队超过 {MAX_WELLS_PER_SIDE} 队，真实编队模式每侧最多 {MAX_WELLS_PER_SIDE} 队；把多出的队「并入上一队」。</p>}

  <div className="solo-tray" onDragOver={event=>event.preventDefault()} onDrop={dropAt(shipId=>onMoveShip(shipId,null))}>
   <span className="solo-tray-title">散舰托盘<small>（拖入下方编队井归队；拖到另一艘散舰上＝开一列新分队；井内「拆出」会回到这里）</small></span>
   <div className="solo-tray-chips">{solo.length===0?<em className="empty-hint">没有散舰——每艘舰都已归入编队。</em>
    :solo.map(column=>{const shipId=column.shipIds[0];const ship=shipById(state,shipId);if(!ship)return null;
     return <span key={column.columnId} className="ship-chip solo" draggable
       onDragStart={event=>{event.dataTransfer.setData(DND_SHIP,shipId);event.dataTransfer.effectAllowed="move";setDragging(shipId)}}
       onDragEnd={()=>setDragging(null)}
       onDragOver={event=>event.preventDefault()}
       onDrop={event=>{event.preventDefault();event.stopPropagation();const dragged=readShip(event);if(dragged&&dragged!==shipId)onPairWell(shipId,dragged);setDragging(null)}}>
      {ship.asset&&<img src={counterAssetUrl(ship.asset)} alt=""/>}<b>{ship.name}</b></span>;})}
   </div>
  </div>

  <div className="formation-wells">{wells.length===0?<em className="empty-hint">本侧还没有 ≥2 艘的编队。</em>
   :wells.map(column=>{
    const canMerge=columns.findIndex(item=>item.columnId===column.columnId)>0;
    return <section className={`formation-well ${dragging?"drag-live":""}`} key={column.columnId}
      onDragOver={event=>{event.preventDefault();event.dataTransfer.dropEffect="move"}}
      onDrop={dropAt(shipId=>onMoveShip(shipId,column.columnId))}>
     <header>
      <input className="well-name" value={column.name} maxLength={40} onChange={event=>onPatch(column.columnId,{name:event.target.value})} aria-label="编队名称"/>
      <span className="well-count">{column.shipIds.length}艘</span>
      <button className="well-action" onClick={()=>onPatch(column.columnId,{spacing:column.spacing===1?2:1})} title="切换列间距">间距 {column.spacing}</button>
      <button className="well-action" onClick={()=>onMergeUp(column.columnId)} disabled={!canMerge} title="并入上一队">并入上一队</button>
     </header>
     <div className="well-controls">
      <label>航向<select value={column.heading} onChange={event=>onPatch(column.columnId,{heading:Number(event.target.value)})}>{[1,2,3,4,5,6].map(h=><option key={h} value={h}>{h}</option>)}</select></label>
      <label>领舰<b className="well-leader-label">{chipLabel(column.shipIds[0],state)}</b></label>
      <label>旗舰<select value={column.flagshipId} onChange={event=>onFlag(column.columnId,"flagshipId",event.target.value)}>{column.shipIds.map(id=><option key={id} value={id}>{chipLabel(id,state)}</option>)}</select></label>
      <label>备用旗舰<select value={column.reserveId} onChange={event=>onFlag(column.columnId,"reserveId",event.target.value)}>{column.shipIds.filter(id=>id!==column.flagshipId).map(id=><option key={id} value={id}>{chipLabel(id,state)}</option>)}</select></label>
     </div>
     <div className="well-chips">{column.shipIds.map((shipId,index)=>{
      const role=shipId===column.flagshipId?"旗":shipId===column.reserveId?"备":index===0?"领":"";
      return <span key={shipId} className={`well-chip${index===0?" leader":""}`} draggable
        onDragStart={event=>{event.dataTransfer.setData(DND_SHIP,shipId);event.dataTransfer.effectAllowed="move";setDragging(shipId)}}
        onDragEnd={()=>setDragging(null)}>
       <b className="chip-index">{index+1}</b>
       <span className="chip-text">{chipLabel(shipId,state)}</span>
       {role&&<i className="chip-role">{role}</i>}
       <span className="chip-actions">
        <button type="button" onClick={()=>onReorder(column.columnId,shipId,-1)} disabled={index===0} title="前移（更靠近领舰）">◀</button>
        <button type="button" onClick={()=>onReorder(column.columnId,shipId,1)} disabled={index===column.shipIds.length-1} title="后移">▶</button>
        <button type="button" className="chip-out" disabled={index===0}
          onClick={()=>onSplit(column.columnId,shipId)} title={index===0?"领舰不能拆出":"从此舰拆出（领舰留在原队，其与之后进入新队）"}>{index===0?"领舰":"拆出"}</button>
       </span>
      </span>;})}
     </div>
     <p className="well-hint">拖入新舰追加到队尾；领舰位置（1）决定纵队锚点与全队航向。</p>
    </section>;})}
  </div>
 </div>;
}
