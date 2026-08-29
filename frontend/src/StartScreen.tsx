import {useState} from "react";
import type {Side} from "./types";

type Mode="hotseat"|"tutorial"|"vs_ai"|"llm";
type Props={
 realistic:boolean;setRealistic:(value:boolean)=>void;recordReport:boolean;setRecordReport:(value:boolean)=>void;
 researchAllow:boolean;setResearchAllow:(value:boolean)=>void;researchHandle:string;setResearchHandle:(value:string)=>void;
 llmProvider:"deepseek"|"zhipu";setLlmProvider:(value:"deepseek"|"zhipu")=>void;llmModel:string;setLlmModel:(value:string)=>void;
 llmKey:string;setLlmKey:(value:string)=>void;llmVision:boolean;setLlmVision:(value:boolean)=>void;
 onStart:(scenario:string,mode?:Mode,side?:Side,profile?:string)=>void;error:string;
 onPreviewRealisticRules:()=>void;
};
const scenarios=[
 ["IBS-S-03","想定 3 · 通道行动"],
 ["IBS-S-01","想定 1 · 埃斯佩兰斯角海战"],
 ["IBS-S-EM-01","扩展 · 第二次马里亚纳海战"],
] as const;

export function StartScreen(props:Props){
 const [scenario,setScenario]=useState("IBS-S-03");
 const [side,setSide]=useState<Side>("axis");
 const [profile,setProfile]=useState("adaptive");
 return <main className="landing start-screen">
  <p className="eyebrow">AUDITABLE NAVAL WARGAME</p><h1>铁底湾的回响 IV</h1><p>确定性裁决 · 规则出处 · 同机交接</p>
  <section className={`realistic-mode ${props.realistic?"on":""}`}>
   <div><b>真实模式 · 编队指挥链</b><p>先编成最多四支纵队并指定领舰、旗舰和备用旗舰；移动时只操纵领舰，后舰沿共享航迹尾随。</p></div>
   <div className="realistic-actions"><button type="button" className="rules-preview-button" onClick={props.onPreviewRealisticRules}>预览完整规则</button><button type="button" aria-pressed={props.realistic} onClick={()=>props.setRealistic(!props.realistic)}>{props.realistic?"已开启":"开启真实模式"}</button></div>
  </section>
  <label className={`record-report${props.recordReport?" on":""}`}><input type="checkbox" checked={props.recordReport} onChange={event=>props.setRecordReport(event.target.checked)}/>自动记录战报</label>
  <label className={`research-toggle${props.researchAllow?" on":""}`}><input type="checkbox" checked={props.researchAllow} onChange={event=>props.setResearchAllow(event.target.checked)}/>允许匿名对战记录用于科研{props.researchAllow&&<input value={props.researchHandle} maxLength={40} placeholder="称呼（可选）" onChange={event=>props.setResearchHandle(event.target.value)}/>}</label>
  <section className="llm-settings"><div className="llm-setting-grid">
   <label>接口供应商<select value={props.llmProvider} onChange={event=>{const provider=event.target.value as "deepseek"|"zhipu";props.setLlmProvider(provider);props.setLlmModel(provider==="zhipu"?"glm-5.2":"deepseek-v4-flash");props.setLlmVision(false)}}><option value="zhipu">智谱 BigModel</option><option value="deepseek">DeepSeek</option></select></label>
   <label>模型<input list="llm-models" value={props.llmModel} onChange={event=>{props.setLlmModel(event.target.value);props.setLlmVision(false)}}/><datalist id="llm-models">{props.llmProvider==="zhipu"?<><option value="glm-5.2"/><option value="glm-5.3-flash"/><option value="glm-5v-turbo"/></>:<option value="deepseek-v4-flash"/>}</datalist></label>
  </div><label className="llm-key">API 密钥（仅保存在当前进程内存）<input type="password" value={props.llmKey} autoComplete="new-password" onChange={event=>props.setLlmKey(event.target.value)}/></label>
  <label className="vision-toggle"><input type="checkbox" checked={props.llmVision} disabled={!props.llmModel.toLowerCase().startsWith("glm-5v")} onChange={event=>props.setLlmVision(event.target.checked)}/>向视觉模型发送本方可见地图</label><small>推荐：glm-5.2（文本 JSON、短思考）；glm-5.3-flash 会强制思考；地图图片请使用 glm-5v-turbo。</small></section>
  <div className="scenario-grid">
   <button className="tutorial-choice" onClick={()=>props.onStart("IBS-S-03","tutorial")}><b>新手教学关</b><span>手把手完成移动、鱼雷、炮击与损伤</span></button>
   {scenarios.map(([id,label])=><button key={id} onClick={()=>props.onStart(id)}><b>{label}</b><span>{props.realistic?"将先进入编队初设":"经典逐舰指挥"}</span></button>)}
   <div className="vs-card"><b>人机大战</b><select value={scenario} onChange={event=>setScenario(event.target.value)}>{scenarios.map(([id,label])=><option key={id} value={id}>{label}</option>)}</select><select value={side} onChange={event=>setSide(event.target.value as Side)}><option value="axis">我指挥轴心</option><option value="allies">我指挥同盟</option></select><select value={profile} onChange={event=>setProfile(event.target.value)}><option value="adaptive">自适应鱼雷战术（推荐）</option><option value="balanced">均衡</option><option value="fleet">大舰队编队</option><option value="line">长纵队</option><option value="cautious">保守</option></select><button onClick={()=>props.onStart(scenario,"vs_ai",side,profile)}>开始</button></div>
   <div className="vs-card llm-card"><b>人类对 LLM</b><p>LLM 与玩家共用引擎合法行动；真实模式下只能提交编队级订单。</p><button onClick={()=>props.onStart(scenario,"llm",side)}>开始</button></div>
  </div>
  {props.error&&<pre>{props.error}</pre>}
 </main>;
}
