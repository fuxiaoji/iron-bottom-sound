# 四向规则审计

每条基础规则和每张表维护一行审计记录：

1. **Source**：规范文档、PDF 页、印刷页/章节、版本、哈希和视觉核验状态。
2. **Data**：完整的结构化字段、表格单元、修正、优先级和取整方式。
3. **Execution**：唯一的引擎调用点；禁止在 UI、API 或 LLM 中复制常量。
4. **Tests**：边界单元、修正组合、非法输入、确定性回放和 UI 事件轨迹。

状态依次为 `indexed`、`verified_source`、`structured`、`executable`、`tested`；`blocked` 表示命名歧义阻止安全裁决。只有所有必选规则和声明纳入的可选规则达到 `tested`，或有来源支持的 `not_applicable`，才可宣称完成。
