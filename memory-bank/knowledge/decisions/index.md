# Decisions Index

Architecture decision records for the Desiderium application.

<!-- BEGIN PARADIGMA AUTO-INDEX -->
<!-- checksum: 54b34bb74e194951 -->
<!-- generated_by: pd-sync-index.py -->

| Path | Type | Title | Hints | Symbols | Relations |
|------|------|-------|-------|---------|-----------|
| [adr-001-single-worker-apscheduler.md](adr-001-single-worker-apscheduler.md) | `paradigma-decision` | ADR-001 Single Worker with APScheduler and Database-backed Coordination | 调度选型<br>单 Worker<br>无 Redis ... | - | constrains:/architecture.md<br>constrains:/contracts/scheduler-jobs-contract.md |
| [adr-002-rule-based-clustering-first.md](adr-002-rule-based-clustering-first.md) | `paradigma-decision` | ADR-002 Deterministic Rule-based Clustering Before Embeddings and LLM | 聚类决策<br>规则优先<br>LLM 边界 ... | - | constrains:/domains/trend-engine.md<br>constrains:/domains/semantic-analysis.md |
| [adr-003-tiktok-isolated-experiment.md](adr-003-tiktok-isolated-experiment.md) | `paradigma-decision` | ADR-003 TikTok as Isolated Default-off Experiment | TikTok 决策<br>实验隔离<br>默认关闭 ... | - | constrains:/domains/tiktok-experiment.md<br>constrains:/contracts/scheduler-jobs-contract.md |
| [adr-004-bounded-embedding-llm-clustering.md](adr-004-bounded-embedding-llm-clustering.md) | `paradigma-decision` | ADR-004 Bounded Embedding Recall and LLM Gray-zone Adjudication | 聚类决策<br>Embedding 召回<br>LLM 灰区裁决 ... | - | constrains:/domains/trend-engine.md<br>constrains:/domains/semantic-analysis.md<br>related_to:/decisions/adr-002-rule-based-clustering-first.md<br>related_to:/plans/g3-g4-stabilization-plan.md |

<!-- END PARADIGMA AUTO-INDEX -->
