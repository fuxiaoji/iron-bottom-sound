import {useEffect,useMemo,useRef,useState} from "react";
import type {FireHeatmapMode,FireHeatmapResponse,HexCoord,Marker,MovementPreview,MovementTrajectory,Ship,Side,TorpedoTrack} from "./types";
import {counterAssetUrl} from "./assets";
import {columnLabel,displayRowToAxial,fitMapViewport,getActiveMap,headingRotation,headingVector,hexCenter,hexDistance,hexFromLabel,hexLabel,resolveMapDims,screenToHex,setActiveMapSize,torpedoCounterRotation,HEX_SIZE,HEX_ROW_HEIGHT,MAP_COLUMNS,MAP_ROWS} from "./hexGeometry";
import type {MapViewport} from "./hexGeometry";

export interface TorpedoAssistPath{label:string;hexes:HexCoord[];intercept?:HexCoord|null}
export interface GunneryTargetLine{attackerId:string;targetId:string;attackerName:string;targetName:string;mountCount:number}

// 地图尺寸按当前对局的剧本声明解析：缺省/标准 46×39 走固定常量，逐位不变。
export interface HexMapDims{map_columns?:number;map_rows?:number;printed_columns?:number|null;printed_rows?:number|null}

const points=(cx:number,cy:number)=>Array.from({length:6},(_,i)=>{const a=Math.PI/180*(60*i);return `${cx+HEX_SIZE*Math.cos(a)},${cy+HEX_SIZE*Math.sin(a)}`}).join(" ");
const torpedoAsset=(track:TorpedoTrack)=>track.side==="axis"?`鱼雷${Math.min(3,track.salvo_size)}（日）.png`:`鱼雷${Math.min(2,track.salvo_size)}（美）.png`;
const DEFAULT_VIEWPORT={tx:-100,ty:-250,k:1.8}; // 默认聚焦原想定交战区；“全图”可查看全部缓冲海域

export interface MapMoveMode{
 shipId:string;
 reachable:MovementPreview["reachable"];
 currentHex:HexCoord;
 currentHeading:number;
 nextAdvance:HexCoord|null;
 trajectory:MovementPreview["trajectory"];
 onHexClick:(hex:HexCoord)=>void;
 onDragPath:(path:HexCoord[])=>void;
}

export function HexMap({ships,torpedoTracks,markers,onSelect,viewerSide,visibility,dims,showVisibility=false,moveMode,torpedoAssistPaths,gunneryTargetLines,plannedTrajectories,fireHeatmaps,fireHeatmapMode}:{ships:Ship[];torpedoTracks:TorpedoTrack[];markers:Marker[];onSelect:(ship:Ship)=>void;viewerSide:Side;visibility:number;dims?:HexMapDims;showVisibility?:boolean;moveMode?:MapMoveMode;torpedoAssistPaths?:TorpedoAssistPath[];gunneryTargetLines?:GunneryTargetLine[];plannedTrajectories?:(MovementTrajectory&{side?:Side})[];fireHeatmaps?:FireHeatmapResponse;fireHeatmapMode?:FireHeatmapMode}){
 // —— 声明尺寸进几何：本帧起所有越界判定/像素世界按本局海图（默认 46×39 不变） ——
 setActiveMapSize(resolveMapDims(dims));
 const map=getActiveMap();
 const mapColumns=map.columns,mapRows=map.rows,printedColumns=map.printedColumns,printedRows=map.printedRows;
 const worldW=map.width,worldH=map.height;
 const hasBuffer=printedColumns<mapColumns||printedRows<mapRows;
 const isStandard=mapColumns===MAP_COLUMNS&&mapRows===MAP_ROWS;
 const anchorsOf=(list:Ship[]):{q:number;r:number}[]=>list.filter(ship=>ship.position&&!ship.sunk).map(ship=>ship.position!);
 // —— 地图视口（pan/zoom）：translate + scale 包住全部世界图层，罗盘除外 ——
 // 标准 46×39 用既有常量聚焦原交战区；大战场等非标准海图初次打开即框住当前舰队。
 const [viewport,setViewport]=useState<MapViewport>(()=>isStandard?DEFAULT_VIEWPORT:fitMapViewport(anchorsOf(ships),map));
 const [panning,setPanning]=useState(false);
 const svgRef=useRef<SVGSVGElement>(null);
 const panRef=useRef({active:false,x:0,y:0,tx:0,ty:0});
 const clampK=(v:number)=>Math.min(4,Math.max(0.5,v));
 // 以指针为锚点缩放：指针处的地图世界坐标保持不动，并夹取地图至少一边落在视口内。
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
 const zoomAtCenter=(factor:number)=>{const svg=svgRef.current;if(!svg)return;const rect=svg.getBoundingClientRect();zoomAt(rect.left+rect.width/2,rect.top+rect.height/2,factor)};
 const focusCombat=()=>setViewport(isStandard?DEFAULT_VIEWPORT:fitMapViewport(anchorsOf(ships),map));
 // 滚轮缩放（React onWheel 默认 passive 无法 preventDefault → 原生监听）
 useEffect(()=>{
  const svg=svgRef.current;if(!svg)return;
  const onWheel=(event:WheelEvent)=>{event.preventDefault();zoomAt(event.clientX,event.clientY,Math.exp(-event.deltaY*0.0012))};
  svg.addEventListener("wheel",onWheel,{passive:false});
  return()=>svg.removeEventListener("wheel",onWheel);
 },[]);
 // 拖拽平移：只在空白/背景起手（舰船选中/编辑拖拽、罗盘、moveMode 六角格点击优先）
 const onSvgPointerDown=(event:React.PointerEvent<SVGSVGElement>)=>{
  if(event.button!==0)return;
  const target=event.target as Element;
  if(target.closest(".counter,.status-counter,.heading-compass"))return;
  if(moveMode&&target.closest(".hexes"))return;
  panRef.current={active:true,x:event.clientX,y:event.clientY,tx:viewport.tx,ty:viewport.ty};
  setPanning(true);
  event.currentTarget.setPointerCapture(event.pointerId);
 };
 const onSvgPointerMove=(event:React.PointerEvent<SVGSVGElement>)=>{
  const pan=panRef.current;if(!pan.active)return;
  setViewport(prev=>({...prev,tx:pan.tx+(event.clientX-pan.x),ty:pan.ty+(event.clientY-pan.y)}));
 };
 const onSvgPointerEnd=()=>{panRef.current.active=false;setPanning(false)};
 const observers=ships.filter(ship=>ship.side===viewerSide&&ship.position&&!ship.sunk).map(ship=>ship.position!);
 const highlightByLabel=useMemo(()=>{
  const map=new Map<string,"reachable"|"current"|"next">();
  if(!moveMode)return map;
  for(const reachable of moveMode.reachable)map.set(reachable.label,"reachable");
  map.set(hexLabel(moveMode.currentHex),"current");
  if(moveMode.nextAdvance)map.set(hexLabel(moveMode.nextAdvance),"next");
  return map;
 },[moveMode]);
 const trajectoryPoints=moveMode&&moveMode.trajectory.length>0?moveMode.trajectory.map(step=>{const center=hexCenter(step.hex.q,step.hex.r);return `${center.x},${center.y}`}).join(" "):null;
 const [dragPath,setDragPath]=useState<HexCoord[]>([]);
 const dragRef=useRef<{active:boolean;path:HexCoord[]}>({active:false,path:[]});
 const suppressClick=useRef(false);
 // 热力图：双方合并为一个红色热值面，每格显示热值数字（覆盖坐标标注）。
 const heatData=useMemo(()=>{
  if(!fireHeatmaps||!fireHeatmapMode||fireHeatmapMode==="off")return null;
  // "ship" 模式响应只填充所属那一侧，其余为空 → 按 both 迭代即可拿到被填充侧
  const sides=(fireHeatmapMode==="both"||fireHeatmapMode==="ship"?["axis","allies"]:[fireHeatmapMode]) as ("axis"|"allies")[];
  const merged=new Map<string,number>();
  for(const sideKey of sides){
   const side=fireHeatmaps.sides[sideKey];
   if(!side)continue;
   for(const [label,heat] of Object.entries(side.hexes))merged.set(label,(merged.get(label)??0)+heat);
  }
  if(!merged.size)return null;
  return {merged,max:Math.max(...merged.values())};
 },[fireHeatmaps,fireHeatmapMode]);
 const heatCells=heatData?[...heatData.merged.entries()].map(([label,heat])=>{
  const coord=hexFromLabel(label);
  const center=hexCenter(coord.q,coord.r);
  const opacity=0.12+(heat/heatData.max)*0.5;
  return <polygon key={label} className="heat-cell" points={points(center.x,center.y)} style={{fill:"#e05c3a",fillOpacity:opacity}}><title>{`射界热力 · ${label} · 热值 ${heat.toFixed(2)}`}</title></polygon>;
 }):null;
 const hexes=[];for(let q=0;q<mapColumns;q++)for(let row=0;row<mapRows;row++){const r=displayRowToAxial(q,row);const center=hexCenter(q,r);const label=`${columnLabel(q)}${row+1}`;const highlight=highlightByLabel.get(label);const observed=showVisibility&&observers.some(position=>hexDistance({q,r},position)<=visibility);const heatNumber=heatData?.merged.get(label);const buffer=q>=printedColumns||row>=printedRows;const classes=[buffer?"map-buffer":null,observed?"in-visibility":highlight?`move-${highlight}`:null].filter(Boolean).join(" ");hexes.push(<g key={`${q}:${row}`} onClick={moveMode?()=>moveMode.onHexClick({q,r}):undefined}><polygon className={classes||undefined} points={points(center.x,center.y)}><title>{buffer?`${label} · 扩展纯海缓冲区`:`${label} · 原印刷海图`}</title></polygon><text x={center.x} y={center.y+3} className={heatNumber!==undefined?"heat-value":buffer?"buffer-label":undefined}>{heatNumber!==undefined?heatNumber.toFixed(1):`${columnLabel(q)}${row+1}`}</text></g>) }
 const directions=[1,2,3,4,5,6].map(heading=>({heading,tip:headingVector(heading,42),label:headingVector(heading,55)}));
 const dragPolyline=dragPath.length>0?dragPath.map(hex=>{const center=hexCenter(hex.q,hex.r);return `${center.x},${center.y}`}).join(" "):null;
 const fullMapLabel=`A 至 ${columnLabel(mapColumns-1)}、1 至 ${mapRows}`;
 const ariaLabel=hasBuffer?`${fullMapLabel} 固定扩展六角格战术地图；A 至 ${columnLabel(printedColumns-1)}、1 至 ${printedRows} 为原印刷区`:`${fullMapLabel} 战术地图`;
 return <div className="map-frame"><svg ref={svgRef} viewBox={`0 0 ${worldW} ${worldH}`} role="img" aria-label={ariaLabel} className={panning?"panning":undefined} style={{touchAction:"none"}} onPointerDown={onSvgPointerDown} onPointerMove={onSvgPointerMove} onPointerUp={onSvgPointerEnd} onPointerCancel={onSvgPointerEnd}><defs><marker id="heading-arrow" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="5" markerHeight="5" orient="auto-start-reverse"><path fill="#f4d88c" d="M 0 0 L 10 5 L 0 10 z"/></marker><marker id="gunnery-arrow" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path fill="#ffd36a" d="M 0 0 L 10 5 L 0 10 z"/></marker></defs><g className="map-viewport" transform={`translate(${viewport.tx} ${viewport.ty}) scale(${viewport.k})`}>{heatCells}
  <g className="hexes">{hexes}</g>
  {gunneryTargetLines&&gunneryTargetLines.length>0&&<g className="gunnery-target-lines" aria-label="己方炮击目标线">{gunneryTargetLines.map((targetLine,index)=>{const attacker=ships.find(ship=>ship.id===targetLine.attackerId&&ship.position);const target=ships.find(ship=>ship.id===targetLine.targetId&&ship.position);if(!attacker?.position||!target?.position)return null;const start=hexCenter(attacker.position.q,attacker.position.r);const end=hexCenter(target.position.q,target.position.r);const dx=end.x-start.x,dy=end.y-start.y,length=Math.max(1,Math.hypot(dx,dy));const inset=24;const x1=start.x+dx/length*inset,y1=start.y+dy/length*inset,x2=end.x-dx/length*inset,y2=end.y-dy/length*inset;const mx=(x1+x2)/2,my=(y1+y2)/2-8-index%2*10;return <g className="gunnery-target-line" key={`${targetLine.attackerId}-${targetLine.targetId}`}><title>{`${targetLine.attackerName} → ${targetLine.targetName} · ${targetLine.mountCount} 个炮位`}</title><line x1={x1} y1={y1} x2={x2} y2={y2} markerEnd="url(#gunnery-arrow)"/><text x={mx} y={my}>{targetLine.attackerName} → {targetLine.targetName} · {targetLine.mountCount}炮位</text></g>})}</g>}
  {trajectoryPoints&&<polyline className="move-trajectory" points={trajectoryPoints}/>}
  {dragPolyline&&<polyline className="move-drag-path" points={dragPolyline}/>}
  {plannedTrajectories?.filter(t=>t.valid&&t.trajectory.length>0).map(t=>{
   const ship=ships.find(s=>s.id===t.ship_id);
   if(!ship||!ship.position)return null;
   const enemy=t.side!==undefined&&t.side!==viewerSide;
   const hexes=[ship.position,...t.trajectory.map(step=>step.hex)];
   const deduped=hexes.filter((hex,index)=>index===0||hex.q!==hexes[index-1].q||hex.r!==hexes[index-1].r);
   const trailPoints=deduped.map(hex=>{const center=hexCenter(hex.q,hex.r);return `${center.x},${center.y}`}).join(" ");
   const last=t.trajectory[t.trajectory.length-1];
   const endCenter=hexCenter(last.hex.q,last.hex.r);
   const rotation=headingRotation(t.end_heading??ship.heading);
   return <g className={`planned-move${enemy?" enemy":""}`} key={t.ship_id}><polyline className={`planned-move-trail${enemy?" enemy":""}`} points={trailPoints}/>{ship.asset&&<g className="planned-destination" transform={`translate(${endCenter.x} ${endCenter.y}) rotate(${rotation})`}><title>{enemy?"敌方":"我方"}{ship.name} · 计划终点 {t.end_hex} · 航向 {t.end_heading}</title><image href={counterAssetUrl(ship.asset)} x="-22" y="-14" width="44" height="28" preserveAspectRatio="xMidYMid meet"/><path className="bow-pointer" d="M -25 0 L -17 -5 L -17 5 Z"/><text transform={`rotate(${-rotation})`} y="30">{ship.name}</text></g>}</g>;
  })}
  {torpedoAssistPaths?.map(path=>{const assistPoints=path.hexes.map(hex=>{const center=hexCenter(hex.q,hex.r);return `${center.x},${center.y}`}).join(" ");const end=path.hexes[path.hexes.length-1];const endCenter=end?hexCenter(end.q,end.r):null;const intercept=path.intercept?hexCenter(path.intercept.q,path.intercept.r):null;return <g className="torpedo-assist-overlay" key={path.label}><polyline className="torpedo-assist-path" points={assistPoints}/>{intercept&&<circle className="torpedo-assist-intercept" cx={intercept.x} cy={intercept.y} r="7"><title>{path.label} · 预计在此与目标相遇</title></circle>}{endCenter&&<circle className="torpedo-assist-end" cx={endCenter.x} cy={endCenter.y} r="5"><title>{path.label} · 终点 {hexLabel(end)}</title></circle>}</g>})}
  {torpedoTracks.map(track=>{const center=hexCenter(track.position.q,track.position.r);const vector=headingVector(track.heading,26);const launch=track.launch_position?hexLabel(track.launch_position):"旧存档未记录";const side=track.launch_side==="port"?"左舷":track.launch_side==="starboard"?"右舷":"舷侧未记录";const trail=(track.traversed_hexes??[]).map(hex=>{const c=hexCenter(hex.q,hex.r);return `${c.x},${c.y}`}).join(" ");const launchCenter=track.launch_position?hexCenter(track.launch_position.q,track.launch_position.r):null;const path=(track.traversed_hexes??[]).map(hexLabel).join(" → ");return <g className="torpedo-track-group" key={track.id}>{trail&&<polyline className="torpedo-trail" points={trail}/>}{launchCenter&&<g className="torpedo-launch-marker"><circle cx={launchCenter.x} cy={launchCenter.y} r="6"><title>发射点 {launch} · {side}{track.launch_angle??""} · 航向 {track.heading}</title></circle><text x={launchCenter.x+8} y={launchCenter.y+3}>{track.launch_angle??""}</text></g>}<g className={`torpedo-counter ${track.side===viewerSide?"own":"observed"}`} transform={`translate(${center.x} ${center.y})`}><title>{track.side===viewerSide?"我方":"已发现敌方"}鱼雷 · {track.salvo_size} 枚 · {launch} → {hexLabel(track.position)} · {side}{track.launch_angle??""} · 航向 {track.heading} · 已走 {track.distance_travelled} 格 · 剩余射程 {track.range_remaining}{path?` · 航迹 ${path}`:""}</title><image href={counterAssetUrl(torpedoAsset(track))} x="-17" y="-17" width="34" height="34" transform={`rotate(${torpedoCounterRotation(track.heading)})`}/><line x1="0" y1="0" x2={vector.x} y2={vector.y} markerEnd="url(#heading-arrow)"/><text y="28">{track.salvo_size}枚</text></g></g>})}
  {ships.filter(ship=>ship.position).map(ship=>{
   const editing=moveMode&&moveMode.shipId===ship.id;
   const position=editing?moveMode!.currentHex:ship.position!;
   const heading=editing?moveMode!.currentHeading:ship.heading;
   const center=hexCenter(position.q,position.r);
   if(ship.sunk)return <g className="status-counter sunk" key={ship.id} transform={`translate(${center.x} ${center.y})`} onClick={()=>onSelect(ship)}><title>{ship.name} · 沉没中</title><image href={counterAssetUrl("沉没中.png")} x="-22" y="-22" width="44" height="44"/><text y="31">{ship.name}</text></g>;
   const rotation=headingRotation(heading);
   const handlers=editing?{
    onClick:()=>{if(suppressClick.current){suppressClick.current=false;return}onSelect(ship)},
    onPointerDown:(event:React.PointerEvent<SVGGElement>)=>{event.preventDefault();event.currentTarget.setPointerCapture(event.pointerId);dragRef.current={active:true,path:[]};setDragPath([])},
    onPointerMove:(event:React.PointerEvent<SVGGElement>)=>{const drag=dragRef.current;if(!drag.active)return;const svg=event.currentTarget.ownerSVGElement as SVGSVGElement;const hex=screenToHex(svg,event.clientX,event.clientY,viewport);if(!hex)return;const last=drag.path[drag.path.length-1];if(last&&last.q===hex.q&&last.r===hex.r)return;if(!last||hexDistance(last,hex)===1){drag.path.push(hex);suppressClick.current=true}else{drag.path=[hex]}setDragPath([...drag.path])},
    onPointerUp:()=>{const drag=dragRef.current;if(!drag.active)return;dragRef.current={active:false,path:[]};if(drag.path.length>0){suppressClick.current=true;moveMode?.onDragPath(drag.path)}setDragPath([])},
   }:{onClick:()=>onSelect(ship)};
   return <g className={`counter ${ship.side}${editing?" move-editing":""}`} key={ship.id} transform={`translate(${center.x} ${center.y}) rotate(${rotation})`} {...handlers}><title>{ship.name} · 舰首 {heading}{editing?` · 计划位置 ${moveMode!.currentHex?hexLabel(moveMode!.currentHex):""}`:""}</title>{ship.asset&&<image href={counterAssetUrl(ship.asset)} x="-22" y="-14" width="44" height="28" preserveAspectRatio="xMidYMid meet"/>}<path className="bow-pointer" d="M -25 0 L -17 -5 L -17 5 Z"/>{ship.fire_markers>0&&<g className="fire-marker" transform={`rotate(${-rotation}) translate(18 -17)`}><image href={counterAssetUrl("起火.png")} x="-11" y="-11" width="22" height="22"/><text x="8" y="-7">×{ship.fire_markers}</text></g>}<text transform={`rotate(${-rotation})`} y="30">{ship.name}</text></g>;
  })}
  {moveMode&&ships.filter(ship=>ship.id===moveMode.shipId&&ship.position).map(ship=>{const center=hexCenter(ship.position!.q,ship.position!.r);return <circle className="move-origin" key={ship.id} cx={center.x} cy={center.y} r="4"><title>真实起始位置 {hexLabel(ship.position!)}</title></circle>})}
  {markers.filter(marker=>marker.position&&!['fire','sunk'].includes(marker.kind)).map(marker=>{const center=hexCenter(marker.position!.q,marker.position!.r);return <circle className={`map-marker ${marker.kind}`} key={marker.id} cx={center.x} cy={center.y} r="7"><title>{marker.kind}</title></circle>})}
  </g><g className="heading-compass" transform={`translate(82 ${worldH-92})`} aria-label="舰首方向：1右上、2右下、3下、4左下、5左上、6上"><rect x="-70" y="-70" width="140" height="150" rx="8"/><text className="compass-title" x="0" y="72">舰首方向</text>{directions.map(({heading,tip,label})=><g key={heading}><line x1="0" y1="0" x2={tip.x} y2={tip.y} markerEnd="url(#heading-arrow)"/><text x={label.x} y={label.y+3}>{heading}</text></g>)}<circle r="5"/></g></svg><div className="map-zoom-controls" role="group" aria-label="地图缩放"><button title="缩小" onClick={()=>zoomAtCenter(Math.exp(-0.1))}>−</button><button title="放大" onClick={()=>zoomAtCenter(Math.exp(0.1))}>＋</button><button title="聚焦交战区" onClick={focusCombat}>交战区</button><button title="查看完整扩展海图" onClick={()=>setViewport({tx:0,ty:0,k:1})}>全图</button></div><div className="map-area-legend">{hasBuffer?<><span>原印刷区 A–{columnLabel(printedColumns-1)} / 1–{printedRows}</span><span>浅色：扩展纯海缓冲区</span></>:<span>整图印刷海图 {fullMapLabel}</span>}<b>坐标固定 · 不世界平移</b></div></div>;
}
