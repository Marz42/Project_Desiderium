---
type: paradigma-contract
title: Scheduler Jobs Contract
description: APScheduler job registry, schedules, mutual exclusion, and failure isolation guarantees for the Desiderium worker.
tags: [contract, scheduler, worker, jobs]
timestamp: 2026-07-17T11:16:00+08:00
paradigma:
  schema_version: "0.1"
  temperature: warm
  lifecycle: evolving
  update_policy: requires-human-confirmation
  epistemic_status: confirmed
  contract_kind: scheduler
  retrieval_hints:
    zh:
      - 定时任务
      - 调度
      - 任务互斥
      - 心跳
    en:
      - scheduled jobs
      - worker
      - mutex
      - heartbeat
  symbols:
    - app/jobs/scheduler.py
    - app/worker.py
    - crawl_jobs
  relations:
    depends_on:
      - /architecture.md
    related_to:
      - /contracts/data-model-contract.md
      - /domains/watchlist-ingestion.md
      - /domains/trend-engine.md
---

# Scope

Worker 进程（`python -m app.worker`）注册的全部 APScheduler 任务、调度频率、互斥与失败隔离保证。任务注册集中在 `app/jobs/scheduler.py`。

# Contract

## Job registry

| Job ID | Schedule | Action |
|--------|----------|--------|
| `heartbeat` | 每 5 分钟 | 写 `worker_heartbeats`（含 DB 状态） |
| `crawl_priority` | 每 `CRAWL_PRIORITY_HOURS`（默认 5h） | 重点频道发现 + 详情 |
| `crawl_general` | 每 `CRAWL_GENERAL_HOURS`（默认 18h） | 一般频道发现 |
| `crawl_keywords` | 每日 `CRAWL_KEYWORD_HOUR`:00（默认 06:00） | 关键词搜索（配额预算内） |
| `crawl_retry` | 每 1 小时 | 失败任务重试（最多 3 次） |
| `metric_snapshots` | 每 4 小时 | 按视频年龄动态采集统计快照 |
| `trend_discovery` | 每日 01:30 UTC | 基准刷新 → 聚类 → 评分 → 生命周期 → 每日评分快照 → 候选生成 |
| `transcript_fetch` | 每 6 小时 | 重点视频公开字幕获取 |
| `semantic_analysis` | 每日 02:00 UTC（趋势发现之后） | LLM 语义层：命名 / 解释 / 创作方向 |
| `snapshot_retention` | 每日 03:30 UTC | 清理超过保留期的快照 |
| `disk_monitor` | 每 1 小时 | 磁盘阈值告警日志 |
| `publication_metrics` | 每 2 小时 | G4：按到期窗口（initial/24h/72h/168h，`config/scoring.yaml` 的 `publication.windows_hours`）拉取已发布视频的公开 YouTube 指标，计算 PerformanceRatio，逐记录错误隔离 |

TikTok 任务组（仅 `TIKTOK_ENABLED=true` 时注册）：`crawl_tiktok_accounts` / `crawl_tiktok_keywords` / `crawl_tiktok_rankings`（每 `TIKTOK_CRAWL_HOURS`，默认 12h）、`crawl_tiktok_retry`（每 `TIKTOK_RETRY_HOURS`，默认 2h）。

# Request Schema

任务无外部请求面；手动触发经 Web UI（`/watchlist/{id}/crawl`）调用 `crawl_single_item`。

# Response Schema

- 每次抓取批次写 `crawl_jobs` 记录（status: queued/running/success/partial/failed，items_processed，error_code/message）。
- 所有 job 注册 `max_instances=1` + `coalesce=True`。

# State Transitions

```text
crawl_jobs: queued -> running -> success | partial | failed
failed -> (crawl_retry, retry_count < 3) -> running
```

互斥三层：进程内锁 → PostgreSQL advisory lock → DB running-batch 检查（`app/jobs/mutex.py`）。每个 job 必须在 `LOCK_IDS` 有独立 ID；未知 job 直接失败，不允许回退共享默认锁。`transcript_fetch=1301`，`semantic_analysis=1302`，`publication_metrics=1401`。

# Compatibility Notes

- 调度频率全部来自 `Settings` / `config/`，可通过环境变量调整而不改代码。
- 顺序依赖：`semantic_analysis` 必须在 `trend_discovery` 之后（02:00 > 01:30）；调整任一 cron 需保持该顺序。
- 字幕是语义分析的软依赖：成功字幕优先；unavailable/failed 使用元数据降级；pending/running 不允许语义任务持锁等待。
- 字幕 `success` 是终态；`unavailable` 按 `config/llm.yaml` 的 7 天冷却重试。创作方向最终幂等由数据库 `(trend_id, generated_date, semantic_fingerprint)` 唯一约束保证。
- 失败隔离保证：TikTok 与 LLM 任务失败不得影响 YouTube 采集、趋势评分与简报生成。
- 配额保证：YouTube 配额耗尽时跳过关键词 / 作品搜索，频道抓取继续直至配额上限。
- `publication_metrics`：未配置 `YOUTUBE_API_KEY` 时整体跳过（记录日志，不算失败）；发布时（`AngleStatusService.transition` 到 `PUBLISHED`）还会做一次 best-effort 即时抓取，API 失败不回滚发布状态，记录保持 `fetch_status=pending/failed` 可重试。团队基准频道来自 `config/scoring.yaml` 的 `publication.team_channel_ids`（为空时用全量已发布记录作为低置信度兜底）。

# Breaking Change Policy

移除任务、更改任务顺序依赖或互斥机制属破坏性变更，需用户确认与 SemVer 评估。

# Citations

- [System Architecture](../architecture.md)
- [Data Model Contract](data-model-contract.md)
