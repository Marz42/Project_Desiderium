---
type: paradigma-decision
title: ADR-004 Bounded Embedding Recall and LLM Gray-zone Adjudication
description: Evolve clustering beyond rules-only by allowing bounded embedding recall and constrained LLM adjudication without global free clustering.
tags: [adr, clustering, embedding, llm, trends]
timestamp: 2026-07-17T11:54:00+08:00
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
      - Embedding 召回
      - LLM 灰区裁决
    en:
      - clustering decision
      - embedding recall
      - llm adjudication
  relations:
    constrains:
      - /domains/trend-engine.md
      - /domains/semantic-analysis.md
    related_to:
      - /decisions/adr-002-rule-based-clustering-first.md
      - /plans/g3-g4-stabilization-plan.md
---

# Context

ADR-002 为 MVP 冻结在规则词典聚类。Beta 需要降低跨表述重复占位，但不能引入无约束全局向量聚类或 LLM 全权判定。调研显示在上第二层前必须先修复生产一致性偏差（relevance 传递、正式趋势门、生命周期活动值、成员历史）。

# Decision

- 规则层始终是硬约束：语言/领域兼容、发布时间差 ≤7 天、不同动漫作品禁止合并、同作品下角色/篇章/事件明显冲突禁止自动合并。
- Embedding 只做有限召回：默认 Worker 内本地 Sentence Transformers + ONNX Runtime CPU；保留显式远程 API provider；禁止不同模型/embedding-space 静默混用；不可用时降级到规则/词法召回，不阻断主流程。
- 自动决策三段式（阈值配置化）：高相似度自动归入已有趋势；低相似度创建新趋势；中间灰区才调用 LLM。
- LLM 只输出有限枚举动作：`merge_same_angle`、`merge_theme_keep_angles_separate`、`create_new_theme`、`needs_review`；低置信转人工。
- 不自动重写已有历史简报或已有发布记录的两个趋势；不物理删除被合并趋势；人工合并/移出必须可审计且可回滚。

# Consequences

- 跨表述召回能力提升，同时保持可解释与可回滚。
- Worker 镜像需要预置固定 revision 的本地模型；Web 进程不加载模型。
- 需要新的决策审计、facet、embedding cache 与 G3 golden pair 回归。
- ADR-002 的“MVP 只做规则层”结论被本 ADR 在 Beta 阶段显式演进，而非废止规则优先原则。

# Alternatives Considered

- **继续仅规则聚类**：无法解决同主题跨表述重复占位。
- **全局 embedding 聚类**：解释性差、误合并风险高、运维重。
- **LLM 全权聚类**：违反证据边界与稳定性要求。

# Status

Accepted — Beta G3 实施依据。

# Related Documents

- `memory-bank/knowledge/decisions/adr-002-rule-based-clustering-first.md`
- `memory-bank/knowledge/plans/g3-g4-stabilization-plan.md`
- `memory-bank/knowledge/domains/trend-engine.md`
