---
type: paradigma-plan
title: Iteration 5 Beta Observation and Calibration
description: Observation-only iteration to validate G3 duplicate reduction and G4 association signals on real traffic.
tags: [plan, beta, g3, g4, observation]
timestamp: 2026-07-17T14:32:00+08:00
paradigma:
  schema_version: "0.1"
  temperature: warm
  lifecycle: evolving
  update_policy: agent-editable
  epistemic_status: confirmed
  status: completed
  retrieval_hints:
    zh:
      - Beta 观察
      - G3 校准
      - G4 关联分析
    en:
      - beta observation
      - g3 calibration
      - g4 association
  relations:
    depends_on:
      - /plans/g3-g4-stabilization-plan.md
    related_to:
      - /domains/trend-engine.md
      - /domains/admin-web.md
---

# Goal

在真实流量上回答两个问题（不追求离线分数提升）：

1. **G3**：有界聚类是否稳定减少重复趋势，且误合并可接受？
2. **G4**：TrendScore、生命周期、创作方向是否与发布后表现存在可重复关联？

# Scope

## In scope

- 四处行为契约：URL 唯一、finalize 原子不可变、成员决策优先级、快照式回滚
- Analysis run 重试语义与 G4 历史快照
- G3/G4 只读观察脚本（calibration/holdout 隔离）
- PostgreSQL 并发集成测试

## Out of scope

- ASR、Profile 扩展、TikTok 强化
- 自动根据表现修改 TrendScore 权重
- 因果结论

# Approach

1. Red→Green 修复 URL 唯一约束与 finalize 原子性
2. 固化 membership 优先级与审计快照回滚
3. 扩展 schema（run_fingerprint、历史快照、抓取退避）
4. 补全单元/集成测试
5. 交付只读观察脚本
6. bump `0.10.0`

# Tasks

- [x] URL 唯一约束 + PublishedUrlConflict
- [x] Brief finalize 原子不可变 + finalized_by
- [x] may_reactivate_membership + sync_members 优先级
- [x] rollback_decision 快照恢复 + RollbackConflict
- [x] run_fingerprint + 候选/发布历史快照
- [x] g3_report / g3_sample_export / g4_report
- [x] 单元 + Postgres 集成 + MyPy + 迁移

# Status

**Completed** — 2026-07-17（0.10.0）。工程门已交付；G3 人工抽样与 G4 ≥14 天 / ≥20 条观察门仍待真实流量。
