---
type: paradigma-domain
title: Operations Domain
description: Production monitoring, backup, retention, and cost tracking for the deployed Desiderium stack.
tags: [domain, ops, monitoring, backup, quota]
timestamp: 2026-07-17T09:09:00+08:00
paradigma:
  schema_version: "0.1"
  temperature: warm
  lifecycle: evolving
  update_policy: agent-editable
  epistemic_status: confirmed
  retrieval_hints:
    zh:
      - 运维
      - 监控
      - 备份
      - 成本追踪
    en:
      - operations
      - monitoring
      - backup
      - cost tracking
  symbols:
    - /admin/status
    - worker_heartbeats
    - scripts/backup.sh
  relations:
    depends_on:
      - /architecture.md
    related_to:
      - /manuals/desiderium-ops.md
      - /manuals/desiderium-recovery.md
      - /contracts/config-deployment-contract.md
---

# Responsibility

保障单实例生产系统的可观测性与可恢复性：健康检查、worker 心跳、API 配额与 LLM 成本追踪、快照保留、磁盘监控、数据库备份与恢复。

# Public Interfaces

| Interface | Role | Path |
|-----------|------|------|
| `GET /health` | DB + 磁盘 + worker 心跳综合状态 | `app/services/system_health.py` |
| `GET /admin/status` | 24h 任务失败、YouTube 配额、当日 LLM 成本、快照统计 | `app/services/ops_status.py` |
| `OpsRepository` | heartbeats / quota / llm usage 数据访问 | `app/repositories/ops.py` |
| `snapshot_retention` job | 每日清理超期快照（默认 90 天） | `app/services/snapshot_retention.py` |
| Ops scripts | backup / restore / disk_monitor / optimize_db_indexes | `scripts/` |
| Log rotation | 主机部署 logrotate 配置 | `config/logrotate.desiderium` |

# Internal Flow

```text
worker heartbeat (5min) -> worker_heartbeats -> /health worker.stale 判定 (WORKER_STALE_MINUTES)
crawl/snapshot 批次 -> api_quota_daily (provider=youtube)
semantic 调用 -> llm_usage_logs -> /admin/status 当日成本
backup sidecar (daily) -> backups/desiderium-<UTC>.sql.gz (保留 BACKUP_RETENTION_DAYS)
disk_monitor (hourly) -> 超过 DISK_WARN_PERCENT 记录告警
```

# Dependencies

- Stage 8 ops 表（`worker_heartbeats` / `api_quota_daily` / `llm_usage_logs`）。
- 生产拓扑与环境变量见 config-deployment contract。
- 恢复流程 canonical 版本：根目录 `RECOVERY.md`。

# Related Contracts

- `contracts/config-deployment-contract.md` — 环境变量与 compose 服务。
- `contracts/web-api-contract.md` — `/health` 与 `/admin/status` 的响应约定。

# Known Risks

- 告警只有结构化日志，没有主动推送通道（邮件 / IM）；需要外部日志采集或 cron 钩子消费。
- 备份是本地卷，未做异地副本；主机磁盘故障会同时丢失数据与备份。
- `optimize_db_indexes.py` 为手动流程，数据量增长后的慢查询依赖人工触发。
