// 战报/实时日志/舰船记录表共享：把引擎下发的归一化损伤摘要渲染成中文 chip。
// 引擎 `_damage_delta` 输出 {hull_lost,speed_lost,fire_added,fire_remaining,
// gun_mounts_destroyed,torpedo_launchers_destroyed,sank,flags}；这里只读值渲染，
// 不复制任何裁决常量。

export interface DamageChip{text:string;tone:"loss"|"fire"|"sunk"|"flag"}

const num=(value:unknown):number=>typeof value==="number"?value:0;

// 战报汇总"损伤船体格数"用：只读引擎下发的数值，不做裁决。
export function damageHullLost(damage?:unknown):number{
 const d=typeof damage==="object"&&damage?damage as Record<string,unknown>:{};
 return num(d.hull_lost);
}

const flagLabels:Record<string,(value:unknown)=>string>={
 mfc_destroyed:()=>"射击指挥仪损毁",
 radar_destroyed:()=>"雷达损毁",
 bridge_destroyed:()=>"舰桥损毁",
 rudder_destroyed:()=>"舵机损毁",
 captain_status:(value)=>value==="killed"?"舰长阵亡":value==="wounded"?"舰长负伤":String(value),
 guns_disabled_turns:(value)=>`炮塔卡死 ${value} 回合`,
 turn_limit_degrees:(value)=>`极限转向 ${value}°`,
 forced_straight_turns:(value)=>`被迫直行 ${value} 回合`,
 forced_circle_turns:(value)=>`被迫旋回 ${value} 回合`,
 forced_speed:(value)=>`限制速度 ${value} MF`,
 forced_speed_turns:(value)=>`限制速度 ${value} 回合`,
};

export function damageChips(damage?:unknown):DamageChip[]{
 const d=typeof damage==="object"&&damage?damage as Record<string,unknown>:{};
 const chips:DamageChip[]=[];
 const hullLost=num(d.hull_lost);
 const speedLost=num(d.speed_lost);
 const fireAdded=num(d.fire_added);
 const fireRemaining=num(d.fire_remaining);
 const mounts=num(d.gun_mounts_destroyed);
 const tubes=num(d.torpedo_launchers_destroyed);
 if(hullLost)chips.push({text:`-${hullLost} 船体`,tone:"loss"});
 if(speedLost)chips.push({text:`失速 ${speedLost}`,tone:"loss"});
 if(fireAdded)chips.push({text:fireAdded>1?`起火×${fireAdded}`:"起火",tone:"fire"});
 if(fireRemaining)chips.push({text:`余火 ${fireRemaining}`,tone:"fire"});
 if(mounts)chips.push({text:`-${mounts} 炮位`,tone:"loss"});
 if(tubes)chips.push({text:`-${tubes} 鱼雷管`,tone:"loss"});
 if(d.sank)chips.push({text:"沉没",tone:"sunk"});
 const flags=typeof d.flags==="object"&&d.flags?d.flags as Record<string,unknown>:{};
 for(const [key,value] of Object.entries(flags)){
  const label=flagLabels[key];
  if(!label||!value)continue;
  chips.push({text:label(value),tone:"flag"});
 }
 return chips;
}

export function DamageChips({damage}:{damage?:unknown}){
 const chips=damageChips(damage);
 if(chips.length===0)return null;
 return <span className="damage-chips">{chips.map((chip,index)=><span className={`damage-chip ${chip.tone}`} key={index}>{chip.text}</span>)}</span>;
}
