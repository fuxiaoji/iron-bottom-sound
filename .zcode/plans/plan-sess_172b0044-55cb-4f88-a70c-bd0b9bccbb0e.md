# 兵棋大厅（wargame-hall）：双人对战 + 聊天 + 注册，挂在 fuwenji.asia/hall

## 0. 已确认的前提

| 项 | 结论 |
|---|---|
| 技术栈 | **Node/TypeScript**（Fastify + `ws` + React 19 SPA） |
| 前端范围 | **大厅 + 对局界面统一自研**，一套中文设计系统，杜绝"移植得乱七八糟" |
| 规模目标 | 小规模：几十人、几十局并存 → 单进程单机，**不引入 Redis/NATS**，但留好扩展缝 |
| 本轮交付 | 端到端最小闭环 + 部署上线 |
| 地址 | `https://fuwenji.asia/hall/`（根域作品集、`/tiedi`、`/bismarck` 完全不动） |

**服务器现状**（只读探测所得，未改动任何东西）：

| 路径 | 后端 | 内容 |
|---|---|---|
| `/` | 静态 | 作品集 |
| `/tiedi/` | 127.0.0.1:8001 | 铁底湾的回响 IV（FastAPI + React） |
| `/bismarck/` | 127.0.0.1:4174 | 击沉俾斯麦号 Online（Node/Vite，带 WebSocket 升级） |
| `/game/` | 127.0.0.1:4175 | 同样返回"击沉俾斯麦号" |
| `/spider-api/` | 127.0.0.1:5000/api/ | 无关 |

**两款棋**：铁底湾的回响 IV、击沉俾斯麦号 Online。后者源码**只在服务器上**（本地全盘搜索无副本），状态未知 → 由 B0 只读盘点确定。

**最大杠杆**：`铁底湾-RTT/rules.js` 已经是 `setup / view(state,seat) / action(state,seat,action,arg)` 的纯函数、无 I/O、无依赖形态，且带 9 个 Node 验证测试与 303 条 Python↔JS 冻结规则向量。这正是新大厅的适配器契约，**铁底湾规则零重写**。

---

## 1. 为什么 RTT 慢，以及这次怎么避开

不换语言的借口，而是逐条消除病因：

| RTT 的病因 | 本方案 |
|---|---|
| 服务端每请求渲染 Pug 模板 | 纯 SPA，API 只回 JSON |
| 每次操作整页刷新 | WebSocket 增量推送，页面不重载 |
| `better-sqlite3` 同步调用阻塞 event loop | SQLite 收敛到**一个专用 worker 线程**，主线程只做内存操作；WAL + 读写分离 |
| 每步重写整份状态 JSON 落库 | 内存权威状态 + **追加式事件日志** + 周期性快照（write-behind，热路径零落库） |
| 无版本号，重试即重复 | 单调版本号 `v` + `clientMsgId` 幂等去重 + `resync` 兜底 |

**诚实的目标数字**：回合制兵棋的瓶颈是**连接数而非吞吐**（Colyseus 作者实测：简单回合制在 $5 VPS 上约 3000 CCU）。我们的目标是几十人/几十局，所以用 `ws` 足够，`uWebSockets.js` 留作备选。性能要有**证据**而非口号：随包交付压测脚本，输出并发 WS 数、p50/p95 延迟、RSS、event-loop lag。

---

## 2. 新仓库

位置：`C:\Users\fwj\Documents\ChatGPT\wargame-hall\`（ASCII 目录名，规避你环境里已验证过的中文路径乱码问题）。

```
wargame-hall/
  agent.md  plan.md  havedone.md          # 沿用你的治理三件套
  packages/
    protocol/       # 共享 TS 类型 + WS 消息协议（版本化、zod 校验）
    hall-server/    # Fastify + ws：账号/房间/席位/聊天/裁判/持久化
    hall-web/       # React SPA：设计系统 + 大厅 + 房间 + 对局壳
    game-ibs/       # 铁底湾适配器（包现有 rules.js，纯函数）
    game-bismarck/  # 击沉俾斯麦适配器（依 B0 结论）
  tools/  tests/  deploy/
```

治理沿用你的规矩：开工前更新 `plan.md`，批次完成后向 `havedone.md` 追加日期、测试、证据、提交哈希。同时在 `铁底湾/plan.md`、`铁底湾/havedone.md` 补记 2026-09-11~13 的 RTT 批次（目前缺失，违反 `agent.md`）。

---

## 3. 服务端架构（hall-server）

**每局一个 writer（actor）**：一个 `GameRoom` 对象独占该局权威状态，所有变更走该房间的串行队列。无跨局锁、无分布式事务。

**事件日志 + 快照**：内存变更 → 追加事件 → 按序推入写线程队列 → 每 N 回合快照。冷读与重连只碰快照。

**版本化增量同步（照抄 Lichess 模型）**：每条事件带单调 `v`；每个 socket 记录已下发 `v`；重连时客户端上报自己的 `v`，服务端回增量，落后太多则回 `{"t":"resync"}` 强制全量。设计前提是**广播允许丢失**，所以版本号对账是必需的，不是优化。

**服务端按席位脱敏**：`viewFor(state, seat)` 在服务端完成，敌方秘密计划、鱼雷航迹、未探明舰船**永不进入网络与 DOM**。这是铁底湾"双人同时封存 + 隐蔽接触"的硬要求。

**幂等**：所有客户端命令带 `clientMsgId`，服务端去重 → 弱网重试安全。

**Socket 层隔离**：`ws` 挂 `Transport` 接口，日后要换 `uWebSockets.js` 或拆成独立 WS 层（配 Redis pub/sub）都不动业务代码。

**端口**：大厅监听 `127.0.0.1:4180`（避开已占用的 8000/8001/4174/4175/5000/8080）。

---

## 4. 游戏适配器契约（本项目的核心抽象）

两个棋各实现一份，大厅只认这个接口：

```ts
interface GameAdapter {
  id: string; title: string;                       // "ibs" | "bismarck"
  meta: { cover: string; about: string; seats: SeatMeta[] };
  createOptions(): ScenarioOption[];               // 创建对局表单
  setup(seed, scenarioId, options): GameState;     // 纯函数
  viewFor(state, seat): PublicView;                // 服务端脱敏
  legalActions(state, seat): LegalAction[];
  submit(state, seat, action, arg): { state; events } | Error;  // 纯、幂等
  currentActors(state): Seat[];
  isOver(state): Result | null;
  replay(events): GameState[];
}
```

契约测试对两个适配器统一跑：确定性（同种子同结果）、脱敏（对方视角无秘密）、幂等（重复提交不重复生效）、回放一致（重放事件流得到同一终局）。

铁底湾适配器直接包装 `铁底湾-RTT/rules.js` + `data.js`，把现有 9 个 Node 验证测试纳入本仓库 CI。击沉俾斯麦适配器在 B0 盘点后定：若它已有服务端与 WebSocket，则改用"薄代理"模式（大厅只统一账号/房间/聊天/轮到你了），否则按同一契约包它的规则代码。

---

## 5. 前端：一套设计系统，一个对局壳

`hall-web` = Vite + React 19 + TS。设计令牌走 CSS 自定义属性（深海军蓝 + 羊皮纸金，中文排版 Noto Sans SC），响应式断点按 RTT `NOTES.md` 里那套经验值（400 / 800px、`pointer: coarse`）。

**页面**：登录/注册 → 大厅 → 创建对局 → 对局工作区 → 回放。
**大厅**：两款棋的封面卡片网格 + 顶部"轮到你了"收件箱 + 进行中/已结束列表 + 在线玩家。
**对局工作区**：一个六角地图渲染器 + 一个指挥面板 + 右侧聊天/战报栏 + 席位与回合头，全部由适配器数据驱动。

**防止"前端再被改乱"的硬机制**（这是针对你明确痛点的工程约束）：
1. `game-*` 包**禁止**自带全局 CSS、禁止覆盖设计令牌、禁止内联样式表；只能导出数据适配器 + 少量棋种特有视图组件。
2. CI 校验脚本：扫描 `game-*` 下的 CSS/样式导入，违规即失败。
3. 一个对局壳，两个棋共用；地图、面板、聊天、结算全在壳里。

---

## 6. 账号与安全

- 自研账号：`users` + `sessions` 表，密码用 **argon2id**（或 `node:crypto` scrypt）哈希，绝不明文。
- 会话：不透明 session id + httpOnly + SameSite=Lax cookie（不用 JWT 做会话，便于撤销），CSRF 双提交令牌。
- 限流：`@fastify/rate-limit`；强密码校验。验证码/邮箱验证/找回密码本轮不做，接口预留。
- 跨游戏身份：一次性短时 game ticket 换取席位，两个棋各自校验，不共享 session。
- **凭据纪律**：密钥只进 `/etc/hall.env`（600），不进仓库、不进日志。部署用环境变量瞬时传参。
- ⚠️ **你刚把 root 密码贴在对话里了**。本轮结束后请立刻改密码并改用 SSH 密钥登录；`deploy/README.md:67` 已记录过一次同类事件（DeepSeek key 被要求吊销），不要再累积。

---

## 7. 部署（纯增量，不动现有任何东西）

- `deploy/nginx-hall.conf`：`location = /hall { 301 /hall/; }` + `location /hall/ { ... proxy_pass http://127.0.0.1:4180; Upgrade/Connection 头; proxy_read_timeout 86400s; }`
- `deploy/hall.service`：systemd，`WorkingDirectory=/opt/hall`，`EnvironmentFile=/etc/hall.env`，`Restart=on-failure`。
- 数据：`/opt/hall/data/hall.sqlite3`（WAL）。
- 流程沿用你 `plan.md:718-727` 已定的协议：只读版本核对 → SQLite Backup API 打时间戳备份 → 增量上传（排除 `.git`/数据库/WAL/SHM/缓存）→ 服务端构建 → 重启 → 接受 systemd active、HTTP 200、新 bundle、旧数据可读。
- 影响面：新增一个 nginx location 与一个 systemd unit。作品集、`/tiedi`、`/bismarck`、`/game` **零改动**。

---

## 8. 批次计划

**B0 只读盘点（先做，不改服务器）**
SSH 只读采集：`/opt` 目录、systemd units、`nginx -T` 完整配置、监听端口与进程、击沉俾斯麦的源码路径/技术栈/是否已有服务端与 WebSocket/规则引擎在哪/`/game` 与 `/bismarck` 的区别、`/tiedi` 布局与数据库。产出 `docs/server-inventory.md`。**这是决定俾斯麦接入方式的事实依据。**

**B1 仓库骨架 + 协议包 + 治理文件 + 压测脚手架**

**B2 账号体系**：注册/登录/登出/会话/限流 + 契约测试

**B3 房间与双人对战**：创建/加入/席位/双人同时封存/服务端裁决/事件日志+快照+版本化增量/断线重连/基础回放

**B4 聊天 + 战报 + "轮到你了"收件箱**

**B5 设计系统 + 大厅页 + 房间页 + 对局壳**

**B6 铁底湾适配器接入**（复用现有 JS 规则引擎）→ 端到端打通

**B7 部署 `/hall` 上线** + 压测证据 + 文档 + 治理记录

击沉俾斯麦适配器（B8）**排在本轮最小闭环之后**，具体做法由 B0 结论决定——若它已能联机，则只需"薄代理"（统一账号/房间/聊天/轮到你了），工作量很小；若只有单机，则是一块独立批次，我会带着盘点结果回来跟你确认再开工。

**本轮明确不做**：ELO/等级分、锦标赛、论坛、邮件通知、战绩统计、Redis/多进程水平扩展、观战完整 UI、验证码/邮箱验证/找回密码、移动端深度适配（只做基础响应式）。

---

## 9. 完成定义（缺一不可）

1. 两个不同浏览器、不同网络的人，注册各自账号，在大厅看到同一局，从创建到打完一局，全程无需刷新页面。
2. 聊天双向实时；对方落子后本方**主动**收到"轮到你了"，不需要手动刷新。
3. 服务端权威：拔网线再插上，刷新后局面与席位完全恢复，不丢步、不重复。
4. 隐藏信息不出服务端：抓包与 DOM 中均无对方秘密计划/鱼雷航迹/未探明舰船。
5. 同一事件流重放得到同一终局（确定性）。
6. 压测报告：并发 WS 数、p50/p95 延迟、RSS、event-loop lag，并逐条勾掉第 1 节那五个病症。
7. `https://fuwenji.asia/hall/` 可用，且 `/`、`/tiedi`、`/bismarck`、`/game` 未受影响。
8. `agent.md` / `plan.md` / `havedone.md` 三件套记录齐全（新仓库），并补记 `铁底湾` 仓库缺失的 RTT 批次。

---

## 10. 开工前需要你点头的两件小事

1. **B0 只读 SSH 盘点需要你的授权**：我会用密码登录（仅作环境变量瞬时传参，不落盘、不进仓库、不进日志），只执行读取类命令（`ls`/`cat`/`nginx -T`/`systemctl status`/`ss`/`ps`），不改动服务器任何文件、配置或服务。计划模式当前禁止我联服务器，所以 B0 是第一个执行步骤。
2. **`铁底湾` 仓库当前在 `glm/rtt-port` 分支上有未提交的棋子素材改动**（约 21 个 PNG）。建议先提交，避免与本批次的改动混在一起。我不会擅自动它们。

另外提醒：本方案会新建独立仓库，不改动 `铁底湾` 仓库的任何既有代码；铁底湾的规则引擎是**只读引用**，来源快照固定为 `铁底湾-RTT/` 当前版本并记入 `wargame-hall` 的来源清单，符合你在 `agent.md` 里定的"来源可追溯"要求。