---
type: paradigma-known-issue
title: Transcript and Semantic Jobs Share Mutex Keys
description: transcript_fetch and semantic_analysis fall back to the same advisory lock ID and share CrawlJobAdapter.TRANSCRIPT batch keys, so they can block each other.
tags: [known-issue, scheduler, mutex, worker]
timestamp: 2026-07-17T09:43:00+08:00
paradigma:
  schema_version: "0.1"
  temperature: cold
  lifecycle: evolving
  update_policy: agent-editable
  epistemic_status: confirmed
  retrieval_hints:
    zh:
      - 任务互斥
      - advisory lock
      - 字幕任务
      - 语义任务
    en:
      - job mutex
      - advisory lock
      - transcript job
      - semantic job
  relations:
    related_to:
      - /contracts/scheduler-jobs-contract.md
      - /domains/semantic-analysis.md
---

# Symptom

`transcript_fetch` 与 `semantic_analysis` 未出现在 `LOCK_IDS` 中，因此都回退到 advisory lock `1999`。两者还使用相同的 `CrawlJobAdapter.TRANSCRIPT` + `CrawlJobType.TRANSCRIPT` 作为 running-batch 检查键。

# Impact

- 任一任务运行时，另一任务可能被跳过，即使调度时间不重叠也会因重试或手动触发而互相阻塞。
- 语义管道（每日 02:00）可能因字幕任务仍持有互斥而被静默跳过，导致当日无创作方向。

# Root Cause

`app/jobs/mutex.py` 的 `LOCK_IDS` 只覆盖 crawl / snapshot / trend / retention；字幕与语义任务共用默认锁与 crawl_jobs 批次键。

# Workaround

- 避免在字幕批次运行期间手动触发语义分析。
- 检查 worker 日志中的 `skipped: advisory lock held` / `another batch running`。

# Permanent Fix

- 为 `transcript_fetch` 与 `semantic_analysis` 分配独立 `LOCK_IDS`。
- 为语义任务使用独立的 adapter/job_type（或专用互斥路径），不再复用 TRANSCRIPT 批次键。
- 增加互斥单元测试，防止默认锁回退再次出现。

# Related Documents

- `app/jobs/mutex.py`
- `app/jobs/transcript_tasks.py`
- `app/jobs/semantic_tasks.py`
- `memory-bank/knowledge/contracts/scheduler-jobs-contract.md`

# Status

**Open — P1**（2026-07-17 代码审计确认）。
