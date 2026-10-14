import {useEffect,useRef,useState} from "react";
import type {ReactNode} from "react";
import {aiDebug,memoryExportUrl} from "./api";
import type {NightSetupOptions} from "./api";
import type {Event,HexCoord,NightEnvironment,Observation,Side} from "./types";
import {hexFromLabel,hexLabel} from "./hexGeometry";

export const RULE_NAMES:Record<string,string>={hidden_contacts:"9.1 隐蔽标记",radar:"9.2 雷达",star_shells:"9.3 照明弹",searchlights:"9.4 探照灯",malfunction_66:"9.5 故障",squalls:"9.6 雨飑",smoke:"9.7 烟幕",silhouettes:"9.8 剪影",hidden_damage:"9.9 隐藏战损",blind_torpedoes:"9.10 隐蔽鱼雷"};
export function RuleSetup({value,onChange}:{value:NightSetupOptions;onChange:(v:NightSetupOptions)=>void}){
 const [rain,setRain]=useState(value.squall_hexes.join(" "));
 return <section className="setup-panel night-setup"><h2>夜战与可选规则</h2>
  <p>新局使用 night-v2。未选择时保留剧本默认；剧本强制规则优先。雨飑必须指定中心，不会随机生成。</p>
  <div className="rule-presets"><button onClick={()=>onChange({...value,optional_rules:{...value.optional_rules,radar:true,star_shells:true,searchlights:true,squalls:true,smoke:true}})}>夜战组合</button><button onClick={()=>{setRain("");onChange({optional_rules:{},squall_hexes:[]})}}>恢复剧本默认</button></div>
  <div className="rule-grid">{Object.entries(RULE_NAMES).map(([key,name])=><label key={key}><input type="checkbox" checked={!!value.optional_rules[key]} onChange={e=>{if(key==="squalls"&&!e.target.checked){setRain("");onChange({...value,squall_hexes:[],optional_rules:{...value.optional_rules,[key]:false}})}else onChange({...value,optional_rules:{...value.optional_rules,[key]:e.target.checked}})}}/>{name}</label>)}</div>
  {value.optional_rules.radar&&<label><input type="checkbox" checked={!!value.radar_1942_variant} onChange={e=>onChange({...value,radar_1942_variant:e.target.checked})}/>9.2 附加变体：1942 美舰可雷达射击，首次雷达射击回合限最近目标</label>}
  {value.optional_rules.squalls&&<><label>雨飑中心（空格／逗号分隔）<input aria-label="雨飑中心" value={rain} placeholder="例如 K12 P18；留空＝没有雨区" onChange={e=>{setRain(e.target.value);onChange({...value,squall_hexes:e.target.value.toUpperCase().split(/[\s,，]+/).filter(Boolean)})}}/></label>{!value.squall_hexes.length&&<p className="weather-warning" role="status">已开启雨飑规则，但尚未部署雨区。这局将没有雨；请填写中心格，或关闭雨飑规则。</p>}</>}
 </section>;
}

export function NightSituation({view,environment=view.environment,events=view.recent_events}:{view:Observation;environment?:NightEnvironment;events?:Event[]}){
 if(view.ruleset_version!=="night-v2"||!environment)return null;
 const enabled=(key:string)=>view.enabled_optional_rules?.includes(key);
 const rain=environment.areas?.filter(a=>a.kind==="squall"||a.kind==="storm")??[];
 const stars=environment.areas?.filter(a=>a.kind==="star_shell")??[];
 const beams=environment.beams??[],pending=environment.pending_illumination??[];
 const radar=Object.values(environment.contacts??{}).filter(c=>c==="radar").length;
 const lastAttack=[...events].reverse().find(e=>e.type==="torpedo_attack");
 const torpedoResults=events.filter(e=>["torpedo_attack","torpedo_result"].includes(e.type)).slice(-6);
 const lightingResults=events.filter(e=>["star_shell_fired","aircraft_illumination"].includes(e.type)).slice(-4);
 const modifierNames:Record<string,string>={target_searchlit:"目标受照",searchlight_user:"开灯舰炮击",radar_or_star_shell:"照明弹／雷达",through_smoke:"烟幕"};
 const applied=(e:Event)=>Object.entries((e.payload?.modifiers??{}) as Record<string,number>).filter(([key,value])=>modifierNames[key]&&value!==0).map(([key,value])=>`${modifierNames[key]} ${value>0?"+":""}${value}`).join(" · ");
 const modifiedShots=events.filter(e=>e.type==="gun_mount_attack"&&applied(e)).slice(-4);
 const latestShot=modifiedShots.at(-1);
 return <section className="night-situation" aria-label="夜战态势">
  <div className="night-situation-grid">
   <article><b>{environment.lighting==="night"?"夜间光学":"光学视程"} · {view.visibility} 格</b><span>{environment.recognition_enabled?`发现接触 ≠ 识别 · 近距 ${environment.identification_hexes} 格或有效照明识别`:"亮海面：可视 · 暗海面：视程外"}</span><small>{radar} 个仅雷达接触（蓝色虚线圈）</small></article>
   <article className={enabled("squalls")&&!rain.length?"weather-empty":""}><b>雨飑 · {enabled("squalls")||rain.length?`${rain.length} 个雨区`:"未开启"}</b><span>{rain.length?`中心 ${rain.map(a=>a.center??a.hexes[0]).join("、")}`:enabled("squalls")?"未配置中心，这局没有雨":"开局可指定雨区中心"}</span><small>{rain.length?"蓝灰斜纹区阻挡雷达与射击":"不会自动生成天气"}</small></article>
   <article><b>照明{environment.preview?" · 命令预览":""}</b><span>探照灯 {beams.length} 束 · 生效照明弹 {stars.length} 区</span><small>{pending.length?pending.map(p=>`${p.center} → T${p.turn}移动后检定`).join("；"):"暂无待生效照明弹"}</small>{latestShot&&<small>已结算 T{latestShot.turn}：{applied(latestShot)}</small>}</article>
   <article className="torpedo-situation"><b>可见鱼雷 · {view.torpedo_tracks.length} 组</b><span>{view.torpedo_tracks.length?view.torpedo_tracks.map(t=>`${hexLabel(t.position)} · ${t.salvo_size}枚 · 余程${t.range_remaining}`).join("；"):"海面暂无可见鱼雷"}</span><small>{lastAttack?`最近 T${lastAttack.turn}：${lastAttack.message}`:"命中与损伤在鱼雷结算后显示"}</small></article>
  </div>
  <details><summary>夜战效果与最近结算</summary><div className="night-effect-notes">{Object.entries(environment.effect_notes??{}).filter(([key])=>["visibility","torpedoes"].includes(key)||enabled(key)).map(([key,note])=><p key={key}>{note}</p>)}</div>{modifiedShots.length>0&&<div className="night-results"><b>已应用夜战修正</b>{modifiedShots.map(e=><p key={e.sequence}>T{e.turn} · {e.message}<small>{applied(e)}{e.dice?` · D66 ${e.dice.raw} → ${e.dice.adjusted}`:""}</small></p>)}</div>}{torpedoResults.length>0&&<div className="night-results"><b>最近鱼雷结算</b>{torpedoResults.map(e=><p key={e.sequence}>T{e.turn} · {e.message}</p>)}</div>}{lightingResults.length>0&&<div className="night-results"><b>照明弹检定</b>{lightingResults.map(e=><p key={e.sequence}>T{e.turn} · {e.message}</p>)}</div>}</details>
 </section>;
}

export function NightModal({title,onClose,children}:{title:string;onClose:()=>void;children:ReactNode}){
 const ref=useRef<HTMLElement>(null);
 useEffect(()=>{const previous=document.activeElement as HTMLElement|null;ref.current?.focus();const handler=(e:KeyboardEvent)=>{if(e.key==="Escape")onClose();if(e.key==="Tab"&&ref.current){const nodes=ref.current.querySelectorAll<HTMLElement>('button,input,select,a[href],summary');const first=nodes[0],last=nodes[nodes.length-1];if(e.shiftKey&&document.activeElement===first){e.preventDefault();last?.focus()}else if(!e.shiftKey&&document.activeElement===last){e.preventDefault();first?.focus()}}};window.addEventListener("keydown",handler);return()=>{window.removeEventListener("keydown",handler);previous?.focus()}},[onClose]);
 return <div className="night-modal-mask" onClick={onClose}><section className="night-modal" role="dialog" aria-modal="true" aria-label={title} tabIndex={-1} ref={ref} onClick={e=>e.stopPropagation()}><header><h2>{title}</h2><button onClick={onClose}>关闭</button></header>{children}</section></div>;
}

export function LossModal({view,onClose}:{view:Observation;onClose:()=>void}){
 return <NightModal title="双方战损" onClose={onClose}><p>排水量采用原典 A–I 等级，不换算吨位。沉没、受损与退出分别统计；敌方仅显示已确认战损。</p><div className="loss-grid">{(["axis","allies"] as Side[]).map(side=>{const data=view.battle_losses?.[side];return <article key={side}><h3>{side==="axis"?"轴心舰队":"同盟舰队"}{side===view.side?" · 我方":""}</h3><p>{data?.scope==="complete"?"完整统计":"仅已确认／本地报告"} · 沉没 {data?.sunk_count??0} 艘</p><dl>{Object.entries(data?.by_type??{}).map(([type,count])=><div key={type}><dt>{type}</dt><dd>{count}</dd></div>)}</dl><div className="displacement-bands">{"ABCDEFGHI".split("").map(b=><span key={b}>{b}<b>{data?.by_displacement[b]??0}</b></span>)}</div><ul>{data?.sunk.map(s=><li key={s.id}>{s.name} · {s.ship_type} · {s.displacement_band}级 · 已沉没</li>)}</ul><h4>受损记录</h4><ul>{data?.damaged.map(s=><li key={s.id}>{s.name} · 船体损失 {s.hull_lost}</li>)}</ul>{!data?.damaged.length&&<p>无可确认的受损记录</p>}</article>})}</div></NightModal>;
}

type Candidate={ship_id:string;mount_id?:string;broadside?:string|null;occupied_mount_ids?:string[];target_id?:string;suggested_hexes?:HexCoord[];valid_from_turn?:number};
export function NightOrders({view,draft,setDraft,hints,pickedHex}:{view:Observation;draft:string;setDraft:(v:string)=>void;hints:Record<string,unknown>;pickedHex:HexCoord|null}){
 const legal=hints.night_candidates as {illumination:Candidate[];searchlights:Candidate[];smoke:Candidate[];aircraft_illumination:unknown[]}|undefined;
 const [target,setTarget]=useState("");
 const [error,setError]=useState("");
 useEffect(()=>{if(pickedHex)setTarget(hexLabel(pickedHex))},[pickedHex]);
 if(view.phase!=="gunnery"||!legal)return null;
 const apply=(fn:(b:Record<string,unknown>)=>void)=>{try{const b=JSON.parse(draft);fn(b);setDraft(JSON.stringify(b,null,2));setError("")}catch(e){setError(String(e))}};
 const position=()=>{if(!/^[A-Z]+[1-9]\d*$/.test(target.toUpperCase()))throw new Error("请点击地图或输入有效坐标");return hexFromLabel(target.toUpperCase())};
 const name=(id:string)=>view.ships.find(s=>s.id===id)?.name??id;
 let batch:Record<string,unknown>={};try{batch=JSON.parse(draft)}catch{/* editor will show parse error */}
 const list=(key:string)=>Array.isArray(batch[key])?batch[key] as Array<Record<string,unknown>>:[];
 return <section className="night-orders"><h3>夜战辅助行动</h3><p>{view.environment?.effect_notes?.star_shells} 虚线范围仅为计划，成功检定后才亮起。探照灯直线为本回合照射预览，提交后结算。</p>
 {view.environment?.effect_notes?.searchlights&&legal.searchlights.length>0&&<p>{view.environment.effect_notes.searchlights}</p>}
 {!!(hints.source_blocked_gunnery as unknown[]|undefined)?.length&&<p className="source-blocker">部分远距离目标因 IBS-Q-021（原穿甲表未覆盖）不能自动炮击；仍显示雷达接触。这不是新增最大射程。</p>}
 <label>照明弹目标（点击地图选格）<input aria-label="照明弹目标" value={target} onChange={e=>setTarget(e.target.value.toUpperCase())}/></label>
 {legal.illumination.map(c=><button key={`${c.ship_id}-${c.mount_id}-${c.broadside}`} onClick={()=>apply(b=>{const entries=list("illumination").filter(o=>o.ship_id!==c.ship_id);entries.push({ship_id:c.ship_id,mount_id:c.mount_id,broadside:c.broadside,target_hex:position()});b.illumination=entries;const guns=list("gunnery");for(const gun of guns){if(gun.ship_id===c.ship_id){gun.mounts=(gun.mounts as Array<{mount_id:string}>??[]).filter(m=>!c.occupied_mount_ids?.includes(m.mount_id));gun.primary_target=null;gun.secondary_target=null}}b.gunnery=guns.filter(g=>Array.isArray(g.mounts)&&g.mounts.length)})}>{name(c.ship_id)} · {c.broadside==="port"?"左舷":c.broadside==="starboard"?"右舷":""}{c.mount_id}炮组 → T{c.valid_from_turn}照明</button>)}
 {legal.aircraft_illumination.length>0&&<button onClick={()=>apply(b=>{b.aircraft_illumination=[position()]})}>飞机投放本回合照明弹</button>}
 {legal.searchlights.map(c=><label key={`${c.ship_id}-${c.target_id}`}><input type="checkbox" checked={list("searchlights").some(o=>o.ship_id===c.ship_id&&o.target_id===c.target_id)} onChange={e=>apply(b=>{const rows=list("searchlights").filter(o=>o.ship_id!==c.ship_id);if(e.target.checked)rows.push({...c,active:true});b.searchlights=rows})}/>{name(c.ship_id)} 探照灯 → {name(c.target_id!)}</label>)}
 {legal.smoke.map(c=><label key={c.ship_id}><input type="checkbox" checked={(batch.smoke_ships as string[]??[]).includes(c.ship_id)} onChange={e=>apply(b=>{const ids=(b.smoke_ships as string[]??[]).filter(id=>id!==c.ship_id);if(e.target.checked)ids.push(c.ship_id);b.smoke_ships=ids})}/>{name(c.ship_id)} 沿航迹布烟</label>)}
 <p>{list("illumination").length} 组照明已计划 · {list("searchlights").length} 束探照灯</p>
 {list("illumination").length>0&&<button onClick={()=>apply(b=>{b.illumination=[]})}>取消照明计划（炮位需重新选择）</button>}{error&&<p role="alert">{error}</p>}
 </section>;
}

export function BlindReveal({view,draft,setDraft,hints}:{view:Observation;draft:string;setDraft:(v:string)=>void;hints:Record<string,unknown>}){
 const legal=(hints.night_candidates as {blind_torpedo_reveals?:{track_id:string;position:string}[]}|undefined)?.blind_torpedo_reveals??[];
 if(view.phase!=="torpedo_planning"||!legal.length)return null;
 let b:Record<string,unknown>;try{b=JSON.parse(draft)}catch{return null}
 const selected=b.blind_torpedo_reveals as string[]??[];
 return <section className="night-orders"><h3>9.10 揭示隐蔽鱼雷</h3><p>移动计划已完成。按原典由玩家判断是否接近目标，不添加虚构的“发现距离”。</p>{legal.map(t=><label key={t.track_id}><input type="checkbox" checked={selected.includes(t.track_id)} onChange={e=>{b.blind_torpedo_reveals=e.target.checked?[...selected,t.track_id]:selected.filter(id=>id!==t.track_id);setDraft(JSON.stringify(b,null,2))}}/>{t.position} · {t.track_id}</label>)}</section>;
}

function DebugDecision({entry,view}:{entry:Record<string,unknown>;view:Observation}){
 const plan=(entry.plan??{}) as {phase_goal?:string;unit_intents?:Record<string,string>;contingency?:string[]};
 const name=(id:string)=>view.ships.find(s=>s.id===id)?.name??view.formations.find(f=>f.id===id)?.name??id;
 return <section aria-label="公开决策摘要">{!!entry.model&&<p><strong>模型：</strong>{String(entry.model)}</p>}<p>{String(entry.summary??entry.error??"无决策摘要")}</p>{plan.phase_goal&&<p><strong>阶段目标：</strong>{plan.phase_goal}</p>}{plan.unit_intents&&Object.keys(plan.unit_intents).length>0&&<ul>{Object.entries(plan.unit_intents).map(([id,intent])=><li key={id}><strong>{name(id)}：</strong>{intent}</li>)}</ul>}{plan.contingency&&plan.contingency.length>0&&<p><strong>后续预案：</strong>{plan.contingency.join("；")}</p>}</section>;
}

export function DebugModal({game,view,onClose}:{game:string;view:Observation;onClose:()=>void}){
 const [side,setSide]=useState<Side>(view.side),[turn,setTurn]=useState(""),[phase,setPhase]=useState(""),[formation,setFormation]=useState("");
 const [data,setData]=useState<Awaited<ReturnType<typeof aiDebug>>|null>(null),[error,setError]=useState("");
 const load=(before?:number)=>{setError("");const params:Record<string,string|number>={side};if(turn)params.turn=turn;if(phase)params.phase=phase;if(formation)params.formation_id=formation;if(before)params.before=before;return aiDebug(game,params).then(setData).catch(e=>setError(String(e)))};
 useEffect(()=>{let current=true;setData(null);const params:Record<string,string|number>={side};if(turn)params.turn=turn;if(phase)params.phase=phase;if(formation)params.formation_id=formation;aiDebug(game,params).then(v=>{if(current)setData(v)}).catch(e=>{if(current)setError(String(e))});return()=>{current=false}},[game,side,turn,phase,formation]);
 return <NightModal title="AI 决策与长期记忆" onClose={onClose}><p>显式本地调试：与决策输入分离。只显示公开模型输出、校验和结果，不含模型私有推理或密钥。</p><div className="debug-filters"><label>阵营<select value={side} onChange={e=>setSide(e.target.value as Side)}><option value="axis">轴心</option><option value="allies">同盟</option></select></label><label>回合<input type="number" min="1" value={turn} onChange={e=>setTurn(e.target.value)} placeholder="全部"/></label><label>阶段<select value={phase} onChange={e=>setPhase(e.target.value)}><option value="">全部</option>{["formation_setup","reinforcement","movement_planning","torpedo_planning","gunnery"].map(p=><option key={p}>{p}</option>)}</select></label><label>编队<select value={formation} onChange={e=>setFormation(e.target.value)}><option value="">全部</option>{view.formations.filter(f=>f.side===side).map(f=><option value={f.id} key={f.id}>{f.name}</option>)}</select></label></div><a href={memoryExportUrl(game,side)} download>导出结构化记忆文件</a>
 {error&&<p role="alert">{error}</p>}{!data&&!error&&<p>正在读取…</p>}{data&&<><details><summary>当前阵营记忆</summary><pre>{JSON.stringify(data.memory,null,2)}</pre></details>{data.entries.map(entry=><article className="debug-entry" key={String(entry.id)}><h3>T{String(entry.turn)} · {String(entry.phase)} · {String(entry.status)}</h3><DebugDecision entry={entry} view={view}/><details><summary>模型回复、解析、提交命令、重试与记忆快照</summary><pre>{JSON.stringify(entry,null,2)}</pre></details></article>)}{data.command_delay.map((entry,index)=><details key={index}><summary>命令延迟编队 · {String(entry.formation_id)} · T{String(entry.turn)}</summary><pre>{JSON.stringify(entry,null,2)}</pre></details>)}{!data.entries.length&&!data.command_delay.length&&<p>此筛选条件下尚无已接受的 AI 决策记录。</p>}{data.next_before&&<button onClick={()=>void load(data.next_before!)}>更早一页</button>}</>}
 </NightModal>;
}
