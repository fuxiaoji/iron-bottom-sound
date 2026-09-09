# 目标进度锚点（GLM 数据录入批次）

## 目标：全部完成 ✔
1. 舰只数据录入：船表 38 张舰级卡 → extensions/class-cards.yaml，解锁 34 艘锁定舰，记录 180→214。
2. 剧本数据录入：想定手册 12 个新想定（S-02、04-14）+ catalog 更新，一般+真实模式全通过。
3. 剧本简报页：后端 /scenarios/{id}/briefing + 前端 ScenarioBriefingModal（纸质手册版式），浏览器实测通过。
4. 虚构大剧本：IBS-S-FM-01（91 舰、92×78、日美各 8 历史雷击编队），双模式验证通过。

## 提交
- 04ffe9b feat(data): 全量录入+舰级卡+简报 UI+虚构大决战
- （docs) open_questions IBS-Q-007 更新 + IBS-Q-020 新增

## 遗留
- 本机 vite build/dev 挂起（沙箱限制）；前端用 tsc+Vite 产物验证，浏览器核验用 dist/preview.html 等效页。
- test_api_llm_storage 一个 canonical-counter 用例在本机基线即失败（LFS 指针），与本批无关。

## 计数器
任务完成，结束。
