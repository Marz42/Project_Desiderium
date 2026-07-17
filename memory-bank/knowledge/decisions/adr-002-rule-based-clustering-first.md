---
type: paradigma-decision
title: ADR-002 Deterministic Rule-based Clustering Before Embeddings and LLM
description: Decision to ship MVP trend clustering with an entity dictionary only, deferring vector recall and LLM adjudication.
tags: [adr, clustering, trends, llm-boundary]
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
      - 聚类决策
      - 规则优先
      - LLM 边界
    en:
      - clustering decision
      - rules first
      - llm boundary
  relations:
    constrains:
      - /domains/trend-engine.md
      - /domains/semantic-analysis.md
---

# Context

趋势聚类设计为三层（规则词典 → 文本向量召回 → LLM 歧义裁决）。MVP 时间盒内需要一个可解释、可回归、不依赖外部服务的聚类核心；同时项目原则要求 LLM 不得参与数值计算与趋势判定。

# Decision

- MVP 只实现第一层：基于 `config/anime_entities.yaml` 实体词典的规则聚类（`cluster_videos()`），带多频道过滤（≥2 成员且 ≥2 频道）。
- 趋势主题跨日按 entity / canonical name 匹配复用 ID，不每日重建。
- 向量召回与 LLM 裁决保留为设计目标（`trend_members.membership_method` 已预留 `embedding` / `llm` 枚举值），不在 MVP 交付。
- LLM 仅在聚类完成后处理语义任务（命名、解释、创作方向），且必须携带证据视频 ID。

# Consequences

- 聚类结果完全可解释、可用 golden dataset 回归；无外部依赖。
- 词典覆盖不到的新作品 / 别名会漏聚或误合并，需要人工维护词典。
- 同作品不同剧情事件的区分粒度受限于词典条目粒度。
- 引入 embedding 层时无需迁移 schema（枚举与 membership_score 已预留）。

# Alternatives Considered

- **直接上 embedding 聚类**：召回更广，但引入向量依赖且难以解释"为什么这两个视频是同一趋势"，与 MVP 可解释性验收冲突。
- **LLM 全权聚类**：违反"LLM 不判定趋势"的硬边界，成本与稳定性不可控。

# Status

Accepted（Stage 3 实施；第二 / 三层为 post-MVP，见 architecture Open Questions）。

# Related Documents

- `memory-bank/knowledge/domains/trend-engine.md`
- `memory-bank/knowledge/plans/mvp-plan.md`
