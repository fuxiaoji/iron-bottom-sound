# 二马扩展想定规则审计

## 来源与身份

- 稳定想定 ID：`IBS-S-EM-01`
- 标题：第二次马里亚纳海战（内南洋水雷强袭战）
- 日期：1944-06-21；当前项目设定为 12 回合（原扩展资料为 8 回合）
- 想定来源：`resources/originals/extensions/erma/scenario/second-battle-of-the-philippine-sea-zh.pdf`（2 页）
- 船表来源：`resources/originals/extensions/erma/records/erma-ship-records-overview.png`（日军第 1 页、美军第 2 页）
- 原始路径、SHA-256、重复别名与页数由 `resources/originals/manifest.json` 和扩展内 `source-manifest.yaml` 追踪。

## 规则核验

| ID | 结构化内容 | 来源 | 审计状态 |
|---|---|---|---|
| `IBS-S-EM-01-R1` | 自由初设；日军在 A14–Q1 连线西北侧、美军在 R27–HH14 连线东南侧，连线格不含；各掷 1D6 高者先手；先大型舰、再小型舰交替布置；完成后从第 1 回合炮击阶段开始。 | 想定 PDF 第 1 页 | `verified_source → structured → executable(default setup) → tested` |
| `IBS-S-EM-01-R2` | 炮击命中表增加 101–120、121+ 两行，全部 18 个 D66 单元逐格转录。 | 想定 PDF 第 2 页 | `verified_source → structured → executable → tested` |
| `IBS-S-EM-01-R3` | 日军 3.9 英寸炮仍遵守 4 英寸炮射程限制；穿甲检定改用 3 英寸炮数据。 | 想定 PDF 第 2 页 | `verified_source → structured → executable → tested` |
| `IBS-S-EM-01-R4` | 第 8 回合结束计分：每 3 点舰体损失 1 分；BB 的 MFC、雷达、每座主炮各损失 1 分，每 2 点速力损失 1 分；领先 25 分胜，否则平局。 | 想定 PDF 第 2 页 | `verified_source → structured → executable → tested` |
| `IBS-S-EM-01-R5` | 将对局上限与 R4 的终局计分时点延后到第 12 回合；计分公式和 25 分门槛不变。此项是用户指定的项目扩展，不是原 PDF 内容。 | 用户需求，2026-08-27 | `structured → executable → tested` |

## 初设实现边界

来源允许玩家自由部署。当前 UI 为保证扩展导入后可立即开局，提供一组完全位于双方合法区域内的“引擎默认编队”，并在结构化想定的 `setup` 节保留完整区域、先手和交替顺序数据；默认格不是来源规定的唯一初设。后续自由部署编辑器必须读取同一 `setup` 数据，不得复制边界常量或把默认格误称为规则指定格。

2026-08-27 根据实机反馈把默认部署整理为双方各三支平行长纵队（主力舰、巡洋舰、驱逐舰），每队同航向、同航速并保存稳定成员顺序。该编组位于 `setup.engine_default_formations`，属于便利部署和 AI 协调元数据；玩家仍可依来源规则自由部署，编组不会改变任何碰撞、移动或射击裁决。

## 舰船与素材

- 24 艘逐舰记录使用 `resources/derived/structured/ships/extensions/erma.yaml`，与基础 30 艘记录分文件加载。
- 船体行数允许 3–5 行；炮位支持 `primary / secondary / tertiary`，避免把大和级 5 英寸高射炮或得梅因级 3 英寸炮误并入副炮。
- 鱼雷发射器的圆圈内横线按可发射数量、图标外横线按备雷数量逐项转录；鞍马的两舷与中轴发射器保持独立状态。
- 只导入普通舰船剪影；舰娘替代棋子不进入规范素材集。风云、长波、卷波三枚既有相同文件按 SHA-256 复用并登记新的原路径别名；扩展版大和与基础素材同名但哈希不同，使用 `日本-BB-大和-二马.png` 隔离，未覆盖基础想定棋子。

## AI 接入证据

扩展没有另写 AI。现有 `TacticalCommander` 继续只读取阵营观察和引擎合法动作，经 `OrderBatch` 提交。状态机 AI 现在对整批友舰航迹做逐脉冲同格/换位检查；`line` 风格让三支平行纵队执行共同舵令，并要求舰首保留下一回合净空；鱼雷推荐标注己方当前格与封存航路风险，AI 不选择风险组合。
