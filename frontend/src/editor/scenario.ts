// 剧本工坊的纯模型与推导：所有编辑状态收敛到 ships + columns（纵队），
// 每艘舰恰好属于一列；位置一律由「锚点 + 航向 + 间距 + 列内序号」推导，
// 与引擎 realistic_command._layout_for_order 同一套几何。任何组件都不另存坐标。
import type {Side} from "../types";
import type {CustomFormation,CustomScenarioDefinition,RecommendedMode} from "../api";
import {asternColumn,columnLabel,hexFromLabel,hexLabel} from "../hexGeometry";
import type {Axial} from "../hexGeometry";

export interface EditorShip{
 id:string;name:string;ship_type:string;asset:string;side:Side;heading:number;speed:number;
}
export interface EditorColumn{
 columnId:string;name:string;heading:number;spacing:1|2;shipIds:string[];flagshipId:string;reserveId:string;anchor:Axial|null;
}
export type SideColumns=Record<Side,EditorColumn[]>;

export interface EditorState{
 ships:EditorShip[];
 columns:SideColumns;
}

export const SIDES:Side[]=["axis","allies"];
export const sideLabel=(side:Side)=>side==="axis"?"轴心":"同盟";
// 剧本可选海图尺寸（与后端 MAX/默认同源；标准图有 34×27 印刷区+扩展缓冲海）。
export interface MapSize{columns:number;rows:number;printedColumns:number;printedRows:number}
export const MAP_SIZE_STANDARD:MapSize={columns:46,rows:39,printedColumns:34,printedRows:27};
export const MAP_SIZE_BIG:MapSize={columns:92,rows:78,printedColumns:92,printedRows:78};
export const MAP_SIZE_OPTIONS:{key:"standard"|"big";label:string;size:MapSize}[]=[
 {key:"standard",label:"标准海图 46×39（印刷区 34×27）",size:MAP_SIZE_STANDARD},
 {key:"big",label:"大战场 92×78（整图印刷）",size:MAP_SIZE_BIG},
];
export function mapSizeOfMeta(meta:ScenarioMeta):MapSize{
 const columns=meta.mapColumns??MAP_SIZE_STANDARD.columns;
 const rows=meta.mapRows??MAP_SIZE_STANDARD.rows;
 const printedColumns=meta.printedColumns??(columns===MAP_SIZE_STANDARD.columns?MAP_SIZE_STANDARD.printedColumns:columns);
 const printedRows=meta.printedRows??(rows===MAP_SIZE_STANDARD.rows?MAP_SIZE_STANDARD.printedRows:rows);
 return {columns,rows,printedColumns,printedRows};
}
// 每侧真实编队上限：用户裁定由 4 放开到 8，支持“全主力+大队驱逐”的巨舰剧本。
export const MAX_WELLS_PER_SIDE=8;

export const OPTIONAL_RULES:{key:string;label:string}[]=[
 {key:"hidden_contacts",label:"隐藏接敌接触"},
 {key:"radar",label:"雷达（+2 格观测）"},
 {key:"star_shells",label:"照明弹"},
 {key:"searchlights",label:"探照灯"},
 {key:"malfunction_66",label:"舰炮故障（66 法则）"},
 {key:"squalls",label:"暴雨阵"},
 {key:"smoke",label:"烟幕"},
 {key:"silhouettes",label:"剪影识别"},
 {key:"hidden_damage",label:"隐藏损伤"},
 {key:"blind_torpedoes",label:"盲射鱼雷"},
];

export const sideShips=(state:EditorState,side:Side)=>state.ships.filter(ship=>ship.side===side);
export const shipById=(state:EditorState,id:string)=>state.ships.find(ship=>ship.id===id);

function shipFromCatalog(entry:{id:string;name:string;ship_type:string;asset:string|null},side:Side):EditorShip{
 return {id:entry.id,name:entry.name,ship_type:entry.ship_type,asset:entry.asset??"",side,heading:1,speed:3};
}

// 默认锚点：同侧各列按 2 行间隔散开（平行纵队），列多了再右移一列，避免纵队互相压格。
export function defaultAnchor(side:Side,ordinal:number):Axial{
 const baseRow=side==="axis"?5:20;
 const baseCol=side==="axis"?7:23;
 const slot=Math.max(0,ordinal)%8;
 const band=Math.floor(Math.max(0,ordinal)/8);
 return hexFromLabel(`${columnLabel(baseCol+band)}${baseRow+slot*2}`);
}

export function columnById(state:EditorState,columnId:string):{side:Side;column:EditorColumn}|null{
 for(const side of SIDES){
  const column=state.columns[side].find(item=>item.columnId===columnId);
  if(column)return {side,column};
 }
 return null;
}

// 新列的 id 必须全局唯一：编号按 ordinal 但列序在拆分/配对后会乱，若复用作 id 会撞出两列同名。
let columnSeq=0;
export function makeColumn(side:Side,shipIds:string[],ordinal:number,heading:number):EditorColumn{
 columnSeq+=1;
 const flagship=shipIds[0]??"";
 const reserve=shipIds[1]??shipIds[0];
 return {columnId:`${side}-col-${columnSeq.toString(36)}-${ordinal+1}`,name:`${sideLabel(side)}第${ordinal+1}队`,heading,spacing:1,
   shipIds,flagshipId:flagship,reserveId:reserve,anchor:defaultAnchor(side,ordinal)};
}

// —— 不可变更新器 ——

export function pickShip(state:EditorState,entry:{id:string;name:string;ship_type:string;asset:string|null},side:Side):EditorState{
 if(state.ships.some(ship=>ship.id===entry.id))return state;
 const ship=shipFromCatalog(entry,side);
 const ships=[...state.ships,ship];
 // 新舰各自成一列（散舰）。想组成纵队就到「编队」一步拖入编队井，或用「自动合并」。
 const columns=[...state.columns[side],makeColumn(side,[ship.id],state.columns[side].length,ship.heading)];
 return {ships,columns:{...state.columns,[side]:columns}};
}

export function unpickShip(state:EditorState,shipId:string):EditorState{
 if(!state.ships.some(ship=>ship.id===shipId))return state;
 return dropShip(state,shipId);
}

export function changeShipSide(state:EditorState,shipId:string,side:Side):EditorState{
 const ship=shipById(state,shipId);
 if(!ship||ship.side===side)return state;
 const without=detachShip(state,shipId);
 const ships=without.ships.map(item=>item.id===shipId?{...item,side,heading:1}:item);
 const columns=[...without.columns[side],makeColumn(side,[shipId],without.columns[side].length,1)];
 return {ships,columns:{...without.columns,[side]:columns}};
}

// 把某侧所有舰合并回一列（自动编队）：保留原第一列的锚点，其余列成员按列序并入。
export function autoAssignSide(state:EditorState,side:Side):EditorState{
 const members=sideShips(state,side);
 if(members.length<1)return state;
 const old=state.columns[side];
 const order=members.map(ship=>ship.id);
 const column:EditorColumn={columnId:`${side}-auto`,name:`${sideLabel(side)}编队`,heading:members[0].heading,spacing:1,
   shipIds:order,flagshipId:order[0],reserveId:order[1]??order[0],anchor:old[0]?.anchor??defaultAnchor(side,0)};
 return {...state,columns:{...state.columns,[side]:[column]}};
}

// 仅把舰从各纵队摘出（保留在 ships 名单）——搬动/换位时用，避免误删参战舰。
function detachShip(state:EditorState,shipId:string):EditorState{
 const columns:SideColumns={...state.columns};
 for(const side of SIDES){
  columns[side]=columns[side].map(column=>({...column,shipIds:column.shipIds.filter(id=>id!==shipId)}))
   .filter(column=>column.shipIds.length>0);
 }
 return {...state,columns};
}
// 彻底移除（取消选择）：摘出纵队并从 ships 名单删除。
function dropShip(state:EditorState,shipId:string):EditorState{
 return {...detachShip(state,shipId),ships:state.ships.filter(ship=>ship.id!==shipId)};
}

// 取两艘散舰（各自单独成列）开一列新分队：先落者为领舰（index0）。
// 已存在 ≥4 支 ≥2 舰编队（真实模式上限）或任一方不是散舰时不动。
export function pairSolosIntoWell(state:EditorState,side:Side,leadId:string,followerId:string):EditorState{
 if(!leadId||!followerId||leadId===followerId)return state;
 const existing=state.columns[side];
 const leaderSolo=existing.find(column=>column.shipIds.length===1&&column.shipIds[0]===leadId);
 const followerSolo=existing.find(column=>column.shipIds.length===1&&column.shipIds[0]===followerId);
 if(!leaderSolo||!followerSolo)return state;
 if(existing.filter(column=>column.shipIds.length>=2).length>=MAX_WELLS_PER_SIDE)return state;
 const lead=shipById(state,leadId);
 const without=detachShip(detachShip(state,leadId),followerId);
 const columns=[...without.columns[side]];
 columns.push(makeColumn(side,[leadId,followerId],columns.length,lead?.heading??1));
 return {...without,columns:{...without.columns,[side]:columns}};
}

export function setColumnFlag(state:EditorState,side:Side,columnId:string,field:"flagshipId"|"reserveId",shipId:string):EditorState{
 return {...state,columns:{...state.columns,[side]:state.columns[side].map(column=>{
  if(column.columnId!==columnId)return column;
  if(!column.shipIds.includes(shipId))return column;
  const patch={flagshipId:column.flagshipId,reserveId:column.reserveId};
  patch[field]=shipId;
  if(field==="flagshipId"&&patch.flagshipId===patch.reserveId)
   patch.reserveId=column.shipIds.find(id=>id!==patch.flagshipId)??shipId;
  if(field==="reserveId"&&patch.reserveId===patch.flagshipId)
   patch.flagshipId=column.shipIds.find(id=>id!==patch.reserveId)??shipId;
  return {...column,...patch};
 })}};
}

export function patchColumn(state:EditorState,side:Side,columnId:string,patch:Partial<EditorColumn>):EditorState{
 return {...state,columns:{...state.columns,[side]:state.columns[side].map(column=>column.columnId===columnId?{...column,...patch}:column)}};
}

// 在 shipId 处拆列：其与之后的成员进入新列（领舰 index0 不能拆出）。
export function splitColumnAt(state:EditorState,side:Side,columnId:string,shipId:string):EditorState{
 const found=state.columns[side].find(column=>column.columnId===columnId);
 if(!found)return state;
 const index=found.shipIds.indexOf(shipId);
 if(index<1)return state;
 const head=found.shipIds.slice(0,index);
 const tail=found.shipIds.slice(index);
 const columns=[...state.columns[side]];
 const at=columns.findIndex(column=>column.columnId===columnId);
 const fresh={...found,columnId:`${side}-split-${Date.now().toString(36)}`,
   shipIds:tail,flagshipId:tail[0],reserveId:tail[1]??tail[0],anchor:defaultAnchor(side,columns.length)};
 columns[at]={...found,shipIds:head,flagshipId:head[0],reserveId:head[1]??head[0]};
 columns.splice(at+1,0,fresh);
 return {...state,columns:{...state.columns,[side]:columns}};
}

// 把 shipId 移入目标列（若目标为 null 则新起一列散舰）。
export function moveShipInto(state:EditorState,shipId:string,targetColumnId:string|null,side:Side):EditorState{
 const member=shipById(state,shipId);
 if(!member||member.side!==side)return state;
 const without=detachShip(state,shipId);
 const columns=[...without.columns[side]];
 if(targetColumnId===null){
  columns.push(makeColumn(side,[shipId],columns.length,member.heading));
 }else{
  const at=columns.findIndex(column=>column.columnId===targetColumnId);
  if(at<0)return state;
  columns[at]={...columns[at],shipIds:[...columns[at].shipIds,shipId]};
 }
 return {...without,columns:{...without.columns,[side]:columns}};
}

export function reorderInColumn(state:EditorState,side:Side,columnId:string,shipId:string,direction:-1|1):EditorState{
 return {...state,columns:{...state.columns,[side]:state.columns[side].map(column=>{
  if(column.columnId!==columnId)return column;
  const index=column.shipIds.indexOf(shipId);
  const target=index+direction;
  if(index<0||target<0||target>=column.shipIds.length)return column;
  const shipIds=[...column.shipIds];
  [shipIds[index],shipIds[target]]=[shipIds[target],shipIds[index]];
  return {...column,shipIds};
 })}};
}

// 把该列并入上一列（收编多余队，保证每侧 ≤ MAX_WELLS_PER_SIDE 队）。
export function mergeColumnUp(state:EditorState,side:Side,columnId:string):EditorState{
 const list=state.columns[side];
 const at=list.findIndex(column=>column.columnId===columnId);
 if(at<1)return state;
 const upper=list[at-1];
 const moving=list[at];
 const columns=[...list];
 columns[at-1]={...upper,anchor:upper.anchor??moving.anchor,shipIds:[...upper.shipIds,...moving.shipIds]};
 columns.splice(at,1);
 return {...state,columns:{...state.columns,[side]:columns}};
}

// —— 真实编队能力 ——
// 直接对已保存剧本体判定（StartScreen 选自定义剧时用，无需重建 EditorState）。
export function bodyRealisticCapable(body:{ships:{id:string;side:Side}[];formations?:Record<Side,CustomFormation[]>}):boolean{
 for(const side of SIDES){
  const owned=body.ships.filter(ship=>ship.side===side);
  if(owned.length<2)return false;
  const list=body.formations?.[side]??[];
  if(list.length<1||list.length>MAX_WELLS_PER_SIDE)return false;
  if(!list.every(formation=>formation.ship_ids.length>=2))return false;
  const covered=new Set<string>();
  list.forEach(formation=>formation.ship_ids.forEach(id=>covered.add(id)));
  if(covered.size!==owned.length)return false;
  if(!owned.every(ship=>covered.has(ship.id)))return false;
 }
 return true;
}
export function sideRealisticCapable(state:EditorState,side:Side):boolean{
 const columns=state.columns[side];
 if(columns.length<1||columns.length>MAX_WELLS_PER_SIDE)return false;
 if(!columns.every(column=>column.shipIds.length>=2))return false;
 const owned=sideShips(state,side).length;
 const listed=columns.reduce((total,column)=>total+column.shipIds.length,0);
 return owned>0&&owned===listed;
}
export function realisticCapable(state:EditorState):boolean{
 return SIDES.every(side=>sideRealisticCapable(state,side));
}

// —— 纵队布局 ——
export interface DeployedColumn{column:EditorColumn;side:Side;cells:Axial[];memberByCell:Map<string,string>}
export function computeLayout(state:EditorState):{columns:DeployedColumn[];errors:string[]}{
 const columns:DeployedColumn[]=[];
 const errors:string[]=[];
 const occupied=new Map<string,string>();
 for(const side of SIDES){
  for(const column of state.columns[side]){
   if(column.shipIds.length<1)continue;
   if(!column.anchor){errors.push(`${column.name} 还没有锚点，请先在地图上放下`);continue}
   let cells:Axial[]|null=null;
   try{cells=asternColumn(column.anchor,column.heading,column.spacing,column.shipIds.length)}
   catch{cells=null}
   if(!cells){errors.push(`${column.name}：纵队会伸出地图边缘，把锚点往中间拖`);continue}
   const memberByCell=new Map<string,string>();
   cells.forEach((cell,index)=>memberByCell.set(hexLabel(cell),column.shipIds[index]));
   for(const cell of cells){
    const key=hexLabel(cell);
    if(occupied.has(key))errors.push(`${column.name} 在 ${key} 与其他舰船重叠`);
   }
   cells.forEach(cell=>occupied.set(hexLabel(cell),column.columnId));
   columns.push({column,side,cells,memberByCell});
  }
 }
 return {columns,errors};
}

// 拖拽试探：目标列放到 anchor 是否合法（越界 / 与他列占用格重叠）。
export function tryAnchor(state:EditorState,columnId:string,anchor:Axial):{cells:Axial[]|null;reason:string|null}{
 const found=columnById(state,columnId);
 if(!found)return {cells:null,reason:null};
 const column=found.column;
 let cells:Axial[]|null=null;
 try{cells=asternColumn(anchor,column.heading,column.spacing,column.shipIds.length)}
 catch{cells=null}
 if(!cells)return {cells:null,reason:"纵队会伸出地图边缘"};
 const other=new Set<string>();
 for(const side of SIDES)for(const otherColumn of state.columns[side]){
  if(otherColumn.columnId===columnId)continue;
  if(!otherColumn.anchor)continue;
  try{
   const otherCells=asternColumn(otherColumn.anchor,otherColumn.heading,otherColumn.spacing,otherColumn.shipIds.length);
   otherCells.forEach(cell=>other.add(hexLabel(cell)));
  }catch{/* 原列问题由 computeLayout 提示 */}
 }
 const used=new Set<string>();
 for(const cell of cells){
  const key=hexLabel(cell);
  if(other.has(key)||used.has(key))return {cells:null,reason:`${key} 已被占用`};
  used.add(key);
 }
 return {cells,reason:null};
}

// —— 汇总成可保存剧本（含推导的每舰坐标与航向） ——
export interface ScenarioMeta{
 title:string;turns:number;visibility:{axis:number;allies:number};optional_rules:string[];description:string;recommended_mode:RecommendedMode;
 // 可选地图尺寸（缺省 = 标准 46×39/印刷 34×27，保存时不写键、逐字节不变）。
 mapColumns?:number;mapRows?:number;printedColumns?:number;printedRows?:number;
}
export function buildPayload(state:EditorState,meta:ScenarioMeta):
 {body:CustomScenarioDefinition;errors:string[];realisticCapable:boolean}{
 const layout=computeLayout(state);
 const errors=[...layout.errors];
 const capable=realisticCapable(state);
 const positionByShip=new Map<string,string>();
 const headingByShip=new Map<string,number>();
 for(const deployed of layout.columns){
  const heading=deployed.column.heading;
  deployed.column.shipIds.forEach((shipId,index)=>positionByShip.set(shipId,hexLabel(deployed.cells[index])));
  deployed.column.shipIds.forEach(shipId=>headingByShip.set(shipId,heading));
 }
 const ships=state.ships.map(ship=>{
  const position=positionByShip.get(ship.id);
  if(!position){errors.push(`${ship.name} 还没有可保存的位置`);return null}
  return {id:ship.id,side:ship.side,position,heading:headingByShip.get(ship.id)??ship.heading,
    speed:ship.speed,asset:ship.asset};
 }).filter((ship):ship is NonNullable<typeof ship>=>ship!==null);
 const formations:Record<Side,CustomFormation[]>={axis:[],allies:[]};
 if(capable){
  for(const side of SIDES){
   let number=1;
   for(const column of state.columns[side]){
    if(column.shipIds.length<2)continue;
    formations[side].push({
     formation_id:column.columnId,
     name:column.name||`${sideLabel(side)}第${number}队`,
     ship_ids:column.shipIds,leader_id:column.shipIds[0],
     flagship_id:column.flagshipId||column.shipIds[0],
     reserve_flagship_id:column.reserveId||column.shipIds[1]||column.shipIds[0],
     spacing:column.spacing,heading:column.heading,
    });
    number+=1;
   }
  }
 }
 const body:CustomScenarioDefinition={title:meta.title,turns:meta.turns,visibility:meta.visibility,
   optional_rules:meta.optional_rules,ships,formations,
   description:meta.description,recommended_mode:meta.recommended_mode};
 const size=mapSizeOfMeta(meta);
 const isStandard=size.columns===MAP_SIZE_STANDARD.columns&&size.rows===MAP_SIZE_STANDARD.rows
   &&size.printedColumns===MAP_SIZE_STANDARD.printedColumns&&size.printedRows===MAP_SIZE_STANDARD.printedRows;
 if(!isStandard){
  // 大战场等非标准海图：明确声明尺寸；印刷区=整图（无缓冲暗区）时不写 printed_*，
  // 由后端按「非 46×39 ⇒ 整图」的缺省补齐（与地图副本生成器同形）。
  body.map_columns=size.columns;body.map_rows=size.rows;
  if(size.printedColumns!==size.columns||size.printedRows!==size.rows){
   body.printed_columns=size.printedColumns;body.printed_rows=size.printedRows;
  }
 }
 return {body,errors,realisticCapable:capable};
}

// 把已保存/模板/导入的剧本体还原成编辑状态：有编队的舰归队（领舰落点为锚点），
// 其余各成一列散舰。nameOf 用舰船目录补全显示名，未知则退回舰 id。
export function stateFromBody(body:CustomScenarioDefinition,nameOf:(shipId:string)=>string):EditorState{
 const positionById=new Map<string,string>();
 const sideById=new Map<string,Side>();
 const headingById=new Map<string,number>();
 const speedById=new Map<string,number>();
 const assetById=new Map<string,string>();
 for(const ship of body.ships){
  positionById.set(ship.id,ship.position);
  sideById.set(ship.id,ship.side);
  headingById.set(ship.id,ship.heading);
  speedById.set(ship.id,ship.speed);
  assetById.set(ship.id,ship.asset);
 }
 const ships=body.ships.map(ship=>({id:ship.id,name:nameOf(ship.id),ship_type:"",asset:assetById.get(ship.id)??"",
   side:sideById.get(ship.id)??"axis",heading:headingById.get(ship.id)??1,speed:speedById.get(ship.id)??3}));
 const columns:SideColumns={axis:[],allies:[]};
 for(const side of SIDES){
  const formations=(body.formations?.[side]??[]) as CustomFormation[];
  const used=new Set<string>();
  for(const formation of formations){
   const shipIds=formation.ship_ids.filter(id=>sideById.get(id)===side);
   if(shipIds.length<2)continue;
   shipIds.forEach(id=>used.add(id));
   const leaderLabel=positionById.get(formation.ship_ids[0]);
   let anchor:Axial|null=null;
   try{anchor=leaderLabel?hexFromLabel(leaderLabel):defaultAnchor(side,columns[side].length)}catch{anchor=defaultAnchor(side,columns[side].length)}
   columns[side].push({
    columnId:formation.formation_id,name:formation.name||`${sideLabel(side)}编队`,
    heading:formation.heading??headingById.get(shipIds[0])??1,spacing:formation.spacing,
    shipIds,flagshipId:shipIds.includes(formation.flagship_id)?formation.flagship_id:shipIds[0],
    reserveId:shipIds.includes(formation.reserve_flagship_id)&&formation.reserve_flagship_id!==formation.flagship_id?formation.reserve_flagship_id:(shipIds[1]??shipIds[0]),
    anchor});
  }
  const leftover=body.ships.filter(ship=>ship.side===side&&!used.has(ship.id));
  for(const ship of leftover){
   let anchor:Axial|null=null;
   try{anchor=hexFromLabel(ship.position)}catch{anchor=defaultAnchor(side,columns[side].length)}
   columns[side].push({columnId:`${side}-solo-${columns[side].length+1}`,name:`${nameOf(ship.id)} 单独成列`,
     heading:ship.heading,spacing:1,shipIds:[ship.id],flagshipId:ship.id,reserveId:ship.id,anchor});
  }
 }
 return {ships,columns};
}
