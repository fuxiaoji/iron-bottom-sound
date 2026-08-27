# 多模态 LLM 接口

## 数据流

每次 LLM 对手下令均由服务端完成以下只读投影：

1. `engine.observe(game_id, side)` 生成绑定阵营的 `PlayerObservation`。
2. `export_frame`、`render_board` 和 `render_map_image` 从同一观察生成结构化世界态、文字棋盘和 PNG 地图。
3. `engine.legal_actions(game_id, side)` 生成当前阶段合法动作及 Schema。
4. OpenAI-compatible 请求把 JSON 文字放在 `content[type=text]`，把 PNG Data URL 放在 `content[type=image_url]`。
5. 返回的 `AIPlanSheet.orders` 经 Pydantic 和规则引擎再次校验；LLM 永远不能直接修改状态。

禁止使用浏览器全屏截图。浏览器中可能同时存在玩家草稿、调试图层、战报入口和上一阵营缓存；服务端观察渲染器只接触规则核心已过滤的数据。

## 供应商配置

| provider | endpoint | 环境变量回退 | 特殊参数 |
|---|---|---|---|
| `deepseek` | `https://api.deepseek.com` | `DEEPSEEK_API_KEY` | 支持现有 `thinking` 开关 |
| `zhipu` | `https://open.bigmodel.cn/api/paas/v4` | `ZHIPU_API_KEY` | 不发送 DeepSeek 专属 `thinking` 字段 |

玩家也可在 UI 手动填写模型 ID。适配器原样发送模型名；供应商拒绝时返回脱敏的 HTTP 状态与错误摘要，不静默替换模型。

智谱官方 OpenAI 兼容说明与图像消息格式：

- <https://docs.bigmodel.cn/cn/guide/develop/openai/introduction>
- <https://docs.bigmodel.cn/cn/guide/develop/python/introduction>

当前官方视觉示例使用 `glm-5v-turbo`。`glm-5.3-flash` 是用户要求的试验模型名，尚未在上述官方文档中得到视觉能力确认，必须以真实端点响应为准。

## 密钥边界

- 浏览器使用 `password` 输入，React 状态仅存在当前页面内存。
- 后端 `_user_llm_keys` 仅存在当前 Python 进程内存，重启即清。
- 密钥不进入 `GameState`、SQLite、事件、战报、审计对象或 Git。
- 请求错误只记录供应商状态码和至多 240 字错误消息；不序列化请求头。
