---
type: paradigma-manual
title: Desiderium Beta Trial Manual
description: Three-stage beta trial playbook — shadow run, assisted decision, and Beta gate evaluation — with frozen baseline, data collection, daily/weekly routines, and stop conditions.
tags: [manual, beta, trial, observation, g3, g4]
timestamp: 2026-07-17T14:45:00+08:00
paradigma:
  schema_version: "0.1"
  temperature: warm
  lifecycle: evolving
  update_policy: agent-editable
  epistemic_status: confirmed
  retrieval_hints:
    zh:
      - 试运行手册
      - Beta 试运行
      - 影子运行
      - 观察期
      - 停止条件
    en:
      - beta trial manual
      - shadow run
      - observation period
      - stop conditions
  relations:
    related_to:
      - /plans/iteration-5-beta-observation.md
      - /manuals/desiderium-ops.md
      - /domains/trend-engine.md
      - /contracts/data-model-contract.md
---

# Purpose

Desiderium 0.10.0 试运行操作手册。定义三阶段试运行流程（影子运行 → 辅助决策 → Beta 门评估）、试运行期间的基线冻结规则、必须收集的四类数据、每日/每周操作节奏、停止条件与 Beta Ready 判定标准。目标：在不干扰现有业务的前提下验证 G3（聚类质量）与 G4（发布表现回收），并把选题时间从 1—3 小时降到 30—60 分钟。

# Preconditions

## 系统就绪

- 版本为 `0.10.0`，已按 [Operations Manual](desiderium-ops.md) 部署，`GET /health` 全绿。
- `alembic upgrade head` 已执行到 `a7b8c9d0e1f2`（Iteration 5 迁移）。
- `config/scoring.yaml` 中 `publication.team_channel_ids` 已填入团队频道 ID（G4 基准计算依赖）。
- 观察脚本可运行：`scripts/observation/g3_report.py`、`g3_sample_export.py`、`g4_report.py`。

## 基线冻结（试运行开始前建立并记录）

为本轮试运行记录一个明确的基线版本组合：

| 项 | 值 |
|---|---|
| application_version | `0.10.0` |
| scoring_config_version | `beta-baseline-1`（即 `config/scoring.yaml` version `1.2` 的冻结快照） |
| prompt_version | `beta-baseline-1` |
| embedding_space_id | `local-onnx:all-MiniLM-L6-v2`（固定，不换模型） |
| eligibility_config_version | 固定（`relevance` 段不动） |
| baseline_version | `publication-velocity-v1` |

试运行期间**原则上不修改**：

- TrendScore 权重（`scoring` 段）；
- 生命周期阈值（`thresholds` / `lifecycle` 段）；
- Embedding 模型与 `embedding_space`；
- 自动合并高低阈值（`clustering.high_similarity` / `low_similarity`）；
- LLM 聚类 Prompt 与 `llm_min_confidence`；
- 候选数量与多样性约束（`candidates` 段）；
- Eligibility 规则（`relevance` 段）。

**可以修复**（不算破坏基线）：

- 抓取失败、页面错误、数据写入错误；
- 明确的幂等性或一致性缺陷；
- 不修复就无法继续运行的阻断问题。

任何行为修复必须在 `memory-bank/logs/changelog.md` 记录**生效日期**，分析时将修复前后的数据分组隔离，不混在同一组。

# Steps

## 阶段 1：影子运行（3—5 个工作日）

系统每天正常生成 Top 30 和简报，但**不要求团队使用**。管理者照常按原有方法选题，同时独立查看系统结果。

每日对照记录五项：

1. 系统发现了哪些人工也发现的趋势；
2. 系统**提前**发现了哪些趋势；
3. 人工发现但系统遗漏了什么；
4. 哪些候选属于明显误报；
5. 是否出现重复趋势或错误合并。

本阶段只验证 G3，**不评价发布表现**。阶段结束时运行一次 G3 报告确认无结构性问题：

```powershell
python scripts/observation/g3_report.py --output artifacts/observation/g3-report.md
```

## 阶段 2：辅助决策（至少 14 天）

管理者正式使用系统完成每日选题审核，保留人工最终决定权。开始积累 G4 数据。

标准工作流：

1. 系统生成约 30 个候选；
2. 管理者在 **60 分钟内**完成审核；
3. 选择 10—15 个方向，添加必要备注；
4. 导出简报（finalize 后不可变，`finalized_by` 记录操作者）；
5. 剪辑师自主采用；
6. 管理者记录采用情况和发布链接（发布 URL 全局唯一，同方向重复提交同一视频幂等，换视频会被拒绝）。

### 每日操作（额外记录 ≤ 5 分钟）

- 审核当天候选，选出 10—15 条；
- 对明显错误做快速标注（见下方"人工反馈字段"）；
- 记录采用与发布链接；
- 遇到严重错误**保留案例，不立即调参**；
- 记录：打开系统时间、完成审核时间、最终选择数量、是否额外去 YouTube/TikTok 人工搜索。

### 每周复盘（提假设，不改参数）

固定查看：

- Precision@15、Top 30 非目标内容比例、重复趋势占位；
- 自动合并与人工修正（合并/移出/回滚）次数；
- 平均审核时间、人工额外搜索时间；
- 候选 → 入选 → 采纳 → 发布漏斗；
- 已成熟发布记录的 PerformanceRatio、推荐到发布耗时；
- 失败任务与降级运行（`/admin/status`）。

每周可提出假设，但**至少积累两周数据后**再统一形成下一轮调整方案。周中运行：

```powershell
python scripts/observation/g3_report.py
python scripts/observation/g3_sample_export.py --output-dir artifacts/observation
python scripts/observation/g4_report.py --output-dir artifacts/observation
```

`g3_sample_export.py` 输出 `g3-calibration.csv`（可迭代标注）与 `g3-holdout-regression.csv`（冻结集，后续导出不重写既有行）。人工标注只在 CSV 上进行，标注取值：`correct_merge` / `false_merge` / `correct_new_theme` / `false_split` / `same_theme_different_angle` / `uncertain`。

### G3 抽样最低数量

| 类型 | 最低数量 |
|---|---|
| 自动合并 | 50 |
| LLM 灰区裁决 | 30 |
| 自动新建趋势 | 50 |
| lexical 降级 | 全部检查 |

### 必须收集的四类数据

1. **G3 聚类质量**：误合并率、误拆分率、Top 30 重复占位率、人工合并/移出/回滚频率、降级运行次数。
2. **使用效率**：每日审核时间、人工额外搜索时间、30 个候选中可用方向数。目标是审核 30—60 分钟内完成。
3. **业务漏斗**：`candidate → selected → adopted → published → performance_observed`。分别计算入选率（selected/candidate）、采纳率（adopted/selected）、发布转化率（published/adopted）、表现回收率（observed/已到成熟窗口的 published）。**管理者未选择 ≠ 系统推荐失败**（团队产能有限）。
4. **发布表现**：至少回收 24h / 72h / 7d 三个窗口。每条记录保存发布时 TrendScore 快照、生命周期快照、候选排名、推荐到发布耗时、Shorts/长视频、PerformanceRatio、基准置信度、是否晚录入。重点是**同龄表现 ÷ 频道同格式历史基准**，不是绝对播放量。

### 人工反馈字段

管理者侧（候选快速标注原因）：

`有价值` / `不相关` / `题材正确但角度一般` / `已经做过` / `发现太晚` / `证据不足` / `同一趋势重复` / `错误合并` / `错误拆分` / `团队无产能` / `版权或素材问题`

剪辑师侧（由管理者汇总）：

`采用` / `未采用` / `素材难找` / `不适合账号` / `角度不可执行` / `内容已经过热`

这些反馈用于区分问题在趋势发现、创作角度、团队流程还是制作资源，避免一律归因评分算法。

## 阶段 3：Beta 门评估

达到最低条件后运行正式评估：连续运行 ≥ 14 天、有效发布记录 ≥ 20 条、G3 人工标注达最低样本量。

注意样本量的解释力分层：

- **20 条**：只能证明链路通畅和初步方向；
- **50 条以上**：较可靠的校准；
- **约 100 条**：才建议真正调整评分权重。

# Verification

## Beta Ready 判定标准

### G3 技术门

- 连续真实运行 ≥ 14 天；
- 自动合并人工抽样 ≥ 50、新建趋势人工抽样 ≥ 50；
- 误合并率 ≤ 5%；
- 误拆分率 ≤ 15%;
- Top 30 重复占位率 ≤ 10%；
- 所有人工操作可回滚（快照式 rollback 验证通过）。

### G4 技术门

- 有效发布记录 ≥ 20；
- 至少一个成熟窗口快照覆盖率 ≥ 90%；
- 24h 和 72h 双窗口覆盖率 ≥ 75%；
- URL 解析与绑定正确率 ≥ 95%；
- PerformanceRatio 可追溯（基准版本 + 快照字段齐全）；
- 报告正确处理晚录入和未成熟窗口。

### 业务门

- 平均审核时间 ≤ 60 分钟；
- 每天至少选出 10 个可执行方向；
- Top 15 参考价值 ≥ 60%；
- 团队实际采用系统建议。

**技术门通过 ≠ Beta 成功**：若管理者仍需额外搜索 2 小时，或剪辑师基本不采用建议，不能宣布业务 Beta 成功。

## 试运行后的迭代决策

| 观察结果 | 下一步 |
|---|---|
| 误合并高 | 收紧自动合并阈值和硬约束 |
| 误拆分高 | 优化 Embedding 输入、召回和 LLM 裁决 |
| 非目标内容多 | 优化 Eligibility 与语言/领域分类 |
| 候选合理但不采用 | 改进创作方向与业务流程 |
| 采用多但表现一般 | 研究时效、账号适配和角度质量 |
| 高分与表现无关联 | 重新审视 TrendScore 构成 |
| 管理者时间仍高 | 优化页面信息密度和审核操作 |
| 无字幕导致方向空泛 | 再接选择性 ASR |

# Rollback

## 停止条件（暂停 Beta，先修复）

- 每日简报连续两次无法生成；
- 数据或历史 Brief 被错误覆盖；
- 人工决策被自动任务反向修改；
- 发布链接关联错误；
- 趋势合并导致历史记录不可追踪；
- Top 30 中明确非目标内容持续超过 20%；
- 误合并造成管理者无法可靠使用系统；
- 发布数据回收存在系统性错位。

暂停后按 [Recovery Guide](desiderium-recovery.md) 处理数据问题；行为缺陷修复后记录生效日期再恢复试运行，修复前后数据分组分析。

## 不需要停止（设计内可降级，记录即可）

- 个别 YouTube 视频无法读取；
- TikTok 实验模块失败；
- 某次 Embedding 降级为 lexical；
- 少量候选缺少字幕；
- 个别趋势需要人工拆分。

# Troubleshooting

- 任务失败 / worker 异常 / 配额耗尽：按 [Operations Manual](desiderium-ops.md) 与根目录 `RECOVERY.md` 路由。
- 发布指标回收失败：系统按 `max_consecutive_failures: 3` + `retry_backoff_hours: 24` 自动退避；连续失败达上限标记 terminal，需人工核对 URL。
- 误合并需回滚：使用快照式 `rollback_decision`（基于审计快照恢复，事务化、幂等）；已知冲突会抛 `RollbackConflict`，不会破坏后续人工修改。
- 晚录入发布：仅回补最近一个成熟窗口，报告中标记 `late entry`，不伪造历史窗口。

# Citations

- [Iteration 5 Plan](../plans/iteration-5-beta-observation.md)
- [Data Model Contract](../contracts/data-model-contract.md)
- [Operations Manual](desiderium-ops.md)
- [Recovery Guide](desiderium-recovery.md)
- `config/scoring.yaml`（基线参数）
- `scripts/observation/`（G3/G4 报告与抽样导出）
