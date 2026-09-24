// 命令延迟模式的「下达命令」面板：舰队总指挥的全部操作入口。
//
// 这个面板解决的是「不知道这个模式怎么玩」：先亮出本回合的操作顺序，再让「收件编队 →
// 这道命令多久能到 → 正文 → 发送」这条线一路可读，最后把代理方案与交接按钮放在一起。
// 命令正文始终是权威（引擎把它同时写进 mission/intent/task）；结构化字段只是帮你把话
// 写全的辅助，拼出来的还是正文，不存在"填了表但模型没看到"的暗通道。
import {useCallback,useEffect,useState} from "react";
import type {AgentLog,CommandPreview,FleetView,FormationView,Side} from "./api";
import {agentLog,commandDelayOrder,formationOrders,formationView,fleetView,previewCommandDelayOrder} from "./api";
import {kindLabel,linkLabel,mediumLabel,statusLabel} from "./CommandDelayPanel";

type PlanOrder={formation_id:string;leader_plan:string;movement_style?:string|null;spacing?:number|null;reform_column?:boolean};
type Props={
 game:string;side:Side;turn:number;phase:string;debug:boolean;
 recipient:string|null;onRecipient:(formationId:string)=>void;
 onSubmitAgentOrders:()=>Promise<string>;
 onAdvance:()=>void;advanceLabel:string;
};

const styleLabel=(value:string|undefined|null)=>value==="move_together"?"整队机动"
 :value==="follow_wake"?"尾随":"";
// 预案分支是引擎的枚举值，界面上给中文；未知取值原样显示（宁可显示原值也不编造）。
const branchLabel:Record<string,string>={
 explicit_signal_branch:"按上级指定的信号分支",
 local_condition_branch:"按本地情况分支",
 loss_of_comm_branch:"按失联预案分支",
};
const plainBranch=(value:string)=>branchLabel[value]??value;

// 投递预判：把引擎算出来的链路与延迟说成人话。预判来自引擎自己的路由，不是前端猜的。
function deliveryText(preview:CommandPreview|null):{tone:string;headline:string;detail:string}{
 if(!preview)return {tone:"unknown",headline:"正在计算链路…",detail:""};
 const distance=preview.distance_hex==null?"":`距离 ${preview.distance_hex} 格（≈${preview.range_nmi} 海里，TBS 射程 ${preview.tbs_range_hex} 格）`;
 switch(preview.reason_code){
  case "face_to_face":
   return {tone:"instant",headline:"当面交办：立即生效，不占用通信链路",
    detail:"你的旗舰就在这个编队上，命令当场交办，不受任何延迟影响。"};
  case "tbs_short":
   return {tone:"fast",headline:"TBS 直连：本回合可投递",
    detail:`${distance}。短距战术语音，处理后立即送达；长命令要占多个时隙，可能顺延。`};
  case "blinker":
   return {tone:"slow",headline:`视觉信号：链路开销 +${preview.total_delay} 回合`,
    detail:`${distance}。超出 TBS 直连射程但有直视条件，用闪光信号转发。`};
  case "wt_coded":
   return {tone:"slow",headline:`编码电文：链路开销 +${preview.total_delay} 回合`,
    detail:`${distance}。直连与视觉都不可用，改走编码电报（译电需要时间）。`};
  case "recipient_not_on_board":
   return {tone:"blocked",headline:"现在无法与它通信",
    detail:"该编队还不在图上（尚未到场），或其旗舰已损失。等它到场后再下令。"};
  case "fleet_flagship_not_on_board":
   return {tone:"blocked",headline:"你的指挥平台已不在图上",
    detail:"旗舰损失后，本侧只能靠各编队自己的报告与判断；这里发不出新的命令。"};
  case "no_fleet_formation":
   return {tone:"blocked",headline:"本侧已无编队可以下令",detail:"所有编队都已不在水面。"};
  default:
   return {tone:"slow",headline:`${mediumLabel[preview.medium]??preview.medium}：链路开销 +${preview.total_delay} 回合`,
    detail:`${preview.medium_reason}${distance?"。 "+distance:""}`};
 }
}

// 记号读法（只用于显示）：数字＝直线前进格数，S＝右转60°、P＝左转60°，写两次＝120°。
// 引擎自己会给 manoeuvre/ends_heading/jams_spaced_column；这里只是让**打补丁之前**写下的
// 旧决策记录也读得懂，引擎字段存在时一律以引擎为准。
const decodePlan=(plan:string)=>{
 const parts:string[]=[];let pending=0;
 for(const token of plan.match(/\d+|[SP]+/g)??[]){
  if(/^\d+$/.test(token)){pending+=Number(token);continue}
  if(pending){parts.push(`前进 ${pending} 格`);pending=0}
  const side=token[0]==="S"?"右转":"左转";
  parts.push(token.length>=2?`${side} 120°（原地调头一步）`:`${side} 60°`);
 }
 if(pending)parts.push(`前进 ${pending} 格`);
 return parts.join(" → ");
};
const planManoeuvre=(actions:Array<Record<string,unknown>>,plan:string)=>{
 const chosen=actions.find(item=>String(item.plan)===plan);
 if(chosen?.manoeuvre)return {text:String(chosen.manoeuvre),jams:Boolean(chosen.jams_spaced_column),engine:true};
 if(!plan)return {text:"",jams:false,engine:false};
 return {text:decodePlan(plan),jams:/SS|PP/.test(plan),engine:false};
};

const ROE_PRESETS=["不要进入主力火线前方","避免夜间鱼雷突击，保持距离","优先保全自身，不追击","保留鱼雷直到 3000 码以内","受击后向主力靠拢"];

const TEMPLATES:[string,string,string][]=[
 ["保持接触","以现有航向保持接触，不要主动进入对方主炮射程；发现敌主力转向就报告并跟住。","维持接触，不贸然接战"],
 ["脱离接触","向东拉开距离，脱离对方轻巡的射程后转向与主力会合。","脱离并保存战力"],
 ["抢占阵位","向敌方编队的侧翼机动，占领有利射击位置，等我方主力进入后再压上。","抢占 T 字横位"],
 ["集中火力","集中火力先打对方的驱逐舰，再由近及远清理轻巡；不要分散射击。","按舰级顺序集中火力"],
 ["自主决断","情况已变，你按自己的判断行事，保证自身编队完整并向我报告你的意图。","授权自主决断"],
];

export function CommandDelayOrders({game,side,turn,phase,debug,recipient,onRecipient,onSubmitAgentOrders,onAdvance,advanceLabel}:Props){
 const [fleet,setFleet]=useState<FleetView|null>(null);
 const [plans,setPlans]=useState<PlanOrder[]>([]);
 const [log,setLog]=useState<AgentLog|null>(null);
 const [local,setLocal]=useState<FormationView|null>(null);
 const [preview,setPreview]=useState<CommandPreview|null>(null);
 const [text,setText]=useState("");
 const [priorities,setPriorities]=useState("");
 const [roe,setRoe]=useState<string[]>([]);
 const [deadline,setDeadline]=useState("");
 const [busy,setBusy]=useState(false);
 const [dispatch,setDispatch]=useState<string>("");
 const [notice,setNotice]=useState("");
 const [error,setError]=useState("");
 const [showCompose,setShowCompose]=useState(false);

 const target=recipient??"";

 const load=useCallback(()=>{
  fleetView(game,side).then(setFleet).catch(()=>setFleet(null));
  formationOrders(game,side).then(next=>setPlans(next.orders as PlanOrder[])).catch(()=>setPlans([]));
  agentLog(game,side,undefined,6).then(setLog).catch(()=>setLog(null));
 },[game,side]);
 useEffect(()=>{load()},[load,turn,phase]);

 useEffect(()=>{
  if(!target){setLocal(null);return}
  let active=true;
  formationView(game,side,target).then(next=>{if(active)setLocal(next)}).catch(()=>{if(active)setLocal(null)});
  return()=>{active=false};
 },[game,side,target,turn,phase]);

 // 投递预判：稍作去抖，正文每改几个字就重算一次链路与开销。
 useEffect(()=>{
  if(!target){setPreview(null);return}
  let active=true;
  const timer=setTimeout(()=>{
   previewCommandDelayOrder(game,side,{formation_id:target,text})
    .then(next=>{if(active)setPreview(next)})
    .catch(()=>{if(active)setPreview(null)});
  },300);
  return()=>{active=false;clearTimeout(timer)};
 },[game,side,target,text,turn,phase]);

 const classes=Array.from(new Set((local?.legal_target_priority_options??[]).map(option=>option.target_class).filter(Boolean)));
 const delivery=deliveryText(preview);
 const canSend=Boolean(target)&&text.trim().length>0&&delivery.tone!=="blocked";

 const compose=()=>{
  const parts:string[]=[];
  if(text.trim())parts.push(text.trim());
  if(roe.length>0)parts.push(`约束：${roe.join("；")}。`);
  if(priorities.trim())parts.push(`火力优先打：${priorities.trim()}。`);
  const turns=Number(deadline);
  if(deadline&&Number.isFinite(turns))parts.push(`第 ${turns} 回合前完成。`);
  setText(parts.join(" "));
 };

 const appendPriority=(value:string)=>{
  const list=priorities.split(/[,，\s]+/).filter(Boolean);
  if(list.includes(value))return;
  setPriorities([...list,value].join(","));
 };

 const send=async()=>{
  if(!canSend)return;
  setBusy(true);setError("");setDispatch("");
  try{
   const result=await commandDelayOrder(game,side,{
    formation_id:target,text:text.trim(),
    priority_classes:priorities.split(/[,，\s]+/).filter(Boolean),
    roe:roe.length>0?roe:undefined,
    deadline_turn:deadline?Number(deadline):null,
   });
   const arrival=result.handling_delay>0
    ? `预计第 ${result.expected_delivery_turn} 回合送达（链路开销 +${result.handling_delay} 回合）`
    : `本回合即可送达（第 ${result.expected_delivery_turn} 回合）`;
   setDispatch(`电报已发出（${mediumLabel[result.medium]??result.medium}，编号 ${result.message_id}）：${arrival}。${
    result.medium==="face_to_face"?"当面交办，对方立刻受令。":"在送达之前，那个编队仍按现行命令行动。"}`);
   setText("");
   setRoe([]);setPriorities("");setDeadline("");
   load();
  }catch(reason){setError(String(reason))}
  finally{setBusy(false)}
 };

 const submitPlans=async()=>{
  setBusy(true);setError("");setNotice("");
  try{setNotice(await onSubmitAgentOrders())}
  catch(reason){setError(String(reason))}
  finally{setBusy(false)}
 };

 const activeOrder=preview?.active_order??local?.active_mission_order??null;
 const orderHistory=(fleet?.messages??[]).filter(m=>String(m.kind).includes("order"));
 const decisions=(log?.entries??[]).filter(entry=>entry.side===side);

 return <section className="cd-orders">
  <header><h2>下达命令</h2>
   <span className="muted">你是舰队总指挥：写命令、收报告；各编队由自己的代理执行，你不需要逐舰点格子。</span></header>

  <ol className="cd-steps">
   <li className={phase==="movement_planning"?"now":""}><b>1</b> 写命令</li>
   <li className={phase==="movement_planning"?"now":""}><b>2</b> 发电报（可能延迟）</li>
   <li className={["movement_planning","torpedo_planning","gunnery"].includes(phase)?"now":""}><b>3</b> 看代理方案</li>
   <li className={["movement_planning","torpedo_planning","gunnery"].includes(phase)?"now":""}><b>4</b> 校验并交接</li>
  </ol>

  {phase!=="movement_planning"&&["torpedo_planning","gunnery"].includes(phase)&&<p className="cd-note">
   当前是<b>{phase==="gunnery"?"炮击阶段":"鱼雷阶段"}</b>：机动已经封存，你能改的只有火力优先级（下面「火力优先级舰级」），
   炮位与射界由引擎选择器决定。
  </p>}

  <div className="cd-order-form">
   <label>收件编队（点指挥链里的卡片也可以改）
    <select value={target} onChange={event=>onRecipient(event.target.value)}>
     {!target&&<option value="">（选一个编队）</option>}
     {(fleet?.reports??[]).map(report=><option key={report.formation_id} value={report.formation_id}>
      {report.name}{report.is_source_of_truth
       ? " · 当面受令（立即生效，无延迟）"
       : ` · 链路${linkLabel[report.link_status]??report.link_status} · 报告${report.age_turns===null?"未知":`${report.age_turns} 回合前`}`}
     </option>)}
    </select></label>

   <div className={`cd-delivery ${delivery.tone}`}>
    <b>{delivery.headline}</b>
    {delivery.detail&&<span>{delivery.detail}</span>}
    {preview?.long_order&&<span className="cd-warn">正文偏长（超过 240 字）：占用 2 个时隙，可能顺延到下一回合。</span>}
   </div>

   <label>命令正文（自然语言，这是权威内容）
    <textarea rows={4} value={text} maxLength={1000}
     placeholder="例：敌轻巡已出现在西北（约 7 格），你部向东拉开距离保持接触，不要进入主力火线前方；优先打掉对方的驱逐舰。"
     onChange={event=>setText(event.target.value)}/>
   </label>
   <div className="cd-counter">{text.length}/1000 字</div>

   <div className="cd-templates">
    <span className="muted">快速套用：</span>
    {TEMPLATES.map(([label,body,mission])=><button type="button" key={label} className="quiet"
      onClick={()=>setText(`${mission}：${body}`)}>{label}</button>)}
   </div>

   <button type="button" className="quiet" onClick={()=>setShowCompose(!showCompose)}>
    {showCompose?"收起逐项辅助":"逐项辅助（约束 / 期限 / 火力优先级）"}
   </button>

   {showCompose&&<div className="cd-compose">
    <label>约束（写进命令正文，编队代理会读到）
     <span className="cd-chips-pick">{ROE_PRESETS.map(item=><button type="button" key={item}
       className={roe.includes(item)?"chip on":"chip"}
       onClick={()=>setRoe(roe.includes(item)?roe.filter(value=>value!==item):[...roe,item])}>{item}</button>)}</span>
    </label>
    <label>完成期限
     <select value={deadline} onChange={event=>setDeadline(event.target.value)}>
      <option value="">不设期限</option>
      <option value={turn}>{turn} 回合（本回合）内</option>
      <option value={turn+1}>{turn+1} 回合内</option>
      <option value={turn+2}>{turn+2} 回合内</option>
      <option value={turn+3}>{turn+3} 回合内</option>
     </select></label>
    <label>火力优先级舰级（只影响选靶顺序，不改射界与合法性）
     {classes.length>0&&<span className="cd-chips-pick">{classes.map(value=><button type="button" key={value}
       className={priorities.split(/[,，\s]+/).includes(value)?"chip on":"chip"}
       onClick={()=>appendPriority(value)}>{value}</button>)}</span>}
     <input value={priorities} onChange={event=>setPriorities(event.target.value)} placeholder="例如 DD,CL（可留空）"/>
    </label>
    <div className="cd-order-actions">
     <button className="quiet" onClick={compose}>把这些字段补进正文</button>
    </div>
    <p className="cd-note">辅助字段拼出来的只是正文；编队代理读到的永远是正文本身。</p>
   </div>}

   {preview?.restates_active_order&&<p className="cd-warn">
    与它现行命令的措辞基本一致：引擎会记为「重复命令（NO_NEW_ORDER）」，不会新建一版。要改变行动，请写出差别。
   </p>}

   <div className="cd-order-actions">
    <button disabled={busy||!canSend} onClick={send}>发送电报</button>
    <span className="muted cd-btn-note">命令是一项<b>信号</b>：按上面的链路投递，可能延迟；送达前编队仍按旧命令行动。</span>
   </div>
  </div>
  {dispatch&&<p className="cd-dispatch">{dispatch}</p>}
  {error&&<p className="cd-error">{error}</p>}

  <div className="cd-orders-current">
   <h4>它现行的命令</h4>
   {activeOrder?<div className="cd-order">
     <b>{activeOrder.mission}</b>
     <p className="muted">版本 {activeOrder.revision??1}
      {activeOrder.confirmed_turn?` · T${activeOrder.confirmed_turn} 已确认`:" · 尚未确认"}
      {activeOrder.deadline_turn?` · 期限 T${activeOrder.deadline_turn}`:""}</p>
    </div>
    :<p className="muted">这个编队还没有已确认的作战命令：它按预令与自己的判断行动。</p>}
   {orderHistory.length>0&&<details><summary>命令投递台账（{orderHistory.length} 条）</summary>
    <ul>{orderHistory.slice(-6).reverse().map((m,index)=><li key={String(m.message_id??index)}>
     {statusLabel[String(m.status)]??String(m.status)} · {kindLabel[String(m.kind)]??String(m.kind)}
     {" "}· 发 T{String(m.issued_turn)} → {m.delivered_turn?`到 T${String(m.delivered_turn)}`:"在途"}
     {m.payload?<span className="cd-reason">「{String((m.payload as Record<string,unknown>).order_text??"")}」</span>:null}
    </li>)}</ul></details>}
  </div>

  <div className="cd-orders-plans">
   <h4>本阶段各编队的代理方案</h4>
   {plans.length===0
    ? <p className="muted">{phase==="gunnery"
      ? "炮击阶段没有编队机动方案：炮位、射界与目标是引擎选择器按你下达的火力优先级生成的，你不需要提交炮击指令。"
      : phase==="torpedo_planning"
        ? "鱼雷阶段没有编队机动方案：本阶段提交的是鱼雷攻击计划（由引擎与自动计划填充）。"
        : "本阶段各编队没有机动方案（可能已过机动阶段，或本侧没有在编编队）。"}</p>
    : <ul>{plans.map(plan=><li key={plan.formation_id}>
      <b>{(fleet?.reports??[]).find(report=>report.formation_id===plan.formation_id)?.name??plan.formation_id}</b>
      {" "}机动 {plan.leader_plan}{(()=>{const decision=decisions.find(entry=>entry.formation_id===plan.formation_id);
       const actions=(decision?.prompt?.legal_formation_actions??[]) as Array<Record<string,unknown>>;
       const decoded=planManoeuvre(actions,plan.leader_plan);
       return decoded.text?`（${decoded.text}${decoded.jams?"，会挤停纵队":""}）`:"";})()}{styleLabel(plan.movement_style)?` · ${styleLabel(plan.movement_style)}`:""}
      {plan.reform_column?" · 本回合重整队形":""}
      {(()=>{const decision=decisions.find(entry=>entry.formation_id===plan.formation_id);
       const payload=(decision?.decision??{}) as Record<string,unknown>;
       const raw=String(payload.rationale_summary??"");
       // 教条与模型偶尔给出的是引擎审计串（link=… authority=…）而不是句子：正常视图不把
       // 机器字段当理由展示，原样保留在下面的调试块里。
       const readable=raw&&!/\b(link|authority|branch|action|contacts)=/.test(raw)?raw:"";
       const branch=String(payload.selected_contingency_branch??"");
       return readable?<em className="cd-reason">（{readable}）</em>
        :branch?<em className="cd-reason">（{plainBranch(branch)}执行）</em>:null;})()}
     </li>)}</ul>}
   <div className="cd-order-actions">
    <button className="quiet" disabled={busy||plans.length===0} onClick={submitPlans}>按编队代理方案提交订单</button>
    <span className="muted cd-btn-note">把各编队代理自己选定的合法机动方案作为<b>本侧订单</b>提交（等价于替它们填表）；引擎仍会逐单校验。</span>
   </div>
   {notice&&<p className="cd-dispatch">{notice}</p>}
  </div>

  <div className="cd-orders-advance">
   <h4>交接</h4>
   <div className="cd-order-actions">
    <button disabled={busy} onClick={onAdvance}>{advanceLabel}</button>
    <span className="muted cd-btn-note">提交本阶段计划并推进裁决；命令延迟模式下提交的就是<b>计划表里那份方案</b>（＝各编队代理的选择，引擎仅在两支编队航迹真冲突时调整一支的航速）。</span>
   </div>
  </div>

  <details className="cd-log">
   <summary>编队代理记录{debug?"（调试 · 含思考链）":""}{log?` · ${String(log.policy_labels[side]??"未知").startsWith("llm:")?"模型":"教条"} · ${(log.entries??[]).length} 条`:""}</summary>
   {!log&&<p className="muted">暂无代理记录。</p>}
   {log&&String(log.policy_labels[side]??"").startsWith("deterministic")&&<p className="cd-policy">
    本侧编队代理策略：<b>确定性教条</b>（未接入模型密钥）。编队照常行动，但这些决策不是模型给出的 ——
    引擎记录里的标签如此，界面也不会把它说成模型判断。要接模型，见左侧「指挥链与通信 → 编队代理」。
   </p>}
   {log&&decisions.slice(0,6).map((entry,index)=>{const payload=(entry.decision??{}) as Record<string,unknown>;
    const isFleet=entry.role==="fleet_agent";
    return <div className="cd-log-entry" key={`${entry.formation_id}-${entry.turn}-${index}`}>
     <b>{isFleet?`舰队总指挥（${entry.formation_name}）`:entry.formation_name}</b>
     {isFleet&&<em className="cd-badge order">舰队层代理</em>}
     <span className="muted">第 {entry.turn} 回合 · {entry.agent}</span>
     <p>收到的命令：{entry.order_text?`「${entry.order_text}」`:"（还没有命令）"}</p>
     <p className="cd-decision">{isFleet?"本回合下令：":"选择 "}{isFleet
       ?(Array.isArray(payload.orders)&&(payload.orders as unknown[]).length>0
         ?(payload.orders as Array<Record<string,unknown>>).map(order=>`${String(order.formation_id??"")}：${String(order.order_event??"NEW_ORDER")} 「${String(order.text??"")}」`).join("；")
         :"不下新命令（no_order）")
       :(()=>{const plan=String(payload.selected_movement_plan??"");
          if(!plan)return "保持";
          const actions=(entry.prompt?.legal_formation_actions??[]) as Array<Record<string,unknown>>;
          const chosen=actions.find(item=>String(item.plan)===plan);
          const decoded=planManoeuvre(actions,plan);
          return <>{plan}{decoded.text?`（${decoded.text}）`:""}
           {chosen?.ends_heading!=null&&<> · 结束航向 <b>{String(chosen.ends_heading)}</b>{chosen.keeps_heading?"（保持航向）":"（会转向）"}</>}</>;})()}
     </p>
     {Array.isArray(payload.target_priority_adjustments)&&(payload.target_priority_adjustments as Array<Record<string,unknown>>).length>0&&
      <p className="cd-note">火力权重：{(payload.target_priority_adjustments as Array<Record<string,unknown>>)
       .map(adjustment=>`${String(adjustment.target_id)} ${Number(adjustment.weight)>0?"+":""}${String(adjustment.weight)}`).join("、")}</p>}
     {String(payload.memory_note??"")&&<p className="cd-note">写给自己的备忘：{String(payload.memory_note)}</p>}
     {(()=>{const plan=String(payload.selected_movement_plan??"");
        const actions=(entry.prompt?.legal_formation_actions??[]) as Array<Record<string,unknown>>;
        if(!planManoeuvre(actions,plan).jams)return null;
        return <p className="cd-warn">这个方案含原地 120° 转向：间距纵队里后舰会在同一脉冲挤进领舰格，
         结算时整队急停（基本等于没走出去）。若上级命令要求保持航向，这条方案与命令不符。</p>;})()}
     {debug&&entry.attempts.map(attempt=><div key={attempt.attempt} className={`cd-attempt ${attempt.accepted?"ok":attempt.fallback?"fallback":"bad"}`}>
      <span>第 {attempt.attempt} 次{attempt.accepted?"已采纳":attempt.fallback?"回退教条":"被拒"}
       {attempt.finish_reason?` · finish=${attempt.finish_reason}`:""}
       {attempt.usage?.completion_tokens?` · 输出 ${attempt.usage.completion_tokens} tokens`:""}</span>
      {attempt.errors.length>0&&<em>{attempt.errors.join("；")}</em>}
      {attempt.thinking
       ? <div className="cd-thinking">
         <b>思考过程</b>
         <span className="muted">模型自己的推理，只用于解释它为什么这样决定，不参与任何裁决</span>
         <pre>{attempt.thinking.slice(0,2000)}{attempt.thinking.length>2000?"…（已截断）":""}</pre>
        </div>
       : <p className="muted cd-no-thinking">这次往返没有思考内容：非推理模型，或该模型未开启思考链。</p>}
      <div className="cd-response"><b>原始回复</b><pre>{attempt.raw_response.slice(0,900)}</pre></div>
     </div>)}
    </div>;})}
   {debug&&log&&Object.entries(log.memories).map(([fid,memory])=>{
    const payload=memory as {active_order_text?:string|null;scratchpad?:string[];counts?:Record<string,number>};
    return <div className="cd-memory" key={fid}>
     <b>{fid} 的记忆</b>
     <p>当前命令：{payload.active_order_text??"（无）"}</p>
     <p className="muted">条目：{Object.entries(payload.counts??{}).map(([key,value])=>`${key} ${value}`).join(" · ")}</p>
     {(payload.scratchpad?.length??0)>0&&<ul>{payload.scratchpad!.map((note,index)=><li key={index}>{note}</li>)}</ul>}
    </div>;})}
  </details>
 </section>;
}
