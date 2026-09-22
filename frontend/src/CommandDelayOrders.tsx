// 命令延迟模式的输入通道：舰队总指挥在**移动阶段**用自然语言写命令，命令作为一项
// 信号经通信链路投递（可能延迟、可能丢失）。各编队的代理自行执行，玩家不逐舰微操。
import {useCallback,useEffect,useState} from "react";
import type {AgentLog,FormationReport,Side} from "./api";
import {agentLog,commandDelayOrder,fleetView} from "./api";

type Props={game:string;side:Side;turn:number;phase:string;debug:boolean;onSubmitAgentOrders:()=>Promise<string>};

const mediumLabel:Record<string,string>={tbs_short:"TBS 短距战术",blinker:"视觉信号",wt_coded:"编码电文",wt_reencipher_relay:"转报/再加密",multi_hop:"复合路由",blackout:"无通路"};

export function CommandDelayOrders({game,side,turn,phase,debug,onSubmitAgentOrders}:Props){
 const [reports,setReports]=useState<FormationReport[]>([]);
 const [target,setTarget]=useState<string>("");
 const [text,setText]=useState("");
 const [priorities,setPriorities]=useState("DD,CL");
 const [busy,setBusy]=useState(false);
 const [dispatch,setDispatch]=useState<string>("");
 const [error,setError]=useState("");
 const [log,setLog]=useState<AgentLog|null>(null);
 const [openLog,setOpenLog]=useState(true);

 const load=useCallback(()=>{
  fleetView(game,side).then(next=>{
   const remote=next.reports.filter(r=>!r.is_source_of_truth);
   setReports(remote);
   setTarget(current=>current&&remote.some(r=>r.formation_id===current)?current:(remote[0]?.formation_id??""));
  }).catch(()=>setReports([]));
  if(debug)agentLog(game,side,undefined,6).then(setLog).catch(()=>setLog(null));
 },[game,side,debug]);
 useEffect(()=>{load()},[load,turn,phase]);

 const send=async()=>{
  if(!target||!text.trim())return;
  setBusy(true);setError("");setDispatch("");
  try{
   const result=await commandDelayOrder(game,side,{formation_id:target,text:text.trim(),
    priority_classes:priorities.split(/[,，\s]+/).filter(Boolean)});
   setDispatch(`已发出（${mediumLabel[result.medium]??result.medium}）：预计第 ${result.expected_delivery_turn} 回合送达；${result.handling_delay>0?`链路开销 +${result.handling_delay} 回合`:"本回合可达"}`);
   setText("");
   load();
  }catch(reason){setError(String(reason))}
  finally{setBusy(false)}
 };

 const submit=async()=>{
  setBusy(true);setError("");setDispatch("");
  try{setDispatch(await onSubmitAgentOrders())}
  catch(reason){setError(String(reason))}
  finally{setBusy(false)}
 };

 const latest=log?.entries??[];
 return <section className="cd-orders">
  <header><h2>命令延迟 · 下达命令</h2>
   <span className="muted">你是舰队总指挥：写命令、收发报，各编队由自己的代理执行。</span></header>
  {phase!=="movement_planning"&&<p className="cd-note">命令通常在移动阶段下达；当前阶段仍可补发，但链路开销照算。</p>}
  <div className="cd-order-form">
   <label>收件编队
    <select value={target} onChange={event=>setTarget(event.target.value)}>
     {reports.length===0&&<option value="">（本侧没有可指挥的远端编队）</option>}
     {reports.map(report=><option key={report.formation_id} value={report.formation_id}>
      {report.name} · 链路{report.link_status} · 报告年龄{report.age_turns===null?"未知":`${report.age_turns} 回合`}
     </option>)}
    </select></label>
   <label>命令正文（自然语言）
    <textarea rows={3} value={text} maxLength={400}
     placeholder="例：敌轻巡已出现在西北，你部向东拉开距离保持接触，不要进入主力火线前方；优先打掉对方的驱逐舰。"
     onChange={event=>setText(event.target.value)}/></label>
   <label>火力优先级舰级（逗号分隔，只给权重）
    <input value={priorities} onChange={event=>setPriorities(event.target.value)}/></label>
   <div className="cd-order-actions">
    <button disabled={busy||!target||!text.trim()} onClick={send}>发送电报</button>
    <button className="quiet" disabled={busy} onClick={submit}>按编队代理方案提交订单</button>
   </div>
  </div>
  {dispatch&&<p className="cd-dispatch">{dispatch}</p>}
  {error&&<p className="cd-error">{error}</p>}

  <details className="cd-log" open={openLog} onToggle={event=>setOpenLog((event.target as HTMLDetailsElement).open)}>
   <summary>编队代理记录{debug?"（调试）":""}{log?` · ${log.policy_labels[side]??"未知"} · ${latest.length} 条`:""}</summary>
   {!debug&&<p className="muted">打开顶栏的「调试」可以看到每个代理的提示词、原始回复与记忆。</p>}
   {debug&&log&&<>
    <p className="cd-policy">本侧代理策略：<b>{log.policy_labels[side]??"未知"}</b>
     {String(log.policy_labels[side]??"").startsWith("deterministic")&&
      <em>（未配置模型密钥，编队按确定性教条行动；该标记由引擎写入，不会把教条输出冒充为模型输出）</em>}</p>
    {latest.map((entry,index)=><div className="cd-log-entry" key={`${entry.formation_id}-${entry.turn}-${index}`}>
     <b>{entry.formation_name}</b>
     <span className="muted">第 {entry.turn} 回合 · {entry.agent}</span>
     <p>命令：{entry.order_text??"（无）"}</p>
     {entry.attempts.map(attempt=><div key={attempt.attempt} className={`cd-attempt ${attempt.accepted?"ok":attempt.fallback?"fallback":"bad"}`}>
      <span>第 {attempt.attempt} 次{attempt.accepted?"已采纳":attempt.fallback?"回退教条":"被拒"}</span>
      {attempt.errors.length>0&&<em>{attempt.errors.join("；")}</em>}
      <pre>{attempt.raw_response.slice(0,600)}</pre>
     </div>)}
     <p className="cd-decision">决策：{String((entry.decision as Record<string,unknown>).selected_movement_plan??"保持")} · 分支 {String((entry.decision as Record<string,unknown>).selected_contingency_branch??"无")} · {String((entry.decision as Record<string,unknown>).rationale_summary??"")}</p>
     {String((entry.decision as Record<string,unknown>).memory_note??"")&&<p className="cd-note">写给自己的备忘：{String((entry.decision as Record<string,unknown>).memory_note)}</p>}
    </div>)}
    {Object.entries(log.memories).map(([fid,memory])=>{
     const payload=memory as {active_order_text?:string|null;scratchpad?:string[];counts?:Record<string,number>};
     return <div className="cd-memory" key={fid}>
      <b>{fid} 的记忆</b>
      <p>当前命令：{payload.active_order_text??"（无）"}</p>
      <p className="muted">条目：{Object.entries(payload.counts??{}).map(([k,v])=>`${k} ${v}`).join(" · ")}</p>
      {(payload.scratchpad?.length??0)>0&&<ul>{payload.scratchpad!.map((note,i)=><li key={i}>{note}</li>)}</ul>}
     </div>;
    })}
   </>}
  </details>
 </section>;
}
