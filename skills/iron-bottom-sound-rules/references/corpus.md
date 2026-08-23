# 语料库契约

生成结果位于 `resources/derived/rag/`：

- `manifest.json`：来源身份、哈希、页数、文本量和 OCR 状态。
- `core_chunks.jsonl`：保留页边界的重叠文本块。
- `table_candidates.jsonl`：自动发现的表格/图标题候选，不代表已视觉核验。
- `iron_bottom_sound_rules.sqlite3`：SQLite FTS5 检索库。

文本层由 `pypdf` 提取。扫描页优先读取 `resources/derived/ocr/pages.jsonl` 中经人工复核的文本；安装 RapidOCR 时可用它生成初稿，但初稿不得直接晋升为结构化规则。
