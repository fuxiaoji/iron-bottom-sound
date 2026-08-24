import {counterAssetUrl} from "./assets";
import type {Ship} from "./types";

const arcNames:Record<string,string>={bow:"艏",stern:"艉",port:"左",starboard:"右"};
const arcLabel=(arcs:string[])=>arcs.map(arc=>arcNames[arc]??arc).join("·");
const phaseNames:Record<string,string>={gunnery:"炮击",torpedo_effects:"鱼雷",fire_end:"火灾/回合末",movement_resolution:"碰撞"};

function CombatColumn({ship,direction,title}:{ship:Ship;direction:"inflicted"|"received";title:string}){
 const entries=ship.combat_history.filter(entry=>entry.direction===direction).slice(-8).reverse();
 return <section className={`combat-ledger ${direction}`}><h3>{title}<small>{entries.length?`最近 ${entries.length} 项`:"尚无记录"}</small></h3>{entries.length?<ol>{entries.map(entry=><li key={`${direction}-${entry.sequence}`}><div><b>T{entry.turn} · {phaseNames[entry.phase]??entry.phase}</b>{entry.related_ship_name&&<span>{direction==="inflicted"?"目标":"来源"}：{entry.related_ship_name}</span>}</div><p>{entry.message}</p><footer>{entry.dice&&<span>{entry.dice.notation} {entry.dice.raw}{entry.dice.adjusted!=null&&entry.dice.adjusted!==entry.dice.raw?` → ${entry.dice.adjusted}`:""}</span>}{entry.rule&&<code>{entry.rule.rule_id}{entry.rule.pdf_page?` · p.${entry.rule.pdf_page}`:""}</code>}</footer></li>)}</ol>:<p className="empty-plan">{direction==="inflicted"?"本舰还没有公开战果。":"本舰还没有受到公开攻击或损伤。"}</p>}</section>;
}

export function ShipStatusCard({ship}:{ship:Ship|undefined}){
 if(!ship)return <section className="ship-status"><h2>舰船记录表</h2><p className="empty-plan">点击地图上的己方棋子查看记录。</p></section>;
 const hull=ship.hull??0,maxHull=ship.max_hull??0,maxSpeed=ship.max_speed??0;
 return <section className="ship-status record-strip">
  <h2>舰船记录表</h2>
  <div className="record-title">{ship.asset&&<img src={counterAssetUrl(ship.asset)} alt={`${ship.name} 棋子`}/>}<div><h3>{ship.name}</h3><p>{ship.ship_type} · 舰首方向 <strong>{ship.heading}</strong></p></div><span className={`readiness ${ship.sunk?"bad":""}`}>{ship.sunk?"沉没":ship.fired?"已开火":"可行动"}</span></div>
  <div className="record-tracks">
   <div><span>舰体</span><b>{ship.hull??"?"}/{ship.max_hull??"?"}</b><div className="box-track hull-track" aria-label={`舰体 ${hull}/${maxHull}`}>{Array.from({length:maxHull},(_,index)=><i className={index<hull?"intact":"lost"} key={index}>{index<hull?"":"×"}</i>)}</div></div>
   <div><span>速度循环上限</span><b>{ship.max_speed??"?"} MF</b>{maxSpeed>0?<div className="box-track speed-track" aria-label={`速度循环上限 ${maxSpeed}`}>{Array.from({length:maxSpeed+1},(_,speed)=><i className={speed===ship.current_speed?"current":""} key={speed}>{speed}</i>)}</div>:<em>隐藏</em>}</div>
   <div className="condition-row"><span>上回合实际消耗 <b>{ship.current_speed} MF</b></span><span>本回合合法消耗 <b>{ship.min_legal_speed??"?"}–{ship.max_legal_speed??"?"} MF</b></span><span>火灾 <b>{ship.fire_markers}</b></span></div>
  </div>
  <div className="ship-diagram" aria-label="舰体炮位与鱼雷配置"><span className="bow-label">舰艏 ▶</span><div className="hull-silhouette"/><div className="mount-line">{ship.gun_mounts.map(mount=><div className={`mount-token ${mount.destroyed?"destroyed":mount.fired_this_phase?"used":""}`} key={mount.id} title={`${mount.id} · ${arcLabel(mount.arcs)}`}><b>{mount.id}</b><span>GF {mount.firepower}</span><small>{mount.caliber}&quot; · {arcLabel(mount.arcs)}</small></div>)}</div>{ship.gun_mounts.length===0&&<p className="empty-plan">炮位记录未向本阵营公开。</p>}</div>
  <div className="record-legend"><span><i className="sample ready"/>可用</span><span><i className="sample used"/>已射击</span><span><i className="sample destroyed"/>摧毁</span></div>
  <h3 className="section-label">鱼雷 {ship.torpedo_type??""}</h3>
  <div className="launcher-strip">{ship.torpedo_launchers.map(launcher=><div className={`launcher-token ${launcher.destroyed?"destroyed":""}`} key={launcher.id}><b>{launcher.id}</b><span>{arcLabel(launcher.arcs)}</span><div className="torpedo-pips" aria-label={`已装填 ${launcher.loaded}`}>{Array.from({length:launcher.torpedoes},(_,index)=><i className={index<launcher.loaded?"loaded":"empty"} key={index}/>)}</div><small>备雷 {launcher.reloads_remaining}{launcher.reload_turns_remaining?` · 装填剩余 ${launcher.reload_turns_remaining} 回合`:""}</small></div>)}</div>
  {ship.torpedo_launchers.length===0&&<p className="empty-plan">无鱼雷发射器。</p>}
  <div className="combat-ledgers"><CombatColumn ship={ship} direction="inflicted" title="本舰战果"/><CombatColumn ship={ship} direction="received" title="受伤与攻击来源"/></div>
 </section>;
}
