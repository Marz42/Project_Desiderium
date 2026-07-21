---
type: paradigma-runtime-state
title: Active Task
description: Current active task state for the Agent session.
tags: [runtime, active-task]
timestamp: 2026-07-21T10:01:00+08:00
paradigma:
  layer: runtime
  temperature: hot
  lifecycle: ephemeral
  okf_export: false
  update_policy: agent-editable
  archive_to: /memory-bank/logs/progress/
---

# Active Task

## Task ID

2026-07-21-pipeline-snapshot-greenlet-fixes

## User Request

修复管道测试发现的两个 bug：metric snapshots 日志 `created` KeyError；trend discovery baseline 路径 MissingGreenlet。验证后提交。

## Current Status

completed — 两处已修复并验证通过。

## Checklist

- [x] 将 snapshot summary 的 `created` 重命名为 `snapshots_created`（避免 LogRecord 保留字段冲突）
- [x] `list_content_for_baseline` 对 `metric_snapshots` 使用 `selectinload`
- [x] 运行 `capture_metric_snapshots`（无 KeyError）
- [x] 运行 `run_trend_discovery`（无 MissingGreenlet；channel_baselines=2）
- [x] `pytest tests/ -v --tb=short`（152 passed, 8 skipped）
- [x] 检查 DB 计数并更新 memory-bank / commit

## Relevant Knowledge

- `knowledge/domains/trend-engine.md`
- `knowledge/known-issues/brief-lazyload-missing-greenlet.md`
- `knowledge/contracts/scheduler-jobs-contract.md`

## Blockers

无。

## Notes

- Entry points live in `app/jobs/trend_tasks.py`（非 services 模块顶层函数）。
- discovery 已跑通 baseline；`trend_themes` / `creative_angles` 仍为 0（聚类未达阈值，非崩溃）。
- 提交时排除 `.git-rewrite/`、`data/shadow/fetch_meta.json`（密钥风险）、以及无关的 `cursor-comm-log.md` / `scripts/shadow/watchlist.csv` 改动。
