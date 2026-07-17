---
type: paradigma-plan
title: G3/G4 Stabilization Plan
description: Beta release gates for trend consistency, publication performance feedback, and blocking MyPy after G1/G2.
tags: [plan, beta, g3, g4, mypy, clustering, publication]
timestamp: 2026-07-17T13:13:00+08:00
paradigma:
  schema_version: "0.1"
  temperature: warm
  lifecycle: evolving
  update_policy: agent-editable
  epistemic_status: confirmed
  status: completed
  retrieval_hints:
    zh:
      - G3 趋势一致性
      - G4 发布表现
      - MyPy
    en:
      - trend consistency
      - publication performance
      - mypy
  relations:
    depends_on:
      - /project-brief.md
      - /architecture.md
      - /plans/beta-stabilization-plan.md
    related_to:
      - /decisions/adr-004-bounded-embedding-llm-clustering.md
      - /domains/trend-engine.md
      - /domains/admin-web.md
---

# Goal

在 G1/G2 已通过的基础上完成 **G3 Trend Consistency**、**G4 Business Verifiability（公开数据表现回收）**，并将 MyPy 从 advisory 升级为 CI 阻断门。里程碑保持：`MVP Feature Complete / Beta Readiness: Not Ready`，直到真实流量观察通过。

# Scope

## In scope

- G3 Phase 0：生产/golden 一致性基线修复。
- G3：规则硬约束 + 本地 ONNX Embedding 有限召回 + LLM 灰区裁决 + 人工可回滚操作。
- G4：published URL 录入、公开 YouTube 指标四窗口回收、PerformanceRatio 关联分析与后台展示。
- Brief GET 只读与显式 finalize；MyPy zero + blocking CI。

## Out of scope

- 反向修改 TrendScore 权重。
- YouTube OAuth / Analytics API。
- TikTok 发布回收、自动发现未关联视频。
- 完整审核计时与独立“参考价值”标签矩阵。
- 独立向量数据库。

# Release Gates

| Gate | Auto / Runtime | Criteria |
|------|----------------|----------|
| G3 | Auto + sample review | Top30 同主题重复占位相对基线 ↓≥30%；误合并 ≤5%；误拆分 ≤15%；自动合并可解释可回滚；不破坏历史 brief/angle/publication |
| G4 code | Auto | URL 解析 ≥90% fixture；四窗口幂等；单条失败隔离；≥80% published fixtures 有有效快照 |
| G4 live | Observation | ≥14 天、≥20 条有效发布后才宣称通过 |
| MyPy | Auto | `mypy app` 零错误且 CI blocking |

# Approach

1. 固化 ADR 与 known issues。
2. 修复 G3 一致性基线后再上 Embedding。
3. 清零 MyPy 并改为阻断。
4. 实现有界召回/裁决与人工操作。
5. 实现发布表现回收与只读简报流程。
6. 全量验证并 bump `0.9.0`。

# Tasks

- [x] Gate docs / ADR / known issues
- [x] G3 consistency baseline
- [x] MyPy zero + blocking CI
- [x] G3 bounded clustering
- [x] G4 publication performance loop
- [x] Verify + memory-bank sync

# Status

**Completed** — 2026-07-17（0.9.0）。代码与自动门已交付；真实流量观察门仍开放。
