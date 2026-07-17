---
type: paradigma-progress-log
title: Iteration 5 Beta Observation
description: Progress log for Iteration 5 integrity contracts, observation tools, and 0.10.0 release.
tags: [progress, iteration-5, g3, g4, observation]
timestamp: 2026-07-17 14:32
paradigma:
  layer: logs
  temperature: cold
  lifecycle: archived
  okf_export: false
---

# Iteration 5: Beta Observation and Calibration

## Summary

交付 0.10.0：四处行为契约修复（URL 唯一、finalize 原子不可变、成员决策优先级、快照式回滚）、Analysis run 重试语义、G4 历史快照与失败退避、G3/G4 只读观察脚本，以及 PostgreSQL 并发集成测试。

## Completed

- `UNIQUE(platform, external_video_id)` 迁移 + `PublishedUrlConflict` + 同 angle 幂等
- Brief `finalize` 条件原子更新 + `finalized_by`
- `may_reactivate_membership` + `sync_members` 优先级
- `rollback_decision` 基于 evidence 快照恢复 + `RollbackConflict`
- `analysis_runs.run_fingerprint`；移除 `(run_date, run_kind)` 唯一约束
- `daily_candidates` 历史 score/lifecycle 快照；publication 基准版本与 observed ratio
- `scripts/observation/g3_report.py`、`g3_sample_export.py`、`g4_report.py`

## Verification

- Unit: 140+ passed
- Integration (Postgres): publication URL 并发、finalize 并发、G3 membership/rollback 通过
- MyPy: 0 errors
- Migration: fresh DB `alembic upgrade head` 通过

## Remaining (observation gates)

- 真实流量 G3 人工抽样误合并/误拆分率
- G4 ≥14 天 / ≥20 条发布表现关联观察

## Follow-up (2026-07-17 14:45)

- 修复 `semantic_analysis._load_members` 仅加载 `active=True` 成员
- 已发布 angle 重复提交：同视频幂等、换视频抛 `PublishedUrlChangeConflict`（web 层 flash 提示）
- 新增 `manuals/desiderium-beta-trial.md`：三阶段试运行手册（影子运行 / 辅助决策 / Beta 门评估），含基线冻结、四类数据收集、每日每周节奏、停止条件与 Beta Ready 判定
