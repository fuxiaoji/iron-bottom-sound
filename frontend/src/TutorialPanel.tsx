import type {Observation,Phase} from "./types";

const lessons:{phases:Phase[];title:string;goal:string;action:string;rule:string}[]=[
 {phases:["reinforcement"],title:"1. 阶段确认",goal:"认识回合阶段与秘密订单。",action:"想定 3 第一回合没有增援。阅读提示后点击“校验并让教官行动”。",rule:"IBS-R-05 · 规则书 p.6"},
 {phases:["movement_planning"],title:"2. 编制移动",goal:"区分上回合速度、循环上限与本回合实际 MF。",action:"点击地图棋子查看引擎给出的合法 MF 范围，再填写航路。数字是直航 MF，P/S 是左/右转 60°，PP/SS 是 120°。可用示例按钮按合法上限填入。",rule:"IBS-R-06 · 规则书 p.7–8"},
 {phases:["torpedo_planning"],title:"3. 计划鱼雷",goal:"理解鱼雷必须预先指定发射时点和位置。",action:"本次可以留空学习安全通过；随后再用“添加发射”选择发射器、MF、舷侧和角度。非法位置会由引擎拒绝并解释。",rule:"IBS-R-08.2 · 规则书 p.10–11"},
 {phases:["movement_resolution"],title:"4. 同步移动",goal:"观察双方按 MF 脉冲同时移动。",action:"点击“执行引擎裁决”。地图棋子会按双方已封存计划移动，玩家不能在结算中途改令。",rule:"IBS-R-06 · 规则书 p.7"},
 {phases:["gunnery"],title:"5. 炮击",goal:"为可用炮位选择一个已观察目标。",action:"点击“添加齐射”，选择目标和参加射击的炮位；若当前没有合法射界，可不射击直接确认。日志会显示掷骰、修正、查表与规则出处。",rule:"IBS-R-08.1 · 规则书 p.8–10"},
 {phases:["torpedo_effects","fire_end","complete"],title:"6. 损伤与回合结束",goal:"读取鱼雷、火灾、沉没与胜负事件。",action:"依次执行自动裁决，查看舰体格、速度、火灾和炮位状态如何变化。进入下一回合后重复移动—鱼雷—炮击流程。",rule:"IBS-R-08.2 / IBS-R-05 · p.10–12"},
];

export function TutorialPanel({view}:{view:Observation}){
 const index=Math.max(0,lessons.findIndex(lesson=>lesson.phases.includes(view.phase)));
 const lesson=lessons[index];
 const visibleEnemies=view.ships.filter(ship=>ship.side!==view.side&&!ship.sunk);
 return <section className="tutorial-card">
  <div className="tutorial-kicker">教学关 · 第 {index+1}/{lessons.length} 课</div><h2>{lesson.title}</h2>
  <p><b>目标：</b>{lesson.goal}</p><p><b>操作：</b>{lesson.action}</p><code>{lesson.rule}</code>
  {view.phase==="gunnery"&&visibleEnemies.length===0&&<p className="visibility-warning"><b>当前没有可见英舰。</b>英舰仍在对局中，只是全部超出德方 {view.visibility} 格能见度；本阶段不能指定其为目标。</p>}
  <ol className="lesson-track">{lessons.map((item,itemIndex)=><li className={itemIndex<index?"done":itemIndex===index?"current":""} key={item.title}>{item.title}</li>)}</ol>
 </section>;
}
