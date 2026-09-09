import {useEffect,useRef,useState} from "react";
import type {Side} from "./types";
import type {CustomScenarioDefinition,SavedGameSummary} from "./api";
import {customScenarios,savedGames} from "./api";
import {CustomScenarioEditor} from "./CustomScenarioEditor";
import {bodyRealisticCapable} from "./editor/scenario";

type Mode="hotseat"|"tutorial"|"vs_ai"|"llm";
type Journey="learn"|"play";
type Props={
 realistic:boolean;setRealistic:(value:boolean)=>void;recordReport:boolean;setRecordReport:(value:boolean)=>void;
 researchAllow:boolean;setResearchAllow:(value:boolean)=>void;researchHandle:string;setResearchHandle:(value:string)=>void;
 llmProvider:"deepseek"|"zhipu";setLlmProvider:(value:"deepseek"|"zhipu")=>void;llmModel:string;setLlmModel:(value:string)=>void;
 llmKey:string;setLlmKey:(value:string)=>void;llmVision:boolean;setLlmVision:(value:boolean)=>void;
 onStart:(scenario:string,mode?:Mode,side?:Side,profile?:string,realisticOverride?:boolean,tutorialScript?:"classic_night"|"erma_grand_fleet")=>void;
 onResume:(game:SavedGameSummary,side:Side)=>void;onImport:(bundle:unknown,side:Side)=>Promise<void>;
 error:string;onPreviewRealisticRules:()=>void;
};
const scenarios=[
 ["IBS-S-03","通道行动","驱逐舰夜战 · 4 回合"],
 ["IBS-S-01","埃斯佩兰斯角","巡洋舰、增援与轰岸"],
 ["IBS-S-EM-01","第二次马里亚纳海战","24 艘主力舰 · 12 回合"],
] as const;

export function StartScreen(props:Props){
 const [journey,setJourney]=useState<Journey>("learn");
 const [customOpen,setCustomOpen]=useState(false);
 const [matchMode,setMatchMode]=useState<Exclude<Mode,"tutorial">>("hotseat");
 const [scenario,setScenario]=useState("IBS-S-EM-01");
 const [side,setSide]=useState<Side>("axis");
 const [profile,setProfile]=useState("adaptive");
 const [customs,setCustoms]=useState<CustomScenarioDefinition[]>([]);
 const [saves,setSaves]=useState<SavedGameSummary[]>([]);
 const [importBusy,setImportBusy]=useState(false);
 const [importError,setImportError]=useState("");
 const saveInput=useRef<HTMLInputElement>(null);
 const modeTouched=useRef(false);
 useEffect(()=>{customScenarios().then(list=>setCustoms(list)).catch(()=>setCustoms([]));savedGames().then(list=>setSaves(list)).catch(()=>setSaves([]))},[]);
 const importSave=async(file:File|undefined)=>{if(!file)return;setImportBusy(true);setImportError("");try{const text=await file.text();await props.onImport(JSON.parse(text),side)}catch(error){setImportError(String(error))}finally{setImportBusy(false);if(saveInput.current)saveInput.current.value=""}};
 const startLabel=matchMode==="hotseat"?"建立同机对战":matchMode==="vs_ai"?"开始人机对战":"连接并开始 LLM 对战";
 // 自定义剧本：能力门控（不够真实编队资格的剧强制经典）+ 推荐玩法默认对手。
 const builtinScenario=scenarios.find(item=>item[0]===scenario);
 const activeCustom=customs.find(item=>item.id===scenario);
 const activeCapable=activeCustom?bodyRealisticCapable(activeCustom):null;
 const customLocked=activeCustom!==undefined&&activeCapable===false;
 const effectiveRealistic=customLocked?false:props.realistic;
 const chosenTitle=builtinScenario?.[1]??activeCustom?.title??"自定义剧本";
 const selectScenario=(id:string)=>{
  setScenario(id);
  const item=customs.find(entry=>entry.id===id);
  if(!item)return;
  if(!modeTouched.current&&item.recommended_mode)setMatchMode(item.recommended_mode==="pvp"?"hotseat":"vs_ai");
  if(!bodyRealisticCapable(item))props.setRealistic(false);
 };
 const chooseMode=(mode:Exclude<Mode,"tutorial">)=>{setMatchMode(mode);modeTouched.current=true};
 if(customOpen)return <CustomScenarioEditor onClose={()=>setCustomOpen(false)}
   onLaunch={(id,mode,customSide,profileOverride,realistic)=>props.onStart(id,mode,customSide,profileOverride,realistic)} error={props.error}/>;
 return <main className="landing start-screen">
  <header className="landing-hero"><p className="eyebrow">AUDITABLE NAVAL WARGAME</p><h1>铁底湾的回响 IV</h1><p>从第一道命令开始，学会指挥一支舰队。</p></header>
  <nav className="journey-tabs" aria-label="选择开始方式">
   <button className={journey==="learn"?"active":""} onClick={()=>setJourney("learn")}><span>推荐</span><b>我是第一次玩</b><small>从手把手教学开始</small></button>
   <button className={journey==="play"?"active":""} onClick={()=>setJourney("play")}><span>自由</span><b>我想直接开战</b><small>选择想定与对手</small></button>
  </nav>

  <section className="save-hub">
   <div><p className="eyebrow">舰长日志</p><h2>继续战局或导入存档</h2><p>游戏进度会在每次裁决后自动落库；下载的存档可带到另一台设备。</p></div>
   <label className="save-side">进入阵营<select value={side} onChange={event=>setSide(event.target.value as Side)}><option value="axis">轴心 / 日德方</option><option value="allies">同盟 / 美英方</option></select></label>
   <button className="import-save" disabled={importBusy} onClick={()=>saveInput.current?.click()}>{importBusy?"正在校验…":"导入 .ibs-save.json"}</button>
   <input ref={saveInput} hidden type="file" accept=".json,.ibs-save.json,application/json" onChange={event=>void importSave(event.target.files?.[0])}/>
   {importError&&<p className="save-import-error">导入失败：{importError}</p>}
   {saves.length>0&&<div className="saved-games">{saves.slice(0,6).map(item=><button key={item.game_id} onClick={()=>props.onResume(item,side)}><span><b>{item.scenario_title}</b><small>{item.updated_at.replace("T"," ").replace("Z","")} · {item.mode==="hotseat"?"同机双人":item.mode==="vs_ai"?"状态机 AI":item.mode==="llm"?"LLM 对战":"教学"}</small></span><strong>第 {item.turn}/{item.max_turns} 回合{item.winner?" · 已结束":""} →</strong></button>)}</div>}
  </section>

  {journey==="learn"?<section className="academy-route">
   <div className="start-step"><span>第 1 步</span><h2>选择你的第一堂海战课</h2><p>两条教程都使用正式规则引擎；教官只提交合法订单，不会替你改状态。</p></div>
   <div className="academy-grid">
    <article className="academy-card classic">
     <div className="academy-meta"><span>25–35 分钟</span><span>入门</span><span>经典规则</span></div>
     <p className="academy-kicker">夜战军官速成班</p><h3>通道行动：三艘驱逐舰</h3>
     <p>从一张移动计划表开始，亲手完成转向、鱼雷预射、逐舰齐射和回合战报。</p>
     <ul><li>图形化规划航路，随时看合法轨迹</li><li>使用最新半自动教练填单，再亲手修改</li><li>认识能见度、射界、鱼雷和损伤</li></ul>
     <button onClick={()=>props.onStart("IBS-S-03","tutorial","axis","balanced",false,"classic_night")}><b>开始经典教学</b><span>我会告诉你下一步点哪里 →</span></button>
    </article>
    <article className="academy-card grand">
     <div className="academy-meta"><span>45–60 分钟</span><span>进阶</span><span>真实模式</span></div>
     <p className="academy-kicker">大舰队指挥学院</p><h3>二马：大炮巨舰</h3>
     <p>指挥大和、武藏与巡洋舰纵队迎战美军战列线。先编队，再让巨炮说话。</p>
     <ul><li>建立领舰、旗舰、备用旗舰与六支战列线</li><li>用主力舰齐射体验命中、穿甲与战果战报</li><li>固定战情触发编队降速、永久脱队和撤离</li></ul>
     <div className="script-note"><b>教学剧本</b> 首轮后必定出现一艘轮机受损舰；你必须决定全队减速，还是让它脱队求生。</div>
     <button className="primary" onClick={()=>props.onStart("IBS-S-EM-01","tutorial","axis","balanced",true,"erma_grand_fleet")}><b>进入大舰队教学</b><span>从六支编队初设开始 →</span></button>
    </article>
   </div>
   <button className="text-action" onClick={()=>setJourney("play")}>我已经会玩，直接选择对战模式</button>
  </section>:<section className="battle-setup">
   <button className="text-action custom-entry" onClick={()=>setCustomOpen(true)}>创建自定义剧本 →</button>
   <div className="setup-progress"><b><span>1</span>选择对手</b><b><span>2</span>选择战场</b><b><span>3</span>确认开战</b></div>
   <section className="setup-panel"><h2>1. 你要和谁对战？</h2><div className="mode-picks">
    <button className={matchMode==="hotseat"?"active":""} onClick={()=>chooseMode("hotseat")}><b>同机双人</b><span>秘密交接锁屏</span></button>
    <button className={matchMode==="vs_ai"?"active":""} onClick={()=>chooseMode("vs_ai")}><b>状态机 AI</b><span>随时可修改 AI 建议</span></button>
    <button className={matchMode==="llm"?"active":""} onClick={()=>chooseMode("llm")}><b>多模态 LLM</b><span>自行提供模型接口</span></button>
   </div></section>
   <section className="setup-panel"><h2>2. 选择战场与指挥方式</h2><div className="scenario-picks">{scenarios.map(([id,title,detail])=><button key={id} className={scenario===id?"active":""} onClick={()=>selectScenario(id)}><b>{title}</b><span>{detail}</span></button>)}
    {customs.length>0&&<div className="scenario-divider" role="separator">你的自定义剧本</div>}
    {customs.map(item=><button key={item.id} className={"custom-scenario"+(scenario===item.id?" active":"")} onClick={()=>selectScenario(item.id!)}><b>{item.title}</b><span>{item.turns}回合 · {item.ships.length}艘{item.recommended_mode?` · 推荐${item.recommended_mode==="pvp"?"PvP":"PvE"}`:""}</span></button>)}
   </div>
    <div className={`command-choice ${effectiveRealistic?"on":""}`}><div><b>{effectiveRealistic?"真实模式：编队指挥":"经典模式：逐舰下令"}</b><p>{effectiveRealistic?"只为领舰规划航路，后舰沿共享航迹；包含共同航速、指挥链和脱队撤离。":"逐艘舰船填写移动、炮击与鱼雷订单。"}</p></div><div><button disabled={customLocked} onClick={()=>props.setRealistic(!effectiveRealistic)}>{effectiveRealistic?"切换为经典":"切换为真实"}</button><button className="quiet" onClick={props.onPreviewRealisticRules}>查看真实模式规则</button></div></div>
    {customLocked&&<p className="scenario-lock-hint">这个自定义剧本还达不到真实编队资格（某侧不足 2 艘或还有散舰），将按经典逐舰模式开局；可在「剧本工坊」里编好纵队后再次保存。</p>}
   </section>
   <section className="setup-panel final"><h2>3. 确认你的席位</h2><div className="final-grid">
    <label>我方阵营<select value={side} onChange={event=>setSide(event.target.value as Side)}><option value="axis">轴心 / 日德方</option><option value="allies">同盟 / 美英方</option></select></label>
    {matchMode==="vs_ai"&&<label>AI 风格<select value={profile} onChange={event=>setProfile(event.target.value)}><option value="adaptive">自适应鱼雷战术（推荐）</option><option value="balanced">均衡</option><option value="fleet">大舰队编队</option><option value="line">长纵队</option><option value="cautious">保守</option></select></label>}
   </div>
   {matchMode==="llm"&&<section className="llm-settings"><h3>LLM 连接（只用于本局）</h3><div className="llm-setting-grid">
    <label>接口供应商<select value={props.llmProvider} onChange={event=>{const provider=event.target.value as "deepseek"|"zhipu";props.setLlmProvider(provider);props.setLlmModel(provider==="zhipu"?"glm-5.2":"deepseek-v4-flash");props.setLlmVision(false)}}><option value="zhipu">智谱 BigModel</option><option value="deepseek">DeepSeek</option></select></label>
    <label>模型<input list="llm-models" value={props.llmModel} onChange={event=>{props.setLlmModel(event.target.value);props.setLlmVision(false)}}/><datalist id="llm-models">{props.llmProvider==="zhipu"?<><option value="glm-5.2"/><option value="glm-5.3-flash"/><option value="glm-5v-turbo"/></>:<option value="deepseek-v4-flash"/>}</datalist></label>
   </div><label className="llm-key">API 密钥（仅在本次会话内存中）<input type="password" value={props.llmKey} autoComplete="new-password" onChange={event=>props.setLlmKey(event.target.value)}/></label><label className="vision-toggle"><input type="checkbox" checked={props.llmVision} disabled={!props.llmModel.toLowerCase().startsWith("glm-5v")} onChange={event=>props.setLlmVision(event.target.checked)}/>每阶段发送本方可见地图</label></section>}
   <div className="launch-summary"><div><b>{chosenTitle}</b><span>{effectiveRealistic?"真实编队指挥":"经典逐舰指挥"} · {side==="axis"?"轴心席位":"同盟席位"}</span></div><button className="launch" onClick={()=>props.onStart(scenario,matchMode,side,profile,effectiveRealistic)}>{startLabel} →</button></div>
   </section>
   <details className="start-options"><summary>战报、科研授权与其他选项</summary><label><input type="checkbox" checked={props.recordReport} onChange={event=>props.setRecordReport(event.target.checked)}/>自动记录战报</label><label><input type="checkbox" checked={props.researchAllow} onChange={event=>props.setResearchAllow(event.target.checked)}/>允许匿名对战记录用于科研</label>{props.researchAllow&&<input value={props.researchHandle} maxLength={40} placeholder="称呼（可选）" onChange={event=>props.setResearchHandle(event.target.value)}/>}</details>
   <button className="text-action" onClick={()=>setJourney("learn")}>返回新手教学路线</button>
  </section>}
  {props.error&&<pre className="start-error">{props.error}</pre>}
 </main>;
}
