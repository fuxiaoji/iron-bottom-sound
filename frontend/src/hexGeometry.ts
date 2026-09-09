export const HEX_SIZE=24;
export const HEX_ROW_HEIGHT=HEX_SIZE*Math.sqrt(3);
export const PRINTED_MAP_COLUMNS=34;
export const PRINTED_MAP_ROWS=27;
export const MAP_COLUMNS=46;
export const MAP_ROWS=39;
// 固定 46×39 扩展海图尺寸，与 HexMap viewBox / screenToHex 共用。
export const MAP_W=1720;
export const MAP_H=1700;
export interface MapViewport{tx:number;ty:number;k:number}

export type Axial={q:number;r:number};

// 引擎 compass（models.direction_delta，axial 步进）：1 NE(1,-1)、2 SE(1,0)、3 S(0,1)、
// 4 SW(-1,1)、5 NW(-1,0)、6 N(0,-1)。客户端镜像，供剧本工坊的纵队排布与引擎 `_layout_for_order`
// 使用同一套几何。
const HEADING_DELTA:Record<number,Axial>={1:{q:1,r:-1},2:{q:1,r:0},3:{q:0,r:1},4:{q:-1,r:1},5:{q:-1,r:0},6:{q:0,r:-1}};

export function normalizedHeading(heading:number){return ((heading-1)%6+6)%6+1}
// 与 realistic_command._opposite 相同：(h+2)%6+1 ≡ h+3 (mod 6)，即 180° 转向。
export function hexOpposite(heading:number){return ((heading+2)%6)+1}

// —— 当前激活的棋盘尺寸 ——
// 大部分几何函数是「坐标换算」不需要知道边界；只有越界判定（stepNeighbor）、
// 像素世界范围（screenToHex / 各 SVG viewBox）依赖声明尺寸。屏幕同一时刻只展示
// 一张海图（对局视图 = 一场，剧本工坊 = 一个想定），因此在画布组件挂载/换局时
// setActiveMapSize(dims) 即可，默认 46×39 让所有既有调用逐位不变。
export interface MapSize{
 columns:number;rows:number;
 printedColumns:number;printedRows:number;
}
export interface ActiveMap extends MapSize{width:number;height:number}

let activeMap:MapSize={columns:MAP_COLUMNS,rows:MAP_ROWS,printedColumns:PRINTED_MAP_COLUMNS,printedRows:PRINTED_MAP_ROWS};

export function resetActiveMapSize():void{
 activeMap={columns:MAP_COLUMNS,rows:MAP_ROWS,printedColumns:PRINTED_MAP_COLUMNS,printedRows:PRINTED_MAP_ROWS};
}
// 把后端 Observation / CustomScenarioDefinition 的 snake_case 尺寸解析成 MapSize：
// 缺省字段回落到标准 46×39 / 印刷 34×27（与 data._scenario_map_dims 同一约定；
// 非标准整幅图缺省印刷区=整图，即无 buffer 暗区）。
export function resolveMapDims(src?:{map_columns?:number;map_rows?:number;printed_columns?:number|null;printed_rows?:number|null}|null):MapSize{
 const columns=src?.map_columns??MAP_COLUMNS;
 const rows=src?.map_rows??MAP_ROWS;
 const printedColumns=src?.printed_columns!=null?src.printed_columns:(columns===MAP_COLUMNS?PRINTED_MAP_COLUMNS:columns);
 const printedRows=src?.printed_rows!=null?src.printed_rows:(rows===MAP_ROWS?PRINTED_MAP_ROWS:rows);
 return {columns,rows,printedColumns,printedRows};
}
// dims 缺省字段保留现值；printed_* 缺省按「标准图 34×27、其他整图」补齐（同后端 _scenario_map_dims）。
export function setActiveMapSize(dims:Partial<MapSize>|null):void{
 if(dims===null){resetActiveMapSize();return}
 const columns=dims.columns??activeMap.columns;
 const rows=dims.rows??activeMap.rows;
 const printedColumns=dims.printedColumns??(columns===MAP_COLUMNS?PRINTED_MAP_COLUMNS:columns);
 const printedRows=dims.printedRows??(rows===MAP_ROWS?PRINTED_MAP_ROWS:rows);
 activeMap={columns,rows,printedColumns,printedRows};
}

// 像素世界范围：沿用现图 46×39 → 1720×1700 的留白规则（右/下补齐），大图按比例放大。
const DEFAULT_RIGHT_PAD=MAP_W-(38+(MAP_COLUMNS-1)*HEX_SIZE*1.5);          // 62
const DEFAULT_BOTTOM_PAD=MAP_H-(35+(MAP_ROWS-0.5)*HEX_ROW_HEIGHT);        // ≈64.59
let worldCache:{columns:number;rows:number;width:number;height:number}|null=null;
function activeWorld():ActiveMap{
 const m=activeMap;
 if(!worldCache||worldCache.columns!==m.columns||worldCache.rows!==m.rows){
  let maxX=-Infinity,maxY=-Infinity;
  for(let q=0;q<m.columns;q++)for(let dr=0;dr<m.rows;dr++){
   const c=hexCenter(q,dr-Math.floor(q/2));
   if(c.x>maxX)maxX=c.x;
   if(c.y>maxY)maxY=c.y;
  }
  worldCache={columns:m.columns,rows:m.rows,width:Math.round(maxX+DEFAULT_RIGHT_PAD),height:Math.round(maxY+DEFAULT_BOTTOM_PAD)};
 }
 return {...m,width:worldCache.width,height:worldCache.height};
}
export function getActiveMap():ActiveMap{return activeWorld()}
export function hexWorld():ActiveMap{return activeWorld()}
// 非标准（如 92×78 大战场）海图的初始视口：框住给定锚点集合（如当前舰位）留 ~3 格边距，
// 全图缩放级封顶 4（与手动缩放一致）。标准 46×39 不走此路径，仍用既有常量视口。
export function fitMapViewport(anchors:{q:number;r:number}[], map:ActiveMap):MapViewport{
 if(!anchors.length)return {tx:0,ty:0,k:1};
 let x0=Infinity,y0=Infinity,x1=-Infinity,y1=-Infinity;
 for(const position of anchors){
  const center=hexCenter(position.q,position.r);
  if(center.x<x0)x0=center.x;
  if(center.y<y0)y0=center.y;
  if(center.x>x1)x1=center.x;
  if(center.y>y1)y1=center.y;
 }
 const padX=HEX_SIZE*1.5*3,padY=HEX_ROW_HEIGHT*3;
 x0-=padX;y0-=padY;x1+=padX;y1+=padY;
 const spanX=Math.max(1,x1-x0),spanY=Math.max(1,y1-y0);
 const k=Math.min(4,map.width/spanX,map.height/spanY);
 return {tx:map.width/2-(x0+x1)/2*k,ty:map.height/2-(y0+y1)/2*k,k};
}

function stepNeighbor(coord:Axial,heading:number):Axial{
 const d=HEADING_DELTA[normalizedHeading(heading)];
 const q=coord.q+d.q;
 const r=coord.r+d.r;
 // 引擎按「行号」判断越界：displayRow = r + floor(q/2)（models.HexCoord.neighbor）。
 const displayRow=r+Math.floor(q/2);
 if(q<0||q>=activeMap.columns||displayRow<0||displayRow>=activeMap.rows)throw new Error("步进越出地图边缘");
 return {q,r};
}

export function walkHex(coord:Axial,heading:number,steps:number):Axial{
 if(steps===0)return coord;
 const direction=steps<0?hexOpposite(heading):heading;
 let cursor=coord;
 for(let i=0;i<Math.abs(steps);i++)cursor=stepNeighbor(cursor,direction);
 return cursor;
}

// 与 realistic_command._layout_for_order 完全一致的纵队几何：领舰停在锚点，
// 后续每艘相对上一艘沿航向尾向(astern)走 spacing 格。越界时抛错。
export function asternColumn(anchor:Axial,heading:number,spacing:number,count:number):Axial[]{
 const astern=hexOpposite(heading);
 const cells=[anchor];
 let cursor=anchor;
 for(let i=1;i<count;i++){
  for(let step=0;step<spacing;step++)cursor=stepNeighbor(cursor,astern);
  cells.push(cursor);
 }
 return cells;
}

export function displayRowToAxial(q:number,row:number){
 return row-Math.floor(q/2);
}

export function hexCenter(q:number,r:number){
 return {x:38+q*HEX_SIZE*1.5,y:35+(r+q/2)*HEX_ROW_HEIGHT};
}

export function hexDistance(a:{q:number;r:number},b:{q:number;r:number}){
 const dq=a.q-b.q,dr=a.r-b.r;
 return (Math.abs(dq)+Math.abs(dr)+Math.abs(dq+dr))/2;
}

// 重复字母制列标签（与后端 models.index_to_column 同一公式）：A..Z、AA..ZZ、
// AAA..ZZZ、AAAA..。q=45→TT、q=51→ZZ、q=91→NNNN。标准 46 列内与旧实现一致。
export function columnLabel(q:number){
 if(!Number.isInteger(q)||q<0)throw new Error(`Invalid map column ${q}`);
 return String.fromCharCode(65+(q%26)).repeat(1+Math.floor(q/26));
}

export function hexLabel(coord:{q:number;r:number}){
 return `${columnLabel(coord.q)}${coord.r+Math.floor(coord.q/2)+1}`;
}

// Inverse of hexLabel: parse an engine hex label ("R16", "HH27", "NNNN78") back
// into axial coordinates. Pure geometry, no rule data. Repeated-letter columns
// cover q 0..127 (length 1..5) and rows up to 128.
export function hexFromLabel(label:string){
 const match=/^([A-Za-z]+)(\d{1,3})$/.exec(label.trim().toUpperCase());
 if(!match)throw new Error(`Invalid hex label ${label}`);
 const letters=match[1];
 if(![...letters].every(ch=>ch===letters[0]))throw new Error(`Invalid map column ${match[1]}`);
 const column=(letters.length-1)*26+(letters.charCodeAt(0)-65);
 const displayRow=Number.parseInt(match[2],10)-1;
 return {q:column,r:displayRow-Math.floor(column/2)};
}

// IBS-M-MAIN compass: 1 NE, 2 SE, 3 S, 4 SW, 5 NW, 6 N. Counter artwork's
// printed bow arrow points left (180 degrees), so rotate that arrow onto the
// corresponding edge-centre vector.
export function headingRotation(heading:number){
 return (150+((heading-1)%6+6)%6*60)%360;
}

export function headingVector(heading:number,length=1){
 const radians=(180+headingRotation(heading))*Math.PI/180;
 return {x:Math.cos(radians)*length,y:Math.sin(radians)*length};
}

// The source torpedo artwork points to direction 5 (north-west) before rotation.
export function torpedoCounterRotation(heading:number){
 return (((heading-5)%6+6)%6)*60;
}

// Source map IBS-M-MAIN uses flat-top odd-q: B/D/... sit half a row below A/C/....
const even=hexCenter(0,displayRowToAxial(0,0));
const odd=hexCenter(1,displayRowToAxial(1,0));
if(Math.abs((odd.y-even.y)-HEX_ROW_HEIGHT/2)>1e-9)throw new Error("odd-q projection invariant failed");
const compassRotations=[150,210,270,330,30,90];
if(compassRotations.some((rotation,index)=>headingRotation(index+1)!==rotation))throw new Error("IBS-M-MAIN heading compass invariant failed");
const torpedoRotations=[120,180,240,300,0,60];
if(torpedoRotations.some((rotation,index)=>torpedoCounterRotation(index+1)!==rotation))throw new Error("torpedo counter heading invariant failed");
if(hexLabel({q:17,r:7})!=="R16"||hexLabel({q:16,r:7})!=="Q16"||hexLabel({q:0,r:0})!=="A1"||hexLabel({q:33,r:10})!=="HH27")throw new Error("IBS-M-MAIN coordinate label invariant failed");
if(hexLabel({q:45,r:16})!=="TT39"||hexLabel(hexFromLabel("TT39"))!=="TT39"||hexLabel(hexFromLabel("HH27"))!=="HH27"||hexFromLabel(hexLabel({q:17,r:7})).q!==17||hexFromLabel("R16").r!==7)throw new Error("fixed expanded map round-trip invariant failed");
// 大战场编解码断点（92×78 全海图）必须与后端 models 一致。
if(hexLabel({q:91,r:32})!=="NNNN78"||hexLabel(hexFromLabel("NNNN78"))!=="NNNN78"||hexFromLabel("NNNN1").q!==91)throw new Error("big-map label codec invariant failed");

// 从 SVG 客户端坐标反推六角格（逆 hexCenter，取最近格心并夹在地图内）。
// viewport 为地图 <g> 的 translate/scale：先按 viewBox "xMidYMid meet" 还原用户单位，
// 再施加 (v - t)/k 逆变换回到地图世界坐标。尺寸取当前激活海图。
export function screenToHex(svg:SVGSVGElement,clientX:number,clientY:number,viewport:MapViewport):Axial|null{
 const world=activeWorld();
 const rect=svg.getBoundingClientRect();
 if(rect.width===0||rect.height===0)return null;
 const s=Math.min(rect.width/world.width,rect.height/world.height);
 const ox=(rect.width-world.width*s)/2;
 const oy=(rect.height-world.height*s)/2;
 const ux=(clientX-rect.left-ox)/s;
 const uy=(clientY-rect.top-oy)/s;
 const vx=(ux-viewport.tx)/viewport.k;
 const vy=(uy-viewport.ty)/viewport.k;
 const q0=Math.round((vx-38)/(HEX_SIZE*1.5));
 const r0=Math.round((vy-35)/HEX_ROW_HEIGHT-q0/2);
 let best:Axial|null=null;let bestDistance=Infinity;
 for(let dq=-1;dq<=1;dq++)for(let dr=-1;dr<=1;dr++){
  const q=q0+dq,r=r0+dr;
  if(q<0||q>=world.columns)continue;
  const displayRow=r+Math.floor(q/2);
  if(displayRow<0||displayRow>=world.rows)continue;
  const center=hexCenter(q,r);
  const distance=Math.hypot(center.x-vx,center.y-vy);
  if(distance<bestDistance){bestDistance=distance;best={q,r}}
 }
 return best;
}
