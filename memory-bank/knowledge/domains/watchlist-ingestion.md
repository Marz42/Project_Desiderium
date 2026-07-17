---
type: paradigma-domain
title: Watchlist and YouTube Ingestion Domain
description: Unified watchlist management and quota-aware YouTube content ingestion.
tags: [domain, watchlist, youtube, ingestion, crawl]
timestamp: 2026-07-17T09:09:00+08:00
paradigma:
  schema_version: "0.1"
  temperature: warm
  lifecycle: evolving
  update_policy: agent-editable
  epistemic_status: confirmed
  retrieval_hints:
    zh:
      - 监控列表
      - YouTube 采集
      - CSV 导入
      - 配额
    en:
      - watchlist
      - youtube crawl
      - csv import
      - quota
  symbols:
    - WatchlistService
    - YouTubeAdapter
    - IngestionService
    - crawl_jobs
  relations:
    depends_on:
      - /architecture.md
    related_to:
      - /contracts/scheduler-jobs-contract.md
      - /contracts/data-model-contract.md
---

# Responsibility

维护统一监控列表（频道 / 账号 / 关键词 / 作品 / 榜单，重点 / 一般 / 实验三级），并通过 YouTube Data API 稳定发现新视频、批量拉取详情、幂等写入 `content_items`。

# Public Interfaces

| Interface | Role | Path |
|-----------|------|------|
| `WatchlistService` | CRUD、CSV 导入（校验 + 去重）、启停、抓取状态 | `app/services/watchlist.py` |
| `IngestionService` | 发现 → 详情 → normalize → upsert 管道 | `app/services/ingestion.py` |
| `YouTubeAdapter` | 实现 `SourceAdapter`：频道 ID 解析、Uploads playlist、关键词搜索、批量详情（50 IDs） | `app/adapters/youtube/adapter.py` |
| `YouTubeClient` | 底层 API 调用、配额计数、指数退避 | `app/adapters/youtube/client.py` |
| Watchlist UI | 列表 / 编辑 / 导入 / 手动触发 | `app/web/routes/watchlist.py` |

# Internal Flow

```text
watch_items (enabled, tier) -> discover (uploads playlist / search.list)
  -> videos.list 批量详情 -> normalize.py (含 source_confidence: high)
  -> upsert content_items ON CONFLICT (platform, external_id)
  -> crawl_jobs 记录 + watch_items 状态回写 (last_success_at, consecutive_failures)
```

频道发现优先 Uploads playlist（低成本），`search.list` 仅用于关键词且受 `YOUTUBE_MAX_SEARCH_CALLS` 预算约束；游标增量抓取存于 `watch_items.config.page_token`。

# Dependencies

- YouTube Data API v3（配额：默认每日 10,000 单位，search 100 次）。
- `app/services/quota_tracker.py`：配额计数持久化到 `api_quota_daily`。
- 调度频率来自 `Settings`（见 scheduler-jobs contract）。

# Related Contracts

- `contracts/scheduler-jobs-contract.md` — 抓取任务频率与互斥。
- `contracts/data-model-contract.md` — `watch_items` / `content_items` / `crawl_jobs` 约束。

# Known Risks

- 配额耗尽时关键词搜索被跳过，仅频道抓取继续——新兴关键词趋势可能延迟一天发现。
- 频道 handle → channel ID 解析依赖 API 响应形态，YouTube 改版可能需要适配。
- `raw_payload` 全量保留会随时间增长，依赖快照保留策略以外的归档尚未实现。
