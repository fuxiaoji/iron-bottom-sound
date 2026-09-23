# 第二次马里亚纳海战（内南洋水雷强袭战）· 命令延迟模式 LLM 对 LLM 战报

- **想定**：IBS-S-EM-01（seed 19440619），12 回合后结束
- **指挥链**：舰队总指挥（独立 agent）→ 3 个分舰队指挥（各自 agent + 记忆）；总指挥随队编队当面受令、零延迟，其余编队经电报按媒介延迟
- **模型**：编队级 `deterministic-formation-v1`；舰队级 `no-fleet-agent`；思维链关闭，每次调用预算 2000 tokens
- **结果**：平局：损伤分差 6，未达到 25 分；比分 轴心 2 : 8 盟军；友军碰撞 0 次
- **调用记账**：0 次成功调用（另有 0 次传输失败被重试），提示 0 tokens / 生成 0 tokens，平均思维链 0 字
- **引擎拒绝并回退教条的次数**：10（明细见下）
- **配套影像**：`research/battle_video/`（同一份记录生成的三视图纪录片）

## 逐回合：真实态势与双方决策

### 第 1 回合

> 第一回合，双方仍在接近。海图上两支舰队隔着十几海里并行，没有接触，没有交火，只有航向和速度。

### 第 2 回合

> 第 2 回合，真实态势。这一回合没有新的命中，双方仍在调整阵位。

### 第 3 回合

> 第 3 回合，真实态势。这一回合没有新的命中，双方仍在调整阵位。

### 第 4 回合

> 第 4 回合，真实态势。这一回合没有新的命中，双方仍在调整阵位。

### 第 5 回合

> 第 5 回合，真实态势。这一回合没有新的命中，双方仍在调整阵位。

### 第 6 回合

> 第 6 回合，真实态势。这一回合没有新的命中，双方仍在调整阵位。

### 第 7 回合

> 第 7 回合，真实态势。这一回合没有新的命中，双方仍在调整阵位。

### 第 8 回合

> 第 8 回合，真实态势。炮击结果 14 条：岛风 命中结果 21有舰沉没：长波 沉没，等待下一回合漂移

### 第 9 回合

> 第 9 回合，真实态势。炮击结果 30 条：衣阿华 命中结果 35有舰沉没：卷波 沉没，等待下一回合漂移

### 第 10 回合

> 第 10 回合，真实态势。炮击结果 6 条：艾伦·M·萨姆纳 命中结果 56

### 第 11 回合

> 第 11 回合，真实态势。炮击结果 2 条：风云 命中结果 33有舰沉没：岛风 沉没，等待下一回合漂移

### 第 12 回合

> 第 12 回合，真实态势。这一回合没有新的命中，双方仍在调整阵位。

## 日方的指挥与上报

| 回合 | 总指挥命令（原文摘录） | 下达方式 | 媒介 | 延迟 |
|---|---|---|---|---|

**分舰队的上报**（agent 亲笔正文 + 引擎保底态势）

| 报文 | 上报编队 | 类型 | 发出 | 送达 | 延迟 | 正文摘录 |
|---|---|---|---|---|---|---|
| `MSG-00001` | axis-cruiser-line | 态势报告 | T1 | T1 | +0 |  |
| `MSG-00002` | axis-destroyer-line | 态势报告 | T1 | T1 | +0 |  |
| `MSG-00005` | axis-cruiser-line | 态势报告 | T1 | T1 | +0 |  |
| `MSG-00006` | axis-destroyer-line | 态势报告 | T1 | T1 | +0 |  |
| `MSG-00009` | axis-cruiser-line | 态势报告 | T1 | T2 | +0 |  |
| `MSG-00010` | axis-destroyer-line | 态势报告 | T1 | T2 | +0 |  |
| `MSG-00013` | axis-cruiser-line | 态势报告 | T2 | T2 | +0 |  |
| `MSG-00014` | axis-destroyer-line | 态势报告 | T2 | T2 | +0 |  |
| `MSG-00021` | axis-cruiser-line | 态势报告 | T2 | T2 | +0 |  |
| `MSG-00022` | axis-destroyer-line | 态势报告 | T2 | T2 | +0 |  |
| `MSG-00025` | axis-cruiser-line | 态势报告 | T2 | T2 | +0 |  |
| `MSG-00026` | axis-destroyer-line | 态势报告 | T2 | T2 | +0 |  |
| `MSG-00029` | axis-cruiser-line | 态势报告 | T2 | T2 | +0 |  |
| `MSG-00030` | axis-destroyer-line | 态势报告 | T2 | T2 | +0 |  |
| `MSG-00033` | axis-cruiser-line | 态势报告 | T2 | T2 | +0 |  |
| `MSG-00034` | axis-destroyer-line | 态势报告 | T2 | T2 | +0 |  |
| `MSG-00037` | axis-cruiser-line | 态势报告 | T2 | T2 | +0 |  |
| `MSG-00038` | axis-destroyer-line | 态势报告 | T2 | T2 | +0 |  |
| `MSG-00041` | axis-cruiser-line | 态势报告 | T2 | T3 | +0 |  |
| `MSG-00042` | axis-destroyer-line | 态势报告 | T2 | T3 | +0 |  |
| `MSG-00045` | axis-cruiser-line | 态势报告 | T3 | T3 | +0 |  |
| `MSG-00046` | axis-destroyer-line | 态势报告 | T3 | T3 | +0 |  |
| `MSG-00049` | axis-cruiser-line | 态势报告 | T3 | T3 | +0 |  |
| `MSG-00050` | axis-destroyer-line | 态势报告 | T3 | T3 | +0 |  |
| `MSG-00053` | axis-cruiser-line | 态势报告 | T3 | T3 | +0 |  |
| `MSG-00054` | axis-destroyer-line | 态势报告 | T3 | T3 | +0 |  |
| `MSG-00057` | axis-cruiser-line | 态势报告 | T3 | T3 | +0 |  |
| `MSG-00058` | axis-destroyer-line | 态势报告 | T3 | T3 | +0 |  |
| `MSG-00061` | axis-cruiser-line | 态势报告 | T3 | T3 | +0 |  |
| `MSG-00062` | axis-destroyer-line | 态势报告 | T3 | T3 | +0 |  |
| `MSG-00065` | axis-cruiser-line | 态势报告 | T3 | T4 | +0 |  |
| `MSG-00066` | axis-destroyer-line | 态势报告 | T3 | T4 | +0 |  |
| `MSG-00069` | axis-cruiser-line | 态势报告 | T3 | T4 | +0 |  |
| `MSG-00070` | axis-destroyer-line | 态势报告 | T3 | T4 | +0 |  |
| `MSG-00073` | axis-cruiser-line | 态势报告 | T4 | T4 | +0 |  |
| `MSG-00074` | axis-destroyer-line | 态势报告 | T4 | T4 | +0 |  |
| `MSG-00077` | axis-cruiser-line | 态势报告 | T4 | T4 | +0 |  |
| `MSG-00078` | axis-destroyer-line | 态势报告 | T4 | T4 | +0 |  |
| `MSG-00081` | axis-cruiser-line | 态势报告 | T4 | T4 | +0 |  |
| `MSG-00082` | axis-destroyer-line | 态势报告 | T4 | T4 | +0 |  |
| `MSG-00085` | axis-cruiser-line | 态势报告 | T4 | T4 | +0 |  |
| `MSG-00086` | axis-destroyer-line | 态势报告 | T4 | T4 | +0 |  |
| `MSG-00089` | axis-cruiser-line | 态势报告 | T4 | T4 | +0 |  |
| `MSG-00090` | axis-destroyer-line | 态势报告 | T4 | T4 | +0 |  |
| `MSG-00093` | axis-cruiser-line | 态势报告 | T4 | T5 | +0 |  |
| `MSG-00094` | axis-destroyer-line | 态势报告 | T4 | T5 | +0 |  |
| `MSG-00097` | axis-cruiser-line | 态势报告 | T4 | T5 | +0 |  |
| `MSG-00098` | axis-destroyer-line | 态势报告 | T4 | T5 | +0 |  |
| `MSG-00101` | axis-cruiser-line | 态势报告 | T5 | T5 | +0 |  |
| `MSG-00102` | axis-destroyer-line | 态势报告 | T5 | T5 | +0 |  |
| `MSG-00105` | axis-cruiser-line | 态势报告 | T5 | T5 | +0 |  |
| `MSG-00106` | axis-destroyer-line | 态势报告 | T5 | T5 | +0 |  |
| `MSG-00109` | axis-cruiser-line | 态势报告 | T5 | T5 | +0 |  |
| `MSG-00110` | axis-destroyer-line | 态势报告 | T5 | T5 | +0 |  |
| `MSG-00113` | axis-cruiser-line | 态势报告 | T5 | T5 | +0 |  |
| `MSG-00114` | axis-destroyer-line | 态势报告 | T5 | T5 | +0 |  |
| `MSG-00117` | axis-cruiser-line | 态势报告 | T5 | T5 | +0 |  |
| `MSG-00118` | axis-destroyer-line | 接触报告 | T5 | T5 | +0 |  |
| `MSG-00121` | axis-cruiser-line | 态势报告 | T5 | T6 | +0 |  |
| `MSG-00122` | axis-destroyer-line | 接触报告 | T5 | T5 | +0 |  |
| `MSG-00125` | axis-cruiser-line | 态势报告 | T5 | T6 | +0 |  |
| `MSG-00126` | axis-destroyer-line | 接触报告 | T5 | T6 | +0 |  |
| `MSG-00129` | axis-cruiser-line | 态势报告 | T6 | T6 | +0 |  |
| `MSG-00130` | axis-destroyer-line | 接触报告 | T6 | T6 | +0 |  |
| `MSG-00133` | axis-cruiser-line | 态势报告 | T6 | T6 | +0 |  |
| `MSG-00134` | axis-destroyer-line | 接触报告 | T6 | T6 | +0 |  |
| `MSG-00137` | axis-cruiser-line | 态势报告 | T6 | T6 | +0 |  |
| `MSG-00138` | axis-destroyer-line | 接触报告 | T6 | T6 | +0 |  |
| `MSG-00141` | axis-cruiser-line | 态势报告 | T6 | T6 | +0 |  |
| `MSG-00142` | axis-destroyer-line | 接触报告 | T6 | T6 | +0 |  |
| `MSG-00145` | axis-cruiser-line | 态势报告 | T6 | T6 | +0 |  |
| `MSG-00146` | axis-destroyer-line | 接触报告 | T6 | T8 | +2 |  |
| `MSG-00149` | axis-cruiser-line | 态势报告 | T6 | T6 | +0 |  |
| `MSG-00150` | axis-destroyer-line | 接触报告 | T6 | T8 | +2 |  |
| `MSG-00153` | axis-cruiser-line | 态势报告 | T6 | T7 | +0 |  |
| `MSG-00154` | axis-destroyer-line | 接触报告 | T6 | T8 | +2 |  |
| `MSG-00157` | axis-cruiser-line | 态势报告 | T7 | T7 | +0 |  |
| `MSG-00158` | axis-destroyer-line | 接触报告 | T7 | T9 | +2 |  |
| `MSG-00161` | axis-cruiser-line | 态势报告 | T7 | T7 | +0 |  |
| `MSG-00162` | axis-destroyer-line | 接触报告 | T7 | T9 | +2 |  |
| `MSG-00165` | axis-cruiser-line | 态势报告 | T7 | T7 | +0 |  |
| `MSG-00166` | axis-destroyer-line | 接触报告 | T7 | T9 | +2 |  |
| `MSG-00169` | axis-cruiser-line | 态势报告 | T7 | T7 | +0 |  |
| `MSG-00170` | axis-destroyer-line | 接触报告 | T7 | T9 | +2 |  |
| `MSG-00173` | axis-cruiser-line | 态势报告 | T7 | T7 | +0 |  |
| `MSG-00174` | axis-destroyer-line | 接触报告 | T7 | T9 | +2 |  |
| `MSG-00177` | axis-cruiser-line | 态势报告 | T7 | T7 | +0 |  |
| `MSG-00178` | axis-destroyer-line | 接触报告 | T7 | T9 | +2 |  |
| `MSG-00181` | axis-cruiser-line | 态势报告 | T7 | T8 | +0 |  |
| `MSG-00182` | axis-destroyer-line | 接触报告 | T7 | T9 | +2 |  |
| `MSG-00185` | axis-cruiser-line | 态势报告 | T8 | T8 | +0 |  |
| `MSG-00186` | axis-destroyer-line | 接触报告 | T8 | T10 | +2 |  |
| `MSG-00189` | axis-cruiser-line | 态势报告 | T8 | T8 | +0 |  |
| `MSG-00190` | axis-destroyer-line | 接触报告 | T8 | T10 | +2 |  |
| `MSG-00193` | axis-cruiser-line | 态势报告 | T8 | T8 | +0 |  |
| `MSG-00194` | axis-destroyer-line | 接触报告 | T8 | T10 | +2 |  |
| `MSG-00197` | axis-cruiser-line | 态势报告 | T8 | T8 | +0 |  |
| `MSG-00198` | axis-destroyer-line | 接触报告 | T8 | T10 | +2 |  |
| `MSG-00201` | axis-cruiser-line | 态势报告 | T8 | T8 | +0 |  |
| `MSG-00202` | axis-destroyer-line | 接触报告 | T8 | T10 | +2 |  |
| `MSG-00205` | axis-cruiser-line | 态势报告 | T8 | T8 | +0 |  |
| `MSG-00206` | axis-destroyer-line | 接触报告 | T8 | T10 | +2 |  |
| `MSG-00209` | axis-cruiser-line | 态势报告 | T8 | T9 | +0 |  |
| `MSG-00210` | axis-destroyer-line | 接触报告 | T8 | T10 | +2 |  |
| `MSG-00213` | axis-cruiser-line | 态势报告 | T9 | T9 | +0 |  |
| `MSG-00214` | axis-destroyer-line | 接触报告 | T9 | T11 | +2 |  |
| `MSG-00217` | axis-cruiser-line | 态势报告 | T9 | T9 | +0 |  |
| `MSG-00218` | axis-destroyer-line | 接触报告 | T9 | T11 | +2 |  |
| `MSG-00221` | axis-cruiser-line | 态势报告 | T9 | T9 | +0 |  |
| `MSG-00222` | axis-destroyer-line | 接触报告 | T9 | T11 | +2 |  |
| `MSG-00225` | axis-cruiser-line | 态势报告 | T9 | T9 | +0 |  |
| `MSG-00226` | axis-destroyer-line | 接触报告 | T9 | T11 | +2 |  |
| `MSG-00229` | axis-cruiser-line | 态势报告 | T9 | T9 | +0 |  |
| `MSG-00230` | axis-destroyer-line | 接触报告 | T9 | T11 | +2 |  |
| `MSG-00233` | axis-cruiser-line | 接触报告 | T9 | T9 | +0 |  |
| `MSG-00234` | axis-destroyer-line | 接触报告 | T9 | T11 | +2 |  |
| `MSG-00237` | axis-cruiser-line | 接触报告 | T9 | T10 | +0 |  |
| `MSG-00238` | axis-destroyer-line | 接触报告 | T9 | T11 | +2 |  |
| `MSG-00241` | axis-cruiser-line | 态势报告 | T10 | T10 | +0 |  |
| `MSG-00242` | axis-destroyer-line | 接触报告 | T10 | T12 | +2 |  |
| `MSG-00245` | axis-cruiser-line | 态势报告 | T10 | T10 | +0 |  |
| `MSG-00246` | axis-destroyer-line | 接触报告 | T10 | T12 | +2 |  |
| `MSG-00249` | axis-cruiser-line | 态势报告 | T10 | T10 | +0 |  |
| `MSG-00250` | axis-destroyer-line | 接触报告 | T10 | T12 | +2 |  |
| `MSG-00253` | axis-cruiser-line | 态势报告 | T10 | T10 | +0 |  |
| `MSG-00254` | axis-destroyer-line | 接触报告 | T10 | T12 | +2 |  |
| `MSG-00257` | axis-cruiser-line | 态势报告 | T10 | T10 | +0 |  |
| `MSG-00258` | axis-destroyer-line | 接触报告 | T10 | T12 | +2 |  |
| `MSG-00261` | axis-cruiser-line | 态势报告 | T10 | T10 | +0 |  |
| `MSG-00262` | axis-destroyer-line | 接触报告 | T10 | T12 | +2 |  |
| `MSG-00265` | axis-cruiser-line | 态势报告 | T10 | T11 | +0 |  |
| `MSG-00266` | axis-destroyer-line | 接触报告 | T10 | T12 | +2 |  |
| `MSG-00269` | axis-cruiser-line | 态势报告 | T11 | T11 | +0 |  |
| `MSG-00270` | axis-destroyer-line | 接触报告 | T11 | — | +2 |  |
| `MSG-00273` | axis-cruiser-line | 态势报告 | T11 | T11 | +0 |  |
| `MSG-00274` | axis-destroyer-line | 接触报告 | T11 | — | +2 |  |
| `MSG-00277` | axis-cruiser-line | 态势报告 | T11 | T11 | +0 |  |
| `MSG-00278` | axis-destroyer-line | 接触报告 | T11 | — | +2 |  |
| `MSG-00281` | axis-cruiser-line | 态势报告 | T11 | T11 | +0 |  |
| `MSG-00282` | axis-destroyer-line | 接触报告 | T11 | — | +2 |  |
| `MSG-00285` | axis-cruiser-line | 态势报告 | T11 | T11 | +0 |  |
| `MSG-00286` | axis-destroyer-line | 接触报告 | T11 | — | +2 |  |
| `MSG-00289` | axis-cruiser-line | 态势报告 | T11 | T11 | +0 |  |
| `MSG-00290` | axis-destroyer-line | 接触报告 | T11 | — | +2 |  |
| `MSG-00293` | axis-cruiser-line | 态势报告 | T11 | T12 | +0 |  |
| `MSG-00296` | axis-cruiser-line | 态势报告 | T12 | T12 | +0 |  |
| `MSG-00299` | axis-cruiser-line | 态势报告 | T12 | T12 | +0 |  |
| `MSG-00302` | axis-cruiser-line | 态势报告 | T12 | T12 | +0 |  |
| `MSG-00305` | axis-cruiser-line | 态势报告 | T12 | T12 | +0 |  |
| `MSG-00308` | axis-cruiser-line | 态势报告 | T12 | T12 | +0 |  |
| `MSG-00311` | axis-cruiser-line | 态势报告 | T12 | T12 | +0 |  |
| `MSG-00314` | axis-cruiser-line | 态势报告 | T12 | T12 | +0 |  |
| `MSG-00317` | axis-cruiser-line | 态势报告 | T12 | — | +0 |  |

## 美方的指挥与上报

| 回合 | 总指挥命令（原文摘录） | 下达方式 | 媒介 | 延迟 |
|---|---|---|---|---|

**分舰队的上报**（agent 亲笔正文 + 引擎保底态势）

| 报文 | 上报编队 | 类型 | 发出 | 送达 | 延迟 | 正文摘录 |
|---|---|---|---|---|---|---|
| `MSG-00003` | allies-cruiser-line | 态势报告 | T1 | T1 | +0 |  |
| `MSG-00004` | allies-destroyer-line | 态势报告 | T1 | T1 | +0 |  |
| `MSG-00007` | allies-cruiser-line | 态势报告 | T1 | T1 | +0 |  |
| `MSG-00008` | allies-destroyer-line | 态势报告 | T1 | T1 | +0 |  |
| `MSG-00011` | allies-cruiser-line | 态势报告 | T1 | T2 | +0 |  |
| `MSG-00012` | allies-destroyer-line | 态势报告 | T1 | T2 | +0 |  |
| `MSG-00015` | allies-cruiser-line | 态势报告 | T2 | T2 | +0 |  |
| `MSG-00016` | allies-destroyer-line | 态势报告 | T2 | T2 | +0 |  |
| `MSG-00023` | allies-cruiser-line | 态势报告 | T2 | T2 | +0 |  |
| `MSG-00024` | allies-destroyer-line | 态势报告 | T2 | T2 | +0 |  |
| `MSG-00027` | allies-cruiser-line | 态势报告 | T2 | T2 | +0 |  |
| `MSG-00028` | allies-destroyer-line | 态势报告 | T2 | T2 | +0 |  |
| `MSG-00031` | allies-cruiser-line | 态势报告 | T2 | T2 | +0 |  |
| `MSG-00032` | allies-destroyer-line | 态势报告 | T2 | T2 | +0 |  |
| `MSG-00035` | allies-cruiser-line | 态势报告 | T2 | T2 | +0 |  |
| `MSG-00036` | allies-destroyer-line | 态势报告 | T2 | T2 | +0 |  |
| `MSG-00039` | allies-cruiser-line | 态势报告 | T2 | T2 | +0 |  |
| `MSG-00040` | allies-destroyer-line | 态势报告 | T2 | T2 | +0 |  |
| `MSG-00043` | allies-cruiser-line | 态势报告 | T2 | T3 | +0 |  |
| `MSG-00044` | allies-destroyer-line | 态势报告 | T2 | T3 | +0 |  |
| `MSG-00047` | allies-cruiser-line | 态势报告 | T3 | T3 | +0 |  |
| `MSG-00048` | allies-destroyer-line | 态势报告 | T3 | T3 | +0 |  |
| `MSG-00051` | allies-cruiser-line | 态势报告 | T3 | T3 | +0 |  |
| `MSG-00052` | allies-destroyer-line | 态势报告 | T3 | T3 | +0 |  |
| `MSG-00055` | allies-cruiser-line | 态势报告 | T3 | T3 | +0 |  |
| `MSG-00056` | allies-destroyer-line | 态势报告 | T3 | T3 | +0 |  |
| `MSG-00059` | allies-cruiser-line | 态势报告 | T3 | T3 | +0 |  |
| `MSG-00060` | allies-destroyer-line | 态势报告 | T3 | T3 | +0 |  |
| `MSG-00063` | allies-cruiser-line | 态势报告 | T3 | T3 | +0 |  |
| `MSG-00064` | allies-destroyer-line | 态势报告 | T3 | T3 | +0 |  |
| `MSG-00067` | allies-cruiser-line | 态势报告 | T3 | T4 | +0 |  |
| `MSG-00068` | allies-destroyer-line | 态势报告 | T3 | T4 | +0 |  |
| `MSG-00071` | allies-cruiser-line | 态势报告 | T3 | T4 | +0 |  |
| `MSG-00072` | allies-destroyer-line | 态势报告 | T3 | T4 | +0 |  |
| `MSG-00075` | allies-cruiser-line | 态势报告 | T4 | T4 | +0 |  |
| `MSG-00076` | allies-destroyer-line | 态势报告 | T4 | T4 | +0 |  |
| `MSG-00079` | allies-cruiser-line | 态势报告 | T4 | T4 | +0 |  |
| `MSG-00080` | allies-destroyer-line | 态势报告 | T4 | T4 | +0 |  |
| `MSG-00083` | allies-cruiser-line | 态势报告 | T4 | T4 | +0 |  |
| `MSG-00084` | allies-destroyer-line | 态势报告 | T4 | T4 | +0 |  |
| `MSG-00087` | allies-cruiser-line | 态势报告 | T4 | T4 | +0 |  |
| `MSG-00088` | allies-destroyer-line | 态势报告 | T4 | T4 | +0 |  |
| `MSG-00091` | allies-cruiser-line | 态势报告 | T4 | T4 | +0 |  |
| `MSG-00092` | allies-destroyer-line | 态势报告 | T4 | T4 | +0 |  |
| `MSG-00095` | allies-cruiser-line | 态势报告 | T4 | T5 | +0 |  |
| `MSG-00096` | allies-destroyer-line | 态势报告 | T4 | T5 | +0 |  |
| `MSG-00099` | allies-cruiser-line | 态势报告 | T4 | T5 | +0 |  |
| `MSG-00100` | allies-destroyer-line | 态势报告 | T4 | T5 | +0 |  |
| `MSG-00103` | allies-cruiser-line | 态势报告 | T5 | T5 | +0 |  |
| `MSG-00104` | allies-destroyer-line | 态势报告 | T5 | T5 | +0 |  |
| `MSG-00107` | allies-cruiser-line | 态势报告 | T5 | T5 | +0 |  |
| `MSG-00108` | allies-destroyer-line | 态势报告 | T5 | T5 | +0 |  |
| `MSG-00111` | allies-cruiser-line | 态势报告 | T5 | T5 | +0 |  |
| `MSG-00112` | allies-destroyer-line | 态势报告 | T5 | T5 | +0 |  |
| `MSG-00115` | allies-cruiser-line | 态势报告 | T5 | T5 | +0 |  |
| `MSG-00116` | allies-destroyer-line | 态势报告 | T5 | T5 | +0 |  |
| `MSG-00119` | allies-cruiser-line | 态势报告 | T5 | T5 | +0 |  |
| `MSG-00120` | allies-destroyer-line | 态势报告 | T5 | T6 | +0 |  |
| `MSG-00123` | allies-cruiser-line | 态势报告 | T5 | T6 | +0 |  |
| `MSG-00124` | allies-destroyer-line | 态势报告 | T5 | T6 | +0 |  |
| `MSG-00127` | allies-cruiser-line | 态势报告 | T5 | T6 | +0 |  |
| `MSG-00128` | allies-destroyer-line | 态势报告 | T5 | T6 | +0 |  |
| `MSG-00131` | allies-cruiser-line | 态势报告 | T6 | T6 | +0 |  |
| `MSG-00132` | allies-destroyer-line | 态势报告 | T6 | T6 | +0 |  |
| `MSG-00135` | allies-cruiser-line | 态势报告 | T6 | T6 | +0 |  |
| `MSG-00136` | allies-destroyer-line | 态势报告 | T6 | T6 | +0 |  |
| `MSG-00139` | allies-cruiser-line | 态势报告 | T6 | T6 | +0 |  |
| `MSG-00140` | allies-destroyer-line | 态势报告 | T6 | T6 | +0 |  |
| `MSG-00143` | allies-cruiser-line | 态势报告 | T6 | T6 | +0 |  |
| `MSG-00144` | allies-destroyer-line | 态势报告 | T6 | T6 | +0 |  |
| `MSG-00147` | allies-cruiser-line | 态势报告 | T6 | T6 | +0 |  |
| `MSG-00148` | allies-destroyer-line | 态势报告 | T6 | T6 | +0 |  |
| `MSG-00151` | allies-cruiser-line | 态势报告 | T6 | T7 | +0 |  |
| `MSG-00152` | allies-destroyer-line | 态势报告 | T6 | T7 | +0 |  |
| `MSG-00155` | allies-cruiser-line | 态势报告 | T6 | T7 | +0 |  |
| `MSG-00156` | allies-destroyer-line | 态势报告 | T6 | T7 | +0 |  |
| `MSG-00159` | allies-cruiser-line | 态势报告 | T7 | T7 | +0 |  |
| `MSG-00160` | allies-destroyer-line | 态势报告 | T7 | T7 | +0 |  |
| `MSG-00163` | allies-cruiser-line | 态势报告 | T7 | T7 | +0 |  |
| `MSG-00164` | allies-destroyer-line | 态势报告 | T7 | T7 | +0 |  |
| `MSG-00167` | allies-cruiser-line | 态势报告 | T7 | T7 | +0 |  |
| `MSG-00168` | allies-destroyer-line | 态势报告 | T7 | T7 | +0 |  |
| `MSG-00171` | allies-cruiser-line | 态势报告 | T7 | T7 | +0 |  |
| `MSG-00172` | allies-destroyer-line | 态势报告 | T7 | T7 | +0 |  |
| `MSG-00175` | allies-cruiser-line | 接触报告 | T7 | T7 | +0 |  |
| `MSG-00176` | allies-destroyer-line | 接触报告 | T7 | T7 | +0 |  |
| `MSG-00179` | allies-cruiser-line | 接触报告 | T7 | T7 | +0 |  |
| `MSG-00180` | allies-destroyer-line | 接触报告 | T7 | T7 | +0 |  |
| `MSG-00183` | allies-cruiser-line | 接触报告 | T7 | T8 | +0 |  |
| `MSG-00184` | allies-destroyer-line | 接触报告 | T7 | T8 | +0 |  |
| `MSG-00187` | allies-cruiser-line | 接触报告 | T8 | T8 | +0 |  |
| `MSG-00188` | allies-destroyer-line | 接触报告 | T8 | T8 | +0 |  |
| `MSG-00191` | allies-cruiser-line | 接触报告 | T8 | T8 | +0 |  |
| `MSG-00192` | allies-destroyer-line | 接触报告 | T8 | T8 | +0 |  |
| `MSG-00195` | allies-cruiser-line | 接触报告 | T8 | T8 | +0 |  |
| `MSG-00196` | allies-destroyer-line | 接触报告 | T8 | T8 | +0 |  |
| `MSG-00199` | allies-cruiser-line | 接触报告 | T8 | T8 | +0 |  |
| `MSG-00200` | allies-destroyer-line | 接触报告 | T8 | T8 | +0 |  |
| `MSG-00203` | allies-cruiser-line | 接触报告 | T8 | T8 | +0 |  |
| `MSG-00204` | allies-destroyer-line | 接触报告 | T8 | T8 | +0 |  |
| `MSG-00207` | allies-cruiser-line | 接触报告 | T8 | T8 | +0 |  |
| `MSG-00208` | allies-destroyer-line | 接触报告 | T8 | T8 | +0 |  |
| `MSG-00211` | allies-cruiser-line | 接触报告 | T8 | T9 | +0 |  |
| `MSG-00212` | allies-destroyer-line | 接触报告 | T8 | T9 | +0 |  |
| `MSG-00215` | allies-cruiser-line | 接触报告 | T9 | T9 | +0 |  |
| `MSG-00216` | allies-destroyer-line | 接触报告 | T9 | T9 | +0 |  |
| `MSG-00219` | allies-cruiser-line | 接触报告 | T9 | T9 | +0 |  |
| `MSG-00220` | allies-destroyer-line | 接触报告 | T9 | T9 | +0 |  |
| `MSG-00223` | allies-cruiser-line | 接触报告 | T9 | T9 | +0 |  |
| `MSG-00224` | allies-destroyer-line | 接触报告 | T9 | T9 | +0 |  |
| `MSG-00227` | allies-cruiser-line | 接触报告 | T9 | T9 | +0 |  |
| `MSG-00228` | allies-destroyer-line | 接触报告 | T9 | T9 | +0 |  |
| `MSG-00231` | allies-cruiser-line | 接触报告 | T9 | T9 | +0 |  |
| `MSG-00232` | allies-destroyer-line | 接触报告 | T9 | T9 | +0 |  |
| `MSG-00235` | allies-cruiser-line | 接触报告 | T9 | T9 | +0 |  |
| `MSG-00236` | allies-destroyer-line | 接触报告 | T9 | T9 | +0 |  |
| `MSG-00239` | allies-cruiser-line | 接触报告 | T9 | T10 | +0 |  |
| `MSG-00240` | allies-destroyer-line | 接触报告 | T9 | T10 | +0 |  |
| `MSG-00243` | allies-cruiser-line | 接触报告 | T10 | T10 | +0 |  |
| `MSG-00244` | allies-destroyer-line | 接触报告 | T10 | T10 | +0 |  |
| `MSG-00247` | allies-cruiser-line | 接触报告 | T10 | T10 | +0 |  |
| `MSG-00248` | allies-destroyer-line | 接触报告 | T10 | T10 | +0 |  |
| `MSG-00251` | allies-cruiser-line | 接触报告 | T10 | T10 | +0 |  |
| `MSG-00252` | allies-destroyer-line | 接触报告 | T10 | T10 | +0 |  |
| `MSG-00255` | allies-cruiser-line | 接触报告 | T10 | T10 | +0 |  |
| `MSG-00256` | allies-destroyer-line | 接触报告 | T10 | T10 | +0 |  |
| `MSG-00259` | allies-cruiser-line | 接触报告 | T10 | T10 | +0 |  |
| `MSG-00260` | allies-destroyer-line | 接触报告 | T10 | T10 | +0 |  |
| `MSG-00263` | allies-cruiser-line | 接触报告 | T10 | T10 | +0 |  |
| `MSG-00264` | allies-destroyer-line | 接触报告 | T10 | T10 | +0 |  |
| `MSG-00267` | allies-cruiser-line | 接触报告 | T10 | T11 | +0 |  |
| `MSG-00268` | allies-destroyer-line | 接触报告 | T10 | T11 | +0 |  |
| `MSG-00271` | allies-cruiser-line | 接触报告 | T11 | T11 | +0 |  |
| `MSG-00272` | allies-destroyer-line | 接触报告 | T11 | T11 | +0 |  |
| `MSG-00275` | allies-cruiser-line | 接触报告 | T11 | T11 | +0 |  |
| `MSG-00276` | allies-destroyer-line | 接触报告 | T11 | T11 | +0 |  |
| `MSG-00279` | allies-cruiser-line | 接触报告 | T11 | T11 | +0 |  |
| `MSG-00280` | allies-destroyer-line | 接触报告 | T11 | T11 | +0 |  |
| `MSG-00283` | allies-cruiser-line | 接触报告 | T11 | T11 | +0 |  |
| `MSG-00284` | allies-destroyer-line | 接触报告 | T11 | T11 | +0 |  |
| `MSG-00287` | allies-cruiser-line | 接触报告 | T11 | T11 | +0 |  |
| `MSG-00288` | allies-destroyer-line | 接触报告 | T11 | T11 | +0 |  |
| `MSG-00291` | allies-cruiser-line | 接触报告 | T11 | T11 | +0 |  |
| `MSG-00292` | allies-destroyer-line | 接触报告 | T11 | T11 | +0 |  |
| `MSG-00294` | allies-cruiser-line | 接触报告 | T11 | T12 | +0 |  |
| `MSG-00295` | allies-destroyer-line | 接触报告 | T11 | T12 | +0 |  |
| `MSG-00297` | allies-cruiser-line | 态势报告 | T12 | T12 | +0 |  |
| `MSG-00298` | allies-destroyer-line | 态势报告 | T12 | T12 | +0 |  |
| `MSG-00300` | allies-cruiser-line | 态势报告 | T12 | T12 | +0 |  |
| `MSG-00301` | allies-destroyer-line | 态势报告 | T12 | T12 | +0 |  |
| `MSG-00303` | allies-cruiser-line | 态势报告 | T12 | T12 | +0 |  |
| `MSG-00304` | allies-destroyer-line | 态势报告 | T12 | T12 | +0 |  |
| `MSG-00306` | allies-cruiser-line | 态势报告 | T12 | T12 | +0 |  |
| `MSG-00307` | allies-destroyer-line | 态势报告 | T12 | T12 | +0 |  |
| `MSG-00309` | allies-cruiser-line | 态势报告 | T12 | T12 | +0 |  |
| `MSG-00310` | allies-destroyer-line | 态势报告 | T12 | T12 | +0 |  |
| `MSG-00312` | allies-cruiser-line | 态势报告 | T12 | T12 | +0 |  |
| `MSG-00313` | allies-destroyer-line | 态势报告 | T12 | T12 | +0 |  |
| `MSG-00315` | allies-cruiser-line | 态势报告 | T12 | T12 | +0 |  |
| `MSG-00316` | allies-destroyer-line | 态势报告 | T12 | T12 | +0 |  |
| `MSG-00318` | allies-cruiser-line | 态势报告 | T12 | — | +0 |  |
| `MSG-00319` | allies-destroyer-line | 态势报告 | T12 | — | +0 |  |

## 代理自主性：如实记账

被引擎拒绝、改由确定性教条执行的回合：

| 回合 | 阵营 | 驳回原因（引擎原文） |
|---|---|---|
| T3 | 日方 | axis-destroyer-line: speed 6 is outside member limits; reduce or detach |
| T3 | 美方 | allies-battle-line: IBS-U-USN-ERMA-NEW-JERSEY (新泽西) follower speed 6 outside 2-5；allies-battle-line: IBS-U-USN-ERMA-MISSOURI (密苏里) cannot follow guide |
| T5 | 日方 | axis-battle-line: IBS-U-IJN-ERMA-MUSASHI (武藏) cannot follow guide trail before advancing；axis-battle-line: IBS-U-IJN-ERMA-SHINANO (信浓) cannot follow g |
| T6 | 日方 | axis-destroyer-line: speed 6 is outside member limits; reduce or detach |
| T7 | 日方 | axis-cruiser-line: IBS-U-IJN-ERMA-KURAMA (鞍马) cannot follow guide trail before advancing |
| T9 | 日方 | axis-cruiser-line: IBS-U-IJN-ERMA-GOKASE (五濑) cannot follow guide trail before advancing；axis-destroyer-line: IBS-U-IJN-ERMA-MAKINAMI (卷波) follower sp |
| T11 | 日方 | axis-destroyer-line: IBS-U-IJN-ERMA-KAZEGUMO (风云) cannot follow guide trail before advancing |
| T11 | 美方 | allies-battle-line: speed 0 is outside member limits; reduce or detach |
| T12 | 日方 | axis-battle-line: speed 0 is outside member limits; reduce or detach |
| T12 | 美方 | allies-battle-line: speed 0 is outside member limits; reduce or detach |

## 思维链摘录（每位指挥每回合的判断）


## 数据文件

| 文件 | 内容 |
|---|---|
| `battle_data.json` | 对局全记录：逐回合事件、决策、记忆、电报台账、三视角观测索引 |
| `calls.jsonl` | 每次模型调用：提示词、回复、思维链、token 用量、延迟、传输失败 |
| `orders.jsonl` | 引擎接受的每一个指令批次（可用 replay_battle.py 逐位重演） |
| `reports.jsonl` | 每一封上报：作者、正文、发出/送达回合与延迟 |
| `views/` | 逐阶段三视角观测（上帝/日方/美方）与全状态快照 |
| `replay_verification.json` | 从 orders.jsonl 重演与本局终局的一致性核验 |
| `leak_scan.json` | 提示词泄漏核验（含上报正文判据与注入正对照） |
