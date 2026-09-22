// 命令延迟模式面板：把该模式真正新增的东西显示出来 —— 舰队总指挥视图（只有被搭载编队
// 是精确状态，其余以带年龄的报告呈现）、某个编队的本地决策与通信状态、以及报文台账。
//
// 数据全部来自两个只读端点。面板不复制任何规则常量：链路、权限、报告年龄、合法动作与
// 权重上限都由引擎下发。
import {useCallback,useEffect,useState} from "react";
import type {FleetView,FormationView,Side} from "./api";
import {fleetView,formationView} from "./api";

type Props={game:string;side:Side;turn:number;phase:string;collapsed:boolean;onToggle:()=>void};

const linkLabel:Record<string,string>={direct:"直连",relayed:"经转报",stale:"陈旧",blackout:"中断"};
const authorityLabel:Record<string,string>={fleet_directed:"总指挥直控",delegated:"受领任务",local_autonomy:"本地自主"};

const ageText=(age:number|null)=>(age===null?"未知":age===0?"本回合":`${age} 回合前`);

// 被搭载编队是精确状态：它的行必须显示**实时**位置与兵力，而不是那份过期报告
// （报告只在编成时写过一次）。否则同一块面板里"兵力 2 艘"与表格里的 3 会自相矛盾。
type Embarked={leader_id?:string;ships?:Array<Record<string,unknown>>};
function liveGuide(embarked:Embarked){
 const ships=(embarked.ships??[]).filter(s=>String(s.position??"")!=="");
 const guide=ships.find(s=>s.ship_id===embarked.leader_id)??ships[0];
 return {position:guide?String(guide.position):null,count:ships.length};
}

export function CommandDelayPanel({game,side,turn,phase,collapsed,onToggle}:Props){
 const [fleet,setFleet]=useState<FleetView|null>(null);
 const [selected,setSelected]=useState<string|null>(null);
 const [local,setLocal]=useState<FormationView|null>(null);
 const [error,setError]=useState("");

 const load=useCallback(()=>{
  fleetView(game,side).then(next=>{
   setFleet(next);setError("");
   setSelected(current=>current&&next.reports.some(item=>item.formation_id===current)?current:(next.reports[0]?.formation_id??null));
  }).catch(reason=>setError(String(reason)));
 },[game,side]);
 useEffect(()=>{load()},[load,turn,phase]);
 useEffect(()=>{
  if(!selected){setLocal(null);return}
  let active=true;
  formationView(game,side,selected).then(next=>{if(active)setLocal(next)}).catch(()=>{if(active)setLocal(null)});
  return()=>{active=false};
 },[game,side,selected,turn,phase]);

 if(collapsed)return <section className="cd-panel collapsed"><button className="cd-toggle" onClick={onToggle}>命令延迟 · 展开指挥链面板</button></section>;

 return <section className="cd-panel">
  <header className="cd-head">
   <div><span>命令延迟模式</span><h3>指挥链与通信</h3></div>
   <div className="cd-head-actions"><button className="quiet" onClick={load}>刷新</button><button className="quiet" onClick={onToggle}>收起</button></div>
  </header>
  {error&&<p className="cd-error">指挥链数据加载失败：{error}</p>}
  {fleet&&(()=>{const live=liveGuide(fleet.embarked);return <>
   <div className="cd-fleet">
    {(fleet.embarked.ship_ids?.length ?? 0) === 0 ? <div className="cd-embarked">
     <b>舰队总指挥所在编队已不在水面</b>
     <span>本视图不再有任何精确来源；其余编队（若还在）只能通过过期报告得知。</span>
    </div> : <div className="cd-embarked">
     <b>舰队总指挥在 {fleet.embarked.name ?? fleet.embarked_formation_id ?? "—"}</b>
     <span>该编队是唯一精确状态；其余编队只能通过报告得知（这是命令延迟模式的核心约束）。</span>
     <div className="cd-chips">
      <em>兵力 {fleet.embarked.ship_ids?.length ?? 0} 艘</em>
      <em>队形 {fleet.embarked.movement_style === "move_together" ? "整队机动" : "尾随"}</em>
      <em>几何 {fleet.embarked.geometry_kind === "straight_line" ? "斜队/横队" : "纵队"}</em>
      <em>可见接触 {fleet.contacts.length}</em>
     </div>
    </div>}
    {fleet.reports.length===0?<p className="muted">本方已无在编编队。</p>:
    <table className="cd-reports">
     <thead><tr><th>编队</th><th>链路</th><th>权限</th><th>报告年龄</th><th>引导位置</th><th>兵力</th><th>命令</th></tr></thead>
     <tbody>
      {fleet.reports.map(report=>{const exact=report.is_source_of_truth;return <tr key={report.formation_id} className={exact?"exact":""}
        onClick={()=>setSelected(report.formation_id)}>
       <td>{report.name}{exact&&<em className="cd-exact">精确</em>}</td>
       <td><span className={`cd-link cd-link-${report.link_status}`}>{linkLabel[report.link_status]??report.link_status}</span></td>
       <td>{authorityLabel[report.authority]??report.authority}</td>
       <td>{exact?"本舰所在（实时）":ageText(report.age_turns)}</td>
       <td>{exact?live.position??"—":report.guide_label??"—"}</td>
       <td>{exact?live.count:report.ship_count??"—"}</td>
       <td>{exact?"—":report.active_order_id?"已下达":"未确认"}</td>
      </tr>})}
     </tbody>
    </table>}
   </div>
   {local&&<div className="cd-local">
    <div className="cd-local-head"><b>{local.formation_name} 的本地情报</b>
     <span>链路 {linkLabel[local.link_status]??local.link_status} · 权限 {authorityLabel[local.authority]??local.authority}</span></div>
    <div className="cd-grid">
     <div><h4>本编队</h4>
      <ul><li>舰数 {(local.formation_state.ships as unknown[]|undefined)?.length ?? 0}</li>
       <li>航向 {String(local.formation_state.heading ?? "—")} · 航速 {String(local.formation_state.speed ?? "—")}</li>
       <li>状态 {String(local.formation_state.status ?? "—")}</li></ul>
      <h4>本地接触（仅本编队自身舰只可见）</h4>
      {local.local_contacts.length===0?<p className="muted">暂无接触</p>:
       <ul>{local.local_contacts.map(c=><li key={c.ship_id}>{c.name}（{c.ship_type}）· 距离 {c.range??"—"}</li>)}</ul>}</div>
     <div><h4>生效命令</h4>
      {local.active_mission_order?<div className="cd-order">
        <b>{local.active_mission_order.mission}</b>
        <p>意图：{local.active_mission_order.commander_intent}</p>
        <p>任务：{local.active_mission_order.task_to_formation}</p>
        <p className="muted">协同：{local.active_mission_order.coordination_measures.join("；")}</p>
       </div>:<p className="muted">尚未收到已确认的作战命令，执行预令。</p>}
      <h4>通信状态</h4>
      <ul><li>可用媒介 {((local.comm_state.mediums_available as string[]|undefined)??[]).join("、")}</li>
       <li>已收报文 {local.received_messages.length}</li>
       <li>外部报告 {local.stale_external_reports.length}（年龄 {local.stale_external_reports.map(r=>ageText(r.age_turns)).join("、")||"—"}）</li></ul></div>
     <div><h4>可加权目标（上限 ±{local.local_priority_weight_limit}）</h4>
      {local.legal_target_priority_options.length===0?<p className="muted">无可加权目标</p>:
       <ul>{local.legal_target_priority_options.map(o=><li key={o.target_id}>{o.target_id} · {o.target_class} · 距离 {o.range??"—"}</li>)}</ul>}
      <h4>允许的报告动作</h4><p className="muted">{local.report_actions.join("、")}</p></div>
    </div>
    <p className="cd-note">炮位分配、射界、修正与命中由引擎选择器完成；本编队只能对上述目标附加有界优先级权重。</p>
   </div>}
   {fleet.messages.length===0&&<p className="cd-note">本局双方各只有一个编队：舰队总指挥就在其中，没有需要通信的远端编队，因此没有报文。想看通信与报告年龄，请选有多条战列线的想定（想定 1 或第二次马里亚纳海战）。</p>}
   {fleet.messages.length>0&&<div className="cd-messages">
    <h4>近期报文（本回合台账）</h4>
    <ul>{fleet.messages.slice(-8).map(m=><li key={String(m.message_id)}>
     <span className={`cd-link cd-link-${String(m.status)}`}>{String(m.status)}</span>
     {" "}{String(m.kind)} · {String(m.medium)} · 发出 T{String(m.issued_turn)} → 送达 {m.delivered_turn?`T${m.delivered_turn}`:"待投递"}
    </li>)}</ul></div>}
  </>;})()}
 </section>;
}
