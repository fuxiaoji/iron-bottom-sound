# QQ / MCP 验证记录（2026-10-22）

当前 QQ 路线为官方机器人「铁底湾指挥官」，AppID `1905878837`；NapCat 已停止，临时探针已还原。本记录区分官方协议/绑定验证、不同代码快照上的历史回归、服务器引擎烟测和真实 QQ 联调。各批次交叉覆盖，不把通过数相加；旧全批通过不代表所有后续改动已在同一最终快照全量通过。

GitHub 审查入口为 [validation-summary.json](evidence/validation-summary.json)，保留各批 raw XML 的 SHA256、计数与失败测试名，不发布原始错误正文或环境配置。安全部署副本包括 [鉴权](evidence/official-auth.json)、[回调](evidence/official-callback.json)、[实群](evidence/official-live.json)、[PVE 烟测](evidence/server-smoke.json)、[SSH MCP 烟测](evidence/ssh-mcp-smoke.json)、[来源](evidence/runtime-sources.json)、[运行包清单](evidence/ibs-bot-runtime.tar.gz.json)、[缓存清理](evidence/cleanup.json) 和 [切换清理](evidence/official-switch-cleanup.json)。完整 raw XML、PNG、截图及运行包二进制留本地 `artifacts/bot-20261022/`，不入 Git；本文原始产物链接用于本地核验。

## 官方方案：已验证与仍待验收

按用户指示创建应用，AppSecret 由用户本人重置后，服务器完成私有配置与官方 token 交换。平台已保存 Webhook 地址 `https://fuwenji.asia/ibs-bot/qq-official/events`；01:33:36 的真实平台 HTTP 挑战返回 200，服务记录 `challenge_signed`，腾讯平台验证回调并成功保存。验收依据为平台成功保存与服务端挑战记录，见 [official-callback.json](../../artifacts/bot-20261022/deploy/official-callback.json)。服务器伪造业务探针为 401，GET 为 405；旧游戏服务同时返回 200。官方网关/绑定提交为 `65eb4c8b`，连写解析为 `160aa235`，斜杠/引导为 `110c4a43`；群图/手动草稿修复为 `5bc33acc88de7f04560e06eeb8aebb33241d01c9`，服务器 10 个源码摘要匹配。

`GROUP_AT_MESSAGE_CREATE`、`C2C_MESSAGE_CREATE` 两项订阅已保存。用户真实 @ 触发验签、回复成功，服务器从该事件发现唯一真实 `group_openid` 并配置白名单，没有把数字群号猜成 OpenID。私有表 `bot_official_groups` 只存应用、群 OpenID 和最后发现时间，不存正文、发送者或命令。安全实群收据仅发布群与对局摘要，不发布成员、私聊身份或验证码。

首次真实「创建 编队pve」因参数连写返回用法；修复后用户原命令重发，成功建立 formation/PVE、盟军席位的对局。C2C 申请码、正确群作者确认绑定均有真实回调与回复；数据库确认唯一别名与已消费挑战。首次真实私聊「自动 0」从编队部署推进到第 1 回合增援、revision 1，日志 `command_auto`、`image_delivered`、`delivered` 证明腾讯 API 确认本方 PNG 发送。随后真实群「战况」触发 `command_public_map`、`image_delivered`、`delivered`，用户确认「两处都有图」。API 回执和用户实际显示确认为两种独立证据；本轮不包含逐像素或全局终局验收。当前未认证应用的管理员/群主范围与后续个人认证说明见 [QQ_OFFICIAL.md](QQ_OFFICIAL.md)。普通 QQ 账号历史限制 168 不再作为这条路线的阻断。

### 管理员 DeepSeek 裁判（dd36c9d6）

功能提交 `dd36c9d6d40109250caf891813add374e6d4784d` 已部署，13个源码摘要匹配。新增 `/裁判` 自然语言创建、双方阶段推进、状态修正、最近快照撤销及只读解释。生产运行进程只配置1名已验证管理员，私有env为0600；普通成员或自称管理员的提示不能提权。修改边界与生命周期限制见[管理员裁判](QQ_OFFICIAL.md#管理员-llm-裁判)。

最终同一源码主整合回归 `referee-release.xml` 为 **542通过 / 0失败 / 0跳过，129.265秒**。原423项范围加裁判服务、客户端和QQ路由，不把重叠单批相加。服务定点64项、客户端124项、恢复路由15项均有独立原始XML摘要。初次服务夹具漏 `role=assistant` 的1失败/46通过保留，修正夹具后重验；不得把初失败改为通过。

独立[有限审计](evidence/referee-audit.json)找到并验证修复：客户端metadata与六字段协议边界、地图坐标调用、模型猜隐藏舰、创建已提交但最终收据失败、QQ缓存挡住恢复。最终在冻结SHA下复验；一次或连续两次故障后均仅1次模型、1局，对同一事件恢复为done且回复msg_seq不重复。审计用真实客户端+MockTransport和隔离引擎，真实API调用0，不冒称独立模型提供研究结论。

[真实DeepSeek副本验证](evidence/referee-live-smoke.json)顺序调用4次：创建1.014秒/7217tokens，推进0.729秒/6863tokens，位置+正舰体修正1.373秒/7003tokens，撤销1.225秒/6994tokens。副本版本0→1→2→3，撤销后完整状态JSON与修正前相等（包括RNG）；重复撤销及非管理员均无新增模型请求或推进。正式SQLite只读连接复制，正式行摘要不变；QQ发送为Mock且每次成功操作返回1张PNG，不能称实际群修改验收。

另有[初次真实调用夹具失败](evidence/referee-live-smoke-initial.json)：模型create合法返回，记录进度时跨线程查询主线程创建的只读SQLite触发异常，隔离局未创建；该次1请求0.834秒/7216tokens如实保留。修正烟测只读连接的线程设置后，上述4请求全部通过；本批共5次真实API调用，不隐去失败成本。未因该夹具修改产品代码。首次部署检查误将健康字段当ok布尔值、随后用系统Python3.6执行仅支持新版本的text参数，均是验证助手错误；改用健康status字段与已有Python3.11后完成，服务保持active，没有重复重启。

[部署收据](evidence/referee-deployment.json)确认Bot/Nginx/旧游戏/大厅active，13192健康、旧游戏API、4180 HTTP探针均200（4180只为HTTP探针，不冒称引擎JSON健康）。[预设](evidence/qq-referee-panel.json)的好友/群各10条已保存重载；群“我的对局”、私聊“自动”的面板位置换为“裁判”，旧文本指令仍有效。当前运行包68,238,745字节/129成员，SHA256 `941445ce0227697ed8b90e5daeef8f8ba7444b1e78e2dfd8ea11451c39752153`，5份LFS原始来源核验通过。真实QQ管理员只读裁判回复/客户端预设显示已请求用户验证，尚未以旧版参谋确认代替；正式局未由验证脚本推进。

### DeepSeek群参谋与自然语言下令（a43f6fab）

功能a43f6fab18c8cc675ba667bedc5aaf0f2887dc82已部署，12源码摘要匹配。/参谋只读战报/建议，/下令仅当前发令者自有席位；原引擎最终验证。PVE群看玩家受限观察，PVP报告只看交集且下令/澄清群回执不展开私有战术。SQLite pending/prepared/done持久防重，模型IO不持锁，失败无状态机回退。完整说明与API字段来源见[QQ_OFFICIAL.md](QQ_OFFICIAL.md#llm-参谋与自然语言下令)。

主合并回归llm-release.xml为423通过/0失败/0跳过，108.283秒。随后仅Bot默认模型由旧全局别名改为账户当前可用deepseek-flash，llm-client-current-model.xml单文件84通过；全局模型配置未改。各批不累加，安全摘要见[validation-summary.json](evidence/validation-summary.json)。客户端初版1个负例误将任意str航程当结构错误，修正为缺必填ship_id，语义仍留原引擎裁决；该初失败无XML，不伪造收据。

[真实模型副本验证](evidence/llm-live-smoke.json)调用DeepSeek普通API共2次，战报2.067秒/3789tokens，订单0.729秒/8409tokens；不读取或存储私有推理。正式库只读复制至内存，实际炮战版本4经明确自然语言单炮位命令在副本推进到5，重复事件不再调用模型或推进，正式行摘要不变。QQ平台发送全部MockTransport，含回图，不能称实群执行。

用户反馈“两条都正常”；实际官方群日志有参谋与两次下令回复成功。正式LLM收据为战报1次、下令澄清2次，均未提交，没有新PNG投递标签。第一次混合炮击/移动/雷击阶段要求，第二次仅说推进阶段；应记录为战报及澄清成功，不假称实群已推进。[实群收据](evidence/qq-llm-live.json)。当前好友/群各10条预设保存重载核验，见[面板](evidence/qq-llm-panel.json)。后续用户要求管理员裁判完整对局权限，另批开发，不把该需求当旧下令已支持。

该批当时的包68229020字节/128成员，SHA256 758f342812a9ac1bf9857f71f0f8147b0d9d143fe4f19524e455345cb7917831，5来源OID核验。Bot/Nginx/旧游戏/大厅active，bot健康200；凭据仅服务器私有env，公开证据无原始身份或聊天。

### PVE 群图与可操作的手动草稿（5bc33acc）

用户实际反馈推翻了“收到 PNG 与提示即可操作”的假设：PVE 仍取双方观察交集，因本方真实 ID 与敌方观察别名不同，实局交集为 0 艘；`/行动` 发送整个嵌套 schema 超过被动回复上限，旧舰 ID 筛选还错误匹配顶层动作。没有据此改引擎识别规则。PVE 群图改用唯一人类席位的受限观察，PVP 保持交集并增加空图提示；菜单从本方提示构造代表选项，选择进入持久私有草稿，原引擎负责最终提交校验。未选动作不代填。

最终同一源码快照 [manual-group-release.xml](../../artifacts/bot-20261022/manual-group-release.xml) 为 **289 passed / 0 failed / 0 skipped**。覆盖两模式/两阵营 PVE 投影和隐藏负例、PVP 交集、席位与群隔离、分页/筛选、选择/替换/清空不推进、草稿重启恢复、多实例修改草稿后拒绝旧提交、当前版本校验与幂等、旧 JSON 与 OneBot 兼容。详细计数与原始收据摘要见 [validation-summary.json](evidence/validation-summary.json)，各批不累加。

部署后 [manual-group-server-smoke.json](evidence/manual-group-server-smoke.json) 验证 10 个源码摘要。正式数据库以只读连接备份至内存，使用现有绑定的实际版本 4 / 炮战阶段，群图渲染 8 艘玩家可见船，经过原 QQ 路由模拟群战况、私聊行动、选择、草稿、提交及重复消息；副本从版本 4 推进到 5，正式对局行摘要前后相同。行动回复为 434 字符/1 条，选择 120 字符，草稿 128 字符，提交 2 条含本方 PNG。所有平台发送为 MockTransport，不是实群确认。初次烟测脚本为同一消息 ID 生成了不同时间戳，被防重放检查拒绝；修正为重放完全相同事件后通过，此次夹具失败不计为产品推进失败。

实际版本 4 群图保存在本地 [manual-group-live-before.png](../../artifacts/bot-20261022/deploy/manual-group-live-before.png)，已视觉核验有带名称舰船；不上传用户对局图或原始身份。另有两模式/两阵营重置测试图及 PVP 空交集图，摘要见 [pve-group-map-render-evidence.json](evidence/pve-group-map-render-evidence.json)，它们不是实际玩家局。当前官方路径已切换；停用的旧 OneBot 异步队列仍保留历史公共交集策略。

控制台好友与群聊各 10 个预设保存、重载核验；好友新增选择/草稿/提交/清空入口，原建议/确认仍可直接输入。证据见 [qq-manual-panel.json](evidence/qq-manual-panel.json)。本版真实客户端群图、选择与草稿已请求用户复测，尚未用旧版确认代替。菜单并未穷举自定义重组、照明/烟幕等全部动作，详见 [手动流程与边界](QQ_OFFICIAL.md#手动选择检查与提交)。

运行包 68,218,771 字节，SHA256 `6053b6023f53103b1026d8d8e023008ef0beeec8376e6fa5cc95cabb03b3a5d2`，5 个原始来源均与 HEAD LFS OID 一致。独立 bot、Nginx、旧游戏与大厅服务均 active，13192/8001/4180 对应探针返回 200；未重启旧玩家服务。

### 斜杠预设与详细推进引导（110c4a43，历史快照）

控制台已保存群聊 10 条、好友 8 条斜杠预设，好友底部另有 3 个只读菜单；重载后存在且无未保存改动，见 [qq-command-panel.json](evidence/qq-command-panel.json)。当前控制台显示每场景上限 10 条，不能把历史文档的上限直接当本应用实际能力。用户随后在真实 QQ 私聊中确认「列表和推进提示都有」，实际 `/下一步` 回调与回复计数见 [qq-shortcuts-live.json](evidence/qq-shortcuts-live.json)。此确认不外推为全部预设的全模式终局测试。

最终相关快照 [qq-shortcuts-release.xml](../../artifacts/bot-20261022/qq-shortcuts-release.xml) 为 **144 passed / 0 failed / 0 skipped**：网关 36、工厂 6、引导 36、短路由 46、真实绑定/引擎/重启 2、既有身份绑定 18。涵盖允许群与 App/席位隔离、多局不猜默认、明确版本门槛、无版本自动/确认只读、提交 JSON 保真、公开元数据白名单、PVP 等待与终局不误导提交。真实引擎两模式在隔离 SQLite 中通过绑定、首阶段提交、路由重建/数据库重开、旧事件重发不重复推进和真实 PNG；平台网络为 MockTransport，未向 QQ 用户发送测试消息。

服务器部署后，[qq-shortcuts-server-smoke.json](evidence/qq-shortcuts-server-smoke.json) 从正式库只读备份到内存，使用实际已绑定席位验证短 `/下一步`、`/态势`、无版本 `/自动` 与 `/帮助 推进`；回复走模拟平台，未向真实用户额外发消息。正式对局行摘要和内存版本均未改变，用户局仍 revision 1 / 增援。此证据证明已部署代码可解析现有绑定；后续用户的真实客户端确认另列，不与模拟平台烟测混淆。

中途失败保留：[qq-shortcuts-initial.xml](../../artifacts/bot-20261022/qq-shortcuts-initial.xml) 为 68 passed / 4 failed，旧断言要求英文 JSON 键 `match_id`，与本轮改为中文状态说明的显示契约冲突；后续断言改为实际对局编号仍可见，解析与席位断言保留。[qq-shortcuts-real-core.xml](../../artifacts/bot-20261022/qq-shortcuts-real-core.xml) 为 0 passed / 2 failed，测试夹具误把既有 URL-safe 验证码当十六进制；修正夹具后 [qq-shortcuts-real-recheck.xml](../../artifacts/bot-20261022/qq-shortcuts-real-recheck.xml) 2 passed。最终 144 项在上述修正与多局手动提示明确化后运行，旧失败不改写。

### 此前官方协议与安全绑定收据

- [identity-links.xml](../../artifacts/bot-20261022/identity-links.xml)：31 passed，29.504 秒，其中新绑定 18 项、既有服务 13 项。覆盖同 raw 值不同域、AppID/群隔离、错误作者不消费、过期、绑定冲突、8 个活码上限、稳定私聊收据、重启、双实例原子消费及真实别名席位/提交幂等。
- [qq-official-protocol-pass.xml](../../artifacts/bot-20261022/qq-official-protocol-pass.xml)：35 passed，0.477 秒，其中网关 30 项、工厂/配置兼容 5 项。覆盖签名/时间窗、挑战限制、两类事件、群发现/白名单、消息幂等、回复次数与完整 JSON 超限拒发、私聊绑定及图片流程。
- [official-discovery-final.xml](../../artifacts/bot-20261022/official-discovery-final.xml)：最终官方批次 36 passed，0.523 秒，其中网关 30 项、工厂/发现 6 项；新增持久化合法空白名单群发现，未验签事件不得写入记录。
- [official-live-audit.xml](../../artifacts/bot-20261022/official-live-audit.xml)：36 passed，0.582 秒，核验静态命令结果与投递标签，不记录命令正文、用户身份、密钥或原始错误。
- [official-compact-command.xml](../../artifacts/bot-20261022/official-compact-command.xml)：42 passed，0.715 秒，增加普通/编队与大小写 PVE/PVP 连写、原空格命令及错误参数覆盖。此为当前连写修复快照的定点验证，各批不相加。
- [official-app-compat.xml](../../artifacts/bot-20261022/official-app-compat.xml)：兼容批次 70 passed，2.379 秒，分项为既有 HTTP/通知 9、当时官方工厂 5、OneBot 56；该批次早于新增第 6 项发现测试，不与最终 36 项相加。
- [qq-official-core-integration.json](../../artifacts/bot-20261022/qq-official-core-integration.json)：真实 Python 引擎、群创建/加入、私聊申请码→群持有人确认、别名取得原席位、本方 PNG、自动命令及重复消息不再次推进、公共图均有本地联通证据；网络完全为 `httpx.MockTransport`，3 张图经模拟上传，未向真实平台广播。

### 保留的公开签名示例失败

[qq-official-signature-evidence.json](../../artifacts/bot-20261022/qq-official-signature-evidence.json) 记录首轮协议运行 29 passed / 1 failed；首轮没有生成原始 JUnit，不把后续文件冒充首轮记录。失败原因是官方公开文档所印签名不能验证其所印 timestamp/body，异常为 `InvalidSignature`。

[qq-official-documented-signature-failure.xml](../../artifacts/bot-20261022/qq-official-documented-signature-failure.xml) 是该示例的独立定点复现：0 passed / 1 failed，0.038 秒。官方公开的 32 字节公钥向量独立匹配，产品实现按官方 SDK 的种子派生及 timestamp+原始请求体校验；这项失败针对公开示例，不能称为产品真实回调失败，也不能被 35 项通过覆盖掉。本 App 后续真实平台挑战及群/C2C 业务验签已通过。示例来源：[官方 sign.md](https://github.com/tencent-connect/bot-docs/blob/main/docs/develop/api-v2/dev-prepare/interface-framework/sign.md)。

## 前一轮服务 / MCP / OneBot 测试与保留的失败

- [pytest.xml](../../artifacts/bot-20261022/pytest.xml)：145 passed，339.592 秒。包括 bot 服务、HTTP、OneBot、公共视角、MCP，以及编队、夜间识别、LLM 机动时钟相关测试。该批次是较早快照。
- [bot-release.xml](../../artifacts/bot-20261022/bot-release.xml)：115 passed，53.909 秒。包括 bot 各层与地图战报回归；与前批次交叉覆盖。
- [publish.xml](../../artifacts/bot-20261022/publish.xml)：123 passed、1 failed，402.611 秒。失败为编队双 MCP 演示超过当时 120 秒的进程预算。随后 [formation-recheck.xml](../../artifacts/bot-20261022/formation-recheck.xml) 同用例单独复验 1 passed，72.189 秒。
- [shipnames-final.xml](../../artifacts/bot-20261022/shipnames-final.xml)：122 passed、3 failed，646.025 秒。三个失败分别是双 stdio 协议检查超时，以及普通/编队真实引擎 MCP 子进程超过当时 120 秒预算。保留失败收据，不将其改写为全绿。
- [last-delta.xml](../../artifacts/bot-20261022/last-delta.xml)：1 passed、1 failed，15.276 秒。失败断言为待发队列意外为空：生产定时投递任务与测试手动检查竞争，队列已被后台任务投递。测试随后显式关闭定时泵、逐步调用投递，保留失败与后续通过两份证据。
- [final-fixes.xml](../../artifacts/bot-20261022/final-fixes.xml)：13 passed，187.497 秒。准确分项为 HTTP/通知 9 项、棋子舰名与中文排版 3 项、编队 MCP 1 项；不能称为 app/counter 单独 13 项。
- [mcp-release-recheck.xml](../../artifacts/bot-20261022/mcp-release-recheck.xml)：最终三个进程用例 3 passed，158.434 秒，包括两独立 stdio 会话及两模式真实引擎首回合。完整 CLI 子进程预算调整为 240 秒，双 stdio 检查预算为 120 秒；每次 MCP→HTTP 请求的 60 秒超时保持不变。调整的是整体进程验收预算，没有把超时视为游戏成功，也没有吞掉失败。
- [onebot-ingress-recheck.xml](../../artifacts/bot-20261022/onebot-ingress-recheck.xml)：最新 OneBot 入口复验 56 passed，0.968 秒。收据 SHA256 为 `4d6e43645dc117a85e2df2bd4747dd7596c641be4a519efad91b869d10df6ccc`。对应命令如下；本次整理文档时只读取收据，没有再运行测试。

```sh
.venv/bin/python -m pytest tests/test_bot_onebot.py \
  --basetemp=.pytest-tmp-qq-evidence \
  --junitxml=artifacts/bot-20261022/onebot-ingress-recheck.xml
```

以上为此前服务/MCP/OneBot 快照，XML 可核验测试名、计数与时长。真实引擎测试使用隔离 SQLite；OneBot 为真实签名解析与模拟动作 API 回执，未向真实 QQ 发消息。测试名中的 `real_qq_group` 指真实服务路径，不代表真实 QQ 群；也不能用它代替新官方网关的验证。

此前已覆盖固定令牌身份、席位/房间隔离、PVP 密封、失败不推进、持久幂等、公共视角交集，以及旧 OneBot 的持久队列、分页和单收件人失败处理。新官方路线只被动回复，不继承旧队列的异步广播承诺。MCP 错误只按允许的领域错误码给静态纠正提示，不返回任意后端错误正文。

## 服务器烟测与运行来源

[server-smoke.json](../../artifacts/bot-20261022/deploy/server-smoke.json) 记录服务器独立 bot HTTP 服务使用现有 Python 引擎、`IBS-S-03`、PVE 状态机完成的两组五阶段烟测：

- 普通模式依次经过增援、机动规划、鱼雷规划、炮击、下一回合增援；最终第 2 回合机动规划，revision 5，2.62 秒；PNG 118,821 字节，SHA256 `6b4f334090248a9037e349459b857123d1a0eac9f6611a03cac375d9c6d6063b`。
- 编队模式依次经过编队部署、增援、机动规划、鱼雷规划、炮击；最终第 2 回合增援，revision 5，2.24 秒；PNG 119,162 字节，SHA256 `13a7add64127b6a11087a289f197976c9902915a385045f6e9c200f0ee5bad2d`。

这两组烟测验证服务器引擎、阶段推进与 PNG 响应；没有经过真实 QQ 事件入口，也不证明完整终局或 LLM 战术能力。

### 服务器 SSH MCP 端到端

[ssh-mcp-smoke.json](../../artifacts/bot-20261022/deploy/ssh-mcp-smoke.json) 记录两个独立官方 MCP 会话经 SSH→服务器会话启动器→共享 HTTP 服务的实际调用；使用非 QQ 房间、PVP、确定性状态机建议：

- 普通模式双方完成一个阶段，revision 1，进入机动规划；返回 PNG 122,803 字节，SHA256 `e51d6ffbb0620a6720cd8004847b63cc00e076e112ebc9643a66f60c3614ca6f`。
- 编队模式双方完成一个阶段，revision 1，进入增援；返回 PNG 109,584 字节，SHA256 `f12558e406f65d296d2fe6dc270b46772a9ac4d5da542515d509fa5260a49faa`。

服务器安装官方 MCP SDK 1.30.0，`pip check` 终端检查通过。入口为 `/opt/ibs-bot/.venv/bin/python /opt/ibs-bot/mcp-session.py blue|red`，服务器内部注入固定身份令牌，不向标准输出写令牌；来源是 [bot_mcp_remote.py](../../scripts/bot_mcp_remote.py)。无令牌本地配置见 [mcp-ssh-config.json](../../artifacts/bot-20261022/deploy/mcp-ssh-config.json)，使用者须已有可用的 `MyAliyunServer` 别名与密钥；部署命令见 [README.md](README.md#两个-mcp-客户端)。后续启动器增加可配置的固定身份选择，默认仍是 `agent:blue/red`；该历史烟测不是新官方 QQ 人类席位的冒领或实群验证。

这项证据新增了真实 SSH 和远端官方 MCP 进程验证；它没有经过 QQ 房间、真实 QQ 事件或 LLM 自主决策，也没有跑完整终局。

### 来源与运行包

部署曾缺少原始 LFS 来源；仅传结构化文件不能满足规则快照的来源核验。补齐后，[runtime-sources.json](../../artifacts/bot-20261022/deploy/runtime-sources.json) 记录以下 5 个原始文件的 SHA256（路径均相对 `resources/originals/`）：

- `rules/iron-bottom-sound-iv-rules-zh.pdf`：`0f14cbf1dee747d14e1fb52db77a4fff440076b2a96826f4299faa60b45c573e`
- `rules/player-aid-tables-zh.pdf`：`0aae79ccc1ec699834e259d8818dbf48f66cbd077b19c34ed9570c6aff9b76bc`
- `scenarios/scenario-book-zh.pdf`：`c11394a7dda262dcafd17a647d3699426ba54c9e55f2a142704f094c31c1c813`
- `records/ship-record-manual-1.1-zh.pdf`：`eeff020db4a7f491def219335404996d4b204035923be2b5bd925f65dfdac210`
- `assets/images/岛屿.jpg`：`5b9cd594846235d829228a202a8a8bb320baf5b0b7ee84753725fb1986fc79fd`

后续运行包使用 [build_bot_release.py](../../scripts/build_bot_release.py)。它要求来源为完整文件，以当前仓库 `HEAD` 的 Git LFS OID 校验这 5 项，并输出来源与归档摘要。`--source-root` 可指定已有完整来源的另一仓库根目录；当前源码和结构化数据仍从当前仓库打包。命令见 [README.md](README.md#构建服务器运行包)。

手动版当时的 [ibs-bot-runtime.tar.gz](../../artifacts/bot-20261022/deploy/ibs-bot-runtime.tar.gz) 正向打包验证通过：68,218,771 字节、126 个成员，SHA256 `6053b6023f53103b1026d8d8e023008ef0beeec8376e6fa5cc95cabb03b3a5d2`；包含官方网关、手动草稿、斜杠/阶段引导、绑定与远端启动器，5 个原始来源摘要均匹配，不含私有环境配置或 `.pyc`。逐来源字节数和摘要见 [最终打包收据](../../artifacts/bot-20261022/deploy/ibs-bot-runtime.tar.gz.json)。这是运行包验证，不合并计为完整 QQ 对局验收。

[cleanup.json](../../artifacts/bot-20261022/deploy/cleanup.json) 保留服务器空间处理收据：清理 4 份旧 VSCode Server 运行缓存与扩展下载缓存，释放 3,020,009,472 字节，清理后可用 3,689,418,752 字节。当前两份 VSCode Server、用户配置、已安装扩展及项目/对局均列为保留项；该容量是清理时快照，不代表安装镜像后的当前剩余空间。

[official-switch-cleanup.json](../../artifacts/bot-20261022/deploy/official-switch-cleanup.json) 是改走官方平台后的另一笔清理：仅删除本任务已停止的 NapCat 容器及可重建固定镜像，保留宿主账号/配置挂载和其他服务。该次释放 1,707,474,944 字节，之后可用 3,303,755,776 字节（约 3.08 GiB）。它不并入前一次约 2.81 GiB 的缓存释放结果；两次空间快照之间还发生过部署写入。

## 历史 NapCat 分支

改用官方平台之前，普通 QQ 账号在 NapCat 扫码后返回安全限制 168。[qq-login-block.json](../../artifacts/bot-20261022/deploy/qq-login-block.json) 保留 `qrcode_scanned`、`core_ready: false` 与错误码，不能回写为登录成功。此前可读的账号/群元数据不足以证明在线；当时不收消息是否同一原因只可能相关，未证实。

用户随后明确改用 AppID/AppSecret 官方机器人。NapCat 已停止、临时探针已还原；这项普通账号限制不再是当前路线的前提或阻断，不要求先修复它才能联调官方应用。

## 官方实群与真实 LLM agent 对战未完成项

真实平台握手、群/C2C 回调、群发现/白名单、编队 PVE 建局、群持有人确认私聊绑定、首阶段推进、本方与群公共 PNG 的官方 API 回执及用户显示确认已完成。仍需其他模式的真实群对局、第二名真实群友加入 PVP、重启后真实续局及完整终局验证。官方主动推送已停止，验收按用户主动查询战况设计，不承诺双方完成就异步广播。

`bot_mcp_duel.py`、本地和远端双会话证据均为确定性状态机建议。尚无两个 LLM 自主制定战术、经 MCP 参与同一官方 QQ 对局并完整终局的证据。管理员配置 agent 房间或已绑定人类身份后，仍须实际验证对应席位权限及公开/私有图边界。
