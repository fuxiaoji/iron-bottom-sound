import type {Observation,Side} from "./types";
const headers=(side?:Side):Record<string,string>=>{const value:Record<string,string>={"Content-Type":"application/json"};if(side)value["X-Player-Side"]=side;return value};
export async function createGame(scenario_id:string,seed:number){const r=await fetch("/api/games",{method:"POST",headers:headers(),body:JSON.stringify({scenario_id,seed})});if(!r.ok)throw new Error(await r.text());return r.json()}
export async function viewGame(id:string,side:Side):Promise<Observation>{const r=await fetch(`/api/games/${id}/view`,{headers:headers(side)});if(!r.ok)throw new Error(await r.text());return r.json()}
export async function advance(id:string){const r=await fetch(`/api/games/${id}/advance`,{method:"POST",headers:headers()});if(!r.ok)throw new Error(await r.text());return r.json()}
export async function submitStanding(id:string,side:Side,ships:string[]){const movement=ships.map(ship_id=>({ship_id,plan:"0"}));const r=await fetch(`/api/games/${id}/orders`,{method:"POST",headers:headers(side),body:JSON.stringify({side,movement,gunnery:[],torpedoes:[],smoke_ships:[]})});if(!r.ok)throw new Error(await r.text());return r.json()}
export async function handoff(id:string){await fetch(`/api/games/${id}/handoff`,{method:"POST"})}
