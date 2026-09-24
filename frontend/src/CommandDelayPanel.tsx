// 命令延迟模式的「指挥链」面板：舰队总指挥能看到什么、每个编队现在是什么状态、以及
// 报文到底走在哪条链路上。
//
// 设计原则（针对「不知道这个模式怎么玩」）：先说你在这个模式里的身份，再说本回合该做
// 什么，最后才是细节。所有规则常量都来自引擎（链路、权限、报告年龄、合法动作、权重
// 上限、投递预判），前端不复制也不猜测。
import {useCallback,useEffect,useState} from "react";
import type {CommandDelayAgentPolicy,FleetView,FormationReport,FormationView,Side} from "./api";
import {commandDelayAgentPolicy,fleetView,formationView,setCommandDelayAgentPolicy} from "./api";

type Props={
 game:string;side:Side;turn:number;phase:string;collapsed:boolean;onToggle:()=>void;
 recipient:string|null;onRecipient:(formationId:string)=>void;onOpenRules:()=>void;
};

export const linkLabel:Record<string,string>={direct:"直连",relayed:"经转报",stale:"陈旧",blackout:"中断"};
export const authorityLabel:Record<string,string>={fleet_directed:"总指挥直控",delegated:"受领任务",local_autonomy:"本地自主"};
export const mediumLabel:Record<string,string>={
 tbs_short:"TBS 短距战术",blinker:"视觉信号",wt_coded:"编码电文",wt_reencipher_relay:"转报/再加密",
 multi_hop:"复合路由",blackout:"无通路",face_to_face:"当面交办",
};
export const kindLabel:Record<string,string>={
 mission_order:"命令",amendment:"命令修订",sitrep:"态势报告",contact_report:"接触报告",
 deviation_report:"偏离报告",acknowledgement:"回执",clarification:"询问",clarification_request:"询问",
 urgent:"急电",mission_status:"任务状态",
};
export const statusLabel:Record<string,string>={
 queued:"待发",delivered:"已送达",dropped:"已丢包",expired:"超时作废",pending:"在途",
};
const confidenceLabel:Record<string,string>={CONFIRMED:"已确认",REPORTED:"据报告",INFERRED:"推断",SUSPECTED:"疑似"};

export const ageText=(age:number|null|undefined)=>(age===null||age===undefined?"未知":age===0?"本回合":`${age} 回合前`);

export function reportAgeClass(report:FormationReport){return report.is_source_of_truth?"exact":`age-${Math.min(report.age_turns??9,4)}`}

// 被搭载编队是精确状态：它的行必须显示**实时**位置与兵力，而不是那份过期报告
// （报告只在编成时写过一次）。否则同一块面板里"兵力 2 艘"与表格里的 3 会自相矛盾。
type Embarked={leader_id?:string;ships?:Array<Record<string,unknown>>};
function liveGuide(embarked:Embarked){
 const ships=(embarked.ships??[]).filter(s=>String(s.position??"")!=="");
 const guide=ships.find(s=>s.ship_id===embarked.leader_id)??ships[0];
 return {position:guide?String(guide.position):null,count:ships.length};
}

const providerLabel:Record<string,string>={deepseek:"DeepSeek",zhipu:"智谱 GLM"};

function ModelCard({game,side,onChanged}:{game:string;side:Side;onChanged:()=>void}){
 const [policy,setPolicy]=useState<CommandDelayAgentPolicy|null>(null);
 const [open,setOpen]=useState(false);
 const [key,setKey]=useState("");
 const [provider,setProvider]=useState("deepseek");
 const [model,setModel]=useState("");
 const [thinking,setThinking]=useState(true);
 const [bothSides,setBothSides]=useState(true);
 const [fleetAgent,setFleetAgent]=useState(false);
 const [busy,setBusy]=useState(false);
 const [result,setResult]=useState("");
 const [error,setError]=useState("");

 const load=useCallback(()=>{
  commandDelayAgentPolicy(game,side).then(next=>{setPolicy(next)}).catch(()=>setPolicy(null));
 },[game,side]);
 useEffect(()=>{load()},[load]);

 const label=policy?.formation_labels?.[side];
 const isModel=Boolean(label&&label.startsWith("llm:"));
 // 思考链状态直接读活策略对象（引擎下发），界面不自己记一份。
 const thinkingOn=policy?.thinking_enabled?.[side]??null;
 const budget=policy?.max_tokens?.[side]??null;
 const roleLine=(value:string|undefined)=>
  !value?"未知":value.startsWith("llm:")?`模型（${value.slice(4)}）`
   :value.includes("no API key")?"教条：服务端没有该模型的密钥"
   :value==="no-fleet-agent"?"无舰队代理":value;

 const submit=async()=>{
  setBusy(true);setError("");setResult("");
  try{
   const next=await setCommandDelayAgentPolicy(game,side,{
    api_key:key.trim()||null,
    config:{provider:provider as "deepseek"|"zhipu",model:model.trim()||undefined as unknown as string,vision_enabled:false},
    thinking_enabled:thinking,
    sides:bothSides?[]:[side],
    fleet:fleetAgent,
   });
   setPolicy(next);
   setResult(next.configured
    ? `已接入：${next.reason}。下一次推进阶段时编队会向模型请求方案；密钥只在服务进程内存里，服务重启后需重新接入。`
    : `未接入模型：${next.reason}。编队仍会行动，但按确定性教条。`);
   setKey("");
   onChanged();
  }catch(reason){setError(String(reason))}
  finally{setBusy(false)}
 };

 return <div className="cd-model">
  <div className="cd-model-head">
   <b>编队代理</b>
   <span className={isModel?"cd-badge ok":"cd-badge warn"}>{roleLine(label)}</span>
   {isModel&&thinkingOn!==null&&<span className={thinkingOn?"cd-badge order":"cd-badge"}>{thinkingOn?"思考链：开":"思考链：关"}</span>}
   {isModel&&budget?<span className="cd-badge">输出上限 {budget} tokens</span>:null}
   <button className="quiet" onClick={()=>setOpen(!open)}>{open?"收起":"接入模型…"}</button>
  </div>
  {!isModel&&!open&&<p className="cd-note">
   当前没有可用的模型密钥：各编队会**照常行动**，但按引擎的确定性教条执行，不调用模型
   （标签由引擎写入，不会把教条输出冒充为模型决策）。想看到代理自己的判断，就在这里接入。
  </p>}
  {open&&<div className="cd-model-form">
   <label>模型提供方
    <select value={provider} onChange={event=>setProvider(event.target.value)}>
     {Object.entries(providerLabel).map(([value,text])=><option key={value} value={value}>{text}</option>)}
    </select></label>
   <label>模型名（留空用默认）
    <input value={model} onChange={event=>setModel(event.target.value)} placeholder={provider==="zhipu"?"glm-4-flash":"deepseek-chat"}/></label>
   <label>API 密钥
    <input type="password" value={key} onChange={event=>setKey(event.target.value)} placeholder="sk-…（只留在内存，不落盘）"/></label>
   <label className="cd-check"><input type="checkbox" checked={thinking} onChange={event=>setThinking(event.target.checked)}/>开启思维链（推理型模型会先想再答，耗时更长）</label>
   <label className="cd-check"><input type="checkbox" checked={bothSides} onChange={event=>setBothSides(event.target.checked)}/>双方编队都用这个密钥</label>
   <label className="cd-check"><input type="checkbox" checked={fleetAgent} onChange={event=>setFleetAgent(event.target.checked)}/>同时给该侧一个舰队代理（让模型替你指挥另一方）</label>
   <div className="cd-order-actions">
    <button disabled={busy} onClick={submit}>接入</button>
    <button className="quiet" disabled={busy} onClick={()=>{setKey("");setOpen(false)}}>取消</button>
   </div>
   <p className="cd-note">
    密钥用于双方的编队代理（可只给本侧）。留空密钥再点「接入」即撤销回教条。
    接上舰队代理后，那一侧的舰队总指挥由模型担任：它会自己写命令，你就不必替它写。<br/>
    <b>想看每个 agent 怎么想</b>：勾上「开启思维链」并用支持的模型（智谱 glm-4.5-flash 实测会返回推理），
    然后打开顶栏的<b>调试</b>开关 —— 代理记录里每次往返都会分开显示「思考过程」与「原始回复」。
    推理模型会先把预算花在思考上，所以输出上限给到 3000 左右；太小时它可能只思考不回答。
   </p>
   {result&&<p className="cd-dispatch">{result}</p>}
   {error&&<p className="cd-error">{error}</p>}
  </div>}
 </div>;
}

export function CommandDelayPanel({game,side,turn,phase,collapsed,onToggle,recipient,onRecipient,onOpenRules}:Props){
 const [fleet,setFleet]=useState<FleetView|null>(null);
 const [local,setLocal]=useState<FormationView|null>(null);
 const [error,setError]=useState("");
 const [modelTick,setModelTick]=useState(0);

 const load=useCallback(()=>{
  fleetView(game,side).then(next=>{
   setFleet(next);setError("");
   const selectable=next.reports.filter(item=>!item.is_source_of_truth);
   if(!recipient&&selectable.length>0)onRecipient(selectable[0].formation_id);
  }).catch(reason=>setError(String(reason)));
 },[game,side,recipient,onRecipient]);
 useEffect(()=>{load()},[load,turn,phase]);

 useEffect(()=>{
  if(!recipient){setLocal(null);return}
  let active=true;
  formationView(game,side,recipient).then(next=>{if(active)setLocal(next)}).catch(()=>{if(active)setLocal(null)});
  return()=>{active=false};
  // modelTick 参与依赖：接入模型后各编队的决策来源变了，详情要重取。
 },[game,side,recipient,turn,phase,modelTick]);

 if(collapsed)return <section className="cd-panel collapsed"><button className="cd-toggle" onClick={onToggle}>命令延迟 · 展开指挥链</button></section>;

 const live=fleet?liveGuide(fleet.embarked):{position:null,count:0};

 return <section className="cd-panel">
  <header className="cd-head">
   <div><span>命令延迟模式</span><h3>指挥链与通信</h3></div>
   <div className="cd-head-actions">
    <button className="quiet" onClick={onOpenRules}>打法说明</button>
    <button className="quiet" onClick={load}>刷新</button>
    <button className="quiet" onClick={onToggle}>收起</button>
   </div>
  </header>
  {error&&<p className="cd-error">指挥链数据加载失败：{error}</p>}

  <div className="cd-role">
   <b>你是舰队总指挥</b>
   {fleet&&((fleet.embarked.ship_ids?.length??0)===0
    ? <span>你的旗舰已不在水面：本侧只剩下过期报告，任何事情都得靠还在的编队自己判断。</span>
    : <span>你的旗舰就在 <b>{fleet.embarked.name??fleet.embarked_formation_id??"—"}</b>：
     对它下命令是<b>当面交办</b>（立即生效、不走链路）；对别的编队只能发电报，命令会<b>延迟送达</b>，
     期间战场已经变了。你看不到远端编队的实时状态，只能看它们的报告——这就是这个模式要玩的东西。</span>)}
  </div>

  {fleet&&<>
   <div className="cd-fleet">
    {(fleet.embarked.ship_ids?.length??0)>0&&<div className="cd-chips">
     <em>当面受令编队 {fleet.embarked.name??"—"}</em>
     <em>兵力 {fleet.embarked.ship_ids?.length??0} 艘</em>
     <em>队形 {fleet.embarked.movement_style==="move_together"?"整队机动":"尾随"}</em>
     <em>几何 {fleet.embarked.geometry_kind==="straight_line"?"斜队/横队":"纵队"}</em>
     <em>舰上能看到的敌舰 {fleet.contacts.length}</em>
    </div>}
    {fleet.reports.length===0?<p className="muted">本方已无在编编队。</p>:
    <div className="cd-cards">
     {fleet.reports.map(report=>{
      const exact=report.is_source_of_truth;
      const active=recipient===report.formation_id;
      return <button type="button" key={report.formation_id}
        className={`cd-card${exact?" exact":""}${active?" active":""}`}
        onClick={()=>onRecipient(report.formation_id)}
        title={exact?"你的旗舰所在编队：状态是实时的":"该编队的状态来自它最近一次报告，可能已经过时"}>
       <div className="cd-card-top">
        <b>{report.name}</b>
        {exact?<em className="cd-badge exact">精确</em>:
         <em className={`cd-badge age-${Math.min(report.age_turns??9,4)}`}>报告 {ageText(report.age_turns)}</em>}
       </div>
       <div className="cd-card-mid">
        <span className={`cd-link cd-link-${report.link_status}`}>{linkLabel[report.link_status]??report.link_status}</span>
        <span>{authorityLabel[report.authority]??report.authority}</span>
        <span>兵力 {exact?live.count:(report.ship_count??"—")}</span>
        <span>位置 {exact?(live.position??"—"):(report.guide_label??"—")}</span>
       </div>
       <div className="cd-card-bot">
        {report.active_order_id
         ? <span className="cd-badge order">现行命令已确认{report.acknowledged_turn?` · 回执 T${report.acknowledged_turn}`:""}</span>
         : <span className="cd-badge warn">尚未确认任何命令</span>}
        {active&&<span className="cd-card-pick">正在向该编队写命令</span>}
       </div>
      </button>;
     })}
    </div>}
    {fleet.reports.some(item=>!item.is_source_of_truth)&&<p className="cd-note">
     点一张编队卡片＝把命令收件人换成它。除旗舰所在编队外，卡片上的位置与兵力都是<b>它自己报告的旧信息</b>。
    </p>}
   </div>

   <ModelCard game={game} side={side} onChanged={()=>setModelTick(value=>value+1)}/>

   {local&&<details className="cd-local" open>
    <summary><b>{local.formation_name}</b> 的本地情报（它自己知道什么）
     <span className="muted"> · 链路 {linkLabel[local.link_status]??local.link_status} · 权限 {authorityLabel[local.authority]??local.authority}</span></summary>
    <div className="cd-grid">
     <div><h4>本编队</h4>
      <ul><li>舰数 {(local.formation_state.ships as unknown[]|undefined)?.length??0}</li>
       <li>航向 {String(local.formation_state.heading??"—")} · 航速 {String(local.formation_state.speed??"—")}</li>
       <li>状态 {String(local.formation_state.status??"—")}</li></ul>
      <h4>它自己看到的敌舰</h4>
      {local.local_contacts.length===0?<p className="muted">暂无接触</p>:
       <ul>{local.local_contacts.map(c=><li key={c.ship_id}>{c.name}（{c.ship_type}）· 距离 {c.range_hex??c.range??"—"} 格
        {typeof c.range_nmi==="number"?` ≈ ${c.range_nmi} 海里`:""}</li>)}</ul>}</div>
     <div><h4>它手上的命令</h4>
      {local.active_mission_order?<div className="cd-order">
        <b>{local.active_mission_order.mission}</b>
        {local.active_mission_order.revision&&<p className="muted">第 {local.active_mission_order.revision} 版
         {local.active_mission_order.confirmed_turn?` · T${local.active_mission_order.confirmed_turn} 确认`:""}</p>}
        {local.active_mission_order.roe.length>0&&<p>约束：{local.active_mission_order.roe.join("；")}</p>}
        {local.active_mission_order.deadline_turn&&<p>期限：T{local.active_mission_order.deadline_turn}</p>}
       </div>:<p className="muted">尚未收到已确认的作战命令：它按预令与自己的判断行动。</p>}
      <h4>通信</h4>
      <ul><li>可用媒介 {((local.comm_state.mediums_available as string[]|undefined)??[]).map(m=>mediumLabel[m]??m).join("、")}</li>
       <li>已收报文 {local.received_messages.length}</li></ul></div>
     <div><h4>它知道的事实（知识账目）</h4>
      {(()=>{const items=(local.knowledge??[]) as Array<Record<string,unknown>>;
       if(items.length===0)return <p className="muted">账目还是空的：本局尚未记录过它的观测与收报（在账目启用之前就已推进的旧对局也会是空的）。再推进一次阶段就会开始逐条累积。</p>;
       return <ul className="cd-knowledge">{items.slice(0,8).map((item,index)=><li key={index}>
        <b>{String(item.subject_id)}</b> {String(item.field)}={String(item.value??"—")}
        <em>（{confidenceLabel[String(item.confidence)]??String(item.confidence)} · 观测于 T{String(item.observed_turn)}
        {item.received_turn!=null?`，T${String(item.received_turn)} 收到`:""}{item.source_kind==="LOCAL_OBSERVATION"?"，自己看到的":"，来电得知"}）</em>
       </li>)}</ul>;})()}
      <h4>可加权的目标（上限 ±{local.local_priority_weight_limit}）</h4>
      {local.legal_target_priority_options.length===0?<p className="muted">无可加权目标</p>:
       <ul>{local.legal_target_priority_options.map(o=><li key={o.target_id}>{o.target_id} · {o.target_class} · 距离 {o.range??"—"} 格</li>)}</ul>}
     </div>
    </div>
    <p className="cd-note">炮位分配、射界、命中修正一律由引擎选择器完成；本编队（以及你）只能给目标加有界权重。</p>
   </details>}

   <details className="cd-messages">
    <summary>报文台账（本回合 {fleet.messages.length} 条）</summary>
    {fleet.messages.length===0
     ? <p className="cd-note">本局双方各只有一个编队（舰队总指挥就在其中），没有需要通信的远端编队，因此没有报文。想玩通信与延迟，请选有多条战列线的想定（想定 1 或第二次马里亚纳海战）。</p>
     : <ul>{fleet.messages.slice(-12).reverse().map((m,index)=><li key={String(m.message_id??index)}>
        <span className={`cd-link cd-link-${String(m.status)}`}>{statusLabel[String(m.status)]??String(m.status)}</span>
        {" "}{kindLabel[String(m.kind)]??String(m.kind)} · {mediumLabel[String(m.medium)]??String(m.medium)}
        {" "}· 发出 T{String(m.issued_turn)} → {m.delivered_turn?`送达 T${String(m.delivered_turn)}`:"待投递"}
        {typeof m.handling_delay==="number"&&m.handling_delay>0?` · 链路开销 +${m.handling_delay} 回合`:""}
        {Array.isArray(m.route_nodes)&&(m.route_nodes as unknown[]).length>0?` · 经 ${(m.route_nodes as string[]).join("→")}`:""}
        {m.reason?<em className="cd-reason">（链路理由：{String(m.reason)}）</em>:""}
       </li>)}</ul>}
   </details>
  </>}
 </section>;
}
