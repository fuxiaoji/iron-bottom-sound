import {useEffect,useState} from "react";
import {advance,aiOpponent,createGame,fieldOfFire,gameEvents,handoff,legalActions,llmOpponent,movementTrajectories,sealedTrajectories,submitOrders,suggestedOrders,tutorialOpponent,viewGame} from "./api";
import {BattleReportModal} from "./BattleReportModal";
import {DamageChips} from "./damageSummary";
import {FleetRoster} from "./FleetRoster";
import {HexMap} from "./HexMap";
import {HexMoveEditor} from "./HexMoveEditor";
import {PlanSheet} from "./PlanSheet";
import {ShipStatusCard} from "./ShipStatusCard";
import {TutorialPanel} from "./TutorialPanel";
import type {FireHeatmapMode,FireHeatmapResponse,HexCoord,MovementTrajectory,Observation,Ship,Side,TurnBattleReport} from "./types";
import "./style.css";

const phaseNames:Record<string,string>={contact_setup:"隐蔽标记部署",reinforcement:"增援",movement_planning:"移动计划",torpedo_planning:"鱼雷计划",movement_resolution:"同步移动",gunnery:"炮击",torpedo_effects:"鱼雷效果",fire_end:"起火与回合结束",complete:"想定结束"};
const heatmapModes:[FireHeatmapMode,string][]=[["off","关"],["axis","轴心"],["allies","同盟"],["both","双方"],["ship","选舰"]];
const AI_PROFILES:[string,string][]=[["balanced","均衡"],["fleet","大舰队编队"],["line","长纵队"],["brawl","乱阵近战"],["torpedo","鱼雷专精"],["cautious","猥琐保守"]];
const orderPhases=new Set(["contact_setup","reinforcement","movement_planning","torpedo_planning","gunnery"]);

function explainError(error:unknown){
 const raw=String(error);
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
  side,phase:view.phase,reinforcements:[],contacts:[],contact_movement:[],
  movement:view.phase==="movement_planning"?own.map(ship=>({ship_id:ship.id,plan:"0"})):[],
  gunnery:[],torpedoes:[],smoke_ships:[],smoke:[],illumination:[],searchlights:[],confirmation:{ready:true}
 };
}

export default function App(){
 const [game,setGame]=useState<string>();const [view,setView]=useState<Observation>();const [side,setSide]=useState<Side>("axis");const [mode,setMode]=useState<"hotseat"|"tutorial"|"vs_ai"|"llm">("hotseat");const [aiProfile,setAiProfile]=useState("balanced");const [vsScenario,setVsScenario]=useState("IBS-S-03");const [vsSide,setVsSide]=useState<Side>("axis");const [vsProfile,setVsProfile]=useState("balanced");const [llmScenario,setLlmScenario]=useState("IBS-S-03");const [llmSide,setLlmSide]=useState<Side>("axis");const [llmBusy,setLlmBusy]=useState(false);const [locked,setLocked]=useState(false);const [selected,setSelected]=useState<Ship>();const [error,setError]=useState("");const [draft,setDraft]=useState("");const [planIntent,setPlanIntent]=useState("");const [actionHints,setActionHints]=useState<Record<string,unknown>>({});const [battleReport,setBattleReport]=useState<TurnBattleReport>();const [reportOpen,setReportOpen]=useState(false);const [moveEditorShip,setMoveEditorShip]=useState<string|null>(null);const [torpedoAssistOverlay,setTorpedoAssistOverlay]=useState<{path:HexCoord[];intercept:HexCoord|null}|null>(null);const [plannedTrajectories,setPlannedTrajectories]=useState<MovementTrajectory[]|null>(null);const [fireHeatmapMode,setFireHeatmapMode]=useState<FireHeatmapMode>("off");const [fireHeatmap,setFireHeatmap]=useState<FireHeatmapResponse|null>(null);const [debug,setDebug]=useState(false);
 const refresh=async(id=game,s=side)=>{if(id){const next=await viewGame(id,s,debug);setView(next);return next}};
 useEffect(()=>{let active=true;setPlanIntent("");setActionHints({});setMoveEditorShip(null);if(view&&game&&orderPhases.has(view.phase)){suggestedOrders(game,side).then(batch=>{if(active)setDraft(JSON.stringify(batch,null,2))}).catch(()=>{if(active)setDraft(JSON.stringify(defaultBatch(view,side),null,2))});legalActions(game,side).then(actions=>{if(active)setActionHints(actions[0]?.schema_hint??{})}).catch(()=>{if(active)setActionHints({})})}else setDraft("");return()=>{active=false}},[view,side,game]);
 useEffect(()=>{if(view)setSelected(previous=>view.ships.find(ship=>ship.id===previous?.id)??(mode==="tutorial"?view.ships.find(ship=>ship.side===side&&!ship.sunk):undefined))},[view,mode,side]);
 useEffect(()=>{
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
    const parsed=JSON.parse(draft) as {movement?:{ship_id:string;plan?:string|null;speed?:number|null}[]};
    plans=(parsed.movement??[]).filter(entry=>entry&&entry.ship_id).map(entry=>({ship_id:entry.ship_id,plan:String(entry.plan??"0")}));
   }catch{ if(!cancelled)setPlannedTrajectories(null);return }
   if(!plans.length){if(!cancelled)setPlannedTrajectories([]);return}
   movementTrajectories(game,side,plans).then(result=>{if(!cancelled)setPlannedTrajectories(result.trajectories)}).catch(()=>{if(!cancelled)setPlannedTrajectories(null)});
  },250);
  return()=>{cancelled=true;window.clearTimeout(timer)};
 },[game,side,view,draft,debug]);
 useEffect(()=>{
  if(!game||!view||fireHeatmapMode==="off"){setFireHeatmap(null);return}
  let cancelled=false;
  const shipId=fireHeatmapMode==="ship"?(selected&&selected.position?selected.id:null):null;
  if(fireHeatmapMode==="ship"&&!shipId){setFireHeatmap(null);return}
  fieldOfFire(game,side,shipId).then(result=>{if(!cancelled)setFireHeatmap(result)}).catch(()=>{if(!cancelled)setFireHeatmap(null)});
  return()=>{cancelled=true};
 },[game,side,view,fireHeatmapMode,selected]);
 const start=async(scenario_id:string,nextMode:"hotseat"|"tutorial"|"vs_ai"|"llm"="hotseat",playerSide:Side="axis",profile="balanced")=>{try{const g=await createGame(scenario_id,1,nextMode,profile);setGame(g.game_id);setMode(nextMode);setAiProfile(profile);setSide(playerSide);setLlmBusy(false);setBattleReport(undefined);setReportOpen(false);setMoveEditorShip(null);setTorpedoAssistOverlay(null);setPlannedTrajectories(null);setFireHeatmapMode("off");setFireHeatmap(null);setDebug(false);setView(await viewGame(g.game_id,playerSide,false));setError("")}catch(e){setError(String(e))}};
 const toggleDebug=async()=>{const next=!debug;setDebug(next);if(game)setView(await viewGame(game,side,next))};
 const clearAndLock=async()=>{if(game)await handoff(game);setView(undefined);setSelected(undefined);setDraft("");setPlanIntent("");setActionHints({});setBattleReport(undefined);setReportOpen(false);setMoveEditorShip(null);setTorpedoAssistOverlay(null);setPlannedTrajectories(null);setFireHeatmapMode("off");setFireHeatmap(null);setDebug(false);setLocked(true)};
 const commitMove=(plan:string,speed:number)=>{if(!moveEditorShip)return;try{const next=JSON.parse(draft) as {movement?:{ship_id:string;plan:string;speed?:number|null}[]};const order=next.movement?.find(item=>item.ship_id===moveEditorShip);if(order){order.plan=plan;order.speed=speed;setDraft(JSON.stringify(next,null,2))}}catch{/* 草稿非 JSON 时不写回 */}setMoveEditorShip(null)};
 const openTurnReport=async(id:string,viewer:Side,completedTurn:number,nextView:Observation)=>{let events=nextView.recent_events.filter(event=>event.turn===completedTurn);try{events=(await gameEvents(id,viewer)).filter(event=>event.turn===completedTurn)}catch{/* 阵营过滤后的观察事件仍可安全降级显示。 */}setBattleReport({scenarioTitle:nextView.scenario_title,turn:completedTurn,events,score:nextView.score,winner:nextView.winner,victoryReason:nextView.victory_reason});setReportOpen(true)};
 const act=async()=>{if(!game||!view)return;try{
  if(orderPhases.has(view.phase)){
   const batch=JSON.parse(draft);const result=await submitOrders(game,side,batch);
   if(mode==="tutorial"){await tutorialOpponent(game,side);await advance(game,side);await refresh(game,side)}else if(mode==="vs_ai"){await aiOpponent(game,side,aiProfile);await advance(game,side);await refresh(game,side)}else if(mode==="llm"){setLlmBusy(true);try{await llmOpponent(game,side);await advance(game,side);await refresh(game,side)}finally{setLlmBusy(false)}}else{if(result.both_submitted)await advance(game,side);await clearAndLock()}
  }else{const completedTurn=view.turn;const makeReport=view.phase==="fire_end";await advance(game,side);const nextView=await refresh();if(makeReport&&nextView)await openTurnReport(game,side,completedTurn,nextView)}
  setError("");
 }catch(e){setError(explainError(e))}};
 const unlock=async()=>{if(!game)return;const next:Side=side==="axis"?"allies":"axis";setSide(next);setView(await viewGame(game,next,debug));setSelected(undefined);setLocked(false)};
 if(!game)return <main className="landing"><p className="eyebrow">AUDITABLE NAVAL WARGAME</p><h1>铁底湾的回响 IV</h1><p>确定性裁决 · 规则出处 · 同机交接</p><div className="scenario-grid"><button className="tutorial-choice" onClick={()=>start("IBS-S-03","tutorial")}><b>新手教学关</b><span>教官带你完成移动、鱼雷、炮击与损伤</span></button><button onClick={()=>start("IBS-S-03")}><b>想定 3</b><span>通道行动 · 4 回合</span></button><button onClick={()=>start("IBS-S-01")}><b>想定 1</b><span>埃斯佩兰斯角海战 · 7 回合</span></button><div className="vs-card"><b>人机大战</b><span>选想定、你的阵营与对手风格</span><div className="vs-form"><select value={vsScenario} onChange={e=>setVsScenario(e.target.value)}><option value="IBS-S-03">想定 3 · 通道行动</option><option value="IBS-S-01">想定 1 · 埃斯佩兰斯角</option></select><select value={vsSide} onChange={e=>setVsSide(e.target.value as Side)}><option value="axis">我指挥轴心</option><option value="allies">我指挥同盟</option></select><select value={vsProfile} onChange={e=>setVsProfile(e.target.value)}>{AI_PROFILES.map(([id,label])=><option key={id} value={id}>{label}</option>)}</select><button onClick={()=>start(vsScenario,"vs_ai",vsSide,vsProfile)}>开始</button></div></div><div className="vs-card llm-card"><b>对战 DeepSeek</b><span>LLM 模式 · 你下订单，DeepSeek 接招，引擎唯一裁决</span><div className="vs-form"><select value={llmScenario} onChange={e=>setLlmScenario(e.target.value)}><option value="IBS-S-03">想定 3 · 通道行动</option><option value="IBS-S-01">想定 1 · 埃斯佩兰斯角</option></select><select value={llmSide} onChange={e=>setLlmSide(e.target.value as Side)}><option value="axis">我指挥轴心</option><option value="allies">我指挥同盟</option></select><button onClick={()=>start(llmScenario,"llm",llmSide)}>开始</button></div></div></div>{error&&<pre>{error}</pre>}</main>;
 if(locked)return <main className="handoff"><div><p>上一方观察、草稿和选择已销毁</p><h1>请交给另一方</h1><button onClick={unlock}>确认无人旁观，进入 {side==="axis"?"同盟":"轴心"} 方</button></div></main>;
 if(!view)return null;
 return <main className={`game ${mode}`}><header><div><p className="eyebrow">{mode==="tutorial"?"GUIDED TUTORIAL":view.scenario_id}</p><h1>{mode==="tutorial"?"新手教学：通道行动":view.scenario_title}</h1>{mode==="vs_ai"&&<div className="opponent-badge">对手：{AI_PROFILES.find(([id])=>id===aiProfile)?.[1]??aiProfile}</div>}{mode==="llm"&&<div className="opponent-badge">对手：LLM(DeepSeek)</div>}</div><div className="turn">第 {view.turn}/{view.max_turns} 回合<br/><b>{phaseNames[view.phase]}</b></div><label className={`debug-toggle${debug?" on":""}`} title="调试模式：查看双方舰船、损伤、计划与历史轨迹（不参与裁决）"><input type="checkbox" checked={debug} onChange={toggleDebug}/>调试</label>{battleReport&&<button className="report-button" onClick={()=>setReportOpen(true)}>查看第 {battleReport.turn} 回合战报</button>}{view.phase==="complete"?<button disabled>对局已结束</button>:<button onClick={act} disabled={llmBusy}>{orderPhases.has(view.phase)?mode==="tutorial"?"检查本课并继续":mode==="vs_ai"?"校验并继续":mode==="llm"?"提交并让 DeepSeek 接招":"校验、封存并交接":"执行引擎裁决"}</button>}</header><section className="workspace"><FleetRoster ships={view.ships} viewerSide={side} selectedId={selected?.id} onSelect={setSelected}/>{view.phase==="movement_planning"&&moveEditorShip&&view.ships.some(ship=>ship.id===moveEditorShip)?<HexMoveEditor game={game} side={side} view={view} ship={view.ships.find(ship=>ship.id===moveEditorShip)!} onSelect={setSelected} onCommit={commitMove} onExit={()=>setMoveEditorShip(null)} showVisibility={mode==="tutorial"}/>:<div className="map-column"><div className="heatmap-toggle" role="group" aria-label="射界热力图">{heatmapModes.map(([value,label])=><button key={value} className={fireHeatmapMode===value?"active":""} title={value==="ship"?"选中地图上的舰船后展示其火力热力":undefined} onClick={()=>setFireHeatmapMode(value)}>{label}</button>)}</div>{fireHeatmapMode==="ship"&&selected&&selected.position&&<div className="heatmap-ship-label">{selected.name} · 火力热力</div>}<HexMap ships={view.ships} torpedoTracks={view.torpedo_tracks} markers={view.markers} onSelect={setSelected} viewerSide={side} visibility={view.visibility} showVisibility={mode==="tutorial"} torpedoAssistPaths={torpedoAssistOverlay&&view.phase==="torpedo_planning"?[{label:"鱼雷预测航迹",hexes:torpedoAssistOverlay.path,intercept:torpedoAssistOverlay.intercept??undefined}]:undefined} plannedTrajectories={plannedTrajectories??undefined} fireHeatmaps={fireHeatmap??undefined} fireHeatmapMode={fireHeatmapMode}/></div>}<aside>{mode==="tutorial"&&<TutorialPanel view={view}/>}<ShipStatusCard ship={selected}/>{orderPhases.has(view.phase)&&<section className="order-editor"><h2>本阶段秘密计划表</h2><p>表格修改会同步到完整 OrderBatch；提交时仍由规则引擎严格校验。</p><PlanSheet view={view} side={side} draft={draft} setDraft={setDraft} intent={planIntent} setIntent={setPlanIntent} actionHints={actionHints} tutorial={mode==="tutorial"} editingShipId={moveEditorShip} onStartMoveEditor={setMoveEditorShip} game={game} onAssistPath={setTorpedoAssistOverlay}/></section>}<h2>裁决日志</h2><ol className="events">{[...view.recent_events].reverse().map(e=><li key={e.sequence}><span>T{e.turn} · {phaseNames[e.phase]}</span>{e.message}{e.dice&&<small>{e.dice.notation}: {e.dice.raw}{e.dice.adjusted!=null&&` → ${e.dice.adjusted}`}</small>}{e.rule&&<code>{e.rule.rule_id} · p.{e.rule.pdf_page}</code>}{e.payload&&<DamageChips damage={e.payload.damage}/>}</li>)}</ol></aside></section>{reportOpen&&battleReport&&<BattleReportModal report={battleReport} onClose={()=>setReportOpen(false)}/>} {error&&<div className="error"><b>还不能继续：</b><br/>{error}</div>}{llmBusy&&<div className="llm-mask"><b>DeepSeek 正在思考本阶段对策…</b><span>引擎仍会严格校验它的一切订单</span></div>}</main>;
}
