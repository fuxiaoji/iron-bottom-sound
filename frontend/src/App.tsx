import {useEffect,useState} from "react";
import {advance,createGame,gameEvents,handoff,legalActions,submitOrders,suggestedOrders,tutorialOpponent,viewGame} from "./api";
import {BattleReportModal} from "./BattleReportModal";
import {HexMap} from "./HexMap";
import {PlanSheet} from "./PlanSheet";
import {ShipStatusCard} from "./ShipStatusCard";
import {TutorialPanel} from "./TutorialPanel";
import type {Observation,Ship,Side,TurnBattleReport} from "./types";
import "./style.css";

const phaseNames:Record<string,string>={contact_setup:"隐蔽标记部署",reinforcement:"增援",movement_planning:"移动计划",torpedo_planning:"鱼雷计划",movement_resolution:"同步移动",gunnery:"炮击",torpedo_effects:"鱼雷效果",fire_end:"起火与回合结束",complete:"想定结束"};
const orderPhases=new Set(["contact_setup","reinforcement","movement_planning","torpedo_planning","gunnery"]);

function explainError(error:unknown){
 const raw=String(error);
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
 const [game,setGame]=useState<string>();const [view,setView]=useState<Observation>();const [side,setSide]=useState<Side>("axis");const [mode,setMode]=useState<"hotseat"|"tutorial">("hotseat");const [locked,setLocked]=useState(false);const [selected,setSelected]=useState<Ship>();const [error,setError]=useState("");const [draft,setDraft]=useState("");const [planIntent,setPlanIntent]=useState("");const [actionHints,setActionHints]=useState<Record<string,unknown>>({});const [battleReport,setBattleReport]=useState<TurnBattleReport>();const [reportOpen,setReportOpen]=useState(false);
 const refresh=async(id=game,s=side)=>{if(id){const next=await viewGame(id,s);setView(next);return next}};
 useEffect(()=>{let active=true;setPlanIntent("");setActionHints({});if(view&&game&&orderPhases.has(view.phase)){suggestedOrders(game,side).then(batch=>{if(active)setDraft(JSON.stringify(batch,null,2))}).catch(()=>{if(active)setDraft(JSON.stringify(defaultBatch(view,side),null,2))});legalActions(game,side).then(actions=>{if(active)setActionHints(actions[0]?.schema_hint??{})}).catch(()=>{if(active)setActionHints({})})}else setDraft("");return()=>{active=false}},[view,side,game]);
 useEffect(()=>{if(mode==="tutorial"&&view)setSelected(previous=>view.ships.find(ship=>ship.id===previous?.id)??view.ships.find(ship=>ship.side===side&&!ship.sunk))},[view,mode,side]);
 const start=async(scenario_id:string,nextMode:"hotseat"|"tutorial"="hotseat")=>{try{const g=await createGame(scenario_id,1,nextMode);setGame(g.game_id);setMode(nextMode);setSide("axis");setBattleReport(undefined);setReportOpen(false);setView(await viewGame(g.game_id,"axis"));setError("")}catch(e){setError(String(e))}};
 const clearAndLock=async()=>{if(game)await handoff(game);setView(undefined);setSelected(undefined);setDraft("");setPlanIntent("");setActionHints({});setBattleReport(undefined);setReportOpen(false);setLocked(true)};
 const openTurnReport=async(id:string,viewer:Side,completedTurn:number,nextView:Observation)=>{let events=nextView.recent_events.filter(event=>event.turn===completedTurn);try{events=(await gameEvents(id,viewer)).filter(event=>event.turn===completedTurn)}catch{/* 阵营过滤后的观察事件仍可安全降级显示。 */}setBattleReport({scenarioTitle:nextView.scenario_title,turn:completedTurn,events,score:nextView.score,winner:nextView.winner,victoryReason:nextView.victory_reason});setReportOpen(true)};
 const act=async()=>{if(!game||!view)return;try{
  if(orderPhases.has(view.phase)){
   const batch=JSON.parse(draft);const result=await submitOrders(game,side,batch);
   if(mode==="tutorial"){await tutorialOpponent(game,side);await advance(game,side);await refresh(game,side)}else{if(result.both_submitted)await advance(game,side);await clearAndLock()}
  }else{const completedTurn=view.turn;const makeReport=view.phase==="fire_end";await advance(game,side);const nextView=await refresh();if(makeReport&&nextView)await openTurnReport(game,side,completedTurn,nextView)}
  setError("");
 }catch(e){setError(explainError(e))}};
 const unlock=async()=>{if(!game)return;const next:Side=side==="axis"?"allies":"axis";setSide(next);setView(await viewGame(game,next));setSelected(undefined);setLocked(false)};
 if(!game)return <main className="landing"><p className="eyebrow">AUDITABLE NAVAL WARGAME</p><h1>铁底湾的回响 IV</h1><p>确定性裁决 · 规则出处 · 同机交接</p><div className="scenario-grid"><button className="tutorial-choice" onClick={()=>start("IBS-S-03","tutorial")}><b>新手教学关</b><span>教官带你完成移动、鱼雷、炮击与损伤</span></button><button onClick={()=>start("IBS-S-03")}><b>想定 3</b><span>通道行动 · 4 回合</span></button><button onClick={()=>start("IBS-S-01")}><b>想定 1</b><span>埃斯佩兰斯角海战 · 7 回合</span></button></div>{error&&<pre>{error}</pre>}</main>;
 if(locked)return <main className="handoff"><div><p>上一方观察、草稿和选择已销毁</p><h1>请交给另一方</h1><button onClick={unlock}>确认无人旁观，进入 {side==="axis"?"同盟":"轴心"} 方</button></div></main>;
 if(!view)return null;
 return <main className={`game ${mode}`}><header><div><p className="eyebrow">{mode==="tutorial"?"GUIDED TUTORIAL":view.scenario_id}</p><h1>{mode==="tutorial"?"新手教学：通道行动":view.scenario_title}</h1></div><div className="turn">第 {view.turn}/{view.max_turns} 回合<br/><b>{phaseNames[view.phase]}</b></div>{battleReport&&<button className="report-button" onClick={()=>setReportOpen(true)}>查看第 {battleReport.turn} 回合战报</button>}{view.phase==="complete"?<button disabled>对局已结束</button>:<button onClick={act}>{orderPhases.has(view.phase)?mode==="tutorial"?"检查本课并继续":"校验、封存并交接":"执行引擎裁决"}</button>}</header><section className="workspace"><HexMap ships={view.ships} onSelect={setSelected} viewerSide={side} visibility={view.visibility} showVisibility={mode==="tutorial"}/><aside>{mode==="tutorial"&&<TutorialPanel view={view}/>}<ShipStatusCard ship={selected}/>{orderPhases.has(view.phase)&&<section className="order-editor"><h2>本阶段秘密计划表</h2><p>表格修改会同步到完整 OrderBatch；提交时仍由规则引擎严格校验。</p><PlanSheet view={view} side={side} draft={draft} setDraft={setDraft} intent={planIntent} setIntent={setPlanIntent} actionHints={actionHints} tutorial={mode==="tutorial"}/></section>}<h2>裁决日志</h2><ol className="events">{[...view.recent_events].reverse().map(e=><li key={e.sequence}><span>T{e.turn} · {phaseNames[e.phase]}</span>{e.message}{e.dice&&<small>{e.dice.notation}: {e.dice.raw}{e.dice.adjusted!=null&&` → ${e.dice.adjusted}`}</small>}{e.rule&&<code>{e.rule.rule_id} · p.{e.rule.pdf_page}</code>}</li>)}</ol></aside></section>{reportOpen&&battleReport&&<BattleReportModal report={battleReport} onClose={()=>setReportOpen(false)}/>} {error&&<div className="error"><b>还不能继续：</b><br/>{error}</div>}</main>;
}
