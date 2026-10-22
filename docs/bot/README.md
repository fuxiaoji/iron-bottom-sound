# 铁底湾 QQ 官方机器人 / MCP

当前 QQ 入口为开放平台官方机器人 **铁底湾指挥官**，AppID `1905878837`。普通逐舰（`classic`）/编队（`formation`）、PVE/PVP 共用现有 Python 引擎和独立 SQLite 服务。PVE 使用 `TacticalCommander` / `RealisticCommander` 离线状态机，不消耗模型 API。

官方接入、精确指令、身份绑定及平台限制见 [QQ_OFFICIAL.md](QQ_OFFICIAL.md)，测试与失败收据见 [VALIDATION.md](VALIDATION.md)。NapCat 已停止、临时探针已还原；普通 QQ 账号的历史错误 168 不是当前官方路线的阻断。

GitHub 可审查的安全证据入口为 [测试批次摘要](evidence/validation-summary.json)、[实群验证](evidence/official-live.json)、[平台回调收据](evidence/official-callback.json) 与 [运行包来源清单](evidence/ibs-bot-runtime.tar.gz.json)。完整 raw XML、PNG、截图及运行包二进制留在本地 `artifacts/bot-20261022/`，不入 Git；下文这类本地产物链接需在本地工作区打开。

## 当前状态

已创建官方应用，用户本人重置 AppSecret 后完成服务器私有配置，token 交换成功。HTTPS 回调 `https://fuwenji.asia/ibs-bot/qq-official/events` 已保存并经腾讯平台验证通过，真实平台挑战返回 200；伪造业务请求返回 401。

`GROUP_AT_MESSAGE_CREATE` 和 `C2C_MESSAGE_CREATE` 两类消息订阅已保存。用户已把机器人加入目标群，真实群事件验签及官方回复成功；从事件发现的唯一群已配置白名单。真实「创建 编队pve」已建立编队 PVE，私聊申请码与群内确认完成同席位绑定；首次私聊「自动 0」已推进到 revision 1 / 增援阶段，本方 PNG 与随后群「战况」公共 PNG 均有腾讯 API 发送确认，用户也确认两处都有图。这证明首阶段实群链路，完整真实 QQ 对局及自主 LLM agent 对战尚未完成。

## 安装与启动

### 直接在 QQ 操作

群聊与私聊的原生 `/` 指令面板已在控制台保存并重载核验。群聊有帮助、四种开局、我的对局、战况、下一步、加入、绑定共 10 项；私聊有 8 项，底部菜单另有「帮助／态势／下一步」。用户已确认实际 QQ 私聊中「列表和推进提示都有」，手动发送同名命令也可使用。

完成一次私聊绑定后，直接发 `/下一步` 获取中文阶段、版本和可复制命令；`/态势` 返回本方图。若只有一个未结束对局，不再要求长串群 OpenID；有多个时须明确对局 ID，系统不猜默认。比如 `/自动 1 对局ID` 用状态机代填并提交一个决策阶段，成功后按新回复的版本继续。只发 `/自动` 或 `/确认` 是只读引导，不推进。

详细帮助为 `/帮助 快速开始`、`/帮助 推进`、`/帮助 手动`、`/帮助 PVP`、`/帮助 绑定`。PVP 已封存的一方只收到等待/刷新提示；终局不再提示提交。完整旧格式仍可用，群公共图继续只显示双方共同可见信息。配置摘要见 [预设面板](evidence/qq-command-panel.json)，服务器只读验证见 [短指令烟测](evidence/qq-shortcuts-server-smoke.json)。

### 服务端

在仓库根目录使用 Python 3.11+：

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[dev,bot]'
cp .env.example .env
```

服务端私有配置示例；AppSecret 占位值须替换为自己的现行配置：

```dotenv
IBS_BOT_DATABASE=backend/bot.sqlite3
IBS_QQ_APP_ID=1905878837
IBS_QQ_APP_SECRET=replace-with-current-app-secret
IBS_QQ_ALLOWED_GROUPS=
IBS_ONEBOT_SELF_ID=
IBS_AGENT_IDENTITIES={}
```

`IBS_QQ_ALLOWED_GROUPS` 填真实事件返回的 `group_openid`，多群用逗号分隔；数字 QQ 群号不能代替它。`IBS_ONEBOT_SELF_ID` 留空，不启动旧 OneBot 投递。需要 MCP 时，由管理员配置独立随机令牌到固定服务身份的映射；工具参数不接受身份或令牌。

```sh
.venv/bin/python -m uvicorn iron_bottom_sound.bot.app:create_app \
  --factory --host 127.0.0.1 --port 3192 --env-file .env --workers 1
```

内部路由为 `POST /qq-official/events`，反向代理提供上述 HTTPS 地址。此适配器使用 Webhook；平台默认 WebSocket 不能替代 Webhook 配置。被动回复进度为单进程内存状态，因此使用一个 worker；对局、提交收据和身份绑定持久保存在 SQLite。

本地示例健康检查为 `http://127.0.0.1:3192/health`；当前独立服务器内部端口为 `13192`。服务使用自己的 `bot_*` 表，不接入旧玩家数据库。中文地图可用 `IBS_REPORT_FONT=/绝对路径/中文字体文件` 指定字体。

## 两个 MCP 客户端

两个客户端各用一个固定身份，连接同一服务。工具有 `ibs_scenarios`、`ibs_matches`、`ibs_create`、`ibs_join`、`ibs_status`、`ibs_legal`、`ibs_suggest`、`ibs_submit`、`ibs_screenshot`。`side` 为 `axis` 或 `allies`，官方 QQ 房间为 `qqbot:1905878837:真实群openid`。

现有服务器可用 [无令牌 SSH 配置](../../artifacts/bot-20261022/deploy/mcp-ssh-config.json) 接入。每位 agent 只启用自己的一个条目，本机须已有 `MyAliyunServer` SSH 别名与密钥：

```json
{
  "mcpServers": {
    "iron-bottom-sound-blue": {
      "command": "/usr/bin/ssh",
      "args": ["-o", "BatchMode=yes", "MyAliyunServer", "/opt/ibs-bot/.venv/bin/python", "/opt/ibs-bot/mcp-session.py", "blue"]
    },
    "iron-bottom-sound-red": {
      "command": "/usr/bin/ssh",
      "args": ["-o", "BatchMode=yes", "MyAliyunServer", "/opt/ibs-bot/.venv/bin/python", "/opt/ibs-bot/mcp-session.py", "red"]
    }
  }
}
```

服务器内部选择令牌，标准输出只用于 MCP。启动器来源为 [bot_mcp_remote.py](../../scripts/bot_mcp_remote.py)，部署命令为：

```sh
scp scripts/bot_mcp_remote.py MyAliyunServer:/opt/ibs-bot/mcp-session.py
```

默认身份是 `agent:blue` / `agent:red`，可以在已知真实 OpenID 的官方房间新建一场 PVP，再让群内用户 @ 机器人查询公共战况；它们不会自动取得现有人类席位。代已授权的人类席位时，管理员需配置固定的官方 C2C/member 身份及匹配令牌，并同步 `IBS_MCP_BLUE_IDENTITY` / `IBS_MCP_RED_IDENTITY`，见 [身份与 MCP](QQ_OFFICIAL.md#身份域与-mcp)。

先读取 status、legal 和本方 PNG，再提交当前 `expected_revision` 与唯一 `request_id`；对手完成后主动查询新态势。`ibs_suggest` 和 [bot_mcp_duel.py](../../scripts/bot_mcp_duel.py) 使用确定性状态机建议；双会话烟测证明传输与裁决，不证明 LLM 自主对战。MCP 推进后官方 QQ 不异步广播，群内需主动查询「战况」。

## 构建服务器运行包

运行包需要以下 5 个完整原始来源，Git LFS 指针不能代替来源本体：

- `resources/originals/rules/iron-bottom-sound-iv-rules-zh.pdf`
- `resources/originals/rules/player-aid-tables-zh.pdf`
- `resources/originals/scenarios/scenario-book-zh.pdf`
- `resources/originals/records/ship-record-manual-1.1-zh.pdf`
- `resources/originals/assets/images/岛屿.jpg`

```sh
.venv/bin/python scripts/build_bot_release.py \
  --output artifacts/bot-20261022/deploy/ibs-bot-runtime.tar.gz \
  --source-root /绝对路径/已有完整原始来源的仓库
```

`--source-root` 指完整来源所在的仓库根目录，默认当前仓库。脚本以当前 `HEAD` 的 Git LFS OID 核验 5 项 SHA256，遇到指针或摘要不符即失败；源码和结构化数据仍从当前仓库打包，包含远程 MCP 启动器。旁边的 `.tar.gz.json` 记录来源与包摘要。私有配置、令牌、数据库和字体另行部署。

当前官方版 [本地运行包](../../artifacts/bot-20261022/deploy/ibs-bot-runtime.tar.gz) 为 68,202,363 字节、124 个成员，SHA256 `027a9e383b5f23cdd5b7f6d7c7aeb2d3a4eb7d75d83be1bff9043a8355ba2e8a`；5 个原始来源摘要核验通过，包含官方模块，不含私有环境配置或 `.pyc`。来源/归档收据见 [ibs-bot-runtime.tar.gz.json](evidence/ibs-bot-runtime.tar.gz.json)。

## OneBot 历史兼容

旧 `/onebot/events`、`IBS_ONEBOT_*` 和数字 `qq:群号` 路径保留兼容，其签名、私聊与持久通知队列测试属于历史证据。当前官方路线不启用 NapCat、不登录普通 QQ 账号，也不继承旧接口的主动广播行为。旧账号限制保留在 [历史记录](VALIDATION.md#历史-napcat-分支)，不作为当前操作步骤。
