# Desiderium Knowledge Index

Agent 路由指南：先读取 runtime active task，再读取本 index，根据任务选择最相关的 1-3 个文档继续阅读。One-shot retrieval 是第一跳，不是终点。

## HOT Knowledge

* [Project Brief](project-brief.md) - Desiderium 的愿景、用户、范围与验收标准。
* [System Architecture](architecture.md) - 应用架构：Web / Worker / 适配器、模块边界与数据流。
* [Conventions](conventions.md) - 编码、测试、文档与双轨版本规范。
* [Repository Contract](contracts/repository-contract.md) - 仓库布局与 harness 工具契约。

## WARM Knowledge

* [Contracts](contracts/) - Web API、数据模型、调度任务、配置部署契约。
* [Domains](domains/) - 采集、趋势引擎、语义分析、管理后台、TikTok 实验、运维。
* [Plans](plans/) - MVP 计划（completed，含完整产品规格）。

## COLD Knowledge

* [Decisions](decisions/) - 应用架构决策记录（ADR）。
* [Known Issues](known-issues/) - 已知问题与事故记录。
* [Manuals](manuals/) - 运维与恢复手册（canonical：根目录 OPS.md / RECOVERY.md）。
* [Glossary](glossary.md) - 业务术语表。

<!-- BEGIN PARADIGMA AUTO-INDEX -->
<!-- checksum: aeb45368ce2629ed -->
<!-- generated_by: pd-sync-index.py -->

| Path | Type | Title | Hints | Symbols | Relations |
|------|------|-------|-------|---------|-----------|
| [architecture.md](architecture.md) | `paradigma-architecture` | System Architecture | 系统架构<br>模块边界<br>数据流 ... | app/main.py<br>app/worker.py<br>SourceAdapter ... | related_to:/contracts/repository-contract.md<br>related_to:/contracts/web-api-contract.md<br>related_to:/contracts/data-model-contract.md<br>related_to:/contracts/scheduler-jobs-contract.md |
| [contracts/config-deployment-contract.md](contracts/config-deployment-contract.md) | `paradigma-contract` | Config and Deployment Contract | 环境变量<br>配置<br>部署 ... | .env.example<br>config/scoring.yaml<br>docker-compose.prod.yml | depends_on:/architecture.md<br>related_to:/manuals/desiderium-ops.md<br>related_to:/domains/operations.md |
| [contracts/data-model-contract.md](contracts/data-model-contract.md) | `paradigma-contract` | Data Model Contract | 数据库表<br>唯一约束<br>迁移链 ... | app/models.py<br>metric_snapshots<br>trend_themes ... | depends_on:/architecture.md<br>related_to:/contracts/web-api-contract.md<br>related_to:/domains/trend-engine.md |
| [contracts/repository-contract.md](contracts/repository-contract.md) | `paradigma-contract` | Repository Contract | 仓库契约<br>目录布局<br>工具命令 ... | VERSION<br>pd-check-all.py<br>docker-compose.prod.yml | depends_on:/architecture.md<br>related_to:/contracts/web-api-contract.md<br>related_to:/contracts/data-model-contract.md<br>related_to:/contracts/scheduler-jobs-contract.md ... |
| [contracts/scheduler-jobs-contract.md](contracts/scheduler-jobs-contract.md) | `paradigma-contract` | Scheduler Jobs Contract | 定时任务<br>调度<br>任务互斥 ... | app/jobs/scheduler.py<br>app/worker.py<br>crawl_jobs | depends_on:/architecture.md<br>related_to:/contracts/data-model-contract.md<br>related_to:/domains/watchlist-ingestion.md<br>related_to:/domains/trend-engine.md |
| [contracts/web-api-contract.md](contracts/web-api-contract.md) | `paradigma-contract` | Web API Contract | API 路由<br>认证<br>健康检查 ... | AuthMiddleware<br>/health<br>/admin/status ... | depends_on:/architecture.md<br>related_to:/contracts/data-model-contract.md<br>related_to:/domains/admin-web.md |
| [conventions.md](conventions.md) | `paradigma-convention` | Coding and Collaboration Conventions | 代码规范<br>测试规范<br>版本规则 ... | SemVer<br>VERSION<br>pytest ... | constrains:/contracts/repository-contract.md |
| [decisions/adr-001-single-worker-apscheduler.md](decisions/adr-001-single-worker-apscheduler.md) | `paradigma-decision` | ADR-001 Single Worker with APScheduler and Database-backed Coordination | 调度选型<br>单 Worker<br>无 Redis ... | - | constrains:/architecture.md<br>constrains:/contracts/scheduler-jobs-contract.md |
| [decisions/adr-002-rule-based-clustering-first.md](decisions/adr-002-rule-based-clustering-first.md) | `paradigma-decision` | ADR-002 Deterministic Rule-based Clustering Before Embeddings and LLM | 聚类决策<br>规则优先<br>LLM 边界 ... | - | constrains:/domains/trend-engine.md<br>constrains:/domains/semantic-analysis.md |
| [decisions/adr-003-tiktok-isolated-experiment.md](decisions/adr-003-tiktok-isolated-experiment.md) | `paradigma-decision` | ADR-003 TikTok as Isolated Default-off Experiment | TikTok 决策<br>实验隔离<br>默认关闭 ... | - | constrains:/domains/tiktok-experiment.md<br>constrains:/contracts/scheduler-jobs-contract.md |
| [domains/admin-web.md](domains/admin-web.md) | `paradigma-domain` | Admin Web Domain | 管理后台<br>每日审核<br>简报导出 ... | AuthMiddleware<br>brief_export<br>angle_status ... | depends_on:/architecture.md<br>related_to:/contracts/web-api-contract.md<br>related_to:/contracts/data-model-contract.md |
| [domains/operations.md](domains/operations.md) | `paradigma-domain` | Operations Domain | 运维<br>监控<br>备份 ... | /admin/status<br>worker_heartbeats<br>scripts/backup.sh | depends_on:/architecture.md<br>related_to:/manuals/desiderium-ops.md<br>related_to:/manuals/desiderium-recovery.md<br>related_to:/contracts/config-deployment-contract.md |
| [domains/semantic-analysis.md](domains/semantic-analysis.md) | `paradigma-domain` | Semantic Analysis Domain | 语义分析<br>字幕<br>创作方向 ... | SemanticAnalysis<br>TranscriptService<br>LlmAdapter ... | depends_on:/architecture.md<br>depends_on:/domains/trend-engine.md<br>related_to:/contracts/scheduler-jobs-contract.md |
| [domains/tiktok-experiment.md](domains/tiktok-experiment.md) | `paradigma-domain` | TikTok Experiment Domain | TikTok<br>实验适配器<br>故障隔离 ... | TikTokAdapter<br>TIKTOK_ENABLED<br>source_confidence | depends_on:/architecture.md<br>related_to:/contracts/scheduler-jobs-contract.md<br>related_to:/decisions/adr-003-tiktok-isolated-experiment.md |
| [domains/trend-engine.md](domains/trend-engine.md) | `paradigma-domain` | Trend Engine Domain | 趋势评分<br>频道基准<br>聚类 ... | BreakoutRatio<br>trend_metrics<br>TrendDiscovery ... | depends_on:/architecture.md<br>related_to:/contracts/data-model-contract.md<br>related_to:/contracts/scheduler-jobs-contract.md<br>related_to:/known-issues/cold-start-baseline-confidence.md |
| [domains/watchlist-ingestion.md](domains/watchlist-ingestion.md) | `paradigma-domain` | Watchlist and YouTube Ingestion Domain | 监控列表<br>YouTube 采集<br>CSV 导入 ... | WatchlistService<br>YouTubeAdapter<br>IngestionService ... | depends_on:/architecture.md<br>related_to:/contracts/scheduler-jobs-contract.md<br>related_to:/contracts/data-model-contract.md |
| [glossary.md](glossary.md) | `paradigma-glossary` | Project Glossary | 术语<br>缩写<br>业务概念 ... | - | related_to:/project-brief.md |
| [known-issues/api-key-leak-in-shadow-cache.md](known-issues/api-key-leak-in-shadow-cache.md) | `paradigma-known-issue` | API Keys Leaked into Shadow Data Cache | 密钥泄漏<br>事故记录<br>影子缓存 ... | - | related_to:/domains/watchlist-ingestion.md |
| [known-issues/cold-start-baseline-confidence.md](known-issues/cold-start-baseline-confidence.md) | `paradigma-known-issue` | Cold-start Channel Baselines Have Low Confidence | 冷启动<br>基准置信度<br>快照积累 ... | - | related_to:/domains/trend-engine.md |
| [known-issues/shadow-validation-false-positives.md](known-issues/shadow-validation-false-positives.md) | `paradigma-known-issue` | Hindi and Manhwa High-resonance False Positives in Trend Ranking | 误报<br>语言过滤<br>影子验证 ... | - | related_to:/domains/trend-engine.md |
| [manuals/desiderium-ops.md](manuals/desiderium-ops.md) | `paradigma-manual` | Desiderium Operations Manual | 运维手册<br>部署<br>监控 ... | - | related_to:/domains/operations.md<br>related_to:/contracts/config-deployment-contract.md |
| [manuals/desiderium-recovery.md](manuals/desiderium-recovery.md) | `paradigma-manual` | Desiderium Failure Recovery Guide | 故障恢复<br>数据库恢复<br>事故处理 ... | - | related_to:/manuals/desiderium-ops.md<br>related_to:/domains/operations.md |
| [plans/mvp-plan.md](plans/mvp-plan.md) | `paradigma-plan` | Desiderium MVP Plan | MVP 计划<br>产品规格<br>分阶段开发 ... | TrendScore<br>BreakoutRatio<br>watch_items | related_to:/project-brief.md<br>related_to:/architecture.md |
| [project-brief.md](project-brief.md) | `paradigma-project-brief` | Project Brief | 项目愿景<br>番剧解说<br>选题辅助 ... | WatchItem<br>TrendTheme<br>CreativeAngle ... | informs:/architecture.md<br>informs:/contracts/repository-contract.md<br>related_to:/plans/mvp-plan.md |

<!-- END PARADIGMA AUTO-INDEX -->
