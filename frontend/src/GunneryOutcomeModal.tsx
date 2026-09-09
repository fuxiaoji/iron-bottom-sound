import {DamageChips,damageHullLost} from "./damageSummary";
import type {Event,Side} from "./types";

type Strike={event:Event;results:Event[]};

function strikesFor(events:Event[],attackerSide:Side):Strike[]{
 const attacks=events.filter(event=>event.type==="gun_mount_attack"&&event.payload?.attacker_side===attackerSide);
 return attacks.map((event,index)=>{const nextSequence=attacks[index+1]?.sequence??Number.POSITIVE_INFINITY;return {event,results:events.filter(result=>result.type==="gunnery_result"&&result.sequence>event.sequence&&result.sequence<nextSequence&&result.payload?.attacker===event.payload?.attacker&&result.payload?.target===event.payload?.target)}});
}

function OutcomeColumn({title,strikes,own}:{title:string;strikes:Strike[];own:boolean}){
 const hits=strikes.reduce((total,strike)=>total+Number(strike.event.payload?.hits??0),0);
 const hull=strikes.flatMap(strike=>strike.results).reduce((total,event)=>total+damageHullLost(event.payload?.damage),0);
 return <section className={`gunnery-outcome-column ${own?"own":"enemy"}`}>
  <header><h3>{title}</h3><div><b>{strikes.length}</b><span>次齐射</span><b>{hits}</b><span>发命中</span><b>{hull}</b><span>已公开船体损伤</span></div></header>
  {strikes.length===0?<p className="outcome-empty">本阶段没有炮击。</p>:<ol>{strikes.map(strike=>{const hits=Number(strike.event.payload?.hits??0);const hidden=hits>strike.results.length;return <li key={strike.event.sequence}><b>{strike.event.message}</b>{strike.results.map(result=><div key={result.sequence}><span>{String(result.payload?.target_name??"目标")}</span><DamageChips damage={result.payload?.damage}/></div>)}{hits===0&&<small>未命中</small>}{hidden&&<small className="outcome-hidden">命中结果中有 {hits-strike.results.length} 项依隐藏损伤规则未公开</small>}</li>})}</ol>}
 </section>;
}

export function GunneryOutcomeModal({events,viewer,turn,onClose}:{events:Event[];viewer:Side;turn:number;onClose:()=>void}){
 const enemy:Side=viewer==="axis"?"allies":"axis";
 return <div className="gunnery-outcome-backdrop" role="dialog" aria-modal="true" aria-label="炮击战果">
  <section className="gunnery-outcome-modal">
   <header><div><p className="eyebrow">GUNNERY AFTER ACTION</p><h2>第 {turn} 回合·炮击战果</h2><p>只汇总引擎已向当前阵营公开的命中与损伤。</p></div><button onClick={onClose}>确认战果</button></header>
   <div className="gunnery-outcome-grid"><OutcomeColumn title="我方取得的战果" strikes={strikesFor(events,viewer)} own/><OutcomeColumn title="敌方取得的战果" strikes={strikesFor(events,enemy)} own={false}/></div>
  </section>
 </div>;
}
