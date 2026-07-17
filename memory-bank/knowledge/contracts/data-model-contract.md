---
type: paradigma-contract
title: Data Model Contract
description: PostgreSQL schema, unique constraints, and Alembic migration chain for Desiderium.
tags: [contract, database, schema, alembic]
timestamp: 2026-07-17T14:32:00+08:00
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

`app/models.py` 中定义的业务/运维表、关键唯一约束与索引，以及 `migrations/versions/` 的 Alembic 版本链。schema 变更必须经 Alembic 迁移并更新本契约。

# Contract

## Core business tables

| Table | Purpose | Key constraint |
|-------|---------|----------------|
| `watch_items` | 统一监控项（频道/账号/关键词/作品/榜单） | `UNIQUE(platform, type, external_id)` |
| `content_items` | 视频等原始内容 + `raw_payload` | `UNIQUE(platform, external_id)` |
| `metric_snapshots` | 指标时间序列（views/likes/comments/…） | `UNIQUE(content_item_id, captured_at_bucket)`；索引 `(content_item_id, captured_at)` |
| `transcripts` | 字幕 / 转录，状态机 pending→success/failed/unavailable | `UNIQUE(content_item_id, source)` |
| `channel_baselines` | 频道中位数速度基准（按年龄桶） | `UNIQUE(channel_external_id, platform, age_bucket)` |
| `trend_themes` | 趋势主题（跨日复用 ID），score + components + lifecycle；`active` / `merged_into_id` 支持人工合并归档 | — |
| `trend_score_snapshots` | 每日趋势评分快照 | `UNIQUE(trend_id, snapshot_date)` |
| `trend_members` | 趋势 ↔ 视频，membership method rule/embedding/llm/manual；`active`/`last_confirmed_at`/`deactivated_at` 软同步；`decision_version` 用于回滚冲突检测 | `UNIQUE(trend_id, content_item_id)` |
| `trend_facets` | G3：同主题不同卖点 facet | `UNIQUE(trend_id, facet_key)` |
| `embedding_cache` | G3：按 embedding_space + input_hash 缓存向量 | `UNIQUE(embedding_space, input_hash)` |
| `cluster_decision_audits` | G3：自动/人工聚类决策与回滚；`decision_version`/`rolled_back_at`/`rollback_audit_id` | 索引 `(target_trend_id, created_at)`；`UNIQUE(rollback_of_id)` |
| `creative_angles` | 创作方向：angle_zh、format、evidence_content_ids、status、semantic_fingerprint | `UNIQUE(trend_id, generated_date, semantic_fingerprint)` |
| `analysis_runs` | 候选/趋势发现等配置/算法/prompt 版本、config hash、run_fingerprint | 索引 `(run_date, run_kind)` |
| `daily_candidates` | 每日候选快照；`trend_score_snapshot` / `lifecycle_status_snapshot` 固化入选时点 | `UNIQUE(date, creative_angle_id)`；索引 `(date, rank)` |
| `briefs` / `brief_items` | 简报与条目；`finalized_*` 首次写入后不可变（含 `finalized_by`） | `UNIQUE(brief_date)`；`UNIQUE(brief_id, creative_angle_id)` |
| `angle_status_audits` | 状态机迁移审计 | 索引 `(creative_angle_id, created_at)` |
| `publication_records` | 已发布记录；关联 brief/daily_candidate；抓取退避字段 | `UNIQUE(platform, external_video_id)` |
| `publication_metric_snapshots` | G4 窗口快照；`baseline_version` / `observed_ratio_at_window` / `calculated_at` | `UNIQUE(publication_record_id, window_key)` |
| `crawl_jobs` | 抓取任务追踪（adapter、status、retry、error） | 索引 `(status, adapter)` |

## Ops tables（Stage 8）

| Table | Purpose |
|-------|---------|
| `worker_heartbeats` | worker 心跳（component 主键，5 分钟一次） |
| `api_quota_daily` | 每日 API 配额用量（`UNIQUE(provider, usage_date)`） |
| `llm_usage_logs` | LLM token 用量与成本估算 |

## Enums

关键枚举（PostgreSQL native enum）：`watch_item_type`、`platform`、`watch_tier`、`crawl_outcome`、`source_quality`、`transcript_source/status`、`age_bucket`（0-6h/6-24h/24-72h/3-7d）、`baseline_confidence`、`topic_type`、`lifecycle_status`（new/rising/stable/declining/reviving/dormant）、`membership_method`、`creative_format`（short/long/both）、`angle_status`、`crawl_job_*`、`brief_status`（draft/finalized/exported）、`publication_status`、`publication_fetch_status`（pending/success/failed，G4）、`publication_window_key`（initial/24h/72h/7d，G4）、`cluster_decision_action` / `cluster_decision_source`（G3）。

# Request Schema

数据访问统一经 `app/repositories/`；服务层不直接写 SQL。幂等写入使用 upsert（`ON CONFLICT` 于上表唯一约束）。

# Response Schema

不适用（进程内 ORM）。时间戳字段统一 `DateTime(timezone=True)`，UUID 主键（快照表用 BigInt 自增）。

# State Transitions

Alembic 迁移链（线性）：

```text
83f6909e9adb (initial schema, create_all 排除后续迁移拥有的表；LATER_REVISION_TABLES 含 publication_metric_snapshots)
  -> a1b2c3d4e5f6 (trend_score_snapshots)
  -> b2c3d4e5f6a7 (angle_status_audits)
  -> c8d9e0f1a2b3 (ops tables + ix_metric_snapshots_content_captured, if_not_exists)
  -> d4e5f6a7b8c9 (analysis_runs + daily_candidates FK + creative angle idempotency)
  -> e5f6a7b8c9d0 (G4: publication_records 扩展列 + FK、publication_metric_snapshots 新表、briefs 固化快照列；并含部分 G3 幂等创建逻辑)
  -> f6a7b8c9d0e1 (G3: trend_members soft-sync 列、embedding_cache / trend_facets / cluster_decision_audits；幂等补齐已 stamp 的 e5f6)
  -> a7b8c9d0e1f2 (Iteration 5: URL 唯一、finalize 不可变、membership 优先级/回滚、run_fingerprint、历史快照、抓取退避)
```

Compose 由一次性 `migrate` 服务执行 `alembic upgrade head`，Web 与 worker 仅在迁移成功后启动，禁止两者并发迁移。

# Compatibility Notes

- 新增表、可空列、索引向后兼容。
- 修改枚举值、唯一约束或删除列属破坏性变更。
- initial migration 基于当前模型 `create_all`；后续迁移必须同时支持 fresh create_all 路径与旧稳定 schema 升级路径，并在 CI 中验证 fresh、`c8d9e0f1a2b3 -> head`、downgrade/upgrade。
- `metric_snapshots` 按 `SNAPSHOT_RETENTION_DAYS`（默认 90 天）由每日任务清理，消费者不得假设无限历史。

# Breaking Change Policy

Schema 破坏性变更需用户确认、Alembic 迁移脚本、SemVer 评估，并同步更新本契约与相关 domain 文档。

# Citations

- [System Architecture](../architecture.md)
- [MVP Plan](../plans/mvp-plan.md)
