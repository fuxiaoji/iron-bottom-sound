import {useEffect} from "react";
import {counterAssetUrl} from "./assets";
import type {Event,TurnBattleReport} from "./types";

const phaseNames:Record<string,string>={contact_setup:"隐蔽部署",reinforcement:"增援",movement_planning:"移动计划",torpedo_planning:"鱼雷计划",movement_resolution:"同步移动",gunnery:"炮击",torpedo_effects:"鱼雷效果",fire_end:"起火与回合结束",complete:"想定结束"};
const administrative=new Set(["orders_submitted","phase_changed","game_created"]);

const groups=[
 {title:"航行、接触与碰撞",matches:(event:Event)=>/movement|moved|reinforcement|contact|collision/.test(event.type)},
 {title:"炮击与命中",matches:(event:Event)=>/gun_|gunnery|star_shell|searchlight|smoke|malfunction/.test(event.type)},
 {title:"鱼雷行动与效果",matches:(event:Event)=>/torpedo/.test(event.type)},
 {title:"损伤、火灾与沉没",matches:(event:Event)=>/damage|fire_check|sunk|wreck|destroyed/.test(event.type)},
 {title:"回合结果与胜负",matches:(event:Event)=>/victory|score|scenario/.test(event.type)},
];

function facts(events:Event[]){
 const salvoes=events.filter(event=>event.type==="gun_mount_attack");
 const hits=salvoes.reduce((total,event)=>total+(typeof event.payload?.hits==="number"?event.payload.hits:0),0);
 return {salvoes:salvoes.length,hits,torpedoes:events.filter(event=>event.type==="torpedo_result").length,fires:events.filter(event=>event.type==="fire_check").length,sunk:events.filter(event=>event.type==="ship_sunk").length};
}

function EventRow({event}:{event:Event}){
 return <li><div><span>{phaseNames[event.phase]??event.phase}</span><b>{event.message}</b></div>{event.dice&&<small>掷骰 {event.dice.notation}：{event.dice.raw}{event.dice.adjusted!=null&&event.dice.adjusted!==event.dice.raw?` → 修正后 ${event.dice.adjusted}`:""}</small>}{event.rule&&<code>{event.rule.rule_id}{event.rule.pdf_page?` · 规则书 p.${event.rule.pdf_page}`:""}{event.rule.section?` · ${event.rule.section}`:""}</code>}</li>;
}

function attackStories(events:Event[]){
 const attacks=events.filter(event=>event.type==="gun_mount_attack"||event.type==="torpedo_attack");
 return attacks.map((attack,index)=>{
  const next=attacks[index+1]?.sequence??Number.POSITIVE_INFINITY;
  const results=events.filter(event=>event.sequence>attack.sequence&&event.sequence<next&&["gunnery_result","torpedo_result","special_damage","ship_sunk"].includes(event.type));
  const hits=typeof attack.payload?.hits==="number"?attack.payload.hits:0;
  return {attack,results,hits};
 });
}

function resultIcon(event:Event){
 if(event.type==="ship_sunk")return "沉没中.png";
 const serialized=JSON.stringify(event.payload??{});
 return /fire|火/.test(serialized)?"起火.png":null;
}

export function BattleReportModal({report,onClose}:{report:TurnBattleReport;onClose:()=>void}){
 useEffect(()=>{const close=(event:KeyboardEvent)=>{if(event.key==="Escape")onClose()};window.addEventListener("keydown",close);return()=>window.removeEventListener("keydown",close)},[onClose]);
 const publicEvents=report.events.filter(event=>!administrative.has(event.type));
 const summary=facts(publicEvents);
 const assigned=new Set<number>();
 const sections=groups.map(group=>{const events=publicEvents.filter(event=>group.matches(event));events.forEach(event=>assigned.add(event.sequence));return {...group,events}});
 const other=publicEvents.filter(event=>!assigned.has(event.sequence));
 const stories=attackStories(publicEvents);
 return <div className="report-backdrop" role="presentation" onMouseDown={event=>{if(event.currentTarget===event.target)onClose()}}><section className="battle-report" role="dialog" aria-modal="true" aria-labelledby="battle-report-title"><header><div><p className="eyebrow">AFTER ACTION REPORT</p><h2 id="battle-report-title">第 {report.turn} 回合结算战报</h2><p>{report.scenarioTitle} · 谁攻击了谁、造成了什么结果</p></div><button type="button" aria-label="关闭战报" onClick={onClose}>关闭 ×</button></header><div className="report-summary"><div><span>炮击齐射</span><b>{summary.salvoes}</b></div><div><span>炮弹命中</span><b>{summary.hits}</b></div><div><span>鱼雷效果</span><b>{summary.torpedoes}</b></div><div><span>火灾检定</span><b>{summary.fires}</b></div><div><span>沉没</span><b>{summary.sunk}</b></div></div><div className="report-score"><span>轴心 {report.score.axis??0} VP</span><span>同盟 {report.score.allies??0} VP</span>{report.victoryReason&&<strong>{report.winner?`${report.winner==="axis"?"轴心":"同盟"}胜利：`:""}{report.victoryReason}</strong>}</div><div className="report-sections">{stories.length>0&&<section className="engagement-report"><h3>逐舰攻击结算<small>{stories.length} 次攻击</small></h3><div className="engagement-cards">{stories.map(({attack,results,hits})=><article className={hits?"hit":"miss"} key={attack.sequence}>{attack.type==="torpedo_attack"&&<img src={counterAssetUrl("鱼雷2（日）.png")} alt="鱼雷攻击"/>}<div className="attack-head"><span>{attack.type==="torpedo_attack"?"鱼雷齐射":"舰炮齐射"}</span><b>{attack.message}</b>{attack.dice&&<small>{attack.dice.notation} {attack.dice.raw}{attack.dice.adjusted!=null&&` → ${attack.dice.adjusted}`}</small>}</div><div className="attack-outcome">{results.length?results.map(result=>{const icon=resultIcon(result);return <div key={result.sequence}>{icon&&<img src={counterAssetUrl(icon)} alt="状态"/>}<span>{result.message}</span>{result.dice&&<small>{result.dice.notation} {result.dice.raw}{result.dice.adjusted!=null&&` → ${result.dice.adjusted}`}</small>}</div>}):<strong>{hits===0?"水柱落空，目标未受损。":"命中已记录，本次没有额外公开损伤结果。"}</strong>}</div><code>{attack.rule?.rule_id}{attack.rule?.pdf_page?` · p.${attack.rule.pdf_page}`:""}</code></article>)}</div></section>}{sections.filter(section=>section.events.length>0).map(section=><section key={section.title}><h3>{section.title}<small>{section.events.length} 项</small></h3><ol>{section.events.map(event=><EventRow event={event} key={event.sequence}/>)}</ol></section>)}{other.length>0&&<section><h3>其他公开裁决<small>{other.length} 项</small></h3><ol>{other.map(event=><EventRow event={event} key={event.sequence}/>)}</ol></section>}{publicEvents.length===0&&<p className="empty-plan">本回合没有可向当前阵营公开的裁决事件。</p>}</div><footer><p>战报只显示当前阵营可观察的引擎事件；隐藏损伤和秘密计划不会出现在这里。</p><button type="button" onClick={onClose}>读完战报，继续游戏</button></footer></section></div>;
}
