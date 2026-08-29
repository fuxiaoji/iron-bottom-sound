import {useEffect,useState} from "react";
import {advance,aiOpponent,battleReport,createGame as createGameApi,fieldOfFire,formationMovementPreview,handoff,legalActions,llmOpponent,movementTrajectories,sealedTrajectories,submitOrders,suggestedOrders,tutorialOpponent,viewGame} from "./api";
import type {LLMConnectionConfig} from "./api";
import {BattleReportModal} from "./BattleReportModal";
import {DamageChips} from "./damageSummary";
import {FleetRoster} from "./FleetRoster";
import {HexMap} from "./HexMap";
import {HexMoveEditor} from "./HexMoveEditor";
import {PlanSheet} from "./PlanSheet";
import {RealisticRulesModal} from "./RealisticRulesModal";
import {ShipStatusCard} from "./ShipStatusCard";
import {TutorialPanel} from "./TutorialPanel";
import {StartScreen} from "./StartScreen";
import type {BattleReport,FireHeatmapMode,FireHeatmapResponse,Formation,HexCoord,MovementTrajectory,Observation,Ship,Side} from "./types";
import "./style.css";

const phaseNames:Record<string,string>={formation_setup:"编队初设",contact_setup:"隐蔽标记部署",reinforcement:"增援",movement_planning:"移动计划",torpedo_planning:"鱼雷计划",movement_resolution:"同步移动",gunnery:"炮击",torpedo_effects:"鱼雷效果",fire_end:"起火与回合结束",complete:"想定结束"};
const heatmapModes:[FireHeatmapMode,string][]=[["off","关"],["axis","轴心"],["allies","同盟"],["both","双方"],["ship","选舰"]];
type AIPersona={id:string;label:string;group:string;intro:string;win:string};
// 人机大战对手阵容：内置风格（tactical.PROFILES）+ 进化冠军（champions.CHAMPIONS）。
// win = 双想定混战赛综合胜率差分（对内置对手池，0=五五开；rl/style-tourney-final 实测快照）。
const AI_PROFILES:AIPersona[]=[
 {id:"adaptive",label:"自适应鱼雷战术",group:"新战术 AI",intro:"反事实封路、破 T、切割、交叉雷幕与保雷",win:"训练中"},
 {id:"balanced",label:"均衡",group:"内置风格",intro:"攻守均衡的手调基准",win:"+0.018"},
 {id:"fleet",label:"大舰队编队",group:"内置风格",intro:"抱团编队、火力协同",win:"+0.017"},
 {id:"line",label:"长纵队",group:"内置风格",intro:"纵队突击、队形纪律",win:"-0.073"},
 {id:"brawl",label:"乱阵近战",group:"内置风格",intro:"贴身乱战、鱼雷激进",win:"+0.007"},
 {id:"torpedo",label:"鱼雷专精",group:"内置风格",intro:"远程雷击、抢分专精",win:"+0.003"},
 {id:"cautious",label:"猥琐保守",group:"内置风格",intro:"避战保船、稳守反击",win:"-0.145"},
 {id:"evolved",label:"进化冠军",group:"进化冠军",intro:"GA 进化·防守反击：热点集火+高撤退+抢胜利点",win:"-0.077"},
 {id:"direct_attack",label:"直击专家",group:"鱼雷战术专家",intro:"近距高价值目标直接打击",win:"专项"},
 {id:"area_denial",label:"封锁专家",group:"鱼雷战术专家",intro:"覆盖高概率航路与关键通道",win:"专项"},
 {id:"break_crossing_t",label:"破 T 专家",group:"鱼雷战术专家",intro:"迫使敌舰放弃 T 头阵位",win:"专项"},
 {id:"formation_split",label:"切割专家",group:"鱼雷战术专家",intro:"拉长并分裂敌方编队",win:"专项"},
 {id:"crossfire",label:"交叉雷幕专家",group:"鱼雷战术专家",intro:"多舰多雷道交叉覆盖",win:"专项"},
 {id:"cover_withdrawal",label:"撤退掩护专家",group:"鱼雷战术专家",intro:"在受损舰与敌军间铺设阻断带",win:"专项"},
];
const orderPhases=new Set(["formation_setup","contact_setup","reinforcement","movement_planning","torpedo_planning","gunnery"]);

function explainError(error:unknown){
 const raw=String(error);
 if(raw.includes("请先提供你自己的 LLM API 密钥"))return `LLM 对战和战报叙事需要一个你自己的 DeepSeek（或 OpenAI 兼容）API 密钥。请在开始界面「LLM API 密钥」框填入后再开新局。\n\n裁决原文：${raw}`;
 if(raw.includes("DEEPSEEK_API_KEY"))return `服务端没有配置 DeepSeek 密钥（DEEPSEEK_API_KEY 环境变量）。请在启动后端前设置后重试。\n\n裁决原文：${raw}`;
 if(raw.includes("launch MF exceeds movement plan"))return `鱼雷不能在该舰停止航行之后发射。请删除这次发射，或把“发射 MF”改成不超过上一阶段为该舰填写的航行 MF。\n\n裁决原文：${raw}`;
 if(raw.includes("movement plan"))return `移动计划未通过。请检查错误中点名的舰船：航路里的直航 MF 总数、转向符号和声明速度必须彼此一致。\n\n裁决原文：${raw}`;
 if(raw.includes("launcher"))return `鱼雷发射器设置未通过。请检查发射器、舷侧、角度、枚数和发射 MF。\n\n裁决原文：${raw}`;
 if(raw.includes("cannot bear"))return `有炮位无法转向当前目标。请根据裁决原文找到舰船和炮位，取消勾选该炮位，或为该舰更换目标后重试。\n\n裁决原文：${raw}`;
 return raw;
}

function defaultBatch(view:Observation,side:Side){
 const own=view.ships.filter(ship=>ship.side===side&&!ship.sunk&&ship.position);
 return {
  side,phase:view.phase,formation_setup:[],formation_movement:[],formation_speed_decisions:[],reinforcements:[],contacts:[],contact_movement:[],
  movement:view.phase==="movement_planning"?own.map(ship=>({ship_id:ship.id,plan:"0"})):[],
  gunnery:[],torpedoes:[],smoke_ships:[],smoke:[],illumination:[],searchlights:[],confirmation:{ready:true}
 };
}

function rosterFormations(view:Observation,draft:string):Formation[]{
 if(view.formations.length||view.phase!=="formation_setup")return view.formations;
 try{
  const setup=(JSON.parse(draft) as {formation_setup?:Array<{formation_id:string;name:string;ship_ids:string[];leader_id:string;flagship_id:string;reserve_flagship_id:string;spacing:1|2;heading?:number|null}>}).formation_setup??[];
  return setup.map(order=>({id:order.formation_id,name:order.name,side:view.side,ship_ids:order.ship_ids,leader_id:order.leader_id,flagship_id:order.flagship_id,reserve_flagship_id:order.reserve_flagship_id,succession_order:[order.reserve_flagship_id,...order.ship_ids.filter(id=>id!==order.flagship_id&&id!==order.reserve_flagship_id)],spacing:order.spacing,heading:order.heading??view.ships.find(ship=>ship.id===order.leader_id)?.heading??1,speed:Math.min(...order.ship_ids.map(id=>view.ships.find(ship=>ship.id===id)?.current_speed??0)),status:"assembling",disruption_turn:null,locked_heading:null,locked_speed:null,guide_trail:[]}));
 }catch{return []}
}

export default function App(){
 const [game,setGame]=useState<string>();const [view,setView]=useState<Observation>();const [side,setSide]=useState<Side>("axis");const [mode,setMode]=useState<"hotseat"|"tutorial"|"vs_ai"|"llm">("hotseat");const [aiProfile,setAiProfile]=useState("balanced");const [vsScenario,setVsScenario]=useState("IBS-S-03");const [vsSide,setVsSide]=useState<Side>("axis");const [vsProfile,setVsProfile]=useState("balanced");const [llmScenario,setLlmScenario]=useState("IBS-S-03");const [llmSide,setLlmSide]=useState<Side>("axis");const [llmBusy,setLlmBusy]=useState(false);const [locked,setLocked]=useState(false);const [selected,setSelected]=useState<Ship>();const [error,setError]=useState("");const [draft,setDraft]=useState("");const [planIntent,setPlanIntent]=useState("");const [actionHints,setActionHints]=useState<Record<string,unknown>>({});const [serverReport,setServerReport]=useState<BattleReport>();const [reportOpen,setReportOpen]=useState(false);const [recordReport,setRecordReport]=useState(true);const [reportEnabled,setReportEnabled]=useState(true);const [llmKey,setLlmKey]=useState("");const [llmProvider,setLlmProvider]=useState<"deepseek"|"zhipu">("zhipu");const [llmModel,setLlmModel]=useState("glm-5.2");const [llmVision,setLlmVision]=useState(false);const [researchAllow,setResearchAllow]=useState(false);const [researchHandle,setResearchHandle]=useState("");const [moveEditorShip,setMoveEditorShip]=useState<string|null>(null);const [torpedoAssistOverlay,setTorpedoAssistOverlay]=useState<{path:HexCoord[];intercept:HexCoord|null}|null>(null);const [plannedTrajectories,setPlannedTrajectories]=useState<MovementTrajectory[]|null>(null);const [fireHeatmapMode,setFireHeatmapMode]=useState<FireHeatmapMode>("off");const [fireHeatmap,setFireHeatmap]=useState<FireHeatmapResponse|null>(null);const [debug,setDebug]=useState(false);const [reportMode,setReportMode]=useState(false);const [guideProfiles,setGuideProfiles]=useState<Record<Side,string>>({axis:"balanced",allies:"balanced"});
 const [realisticCommand,setRealisticCommand]=useState(false);
 const [realisticRulesOpen,setRealisticRulesOpen]=useState(false);
 const llmConfig:LLMConnectionConfig={provider:llmProvider,model:llmModel.trim(),vision_enabled:llmVision};
 const createGame=(scenarioId:string,seed:number,nextMode:"hotseat"|"tutorial"|"vs_ai"|"llm"="hotseat",profile?:string,report=true,key?:string|null,consent?:Parameters<typeof createGameApi>[6],config?:LLMConnectionConfig|null)=>createGameApi(scenarioId,seed,nextMode,profile,report,key,consent,config,realisticCommand);
 // URL 深链：?game=&side=&debug=&report=1 直接进入某局（报告视图供战报截图驱动）。
 useEffect(()=>{const params=new URLSearchParams(window.location.search);const g=params.get("game");if(g){const s=(params.get("side") as Side)??"axis";const d=params.get("debug")==="1";const rep=params.get("report")==="1";setGame(g);setSide(s);setDebug(d);setReportMode(rep);viewGame(g,s,d).then(next=>{setView(next);setError("")}).catch(e=>setError(String(e)))}},[]);
 const refresh=async(id=game,s=side)=>{if(id){const next=await viewGame(id,s,debug);setView(next);return next}};
 useEffect(()=>{let active=true;setPlanIntent("");setActionHints({});setMoveEditorShip(null);if(reportMode){setDraft("");return()=>{active=false}}if(view&&game&&orderPhases.has(view.phase)){suggestedOrders(game,side,guideProfiles[side]).then(batch=>{if(active)setDraft(JSON.stringify(batch,null,2))}).catch(()=>{if(active)setDraft(JSON.stringify(defaultBatch(view,side),null,2))});legalActions(game,side).then(actions=>{if(active)setActionHints(actions[0]?.schema_hint??{})}).catch(()=>{if(active)setActionHints({})})}else setDraft("");return()=>{active=false}},[view,side,game,reportMode]);
 useEffect(()=>{if(view)setSelected(previous=>view.ships.find(ship=>ship.id===previous?.id)??(mode==="tutorial"?view.ships.find(ship=>ship.side===side&&!ship.sunk):undefined))},[view,mode,side]);
 useEffect(()=>{
  if(reportMode){setPlannedTrajectories(null);return}
  if(!game||!view){setPlannedTrajectories(null);return}
  if(view.phase==="torpedo_planning"){
   // 移动阶段已封存：鱼雷计划阶段保留船的运动轨迹（调试模式含敌方）。
   let cancelled=false;
   sealedTrajectories(game,side,debug).then(result=>{if(!cancelled)setPlannedTrajectories(result.trajectories)}).catch(()=>{if(!cancelled)setPlannedTrajectories(null)});
   return()=>{cancelled=true};
  }
  if(view.phase!=="movement_planning"){setPlannedTrajectories(null);return}
  let cancelled=false;
  const timer=window.setTimeout(()=>{
   let plans:{ship_id:string;plan:string}[]=[];
   try{
    const parsed=JSON.parse(draft) as {movement?:{ship_id:string;plan?:string|null;speed?:number|null}[];formation_movement?:unknown[]};
    if(parsed.formation_movement?.length){formationMovementPreview(game,side,parsed.formation_movement).then(result=>{if(!cancelled)setPlannedTrajectories(result.trajectories)}).catch(()=>{if(!cancelled)setPlannedTrajectories(null)});return}
    plans=(parsed.movement??[]).filter(entry=>entry&&entry.ship_id).map(entry=>({ship_id:entry.ship_id,plan:String(entry.plan??"0")}));
   }catch{ if(!cancelled)setPlannedTrajectories(null);return }
   if(!plans.length){if(!cancelled)setPlannedTrajectories([]);return}
   movementTrajectories(game,side,plans).then(result=>{if(!cancelled)setPlannedTrajectories(result.trajectories)}).catch(()=>{if(!cancelled)setPlannedTrajectories(null)});
  },250);
  return()=>{cancelled=true;window.clearTimeout(timer)};
 },[game,side,view,draft,debug]);
 useEffect(()=>{
  if(reportMode){setFireHeatmap(null);return}
  if(!game||!view||fireHeatmapMode==="off"){setFireHeatmap(null);return}
  let cancelled=false;
  const shipId=fireHeatmapMode==="ship"?(selected&&selected.position?selected.id:null):null;
  if(fireHeatmapMode==="ship"&&!shipId){setFireHeatmap(null);return}
  fieldOfFire(game,side,shipId).then(result=>{if(!cancelled)setFireHeatmap(result)}).catch(()=>{if(!cancelled)setFireHeatmap(null)});
  return()=>{cancelled=true};
 },[game,side,view,fireHeatmapMode,selected]);
 const start=async(scenario_id:string,nextMode:"hotseat"|"tutorial"|"vs_ai"|"llm"="hotseat",playerSide:Side="axis",profile="balanced")=>{try{if(nextMode==="llm"&&!llmModel.trim())throw new Error("请先填写模型名称");const g=await createGame(scenario_id,1,nextMode,profile,recordReport,llmKey||null,{allow:researchAllow,handle:researchHandle||null},nextMode==="llm"?llmConfig:null);setGame(g.game_id);setMode(nextMode);setAiProfile(profile);setSide(playerSide);setLlmBusy(false);setServerReport(undefined);setReportOpen(false);setReportEnabled(recordReport);setMoveEditorShip(null);setTorpedoAssistOverlay(null);setPlannedTrajectories(null);setFireHeatmapMode("off");setFireHeatmap(null);setDebug(false);setView(await viewGame(g.game_id,playerSide,false));setError("")}catch(e){setError(String(e))}};
 const toggleDebug=async()=>{const next=!debug;setDebug(next);if(game)setView(await viewGame(game,side,next))};
 const clearAndLock=async()=>{if(game)await handoff(game);setView(undefined);setSelected(undefined);setDraft("");setPlanIntent("");setActionHints({});setServerReport(undefined);setReportOpen(false);setMoveEditorShip(null);setTorpedoAssistOverlay(null);setPlannedTrajectories(null);setFireHeatmapMode("off");setFireHeatmap(null);setDebug(false);setLocked(true)};
 const commitMove=(plan:string,speed:number)=>{if(!moveEditorShip)return;try{const next=JSON.parse(draft) as {movement?:{ship_id:string;plan:string;speed?:number|null}[]};const order=next.movement?.find(item=>item.ship_id===moveEditorShip);if(order){order.plan=plan;order.speed=speed;setDraft(JSON.stringify(next,null,2))}}catch{/* 草稿非 JSON 时不写回 */}setMoveEditorShip(null)};
const changeGuide=async(profile:string)=>{setGuideProfiles(prev=>({...prev,[side]:profile}));if(!game||!view)return;try{const batch=await suggestedOrders(game,side,profile);setDraft(JSON.stringify(batch,null,2));setError("")}catch(e){setError(String(e))}};
 const openServerReport=async()=>{if(!game)return;try{setServerReport(await battleReport(game));setReportOpen(true)}catch(e){setError(String(e))}};
 const act=async()=>{if(!game||!view)return;try{
  if(orderPhases.has(view.phase)){
   const batch=JSON.parse(draft);const result=await submitOrders(game,side,batch);
   if(mode==="tutorial"){await tutorialOpponent(game,side);await advance(game,side);await refresh(game,side)}else if(mode==="vs_ai"){await aiOpponent(game,side,aiProfile);await advance(game,side);await refresh(game,side)}else if(mode==="llm"){setLlmBusy(true);try{await llmOpponent(game,side,{...(llmKey?{api_key:llmKey}:{}),config:llmConfig});await advance(game,side);await refresh(game,side)}finally{setLlmBusy(false)}}else{if(result.both_submitted)await advance(game,side);await clearAndLock()}
  }else{const makeReport=view.phase==="fire_end";await advance(game,side);const nextView=await refresh();if(makeReport&&nextView)await openServerReport()}
  setError("");
 }catch(e){setError(explainError(e))}};
 const unlock=async()=>{if(!game)return;const next:Side=side==="axis"?"allies":"axis";setSide(next);setView(await viewGame(game,next,debug));setSelected(undefined);setLocked(false)};
 if(!game)return <><StartScreen realistic={realisticCommand} setRealistic={setRealisticCommand} recordReport={recordReport} setRecordReport={setRecordReport} researchAllow={researchAllow} setResearchAllow={setResearchAllow} researchHandle={researchHandle} setResearchHandle={setResearchHandle} llmProvider={llmProvider} setLlmProvider={setLlmProvider} llmModel={llmModel} setLlmModel={setLlmModel} llmKey={llmKey} setLlmKey={setLlmKey} llmVision={llmVision} setLlmVision={setLlmVision} onStart={start} onPreviewRealisticRules={()=>setRealisticRulesOpen(true)} error={error}/>{realisticRulesOpen&&<RealisticRulesModal onClose={()=>setRealisticRulesOpen(false)}/>}</>;
 if(locked)return <main className="handoff"><div><p>上一方观察、草稿和选择已销毁</p><h1>请交给另一方</h1><button onClick={unlock}>确认无人旁观，进入 {side==="axis"?"同盟":"轴心"} 方</button></div></main>;
 if(!view)return null;
 if(reportMode)return <main className={`game report ${mode}`}><header><div><p className="eyebrow">{view.scenario_id}</p><h1>{view.scenario_title}</h1></div><div className="turn">第 {view.turn}/{view.max_turns} 回合<br/><b>{phaseNames[view.phase]}</b></div><span className="report-note">报告视图 · {side==="axis"?"轴心":"同盟"}视角</span>{reportEnabled&&<button className="report-button" onClick={openServerReport}>战报</button>}</header><section className="workspace report-workspace"><div className="map-column"><HexMap ships={view.ships} torpedoTracks={view.torpedo_tracks} markers={view.markers} onSelect={setSelected} viewerSide={side} visibility={view.visibility} showVisibility={mode==="tutorial"}/></div></section>{reportOpen&&serverReport&&<BattleReportModal report={serverReport} onClose={()=>setReportOpen(false)}/>}{error&&<div className="error"><b>还不能继续：</b><br/>{error}</div>}</main>;
 return <main className={`game ${mode}`}><header><div><p className="eyebrow">{mode==="tutorial"?"GUIDED TUTORIAL":view.scenario_id}</p><h1>{mode==="tutorial"?"新手教学：通道行动":view.scenario_title}</h1>{mode==="vs_ai"&&<div className="opponent-badge">对手：{AI_PROFILES.find(p=>p.id===aiProfile)?.label??aiProfile}</div>}{mode==="llm"&&<div className="opponent-badge">对手：{llmProvider==="zhipu"?"智谱 GLM":"DeepSeek"} · {llmModel}</div>}</div><div className="turn">第 {view.turn}/{view.max_turns} 回合<br/><b>{phaseNames[view.phase]}</b></div><button className="rules-header-button" onClick={()=>setRealisticRulesOpen(true)}>真实模式规则</button><label className={`debug-toggle${debug?" on":""}`} title="调试模式：查看双方舰船、损伤、计划与历史轨迹（不参与裁决）"><input type="checkbox" checked={debug} onChange={toggleDebug}/>调试</label>{reportEnabled&&<button className="report-button" onClick={openServerReport}>战报</button>}{view.phase==="complete"?<button disabled>对局已结束</button>:<button onClick={act} disabled={llmBusy}>{orderPhases.has(view.phase)?mode==="tutorial"?"检查本课并继续":mode==="vs_ai"?"校验并继续":mode==="llm"?"提交并让 DeepSeek 接招":"校验、封存并交接":"执行引擎裁决"}</button>}</header><section className="workspace"><FleetRoster ships={view.ships} formations={rosterFormations(view,draft)} viewerSide={side} selectedId={selected?.id} onSelect={setSelected}/>{view.phase==="movement_planning"&&moveEditorShip&&view.ships.some(ship=>ship.id===moveEditorShip)?<HexMoveEditor game={game} side={side} view={view} ship={view.ships.find(ship=>ship.id===moveEditorShip)!} onSelect={setSelected} onCommit={commitMove} onExit={()=>setMoveEditorShip(null)} showVisibility={mode==="tutorial"}/>:<div className="map-column"><div className="heatmap-toggle" role="group" aria-label="射界热力图">{heatmapModes.map(([value,label])=><button key={value} className={fireHeatmapMode===value?"active":""} title={value==="ship"?"选中地图上的舰船后展示其火力热力":undefined} onClick={()=>setFireHeatmapMode(value)}>{label}</button>)}</div>{fireHeatmapMode==="ship"&&selected&&selected.position&&<div className="heatmap-ship-label">{selected.name} · 火力热力</div>}<HexMap ships={view.ships} torpedoTracks={view.torpedo_tracks} markers={view.markers} onSelect={setSelected} viewerSide={side} visibility={view.visibility} showVisibility={mode==="tutorial"} torpedoAssistPaths={torpedoAssistOverlay&&view.phase==="torpedo_planning"?[{label:"鱼雷预测航迹",hexes:torpedoAssistOverlay.path,intercept:torpedoAssistOverlay.intercept??undefined}]:undefined} plannedTrajectories={plannedTrajectories??undefined} fireHeatmaps={fireHeatmap??undefined} fireHeatmapMode={fireHeatmapMode}/></div>}<aside>{mode==="tutorial"&&<TutorialPanel view={view}/>}<ShipStatusCard ship={selected}/>{orderPhases.has(view.phase)&&<section className="order-editor"><h2>本阶段秘密计划表</h2><p>表格修改会同步到完整 OrderBatch；提交时仍由规则引擎严格校验。</p>{mode!=="tutorial"&&<div className="guide-bar"><label>自动指导风格</label><select value={guideProfiles[side]} onChange={e=>changeGuide(e.target.value)}>{[...new Set(AI_PROFILES.map(p=>p.group))].map(g=><optgroup key={g} label={g}>{AI_PROFILES.filter(p=>p.group===g).map(p=><option key={p.id} value={p.id}>{p.label}</option>)}</optgroup>)}</select><span className="guide-intro">状态机 AI 半自动填单 · {AI_PROFILES.find(p=>p.id===guideProfiles[side])?.intro??""}（仅建议，可手改）</span></div>}<PlanSheet view={view} side={side} draft={draft} setDraft={setDraft} intent={planIntent} setIntent={setPlanIntent} actionHints={actionHints} tutorial={mode==="tutorial"} editingShipId={moveEditorShip} onStartMoveEditor={setMoveEditorShip} game={game} onAssistPath={setTorpedoAssistOverlay}/></section>}<h2>裁决日志</h2><ol className="events">{[...view.recent_events].reverse().map(e=><li key={e.sequence}><span>T{e.turn} · {phaseNames[e.phase]}</span>{e.message}{e.dice&&<small>{e.dice.notation}: {e.dice.raw}{e.dice.adjusted!=null&&` → ${e.dice.adjusted}`}</small>}{e.rule&&<code>{e.rule.rule_id} · p.{e.rule.pdf_page}</code>}{e.payload&&<DamageChips damage={e.payload.damage}/>}</li>)}</ol></aside></section>{reportOpen&&serverReport&&<BattleReportModal report={serverReport} onClose={()=>setReportOpen(false)}/>} {realisticRulesOpen&&<RealisticRulesModal onClose={()=>setRealisticRulesOpen(false)}/>} {error&&<div className="error"><b>还不能继续：</b><br/>{error}</div>}{llmBusy&&<div className="llm-mask"><b>{llmProvider==="zhipu"?"智谱 GLM":"DeepSeek"} 正在编写本阶段计划…</b><span>引擎仍会严格校验它的一切订单</span></div>}</main>;
}
