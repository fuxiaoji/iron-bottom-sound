# 铁底湾指挥官：QQ 开放平台接入

当前官方机器人为 **铁底湾指挥官**，AppID `1905878837`。用户本人已重置 AppSecret，服务器私有配置与 token 交换完成，安全元数据见 [鉴权收据](evidence/official-auth.json)；文档和本地 MCP 配置不包含 AppSecret 或 access_token。本地另存[创建截图](../../artifacts/bot-20261022/deploy/official-bot-created.png)，图片不入 Git。

## 平台配置与验收边界

QQ 平台及官方 SDK 默认使用 WebSocket，本项目实现 HTTP Webhook。控制台已保存回调：

```text
https://fuwenji.asia/ibs-bot/qq-official/events
```

反向代理转至独立 bot 服务的 `POST /qq-official/events`。真实平台地址验证返回 200，腾讯平台已验证并成功保存回调；伪造业务请求为 401，GET 为 405，见 [平台回调收据](evidence/official-callback.json)。地址验证成功不等于真实群事件、建局和图片回复已通过。

只订阅 `GROUP_AT_MESSAGE_CREATE`、`C2C_MESSAGE_CREATE`，当前界面 2/54 事件已保存。环境变量为 `IBS_QQ_APP_ID`、`IBS_QQ_APP_SECRET`、`IBS_QQ_ALLOWED_GROUPS`，密钥只留服务器私有配置。协议依据见 [官方 Webhook 文档](https://github.com/tencent-connect/bot-docs/blob/main/docs/develop/api-v2/dev-prepare/interface-framework/event-emit.md)。

当前未认证应用的控制台提示：仅管理员使用，只能加入管理员为群主的群；用户提供的目标群界面显示自己为群主。个人认证后可设置公开使用，页面提示机器人进群数量上限为 **500 个群**，不是单群人数。认证须用户本人在平台完成，本项目没有代办或宣称已完成认证。

### 先发现真实群 OpenID

白名单为空时是受限发现模式：经签名验证的群 @ 事件只获得该事件的真实 `group_openid` 回复，不建局、不执行战术命令；C2C 业务暂不处理。服务将合法发现写入私有 SQLite 表 `bot_official_groups`，仅含 `app_id`、`group_openid`、`last_seen`，不保存消息正文、发送者或命令。管理员从后台记录选取正确群、配置 `IBS_QQ_ALLOWED_GROUPS` 并重启，无需让用户转抄群号；未认证/未验签事件不能生成这项发现记录。

数字 QQ 群号、AppID 和用户 QQ 号都不能代替 `group_openid`。当前真实群 @ 已验签、回复并完成唯一目标群授权；编队 PVE 建局、私聊与群内确认绑定、首次私聊自动阶段提交、本方 PNG 与群公共 PNG 的官方 API 回执已验证，用户确认两处都有图。群和成员原始 OpenID 不公开，安全摘要见 [实群收据](evidence/official-live.json)。

## 从群创建到私聊操舰

### 斜杠预设与分步帮助

控制台「高级设置 → 菜单与指令」已保存好友 8 条、群聊 10 条原生指令，好友底部还配置「帮助／态势／下一步」3 个只读菜单；页面重载后均保留，当前界面每场景最多 10 条。原生面板在 QQ 输入 `/` 唤起，见 [官方指令面板说明](https://github.com/tencent-connect/bot-docs/blob/main/docs/README.md#912-指令配置)。配置收据见 [qq-command-panel.json](evidence/qq-command-panel.json)；用户已确认实际 QQ 私聊中列表与详细推进提示均可见，见 [实测收据](evidence/qq-shortcuts-live.json)。

群预设 `/编队人机`、`/普通人机`、`/编队对战`、`/普通对战` 分别创建对应 PVE/PVP；群里仍需真正 @机器人。`/我的对局` 查询本人参加的对局，`/战况` 在本人唯一未结束对局时可省 ID；旁观者或多个对局请用 `/战况 对局ID`。

绑定后可直接私聊：

```text
/下一步
/态势
/自动 版本号 [对局ID]
/确认 版本号 [对局ID]
/行动 [对局ID] [舰ID]
/建议 [对局ID]
/提交 版本号 对局ID {"side":"allies","phase":"reinforcement"}
```

方括号表示可选参数，实际发送不含括号。只有唯一未结束对局时可省 ID；`/提交 版本号 JSON对象` 也要求唯一对局。只有已绑定、已拥有且属于当前应用允许群的席位才能被短命令找到；不同群/App/用户不能借短命令访问。多个对局时明确选择，不使用最近一局作为隐式默认。

`/下一步` 解释当前阶段并给出含实际版本和对局 ID 的可复制指令；`/自动`、`/确认` 不带版本时仅显示引导，不提交。`/自动` 指离线状态机，不是 LLM。PVP 已封存时只等待并刷新，终局不再提示提交。每次成功只推进一个决策阶段，同一回合可以多次更新版本；不得把阶段版本当回合号。

`/帮助` 为快速入口；专题 `/帮助 快速开始`、`/帮助 推进`、`/帮助 手动`、`/帮助 PVP`、`/帮助 绑定` 解释绑定、双方封存、自己下令及旧完整格式。斜杠与旧「铁底湾」前缀均兼容。

### 完整格式与首次绑定

以下流程要求真实群已在 OpenID 白名单内。群命令均需真实 @ 当前机器人。

1. 在群中创建或加入，创建者占所选一方，PVP 另一人加入另一方：

   ```text
   @铁底湾指挥官 铁底湾 创建 普通 pvp IBS-S-03 盟军
   @铁底湾指挥官 铁底湾 创建 编队 pve IBS-S-03 日军
   @铁底湾指挥官 铁底湾 加入 对局ID
   ```

   可省略「铁底湾」前缀，也支持「创建 编队pve」「创建 普通PVP」这种模式与对手连写；想定和阵营仍按上面的空格分隔。

2. 保存回复中的真实群 OpenID 和对局ID，私聊机器人申请自己实际席位的绑定：

   ```text
   铁底湾 群openid 对局ID 绑定 盟军
   铁底湾 群openid 对局ID 绑定 日军
   ```

3. 绑定码只在私聊返回；该席位本人到对应群确认：

   ```text
   @铁底湾指挥官 铁底湾 绑定 私聊获得的验证码
   ```

4. 绑定成功后私聊查看本方图、合法行动，再提交本阶段命令：

   ```text
   铁底湾 群openid 对局ID 态势
   铁底湾 群openid 对局ID 行动
   铁底湾 群openid 对局ID 行动 舰ID
   铁底湾 群openid 对局ID 建议
   铁底湾 群openid 对局ID 自动 版本号
   铁底湾 群openid 对局ID 确认 版本号
   铁底湾 群openid 对局ID 提交 版本号 {"side":"allies","phase":"reinforcement"}
   ```

「态势」返回当前版本、阶段、战况与本方 PNG；「自动」明确使用状态机建议并返回本方 PNG；「建议」不会提交。版本号来自最新态势。手动 `orders` 为引擎 OrderBatch 对象，字段以合法行动/schema 为准。普通模式逐舰下令，编队模式先部署，再用 `formation_movement` 等字段。「确认」为空命令，只有引擎认可时才通过。

PVP 双方使用相同阶段版本；第一方封存后等待，第二方完成后统一推进。另一方须重新私聊「态势」查询结果，不等待异步通知。群公共图也主动查询：

```text
@铁底湾指挥官 铁底湾 战况 对局ID
@铁底湾指挥官 铁底湾 状态 对局ID
```

公共图为双方观察交集，开局可能只有地形；不把一方本方图发给全群。群中发「态势/行动/提交」会提示改用私聊。来源不完整而被引擎阻断的想定仍保持阻断，不由机器人补造规则。

## 身份域与 MCP

官方群事件使用 `author.member_openid`，C2C 使用 `author.user_openid`。同一 AppID 下同一用户跨群的 member OpenID 也不同，不把两个字段、数字 QQ 号或相同原始字符串自动合并，见 [唯一身份机制](https://github.com/tencent-connect/bot-docs/blob/main/docs/develop/api-v2/dev-prepare/unique-id.md) 与 [事件字段](https://github.com/tencent-connect/bot-docs/blob/main/docs/develop/api-v2/server-inter/message/send-receive/event.md)。服务使用：

```text
群席位：qqbot:1905878837:member:群openid:member_openid
私聊：  qqbot:1905878837:c2c:user_openid
房间：  qqbot:1905878837:群openid
```

绑定码固定私聊身份、AppID、群、已有对局、阵营与该席位实际群作者；只有相符的已验签群作者能消费。群友看到并抢发此码，也不能以自己的作者身份通过。有效期 300 秒，每个私聊身份最多 8 个未过期未使用码；过期后发一条新私聊消息重新申请。错误作者不消费，正确作者重复确认幂等，已有不同绑定不能被覆盖。绑定和业务收据持久化；群内确认回复不显示私聊身份。

这项绑定证明既有群席位持有人明确授权该 C2C 通道，不声称官方同账号身份兑换。公开 `union_openid` 文档是需特殊申请的频道关联应用能力，不是普通群成员到 C2C 的现成转换接口，见 [官方用户对象](https://github.com/tencent-connect/bot-docs/blob/main/docs/develop/api-v2/server-inter/channel/manage/user/model.md)。

服务层统一解析房间内绑定，因此 MCP 使用相同的已授权 C2C 固定身份也能操作原群席位。管理员在服务端 `IBS_AGENT_IDENTITIES` 中将独立随机令牌映射到已绑定 C2C，或来自已认证群事件的 member 身份；工具参数不接受身份或令牌，不用数字 QQ 号代替 OpenID。

SSH 启动器的 `IBS_MCP_BLUE_IDENTITY` / `IBS_MCP_RED_IDENTITY` 默认 `agent:blue` / `agent:red`。改为官方身份时，服务端须同时存在该身份对应的独立令牌映射。令牌只在服务器内部注入，不放本地 SSH MCP 配置。下面的 OpenID 是占位符：

```dotenv
IBS_MCP_BLUE_IDENTITY=qqbot:1905878837:c2c:USER_OPENID_A
IBS_MCP_RED_IDENTITY=qqbot:1905878837:c2c:USER_OPENID_B
```

默认两个 agent 也可在真实官方房间另建 PVP，再由群内「战况」查询公共图；它们不会自动拥有现有人类席位。实际权限仍由固定映射、显式绑定和游戏席位检查决定。

## 被动回复与输出上限

官方文档明确主动推送自 2025-04-21 停止。本实现只针对收到的消息被动回复：群消息 5 分钟内最多 5 次，C2C 60 分钟内最多 5 次。不继承旧 OneBot 的长期主动广播行为，见 [官方发送限制](https://github.com/tencent-connect/bot-docs/blob/main/docs/develop/api-v2/server-inter/message/send-receive/send.md)。

文本按最多 1,500 字符分片，PNG 占一条回复。若完整结果超过 5 条，完整 JSON 不发送，只回超限提示，不把截断 JSON 当可执行方案。可用「自动 版本号」、MCP 获取完整 JSON，或「行动 舰ID」缩小查询。操作可能已执行而回复受限，应重新查状态，不把未收到回复当成未提交。

游戏变更使用持久收据，重复事件不重复推进；官方回复分片/发送进度为进程内状态，重启可能重复一段回复，但不应重放游戏变更。单 worker、限时回复与失败处理不构成可靠的异步广播或离线通知承诺。

## 验证结果

安全绑定与既有服务 31 项通过；官方网关/工厂发现批次 36 项通过，增加连写命令及静态结果审计后 42 项通过。较早官方网关批次为 35 项通过，兼容批次 70 项通过，各批交叉覆盖不累加。真实引擎 MockTransport 联通测试与真实平台收据分别记录；实群目前已验证编队 PVE 建局、绑定、首次阶段推进、私聊本方图与群公共图的 API 投递，用户确认两处都有图。未据此宣称所有模式实群终局验收。

公开文档签名示例有单独保留的 1 项失败复现：公钥向量匹配，示例签名与所印正文不匹配。它不是产品真实回调失败；本 App 真实平台挑战已通过。GitHub 安全计数/失败测试名见 [批次摘要](evidence/validation-summary.json)，完整本地收据和未完成的群/C2C/LLM agent 终局见 [VALIDATION.md](VALIDATION.md)。
