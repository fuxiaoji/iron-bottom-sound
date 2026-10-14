# 部署：铁底湾 → https://fuwenji.asia/tiedi

> 目标：域名 `fuwenji.asia`（A 记录 8.134.14.30，阿里云 ECS）上已有作品集（根路径静态
> Vite 应用）。铁底湾**纯增量**部署到子路径 `/tiedi`，不动首页。架构：
>
> ```
> 浏览器 ── https://fuwenji.asia/tiedi ──► nginx（单个 /tiedi/ 反向代理块，剥前缀后全交后端）
>                                        └── 127.0.0.1:8001 后端单进程托管：
>                                            静态 SPA（dist，挂根路径 html=True）
>                                            + /api 前缀剥离 + /assets/counters 棋子图 + 战报截图
> 后端：systemd 服务 tiedi，uvicorn iron_bottom_sound.api:app，DB/SQLite + 战报截图落盘
> ```

## 0) 前提（服务器上一次性）

- 已安装 `python3.11`（`/usr/bin/python3.11`，EPEL 提供）与 `node`（v22 + npm）。
  > 本机只有 Python 3.6（项目需 ≥3.11，装了 EPEL 的 python3.11）；前端构建用 npm 即可
  > （仓库虽有 pnpm-lock.yaml，服务器无 pnpm 且 corepack 的 pnpm 在 workspace 下报
  > "packages field missing or empty"，改用 `npm install` 已验证可行）。

## 1) 上传代码到 /opt/tiedi

本地 Git 远端为 `https://github.com/fuxiaoji/iron-bottom-sound.git`。线上 `/opt/tiedi` 仍是无 Git 的运行目录，使用已提交版本的部署包更新（在**本机**准备）：

发布前提交并推送所选分支，再从该提交归档后端、结构化数据、原始素材与前端。前端使用 `--base=/tiedi/` 构建；不要直接把仍在变化的实验工作区作为线上版本。归档中的 Git LFS 指针必须还原成对应原件，并按对象 SHA256 核对，不能把指针文本作为图片部署。

下面是手动增量上传示例；数据库、战报、凭据和运行依赖不属于代码包：

```bash
rsync -av --exclude .git --exclude tmp --exclude artifacts --exclude node_modules \
  --exclude backend/reports --exclude 'backend/*.sqlite3*' \
  <本机仓库>/ root@8.134.14.30:/opt/tiedi/
# 或 scp/zip 上传后解压。上传后目录结构：/opt/tiedi/backend/src/...、/opt/tiedi/frontend/...
```

依赖 `backend/src/iron_bottom_sound/data.py` 用到的 `resources/originals/`（286 张棋子图）也在
仓库内、会一并上传。

## 2) 后端依赖与运行（服务器）

```bash
cd /opt/tiedi
python3 -m venv .venv
.venv/bin/pip install -U pip
.venv/bin/pip install -e .          # 含 fastapi/uvicorn/pillow 等（pyproject.toml）
.venv/bin/python -c "import iron_bottom_sound, PIL; print('ok')"
```

## 3) 前端构建（base=/tiedi/）

```bash
cd /opt/tiedi/frontend
npm install --no-audit --no-fund
npm run build -- --base=/tiedi/    # => tsc -b && vite build --base=/tiedi/
# 产物 /opt/tiedi/frontend/dist，index.html 内资源为 /tiedi/assets/...；
# api.ts/assets.ts 用 import.meta.env.BASE_URL 自动派生 /tiedi/api 与 /tiedi/assets/counters。
```

> 注：前端源码已是 base 感知（默认 "/" 不变）。若服务器无 node，可本机/他处构建后
> 只上传 `frontend/dist/`，其余步骤照旧。

## 4) 密钥与环境（服务器，root 专属）

```bash
sudo install -m 600 /dev/null /etc/tiedi.env
sudo sh -c 'echo "DEEPSEEK_API_KEY=<你的密钥>" >> /etc/tiedi.env'
```

- **密钥纪律**：`DEEPSEEK_API_KEY` 只从环境变量读取、绝不写入仓库；服务器上持久化于
  root-only 的 `/etc/tiedi.env`。无密钥时战报叙事走确定性回退、LLM 对手不可用，对局照常。
- `IBS_DB_PATH`/`IBS_REPORTS_DIR` 已在 systemd 单元内给出默认值，通常无需再设。

## 5) systemd 服务（服务器）

```bash
sudo cp /opt/tiedi/deploy/tiedi.service /etc/systemd/system/tiedi.service
sudo systemctl daemon-reload
sudo systemctl enable --now tiedi
systemctl status tiedi --no-pager        # active (running)
journalctl -u tiedi -n 20 --no-pager     # 确认无启动报错
```

## 6) nginx 反代（服务器）

把 `deploy/nginx-tiedi.conf` 里两个 location（`= /tiedi` 301 + `/tiedi/` 单块反代）追加到
fuwenji.asia 的 server 块（`/etc/nginx/conf.d/fuwenji.asia.conf`），然后：

```bash
sudo nginx -t && sudo systemctl reload nginx
```

> 单块即可覆盖静态 SPA、`/tiedi/api`、`/tiedi/assets/counters`、战报截图全部——后端单进程
> 托管（dist 挂根路径 + /api 前缀剥离）。若现有 server 块有 `location / { try_files ... }`
> 兜底，`/tiedi` 前缀更具体、优先匹配，不冲突。

## 7) 验证清单

```bash
# 静态页
curl -sS -o /dev/null -w '%{http_code}\n' https://fuwenji.asia/tiedi/                # 200
curl -sS https://fuwenji.asia/tiedi/ | grep -o '/tiedi/assets/[^"]*' | head -3        # base 正确
# API
curl -sS https://fuwenji.asia/tiedi/api/scenarios                                    # JSON
curl -sS -X POST https://fuwenji.asia/tiedi/api/games -H 'Content-Type: application/json' \
  -d '{"scenario_id":"IBS-S-01","seed":1}'                                            # 建局
curl -sS -o /dev/null -w '%{http_code}\n' \
  https://fuwenji.asia/tiedi/assets/counters/1.png                                    # 200 棋子图
```

浏览器打开 https://fuwenji.asia/tiedi/ 建局打一回合：截图战报（每阶段双视角 PNG）、
回合末叙事、下载 .md 自包含——全链路验证。

## 更新流程（后续发版）

1. 从明确的 Git 提交制作部署包，记录文件清单、包 SHA256 和提交号；上传到独立的 staging 目录并核对文件摘要。先用隔离数据库检查导入、新版建局和既有存档格式兼容性。
2. 保留 `/etc/tiedi.env`、`.venv`、`backend/reports` 与线上数据库；停止 `tiedi` 后，用 SQLite Backup API 创建一致性备份并核对旧表行数和原始字节摘要，保存旧运行目录供回滚。不要用本机玩家库覆盖线上玩家库。
3. 切换已核验的代码、数据和 `/tiedi/` 前端产物，启动 `tiedi`。`/tiedi/api/health` 的 `status=ready`、`loaded_revision=source_revision` 且与部署包后端摘要一致才表示加载了目标版本。如启动失败，恢复旧代码；玩家库保留，备份另存。
4. 只读核验旧表摘要、既有存档、想定目录、JS/CSS及棋子图片；新增空的 `ai_debug` 表是新版结构迁移，不改变既有对局。核对公共首页摘要不变。nginx 配置有改动才 `nginx -t && systemctl reload nginx`。

2026-10-14 夜战发布的详细提交、验证和备份位置见 `havedone.md`。服务器根目录的 `release-manifest.json` 记录实际运行提交及逐文件摘要，`deployment-result.json` 记录健康和数据保护结果；两者不含凭据或玩家行内容。
