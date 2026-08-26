import {useEffect,useRef,useState} from "react";
import {battleReportDownloadUrl,battleReportImageUrl} from "./api";
import type {BattleReport,BattleReportTurnEvent} from "./types";

const phaseNames:Record<string,string>={contact_setup:"隐蔽部署",reinforcement:"增援",movement_planning:"移动计划",torpedo_planning:"鱼雷计划",movement_resolution:"同步移动",gunnery:"炮击",torpedo_effects:"鱼雷效果",fire_end:"起火与回合结束",complete:"想定结束"};
const sideNames:Record<string,string>={axis:"轴心",allies:"同盟"};
const modeNames:Record<string,string>={hotseat:"同机热座",tutorial:"新手教学",vs_ai:"人机大战",llm:"对战 DeepSeek"};
const administrative=new Set(["orders_submitted","phase_changed","game_created"]);

const groups=[
 {title:"航行、接触与碰撞",matches:(event:BattleReportTurnEvent)=>/movement|moved|reinforcement|contact|collision/.test(event.type)},
 {title:"炮击与命中",matches:(event:BattleReportTurnEvent)=>/gun_|gunnery|star_shell|searchlight|smoke|malfunction/.test(event.type)},
 {title:"鱼雷行动与效果",matches:(event:BattleReportTurnEvent)=>/torpedo/.test(event.type)},
 {title:"损伤、火灾与沉没",matches:(event:BattleReportTurnEvent)=>/damage|fire_check|sunk|wreck|destroyed/.test(event.type)},
 {title:"回合结果与胜负",matches:(event:BattleReportTurnEvent)=>/victory|score|scenario/.test(event.type)},
];

function EventRow({event}:{event:BattleReportTurnEvent}){
 return <li><div><span>{phaseNames[event.phase]??event.phase}</span><b>{event.message}</b></div></li>;
}

function TurnEvents({events}:{events:BattleReportTurnEvent[]}){
 const publicEvents=events.filter(event=>!administrative.has(event.type));
 const assigned=new Set<number>();
 const sections=groups.map(group=>{const events=publicEvents.filter(event=>group.matches(event));events.forEach(event=>assigned.add(event.sequence));return {...group,events}});
 const other=publicEvents.filter(event=>!assigned.has(event.sequence));
 if(publicEvents.length===0)return <section><h3>公开事件<small>0 项</small></h3><p className="empty-plan">本回合没有公开事件。</p></section>;
 return <>{sections.filter(section=>section.events.length>0).map(section=><section key={section.title}><h3>{section.title}<small>{section.events.length} 项</small></h3><ol>{section.events.map(event=><EventRow event={event} key={event.sequence}/>)}</ol></section>)}{other.length>0&&<section><h3>其他公开事件<small>{other.length} 项</small></h3><ol>{other.map(event=><EventRow event={event} key={event.sequence}/>)}</ol></section>}</>;
}

export function BattleReportModal({report,onClose}:{report:BattleReport;onClose:()=>void}){
 const [turnIndex,setTurnIndex]=useState(report.turns.length?report.turns.length-1:0);
 const [lightbox,setLightbox]=useState<{src:string;caption:string}|null>(null);
 const downloadRef=useRef<HTMLAnchorElement>(null);
 useEffect(()=>{const close=(event:KeyboardEvent)=>{if(event.key==="Escape"){if(lightbox)setLightbox(null);else onClose()}};window.addEventListener("keydown",close);return()=>window.removeEventListener("keydown",close)},[onClose,lightbox]);
 const meta=report.meta;
 const turn=report.turns[turnIndex];
 const score=meta.score??{};
 const captureCaption=(cap:{side:string},phase:string)=>{const t=turn?.turn??meta.turn;return `第 ${t} 回合 ${phaseNames[phase]??phase} · ${sideNames[cap.side]??cap.side} 视角`};
 return <div className="report-backdrop" role="presentation" onMouseDown={event=>{if(event.currentTarget===event.target&&!lightbox)onClose()}}><section className="battle-report" role="dialog" aria-modal="true" aria-labelledby="battle-report-title"><header><div><p className="eyebrow">BATTLE REPORT</p><h2 id="battle-report-title">铁底湾战报</h2><p>{meta.scenario_title} · {modeNames[meta.mode]??meta.mode} · 第 {meta.turn}/{meta.max_turns} 回合</p></div><button type="button" aria-label="关闭战报" onClick={onClose}>关闭 ×</button></header><div className="report-score"><span>轴心 {score.axis??0} VP</span><span>同盟 {score.allies??0} VP</span>{meta.winner&&<strong>{sideNames[meta.winner]??meta.winner}胜利：{meta.victory_reason}</strong>}</div>{report.turns.length>1&&<nav className="report-tabs" role="tablist" aria-label="选择回合">{report.turns.map((t,i)=><button key={t.turn} type="button" role="tab" aria-selected={i===turnIndex} className={i===turnIndex?"active":""} onClick={()=>setTurnIndex(i)}>第 {t.turn} 回合</button>)}</nav>}<div className="report-sections">{!turn?<p className="empty-plan">本局尚未记录战报。</p>:<><section className="report-narrative"><h3>叙事战报</h3>{turn.narrative?turn.narrative.split(/\n+/).filter(Boolean).map((paragraph,index)=><p key={index}>{paragraph}</p>):<p className="empty-plan">本回合还没有叙事战报。</p>}</section>{turn.phases.map(phase=><section key={phase.phase} className="report-captures"><h3>{phaseNames[phase.phase]??phase.phase}<small>{phase.captures.length} 张</small></h3><div className="capture-row">{phase.captures.map(cap=>{const caption=captureCaption(cap,phase.phase);return <figure key={cap.side} className="capture-thumb" onClick={()=>setLightbox({src:battleReportImageUrl(meta.game_id,cap.image_path),caption})}><img src={battleReportImageUrl(meta.game_id,cap.image_path)} alt={caption} loading="lazy"/><figcaption>{sideNames[cap.side]??cap.side}视角</figcaption></figure>})}</div></section>)}<TurnEvents events={turn.events}/></>}</div><footer><p>战报为中立历史文档，展示双方公开视角；隐藏损伤与秘密计划不会出现。</p><div className="footer-actions"><a ref={downloadRef} href={battleReportDownloadUrl(meta.game_id)} download style={{display:"none"}}/><button type="button" onClick={()=>downloadRef.current?.click()}>下载战报 (.md)</button><button type="button" onClick={onClose}>读完战报，继续游戏</button></div></footer></section>{lightbox&&<div className="lightbox" onMouseDown={event=>{if(event.currentTarget===event.target)setLightbox(null)}}><figure><img src={lightbox.src} alt={lightbox.caption}/><figcaption>{lightbox.caption}</figcaption><button type="button" aria-label="关闭大图" onClick={()=>setLightbox(null)}>关闭 ×</button></figure></div>}</div>;
}
