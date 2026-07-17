---
type: paradigma-domain
title: Trend Engine Domain
description: Metric snapshots, channel baselines, BreakoutRatio, rule-based clustering, composite scoring, and trend lifecycle.
tags: [domain, trends, scoring, baselines, clustering]
timestamp: 2026-07-17T09:09:00+08:00
paradigma:
  schema_version: "0.1"
  temperature: warm
  lifecycle: evolving
  update_policy: agent-editable
  epistemic_status: confirmed
  retrieval_hints:
    zh:
      - 趋势评分
      - 频道基准
      - 聚类
      - 生命周期
    en:
      - trend scoring
      - channel baseline
      - clustering
      - lifecycle
  symbols:
    - BreakoutRatio
    - trend_metrics
    - TrendDiscovery
    - config/scoring.yaml
  relations:
    depends_on:
      - /architecture.md
    related_to:
      - /contracts/data-model-contract.md
      - /contracts/scheduler-jobs-contract.md
      - /known-issues/cold-start-baseline-confidence.md
---

# Responsibility

不依赖 LLM 的趋势发现核心：将统计快照转化为频道基准与单视频异常评分，用规则聚类形成跨日持续的趋势主题，并计算综合评分与生命周期状态。

# Public Interfaces

| Interface | Role | Path |
|-----------|------|------|
| `app/domain/trend_metrics.py` | 纯算法：年龄桶、速度、冷启动估算、中位数基准、capped BreakoutRatio | domain 层，无 I/O |
| `SnapshotService` | 按视频年龄动态调度快照（5h / 10h / 24h），负增量异常标记 | `app/services/snapshots.py` |
| `BaselineService` | 频道基准刷新（样本量 → low/medium/high 置信度，全局回退） | `app/services/baseline.py` |
| `cluster_videos()` | 规则聚类（实体词典 + 多频道过滤） | `app/services/clustering.py` |
| `ScoringService` / `LifecycleService` | 综合评分与状态迁移 | `app/services/scoring.py`, `lifecycle.py` |
| `TrendDiscovery` | 每日管道编排 + 评分快照 + 候选生成挂钩 | `app/services/trend_discovery.py` |

# Internal Flow

```text
metric_snapshots -> velocity (增量 / 冷启动估算)
channel_baselines (相同年龄桶中位数) -> BreakoutRatio = velocity / max(baseline, ε), capped at 8
标题/实体 -> cluster_videos (anime_entities.yaml, ≥2 成员且 ≥2 频道)
  -> trend_themes upsert (entity/canonical_name 匹配复用旧 ID)
  -> 综合评分: 共振 0.35 + 异常 0.25 + 动量 0.20 + 持续 0.10 + 规模 0.05 + 新鲜度 0.05
  -> lifecycle: new/rising/stable/declining/reviving/dormant (growth ratio 阈值)
  -> trend_score_snapshots (每日一条)
```

正式趋势门槛：72h 内 ≥3 频道且 ≥50% 视频 BreakoutRatio ≥ 2；或早期信号（24h 内 ≥2 频道、1 条 ≥4 + 佐证）。

# Dependencies

- `config/scoring.yaml`：全部权重与阈值（服务不硬编码）。
- `config/anime_entities.yaml`：实体词典（17 条规则起步）。
- Stage 1 golden dataset（`data/shadow/golden_dataset.csv`）作为回归基线。

# Related Contracts

- `contracts/data-model-contract.md` — snapshots / baselines / trends 表约束。
- `contracts/scheduler-jobs-contract.md` — 01:30 UTC 每日管道与 4h 快照任务。

# Known Risks

- 冷启动期基准置信度低（见 known-issue），低置信基准不应单独触发高置信趋势。
- 聚类仅第一层规则实现；同作品不同剧情可能误合并，向量召回与 LLM 裁决是后续工作。
- Hindi / manhwa 高共振误报待语言过滤校准（见 known-issue）。
