---
type: paradigma-domain
title: TikTok Experiment Domain
description: Isolated, default-off experimental TikTok adapter with cookie auth and low source confidence.
tags: [domain, tiktok, experiment, adapter, isolation]
timestamp: 2026-07-17T09:09:00+08:00
paradigma:
  schema_version: "0.1"
  temperature: warm
  lifecycle: evolving
  update_policy: agent-editable
  epistemic_status: confirmed
  retrieval_hints:
    zh:
      - TikTok
      - 实验适配器
      - 故障隔离
      - 来源置信度
    en:
      - tiktok
      - experimental adapter
      - failure isolation
      - source confidence
  symbols:
    - TikTokAdapter
    - TIKTOK_ENABLED
    - source_confidence
  relations:
    depends_on:
      - /architecture.md
    related_to:
      - /contracts/scheduler-jobs-contract.md
      - /decisions/adr-003-tiktok-isolated-experiment.md
---

# Responsibility

验证 TikTok 指定账号 / 关键词 / 标签榜单的有限抓取路径，不承担稳定性承诺。整个模块默认关闭，失败被完全隔离，不影响 YouTube 主流程。

# Public Interfaces

| Interface | Role | Path |
|-----------|------|------|
| `TikTokAdapter` | 实现 `SourceAdapter`：账号 / 关键词 / 榜单抓取（cookie-authenticated HTTP） | `app/adapters/tiktok/adapter.py` |
| `selectors.py` | 页面结构选择器版本隔离（v1，经 `config/tiktok.yaml`） | `app/adapters/tiktok/selectors.py` |
| `normalize_tiktok_video()` | 归一化到 content_items schema + `source_confidence: low` | `app/adapters/tiktok/normalize.py` |
| `TikTokIngestionService` | 独立采集管道（独立互斥与重试） | `app/services/tiktok_ingestion.py` |
| TikTok jobs | 仅 `TIKTOK_ENABLED=true` 时注册 | `app/jobs/tiktok_tasks.py` |

# Internal Flow

```text
TIKTOK_COOKIE (env, 日志脱敏) -> cookie 失效检测 (登录标记 / 401/403 / 重定向)
账号/关键词/榜单抓取 -> selectors v1 解析 -> normalize (source_confidence: low)
-> content_items upsert -> crawl_jobs (adapter=tiktok)
失败 -> 结构化 ERROR 日志 + 独立重试 (每 TIKTOK_RETRY_HOURS)
```

# Dependencies

- `config/tiktok.yaml`（选择器版本配置）。
- 环境变量：`TIKTOK_ENABLED`（默认 false）、`TIKTOK_COOKIE`、`TIKTOK_PAGE_VERSION`、`TIKTOK_CRAWL_HOURS`、`TIKTOK_RETRY_HOURS`。
- `app/domain/source_confidence.py`：置信度进入趋势评分权重（experimental 0.5）。

# Related Contracts

- `contracts/scheduler-jobs-contract.md` — TikTok 任务组注册条件与隔离保证。
- `contracts/config-deployment-contract.md` — cookie 密钥管理约束。

# Known Risks

- 页面结构变化随时可能使选择器失效；v1 失效时需要新增选择器版本而不是原地修补。
- Cookie 有效期不可控，失效检测只能事后发现。
- 抓取数据不保证完整性，不得单独用于认定高置信趋势（评分侧已降权）。
