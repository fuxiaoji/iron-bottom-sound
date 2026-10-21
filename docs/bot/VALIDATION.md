# QQ / MCP 验证记录（2026-10-22）

当前 QQ 路线为官方机器人「铁底湾指挥官」，AppID `1905878837`；NapCat 已停止，临时探针已还原。本记录区分官方协议/绑定验证、不同代码快照上的历史回归、服务器引擎烟测和真实 QQ 联调。各批次交叉覆盖，不把通过数相加；旧全批通过不代表所有后续改动已在同一最终快照全量通过。

GitHub 审查入口为 [validation-summary.json](evidence/validation-summary.json)，保留各批 raw XML 的 SHA256、计数与失败测试名，不发布原始错误正文或环境配置。安全部署副本包括 [鉴权](evidence/official-auth.json)、[回调](evidence/official-callback.json)、[PVE 烟测](evidence/server-smoke.json)、[SSH MCP 烟测](evidence/ssh-mcp-smoke.json)、[来源](evidence/runtime-sources.json)、[运行包清单](evidence/ibs-bot-runtime.tar.gz.json)、[缓存清理](evidence/cleanup.json) 和 [切换清理](evidence/official-switch-cleanup.json)。完整 raw XML、PNG、截图及运行包二进制留本地 `artifacts/bot-20261022/`，不入 Git；本文原始产物链接用于本地核验。

## 官方方案：已验证与仍待验收

按用户指示创建应用，AppSecret 由用户本人重置后，服务器完成私有配置与官方 token 交换。平台已保存 Webhook 地址 `https://fuwenji.asia/ibs-bot/qq-official/events`；01:33:36 的真实平台 HTTP 挑战返回 200，服务记录 `challenge_signed`，腾讯平台验证回调并成功保存。验收依据为平台成功保存与服务端挑战记录，见 [official-callback.json](../../artifacts/bot-20261022/deploy/official-callback.json)。服务器伪造业务探针为 401，GET 为 405；旧游戏服务同时返回 200。官方网关/绑定功能提交为 `65eb4c8ba944ed1cc64c7eeb528ec2340165be48`，8 个已部署源码与该提交的摘要匹配。

上述结果证明应用鉴权及真实平台地址验证已经联通，不等于真实消息回调或群图回复通过。`GROUP_AT_MESSAGE_CREATE`、`C2C_MESSAGE_CREATE` 两项订阅已保存。白名单为空，仅从合法群事件发现真实 `group_openid`，私有表 `bot_official_groups` 只存应用、群 OpenID 和最后发现时间，不存正文、发送者或命令；管理员后台取值，无需用户转抄。当前该应用真实发现记录为零，没有把数字群号猜成 OpenID。

官方机器人二维码已交给用户，等待用户添加新机器人并真实 @，再完成白名单、群创建/加入、C2C 绑定、私聊推进/PNG 和群公共战况查询。当前未认证应用的管理员/群主范围与后续个人认证说明见 [QQ_OFFICIAL.md](QQ_OFFICIAL.md)。普通 QQ 账号历史限制 168 不再作为这条路线的阻断。

### 官方协议与安全绑定收据

- [identity-links.xml](../../artifacts/bot-20261022/identity-links.xml)：31 passed，29.504 秒，其中新绑定 18 项、既有服务 13 项。覆盖同 raw 值不同域、AppID/群隔离、错误作者不消费、过期、绑定冲突、8 个活码上限、稳定私聊收据、重启、双实例原子消费及真实别名席位/提交幂等。
- [qq-official-protocol-pass.xml](../../artifacts/bot-20261022/qq-official-protocol-pass.xml)：35 passed，0.477 秒，其中网关 30 项、工厂/配置兼容 5 项。覆盖签名/时间窗、挑战限制、两类事件、群发现/白名单、消息幂等、回复次数与完整 JSON 超限拒发、私聊绑定及图片流程。
- [official-discovery-final.xml](../../artifacts/bot-20261022/official-discovery-final.xml)：最终官方批次 36 passed，0.523 秒，其中网关 30 项、工厂/发现 6 项；新增持久化合法空白名单群发现，未验签事件不得写入记录。
- [official-app-compat.xml](../../artifacts/bot-20261022/official-app-compat.xml)：兼容批次 70 passed，2.379 秒，分项为既有 HTTP/通知 9、当时官方工厂 5、OneBot 56；该批次早于新增第 6 项发现测试，不与最终 36 项相加。
- [qq-official-core-integration.json](../../artifacts/bot-20261022/qq-official-core-integration.json)：真实 Python 引擎、群创建/加入、私聊申请码→群持有人确认、别名取得原席位、本方 PNG、自动命令及重复消息不再次推进、公共图均有本地联通证据；网络完全为 `httpx.MockTransport`，3 张图经模拟上传，未向真实平台广播。

### 保留的公开签名示例失败

[qq-official-signature-evidence.json](../../artifacts/bot-20261022/qq-official-signature-evidence.json) 记录首轮协议运行 29 passed / 1 failed；首轮没有生成原始 JUnit，不把后续文件冒充首轮记录。失败原因是官方公开文档所印签名不能验证其所印 timestamp/body，异常为 `InvalidSignature`。

[qq-official-documented-signature-failure.xml](../../artifacts/bot-20261022/qq-official-documented-signature-failure.xml) 是该示例的独立定点复现：0 passed / 1 failed，0.038 秒。官方公开的 32 字节公钥向量独立匹配，产品实现按官方 SDK 的种子派生及 timestamp+原始请求体校验；这项失败针对公开示例，不能称为产品真实回调失败，也不能被 35 项通过覆盖掉。本 App 后续真实平台挑战已通过；真实群业务验签仍需合法消息收据。示例来源：[官方 sign.md](https://github.com/tencent-connect/bot-docs/blob/main/docs/develop/api-v2/dev-prepare/interface-framework/sign.md)。

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

最终官方版 [ibs-bot-runtime.tar.gz](../../artifacts/bot-20261022/deploy/ibs-bot-runtime.tar.gz) 正向打包验证通过：68,202,363 字节、124 个成员，SHA256 `027a9e383b5f23cdd5b7f6d7c7aeb2d3a4eb7d75d83be1bff9043a8355ba2e8a`；包含本轮官方网关、绑定与远端启动器，5 个原始来源摘要均匹配，不含私有环境配置或 `.pyc`。逐来源字节数和摘要见 [最终打包收据](../../artifacts/bot-20261022/deploy/ibs-bot-runtime.tar.gz.json)。这是运行包验证，不合并计为完整 QQ 对局验收。

[cleanup.json](../../artifacts/bot-20261022/deploy/cleanup.json) 保留服务器空间处理收据：清理 4 份旧 VSCode Server 运行缓存与扩展下载缓存，释放 3,020,009,472 字节，清理后可用 3,689,418,752 字节。当前两份 VSCode Server、用户配置、已安装扩展及项目/对局均列为保留项；该容量是清理时快照，不代表安装镜像后的当前剩余空间。

[official-switch-cleanup.json](../../artifacts/bot-20261022/deploy/official-switch-cleanup.json) 是改走官方平台后的另一笔清理：仅删除本任务已停止的 NapCat 容器及可重建固定镜像，保留宿主账号/配置挂载和其他服务。该次释放 1,707,474,944 字节，之后可用 3,303,755,776 字节（约 3.08 GiB）。它不并入前一次约 2.81 GiB 的缓存释放结果；两次空间快照之间还发生过部署写入。

## 历史 NapCat 分支

改用官方平台之前，普通 QQ 账号在 NapCat 扫码后返回安全限制 168。[qq-login-block.json](../../artifacts/bot-20261022/deploy/qq-login-block.json) 保留 `qrcode_scanned`、`core_ready: false` 与错误码，不能回写为登录成功。此前可读的账号/群元数据不足以证明在线；当时不收消息是否同一原因只可能相关，未证实。

用户随后明确改用 AppID/AppSecret 官方机器人。NapCat 已停止、临时探针已还原；这项普通账号限制不再是当前路线的前提或阻断，不要求先修复它才能联调官方应用。

## 官方实群与真实 LLM agent 对战未完成项

真实平台地址握手与两类消息订阅保存已完成；仍需合法群/C2C 回调、真实群 OpenID、白名单、群建局、群持有人确认私聊绑定、本方图与公共战况的官方 API 成功回执，以及重启后续局验证。官方主动推送已停止，验收应按用户主动查询战况设计，而非承诺双方完成就异步广播。

`bot_mcp_duel.py`、本地和远端双会话证据均为确定性状态机建议。尚无两个 LLM 自主制定战术、经 MCP 参与同一官方 QQ 对局并完整终局的证据。管理员配置 agent 房间或已绑定人类身份后，仍须实际验证对应席位权限及公开/私有图边界。
