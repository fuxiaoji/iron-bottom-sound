# 固定扩展海图（IBS-R-MAP-01）

状态：`tested`。这是项目稳定性扩展，不是《铁底湾的回响 IV》原版规则。

## 来源边界

- `IBS-M-MAIN` 原印刷地图仍为 A–HH、1–27；岛屿、海岸、视线和雷达遮挡资料只在该区域内有效。
- 通用规则 6.1.8 的印刷地图边缘处理保留在历史审计中，但运行时不再平移世界坐标。
- 用户要求以固定坐标和更大地图消除舰船、鱼雷、残骸、标记、历史航迹及封存计划在世界平移时不同步的故障面。

## 结构化定义

- 可玩区：A–TT、1–39，共 46×39 格。
- 原印刷区以外的新增格均为纯海，不产生新的陆地、海岸或雷达遮挡。
- 所有想定初始坐标保持不变；原先处于印刷地图南缘的 R27、U27 等格现在位于固定可玩区内部。
- 算子尝试越过最终可玩区边缘时留在当前格，并生成 `movement_blocked_by_edge`；其他算子及所有历史坐标保持不变。
- 事件使用 `coordinate_frame_changed: false` 明示没有坐标变换。旧回放中的世界平移事件仍可读取，但新对局不再产生该事件。

## 执行点与验证

- 模型边界：`models.HexCoord.neighbor`。
- 同步移动：`engine.IronBottomEngine._resolve_movement`。
- AI 边界/撤退：`llm.DeterministicCommander`、`realistic_command`。
- 呈现：`HexMap`、`state_export`、`battle_report`。
- 测试必须覆盖扩展坐标往返、印刷边缘可通行、最终边缘停车、其他算子坐标不变、无 `world_shifted` 事件和鱼雷航迹共线。
