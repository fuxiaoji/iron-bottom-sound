// 剧本工坊第 3 步：把纵队拖上真海图定初设。拖动纵队内任意棋子时，指针格会变成
// 被拖那艘舰的目标格，锚点按「航向反向走 成员序×间距」反推，整队以半透明 ghost 预览；
// 越界或与他队占用格重叠即拒绝。与引擎 _layout_for_order 同一套几何。
// 海图尺寸跟随剧本声明（mapSize，缺省 46×39）：越界判定与 viewBox/像素范围同尺寸。
import {useEffect,useRef,useState} from "react";
import type {Side} from "../types";
import {counterAssetUrl} from "../assets";
import {
 asternColumn,columnLabel,displayRowToAxial,fitMapViewport,getActiveMap,headingRotation,hexCenter,hexLabel,screenToHex,setActiveMapSize,walkHex,
 HEX_SIZE,MAP_COLUMNS,MAP_ROWS,
} from "../hexGeometry";
import type {Axial,MapSize,MapViewport} from "../hexGeometry";
import {computeLayout,sideLabel,shipById} from "./scenario";
import type {EditorColumn,EditorState} from "./scenario";

const DEFAULT_VIEWPORT:MapViewport={tx:-100,ty:-250,k:1.8};

const hexPolygon=(cx:number,cy:number)=>Array.from({length:6},(_,i)=>{const a=Math.PI/180*(60*i);return `${cx+HEX_SIZE*Math.cos(a)},${cy+HEX_SIZE*Math.sin(a)}`}).join(" ");

interface DragState{columnId:string;side:Side;anchor:Axial|null;cells:Axial[]|null;reason:string|null;active:boolean}

export function EditorDeploymentMap({state,onSetAnchor,mapSize}:{
 state:EditorState;
 onSetAnchor:(side:Side,columnId:string,anchor:Axial)=>void;
 mapSize?:MapSize;
}){
 // 尺寸先进几何（缺省 → 标准 46×39），本帧起拖拽/占用判定与像素范围按该尺寸。
 setActiveMapSize(mapSize??null);
 const map=getActiveMap();
 const mapColumns=map.columns,mapRows=map.rows,printedColumns=map.printedColumns,printedRows=map.printedRows;
 const worldW=map.width,worldH=map.height;
 const hasBuffer=printedColumns<mapColumns||printedRows<mapRows;
 const isStandard=mapColumns===MAP_COLUMNS&&mapRows===MAP_ROWS;
 const layout=computeLayout(state);
 const occupiedCells=()=>layout.columns.flatMap(deployed=>deployed.cells);
 // 标准 46×39 沿用聚焦原交战区的常量；大战场等非标准海图初次打开即框住已布纵队。
 const [viewport,setViewport]=useState<MapViewport>(()=>isStandard?DEFAULT_VIEWPORT:fitMapViewport(occupiedCells(),map));
 const [panning,setPanning]=useState(false);
 const svgRef=useRef<SVGSVGElement>(null);
 const panRef=useRef({active:false,x:0,y:0,tx:0,ty:0});
 const [drag,setDrag]=useState<DragState|null>(null);
 const dragRef=useRef<{columnId:string|null;side:Side|null;grab:number;pointerId:number|null}>({columnId:null,side:null,grab:0,pointerId:null});

 const clampK=(value:number)=>Math.min(4,Math.max(0.5,value));
 const zoomAt=(clientX:number,clientY:number,factor:number)=>{
  const svg=svgRef.current;if(!svg)return;
  const rect=svg.getBoundingClientRect();
  if(rect.width===0||rect.height===0)return;
  setViewport(prev=>{
   const s=Math.min(rect.width/worldW,rect.height/worldH);
   const ox=(rect.width-worldW*s)/2,oy=(rect.height-worldH*s)/2;
   const ux=(clientX-rect.left-ox)/s,uy=(clientY-rect.top-oy)/s;
   const k2=clampK(prev.k*factor);
   const wx=(ux-prev.tx)/prev.k,wy=(uy-prev.ty)/prev.k;
   let tx=ux-wx*k2,ty=uy-wy*k2;
   const viewW=rect.width/s,viewH=rect.height/s;
   const minTx=Math.min(0,viewW-worldW*k2),maxTx=Math.max(0,worldW*k2-viewW);
   const minTy=Math.min(0,viewH-worldH*k2),maxTy=Math.max(0,worldH*k2-viewH);
   tx=Math.min(maxTx,Math.max(minTx,tx));
   ty=Math.min(maxTy,Math.max(minTy,ty));
   return {tx,ty,k:k2};
  });
 };
 const zoomCenter=(factor:number)=>{const svg=svgRef.current;if(!svg)return;const rect=svg.getBoundingClientRect();zoomAt(rect.left+rect.width/2,rect.top+rect.height/2,factor)};
 const focusCombat=()=>setViewport(isStandard?DEFAULT_VIEWPORT:fitMapViewport(occupiedCells(),map));
 useEffect(()=>{
  const svg=svgRef.current;if(!svg)return;
  const onWheel=(event:WheelEvent)=>{event.preventDefault();zoomAt(event.clientX,event.clientY,Math.exp(-event.deltaY*0.0012))};
  svg.addEventListener("wheel",onWheel,{passive:false});
  return()=>svg.removeEventListener("wheel",onWheel);
 },[]);

 const svgPointerDown=(event:React.PointerEvent<SVGSVGElement>)=>{
  if(event.button!==0)return;
  const target=event.target as Element;
  if(target.closest(".deploy-member,.deploy-ghost"))return;
  panRef.current={active:true,x:event.clientX,y:event.clientY,tx:viewport.tx,ty:viewport.ty};
  setPanning(true);
  event.currentTarget.setPointerCapture(event.pointerId);
 };
 const svgPointerMove=(event:React.PointerEvent<SVGSVGElement>)=>{
  const pan=panRef.current;
  if(!pan.active)return;
  setViewport(prev=>({...prev,tx:pan.tx+(event.clientX-pan.x),ty:pan.ty+(event.clientY-pan.y)}));
 };
 const svgPointerEnd=()=>{panRef.current.active=false;setPanning(false)};

 const updateDrag=(clientX:number,clientY:number)=>{
  const svg=svgRef.current;
  const {columnId,side,grab}=dragRef.current;
  if(!svg||!columnId||!side)return;
  const pointerHex=screenToHex(svg,clientX,clientY,viewport);
  if(!pointerHex)return;
  const column=state.columns[side].find(item=>item.columnId===columnId);
  if(!column)return;
  let anchor:Axial|null=pointerHex;
  try{anchor=walkHex(pointerHex,column.heading,grab*column.spacing)}catch{anchor=null}
  if(!anchor){setDrag({columnId,side,anchor:null,cells:null,reason:"纵队会伸出地图边缘",active:true});return}
  let cells:Axial[]|null=null;
  try{cells=asternColumn(anchor,column.heading,column.spacing,column.shipIds.length)}catch{cells=null}
  const occupiedByOthers=new Set<string>();
  for(const otherSide of ["axis","allies"] as Side[]){
   for(const otherColumn of state.columns[otherSide]){
    if(otherColumn.columnId===columnId)continue;
    if(!otherColumn.anchor)continue;
    try{
     const others=asternColumn(otherColumn.anchor,otherColumn.heading,otherColumn.spacing,otherColumn.shipIds.length);
     others.forEach(cell=>occupiedByOthers.add(hexLabel(cell)));
    }catch{/* 原列问题由 computeLayout 提示 */}
   }
  }
  let reason:string|null=null;
  if(!cells)reason="纵队会伸出地图边缘";
  else{
   const used=new Set<string>();
   for(const cell of cells){
    const key=hexLabel(cell);
    if(occupiedByOthers.has(key)||used.has(key)){reason=`${key} 已被其他舰船占用`;break}
    used.add(key);
   }
  }
  setDrag({columnId,side,anchor,cells:reason?null:cells,reason,active:true});
 };
 const memberPointerDown=(event:React.PointerEvent<SVGGElement>,columnId:string,side:Side,index:number)=>{
  event.preventDefault();
  event.stopPropagation();
  dragRef.current={columnId,side,grab:index,pointerId:event.pointerId};
  event.currentTarget.setPointerCapture(event.pointerId);
  setDrag({columnId,side,anchor:null,cells:null,reason:null,active:true});
 };
 const memberPointerMove=(event:React.PointerEvent<SVGGElement>)=>{
  if(event.pointerId!==dragRef.current.pointerId)return;
  updateDrag(event.clientX,event.clientY);
 };
 const memberPointerUp=(event:React.PointerEvent<SVGGElement>)=>{
  if(event.pointerId!==dragRef.current.pointerId)return;
  const {columnId,side}=dragRef.current;
  dragRef.current.pointerId=null;
  if(columnId&&side&&drag&&drag.active&&drag.anchor&&!drag.reason)onSetAnchor(side,columnId,drag.anchor);
  setDrag(null);
 };

 const ghostHeading=drag&&drag.active?(()=>{
  const side=drag.side;
  return state.columns[side].find(item=>item.columnId===drag.columnId)?.heading??1;
 })():1;

 const hexes=[];
 for(let q=0;q<mapColumns;q++)for(let row=0;row<mapRows;row++){
  const r=displayRowToAxial(q,row);
  const center=hexCenter(q,r);
  const buffer=q>=printedColumns||row>=printedRows;
  hexes.push(<polygon key={`${q}:${r}`} className={buffer?"editor-hex buffer":"editor-hex"}
   points={hexPolygon(center.x,center.y)}><title>{`${columnLabel(q)}${row+1}`}{buffer?" · 扩展纯海缓冲区":""}</title></polygon>);
 }

 const deployedGroups=layout.columns.map(({column,side,cells})=>{
  const members=column.shipIds.map((shipId,index)=>{
   const ship=shipById(state,shipId);
   if(!ship)return null;
   const cell=cells[index];
   const role=shipId===column.flagshipId?"旗舰":shipId===column.reserveId?"备用旗舰":shipId===column.shipIds[0]?"领舰":"";
   const center=hexCenter(cell.q,cell.r);
   const rotation=headingRotation(column.heading);
   return <g key={shipId} className={`deploy-member ${side}${index===0?" deploy-leader":""}`}
    transform={`translate(${center.x} ${center.y})`}
    onPointerDown={event=>memberPointerDown(event,column.columnId,side,index)}
    onPointerMove={memberPointerMove}
    onPointerUp={memberPointerUp}
    onPointerCancel={memberPointerUp}>
    <title>{`${sideLabel(side)}·${ship.name}${role?`·${role}`:""} · ${hexLabel(cell)} · 列「${column.name}」 · 拖动整队平移`}</title>
    <g transform={`rotate(${rotation})`}>
     {ship.asset&&<image href={counterAssetUrl(ship.asset)} x="-22" y="-14" width="44" height="28" preserveAspectRatio="xMidYMid meet"/>}
     <path className="bow-pointer" d="M -25 0 L -17 -5 L -17 5 Z"/>
    </g>
    <text transform={`rotate(${-rotation})`} y="28" className={index===0?"deploy-role leader":"deploy-role"}>{role||(column.shipIds.length===1?"散舰":"")}</text>
    <text transform={`rotate(${-rotation})`} y="40" className="deploy-pos">{hexLabel(cell)}</text>
   </g>;
  });
  return <g key={column.columnId} className={`deploy-column ${side}`}>{members}</g>;
 });

 const ghost=drag&&drag.active&&drag.cells?drag.cells.map((cell,index)=>{
  const shipId=state.columns[drag.side].find(item=>item.columnId===drag.columnId)?.shipIds[index];
  const ship=shipId?shipById(state,shipId):null;
  if(!ship)return null;
  const center=hexCenter(cell.q,cell.r);
  return <g key={`${ship.id}-ghost`} className="deploy-ghost" transform={`translate(${center.x} ${center.y}) rotate(${headingRotation(ghostHeading)})`}>
   {ship.asset&&<image href={counterAssetUrl(ship.asset)} x="-22" y="-14" width="44" height="28" preserveAspectRatio="xMidYMid meet"/>}
   <path className="bow-pointer" d="M -25 0 L -17 -5 L -17 5 Z"/><title>{`${ship.name} 预览 · ${hexLabel(cell)}`}</title></g>;
 }):null;

 return <div className="map-frame editor-map"><svg ref={svgRef} viewBox={`0 0 ${worldW} ${worldH}`}
  role="img" aria-label="剧本工坊海图：拖动纵队到目标海区"
  className={panning?"panning":undefined} style={{touchAction:"none"}}
  onPointerDown={svgPointerDown} onPointerMove={svgPointerMove} onPointerUp={svgPointerEnd} onPointerCancel={svgPointerEnd}>
  <g className="map-viewport" transform={`translate(${viewport.tx} ${viewport.ty}) scale(${viewport.k})`}>
   <g className="editor-hexes">{hexes}</g>
   {deployedGroups}
   {ghost}
  </g>
 </svg>
 <div className="map-zoom-controls" role="group" aria-label="地图缩放">
  <button title="缩小" onClick={()=>zoomCenter(Math.exp(-0.1))}>−</button>
  <button title="放大" onClick={()=>zoomCenter(Math.exp(0.1))}>＋</button>
  <button title="聚焦已部署区域" onClick={focusCombat}>交战区</button>
  <button title="查看完整海图" onClick={()=>setViewport({tx:0,ty:0,k:1})}>全图</button>
 </div>
 {drag&&drag.active&&drag.reason&&<div className="editor-drop-error">{drag.reason}</div>}
 {drag&&drag.active&&!drag.reason&&drag.anchor&&<div className="editor-drop-hint">松开放下：{hexLabel(drag.anchor)}，整队沿航向 {ghostHeading} 排成纵队</div>}
 <div className="map-area-legend">{hasBuffer?<><span>原印刷区 A–{columnLabel(printedColumns-1)} / 1–{printedRows}</span><span>浅色：扩展纯海缓冲区</span></>:<span>整图印刷海图 A–{columnLabel(mapColumns-1)} / 1–{mapRows}</span>}<b>拖动任意棋子整队平移 · ghost 预览</b></div>
 </div>;
}
