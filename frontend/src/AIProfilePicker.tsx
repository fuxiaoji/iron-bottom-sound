import {useEffect,useId,useRef,useState} from "react";
import {REALISTIC_AI_PROFILES} from "./aiProfiles";

const CLASSIC_PROFILES=[
 {id:"adaptive",label:"自适应鱼雷战术"},
 {id:"balanced",label:"均衡"},
 {id:"fleet",label:"大舰队编队"},
 {id:"line",label:"长纵队"},
 {id:"cautious",label:"保守"},
] as const;

export function aiProfileLabel(profile:string){
 return REALISTIC_AI_PROFILES.find(item=>item.id===profile)?.label
  ?? CLASSIC_PROFILES.find(item=>item.id===profile)?.label ?? profile;
}

// Mode switches remember each mode's choice instead of silently replacing it.
export function useAIProfile(realistic:boolean){
 const remembered=useRef({classic:"adaptive",realistic:"rc_coordinated"});
 const [profile,setProfile]=useState(realistic?"rc_coordinated":"adaptive");
 useEffect(()=>{setProfile(remembered.current[realistic?"realistic":"classic"])},[realistic]);
 const choose=(next:string)=>{
  remembered.current[realistic||next.startsWith("rc_")?"realistic":"classic"]=next;
  setProfile(next);
 };
 return [profile,choose] as const;
}

type Props={profile:string;onChange:(profile:string)=>void;realistic:boolean;
 realisticLocked?:boolean;onEnableRealistic:()=>void;autoFocus?:boolean};

export function AIProfilePicker({profile,onChange,realistic,realisticLocked=false,onEnableRealistic,autoFocus=false}:Props){
 const hintId=useId();
 const selected=REALISTIC_AI_PROFILES.find(item=>item.id===profile);
 const choose=(next:string)=>{
  if(next.startsWith("rc_")){
   if(realisticLocked)return;
   if(!realistic)onEnableRealistic();
  }
  onChange(next);
 };
 return <div className="ai-profile-picker">
  <label>状态机对手类型<select value={profile} autoFocus={autoFocus} aria-describedby={hintId} onChange={event=>choose(event.target.value)}>
   <optgroup label="新 AI · 真实模式">{REALISTIC_AI_PROFILES.map(item=><option key={item.id} value={item.id} disabled={realisticLocked}>
    {item.label}{item.id==="rc_coordinated"?"（推荐）":""}</option>)}</optgroup>
   <optgroup label="旧 AI · 经典 / 真实模式">{CLASSIC_PROFILES.map(item=><option key={item.id} value={item.id}>{item.label}</option>)}</optgroup>
  </select></label>
  <div id={hintId} className="ai-profile-hint">
   {selected&&<p>{selected.intro}</p>}
   <small>{realisticLocked?"新 AI 需要真实模式：请先让双方至少各有两艘船，并把全部舰船编入纵队。":
    realistic?"当前使用真实编队指挥；新旧风格均可选择。":"选择上方的新 AI 会自动切换为真实编队指挥；旧风格保留当前模式。"}</small>
  </div>
 </div>;
}
