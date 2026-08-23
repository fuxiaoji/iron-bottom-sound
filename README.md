# 铁底湾的回响 IV

可审计的 Python 兵棋规则后端与 React/TypeScript Web UI。当前分支是阶段 1 的可运行基础，不代表所有规则已经完成四向闭环；真实状态见 `plan.md` 和 `docs/rules/coverage.csv`。

## 本地运行

```powershell
python -m pip install -e ".[dev,corpus]"
python -m iron_bottom_sound
```

另开终端：

```powershell
cd frontend
pnpm install
pnpm dev
```

浏览器访问 `http://127.0.0.1:5173`。API 文档位于 `http://127.0.0.1:8000/docs`。

## 验证

```powershell
python -m pytest --cov=iron_bottom_sound
python scripts/build_source_manifest.py
python skills/iron-bottom-sound-rules/scripts/build_rule_corpus.py
python skills/iron-bottom-sound-rules/scripts/query_rules.py "炮击"
```

前端生产构建：

```powershell
cd frontend
pnpm run build
```

## 资料与权威

- 想定特例高于舰船记录/玩家辅助表，后者高于通用规则。
- OCR 和全文检索只用于定位；表格与关键图必须回看原始页逐格核验。
- 未核实规则不得进入裁决核心，统一登记到 `docs/rules/open_questions.md`。
- 原始资料可能受版权保护；仓库应保持私有。
