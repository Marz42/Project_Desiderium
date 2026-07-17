# Domains Index

Desiderium application domain documents: ingestion, trend engine, semantics, admin web, TikTok experiment, and operations.

<!-- BEGIN PARADIGMA AUTO-INDEX -->
<!-- checksum: 58e41df72d1be66e -->
<!-- generated_by: pd-sync-index.py -->

| Path | Type | Title | Hints | Symbols | Relations |
|------|------|-------|-------|---------|-----------|
| [admin-web.md](admin-web.md) | `paradigma-domain` | Admin Web Domain | 管理后台<br>每日审核<br>简报导出 ... | AuthMiddleware<br>brief_export<br>angle_status ... | depends_on:/architecture.md<br>related_to:/contracts/web-api-contract.md<br>related_to:/contracts/data-model-contract.md |
| [operations.md](operations.md) | `paradigma-domain` | Operations Domain | 运维<br>监控<br>备份 ... | /admin/status<br>worker_heartbeats<br>scripts/backup.sh | depends_on:/architecture.md<br>related_to:/manuals/desiderium-ops.md<br>related_to:/manuals/desiderium-recovery.md<br>related_to:/contracts/config-deployment-contract.md |
| [semantic-analysis.md](semantic-analysis.md) | `paradigma-domain` | Semantic Analysis Domain | 语义分析<br>字幕<br>创作方向 ... | SemanticAnalysis<br>TranscriptService<br>LlmAdapter ... | depends_on:/architecture.md<br>depends_on:/domains/trend-engine.md<br>related_to:/contracts/scheduler-jobs-contract.md |
| [tiktok-experiment.md](tiktok-experiment.md) | `paradigma-domain` | TikTok Experiment Domain | TikTok<br>实验适配器<br>故障隔离 ... | TikTokAdapter<br>TIKTOK_ENABLED<br>source_confidence | depends_on:/architecture.md<br>related_to:/contracts/scheduler-jobs-contract.md<br>related_to:/decisions/adr-003-tiktok-isolated-experiment.md |
| [trend-engine.md](trend-engine.md) | `paradigma-domain` | Trend Engine Domain | 趋势评分<br>频道基准<br>聚类 ... | BreakoutRatio<br>trend_metrics<br>TrendDiscovery ... | depends_on:/architecture.md<br>related_to:/contracts/data-model-contract.md<br>related_to:/contracts/scheduler-jobs-contract.md<br>related_to:/known-issues/cold-start-baseline-confidence.md |
| [watchlist-ingestion.md](watchlist-ingestion.md) | `paradigma-domain` | Watchlist and YouTube Ingestion Domain | 监控列表<br>YouTube 采集<br>CSV 导入 ... | WatchlistService<br>YouTubeAdapter<br>IngestionService ... | depends_on:/architecture.md<br>related_to:/contracts/scheduler-jobs-contract.md<br>related_to:/contracts/data-model-contract.md |

<!-- END PARADIGMA AUTO-INDEX -->
