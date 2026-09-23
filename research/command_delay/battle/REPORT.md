# 命令延迟模式 · LLM 对 LLM 完整战报

- **想定**：IBS-S-01（seed 20270830）
- **双方策略**：zcode-subagent / zcode-subagent —— 双方每个编队各由一个独立子代理指挥（带记忆），舰队总指挥用自然语言下达命令，命令作为电报经通信链路投递
- **结果**：7 回合，胜方 无（平局：胜利点差小于4）；比分 5–5；友军碰撞 0 次
- **信息边界**：每个代理只能看到自己一侧的过滤视图；本报告为**战后中性文书**，因此正文地图为双方视角，但第 [信息泄露扫描](#信息泄露扫描) 节单独验证了代理收到的材料

## 逐回合态势与指挥

## 通信台账（全部报文）

| 报文 | 类型 | 媒介 | 优先级 | 发出 | 送达 | 状态 | 说明 |
|---|---|---|---|---|---|---|---|
| `MSG-00001` | contact_report | TBS 短距战术 | urgent | T1 | T1 | 已送达 | within tactical range with line of sight |
| `MSG-00002` | contact_report | TBS 短距战术 | urgent | T1 | T1 | 已送达 | within tactical range with line of sight |
| `MSG-00003` | contact_report | TBS 短距战术 | urgent | T1 | T1 | 已送达 | within tactical range with line of sight |
| `MSG-00004` | contact_report | TBS 短距战术 | urgent | T1 | T1 | 已送达 | within tactical range with line of sight |
| `MSG-00005` | contact_report | TBS 短距战术 | urgent | T1 | T2 | 已送达 | within tactical range with line of sight |
| `MSG-00006` | contact_report | TBS 短距战术 | urgent | T1 | T2 | 已送达 | within tactical range with line of sight |
| `MSG-00007` | contact_report | TBS 短距战术 | urgent | T2 | T2 | 已送达 | within tactical range with line of sight |
| `MSG-00008` | contact_report | TBS 短距战术 | urgent | T2 | T2 | 已送达 | within tactical range with line of sight |
| `MSG-00009` | mission_order | TBS 短距战术 | operational | T2 | T3 | 已送达 | within tactical range with line of sight |
| `MSG-00010` | mission_order | TBS 短距战术 | operational | T2 | T3 | 已送达 | within tactical range with line of sight |
| `MSG-00011` | contact_report | TBS 短距战术 | urgent | T2 | T2 | 已送达 | within tactical range with line of sight |
| `MSG-00012` | contact_report | TBS 短距战术 | urgent | T2 | T2 | 已送达 | within tactical range with line of sight |
| `MSG-00013` | contact_report | TBS 短距战术 | urgent | T2 | T2 | 已送达 | within tactical range with line of sight |
| `MSG-00014` | contact_report | TBS 短距战术 | urgent | T2 | T2 | 已送达 | within tactical range with line of sight |
| `MSG-00015` | contact_report | TBS 短距战术 | urgent | T2 | T2 | 已送达 | within tactical range with line of sight |
| `MSG-00016` | contact_report | TBS 短距战术 | urgent | T2 | T2 | 已送达 | within tactical range with line of sight |
| `MSG-00017` | contact_report | TBS 短距战术 | urgent | T2 | T2 | 已送达 | within tactical range with line of sight |
| `MSG-00018` | contact_report | TBS 短距战术 | urgent | T2 | T2 | 已送达 | within tactical range with line of sight |
| `MSG-00019` | contact_report | TBS 短距战术 | urgent | T2 | T2 | 已送达 | within tactical range with line of sight |
| `MSG-00020` | contact_report | TBS 短距战术 | urgent | T2 | T2 | 已送达 | within tactical range with line of sight |
| `MSG-00021` | contact_report | TBS 短距战术 | urgent | T2 | T3 | 已送达 | within tactical range with line of sight |
| `MSG-00022` | contact_report | TBS 短距战术 | urgent | T2 | T3 | 已送达 | within tactical range with line of sight |
| `MSG-00023` | contact_report | TBS 短距战术 | urgent | T3 | T3 | 已送达 | within tactical range with line of sight |
| `MSG-00024` | contact_report | TBS 短距战术 | urgent | T3 | T3 | 已送达 | within tactical range with line of sight |
| `MSG-00025` | contact_report | TBS 短距战术 | urgent | T3 | T3 | 已送达 | within tactical range with line of sight |
| `MSG-00026` | contact_report | TBS 短距战术 | urgent | T3 | T3 | 已送达 | within tactical range with line of sight |
| `MSG-00027` | mission_order | TBS 短距战术 | operational | T3 | T4 | 已送达 | within tactical range with line of sight |
| `MSG-00028` | mission_order | TBS 短距战术 | operational | T3 | T4 | 已送达 | within tactical range with line of sight |
| `MSG-00029` | contact_report | TBS 短距战术 | urgent | T3 | T3 | 已送达 | within tactical range with line of sight |
| `MSG-00030` | contact_report | TBS 短距战术 | urgent | T3 | T3 | 已送达 | within tactical range with line of sight |
| `MSG-00031` | contact_report | TBS 短距战术 | urgent | T3 | T3 | 已送达 | within tactical range with line of sight |
| `MSG-00032` | contact_report | TBS 短距战术 | urgent | T3 | T3 | 已送达 | within tactical range with line of sight |
| `MSG-00033` | contact_report | 转报/再加密 | urgent | T3 | T5 | 已送达 | coded set but the ends are under different ciphers |
| `MSG-00034` | contact_report | TBS 短距战术 | urgent | T3 | T3 | 已送达 | within tactical range with line of sight |
| `MSG-00035` | contact_report | 转报/再加密 | urgent | T3 | T5 | 已送达 | coded set but the ends are under different ciphers |
| `MSG-00036` | contact_report | TBS 短距战术 | urgent | T3 | T3 | 已送达 | within tactical range with line of sight |
| `MSG-00037` | contact_report | 转报/再加密 | urgent | T3 | T5 | 已送达 | coded set but the ends are under different ciphers |
| `MSG-00038` | contact_report | TBS 短距战术 | urgent | T3 | T4 | 已送达 | within tactical range with line of sight |
| `MSG-00039` | contact_report | 转报/再加密 | urgent | T4 | T6 | 已送达 | coded set but the ends are under different ciphers |
| `MSG-00040` | contact_report | TBS 短距战术 | urgent | T4 | T4 | 已送达 | within tactical range with line of sight |
| `MSG-00041` | contact_report | 转报/再加密 | urgent | T4 | T6 | 已送达 | coded set but the ends are under different ciphers |
| `MSG-00042` | contact_report | TBS 短距战术 | urgent | T4 | T4 | 已送达 | within tactical range with line of sight |
| `MSG-00043` | contact_report | 转报/再加密 | urgent | T4 | T6 | 已送达 | coded set but the ends are under different ciphers |
| `MSG-00044` | contact_report | TBS 短距战术 | urgent | T4 | T4 | 已送达 | within tactical range with line of sight |
| `MSG-00045` | contact_report | 转报/再加密 | urgent | T4 | T6 | 已送达 | coded set but the ends are under different ciphers |
| `MSG-00046` | contact_report | TBS 短距战术 | urgent | T4 | T4 | 已送达 | within tactical range with line of sight |
| `MSG-00047` | contact_report | 转报/再加密 | urgent | T4 | T6 | 已送达 | coded set but the ends are under different ciphers |
| `MSG-00048` | contact_report | TBS 短距战术 | urgent | T4 | T4 | 已送达 | within tactical range with line of sight |
| `MSG-00049` | contact_report | 转报/再加密 | urgent | T4 | T6 | 已送达 | coded set but the ends are under different ciphers |
| `MSG-00050` | contact_report | TBS 短距战术 | urgent | T4 | T4 | 已送达 | within tactical range with line of sight |
| `MSG-00051` | contact_report | 转报/再加密 | urgent | T4 | T6 | 已送达 | coded set but the ends are under different ciphers |
| `MSG-00052` | contact_report | TBS 短距战术 | urgent | T4 | T5 | 已送达 | within tactical range with line of sight |
| `MSG-00053` | contact_report | 转报/再加密 | urgent | T5 | T7 | 已送达 | coded set but the ends are under different ciphers |
| `MSG-00054` | contact_report | TBS 短距战术 | urgent | T5 | T5 | 已送达 | within tactical range with line of sight |
| `MSG-00055` | contact_report | 转报/再加密 | urgent | T5 | T7 | 已送达 | coded set but the ends are under different ciphers |
| `MSG-00056` | contact_report | TBS 短距战术 | urgent | T5 | T5 | 已送达 | within tactical range with line of sight |
| `MSG-00057` | contact_report | 转报/再加密 | urgent | T5 | T7 | 已送达 | coded set but the ends are under different ciphers |
| `MSG-00058` | contact_report | TBS 短距战术 | urgent | T5 | T5 | 已送达 | within tactical range with line of sight |
| `MSG-00059` | contact_report | 转报/再加密 | urgent | T5 | T7 | 已送达 | coded set but the ends are under different ciphers |
| `MSG-00060` | contact_report | TBS 短距战术 | urgent | T5 | T5 | 已送达 | within tactical range with line of sight |
| `MSG-00061` | contact_report | 转报/再加密 | urgent | T5 | T7 | 已送达 | coded set but the ends are under different ciphers |
| `MSG-00062` | contact_report | 转报/再加密 | urgent | T5 | T7 | 已送达 | coded set but the ends are under different ciphers |
| `MSG-00063` | sitrep | 转报/再加密 | routine | T5 | T7 | 被取代 | overtaken by a newer report already held from turn 7 |
| `MSG-00064` | sitrep | 转报/再加密 | routine | T5 | T7 | 被取代 | overtaken by a newer report already held from turn 7 |
| `MSG-00065` | sitrep | 转报/再加密 | routine | T6 | — | 排队中 | coded set but the ends are under different ciphers |
| `MSG-00066` | sitrep | 转报/再加密 | routine | T6 | — | 排队中 | coded set but the ends are under different ciphers |
| `MSG-00067` | sitrep | 转报/再加密 | routine | T6 | — | 排队中 | coded set but the ends are under different ciphers |
| `MSG-00068` | sitrep | 转报/再加密 | routine | T6 | — | 排队中 | coded set but the ends are under different ciphers |
| `MSG-00069` | sitrep | 转报/再加密 | routine | T6 | — | 排队中 | coded set but the ends are under different ciphers |
| `MSG-00070` | sitrep | 转报/再加密 | routine | T6 | — | 排队中 | coded set but the ends are under different ciphers |
| `MSG-00071` | sitrep | 转报/再加密 | routine | T6 | — | 排队中 | coded set but the ends are under different ciphers |
| `MSG-00072` | sitrep | 转报/再加密 | routine | T7 | — | 排队中 | coded set but the ends are under different ciphers |
| `MSG-00073` | sitrep | 转报/再加密 | routine | T7 | — | 排队中 | coded set but the ends are under different ciphers |
| `MSG-00074` | sitrep | 转报/再加密 | routine | T7 | — | 排队中 | coded set but the ends are under different ciphers |
| `MSG-00075` | sitrep | 转报/再加密 | routine | T7 | — | 排队中 | coded set but the ends are under different ciphers |
| `MSG-00076` | sitrep | TBS 短距战术 | routine | T7 | T7 | 已送达 | within tactical range with line of sight |
| `MSG-00077` | sitrep | TBS 短距战术 | routine | T7 | T7 | 已送达 | within tactical range with line of sight |
| `MSG-00078` | sitrep | TBS 短距战术 | routine | T7 | T7 | 已送达 | within tactical range with line of sight |
| `MSG-00079` | sitrep | TBS 短距战术 | routine | T7 | — | 排队中 | within tactical range with line of sight |

共 79 条：送达 65（其中跨回合延迟 26），丢弃/被取代 2，其余在队列中。

## 远方命令与当前战局的平衡（逐次决策）

| 回合 | 编队 | 手持命令 | 本地接触 | 激活分支 | 采取的方案 | 依据（代理自述） |
|---|---|---|---|---|---|---|
| T2 | axis-active-heavy | 无（预令） | 156 | 无 | `1P1P1P1S1S` | 无上级命令而敌9舰（2CA2CL5DD）自东以纵队逼近、先头下回合即横越我航路，我仅3巡洋舰且旗舰受损炮击再停1回合，直行必遭T字夹击，故转北脱离夹角拉开距离并发出接触报告，火力优 |
| T2 | axis-active-light | 无（预令） | 283 | 无 | `1S1S1` | 无现行命令且2艘驱逐舰对9舰纵队正面交战明显不利，故选MOVE:1S1S1南撤至敌航路南侧P16保持5-7格侧翼接触，待其纵队展开过半后回转实施雷击，同时南移让开我重队（青叶编队P |
| T2 | allies-active-heavy | 无（预令） | 177 | 无 | `2S2` | 无有效上级命令且敌五舰分两纵队东行快速逼近并占速度优势，故右转(2S2)迎向敌重巡纵队保持舷侧火力并避开驱逐舰纵队航线，火力优先领队重巡青叶、降权远距衣笠与低价值驱逐舰。 |
| T2 | allies-active-light | 无（预令） | 283 | 无 | `1S2S2` | 无在航命令，敌重巡纵队正高速北进，我率五驱斜插其航线东侧占S10雷击阵位（距青叶、吹雪各约3格），炮火优先其驱逐舰屏卫，同时上报接触以引导后方主力。 |
| T3 | axis-active-heavy | 无（预令） | 156 | 无 | `5` | 无新命令，敌9舰自东南钳形压来且先头驱逐舰已距1-3格，遂全速北进V5拉距拒近战待机，火力优先压制最近最速的法伦霍尔特与拉菲。 |
| T3 | axis-active-light | 无（预令） | 177 | 本地条件分支 | `3P1S` | 命令的第2回合拦截期限已过且本编队仅剩吹雪一舰、当面为含2CA2CL的9舰优势兵力，故按local_condition_branch由拦截改为影子跟随并报告，向西西南(M19)拉开 |
| T3 | allies-active-heavy | 无（预令） | 177 | 本地条件分支 | `4` | 敌巡洋舰群三舰处于左转西撤的不同相位（青叶NE、古鹰N、衣笠W），威胁方向已反转，故按命令意图不再追击拦截，保持西向航向5维持与主力相对位置并以舷侧对敌打通过炮战，集火最近的衣笠、 |
| T3 | allies-active-light | 无（预令） | 95 | 无 | `1` | 无在航命令，依前回合雷击意图临机处置：敌重巡纵队正横越我舰首转向北，率队直进S9保持其东翼约2格距离抢占雷击阵位；因吹雪远在6格外，炮火优先权由其屏卫驱逐舰临机改为最近的衣笠。 |
| T4 | axis-active-heavy | 无（预令） | 156 | 无 | `5` | 无新命令且敌主力距9速4、追击DD降速1无法逼近，遂选MOVE:5全速直线北移AA3继续拉距拒近战待机，青叶炮已复仍不宜以3舰（旗舰6/11受损）夜战敌2CA2CL主力，火力集中最 |
| T4 | axis-active-light | 无（预令） | 283 | 本地条件分支 | `1SS2` | 命令基于我仍在P16、盐湖城将临T15的过时几何，实际我在M19且敌主力（2CA+2CL）已转向正西以同速4拉开，同速追击无法进入雷击程，当面9舰对我仅存旗舰吹雪（60%）成优势， |
| T4 | allies-active-heavy | 无（预令） | 283 | 本地条件分支 | `3P1` | 命令所据敌情已过期——敌CA三舰已转东北向以速5脱离（现距9—11且渐开），追击只能是违反勿恋战与防鱼雷约束的尾追战，故按命令意图保持西向再移并微偏南维持对吹雪的舷侧，集火最近之衣 |
| T4 | allies-active-light | 无（预令） | 42 | 无 | `1S2` | 无在航命令；敌重巡纵队以速5沿东北向脱离，我以最大合法机动占其航线东侧U7平随保持约5格接触并全时维持≥2格安全距（旗舰伤重），火力优先最近且为纵队尾舰的衣笠，放弃远距掉队的吹雪。 |
| T5 | axis-active-heavy | 无（预令） | 105 | 无 | `4S1` | 无新命令且敌主力2CA2CL建制完整距14-15并未混乱、残存4DD速仅1-2无法逼近，按既定计划执行最大纵向机动MOVE:4S1至FF1向北续拉距拒近战，火力优先最近残敌驱逐舰、 |
| T5 | axis-active-light | 无（预令） | 283 | 本地条件分支 | `1S1S4` | 命令所据P16/T15拦截几何已失效（我实际在I21、敌主力转向西逃且T3-T5距离3→7→11每回合拉开3-4格），故按local_condition_branch对优势敌兵力继 |
| T5 | allies-active-heavy | 无（预令） | 177 | 本地条件分支 | `1SS1S1` | 命令所据敌情已失效——敌巡洋群向东以速5脱离（衣笠距14仍在拉开）、吹雪距11不在射程且向SW退，故按'勿恋战、得手靠拢'之意图选优势敌军避免决战的地方条件分支，以1SS1S1经北 |
| T5 | allies-active-light | 无（预令） | 42 | 无 | `1S2` | 无在航命令，依既定意图临机处置：敌重巡纵队以速5沿东北继续脱离，我以最大合法机动1S2进至U6沿其尾流平随（距尾舰衣笠4格、保持≥2格安全距）以尽可能延长接触，火力优先最近且居纵队 |
| T6 | axis-active-heavy | 无（预令） | 115 | 无 | `3P2` | 无新命令且敌主力2CA2CL已失联、仅4艘速3驱逐舰在9-12格尾追,按既定拒战方针选MOVE:3P2折向东北边缘续拉最大距离并保留下回合转向余裕,火力优先压制最近之法伦霍尔特、对 |
| T6 | allies-active-heavy | 无（预令） | 177 | 本地条件分支 | `1S1S2` | 命令所据敌情已失效——敌巡洋群以速5东遁且本回合无任何接触，故按‘勿恋战、得手与我靠拢’之意图维持避免决战分支，以1S1S2经北侧倒转至东北向（G6、终向1），开始东进与主力会合。 |
| T6 | allies-active-light | 无（预令） | 95 | 无 | `4` | 无在航命令，依既定意图临机处置：敌3CA以速5沿北北东继续脱离且航速优于我，我以最大合法机动MOVE:4沿其航向纯追击进至Y4以尽最大可能延长接触（预计下回合距尾舰衣笠约10格、全 |
| T7 | axis-active-heavy | 无（预令） | 72 | 无 | `2S2P1` | 无新命令且敌3驱逐舰于11-13格尾追、主力2CA2CL仍失联，遵既定拒战方针以cost5机动折至东北角PP1取得对三敌最大距离并保留下回合沿边北上或西转的余裕，火力优先最近的布坎 |
| T7 | allies-active-heavy | 无（预令） | 280 | 本地条件分支 | `6` | 命令所据敌情（敌巡洋群在Q8—R9、吹雪在侧）已失效且本回合无任何接触，敌纵T5起以速5东遁拉开，故按命令'勿恋战、得手与我靠拢'之意图，以MOVE:6满速沿北侧向东北续进（G6→ |
| T7 | allies-active-light | 无（预令） | 245 | 无 | `6` | 无在航命令，依既定意图临机处置：敌3CA以速5沿东北直线继续脱离且航速占优，我以最大合法机动MOVE:6直线全速追击进至DD1凭净速差逐步拉近接触，火力优先最近且居纵队之尾的衣笠、 |

## 各编队最终记忆

### `allies-active-heavy`

- 当前生效命令（T4收到）：第1编队：我编队现势目力接触——敌重巡3艘（青叶、古鹰、衣笠）集于Q8—R9，在你西侧约5格；敌驱吹雪在P16，距你约2格。你即向西接敌，袭敌巡洋群东翼；吹雪若先入射程先歼之。火力优先CA、次DD，严防夜战鱼雷。我自V12北进夹击，勿恋战，得手与我靠拢。
- 记忆条目：order_received 2, report_sent 6, contact_seen 15, decision 6, contingency 5, note 6
- 自己写的备忘：
  - 「敌两纵东行(航向2速5)：重巡纵r2带、驱纵r6带，速差2不可脱离。本回合2S2右转以舷侧对敌重巡、避开驱纵对穿；火力集火青叶。下回合视距离保持W航向打通过战。」
  - 「已确认order-2；敌CA纵左转西撤，速5难追；保持W舷侧炮战集火衣笠，防吹雪鱼雷，兼顾与主力相对位置。」
  - 「敌CA三舰NE向速5脱离难追未追；吹雪SW向退。我据J11保持西向，炮集衣笠防鱼雷；下回合视令北转靠拢主力。」
  - 「令已过时：敌CA群东逃速5勿追；吹雪11格SW退不在射程。本回合1SS1S1东转，明起东进靠拢F纵，经其北侧避火扇，勿追DD防鱼雷。」
  - 「敌CA群东遁速5(T5距14)勿追。已1S1S2转NE至G6，循北翼东进靠拢F纵避火扇；下回合续NE，遇CA集火防雷。」
  - 「已至M3续NE；无接触则续NE/E找主力（其V12北进情报已旧6回合）；遇CA集火防夜雷，遇友纵靠拢避其火扇。」

### `allies-active-light`

- 当前生效命令（TNone收到）：（无）
- 记忆条目：order_received 0, report_sent 6, contact_seen 22, decision 6, contingency 0, note 6
- 自己写的备忘：
  - 「敌3重巡2驱速5向北，我已插至其航线东侧S10。次回合抵近雷击青叶/吹雪，勿近于2格，保持主力3格内，继续接触报告。」
  - 「敌重巡纵队正于我西舷转向北，衣笠距1掠过。下回合占其前方雷击阵位，保持≥2格；吹雪6格外掉队，我方重巡编队R14向西接近中。」
  - 「敌3CA速5东北撤，我1S2占其东翼U7平随；敌若右转南下即抢其前方雷位。旗舰伤2勿近敌2格内。重巡队西进尾流中。」
  - 「敌3CA速5续向东北(纵队青叶-古鹰-衣笠)，我1S2至U6距尾舰衣笠4格平随；敌若右转南下即抢前方雷位；旗舰伤2保持≥2格；续发接触报告。」
  - 「敌3CA速5向北北东脱离，我MOVE:4追至Y4距约10，速差1渐脱；保持接触续报，敌右转即抢前雷位；旗舰伤2勿近2格。」
  - 「敌3CA速5沿东北直线脱离，我MOVE:6直线全速追至DD1，距尾舰衣笠望缩至约10；敌右转即抢其前方雷位；旗舰有伤勿近敌2格内；续发接触报告。」

### `axis-active-heavy`

- 当前生效命令（TNone收到）：（无）
- 记忆条目：order_received 0, report_sent 6, contact_seen 24, decision 6, contingency 0, note 6
- 自己写的备忘：
  - 「敌9舰纵队东来欲夹叉我列，已北转拒T字脱离；下回合续向北/西拉距，青叶炮下回合恢复，看轻队动向再定反击。」
  - 「已北撤V5拉开至约6格；敌先头3DD紧追，下回合续北/西北拉距，青叶炮已复；观吹雪(P16)袭敌后动向再定反击。」
  - 「已续北拉距，敌4DD仅速1疑重创，主力2CA2CL距9难追。下回合看吹雪动向，敌乱即转反击，否则续北拒战。」
  - 「已至FF1近东北边，下回合直北若触边须转弯续走；主距14-15未乱，4DD速1-2残，观吹雪新报再定反击，否则续拒战拉距。」
  - 「已折向KK2(36,-17)近东北角,拉距至约18格;敌4DD速3尾追,主力2CA2CL失联。下回合若触边沿边转向续走,敌乱或主力再现再定反击。」
  - 「已抵PP1东北角,下回合沿边续走(h6北/h5西)拉距;敌3DD距11-13尾追,主力仍失联;见主力再现或敌乱再议反击。」

### `axis-active-light`

- 当前生效命令（T4收到）：第2编队：敌主力（2CA+2CL）列于R14-U15一线，前卫5DD在S10-U13。你于P16距其主力约3格，占位极佳：抵近雷击T15盐湖城，得手后撤往P18拉开距离，勿与敌DD纠缠。我第1编队自P10方向压其前卫策应。火力优先CA、CL。
- 记忆条目：order_received 2, report_sent 4, contact_seen 24, decision 4, contingency 3, note 4
- 自己写的备忘：
  - 「敌9舰航向西南迫近，2驱对9舰不利；南撤至P16占其纵队南侧，待其过半回转雷击，勿与巡洋舰对射。」
  - 「敌巡洋纵队向西南扫过P-Q列，前卫SF/Boise曾距3格；我撤至M19西南侧影随，保持4格以上，待其前卫过我西侧后回转雷击，勿与CA对射。」
  - 「敌纵队正西速4西逃，雷击几何不成立；我L17沿其南侧6格影随，敌减速回转或与第1编队接战时即突入雷击盐湖城；避DD纠缠，确保旗舰存活。」
  - 「敌纵队西逃每回合拉开3-4格，同速难及雷击程；我经1S1S4至G17保其南侧10-12格影随并报其转向，待其减速回转或与第1编队接战即突袭盐湖城，避DD保旗舰。」

## 代理原始决策记录（抽样）

每条决策的完整提示词、原始回复与记忆快照在 `battle_data.json` 的 `agent_log`；这里抽取首末各一条以见格式：

**`axis-active-heavy` 第 2 回合（zcode-subagent）**

- 手持命令：（无）
- 第 1 次尝试：采纳
  - 原始回复：`{"acknowledgement": false, "memory_note": "敌9舰纵队东来欲夹叉我列，已北转拒T字脱离；下回合续向北/西拉距，青叶炮下回合恢复，看轻队动向再定反击。", "rationale_summary": "无上级命令而敌9舰（2CA2CL5DD）自东以纵队逼近、先头下回合即横越我航路，我仅3巡洋舰且旗舰受损炮击再停1回合，直行必遭T字夹击，故转北脱离夹角拉开距离并发出接触报告，火力优先指向最近最速的法伦`
- 决策：方案 `1P1P1P1S1S`，分支 无，备忘「敌9舰纵队东来欲夹叉我列，已北转拒T字脱离；下回合续向北/西拉距，青叶炮下回合恢复，看轻队动向再定反击。」

**`allies-active-light` 第 7 回合（zcode-subagent）**

- 手持命令：（无）
- 第 1 次尝试：采纳
  - 原始回复：`{"acknowledgement": false, "memory_note": "敌3CA速5沿东北直线脱离，我MOVE:6直线全速追至DD1，距尾舰衣笠望缩至约10；敌右转即抢其前方雷位；旗舰有伤勿近敌2格内；续发接触报告。", "rationale_summary": "无在航命令，依既定意图临机处置：敌3CA以速5沿东北直线继续脱离且航速占优，我以最大合法机动MOVE:6直线全速追击进至DD1凭净速差逐步拉近接触，火力优先最近`
- 决策：方案 `6`，分支 无，备忘「敌3CA速5沿东北直线脱离，我MOVE:6直线全速追至DD1，距尾舰衣笠望缩至约10；敌右转即抢其前方雷位；旗舰有伤勿近敌2格内；续发接触报告。」

## 附录：全量裁决事件日志

```
```

*由 `research/command_delay/generate_battle_md.py` 从 `battle/battle_data.json` 自动生成；引擎事件、报文台账、代理决策与记忆均为引擎记录原样，未手工修饰。*
