import {counterAssetUrl} from "./assets";
import type {Ship} from "./types";

export function ShipStatusCard({ship}:{ship:Ship|undefined}){
 if(!ship)return <section className="ship-status"><h2>舰船状态表</h2><p className="empty-plan">点击地图上的己方棋子查看记录。</p></section>;
 const hull=ship.hull??0,maxHull=ship.max_hull??0;
 return <section className="ship-status">
  <h2>舰船状态表</h2>
  <div className="ship-card-head">{ship.asset&&<img src={counterAssetUrl(ship.asset)} alt={`${ship.name} 棋子`}/>}<div><h3>{ship.name}</h3><p>{ship.ship_type} · 舰首 {ship.heading}</p></div></div>
  <dl className="status-grid"><div><dt>当前速度</dt><dd>{ship.current_speed} MF</dd></div><div><dt>本回合上限</dt><dd>{ship.max_speed??"隐藏"} MF</dd></div><div><dt>火灾</dt><dd>{ship.fire_markers}</dd></div><div><dt>状态</dt><dd>{ship.sunk?"沉没":ship.fired?"已开火":"可行动"}</dd></div></dl>
  <h3>舰体 {ship.hull??"隐藏"}/{ship.max_hull??"隐藏"}</h3>{maxHull>0&&<div className="hull-track" aria-label={`舰体 ${hull}/${maxHull}`}>{Array.from({length:maxHull},(_,index)=><span className={index<hull?"intact":"lost"} key={index}/>)}</div>}
  <h3>炮位</h3>{ship.gun_mounts.length?<table><thead><tr><th>炮位</th><th>GF</th><th>口径</th><th>射界</th><th>状态</th></tr></thead><tbody>{ship.gun_mounts.map(mount=><tr key={mount.id}><td>{mount.id}</td><td>{mount.firepower}</td><td>{mount.caliber}&quot;</td><td>{mount.arcs.join("/")}</td><td>{mount.destroyed?"摧毁":mount.fired_this_phase?"已射击":"可用"}</td></tr>)}</tbody></table>:<p className="empty-plan">未公开炮位记录。</p>}
  <h3>鱼雷 {ship.torpedo_type??""}</h3>{ship.torpedo_launchers.length?<table><thead><tr><th>发射器</th><th>装填</th><th>备雷</th><th>状态</th></tr></thead><tbody>{ship.torpedo_launchers.map(launcher=><tr key={launcher.id}><td>{launcher.id}</td><td>{launcher.loaded}</td><td>{launcher.reloads_remaining}</td><td>{launcher.destroyed?"摧毁":launcher.reload_turns_remaining?`装填 ${launcher.reload_turns_remaining}`:"可用"}</td></tr>)}</tbody></table>:<p className="empty-plan">无可用鱼雷发射器。</p>}
 </section>;
}
