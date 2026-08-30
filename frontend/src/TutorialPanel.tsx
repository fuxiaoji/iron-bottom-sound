import type {Observation,Phase} from "./types";

type Lesson={title:string;why:string;actions:string[];check:string;next:string;rule:string;region:"左侧舰队"|"中央地图"|"右侧计划表"|"顶部按钮"|"战报弹窗"};

const classic:Record<string,Lesson>={
 reinforcement:{title:"认识舰桥：先确认阶段",why:"每回合按固定阶段推进，秘密命令封存后不能反悔。",actions:["看顶部的回合与阶段名称。","右侧计划表已由半自动教练填入合法确认。","点击顶部“检查本课并继续”。"],check:"计划表显示本方阵营，确认项为已就绪。",next:"进入图形化移动计划。",rule:"IBS-R-05 · 规则书 p.6",region:"顶部按钮"},
 movement_planning:{title:"亲手画一条航路",why:"舰船必须先直航再转向；本回合速度由速度循环与既有损伤共同限制。",actions:["在左侧点选卡尔加尔斯特。","在右侧移动行点“地图逐格规划”。","中央地图依次点亮可达格；确认后可继续修改半自动示范。"],check:"中央地图出现虚线预计航迹，终点与舰首朝向符合你的计划。",next:"把已封存航路交给鱼雷发射计划。",rule:"IBS-R-06 · 规则书 p.7–8",region:"右侧计划表"},
 torpedo_planning:{title:"在船还没移动前计划鱼雷",why:"鱼雷直线航行，必须预先指定发射 MF、发射格、舷侧、角度和速度档。",actions:["查看中央地图保留的封存移动轨迹。","在逐舰鱼雷名册选发射器，或保持空计划安全通过。","用鱼雷预测航迹确认不会穿过友舰。"],check:"每个发射器最多一张订单；发射格必须来自本舰封存航路。",next:"双方按 MF 脉冲同步移动。",rule:"IBS-R-08.2 · 规则书 p.10–11",region:"右侧计划表"},
 movement_resolution:{title:"观察同步移动",why:"双方航路已经封存，结算中途不能改令。",actions:["点击顶部“执行引擎裁决”。","观察舰船逐脉冲到达虚线终点。","若世界平移发生，以日志中的原计划终点与修正后终点核对。"],check:"舰船实际终点与封存计划/裁决日志一致。",next:"进入逐舰炮击。",rule:"IBS-R-06 / IBS-R-06.1.8",region:"顶部按钮"},
 gunnery:{title:"逐舰安排齐射",why:"每艘舰、每个炮位都独立检查目标、距离与射界，不能让不可转向炮位混入齐射。",actions:["在右侧逐舰名册点“为该舰安排齐射”。","选择目标后，引擎会自动只勾选能转向的炮位。","用中央射界热力图检查火力覆盖，再提交。"],check:"三艘德舰各自有订单，或界面明确说明当前无可见目标。",next:"结算命中、损伤、鱼雷与火灾。",rule:"IBS-R-08.1 · 规则书 p.8–10",region:"右侧计划表"},
 ending:{title:"读懂一份战报",why:"裁决不是一句“命中”：每次掷骰、修正、穿甲、损伤和来源都能追溯。",actions:["依次执行鱼雷效果与起火/回合结束。","打开自动弹出的战报，先看交战摘要，再看逐舰战果。","关闭战报后进入下一回合，重复一次完整循环。"],check:"你能从战报指出攻击舰、目标舰、骰子、规则号与最终状态。",next:"完成经典入门；可以进入二马大舰队教学。",rule:"IBS-R-08.1 / IBS-R-08.2 / IBS-R-05",region:"战报弹窗"},
};

const grand:Lesson[]=[
 {title:"1. 把 24 艘军舰编成六条战列线",why:"真实模式不是逐艘拖动：领舰决定共享航迹，旗舰维持指挥，备用旗舰负责继承。",actions:["左侧展开战列舰、巡洋舰和驱逐舰三支预置纵队。","在右侧确认每队领舰、旗舰、备用旗舰与 1 格间距。","先不要追求完美；教练建议已经覆盖全部本方舰船。"],check:"本方每艘舰恰好属于一支编队，旗舰与备用旗舰不是同一艘。",next:"双方编成后，直接进入二马首轮炮击。",rule:"IBS-R-RC-01 · 真实模式扩展",region:"右侧计划表"},
 {title:"2. 让主力舰巨炮开火",why:"二马从炮击阶段开局。大和级与美军战列舰在远距离交换齐射，命中、穿甲、炮位损伤全部走正式表。",actions:["中央地图切换“本舰火力”，点选大和查看射界。","右侧逐舰名册点“大和安排齐射”，再检查武藏与信浓。","半自动教练只预选合法炮位；你可以更换目标后重新筛选。"],check:"至少一艘主力舰已有齐射；没有可见目标时查看能见度与距离解释。",next:"提交后读第一轮巨炮战报。",rule:"IBS-R-08.1 + IBS-S-EM-01-R2/R3",region:"右侧计划表"},
 {title:"3. 从齐射结果读战局",why:"巨炮交换之后，教学剧本会插入一条明确标注的轮机战情，用来保证你能练到共同航速机制。",actions:["执行鱼雷效果和起火结算。","在战报逐舰查看命中、穿甲、炮位与舰体变化。","留意“IBS-TUT-EM-05”教学战情：它不是原版随机骰结果。"],check:"日志出现石狩下回合最高航速降至 3 MF。",next:"下一移动阶段必须处理战列线速度危机。",rule:"IBS-TUT-EM-05 · 教学脚本",region:"战报弹窗"},
 {title:"4. 进入第二回合舰桥",why:"增援确认把上一轮结果带入新回合；先看舰船记录表，再决定整队如何行动。",actions:["在左侧点石狩，查看速度轨的受损格。","对比所属战列线当前 5 MF 与石狩最高 3 MF。","确认无增援后继续。"],check:"你能说出冲突：领舰计划 5 MF，但一艘成员最多只能 3 MF。",next:"在编队计划表作真正的指挥决策。",rule:"IBS-R-05 + IBS-R-RC-04",region:"左侧舰队"},
 {title:"5. 共同航速危机：降速还是脱队",why:"编队不能把受损舰拖着超速航行。你必须保全队形，或牺牲队列完整性。",actions:["找到包含石狩的战列线。","选择“全队降速”，把领舰航路压到全员合法速度；或选择“受损舰脱队”并勾选石狩。","观察中央地图的整队预计轨迹，再提交。"],check:"计划不再显示速度冲突；若脱队，石狩将进入永久撤退控制。",next:"同步移动会展开领舰航路和后舰尾随。",rule:"IBS-R-RC-02 / IBS-R-RC-04",region:"右侧计划表"},
 {title:"6. 看战列线沿领舰航迹展开",why:"后舰不是瞬移到队形：它们沿领舰留下的共享航迹逐脉冲尾随，间距保持 1 或 2 格。",actions:["先看中央地图的整队虚线预览。","执行同步移动。","检查后舰是否依次占据领舰旧航迹；受损脱队舰则向安全边缘转进。"],check:"没有友舰重叠；编队成员顺序与共享航迹一致。",next:"为新的阵位安排第二轮齐射与鱼雷。",rule:"IBS-R-RC-02 / IBS-R-RC-03 / IBS-R-RC-06",region:"中央地图"},
 {title:"7. 脱离不是消失：掩护受损舰撤退",why:"脱队舰永久离开编队，由撤退控制器选择安全地图边缘；仍可按规则自卫，直到真正退出地图。",actions:["左侧查看石狩状态：脱队、撤退中或已撤出。","中央地图跟踪其撤退航线与舰首。","用主力编队火力压制追兵，保护它离场。"],check:"石狩状态变化有事件来源，退出地图后不再生成普通编队订单。",next:"继续数轮，体验旗舰继承、鱼雷幕和最终评分。",rule:"IBS-R-RC-04 / IBS-R-RC-06",region:"中央地图"},
 {title:"8. 以舰队司令的方式复盘",why:"胜负不只看沉船：二马按舰体、主炮、雷达、火控与航速损失累计战损分。",actions:["打开战报的交战与逐舰页签。","比较双方战损分，找出最有效的一次齐射。","继续到第 12 回合，或在掌握机制后返回大厅开始正式局。"],check:"你能解释当前比分、受损舰去向和下一回合舰队目标。",next:"大舰队指挥学院毕业。",rule:"IBS-S-EM-01-R4/R5",region:"战报弹窗"},
];

function classicLesson(phase:Phase){return classic[phase]??(phase==="torpedo_effects"||phase==="fire_end"||phase==="complete"?classic.ending:classic.reinforcement)}
function grandIndex(view:Observation){if(view.phase==="formation_setup")return 0;if(view.turn===1&&view.phase==="gunnery")return 1;if(view.turn===1)return 2;if(view.turn>=2&&view.phase==="reinforcement")return 3;if(view.turn>=2&&view.phase==="movement_planning")return 4;if(view.turn>=2&&view.phase==="movement_resolution")return 5;if(view.turn>=2&&view.ships.some(ship=>ship.command_status&&ship.command_status!=="attached"))return 6;return view.turn>=3?7:Math.min(6,view.phase==="gunnery"?6:5)}

export function TutorialPanel({view}:{view:Observation}){
 const isGrand=view.scenario_id==="IBS-S-EM-01";
 const index=isGrand?grandIndex(view):["reinforcement","movement_planning","torpedo_planning","movement_resolution","gunnery","ending"].indexOf(view.phase==="torpedo_effects"||view.phase==="fire_end"||view.phase==="complete"?"ending":view.phase);
 const lesson=isGrand?grand[index]:classicLesson(view.phase);
 const total=isGrand?grand.length:6;
 const visibleEnemies=view.ships.filter(ship=>ship.side!==view.side&&!ship.sunk);
 return <section className={`tutorial-card detailed ${isGrand?"grand-fleet":"classic"}`}>
  <div className="tutorial-head"><div><div className="tutorial-kicker">{isGrand?"大舰队指挥学院":"夜战军官速成班"} · 第 {index+1}/{total} 课</div><h2>{lesson.title}</h2></div><span className="tutorial-region">现在看：{lesson.region}</span></div>
  <div className="coach-why"><b>为什么要学</b><p>{lesson.why}</p></div>
  <div className="coach-actions"><b>现在照着做</b><ol>{lesson.actions.map((action,i)=><li key={action}><span>{i+1}</span>{action}</li>)}</ol></div>
  <div className="coach-check"><b>完成检查</b><p>✓ {lesson.check}</p></div>
  <div className="coach-next"><span>接下来</span>{lesson.next}</div><code>{lesson.rule}</code>
  {view.phase==="gunnery"&&visibleEnemies.length===0&&<p className="visibility-warning"><b>当前没有可见敌舰。</b>敌舰仍在对局中，只是超出本方 {view.visibility} 格观察距离；本阶段不要凭空建立目标。</p>}
  <ol className="lesson-track">{Array.from({length:total},(_,itemIndex)=><li className={itemIndex<index?"done":itemIndex===index?"current":""} key={itemIndex}><span>{itemIndex<index?"✓":itemIndex+1}</span></li>)}</ol>
 </section>;
}
