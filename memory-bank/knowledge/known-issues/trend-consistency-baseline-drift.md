---
type: paradigma-known-issue
title: Trend Consistency Baseline Drift Between Production and Golden Paths
description: Production trend pipeline dropped relevance multipliers, used video counts instead of distinct channels for the formal threshold, and stored momentum as activity_24h.
tags: [known-issue, trends, scoring, lifecycle, g3]
timestamp: 2026-07-17T13:13:00+08:00
paradigma:
  schema_version: "0.1"
  temperature: cold
  lifecycle: evolving
  update_policy: agent-editable
  epistemic_status: confirmed
  retrieval_hints:
    zh:
      - 趋势一致性
      - relevance
      - 生命周期
    en:
      - trend consistency
      - relevance
      - lifecycle
  relations:
    related_to:
      - /domains/trend-engine.md
      - /plans/g3-g4-stabilization-plan.md
---

# Symptom

生产趋势管道与 G2 golden 路径不一致：generic 内容在生产侧未按相关性降权；正式趋势门用 72h 视频数而非频道数；生命周期 growth ratio 比较的是不同量纲。

# Impact

- G2 relevance 过滤在生产评分中失效或减弱。
- 弱聚类可能被持久化为趋势主题。
- 生命周期状态（rising/declining/reviving）可能被错误判定。
- 在此基础上引入 Embedding 会放大误合并与 ID churn。

# Root Cause

1. `assignments_to_member_rows()` 未传递 `relevance_multiplier`。
2. `score_trend_cluster()` 的 `meets_standard_threshold` 使用 `recent_72h` 视频计数。
3. `trend_discovery` 将 `momentum` 写入 `activity_24h`，而 lifecycle 读取该字段与 `cluster_activity()` 比较。
4. `replace_members()` 每日删除重建，丢失首次加入时间。

# Workaround

G3 Phase 0 之前不要启用自动跨表述合并。

# Permanent Fix

0.9.0 已修复：`relevance_multiplier` 传入成员行；正式门使用 72h distinct channels；`activity_24h` 存 `cluster_activity`；成员 soft-sync；golden builder 调用生产 `cluster_videos`。

# Related Documents

- `app/services/clustering.py`
- `app/services/trend_discovery.py`
- `app/services/scoring.py`
- `app/domain/trend_metrics.py`
- `memory-bank/knowledge/domains/trend-engine.md`
- `memory-bank/knowledge/plans/g3-g4-stabilization-plan.md`

# Status

**Resolved - 0.9.0**
