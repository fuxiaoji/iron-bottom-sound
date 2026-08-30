import type {Observation,Phase} from "./types";
import {GuidedTutorial} from "./GuidedTutorial";

export type TutorialVariant="classic"|"grand";

type Lesson={title:string;summary:string;rule:string};

const classic:Record<string,Lesson>={
 reinforcement:{title:"先认清阶段，再封存命令",summary:"顶部显示当前回合与阶段；秘密命令一旦封存便不能反悔。",rule:"IBS-R-05 · 规则书 p.6"},
 movement_planning:{title:"亲手规划一条合法航路",summary:"先直航再转向；航路消耗必须落在本舰本回合合法速度区间内。",rule:"IBS-R-06 · 规则书 p.7–8"},
 torpedo_planning:{title:"在移动前计划直线鱼雷",summary:"发射 MF、发射格、舷侧、角度与速度档都由引擎合法行动给出。",rule:"IBS-R-08.2 · 规则书 p.10–11"},
 movement_resolution:{title:"观察双方同步移动",summary:"双方航路已经封存，按 MF 脉冲同步执行，结算途中不能改令。",rule:"IBS-R-06 / IBS-R-06.1.8"},
 gunnery:{title:"让每艘可射舰安排齐射",summary:"目标、距离与炮位射界逐项检查，界面只会采用引擎判定合法的炮位。",rule:"IBS-R-08.1 · 规则书 p.8–10"},
 ending:{title:"从战报读懂损伤与胜负",summary:"命中、穿甲、舰体、炮位、火灾和来源都能从事件回溯。",rule:"IBS-R-08.1 / IBS-R-08.2 / IBS-R-05"},
};

const grand:Lesson[]=[
 {title:"检查六条战列线",summary:"领舰决定共享航迹，旗舰负责指挥，备用旗舰负责继承。",rule:"IBS-R-RC-01 · 真实模式扩展"},
 {title:"让主力舰巨炮开火",summary:"二马教学从远距离齐射开始，所有命中与损伤仍由正式裁决表处理。",rule:"IBS-R-08.1 + IBS-S-EM-01-R2/R3"},
 {title:"读第一轮巨炮战报",summary:"逐舰核对攻击来源、穿甲、舰体和炮位损伤；教学固定战情会单独标识。",rule:"IBS-TUT-EM-05 · 教学脚本"},
 {title:"进入第二回合舰桥",summary:"先检查受损舰速度轨，再决定整条战列线怎样行动。",rule:"IBS-R-05 + IBS-R-RC-04"},
 {title:"处理共同航速危机",summary:"选择全队降速，或让无法跟队的受损舰永久脱队撤离。",rule:"IBS-R-RC-02 / IBS-R-RC-04"},
 {title:"观察战列线尾随",summary:"后舰沿领舰留下的共享航迹逐 MF 前进，不会瞬移到队形。",rule:"IBS-R-RC-02 / IBS-R-RC-03 / IBS-R-RC-06"},
 {title:"用火力掩护脱离",summary:"脱队舰仍在地图上撤退，直到真正从安全边缘离场。",rule:"IBS-R-RC-04 / IBS-R-RC-06"},
 {title:"以舰队司令视角复盘",summary:"结合舰体、主炮、雷达、火控和航速损失解释当前战损分。",rule:"IBS-S-EM-01-R4/R5"},
];

function classicLesson(phase:Phase){return classic[phase]??(phase==="torpedo_effects"||phase==="fire_end"||phase==="complete"?classic.ending:classic.reinforcement)}
function grandIndex(view:Observation){if(view.phase==="formation_setup")return 0;if(view.turn===1&&view.phase==="gunnery")return 1;if(view.turn===1)return 2;if(view.turn>=2&&view.phase==="reinforcement")return 3;if(view.turn>=2&&view.phase==="movement_planning")return 4;if(view.turn>=2&&view.phase==="movement_resolution")return 5;if(view.turn>=2&&view.ships.some(ship=>ship.command_status&&ship.command_status!=="attached"))return 6;return view.turn>=3?7:Math.min(6,view.phase==="gunnery"?6:5)}

export function TutorialPanel({view,variant}:{view:Observation;variant?:TutorialVariant}){
 const resolved=variant??(view.scenario_id==="IBS-S-EM-01"?"grand":"classic");
 const index=resolved==="grand"?grandIndex(view):["reinforcement","movement_planning","torpedo_planning","movement_resolution","gunnery","ending"].indexOf(view.phase==="torpedo_effects"||view.phase==="fire_end"||view.phase==="complete"?"ending":view.phase);
 const lesson=resolved==="grand"?grand[index]:classicLesson(view.phase);
 const total=resolved==="grand"?grand.length:6;
 return <><section className={`tutorial-card interactive-summary ${resolved}`}>
  <div><span>{resolved==="grand"?"二马大舰队教练":"通道行动教练"} · 第 {Math.max(0,index)+1}/{total} 课</span><h2>{lesson.title}</h2></div>
  <p>{lesson.summary}</p>
  <small>下方强制教练一次只开放一个控件。</small>
  <code>{lesson.rule}</code>
 </section><GuidedTutorial sessionKey={view.scenario_id} view={view} variant={resolved}/></>;
}
