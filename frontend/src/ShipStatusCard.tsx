import {counterAssetUrl} from "./assets";
import {DamageChips} from "./damageSummary";
import type {Ship} from "./types";

const arcNames:Record<string,string>={bow:"艏",stern:"艉",port:"左",starboard:"右"};
const arcLabel=(arcs:string[])=>arcs.map(arc=>arcNames[arc]??arc).join("·");
const phaseNames:Record<string,string>={gunnery:"炮击",torpedo_effects:"鱼雷",fire_end:"火灾/回合末",movement_resolution:"碰撞"};

// 火控情况：只在本方可见字段（owner-only）出现时渲染；敌方/未公开舰的内部状态不可知。
function FireControlStatus({ship}:{ship:Ship}){
 const chips:string[]=[];
 if(ship.mfc_destroyed)chips.push("射击指挥仪损毁");
 if(ship.radar_destroyed)chips.push("雷达损毁");
 if(ship.bridge_destroyed)chips.push("舰桥损毁");
 if(ship.rudder_destroyed)chips.push("舵机损毁");
 if(ship.captain_status==="wounded")chips.push("舰长负伤");
 if(ship.captain_status==="killed")chips.push("舰长阵亡");
 return <div className="condition-row fire-control"><span>火控情况</span>{chips.length?<span className="damage-chips">{chips.map((chip,index)=><span className="damage-chip flag" key={index}>{chip}</span>)}</span>:<span className="intact-note">射击指挥仪 · 舰桥 · 舵机 完好</span>}</div>;
}

function CombatColumn({ship,direction,title}:{ship:Ship;direction:"inflicted"|"received";title:string}){
 // 战果日志完整展示：不截断最近 N 条，全部按时间倒序呈现。
 const entries=ship.combat_history.filter(entry=>entry.direction===direction).reverse();
 return <section className={`combat-ledger ${direction}`}><h3>{title}<small>{entries.length?`共 ${entries.length} 项`:"尚无记录"}</small></h3>{entries.length?<ol>{entries.map(entry=><li key={`${direction}-${entry.sequence}`}><div><b>T{entry.turn} · {phaseNames[entry.phase]??entry.phase}</b>{entry.related_ship_name&&<span>{direction==="inflicted"?"目标":"来源"}：{entry.related_ship_name}</span>}</div><p>{entry.message}</p><DamageChips damage={entry.payload?.damage}/><footer>{entry.dice&&<span>{entry.dice.notation} {entry.dice.raw}{entry.dice.adjusted!=null&&entry.dice.adjusted!==entry.dice.raw?` → ${entry.dice.adjusted}`:""}</span>}{entry.rule&&<code>{entry.rule.rule_id}{entry.rule.pdf_page?` · p.${entry.rule.pdf_page}`:""}</code>}</footer></li>)}</ol>:<p className="empty-plan">{direction==="inflicted"?"本舰还没有公开战果。":"本舰还没有受到公开攻击或损伤。"}</p>}</section>;
}

export function ShipStatusCard({ship}:{ship:Ship|undefined}){
 if(!ship)return <section className="ship-status"><h2>舰船记录表</h2><p className="empty-plan">点击地图上的己方棋子查看记录。</p></section>;
 const hull=ship.hull??0,maxHull=ship.max_hull??0,maxSpeed=ship.max_speed??0;
 const speedDamageCrossed=ship.speed_damage_crossed;
 const speedDamageTrack=ship.speed_damage_track;
 return <section className="ship-status record-strip">
  <h2>舰船记录表</h2>
  <div className="record-title">{ship.asset&&<img src={counterAssetUrl(ship.asset)} alt={`${ship.name} 棋子`}/>}<div><h3>{ship.name}</h3><p>{ship.ship_type} · 舰首方向 <strong>{ship.heading}</strong></p></div><span className={`readiness ${ship.sunk?"bad":""}`}>{ship.sunk?"沉没":ship.fired?"已开火":"可行动"}</span></div>
  <div className="record-tracks">
   <div><span>舰体</span><b>{ship.hull??"?"}/{ship.max_hull??"?"}</b><div className="box-track hull-track" aria-label={`舰体 ${hull}/${maxHull}`}>{Array.from({length:maxHull},(_,index)=><i className={index<hull?"intact":"lost"} key={index}>{index<hull?"":"×"}</i>)}</div></div>
   <div><span>速度循环上限</span><b>{ship.max_speed??"?"} MF</b>{maxSpeed>0?<div className="box-track speed-track" aria-label={`速度循环上限 ${maxSpeed}`}>{Array.from({length:maxSpeed+1},(_,speed)=><i className={speed===ship.current_speed?"current":""} key={speed}>{speed}</i>)}</div>:<em>隐藏</em>}</div>
   {speedDamageTrack&&speedDamageCrossed&&<div className="speed-damage"><span>失速循环</span><b>{speedDamageCrossed.reduce((total,value)=>total+value,0)} 格</b><div className="speed-damage-track" aria-label="失速循环（已划去速度为受损格）">{speedDamageTrack.map((row,rowIndex)=><span className="cycle-row" key={rowIndex}>{row.map((value,boxIndex)=><i className={boxIndex<speedDamageCrossed[rowIndex]?"lost":""} key={boxIndex}>{boxIndex<speedDamageCrossed[rowIndex]?"×":value}</i>)}</span>)}</div></div>}
   <div className="condition-row"><span>上回合实际消耗 <b>{ship.current_speed} MF</b></span><span>本回合合法消耗 <b>{ship.min_legal_speed??"?"}–{ship.max_legal_speed??"?"} MF</b></span><span>火灾 <b>{ship.fire_markers}</b></span></div>
   {ship.max_legal_speed!=null&&<FireControlStatus ship={ship}/>}
  </div>
  <div className="ship-diagram" aria-label="舰体炮位与鱼雷配置"><span className="bow-label">舰艏 ▶</span><div className="hull-silhouette"/><div className="mount-line">{ship.gun_mounts.map(mount=>{const kind={primary:"主炮",secondary:"副炮",tertiary:"高射炮"}[mount.kind];return <div className={`mount-token ${mount.destroyed?"destroyed":mount.fired_this_phase?"used":""}`} key={mount.id} title={`${mount.id} · ${mount.caliber}" ${kind} · 装甲 ${mount.armour!=null?`${mount.armour}"`:"无"} · ${arcLabel(mount.arcs)}`}><b>{mount.id}</b><span>{kind} · GF {mount.firepower}</span><small>{mount.caliber}&quot; · 装 {mount.armour!=null?`${mount.armour}"`:"无"} · {arcLabel(mount.arcs)}</small></div>})}</div>{ship.gun_mounts.length===0&&<p className="empty-plan">炮位记录未向本阵营公开。</p>}</div>
  <div className="record-legend"><span><i className="sample ready"/>可用</span><span><i className="sample used"/>已射击</span><span><i className="sample destroyed"/>摧毁</span></div>
  <h3 className="section-label">鱼雷 {ship.torpedo_type??""}</h3>
  <div className="launcher-strip">{ship.torpedo_launchers.map(launcher=><div className={`launcher-token ${launcher.destroyed?"destroyed":""}`} key={launcher.id}><b>{launcher.id}</b><span>{arcLabel(launcher.arcs)}</span><div className="torpedo-pips" aria-label={`已装填 ${launcher.loaded}`}>{Array.from({length:launcher.torpedoes},(_,index)=><i className={index<launcher.loaded?"loaded":"empty"} key={index}/>)}</div><small>备雷 {launcher.reloads_remaining}{launcher.reload_turns_remaining?` · 装填剩余 ${launcher.reload_turns_remaining} 回合`:""}</small></div>)}</div>
  {ship.torpedo_launchers.length===0&&<p className="empty-plan">无鱼雷发射器。</p>}
  <div className="combat-ledgers"><CombatColumn ship={ship} direction="inflicted" title="本舰战果"/><CombatColumn ship={ship} direction="received" title="受伤与攻击来源"/></div>
 </section>;
}
