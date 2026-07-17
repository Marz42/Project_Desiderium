---
type: paradigma-known-issue
title: Hindi and Manhwa High-resonance False Positives in Trend Ranking
description: Non-target-language and manhwa recap content triggers cross-channel resonance and pollutes top candidates.
tags: [known-issue, scoring, clustering, language-filter]
timestamp: 2026-07-17T09:09:00+08:00
paradigma:
  schema_version: "0.1"
  temperature: cold
  lifecycle: evolving
  update_policy: agent-editable
  epistemic_status: confirmed
  retrieval_hints:
    zh:
      - 误报
      - 语言过滤
      - 影子验证
    en:
      - false positives
      - language filter
      - shadow validation
  relations:
    related_to:
      - /domains/trend-engine.md
---

# Symptom

Stage 1 影子验证（389 条真实视频、79 个频道）中，Hindi 语解说和 manhwa（韩漫）recap 内容形成高跨频道共振，进入趋势排名前列，但对目标市场（美国英语番剧解说）无参考价值。Precision@15 为 60%，误报主要来自这两类。

# Impact

- 排名前 15 的候选中最多约 40% 是管理者不会采用的内容，稀释每日审核效率。
- 共振分项（权重 35%）对这类内容天然敏感：同语种 / 同题材频道群会互相印证。

# Root Cause

- 聚类与评分只看标题实体与频道数量，不区分内容语言与题材（anime vs manhwa）。
- Watchlist 中的一般频道包含多语种 recap 频道，进一步放大共振信号。

# Workaround

- 管理者在审核时手动跳过；将明确无价值的频道在 Watchlist 中停用或降级为 experimental。
- Stage 1 已把这批案例记入 golden dataset 作为反例（`data/shadow/trend_labels.json` 的 manager value 标签）。

# Permanent Fix

- 在 normalize / 聚类阶段加入语言检测过滤（`content_items.language` 字段已预留）。
- 在趋势评分中加入 manager-value 惩罚项：被标记 blocked 的题材类别降低共振权重。
- 阈值与惩罚参数进 `config/scoring.yaml` 并在 golden dataset 上回归。

# Related Documents

- `memory-bank/knowledge/domains/trend-engine.md`
- `memory-bank/logs/progress/2026-07-17-stage-1-shadow-validation.md`

# Status

**Identified** — Stage 1 记录，Stage 2 校准计划中，永久修复未实施。
