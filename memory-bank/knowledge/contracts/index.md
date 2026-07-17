# Contracts Index

Repository, API, data model, scheduler, and deployment contracts for Desiderium.

<!-- BEGIN PARADIGMA AUTO-INDEX -->
<!-- checksum: 3e29ebc021f3ef0d -->
<!-- generated_by: pd-sync-index.py -->

| Path | Type | Title | Hints | Symbols | Relations |
|------|------|-------|-------|---------|-----------|
| [config-deployment-contract.md](config-deployment-contract.md) | `paradigma-contract` | Config and Deployment Contract | 环境变量<br>配置<br>部署 ... | .env.example<br>config/scoring.yaml<br>docker-compose.prod.yml | depends_on:/architecture.md<br>related_to:/manuals/desiderium-ops.md<br>related_to:/domains/operations.md |
| [data-model-contract.md](data-model-contract.md) | `paradigma-contract` | Data Model Contract | 数据库表<br>唯一约束<br>迁移链 ... | app/models.py<br>metric_snapshots<br>trend_themes ... | depends_on:/architecture.md<br>related_to:/contracts/web-api-contract.md<br>related_to:/domains/trend-engine.md |
| [repository-contract.md](repository-contract.md) | `paradigma-contract` | Repository Contract | 仓库契约<br>目录布局<br>工具命令 ... | VERSION<br>pd-check-all.py<br>docker-compose.prod.yml | depends_on:/architecture.md<br>related_to:/contracts/web-api-contract.md<br>related_to:/contracts/data-model-contract.md<br>related_to:/contracts/scheduler-jobs-contract.md ... |
| [scheduler-jobs-contract.md](scheduler-jobs-contract.md) | `paradigma-contract` | Scheduler Jobs Contract | 定时任务<br>调度<br>任务互斥 ... | app/jobs/scheduler.py<br>app/worker.py<br>crawl_jobs | depends_on:/architecture.md<br>related_to:/contracts/data-model-contract.md<br>related_to:/domains/watchlist-ingestion.md<br>related_to:/domains/trend-engine.md |
| [web-api-contract.md](web-api-contract.md) | `paradigma-contract` | Web API Contract | API 路由<br>认证<br>健康检查 ... | AuthMiddleware<br>/health<br>/admin/status ... | depends_on:/architecture.md<br>related_to:/contracts/data-model-contract.md<br>related_to:/domains/admin-web.md |

<!-- END PARADIGMA AUTO-INDEX -->
