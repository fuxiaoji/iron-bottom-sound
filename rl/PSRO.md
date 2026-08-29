# 自适应鱼雷 AI 长时训练运行手册

本训练器以真实模式二马（IBS-S-EM-01）为主要验收槽位，同时保留经典想定 1、3 以防策略过拟合。规则引擎始终独立裁决；训练器只能提交合法订单。

## 先做短验收

在仓库根目录执行：

~~~powershell
$env:PYTHONPATH = 'backend/src;.'
python -m rl.psro --out rl/results/psro-smoke-local --smoke --serve-dashboard --dashboard-port 8766
~~~

烟雾测试只运行两场真实模式二马对局。必须以 stage=complete 结束，且结果中友军碰撞与友军鱼雷命中均为零，才允许开始长时训练。

## 正式训练与实时面板

~~~powershell
$env:PYTHONPATH = 'backend/src;.'
python -m rl.psro --out rl/results/psro-torpedo-v1 --serve-dashboard --dashboard-port 8765
~~~

训练期间访问 http://127.0.0.1:8765/dashboard.html。面板每秒读取一次 status.json，训练器另以两秒周期独立刷新心跳；页面显示阶段、PSRO 轮次、完成/预计对局、ETA、策略混合分布、当前最佳响应和最近错误。只要仍有在途工作且连续 300 秒没有新对局完成，status.json 会置 stalled=true，并显示无进展时长和在途数量；这表示心跳在线但工作进程疑似陷入计算活锁，不应继续相信 ETA。

若需要让训练在隐藏窗口运行：

~~~powershell
$root = (Resolve-Path '.').Path
$env:PYTHONPATH = 'backend/src;.'
New-Item -ItemType Directory -Force 'rl/results/psro-torpedo-v1' | Out-Null
Start-Process -FilePath 'python' -ArgumentList @('-m','rl.psro','--out','rl/results/psro-torpedo-v1','--serve-dashboard','--dashboard-port','8765') -WorkingDirectory $root -RedirectStandardOutput 'rl/results/psro-torpedo-v1/stdout.log' -RedirectStandardError 'rl/results/psro-torpedo-v1/stderr.log' -WindowStyle Hidden
~~~

同一个输出目录只能有一个训练进程，禁止同时启动两个写入者。

## 断电与中断恢复

每完成一场对局，训练器都会立即：

1. 把结果提交到 results.sqlite3；数据库启用 WAL 和 synchronous=FULL。
2. 追加并 fsync games.jsonl 审计行。
3. 以临时文件、fsync、原子替换更新 checkpoint.json 和 status.json。

因此断电最多丢失当时尚未完成的在途对局，不会丢失已经提交的结果。恢复命令为：

~~~powershell
$env:PYTHONPATH = 'backend/src;.'
python -m rl.psro --out rl/results/psro-torpedo-v1 --resume --serve-dashboard --dashboard-port 8765
~~~

收到 Ctrl+C 或终止信号后，状态写为 interrupted，不会注册未完成轮次的冠军。重启后，SQLite 是逐局结果权威来源；checkpoint.json 保存轮次、种群和策略池；games.jsonl 只用于人工审计。

## 故障检查

- status.json 的 heartbeat 长时间不变：先检查进程及 stderr.log，不要直接删除输出目录。
- heartbeat 持续更新但 stalled=true：记录完成数、progress_age_seconds 和进程 CPU，优雅停止；若工作进程无法退出，再终止父进程树。SQLite 中已完成行仍可用 --resume 复用，禁止删除 results.sqlite3、checkpoint.json 或 games.jsonl。
- stage=failed：查看 last_error，修复代码后用 --resume；失败状态不会注册冠军。
- SQLite 存在 -wal 文件：保持三个 SQLite 文件在同一目录，不要单独复制主文件。需要备份时优先停止训练或使用 SQLite Backup API。
- 训练完成后必须跑 fresh-seed 真实模式二马验收；训练分数本身不能替代引擎终局、友伤和回放检查。
