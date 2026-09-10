import {useEffect} from "react";
import type {Side} from "./types";
import type {BriefingShip,ScenarioBriefing} from "./api";
import {counterImage,counterFallbackImage} from "./assets";

type Props={briefing:ScenarioBriefing;onClose:()=>void;mySide?:Side};

const headingNames=["","东北","东南","南","西南","西北","北"];
const VICTORY_LABELS:Record<string,string>={
 victory_points:"胜利点判定",scenario_03_thresholds:"通道行动目标判定",erma_damage_points:"损伤分判定",
 custom_score_thresholds:"按想定文本判定",
};

function Counter({ship}:{ship:BriefingShip}){
 const img=ship.asset?counterImage(ship.asset):null;
 return <span className={"paper-counter "+(ship.side==="axis"?"ij":"us")+(ship.flagship?" flagship":"")} title={ship.flagship?"旗舰":undefined}>
  {img&&<img src={img} alt="" loading="lazy"/>}
  <span className="c-type">{ship.ship_type??"?"}</span>
  <span className="c-name">{ship.name}</span>
  {ship.vp!=null&&<span className="c-vp">{ship.vp}VP</span>}
  {!ship.recorded&&<span className="c-norec">未建档</span>}
 </span>;
}

function FleetBlock({title,ships,flagshipNote,reinforcements}:{title:string;ships:BriefingShip[];flagshipNote:string|null;reinforcements?:BriefingShip[]}){
 const withPos=ships.filter(s=>s.position);
 const noPos=ships.filter(s=>!s.position);
 return <section className={"paper-fleet "+(ships[0]?.side==="axis"?"axis":"allies")}>
  <h3>{title}{flagshipNote&&<small>{flagshipNote}</small>}</h3>
  <div className="paper-counters">{withPos.map(s=><Counter key={s.id} ship={s}/>)}</div>
  <table className="paper-table"><tbody>
   <tr><th>位置</th>{withPos.map(s=><td key={s.id}>{s.position}</td>)}</tr>
   <tr><th>方向</th>{withPos.map(s=><td key={s.id}>{s.heading??"—"}<small>{s.heading?`（${headingNames[s.heading]??""}）`:""}</small></td>)}</tr>
   <tr><th>速度</th>{withPos.map(s=><td key={s.id}>{s.speed??"—"}</td>)}</tr>
  </tbody></table>
  {reinforcements&&reinforcements.length>0&&<div className="paper-reinforce">
   <h4>援军</h4>
   <div className="paper-counters">{reinforcements.map(s=><Counter key={s.id} ship={s}/>)}</div>
  </div>}
  {noPos.length>0&&<p className="paper-nopos">入场未定列阵：{noPos.map(s=>s.name).join("、")}（按想定规则入场）</p>}
 </section>;
}

function FormationList({briefing}:{briefing:ScenarioBriefing}){
 if(!briefing.formations)return null;
 const sideName:Record<Side,string>={axis:"轴心（日本）",allies:"同盟（美英）"};
 return <section className="paper-formations">
  <h3>真实模式 · 默认编队提案</h3>
  <p className="paper-fine">{briefing.setup_note??"编队仅为直接开局的默认提案；部署权威仍是想定初始位置与规则。"}</p>
  {(["axis","allies"] as Side[]).map(side=>
   (briefing.formations?.[side]??[]).length>0&&<div key={side} className="paper-formation-side">
    <b>{sideName[side]}</b>
    <ul>{(briefing.formations?.[side]??[]).map(f=><li key={f.id}><b>{f.note??f.id}</b><span>{f.ships.length} 艘纵队</span></li>)}</ul>
   </div>)}
 </section>;
}

export function ScenarioBriefingModal({briefing,onClose,mySide}:Props){
 useEffect(()=>{
  const onKey=(e:KeyboardEvent)=>{if(e.key==="Escape")onClose()};
  window.addEventListener("keydown",onKey);
  return ()=>window.removeEventListener("keydown",onKey);
 },[onClose]);
 const numberText=briefing.number==null?"":String(briefing.number).padStart(2,"0");
 const my=briefing.ships.find(s=>s.side===mySide&&s.flagship)??briefing.ships.find(s=>s.side===mySide);
 return <div className="paper-mask" role="dialog" aria-modal onClick={onClose}>
  <article className="paper-sheet" onClick={e=>e.stopPropagation()}>
   <header className="paper-header"><span>IRON BOTTOM SOUND IV</span><button className="paper-close" onClick={onClose}>关闭 ✕</button></header>
   <div className="paper-title-row">
    <span className="paper-badge"><small>Scenario</small><b>{numberText||briefing.id}</b></span>
    <div><h2>{briefing.title}</h2><p>{briefing.date??"日期未知"}</p></div>
    {my&&<div className="paper-myside">你的席位提示：{my.side==="axis"?"轴心（日本）":"同盟（美英）"}{my.flagship?" · 旗舰 "+my.name:""}</div>}
   </div>
   <FleetBlock title="日本舰队 配置" ships={briefing.ships.filter(s=>s.side==="axis")} flagshipNote="（旗舰加框标示）" reinforcements={briefing.reinforcements?.ships.filter(s=>s.side==="axis")}/>
   <FleetBlock title="盟军舰队 配置" ships={briefing.ships.filter(s=>s.side==="allies")} flagshipNote="（旗舰加框标示）" reinforcements={briefing.reinforcements?.ships.filter(s=>s.side==="allies")}/>
   {briefing.reinforcements&&<p className="paper-reinforce-note">
    援军检定：第 {String((briefing.reinforcements.trigger as {turn?:number}).turn??"—")} 回合掷
    {" "+String((briefing.reinforcements.trigger as {roll?:string}).roll??"1d6")+" "}
    掷出 {(briefing.reinforcements.trigger as {succeeds_on?:number[]}).succeeds_on?.join("/")??"—"} 时，第 {String((briefing.reinforcements.arrival as {turn?:number}).turn??"—")} 回合
    从 {(briefing.reinforcements.arrival as {entry_hex_range?:string[]}).entry_hex_range?.join(" 至 ")??"—"} 间入场。
   </p>}
   <section className="paper-meta">
    <p><b>游戏回合：</b>{briefing.turns} 个回合。<b>能见度：</b>日军 {briefing.visibility.axis} 格，盟军 {briefing.visibility.allies} 格。</p>
   </section>
   {briefing.special_rules.length>0&&<section className="paper-rules">
    <h3>特殊规则</h3>
    <ol>{briefing.special_rules.map(r=><li key={r.id}>{r.text}</li>)}</ol>
   </section>}
   <section className="paper-victory">
    <h3>胜利条件</h3>
    <p className="paper-fine">判定方式：{VICTORY_LABELS[String(briefing.victory.kind)]??String(briefing.victory.kind??"通用规则")}；以下为想定文本，冲突时以想定特例为高优先级。</p>
    <ol>{briefing.special_rules.filter(r=>r.id.endsWith("-R1")&&false).map(()=><li key="unused"/>)}
     {String(briefing.victory.kind)==="victory_points"&&<li>回合结束时统计胜利分：每造成 3 点船体损失计入 1 分{briefing.victory.leader_margin?`；领先 ${String(briefing.victory.leader_margin)} 分或更多为胜利者，其他结果为平局`:""}。</li>}
     {briefing.special_rules.filter(r=>/胜利|平局|胜者/.test(r.text)).map(r=><li key={"v-"+r.id}>{r.text}</li>)}
    </ol>
   </section>
   {briefing.ai_stats&&briefing.ai_stats.games>0&&<section className="paper-ai-stats">
    <h3>AI 自战平衡参考</h3>
    <p className="paper-fine">{briefing.ai_stats.note}</p>
    <p>轴心 {briefing.ai_stats.axis_wins} 胜 · 盟军 {briefing.ai_stats.allies_wins} 胜 · 平局 {briefing.ai_stats.draws}
     （共 {briefing.ai_stats.games} 局{briefing.ai_stats.failures?`，${briefing.ai_stats.failures} 局异常`:""}）
     {briefing.ai_stats.avg_turns!=null&&<span> · 平均 {briefing.ai_stats.avg_turns} 回合</span>}
     {briefing.ai_stats.avg_sunk&&<span> · 场均击沉 轴{briefing.ai_stats.avg_sunk.axis}/盟{briefing.ai_stats.avg_sunk.allies}</span>}
    </p>
   </section>}
   <FormationList briefing={briefing}/>
   <footer className="paper-footer"><span>想定手册 · 双方开局前共知信息</span><span>{briefing.id}</span></footer>
  </article>
 </div>;
}
