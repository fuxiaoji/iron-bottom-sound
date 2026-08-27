import type {Formation,Observation,Ship} from "./types";

export interface FormationSetupDraft{formation_id:string;name:string;ship_ids:string[];leader_id:string;flagship_id:string;reserve_flagship_id:string;spacing:1|2;heading:number|null}
export interface FormationSpeedDraft{formation_id:string;action:"reduce"|"detach";speed?:number|null;detach_ship_ids:string[]}
export interface FormationMovementDraft{formation_id:string;leader_plan:string;spacing:1|2|null;speed_decision:FormationSpeedDraft|null}

const shipName=(ships:Ship[],id:string)=>ships.find(ship=>ship.id===id)?.name??id;

export function FormationSetupPanel({view,orders,onChange}:{view:Observation;orders:FormationSetupDraft[];onChange:(orders:FormationSetupDraft[])=>void}){
 const update=(index:number,patch:Partial<FormationSetupDraft>)=>{const next=structuredClone(orders);Object.assign(next[index],patch);onChange(next)};
 const move=(formationIndex:number,shipId:string,direction:-1|1)=>{const next=structuredClone(orders);const ships=next[formationIndex].ship_ids;const at=ships.indexOf(shipId);const target=at+direction;if(target<0||target>=ships.length)return;[ships[at],ships[target]]=[ships[target],ships[at]];if(direction<0&&target===0)next[formationIndex].leader_id=shipId;onChange(next)};
 return <section className="formation-panel">
  <div className="plan-heading"><h3>编队初设</h3><span className="engine-filtered">最多四队 · 阵营私有</span></div>
  <p className="notation-help">每艘舰必须恰好编入一队。纵队第 1 艘是领舰；旗舰负责指挥，备用旗舰在旗舰失能后继承。</p>
  {orders.map((order,index)=><article className="formation-card" key={order.formation_id}>
   <label>编队名称<input value={order.name} maxLength={40} onChange={event=>update(index,{name:event.target.value})}/></label>
   <div className="formation-controls">
    <label>领舰<select value={order.leader_id} onChange={event=>{const leader=event.target.value;update(index,{leader_id:leader,ship_ids:[leader,...order.ship_ids.filter(id=>id!==leader)]})}}>{order.ship_ids.map(id=><option key={id} value={id}>{shipName(view.ships,id)}</option>)}</select></label>
    <label>旗舰<select value={order.flagship_id} onChange={event=>update(index,{flagship_id:event.target.value})}>{order.ship_ids.map(id=><option key={id} value={id}>{shipName(view.ships,id)}</option>)}</select></label>
    <label>备用旗舰<select value={order.reserve_flagship_id} onChange={event=>update(index,{reserve_flagship_id:event.target.value})}>{order.ship_ids.filter(id=>id!==order.flagship_id).map(id=><option key={id} value={id}>{shipName(view.ships,id)}</option>)}</select></label>
    <label>舰间距<select value={order.spacing} onChange={event=>update(index,{spacing:Number(event.target.value) as 1|2})}><option value={1}>1 格（相邻）</option><option value={2}>2 格（空一格）</option></select></label>
    <label>舰首方向<select value={order.heading??1} onChange={event=>update(index,{heading:Number(event.target.value)})}>{[1,2,3,4,5,6].map(value=><option key={value}>{value}</option>)}</select></label>
   </div>
   <ol className="formation-order">{order.ship_ids.map((id,shipIndex)=><li key={id}><b>{shipIndex+1}. {shipName(view.ships,id)}</b>{id===order.leader_id&&<span>领舰</span>}{id===order.flagship_id&&<span>旗舰</span>}{id===order.reserve_flagship_id&&<span>备用</span>}<button type="button" disabled={shipIndex===0} onClick={()=>move(index,id,-1)}>上移</button><button type="button" disabled={shipIndex===order.ship_ids.length-1} onClick={()=>move(index,id,1)}>下移</button></li>)}</ol>
  </article>)}
 </section>;
}

export function FormationMovementPanel({view,orders,onChange}:{view:Observation;orders:FormationMovementDraft[];onChange:(orders:FormationMovementDraft[])=>void}){
 const byId=new Map((view.formations??[]).map(item=>[item.id,item]));
 const update=(index:number,patch:Partial<FormationMovementDraft>)=>{const next=structuredClone(orders);Object.assign(next[index],patch);onChange(next)};
 return <section className="formation-panel">
  <div className="plan-heading"><h3>编队移动计划</h3><span className="engine-filtered">只给领舰下令</span></div>
  <p className="notation-help">填写领舰航路，后舰由引擎逐 MF 沿共享航迹尾随。共同航速不足时，降低全队速度或让受损舰永久脱队。</p>
  {orders.map((order,index)=>{const formation=byId.get(order.formation_id) as Formation|undefined;const members=formation?.ship_ids.map(id=>view.ships.find(ship=>ship.id===id)).filter(Boolean) as Ship[]|undefined;return <article className="formation-card" key={order.formation_id}>
   <h4>{formation?.name??order.formation_id}</h4><p>{formation?`领舰 ${shipName(view.ships,formation.leader_id)} · 旗舰 ${shipName(view.ships,formation.flagship_id)} · 当前 ${formation.speed} MF`:"编队数据载入中"}</p>
   {formation?.status==="command_disrupted"&&<p className="form-error">指挥中断：本回合锁定舰首 {formation.locked_heading}、航速 {formation.locked_speed} 直航；损伤或碰撞可截断。</p>}
   <div className="formation-controls">
    <label>领舰航路<input value={order.leader_plan} disabled={formation?.status==="command_disrupted"} onChange={event=>update(index,{leader_plan:event.target.value.toUpperCase()})}/></label>
    <label>目标间距<select value={order.spacing??formation?.spacing??1} onChange={event=>update(index,{spacing:Number(event.target.value) as 1|2})}><option value={1}>1 格</option><option value={2}>2 格</option></select></label>
    <label>速度危机<select value={order.speed_decision?.action??"none"} onChange={event=>{const action=event.target.value;if(action==="none")update(index,{speed_decision:null});else update(index,{speed_decision:{formation_id:order.formation_id,action:action as "reduce"|"detach",speed:action==="reduce"?formation?.speed??0:null,detach_ship_ids:[]}})}}><option value="none">无</option><option value="reduce">全队降速</option><option value="detach">受损舰脱队</option></select></label>
    {order.speed_decision?.action==="reduce"&&<label>降至<input type="number" min={0} max={8} value={order.speed_decision.speed??0} onChange={event=>update(index,{speed_decision:{...order.speed_decision!,speed:Number(event.target.value)}})}/></label>}
   </div>
   {order.speed_decision?.action==="detach"&&<fieldset><legend>永久脱队舰</legend>{members?.filter(ship=>ship.id!==formation?.leader_id).map(ship=><label key={ship.id}><input type="checkbox" checked={order.speed_decision?.detach_ship_ids.includes(ship.id)??false} onChange={event=>{const current=order.speed_decision!.detach_ship_ids;update(index,{speed_decision:{...order.speed_decision!,detach_ship_ids:event.target.checked?[...current,ship.id]:current.filter(id=>id!==ship.id)}})}}/>{ship.name} · 合法 {ship.min_legal_speed}–{ship.max_legal_speed} MF</label>)}</fieldset>}
  </article>})}
 </section>;
}
