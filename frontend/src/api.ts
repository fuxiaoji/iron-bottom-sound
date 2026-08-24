import type {Observation,Side} from "./types";
const headers=(side?:Side):Record<string,string>=>{const value:Record<string,string>={"Content-Type":"application/json"};if(side)value["X-Player-Side"]=side;return value};
export async function createGame(scenario_id:string,seed:number,mode:"hotseat"|"tutorial"="hotseat"){const r=await fetch("/api/games",{method:"POST",headers:headers(),body:JSON.stringify({scenario_id,seed,options:{mode}})});if(!r.ok)throw new Error(await r.text());return r.json()}
export async function viewGame(id:string,side:Side):Promise<Observation>{const r=await fetch(`/api/games/${id}/view`,{headers:headers(side)});if(!r.ok)throw new Error(await r.text());return r.json()}
export async function advance(id:string){const r=await fetch(`/api/games/${id}/advance`,{method:"POST",headers:headers()});if(!r.ok)throw new Error(await r.text());return r.json()}
export async function submitOrders(id:string,side:Side,batch:unknown){const r=await fetch(`/api/games/${id}/orders`,{method:"POST",headers:headers(side),body:JSON.stringify(batch)});if(!r.ok)throw new Error(await r.text());return r.json() as Promise<{valid:boolean;both_submitted:boolean;phase:string}>}
export async function suggestedOrders(id:string,side:Side){const r=await fetch(`/api/games/${id}/suggested-orders`,{headers:headers(side)});if(!r.ok)throw new Error(await r.text());return r.json()}
export async function tutorialOpponent(id:string,side:Side){const r=await fetch(`/api/games/${id}/tutorial-opponent`,{method:"POST",headers:headers(side)});if(!r.ok)throw new Error(await r.text());return r.json()}
export async function handoff(id:string){await fetch(`/api/games/${id}/handoff`,{method:"POST"})}
