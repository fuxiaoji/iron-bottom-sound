import type {Ship} from "./types";
import {counterAssetUrl} from "./assets";
import {columnLabel,displayRowToAxial,headingRotation,hexCenter,HEX_SIZE} from "./hexGeometry";
const points=(cx:number,cy:number)=>Array.from({length:6},(_,i)=>{const a=Math.PI/180*(60*i);return `${cx+HEX_SIZE*Math.cos(a)},${cy+HEX_SIZE*Math.sin(a)}`}).join(" ");
export function HexMap({ships,onSelect}:{ships:Ship[];onSelect:(ship:Ship)=>void}){
 const hexes=[];for(let q=0;q<34;q++)for(let row=0;row<27;row++){const r=displayRowToAxial(q,row);const center=hexCenter(q,r);hexes.push(<g key={`${q}:${r}`}><polygon points={points(center.x,center.y)}/><text x={center.x} y={center.y+3}>{columnLabel(q)}{row+1}</text></g>) }
 return <div className="map-frame"><svg viewBox="0 0 1280 1180" role="img" aria-label="A 至 HH、1 至 27 六角格战术地图"><g className="hexes">{hexes}</g>{ships.filter(s=>s.position&&!s.sunk).map(s=>{const p=s.position!;const center=hexCenter(p.q,p.r);const rotation=headingRotation(s.heading);return <g className={`counter ${s.side}`} key={s.id} transform={`translate(${center.x} ${center.y}) rotate(${rotation})`} onClick={()=>onSelect(s)}><title>{s.name} · 舰首 {s.heading}</title>{s.asset&&<image href={counterAssetUrl(s.asset)} x="-22" y="-14" width="44" height="28" preserveAspectRatio="xMidYMid meet"/>}<path className="bow-pointer" d="M 25 0 L 17 -5 L 17 5 Z"/><text transform={`rotate(${-rotation})`} y="30">{s.name}</text></g>})}</svg></div>
}
