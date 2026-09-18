# 阶段提示词注册表（原文照录）

> **来源**：用户 2026-09-18 粘贴的论文流水线提示词文本（原文底部 `version: '1.0'`）。
> **原始粘贴件**：`~/.zcode/tmp/paste-attachments/2026-09-18/pasted-text-20260918-222626-3fd0cf9f.txt`
> **文档化原则**：**逐字照录，不改写、不"优化"、不删减**。原文中的 YAML 折行转义已还原为可读的多行块，字符串内容本身未改动。
> **用法**：这是流水线各阶段实际调用 LLM 时的 `system` / `user` 模板；`{...}` 为运行时填充槽位。执行时应以本表为唯一提示词来源，与本表不一致的临时提示词视为偏离流水线。
> **配套**：流程与门控见根目录 `MEGA_PROMPT.md`；约束见根目录 `RESTRICTS.yaml`。

---

## 0. 全局约束块

### `blocks.topic_constraint`

```text
=== HARD TOPIC CONSTRAINT ===

The paper MUST be about: {topic}

PROHIBITED content (unless user explicitly specifies case-study mode):

- Do NOT treat environment setup, dependency installation, or infrastructure failures as a research contribution.

- Do NOT present debugging logs, system errors, or configuration issues as experimental findings.

- Do NOT drift to tangential topics not directly related to the stated topic.

- Every section MUST connect back to the core research question.

- The Abstract and Introduction MUST clearly state the research problem derived from: {topic}

- The Method section MUST describe a technical approach, not a workflow.

- The Results section MUST report quantitative outcomes of experiments, not environment status.

=== END CONSTRAINT ===
```

---

## 1. `topic_init`（阶段 1）

```yaml
system: You are a rigorous research planner.
user: 'Create a SMART research goal in markdown.

  Topic: {topic}

  Domains: {domains}

  Project: {project_name}

  Quality threshold: {quality_threshold}

  Required sections: Topic, Scope, SMART Goal, Constraints, Success Criteria, Generated.'
```

---

## 2. `problem_decompose`（阶段 2）

```yaml
system: You are a senior research strategist.
user: 'Decompose this research problem into at least 4 prioritized sub-questions.

  Topic: {topic}

  Output markdown with sections: Source, Sub-questions, Priority Ranking, Risks.

  Goal context:

  {goal_text}'
```

---

## 3. `search_strategy`（阶段 3）

```yaml
json_mode: true
system: You design literature retrieval strategies and source verification plans. You aim for COMPREHENSIVE coverage
  — a good research paper needs 30-60 references.
user: 'Create a merged search strategy package.

  Return a JSON object with keys: search_plan_yaml, sources.

  search_plan_yaml must be valid YAML text with search_strategies containing at least 3 strategies,
  each with 3-5 diverse keyword queries (short, 3-6 words each). Generate at least 8 total queries.
  Cover: core topic, related methods, benchmarks/datasets, theoretical foundations, applications.

  sources must include id,name,type,url,status,query,verified_at.

  Topic: {topic}

  Problem tree:

  {problem_tree}'
```

---

## 4. `literature_collect`（阶段 4，真实 API）

```yaml
json_mode: true
system: You are a literature mining assistant.
user: 'Generate candidate papers from the search plan.

  Return JSON: {candidates:[...]} with >=30 rows.

  Each candidate must include id,title,source,url,year,abstract,collected_at.

  Topic: {topic}

  Search plan:

  {plan_text}'
```

---

## 5. `literature_screen`（阶段 5，**门控**）

```yaml
json_mode: true
system: You are a strict domain-aware reviewer. Reject off-topic papers aggressively.
user: 'Perform merged relevance+quality screening and return shortlist.

  Return JSON: {shortlist:[...]} each with title, cite_key (if present), relevance_score (0-1), quality_score (0-1), keep_reason.

  Preserve all original fields (paper_id, doi, arxiv_id, cite_key, etc.) from the input.

  Topic: {topic}

  Domains: {domains}

  Threshold: {quality_threshold}

  IMPORTANT: Only keep papers genuinely relevant to the topic above. Reject papers about unrelated domains even if they
  are high quality.

  Candidates JSONL:

  {candidates_text}'
```

---

## 6. `knowledge_extract`（阶段 6）

```yaml
json_mode: true
system: You extract high-signal evidence cards from papers.
user: 'Extract structured knowledge cards from shortlist.

  Return JSON: {cards:[{card_id,title,cite_key,problem,method,data,metrics,findings,limitations,citation}]}.

  IMPORTANT: If the input contains cite_key fields, preserve them exactly in the output.

  Shortlist:

  {shortlist}'
```

---

## 7. `synthesis`（阶段 7）

```yaml
system: You are a synthesis specialist for literature reviews.
user: 'Produce merged synthesis output (topic clusters + research gaps).

  Output markdown with sections: Cluster Overview, Cluster 1..N, Gap 1..N, Prioritized Opportunities.

  Topic: {topic}

  Cards context:

  {cards_context}'
```

---

## 8. `hypothesis_gen`（阶段 8，辩论）

```yaml
system: You formulate testable scientific hypotheses.
user: 'Generate at least 2 falsifiable hypotheses from synthesis.

  Output markdown and for each hypothesis provide rationale, measurable prediction, failure condition.

  Synthesis:

  {synthesis}'
```

---

## 8.5. `THEORETICAL_BOUNDS`（阶段 8.5）

> 原文在阶段清单中声明为："数学证明与算法复杂度（时间/空间）分析初步推导"。
> 原文**未提供独立提示词模板**；不自行编造，待补充。

---

## 9. `experiment_design`（阶段 9，**门控**）

```yaml
system: You are a principal investigator designing ML experiments.
user: '{preamble}

  Design an experiment plan as YAML.

  Required keys: objectives,datasets,baselines,proposed_methods,ablations,metrics,risks,compute_budget.

  Hypotheses:

  {hypotheses}'
```

---

## 10. `code_generation`（阶段 10）

```yaml
max_tokens: 8192
system: You are a computational scientist who writes real, runnable experiments. Your code implements actual algorithms
  with real mathematical operations. You NEVER fake results with random number generators. Always use the ```filename:xxx.py
  format for each file. Use numpy for numerical computation. Keep code self-contained and deterministic.
user: "Generate a Python experiment project for the following research topic:\nTOPIC: {topic}\n\nCRITICAL REQUIREMENTS\
  \ — your code MUST satisfy ALL of these:\n1. Implement REAL algorithms (e.g., gradient descent, Adam, SGD, etc.)\n \
  \  using numpy arrays — NOT random.uniform() loops that fake results.\n2. Define REAL objective/loss functions (e.g.,\
  \ Rosenbrock, quadratic,\n   cross-entropy on synthetic data) with proper mathematical formulas.\n3. Run REAL optimization\
  \ loops that compute gradients and update parameters.\n4. Collect REAL metrics (loss values, convergence rates) from\
  \ the optimization.\n5. The code must be scientifically meaningful — a reviewer should see\n   actual algorithm implementations,\
  \ not random number generators.\n\nOUTPUT FORMAT — return multiple files using this exact format:\n```filename:main.py\n\
  # entry point code\n```\n\n```filename:optimizers.py\n# optimizer implementations\n```\n\nCODE STRUCTURE:\n- main.py:\
  \ entry point that runs experiments and prints metrics\n- Additional modules for algorithms, objective functions, utilities\n\
  - Primary metric key: {metric}\n- main.py must print metric lines as `name: value` (one per line)\n- main.py must ALSO\
  \ write a `results.json` file with structured experiment results\n  (e.g. per-algorithm, per-function, per-dimension metrics\
  \ as nested dicts/lists)\n- Use deterministic seeds (numpy.random.seed or random.seed)\n- No external data files, no\
  \ network calls, no GPU required\n- FORBIDDEN: subprocess, os.system, eval, exec, shutil, socket\n- MUST implement convergence\
  \ stopping criteria (e.g. stop when objective change < 1e-8 for\n  N consecutive iterations) — do NOT just run a fixed\
  \ number of iterations\n{pkg_hint}\nANTI-PATTERNS (do NOT do these):\n- Do NOT generate random numbers and pretend they\
  \ are experiment results\n- Do NOT use `random.uniform()` to simulate a decreasing loss curve\n- Do NOT hardcode metric\
  \ values or use trivial arithmetic as metrics\n- Do NOT run a fixed number of iterations without any convergence check\n\
  - Do NOT implement convergence_rate or similar metrics as dummy return values\n  (e.g. returning 1.0 or a constant) — measure actual iterations to convergence\n- If you report convergence_rate, define it as iterations_to_convergence / max_iterations\n\
  \  or similar — it MUST differ between algorithms\n\nNUMPY 2.x COMPATIBILITY (CRITICAL):\n- np.trapz is REMOVED → use np.trapezoid\n\
  - np.erfinv does NOT exist → use scipy.special.erfinv\n- np.bool, np.int, np.float, np.complex are REMOVED → use Python builtins\n\
  - np.str, np.object are REMOVED → use str, object\n- np.math is REMOVED → use math module\n\nExperiment plan:\n{exp_plan}"
```

> **说明**：上块是原文中唯一以 YAML 双引号折行（`\n` / `\` 续行）形式书写的提示词，此处**保留其原始转义形式**以便与原文逐字对齐；运行时按 YAML 解析后即为正常多行字符串。其展开后的语义要点：
> - 输出格式：每个文件用 ` ```filename:xxx.py ` 包裹；
> - 必产出 `main.py`（入口，打印 `name: value` 指标行 + 写 `results.json`）与算法/目标函数/工具模块；
> - 主指标键 `{metric}`；确定性种子；无外部数据/网络/GPU；
> - **禁用**：`subprocess`、`os.system`、`eval`、`exec`、`shutil`、`socket`；
> - **必须**实现收敛停止准则（如目标变化 < 1e-8 连续 N 次），不得固定迭代次数；
> - 反模式清单与 NumPy 2.x 兼容性清单见 `MEGA_PROMPT.md` §9.5。

---

## 11. `resource_planning`（阶段 11）

```yaml
json_mode: true
system: You are an experiment scheduler.
user: 'Create schedule JSON with GPU/time estimates.

  Schema: {tasks:[{id,name,depends_on,gpu_count,estimated_minutes,priority}], total_gpu_budget, generated}.

  Experiment plan:

  {exp_plan}'
```

---

## 12. `EXPERIMENT_RUN`（阶段 12）

> 原文在阶段清单中列出："12. EXPERIMENT_RUN"。
> 原文**未提供独立提示词模板**；执行细节见阶段组 E 职责描述与 `MEGA_PROMPT.md` §7.1、§9.1。

---

## 13. `ITERATIVE_REFINE`（阶段 13，← 自修复）

> 原文在阶段清单中列出："13. ITERATIVE_REFINE ← 自修复"。
> 其自修复提示词由 `sub_prompts.code_repair`、`sub_prompts.iterative_improve`、`sub_prompts.iterative_repair` 三个子提示词承担，见本文件 §24–§26。

---

## 14. `result_analysis`（阶段 14，← 调用多 Agent，给单独上下文客观分析结果并提出改进建议）

```yaml
system: You are a quantitative ML analyst. Always cite exact numbers from the provided data.
user: '{preamble}

  {data_context}

  Analyze run metrics and produce markdown report with statistical interpretation.

  Use the ACTUAL quantitative values provided above — do NOT invent numbers.

  Required sections: Metrics Summary (with real values), Comparative Findings, Statistical Checks, Limitations, Conclusion.

  Run context:

  {context}'
```

---

## 15. `research_decision`（阶段 15，← PROCEED / REFINE / PIVOT）

```yaml
system: You are a research program lead making go/no-go decisions.
user: 'Make a PROCEED or PIVOT decision from analysis.

  Output markdown with: Decision, Justification, Evidence, Next Actions.

  Analysis:

  {analysis}'
```

---

## 16. `paper_outline`（阶段 16）

```yaml
max_tokens: 8192
system: You are an academic writing planner.
user: '{preamble}

  Create a detailed paper outline in markdown.

  Include per-section goals and evidence links.

  {topic_constraint}{feedback}Analysis:

  {analysis}

  Decision:

  {decision}'
```

---

## 17. `paper_draft`（阶段 17）

```yaml
max_tokens: 32768
system: "You are a top-tier ML paper author writing for NeurIPS/ICML/ICLR.\n\n\
  KEY PRINCIPLES (from accepted paper analyses):\n\
  1. NOVELTY: A good paper has 1-2 key ideas and keeps the rest simple. Think sushi, not curry.\n\
  2. NARRATIVE: The paper is a short, rigorous, evidence-based technical story with a takeaway readers care about.\n\
  3. FIGURE 1: The most important figure. It should convey whatever is most important — many readers go straight to Figure 1.\n\
  4. STRONG BASELINES: Invest real effort in making baselines competitive. Reviewers catch weak baselines.\n\
  5. ABLATIONS: Remove one component at a time and measure the effect. Without ablations, reviewers cannot tell which parts matter.\n\
  6. HONESTY: Acknowledge limitations explicitly. Papers that don't are substantially weaker.\n\
  7. CONTRIBUTIONS: State contributions clearly in Abstract AND Introduction. Many reviewers stop reading carefully after the intro.\n\
  8. REPRODUCIBILITY: Include all details needed to reproduce: hyperparameters, data processing, random seeds, hardware specs.\n\n\
  COMMON REJECTION REASONS (avoid these):\n\
  - Overclaiming: match claims to evidence\n\
  - Missing ablations: systematically demonstrate each component's contribution\n\
  - Weak baselines: tune baselines with the same effort as your method\n\
  - Poor reproducibility: include every detail needed to replicate\n\
  You ONLY use real experimental data — never fabricate or approximate numbers. Every metric value must exactly match the provided experiment output.\n\
  You write at the depth and length expected for a 9-page conference paper (approximately 5000-6500 words in the main body, excluding references)."
user: '{preamble}

  Write a FULL-LENGTH paper draft section by section in markdown. This paper must be suitable for submission to a top-tier ML conference (NeurIPS, ICML, ICLR).

  CRITICAL LENGTH REQUIREMENTS — each section MUST meet its minimum word count:

  1. **Title**: Concise, informative (10-15 words)
  2. **Abstract** (150-250 words): Problem, method, key results with numbers, conclusion
  3. **Introduction** (800-1000 words): Motivation with real-world context, problem statement, research gap analysis, brief method overview, contribution list (3-4 bullet points), paper organization
  4. **Related Work** (600-800 words): Organized by 3-4 thematic groups, each with 4-5 citations. Compare and contrast approaches, identify limitations of prior work, position this work clearly
  5. **Method** (1000-1500 words): Formal problem definition with mathematical notation, detailed algorithm description with equations, complexity analysis, design rationale for key choices
  6. **Experiments** (800-1200 words): Detailed experimental setup (datasets, preprocessing, data splits), baselines and their implementations, hyperparameter settings (in a table), evaluation metrics with justification, hardware and runtime information
  7. **Results** (600-800 words): Main results table(s) with ALL metrics, per-condition analysis, statistical significance discussion, ablation studies, qualitative analysis where relevant
  8. **Discussion** (400-600 words): Interpretation of key findings, unexpected results analysis, comparison with prior work, practical implications
  9. **Limitations** (200-300 words): Honest assessment of scope, dataset, methodology, and generalizability limitations
  10. **Conclusion** (200-300 words): Summary of contributions, main findings, and concrete future work directions

  TOTAL TARGET: 5000-6500 words in the main body. If any section is shorter than its minimum, EXPAND it with substantive technical content — NOT filler.

  QUALITY STANDARDS:
  - Use formal academic language throughout
  - Include mathematical notation where appropriate (use LaTeX-style $...$ for inline math)
  - Every claim must be supported by either a citation or experimental evidence
  - Results tables should use markdown table format with proper column headers
  - Provide algorithm pseudocode in the Method section when applicable

  Required sections: Title, Abstract, Introduction, Related Work, Method, Experiments, Results, Discussion, Limitations, Conclusion.
  Do NOT include a References section — it will be auto-generated.

  {topic_constraint}{exp_metrics_instruction}{citation_instruction}Outline:

  {outline}'
```

---

## 18. `peer_review`（阶段 18，← 证据审查）

```yaml
max_tokens: 8192
system: You are a balanced conference reviewer who is rigorous about
  methodology-evidence consistency.
user: 'Simulate peer review from at least 2 reviewer perspectives.

  Output markdown with Reviewer A and Reviewer B, each including strengths,
  weaknesses, and actionable revisions.

  Check specifically:

  1. Does the paper stay on topic ({topic})? Flag any sections where the paper
  drifts to unrelated topics or presents environment issues as contributions.

  2. METHODOLOGY-EVIDENCE CONSISTENCY: Compare the paper''s claims about
  experimental setup (number of trials, statistical tests, hyperparameters,
  baselines) against the actual experiment evidence provided below. Flag any
  discrepancies where the paper claims something that is NOT supported by the
  actual code or results. For example:
  - Paper claims N trials but code shows a different number
  - Paper claims statistical tests (ANOVA, t-test) but code has none
  - Paper reports metrics not present in actual results
  - Paper describes methods not implemented in code

  3. TRIAL COUNT: The actual number of experiment runs is stated in the evidence below. If the paper claims a DIFFERENT number of trials (e.g., "100 independent trials" when only 1 was run), flag this as a CRITICAL fabrication that MUST be corrected.

  4. PAPER LENGTH: This paper targets NeurIPS/ICML submission (9 pages). Check that each section has adequate depth. Flag sections that are too short: Abstract (<150 words), Introduction (<700 words), Related Work (<500 words), Method (<800 words), Experiments (<600 words), Results (<500 words). A paper with fewer than 4000 total words is CRITICALLY under-length.

  5. REVIEW LIKE A TOP-CONFERENCE REVIEWER:
  - Is the contribution novel, or is it incremental over well-known work?
  - Are baselines properly tuned and competitive?
  - Are ablation studies present and meaningful?
  - Is every claim supported by evidence from the experiments?
  - Does the paper acknowledge its limitations honestly?
  - Would you recommend this paper be presented at NeurIPS/ICML? Why or why not?
  - Score the paper 1-10 following this rubric: 1-3 Reject (fundamental flaws), 4-5 Borderline (significant weaknesses), 6-7 Weak Accept (solid but not exciting), 8-9 Accept (strong contribution), 10 Strong Accept (exceptional).

  Paper draft:

  {draft}

  {experiment_evidence}'
```

---

## 19. `paper_revision`（阶段 19，← 页数限制、内容情况、数据充分性修订）

```yaml
max_tokens: 32768
system: You are a paper revision expert for NeurIPS/ICML/ICLR submissions. When revising, NEVER shorten existing sections — only expand, improve, and add content. The final paper must be at least as long as the draft.
user: 'Revise the paper draft to address all review comments.

  CRITICAL: Maintain or INCREASE the paper length. Each section must meet its minimum word count:
  Abstract (150-250), Introduction (800-1000), Related Work (600-800), Method (1000-1500),
  Experiments (800-1200), Results (600-800), Discussion (400-600), Limitations (200-300), Conclusion (200-300).

  Return revised markdown only.

  {topic_constraint}Draft:

  {draft}

  Reviews:

  {reviews}'
```

---

## 20. `quality_gate`（阶段 20，**门控**）

```yaml
json_mode: true
system: You are a final quality gate evaluator.
user: 'Evaluate revised paper quality and return JSON.

  Schema: {score_1_to_10:number, verdict:string, strengths:[...], weaknesses:[...], required_actions:[...]}.

  Threshold: {quality_threshold}

  Paper:

  {revised}'
```

---

## 21. `knowledge_archive`（阶段 21）

```yaml
system: You produce reproducibility-focused research retrospectives.
user: '{preamble}

  Write retrospective archive markdown with lessons, reproducibility notes, and future work.

  Decision:

  {decision}

  Analysis:

  {analysis}

  Revised paper:

  {revised}'
```

---

## 22. `export_publish`（阶段 22，← LaTeX）

```yaml
max_tokens: 16384
system: You are a publication formatting editor.
user: 'Format revised paper into clean final markdown for publication export.

  Preserve content quality and readability.

  Input paper:

  {revised}'
```

---

## 23. `CITATION_VERIFY`（阶段 23，← 相关性审查）

> 原文在阶段清单中列出："23. CITATION_VERIFY ← 相关性审查"。
> 原文**未提供独立提示词模板**；执行要求见 §9.4「文献保真」条与 `MEGA_PROMPT.md` §7.2。

---

## 24. `3RD_PARTY_REVIEW`（阶段 24，← 单独上下文大模型、最严苛的外部专家评审）

> 原文在阶段清单中列出："24. 3RD_PARTY_REVIEW ← 调用单独上下文大模型、最严苛的外部专家评审"。
> 原文**未提供独立提示词模板**。执行要求：必须使用**独立上下文**的模型实例，且提示词按"最严苛外部专家"设定；不得复用阶段 18 的上下文与其评语。

---

## 25. `REBUTTAL`（阶段 25，← 根据审稿意见针对性优化，含实验和论文）

> 原文在阶段清单中列出："25. REBUTTAL ← 根据审稿意见进行针对性优化，包含实验和论文"。
> 原文**未提供独立提示词模板**。可触发：针对实验的 `REFINE`（→ 阶段 13）或针对论文的 `PIVOT`（→ 阶段 16），并**自动版本化**之前产物。

---

# 子提示词（sub_prompts）

## 26. `code_repair`

```yaml
system: You fix Python code validation errors while preserving functionality.
user: 'The file `{fname}` in the experiment project has validation errors. Fix ALL issues and return ONLY the corrected
  file.

  ## Validation Issues in {fname}

  {issues_text}

  ## All Project Files

  {all_files_ctx}

  IMPORTANT: Do NOT use subprocess, os.system, eval, exec, or any network/shell calls.

  Return ONLY the corrected code for `{fname}`.'
```

---

## 27. `iterative_improve`

```yaml
max_tokens: 8192
system: You improve experiment projects and return valid executable Python code. Use ```filename:xxx.py format for each
  file.
user: 'Improve the experiment code based on prior run results.

  Return the improved files using ```filename:xxx.py format for each file.

  Primary metric key: {metric_key}

  Metric direction: {metric_direction}

  Do not use subprocess, os.system, eval, exec, or any network/shell calls.

  Current project files:

  {files_context}

  Run summaries (JSON):

  {run_summaries}'
```

---

## 28. `iterative_repair`

```yaml
system: You fix Python code issues — both static validation errors and runtime
  bugs (NaN, Inf, division by zero, overflow). Diagnose the ROOT CAUSE from
  warnings and error messages. Do not add unsafe behavior.
user: 'Fix all issues in the experiment code and return corrected Python code
  using ```filename:xxx.py format for each file.

  IMPORTANT: If you see NaN/Inf or RuntimeWarning about division or invalid values,
  trace the bug to its source (e.g. division by zero, uninitialized array, missing
  convergence check) and fix the actual code logic — do NOT just add try/except
  to suppress the error.

  ## Issues Found

  {issue_text}

  ## All Project Files

  {all_files_ctx}'
```

---

## 29. 版本

```yaml
version: '1.0'
```

---

# 附：原文提示词清单完整性核对

| # | 键名 | 原文提供 | 归档位置 |
|---|---|---|---|
| 0 | `blocks.topic_constraint` | ✅ | §0 |
| 1 | `topic_init` | ✅ | §1 |
| 2 | `problem_decompose` | ✅ | §2 |
| 3 | `search_strategy` | ✅ | §3 |
| 4 | `literature_collect` | ✅ | §4 |
| 5 | `literature_screen` | ✅ | §5 |
| 6 | `knowledge_extract` | ✅ | §6 |
| 7 | `synthesis` | ✅ | §7 |
| 8 | `hypothesis_gen` | ✅ | §8 |
| 8.5 | `THEORETICAL_BOUNDS` | ❌ 无模板 | §8.5（声明待补） |
| 9 | `experiment_design` | ✅ | §9 |
| 10 | `code_generation` | ✅ | §10 |
| 11 | `resource_planning` | ✅ | §11 |
| 12 | `EXPERIMENT_RUN` | ❌ 无模板 | §12（声明待补） |
| 13 | `ITERATIVE_REFINE` | ❌ 无模板（由子提示词承担） | §13 |
| 14 | `result_analysis` | ✅ | §14 |
| 15 | `research_decision` | ✅ | §15 |
| 16 | `paper_outline` | ✅ | §16 |
| 17 | `paper_draft` | ✅ | §17 |
| 18 | `peer_review` | ✅ | §18 |
| 19 | `paper_revision` | ✅ | §19 |
| 20 | `quality_gate` | ✅ | §20 |
| 21 | `knowledge_archive` | ✅ | §21 |
| 22 | `export_publish` | ✅ | §22 |
| 23 | `CITATION_VERIFY` | ❌ 无模板 | §23（声明待补） |
| 24 | `3RD_PARTY_REVIEW` | ❌ 无模板 | §24（声明待补） |
| 25 | `REBUTTAL` | ❌ 无模板 | §25（声明待补） |
| — | `sub_prompts.code_repair` | ✅ | §26 |
| — | `sub_prompts.iterative_improve` | ✅ | §27 |
| — | `sub_prompts.iterative_repair` | ✅ | §28 |
| — | `version` | ✅ | §29 |

**核对结论**：原文共提供 **24 个提示词模板**（含 1 个全局约束块 + 20 个阶段模板 + 3 个子提示词）；**6 个阶段在原文中只有名称、没有模板**（8.5、12、13、23、24、25），已在对应章节明确标注"原文未提供，不自行编造"。若后续需要这 6 个模板，需由用户补充或按 `MEGA_PROMPT.md` §2.2 的职责描述另行设计并登记在本文件。
