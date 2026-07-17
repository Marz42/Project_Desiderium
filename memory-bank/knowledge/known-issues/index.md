# Known Issues Index

Recorded issues and their resolution status.

<!-- BEGIN PARADIGMA AUTO-INDEX -->
<!-- checksum: 0d0e6be6e8357949 -->
<!-- generated_by: pd-sync-index.py -->

| Path | Type | Title | Hints | Symbols | Relations |
|------|------|-------|-------|---------|-----------|
| [api-key-leak-in-shadow-cache.md](api-key-leak-in-shadow-cache.md) | `paradigma-known-issue` | API Keys Leaked into Shadow Data Cache | 密钥泄漏<br>事故记录<br>影子缓存 ... | - | related_to:/domains/watchlist-ingestion.md |
| [brief-lazyload-missing-greenlet.md](brief-lazyload-missing-greenlet.md) | `paradigma-known-issue` | Fresh Brief Row Triggers MissingGreenlet on First Read | MissingGreenlet<br>懒加载<br>简报 ... | - | related_to:/domains/admin-web.md<br>related_to:/contracts/data-model-contract.md |
| [cold-start-baseline-confidence.md](cold-start-baseline-confidence.md) | `paradigma-known-issue` | Cold-start Channel Baselines Have Low Confidence | 冷启动<br>基准置信度<br>快照积累 ... | - | related_to:/domains/trend-engine.md |
| [dev-dockerfile-missing-config.md](dev-dockerfile-missing-config.md) | `paradigma-known-issue` | Development Dockerfile Omits Runtime Config Directory | 开发镜像<br>config 缺失<br>Dockerfile ... | - | related_to:/contracts/config-deployment-contract.md<br>related_to:/domains/operations.md |
| [fresh-database-migration-fails.md](fresh-database-migration-fails.md) | `paradigma-known-issue` | Fresh Database Migration Fails After Initial Revision | 全新数据库迁移失败<br>Alembic<br>部署阻断 ... | - | related_to:/contracts/data-model-contract.md<br>related_to:/contracts/config-deployment-contract.md |
| [shadow-validation-false-positives.md](shadow-validation-false-positives.md) | `paradigma-known-issue` | Hindi and Manhwa High-resonance False Positives in Trend Ranking | 误报<br>语言过滤<br>影子验证 ... | - | related_to:/domains/trend-engine.md |
| [transcript-semantic-mutex-collision.md](transcript-semantic-mutex-collision.md) | `paradigma-known-issue` | Transcript and Semantic Jobs Share Mutex Keys | 任务互斥<br>advisory lock<br>字幕任务 ... | - | related_to:/contracts/scheduler-jobs-contract.md<br>related_to:/domains/semantic-analysis.md |
| [trend-consistency-baseline-drift.md](trend-consistency-baseline-drift.md) | `paradigma-known-issue` | Trend Consistency Baseline Drift Between Production and Golden Paths | 趋势一致性<br>relevance<br>生命周期 ... | - | related_to:/domains/trend-engine.md<br>related_to:/plans/g3-g4-stabilization-plan.md |

<!-- END PARADIGMA AUTO-INDEX -->
