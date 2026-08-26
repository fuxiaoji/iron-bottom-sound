# 部署：铁底湾 → https://fuwenji.asia/tiedi

> 目标：域名 `fuwenji.asia`（A 记录 8.134.14.30，阿里云 ECS）上已有作品集（根路径静态
> Vite 应用）。铁底湾**纯增量**部署到子路径 `/tiedi`，不动首页。架构：
>
> ```
> 浏览器 ── https://fuwenji.asia/tiedi ──► nginx
>                                       ├── /tiedi/*             → /opt/tiedi/frontend/dist（静态 SPA）
>                                       ├── /tiedi/api/*         → 127.0.0.1:8001 后端（uvicorn）
>                                       └── /tiedi/assets/counters/* → 后端棋子图片挂载
> 后端：systemd 服务 tiedi，uvicorn iron_bottom_sound.api:app，DB/SQLite + 战报截图落盘
> ```

## 0) 前提（服务器上一次性）

- 已安装 `python3`（≥3.11）与 `node`/`pnpm`（作品集是 Vite 构建，通常已有 node）。
  无 pnpm 时：`corepack enable && corepack prepare pnpm@latest --activate` 或 `npm i -g pnpm`。
- 无 node 时无法在前端构建——可在任意有 node 的机器构建 dist 后上传（见 §3 注）。

## 1) 上传代码到 /opt/tiedi

仓库无 git remote，需手动上传（在**本机**执行）：

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
pnpm install
pnpm build -- --base=/tiedi/        # => tsc -b && vite build --base=/tiedi/
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
- **安全提示**：此前在对话中粘贴过一把 DeepSeek 密钥（`sk-8758...`）——请尽快到
  DeepSeek 控制台**吊销并更换**；本部署只会用它注册到 `/etc/tiedi.env`，不落仓库。
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

把 `deploy/nginx-tiedi.conf` 里三个 location 追加到 fuwenji.asia 的 server 块
（`/etc/nginx/sites-available/...` 或 `nginx.conf`），然后：

```bash
sudo nginx -t && sudo systemctl reload nginx
```

> 若现有 server 块用了 `location / { try_files $uri $uri/ /index.html; }` 之类的兜底，
> `/tiedi` 前缀更具体、优先匹配，不冲突。

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

1. 重新上传代码（rsync，保留 DB/后端 reports）。
2. `systemctl restart tiedi`；如需改前端：重跑 §3 构建。
3. nginx 配置有改动才 `nginx -t && systemctl reload nginx`。
