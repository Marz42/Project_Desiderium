---
type: paradigma-decision
title: ADR-001 Single Worker with APScheduler and Database-backed Coordination
description: Decision to run scheduling in one APScheduler worker process with PostgreSQL-based mutex and heartbeat instead of Redis/Celery.
tags: [adr, scheduler, worker, infrastructure]
timestamp: 2026-07-17T09:09:00+08:00
paradigma:
  schema_version: "0.1"
  temperature: cold
  lifecycle: append-only
  update_policy: append-only
  epistemic_status: decision
  status: accepted
  retrieval_hints:
    zh:
      - 调度选型
      - 单 Worker
      - 无 Redis
    en:
      - scheduler choice
      - single worker
      - no redis
  relations:
    constrains:
      - /architecture.md
      - /contracts/scheduler-jobs-contract.md
---

# Context

系统监控项不超过 100 个，直接用户只有 1 名管理者。任务面（采集、快照、每日趋势管道、语义分析、运维清理）是低并发的周期性批处理，但需要防止重复运行和可观测的失败追踪。

# Decision

- 调度在单一 worker 进程内用 APScheduler（`python -m app.worker`），不引入 Redis / Celery / 消息队列。
- 任务互斥三层：进程内锁 + PostgreSQL advisory lock + `crawl_jobs` running-batch 检查。
- Worker 存活经数据库心跳（`worker_heartbeats`，每 5 分钟），由 `/health` 判定 stale。
- 任务失败落 `crawl_jobs` 表，由每小时重试任务收敛（最多 3 次）。

# Consequences

- 部署面最小化：Compose 只需 web / worker / postgres 三个核心服务。
- 任务队列语义（优先级、公平调度）不可用；所有并发控制依赖互斥而不是队列。
- 水平扩展 worker 需要先解决任务分片，当前明确不支持多 worker。
- 升级路径已在 mvp-plan 上位替代表中预留（Celery / Dramatiq / Temporal）。

# Alternatives Considered

- **Celery + Redis**：任务语义完整，但为单实例系统引入两个额外运行时依赖，运维成本不成比例。
- **系统 Cron + 独立脚本**：更简单，但缺少进程内互斥、心跳与统一日志上下文。

# Status

Accepted（Stage 0 起实施，Stage 8 补充心跳持久化）。

# Related Documents

- `memory-bank/knowledge/contracts/scheduler-jobs-contract.md`
- `memory-bank/knowledge/architecture.md`
