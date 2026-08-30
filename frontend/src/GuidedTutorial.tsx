import {useEffect,useMemo,useRef,useState} from "react";
import type {Observation} from "./types";
import type {TutorialVariant} from "./TutorialPanel";

type GuideStep={title:string;instruction:string;selectors:string[];fallback:string;event?:"click"|"change";waitForPhase?:boolean};

const submit=(instruction:string):GuideStep=>({title:"封存并继续",instruction,selectors:['main.game > header > button:last-child:not(:disabled)'],fallback:instruction,waitForPhase:true});

export function tutorialSteps(view:Observation,variant:TutorialVariant):GuideStep[]{
 if(variant==="grand"){
  if(view.phase==="formation_setup")return [
   {title:"先检查第一支战列线",instruction:"点击高亮的舰间距，确认纵队按相邻 1 格展开。",selectors:['[data-tutorial="formation-spacing"]'],fallback:"检查第一支编队的舰间距。"},
   submit("点击顶部按钮，让引擎校验六条战列线并封存日方编队。"),
  ];
  if(view.phase==="gunnery")return [
   {title:"为第一艘主力舰筛选射界",instruction:"点击高亮的“为该舰安排齐射”；引擎会为它选择合法目标和炮位。",selectors:['.gunnery-roster button:not(:disabled)','main.game > header > button:last-child:not(:disabled)'],fallback:"当前没有合法炮击目标，直接封存空炮击表。"},
   submit("检查已编排齐射，然后点击顶部按钮开始正式炮击裁决。"),
  ];
  if(view.phase==="movement_planning")return [
   {title:"处理战列线共同速度",instruction:"点击高亮的“速度危机”，为受损编队选择全队降速或受损舰脱队。",selectors:['[data-tutorial="formation-speed"]','main.game > header > button:last-child:not(:disabled)'],fallback:"当前没有共同速度冲突，直接封存编队航路。",event:"change"},
   submit("检查中央虚线预览，再封存全部领舰航路。"),
  ];
  if(view.phase==="movement_resolution")return [submit("点击顶部按钮，逐 MF 观看领舰和后舰沿共享航迹同步移动。")];
  if(view.phase==="complete")return [{title:"打开最终战报",instruction:"点击战报，比较双方战损分并完成复盘。",selectors:['.report-button:not(:disabled)'],fallback:"打开最终战报。"}];
  return [submit(view.phase==="fire_end"?"点击顶部按钮结算火灾与回合结束；战报将自动弹出。":"点击顶部按钮执行当前阶段裁决。")];
 }
 if(view.phase==="movement_planning")return [
  {title:"装载一份可改的示范",instruction:"点击“填入保持接触示例”，先看到合法航路如何写入计划表。",selectors:['[data-tutorial="classic-fill-movement"]'],fallback:"填入教练示范航路。"},
  {title:"打开逐格移动编辑器",instruction:"点击第一艘舰的“逐格推进”，然后在地图上亲手确认航路。",selectors:['[data-tutorial="movement-editor"]','main.game > header > button:last-child:not(:disabled)'],fallback:"若当前没有可编辑舰船，直接封存合法示范。"},
  {title:"确认刚才的逐格航路",instruction:"在地图上点相邻格或保持当前示范，然后点击高亮的“确认”写回计划表。",selectors:['[data-tutorial="movement-confirm"]:not(:disabled)'],fallback:"确认逐格航路。"},
  submit("确认地图虚线终点后，点击顶部按钮封存移动计划。"),
 ];
 if(view.phase==="torpedo_planning")return [
  {title:"尝试建立一张鱼雷订单",instruction:"点击任一可用发射器；枚数、发射格、舷侧和角度都会来自引擎合法行动。",selectors:['.torpedo-roster button:not(:disabled)','main.game > header > button:last-child:not(:disabled)'],fallback:"当前没有合法发射器，封存空鱼雷表也是合法命令。"},
  submit("检查鱼雷预测航迹，或保持空表，然后封存鱼雷计划。"),
 ];
 if(view.phase==="gunnery")return [
  {title:"让引擎筛选合法炮位",instruction:"点击第一艘可射舰的“为该舰安排齐射”，不要手工猜测射界。",selectors:['.gunnery-roster button:not(:disabled)','main.game > header > button:last-child:not(:disabled)'],fallback:"当前没有可见且可射的目标，直接提交空表。"},
  submit("逐舰检查目标和已勾选炮位，然后封存齐射。"),
 ];
 if(view.phase==="complete")return [{title:"打开最终战报",instruction:"点击战报，指出攻击舰、目标舰、骰子和最终损伤。",selectors:['.report-button:not(:disabled)'],fallback:"打开最终战报。"}];
 return [submit(view.phase==="fire_end"?"点击顶部按钮结算火灾与回合结束；战报会自动弹出。":"点击顶部按钮执行当前阶段。")];
}

function firstAvailable(selectors:string[]){
 for(let index=0;index<selectors.length;index+=1){const element=document.querySelector<HTMLElement>(selectors[index]);if(element&&!element.matches(":disabled"))return {element,index}}
 return null;
}

export function GuidedTutorial({sessionKey,view,variant}:{sessionKey:string;view:Observation;variant:TutorialVariant}){
 const phaseKey=`${sessionKey}:${variant}:${view.turn}:${view.phase}`;
 const steps=useMemo(()=>tutorialSteps(view,variant),[phaseKey]);
 const [stepIndex,setStepIndex]=useState(0);
 const [armed,setArmed]=useState(false);
 const [message,setMessage]=useState("");
 const [target,setTarget]=useState<{element:HTMLElement;index:number}|null>(null);
 const [rect,setRect]=useState<DOMRect|null>(null);
 const previousKey=useRef(phaseKey);
 const step=steps[Math.min(stepIndex,steps.length-1)];

 useEffect(()=>{if(previousKey.current!==phaseKey){previousKey.current=phaseKey;setStepIndex(0);setArmed(false);setMessage("");setTarget(null);setRect(null)}},[phaseKey]);
 useEffect(()=>{
  if(!armed||!step)return;
  const refresh=()=>{const next=firstAvailable(step.selectors);if(next){const panel=next.element.closest(".roster")?"fleet":next.element.closest("aside")?"orders":next.element.closest(".map-column,.move-editor,.map-frame")?"map":null;if(panel&&document.documentElement.dataset.mobilePanel!==panel)window.dispatchEvent(new CustomEvent("ibs:mobile-panel",{detail:panel}))}setTarget(current=>current?.element===next?.element&&current?.index===next?.index?current:next);setRect(next?.element.getBoundingClientRect()??null)};
  refresh();const observer=new MutationObserver(refresh);observer.observe(document.body,{childList:true,subtree:true});window.addEventListener("resize",refresh);window.addEventListener("scroll",refresh,true);
  const timer=window.setTimeout(()=>{const next=firstAvailable(step.selectors);next?.element.scrollIntoView({behavior:"smooth",block:"center",inline:"center"});window.setTimeout(refresh,350)},40);
  return()=>{window.clearTimeout(timer);observer.disconnect();window.removeEventListener("resize",refresh);window.removeEventListener("scroll",refresh,true)};
 },[armed,stepIndex,phaseKey]);
 useEffect(()=>{
  if(!armed||!step||!target)return;
  const onInteract=(event:Event)=>{const source=event.target as Node|null;if(!source||!target.element.contains(source)){if(event.type==="click"){event.preventDefault();event.stopPropagation();setMessage("先完成高亮动作；其他区域暂时锁定。")}return}if(event.type===(step.event??"click")&&!step.waitForPhase){window.setTimeout(()=>{setStepIndex(index=>Math.min(index+1,steps.length));setArmed(false);setMessage("✓ 已完成，继续下一步。")},0)}else if(step.waitForPhase&&event.type==="click")setMessage("正在等待引擎校验；若订单有误，请按红色提示修正后重试。")};
  const onKey=(event:KeyboardEvent)=>{if(event.key==="Escape"){setArmed(false);setMessage("已暂停定位。点击“带我去点”可继续。")}};
  document.addEventListener("click",onInteract,true);document.addEventListener("change",onInteract,true);document.addEventListener("keydown",onKey,true);
  return()=>{document.removeEventListener("click",onInteract,true);document.removeEventListener("change",onInteract,true);document.removeEventListener("keydown",onKey,true)};
 },[armed,target,step,steps.length]);
 if(stepIndex>=steps.length)return <div className="forced-coach complete"><b>✓ 本阶段操作已完成</b><span>正在等待引擎进入下一阶段……</span></div>;
 const gap=10;const targetText=target&&target.index>0?step.fallback:step.instruction;
 return <>
  {armed&&rect&&<><div className="coach-masks" aria-hidden="true"><i style={{left:0,top:0,width:"100vw",height:Math.max(0,rect.top-gap)}}/><i style={{left:0,top:Math.max(0,rect.top-gap),width:Math.max(0,rect.left-gap),height:rect.height+gap*2}}/><i style={{left:Math.min(window.innerWidth,rect.right+gap),top:Math.max(0,rect.top-gap),right:0,height:rect.height+gap*2}}/><i style={{left:0,top:Math.min(window.innerHeight,rect.bottom+gap),right:0,bottom:0}}/></div><div className="coach-highlight" style={{left:rect.left-gap,top:rect.top-gap,width:rect.width+gap*2,height:rect.height+gap*2}} aria-hidden="true"/></>}
  <section className={`forced-coach ${armed?"armed":""}`} role="dialog" aria-live="polite" aria-label="强制交互教练">
   <div className="coach-progress">强制教练 · {variant==="grand"?"二马":"通道行动"} · {stepIndex+1}/{steps.length}</div>
   <h2>{step.title}</h2><p>{armed?targetText:step.instruction}</p>
   {message&&<small>{message}</small>}
   {!armed?<button type="button" onClick={()=>{setMessage("");setArmed(true)}}>带我去点这个控件</button>:!target?<b className="coach-wait">正在等待当前阶段控件载入……</b>:<b className="coach-now">现在只能点击高亮区域 · Esc 暂停</b>}
  </section>
 </>;
}
