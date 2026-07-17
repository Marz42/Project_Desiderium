---
type: paradigma-contract
title: Data Model Contract
description: PostgreSQL schema, unique constraints, and Alembic migration chain for Desiderium.
tags: [contract, database, schema, alembic]
timestamp: 2026-07-17T09:54:00+08:00
paradigma:
  schema_version: "0.1"
  temperature: warm
  lifecycle: evolving
  update_policy: requires-human-confirmation
  epistemic_status: confirmed
  contract_kind: database
  retrieval_hints:
    zh:
      - 数据库表
      - 唯一约束
      - 迁移链
      - 数据模型
    en:
      - database tables
      - unique constraints
      - migration chain
      - data model
  symbols:
    - app/models.py
    - metric_snapshots
    - trend_themes
    - creative_angles
  relations:
    depends_on:
      - /architecture.md
    related_to:
      - /contracts/web-api-contract.md
      - /domains/trend-engine.md
---

# Scope

`app/models.py` 中定义的全部 18 张表、关键唯一约束与索引，以及 `migrations/versions/` 的 Alembic 版本链。schema 变更必须经 Alembic 迁移并更新本契约。

# Contract

## Core business tables

| Table | Purpose | Key constraint |
|-------|---------|----------------|
| `watch_items` | 统一监控项（频道/账号/关键词/作品/榜单） | `UNIQUE(platform, type, external_id)` |
| `content_items` | 视频等原始内容 + `raw_payload` | `UNIQUE(platform, external_id)` |
| `metric_snapshots` | 指标时间序列（views/likes/comments/…） | `UNIQUE(content_item_id, captured_at_bucket)`；索引 `(content_item_id, captured_at)` |
| `transcripts` | 字幕 / 转录，状态机 pending→success/failed/unavailable | `UNIQUE(content_item_id, source)` |
| `channel_baselines` | 频道中位数速度基准（按年龄桶） | `UNIQUE(channel_external_id, platform, age_bucket)` |
| `trend_themes` | 趋势主题（跨日复用 ID），score + components + lifecycle | — |
| `trend_score_snapshots` | 每日趋势评分快照 | `UNIQUE(trend_id, snapshot_date)` |
| `trend_members` | 趋势 ↔ 视频，membership method rule/embedding/llm/manual | `UNIQUE(trend_id, content_item_id)` |
| `creative_angles` | 创作方向：angle_zh、format、evidence_content_ids、status、semantic_fingerprint | — |
| `daily_candidates` | 每日候选排序快照（历史可重现） | `UNIQUE(date, creative_angle_id)`；索引 `(date, rank)` |
| `briefs` / `brief_items` | 简报与条目（position 排序） | `UNIQUE(brief_date)`；`UNIQUE(brief_id, creative_angle_id)` |
| `angle_status_audits` | 状态机迁移审计 | 索引 `(creative_angle_id, created_at)` |
| `publication_records` | 已采用 / 已发布记录（url、日期） | — |
| `crawl_jobs` | 抓取任务追踪（adapter、status、retry、error） | 索引 `(status, adapter)` |

## Ops tables（Stage 8）

| Table | Purpose |
|-------|---------|
| `worker_heartbeats` | worker 心跳（component 主键，5 分钟一次） |
| `api_quota_daily` | 每日 API 配额用量（`UNIQUE(provider, usage_date)`） |
| `llm_usage_logs` | LLM token 用量与成本估算 |

## Enums

关键枚举（PostgreSQL native enum）：`watch_item_type`、`platform`、`watch_tier`、`crawl_outcome`、`source_quality`、`transcript_source/status`、`age_bucket`（0-6h/6-24h/24-72h/3-7d）、`baseline_confidence`、`topic_type`、`lifecycle_status`（new/rising/stable/declining/reviving/dormant）、`membership_method`、`creative_format`（short/long/both）、`angle_status`、`crawl_job_*`、`brief_status`、`publication_status`。

# Request Schema

数据访问统一经 `app/repositories/`；服务层不直接写 SQL。幂等写入使用 upsert（`ON CONFLICT` 于上表唯一约束）。

# Response Schema

不适用（进程内 ORM）。时间戳字段统一 `DateTime(timezone=True)`，UUID 主键（快照表用 BigInt 自增）。

# State Transitions

Alembic 迁移链（线性）：

```text
83f6909e9adb (initial schema, create_all 排除后续迁移的 5 张表)
  -> a1b2c3d4e5f6 (trend_score_snapshots)
  -> b2c3d4e5f6a7 (angle_status_audits)
  -> c8d9e0f1a2b3 (ops tables + ix_metric_snapshots_content_captured, if_not_exists)
```

Web 与 worker 容器启动时自动执行 `alembic upgrade head`。

# Compatibility Notes

- 新增表、可空列、索引向后兼容。
- 修改枚举值、唯一约束或删除列属破坏性变更。
- initial migration 基于 `create_all`，但通过 `LATER_REVISION_TABLES` 排除后续迁移拥有的表；新增表时必须写显式 op 脚本，并把表名加入该排除集合。
- `metric_snapshots` 按 `SNAPSHOT_RETENTION_DAYS`（默认 90 天）由每日任务清理，消费者不得假设无限历史。

# Breaking Change Policy

Schema 破坏性变更需用户确认、Alembic 迁移脚本、SemVer 评估，并同步更新本契约与相关 domain 文档。

# Citations

- [System Architecture](../architecture.md)
- [MVP Plan](../plans/mvp-plan.md)
