import type {Ship} from "./types";
const size=24, x=(q:number)=>38+q*size*1.5, y=(q:number,r:number)=>35+(r+(q-(q&1))/2)*size*Math.sqrt(3);
const points=(cx:number,cy:number)=>Array.from({length:6},(_,i)=>{const a=Math.PI/180*(60*i);return `${cx+size*Math.cos(a)},${cy+size*Math.sin(a)}`}).join(" ");
export function HexMap({ships,onSelect}:{ships:Ship[];onSelect:(ship:Ship)=>void}){
 const hexes=[];for(let q=0;q<34;q++)for(let row=0;row<27;row++){const r=row-(q-(q&1))/2;hexes.push(<polygon key={`${q}:${r}`} points={points(x(q),y(q,r))}/>) }
 return <div className="map-frame"><svg viewBox="0 0 1280 1180" role="img" aria-label="A 至 HH、1 至 27 六角格战术地图"><g className="hexes">{hexes}</g>{ships.filter(s=>s.position&&!s.sunk).map(s=>{const p=s.position!;return <g className={`counter ${s.side}`} key={s.id} transform={`translate(${x(p.q)} ${y(p.q,p.r)}) rotate(${(s.heading-1)*60})`} onClick={()=>onSelect(s)}><path d="M 0 -14 L 12 10 L 0 6 L -12 10 Z"/><text transform={`rotate(${-(s.heading-1)*60})`} y="30">{s.name}</text></g>})}</svg></div>
}
