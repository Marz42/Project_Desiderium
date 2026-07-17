---
type: paradigma-decision
title: ADR-003 TikTok as Isolated Default-off Experiment
description: Decision to keep the TikTok adapter fully isolated, disabled by default, and excluded from MVP acceptance.
tags: [adr, tiktok, isolation, source-confidence]
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
      - TikTok 决策
      - 实验隔离
      - 默认关闭
    en:
      - tiktok decision
      - experiment isolation
      - default off
  relations:
    constrains:
      - /domains/tiktok-experiment.md
      - /contracts/scheduler-jobs-contract.md
---

# Context

TikTok 官方 Display API 只能读取授权创作者自身内容，Research API 不向商业用户开放。全站热门数据只能靠页面抓取，稳定性不可承诺，而 MVP 验收要求 YouTube 主流程不受任何 TikTok 故障影响。

# Decision

- TikTok 模块整体默认关闭（`TIKTOK_ENABLED=false`），启用与否只影响 TikTok 任务组注册。
- 独立的 ingestion service、任务组、互斥与重试循环，与 YouTube 零共享平台逻辑。
- 抓取结果标记 `source_confidence: low`，趋势评分中实验来源权重 0.5，不得单独触发高置信趋势。
- Cookie 经 `TIKTOK_COOKIE` 环境变量注入，日志脱敏，不进 git。
- 页面选择器按版本隔离在 `config/tiktok.yaml`，改版时新增版本而非原地修改。
- TikTok 抓取稳定性不纳入 MVP 验收条件。

# Consequences

- YouTube 简报生成与 TikTok 状态完全解耦，故障演练验证通过。
- TikTok 数据价值受限（低置信、覆盖不全），仅作为佐证信号。
- 每次 TikTok 改版都是维护成本；若成为核心需求应切换商业数据供应商。

# Alternatives Considered

- **官方 API**：能力不匹配（无全站数据）。
- **商业数据供应商**：数据质量高但成本与 MVP 不匹配，列为上位替代。
- **不做 TikTok**：损失早期验证机会，且 Watchlist 模型已天然支持多平台。

# Status

Accepted（Stage 7 实施）。

# Related Documents

- `memory-bank/knowledge/domains/tiktok-experiment.md`
- `memory-bank/knowledge/contracts/scheduler-jobs-contract.md`
