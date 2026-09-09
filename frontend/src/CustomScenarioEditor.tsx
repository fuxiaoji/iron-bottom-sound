// 剧本工坊：分步向导。0 挑选舰船 → 1 拖编队 → 2 拖纵队上海图定初设 → 3 其他设置 →
// 4 导出/导入/启动（选 PvP/PvE/LLM）。单一不变量：舰船坐标一律由纵队锚点推导。
import {useEffect,useMemo,useRef,useState} from "react";
import type {Side} from "./types";
import type {CustomFormation,CustomScenarioDefinition,CustomShipDefinition,RecommendedMode,ShipCatalogEntry} from "./api";
import {
 createCustomScenario,customScenarios,deleteCustomScenario,loadBuiltinScenarioTemplate,shipCatalog,updateCustomScenario,
} from "./api";
import {counterAssetUrl} from "./assets";
import {EditorDeploymentMap} from "./editor/EditorDeploymentMap";
import {FormationAssignStep} from "./editor/FormationAssignStep";
import {
 autoAssignSide,buildPayload,computeLayout,MAP_SIZE_OPTIONS,MAP_SIZE_STANDARD,mapSizeOfMeta,MAX_WELLS_PER_SIDE,moveShipInto,OPTIONAL_RULES,
 pairSolosIntoWell,patchColumn,pickShip,realisticCapable,reorderInColumn,setColumnFlag,sideLabel,sideShips,
 splitColumnAt,stateFromBody,unpickShip,mergeColumnUp,
} from "./editor/scenario";
import {setActiveMapSize} from "./hexGeometry";
import type {Axial} from "./hexGeometry";
import type {EditorState,ScenarioMeta} from "./editor/scenario";

type Mode="hotseat"|"vs_ai"|"llm";
type Props={onClose:()=>void;onLaunch:(id:string,mode:Mode,side:Side,profile:string,realistic:boolean)=>void;error:string};
const STEPS=["挑选舰船","编组分队","海图初设","其他设置","导出与开战"];
const PROFILE_OPTIONS=[["adaptive","自适应鱼雷战术（推荐）"],["balanced","均衡"],["fleet","大舰队编队"],["line","长纵队"],["cautious","保守"]] as const;
const BUILTIN_TEMPLATES=[["IBS-S-03","通道行动 · 驱逐舰夜战"],["IBS-S-01","埃斯佩兰斯角 · 巡洋舰与增援"],["IBS-S-EM-01","第二次马里亚纳海战 · 24 艘主力舰"]] as const;
const headingOptions=[1,2,3,4,5,6];
const SIDES:Side[]=["axis","allies"];
// 选船列表的舰种排位：主力舰在前、小型舰在后；名录里未收录的类型兜底排最后。
const SHIP_TYPE_RANK:Record<string,number>={BB:0,BC:1,CB:2,CA:3,CL:4,DD:5,APD:6,AV:7};
const typeRank=(shipType:string)=>SHIP_TYPE_RANK[shipType]??99;

function emptyState():EditorState{return {ships:[],columns:{axis:[],allies:[]}}}

export function CustomScenarioEditor({onClose,onLaunch,error}:Props){
 const [catalog,setCatalog]=useState<ShipCatalogEntry[]>([]);
 const [saved,setSaved]=useState<CustomScenarioDefinition[]>([]);
 const [catalogError,setCatalogError]=useState("");
 const [step,setStep]=useState(0);
 const [editorState,setEditorState]=useState<EditorState>(emptyState);
 const [editingId,setEditingId]=useState<string|undefined>(undefined);
 const [meta,setMeta]=useState<ScenarioMeta>({title:"我的铁底湾剧本",turns:12,visibility:{axis:4,allies:4},
   optional_rules:[],description:"",recommended_mode:null});
 const [pickSide,setPickSide]=useState<Side>("axis");
 const [search,setSearch]=useState("");
 const [busy,setBusy]=useState(false);
 const [inlineError,setInlineError]=useState("");
 const [banner,setBanner]=useState<{kind:"warn"|"ok";text:string}|null>(null);
 // step4 开战设置
 const [mode,setMode]=useState<Mode>("hotseat");
 const [launchSide,setLaunchSide]=useState<Side>("axis");
 const [profile,setProfile]=useState("adaptive");
 const [launchRealistic,setLaunchRealistic]=useState(false);
 const [modeTouched,setModeTouched]=useState(false);
 const importRef=useRef<HTMLInputElement>(null);
 const modalImportRef=useRef<HTMLInputElement>(null);
 const [builtinSel,setBuiltinSel]=useState("");
 const [importOpen,setImportOpen]=useState(false);

 const nameOf=useMemo(()=>{const map=new Map(catalog.map(entry=>[entry.id,entry]));return(id:string)=>map.get(id)?.name??id},[catalog]);
 useEffect(()=>{
  Promise.all([shipCatalog(),customScenarios()])
   .then(([ships,scenarios])=>{setCatalog(ships);setSaved(scenarios)})
   .catch(err=>setCatalogError(String(err)));
 },[]);
 useEffect(()=>{
  if(!importOpen)return;
  const onKey=(event:KeyboardEvent)=>{if(event.key==="Escape")setImportOpen(false)};
  window.addEventListener("keydown",onKey);
  return ()=>window.removeEventListener("keydown",onKey);
 },[importOpen]);

 // 剧本所选海图尺寸先进全局几何：本工坊内 computeLayout / 海图越界判定都按该尺寸（缺省标准 46×39）。
 const mapSize=mapSizeOfMeta(meta);
 setActiveMapSize(mapSize);
 const capable=realisticCapable(editorState);
 const layoutErrors=useMemo(()=>computeLayout(editorState).errors,[editorState]);
 const bothSidesPresent=sideShips(editorState,"axis").length>0&&sideShips(editorState,"allies").length>0;
 const shipTotal=editorState.ships.length;

 const togglePick=(entry:ShipCatalogEntry)=>{
  if(editorState.ships.some(ship=>ship.id===entry.id)){setEditorState(state=>unpickShip(state,entry.id));return}
  setEditorState(state=>pickShip(state,entry,pickSide));
  setInlineError("");
 };

 const patchMeta=<K extends keyof ScenarioMeta>(key:K,value:ScenarioMeta[K])=>setMeta(current=>({...current,[key]:value}));
 // 海图尺寸选择：标准图不写尺寸键（旧存档/导出逐字节不变）；大战场等非标准图明确声明。
 const selectMapSize=(size:{columns:number;rows:number;printedColumns:number;printedRows:number})=>{
  const standard=size.columns===MAP_SIZE_STANDARD.columns&&size.rows===MAP_SIZE_STANDARD.rows;
  setMeta(current=>({...current,
   mapColumns:standard?undefined:size.columns,mapRows:standard?undefined:size.rows,
   printedColumns:standard?undefined:size.printedColumns,printedRows:standard?undefined:size.printedRows}));
 };
 const setRecommended=(value:RecommendedMode)=>{
  patchMeta("recommended_mode",value);
  if(!modeTouched){
   if(value==="pvp")setMode("hotseat");
   else if(value==="pve")setMode("vs_ai");
  }
 };

 const visible=useMemo(()=>catalog.filter(entry=>!search||entry.name.toLowerCase().includes(search.toLowerCase())
   ||entry.id.toLowerCase().includes(search.toLowerCase())||String(entry.class_name??"").toLowerCase().includes(search.toLowerCase()))
   // 按舰种分组（同型内可选舰在前），组间稳定排序，便于依作战编成挑舰。
   .sort((a,b)=>typeRank(a.ship_type)-typeRank(b.ship_type)||Number(b.complete)-Number(a.complete)||a.id.localeCompare(b.id)),[catalog,search]);

 const validateStep=(target:number):string|null=>{
  if(target===1){
   if(!bothSidesPresent)return "双方至少各需要 1 艘舰船";
   if(shipTotal<2)return "全剧至少需要 2 艘舰船";
  }
  if(target===2){ // 进海图前保证所有舰都已入列且无重叠
   if(editorState.ships.length===0)return "还没有选任何舰船";
   const errors=computeLayout(editorState).errors;
   if(errors.length)return errors.join("；");
  }
  if(target===4){
   if(!meta.title.trim())return "请先填写剧本名称";
   if(!bothSidesPresent||shipTotal<2)return "双方各至少一艘、全剧至少两艘";
   const errors=computeLayout(editorState).errors;
   if(errors.length)return errors.join("；");
  }
  return null;
 };
 // 向前走一/多步才校验门槛；向后回退与点已完成步骤不校验。
 const goTo=(target:number)=>{if(target<0){onClose();return}if(target>step){const problem=validateStep(target);if(problem){setInlineError(problem);return}}setInlineError("");setStep(target)};
 const headerNav=(target:number)=>{if(target<=step){setInlineError("");setStep(target)}};

 const applyBody=(body:CustomScenarioDefinition)=>{setEditorState(stateFromBody(body,nameOf));setEditingId(undefined)};
 const applyBodyWithMeta=(body:CustomScenarioDefinition)=>{
  applyBody(body);
  const standard=MAP_SIZE_STANDARD;
  const columns=body.map_columns??standard.columns;
  const rows=body.map_rows??standard.rows;
  const printedColumns=body.printed_columns??(columns===standard.columns?standard.printedColumns:columns);
  const printedRows=body.printed_rows??(rows===standard.rows?standard.printedRows:rows);
  const isStandard=columns===standard.columns&&rows===standard.rows&&printedColumns===standard.printedColumns&&printedRows===standard.printedRows;
  setMeta({title:body.title??"",turns:body.turns??12,visibility:body.visibility??{axis:4,allies:4},
   optional_rules:body.optional_rules??[],description:body.description??"",recommended_mode:body.recommended_mode??null,
   mapColumns:isStandard?undefined:columns,mapRows:isStandard?undefined:rows,
   printedColumns:isStandard?undefined:printedColumns,printedRows:isStandard?undefined:printedRows});
  setModeTouched(false);
  setBanner(null);
  setStep(0);
 };

 const loadSaved=(scenario:CustomScenarioDefinition)=>{applyBodyWithMeta(scenario);setEditingId(scenario.id)};
 // 导入/载入会替换当前编辑内容：已有选舰时先让用户确认。
 const confirmReplace=()=>editorState.ships.length===0||window.confirm("载入会替换当前正在编辑的剧本，尚未保存的改动将丢失。继续？");

 const loadBuiltin=async(id:string):Promise<boolean>=>{
  if(!id)return false;
  setBusy(true);setInlineError("");setBanner(null);
  try{
   const template=await loadBuiltinScenarioTemplate(id);
   applyBodyWithMeta(template);
   if(template.warnings?.length)setBanner({kind:"warn",text:template.warnings.join("；")});
   else setBanner({kind:"ok",text:"已载入内置想定作模板，可自由改舰与布阵。"});
   return true;
  }catch(err){setInlineError(`载入想定失败：${String(err)}`);return false}
  finally{setBusy(false)}
 };

 const save=async(andLaunch:boolean)=>{
  const payload=buildPayload(editorState,meta);
  if(payload.errors.length){setInlineError(payload.errors.join("；"));return}
  if(!meta.title.trim()){setInlineError("请先填写剧本名称");return}
  setBusy(true);setInlineError("");
  try{
   let id=editingId;
   if(id)await updateCustomScenario(id,payload.body);
   else{const created=await createCustomScenario(payload.body);id=created.id}
   setEditingId(id);
   setSaved(await customScenarios());
   if(andLaunch)onLaunch(id!,mode,launchSide,profile,launchRealistic&&capable);
  }catch(err){setInlineError(String(err))}
  finally{setBusy(false)}
 };

 const exportJson=()=>{
  const payload=buildPayload(editorState,meta);
  if(payload.errors.length){setInlineError(payload.errors.join("；"));return}
  const blob=new Blob([JSON.stringify(payload.body,null,2)],{type:"application/json"});
  const url=URL.createObjectURL(blob);
  const a=document.createElement("a");
  a.href=url;a.download=`铁底湾剧本-${(meta.title.trim()||"未命名").replace(/[\\/:*?"<>|]/g,"_")}.json`;a.click();
  URL.revokeObjectURL(url);
  setBanner({kind:"ok",text:"已导出 .json：可分享给朋友，或用「导入剧本」载回修改。"});
 };

 const onImportFile=async(file:File):Promise<boolean>=>{
  setBusy(true);setInlineError("");setBanner(null);
  try{
   const text=await file.text();
   const parsed=JSON.parse(text);
   const pick=<T,>(key:string,fallback:T)=>key in parsed?parsed[key] as T:fallback;
   const rawFormations=pick<Record<string,unknown>>("formations",{});
   const axisRaw=rawFormations.axis??[];
   const alliesRaw=rawFormations.allies??[];
   const dimsNum=(key:string):number|undefined=>{const value=parsed[key];return typeof value==="number"?value:undefined};
   const body:CustomScenarioDefinition={
    title:String(pick("title",meta.title)??meta.title),turns:Number(pick("turns",meta.turns)??meta.turns),
    visibility:{axis:Number(pick("visibility",meta.visibility)?.axis??meta.visibility.axis),allies:Number(pick("visibility",meta.visibility)?.allies??meta.visibility.allies)},
    optional_rules:Array.isArray(pick("optional_rules",[]))?pick("optional_rules",[]) as string[]:[],
    ships:Array.isArray(pick("ships",[]))?pick("ships",[]) as CustomShipDefinition[]:[],
    formations:{axis:Array.isArray(axisRaw)?axisRaw as CustomFormation[]:[],allies:Array.isArray(alliesRaw)?alliesRaw as CustomFormation[]:[]},
    description:String(pick("description","")??""),recommended_mode:pick<RecommendedMode>("recommended_mode",null),
    map_columns:dimsNum("map_columns"),map_rows:dimsNum("map_rows"),
    printed_columns:dimsNum("printed_columns"),printed_rows:dimsNum("printed_rows"),
   };
   applyBodyWithMeta(body);
   return true;
  }catch(err){setInlineError(`导入失败：${String(err)}`);return false}
  finally{setBusy(false)}
 };

 // 便捷绑定，让子步骤只关心本侧
 const onMoveShip=(side:Side)=>(shipId:string,target:string|null)=>
  setEditorState(current=>moveShipInto(current,shipId,target,side));
 const onSplit=(side:Side)=>(columnId:string,shipId:string)=>
  setEditorState(current=>splitColumnAt(current,side,columnId,shipId));
 const onMerge=(side:Side)=>(columnId:string)=>
  setEditorState(current=>mergeColumnUp(current,side,columnId));
 const onReorder=(side:Side)=>(columnId:string,shipId:string,direction:-1|1)=>
  setEditorState(current=>reorderInColumn(current,side,columnId,shipId,direction));
 const onPatch=(side:Side)=>(columnId:string,patch:Partial<{name:string;heading:number;spacing:1|2}>)=>
  setEditorState(current=>patchColumn(current,side,columnId,patch));
 const onFlag=(side:Side)=>(columnId:string,field:"flagshipId"|"reserveId",shipId:string)=>
  setEditorState(current=>setColumnFlag(current,side,columnId,field,shipId));
 const onPairWell=(side:Side)=>(leadId:string,followerId:string)=>
  setEditorState(current=>pairSolosIntoWell(current,side,leadId,followerId));
 const onSetAnchor=(side:Side,columnId:string,anchor:Axial)=>
  setEditorState(current=>patchColumn(current,side,columnId,{anchor}));

 const pickCounts=SIDES.map(side=>({side,count:sideShips(editorState,side).length}));
 const shipHeader=editorState.ships.length===0?null
   :<div className="editor-pick-summary">{pickCounts.map(({side,count})=><span key={side} className={`side-pill ${side}`}>{sideLabel(side)} {count}艘</span>)}{capable&&<span className="capability-badge yes">真实编队可用</span>}</div>;

 return <main className="landing custom-editor wizard">
  <header className="landing-hero editor-hero">
   <p className="eyebrow">SCENARIO WORKSHOP</p><h1>剧本工坊</h1>
   <p>挑舰船 → 拖成编队 → 拖上真海图定初设 → 填设定 → 导出/导入/开战。全程正式规则引擎校验。</p>
  </header>
  <div className="editor-steps" role="tablist" aria-label="工坊步骤">
   {STEPS.map((label,index)=><button key={label} role="tab" aria-selected={step===index}
     className={step===index?"active":step>index?"done":""} onClick={()=>headerNav(index)}>
     <span className="step-dot">{step>index?"✓":index+1}</span><b>{label}</b></button>)}
  </div>
  <div className="editor-import-toolbar">
   <button className="editor-import-open" onClick={()=>setImportOpen(true)}
     title="载入他人导出的 .json 剧本，或把服务器上已保存的剧本载回来继续编辑">⇪ 导入剧本（他人 .json / 服务器存档）</button>
  </div>
  {banner&&<div className={`editor-banner ${banner.kind}`}><span>{banner.text}</span><button onClick={()=>setBanner(null)}>×</button></div>}
  {inlineError&&<div className="editor-inline-errors">{inlineError}</div>}

  {step===0&&<section className="editor-panel editor-step-pick">
   <div className="editor-side-head"><h2>第 1 步 · 挑选参战舰船</h2><p className="muted">先把要上场的舰都选进来；编队与布阵随后进行。同名同型的目录舰已并入其完整档案，不再重复出现；标「未建档」的行只有名录、暂无战力数据，暂不可选。</p></div>
   {shipHeader}
   <div className="custom-filters">
    <input placeholder="搜索舰名、舰级或 ID" value={search} onChange={event=>setSearch(event.target.value)}/>
    <label className="editor-pick-side">加入<select value={pickSide} onChange={event=>setPickSide(event.target.value as Side)}>
      <option value="axis">轴心 / 日德方</option><option value="allies">同盟 / 美英方</option></select></label>
   </div>
   <div className="ship-picker editor-ship-picker">{visible.map(entry=>{
    const picked=editorState.ships.some(ship=>ship.id===entry.id);
    const ready=Boolean(entry.complete); // 有完整性能档案即可选（棋子图缺省时海图用舰首/舰名兜底）
    const locked=!ready;
    return <button type="button" key={entry.id} className={(picked?"selected ":"")+(locked?"locked":"")}
      disabled={locked} onClick={()=>togglePick(entry)}>
     {entry.asset&&<img src={counterAssetUrl(entry.asset)} alt=""/>}
     <span><b>{entry.name}</b><small>{entry.ship_type} · {entry.class_name??"未标注舰级"}</small>
     {locked
      ?<em className="not-built">未建档 · 名录舰暂无战力数据，暂不可选</em>
      :<em>{picked?"已加入，再点移除":`点选加入${sideLabel(pickSide)}`}</em>}</span></button>;})}
   </div>
   <div className="editor-step-nav">
    <button className="text-action" onClick={onClose}>取消</button>
    <button className="primary editor-next" onClick={()=>goTo(1)} disabled={!bothSidesPresent||shipTotal<2}>去编队 →</button>
   </div>
  </section>}

  {step===1&&<section className="editor-panel">
   <div className="editor-side-head"><h2>第 2 步 · 拖动分配编队</h2>
    <p className="muted">散舰拖入下方编队井即可归队；单舰（散舰）仍可上地图单独布阵——若每侧都≥2 艘且全舰入队，本剧就支持真实编队指挥。</p>
    <p className="muted"><b>{capable?"✓ 当前每侧所有舰都已编成 ≥2 艘的纵队，真实模式可用。":`提示：真实编队模式要求双方都把所有舰编入 ≥2 艘的纵队（每侧 1–${MAX_WELLS_PER_SIDE} 队）；否则将作为经典逐舰模式开局。`}</b></p></div>
   <div className="editor-both-sides">{SIDES.map(side=><FormationAssignStep key={side} side={side} state={editorState}
     onMoveShip={onMoveShip(side)} onSplit={onSplit(side)} onMergeUp={onMerge(side)}
     onAutoAssign={()=>setEditorState(current=>autoAssignSide(current,side))}
     onPairWell={onPairWell(side)}
     onReorder={onReorder(side)} onPatch={onPatch(side)} onFlag={onFlag(side)}/>)}
   </div>
   <div className="editor-step-nav">
    <button className="text-action" onClick={()=>goTo(0)}>← 上一步</button>
    <button className="primary editor-next" onClick={()=>goTo(2)}>去海图定初设 →</button>
   </div>
  </section>}

  {step===2&&<section className="editor-panel editor-step-map">
   <div className="editor-side-head"><h2>第 3 步 · 拖动纵队上海图（定初设）</h2>
    <p className="muted">拖动纵队内任意一枚棋子即可整队平移：你抓的是哪艘，指针所在的格就是它自己的落点；其余舰沿航向尾向以设定间距自动排成纵队（与引擎同一套几何）。金框虚线为整队 ghost 预览。</p></div>
   <EditorDeploymentMap state={editorState} onSetAnchor={onSetAnchor} mapSize={mapSize}/>
   <div className="editor-step-nav">
    <button className="text-action" onClick={()=>goTo(1)}>← 上一步</button>
    <button className="primary editor-next" onClick={()=>goTo(3)}>定好了，继续设定 →</button>
   </div>
  </section>}

  {step===3&&<section className="editor-panel">
   <div className="editor-side-head"><h2>第 4 步 · 其他设置</h2><p className="muted">回合、能见度、可选规则与推荐玩法会随剧本一起保存。</p></div>
   <div className="editor-settings-grid">
    <label>剧本名称<input value={meta.title} maxLength={120} onChange={event=>patchMeta("title",event.target.value)}/></label>
    <label>回合数<input type="number" min={1} max={99} value={meta.turns} onChange={event=>patchMeta("turns",Number(event.target.value))}/></label>
    <label>轴心能见度<input type="number" min={1} max={99} value={meta.visibility.axis} onChange={event=>patchMeta("visibility",{...meta.visibility,axis:Number(event.target.value)})}/></label>
    <label>同盟能见度<input type="number" min={1} max={99} value={meta.visibility.allies} onChange={event=>patchMeta("visibility",{...meta.visibility,allies:Number(event.target.value)})}/></label>
    <label>海图尺寸<select value={mapSize.columns===MAP_SIZE_STANDARD.columns&&mapSize.rows===MAP_SIZE_STANDARD.rows?"standard":"big"} onChange={event=>{const option=MAP_SIZE_OPTIONS.find(item=>item.key===event.target.value);if(option)selectMapSize(option.size)}}>
      {MAP_SIZE_OPTIONS.map(option=><option key={option.key} value={option.key}>{option.label}</option>)}
     </select>
     <small>标准 46×39 含 34×27 原印刷区（四周为缓冲海）；大战场为 92×78 整幅印刷，用于超大规模会战想定。载入大战场存档后切回标准会让伸出界外的纵队报错，需重新布防。</small></label>
    <label>推荐玩法<select value={meta.recommended_mode??""} onChange={event=>setRecommended((event.target.value||null) as RecommendedMode)}>
      <option value="">无偏好</option><option value="pvp">PvP 同机对战</option><option value="pve">PvE 打 AI</option></select>
     <small>只是启动默认值：开局时仍可临时换成别的对手。</small></label>
   </div>
   <label className="editor-description">剧本说明（可选，会随导出文件保存）<textarea value={meta.description} maxLength={400} rows={2}
     onChange={event=>patchMeta("description",event.target.value)}/></label>
   <fieldset className="editor-rules"><legend>可选规则</legend>
    <div className="editor-rule-grid">{OPTIONAL_RULES.map(rule=><label key={rule.key}>
      <input type="checkbox" checked={meta.optional_rules.includes(rule.key)}
       onChange={event=>patchMeta("optional_rules",event.target.checked?[...meta.optional_rules,rule.key]:meta.optional_rules.filter(key=>key!==rule.key))}/>{rule.label}</label>)}</div>
   </fieldset>
   <div className="editor-per-ship"><h3>舰船初始航速（各舰可 0–8）</h3>
    <div className="editor-speed-grid">{editorState.ships.map(ship=><label key={ship.id} className={`${ship.side}`}>
     <b>{ship.name}</b><select value={ship.speed}
      onChange={event=>setEditorState(current=>({...current,ships:current.ships.map(item=>item.id===ship.id?{...item,speed:Number(event.target.value)}:item)}))}>
      {[0,1,2,3,4,5,6,7,8].map(value=><option key={value} value={value}>{value}</option>)}</select></label>)}</div>
   </div>
   <div className="editor-step-nav">
    <button className="text-action" onClick={()=>goTo(2)}>← 上一步</button>
    <button className="primary editor-next" onClick={()=>goTo(4)}>下一步：导出与开战 →</button>
   </div>
  </section>}

  {step===4&&<section className="editor-panel editor-step-launch">
   <div className="editor-side-head"><h2>第 5 步 · 导出 / 导入 / 开战</h2>
    <p className="muted">剧本只有在你「保存并开战」或导出时才写入。所有校验都走正式引擎。</p></div>
   {layoutErrors.length>0&&<div className="editor-inline-errors">先解决海图问题：{layoutErrors.join("；")}</div>}
   <div className="editor-launch-grid">
    <section className="editor-card"><h3>保存与启动</h3>
     <label>对手<select value={mode} onChange={event=>{setMode(event.target.value as Mode);setModeTouched(true)}}>
      <option value="hotseat">同机双人 PvP</option><option value="vs_ai">状态机 AI（PvE）</option><option value="llm">多模态 LLM（PvE）</option></select></label>
     <label>你的阵营<select value={launchSide} onChange={event=>setLaunchSide(event.target.value as Side)}>
      <option value="axis">轴心 / 日德方</option><option value="allies">同盟 / 美英方</option></select></label>
     {mode==="vs_ai"&&<label>AI 风格<select value={profile} onChange={event=>setProfile(event.target.value)}>
       {PROFILE_OPTIONS.map(([value,label])=><option key={value} value={value}>{label}</option>)}</select></label>}
     <div className={`command-choice editor-mode ${launchRealistic?"on":""}`}>
      <b>指挥模式</b>
      <button onClick={()=>setLaunchRealistic(!launchRealistic)} disabled={!capable} className={launchRealistic?"active":""}>
       {capable?(launchRealistic?"真实编队指挥（已选）":"真实编队指挥"):"真实模式需双方全部编队后才能选"}
      </button>
     </div>
     {!capable&&<p className="editor-inline-warning">本剧只能按经典逐舰模式开局（某方不足 2 艘或还有散舰）。</p>}
     {meta.recommended_mode&&<p className="muted">该剧本推荐 {meta.recommended_mode==="pvp"?"PvP":"PvE"} 对战，可保持或临时更换。</p>}
     <button className="primary launch editor-launch" disabled={busy} onClick={()=>save(true)}>{busy?"校验保存中…":"保存并开战 →"}</button>
     <button className="quiet" disabled={busy} onClick={()=>save(false)}>只保存剧本</button>
     {error&&<pre className="start-error">{error}</pre>}
    </section>
    <section className="editor-card"><h3>导出当前剧本</h3>
     <p className="muted">导出一个干净的 .json（含位置/编队/设定与推荐玩法），可分享或留档。</p>
     <button className="primary" onClick={exportJson}>导出 .json</button>
    </section>
    <section className="editor-card"><h3>导入</h3>
     <p className="muted">从导出的 .json 载回（会当作新剧本另存，不影响原文件）。</p>
     <input ref={importRef} type="file" accept=".json,application/json" style={{display:"none"}}
       onChange={event=>{const file=event.target.files?.[0];if(file)onImportFile(file);event.target.value=""}}/>
     <button className="primary" onClick={()=>importRef.current?.click()} disabled={busy}>导入 .json 文件</button>
     <p className="muted">或从内置想定改编成模板：</p>
     <div className="builtin-row"><select value={builtinSel} onChange={event=>setBuiltinSel(event.target.value)}>
      <option value="">—— 选择想定 ——</option>{BUILTIN_TEMPLATES.map(([id,label])=><option key={id} value={id}>{label}</option>)}</select>
      <button className="primary" disabled={!builtinSel||busy} onClick={()=>loadBuiltin(builtinSel)}>载入改编</button></div>
    </section>
    <section className="editor-card editor-saved"><h3>已保存的自定义剧本</h3>
     {saved.length===0&&<p className="muted">还没有已保存剧本。</p>}
     {saved.map(scenario=><div className="saved-row" key={scenario.id}>
      <button className="saved-title" onClick={()=>loadSaved(scenario)}><b>{scenario.title}</b>
       <small>{scenario.turns}回合 · {scenario.ships.length}艘{scenario.recommended_mode?` · 推荐${scenario.recommended_mode==="pvp"?"PvP":"PvE"}`:""}</small></button>
      <button className="quiet" onClick={async()=>{if(editingId===scenario.id)setEditingId(undefined);await deleteCustomScenario(scenario.id!);setSaved(await customScenarios())}}>删除</button></div>)}
    </section>
   </div>
   <div className="editor-step-nav">
    <button className="text-action" onClick={()=>goTo(3)}>← 上一步</button>
   </div>
  </section>}

  {importOpen&&<div className="editor-modal-backdrop" onClick={()=>setImportOpen(false)}>
   <div className="editor-modal" role="dialog" aria-modal="true" aria-label="导入剧本" onClick={event=>event.stopPropagation()}>
    <header><h2>导入 / 载入剧本</h2>
     <button className="editor-modal-close" onClick={()=>setImportOpen(false)} aria-label="关闭">×</button></header>
    <p className="muted">载入会回到第 1 步并替换当前编辑内容。可以导入别人导出的 .json，也可以载回服务器上已保存的剧本继续修改。</p>
    <section className="editor-card"><h3><i className="import-source-num">1</i>导入他人导出的 .json 剧本</h3>
     <p className="muted">朋友分享的《铁底湾剧本-*.json》，或你自己导出的留档。解析失败会给出原因，不会改动当前内容。</p>
     <input ref={modalImportRef} type="file" accept=".json,application/json" style={{display:"none"}}
       onChange={event=>{const file=event.target.files?.[0];if(file)void onImportFile(file).then(()=>setImportOpen(false));event.target.value=""}}/>
     <button className="primary" disabled={busy}
       onClick={()=>{if(!confirmReplace())return;modalImportRef.current?.click()}}>选择 .json 文件并载入</button>
    </section>
    <section className="editor-card"><h3><i className="import-source-num">2</i>载回服务器上已保存的剧本</h3>
     {saved.length===0&&<p className="muted">服务器上还没有已保存的自定义剧本——先新建一份并「只保存剧本」，就会出现在这里。</p>}
     {saved.map(scenario=><div className="saved-row" key={scenario.id}>
      <button className="saved-title" onClick={()=>{if(!confirmReplace())return;loadSaved(scenario);setImportOpen(false)}}><b>{scenario.title}</b>
       <small>{scenario.turns}回合 · {scenario.ships.length}艘{scenario.recommended_mode?` · 推荐${scenario.recommended_mode==="pvp"?"PvP":"PvE"}`:""}</small></button>
      <button className="quiet" onClick={async()=>{if(editingId===scenario.id)setEditingId(undefined);await deleteCustomScenario(scenario.id!);setSaved(await customScenarios())}}>删除</button></div>)}
    </section>
    <section className="editor-card"><h3><i className="import-source-num">3</i>以内置想定为模板改编</h3>
     <div className="builtin-row"><select value={builtinSel} onChange={event=>setBuiltinSel(event.target.value)}>
       <option value="">—— 选择想定 ——</option>{BUILTIN_TEMPLATES.map(([id,label])=><option key={id} value={id}>{label}</option>)}</select>
      <button className="primary" disabled={!builtinSel||busy} onClick={async()=>{if(!confirmReplace())return;await loadBuiltin(builtinSel);setImportOpen(false)}}>载入改编</button></div>
     <p className="muted">会丢下增援、胜利条件等内置剧本专属设定（载入时会提示），再当作普通自定义剧本另存。</p>
    </section>
   </div>
  </div>}
  {catalogError&&<pre className="start-error">{catalogError}</pre>}
 </main>;
}
