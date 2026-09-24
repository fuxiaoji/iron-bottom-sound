# 测试清单（v2.3 批次新增/修改）

## 新增测试文件

| 文件 | 覆盖 | 用例数 |
|---|---|---|
| `tests/test_command_delay_routing_v23.py` | IR-2 计划要求的 A–F：棋盘距离实测、射程内直连、射程外不可直连、中继需节点、再加密需密码域转换、同几何不同拥塞（排队溢出）、当面不占信道 | 7 |
| `tests/test_command_delay_causal_information_v23.py` | IR-3 的 5 项因果泄漏情形（含投递前后对比、延迟报告的观察回合与年龄、舰队只从投递报文得知他队） | 4 |
| `tests/test_command_delay_mission_order_v23.py` | IR-4 六回合情形（持久、重述不产生修订、迟到修正成为新修订、旧令被拒）+ 撤销 | 2 |
| `tests/test_command_delay_reporting_v23.py` | IR-5 四项：无变化不发报/命令要求才发、CONTACT_ONLY 被接触正确突破、严格静默拦住例行、紧急优先于例行 | 4 |
| `tests/test_command_delay_units_and_claims_v23.py` | IR-6：单位由引擎换算、12 格≠12 海里回归、无据 CONFIRMED 断言回归、等级由来源而非措辞决定 | 4 |
| `tests/test_command_delay_gunnery_authority_v23.py` | IR-7 五项：决策无炮击字段、原始炮击令被拒、权重只改偏好、权重界限、不可见目标指令无效 | 5 |
| `tests/test_command_delay_move_together_v23.py` | IR-8 缺失的三项：强制移动交互、Realistic 模式对等、边界不变量 | 3 |
| `tests/test_command_delay_e2e_v23.py` | IR-9 脚本化端到端：账本自洽（出处/分解/合计/槽位/命令修订）+ 可复现 | 2 |

合计新增 **31 项**。

## 修改的既有测试（均为"旧断言编码了缺陷/旧语义"）

| 文件 | 改动 | 原因 |
|---|---|---|
| `test_command_delay_communications.py` | 延迟表与选路断言改写为 v2.3 | 旧的 TBS +1、跨编队即转报 |
| `test_command_delay_chain_of_command.py` | "远程命令必须有信号时间"改为"当面是独立媒介、远程零基础延迟但占槽位" | IR-2 |
| `test_command_delay_formation_llm.py` / `test_command_delay_mode_shell.py` | 提示词字段表 `stale_external_reports` → `knowledge`；原"兄弟报告可见"断言改为"不可见" | IR-3 |
| `test_command_delay_formation_agent.py` | `local_autonomy ⇒ BLACKOUT` 改为 `STALE 或 BLACKOUT` | CD8-F3 语义；旧断言不可达而非正确 |

## 回归基线

- 命令延迟测试套件：全绿（含 2 项声明为跳过的用例）。
- 8 项审计：PASS。
- 黄金回放：7 行 Classic/Realistic 逐字节未变；`cd_s01`（命令延迟行）三次变更均已归因记录。
- 哈希种子 0/1/2/8：8 行全部稳定。
