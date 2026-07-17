---
type: paradigma-contract
title: Config and Deployment Contract
description: Environment variables, runtime YAML configuration, and production deployment topology for Desiderium.
tags: [contract, config, deployment, docker, secrets]
timestamp: 2026-07-17T11:16:00+08:00
paradigma:
  schema_version: "0.1"
  temperature: warm
  lifecycle: evolving
  update_policy: requires-human-confirmation
  epistemic_status: confirmed
  contract_kind: deployment
  retrieval_hints:
    zh:
      - 环境变量
      - 配置
      - 部署
      - 密钥管理
    en:
      - environment variables
      - configuration
      - deployment
      - secret management
  symbols:
    - .env.example
    - config/scoring.yaml
    - docker-compose.prod.yml
  relations:
    depends_on:
      - /architecture.md
    related_to:
      - /manuals/desiderium-ops.md
      - /domains/operations.md
---

# Scope

应用配置的两个来源（`.env` 环境变量与 `config/` YAML）以及生产部署拓扑。`.env.example` 是环境变量的 canonical 清单。

# Contract

## Environment variables（`app/config.py` Settings）

| Group | Variables | Notes |
|-------|-----------|-------|
| Core | `DATABASE_URL`, `ENVIRONMENT`, `LOG_LEVEL` | asyncpg URL |
| YouTube | `YOUTUBE_DATA_API_KEY`（别名 `YOUTUBE_API_KEY`）, `YOUTUBE_DAILY_QUOTA_LIMIT`(10000), `YOUTUBE_MAX_SEARCH_CALLS`(100) | |
| Crawl | `CRAWL_PRIORITY_HOURS`(5), `CRAWL_GENERAL_HOURS`(18), `CRAWL_KEYWORD_HOUR`(6) | |
| TikTok | `TIKTOK_ENABLED`(false), `TIKTOK_COOKIE`, `TIKTOK_PAGE_VERSION`(v1), `TIKTOK_CRAWL_HOURS`(12), `TIKTOK_RETRY_HOURS`(2) | cookie 不进 git / 日志 |
| LLM | `LLM_API_KEY`, `LLM_BASE_URL`, `LLM_MODEL`, `LLM_COST_PER_MILLION_INPUT_USD`(0.15), `LLM_COST_PER_MILLION_OUTPUT_USD`(0.60) | OpenAI-compatible |
| Auth | `SECRET_KEY`, `MANAGER_PASSWORD` | 密码为空 = 开发模式跳过认证；两者需同时轮换 |
| Ops | `SNAPSHOT_RETENTION_DAYS`(90), `DISK_WARN_PERCENT`(85), `BACKUP_RETENTION_DAYS`(14), `WORKER_STALE_MINUTES`(15) | |
| Prod | `DOMAIN`, `ACME_EMAIL`, `POSTGRES_USER/PASSWORD/DB` | Caddy TLS 必需 `DOMAIN` |

## Runtime YAML（`config/`）

| File | Content |
|------|---------|
| `scoring.yaml` | 评分权重/阈值、生命周期、候选数量/多样性、目标语言与题材相关性规则；`publication:` 段（G4）配置 `team_channel_ids`（团队基准频道 external_id 列表，默认空）、`windows_hours`（发布后指标回收窗口，默认 `[0, 24, 72, 168]`，首项必须为 0 且严格递增）、`late_backfill_grace_hours`（延迟补采宽限期，默认 6） |
| `anime_entities.yaml` | 规则聚类的动漫实体词典（作品 / 别名 / 角色 / 篇章） |
| `llm.yaml` | LLM 调用参数（重试 / 超时 / schema） |
| `tiktok.yaml` | 页面选择器版本隔离配置 |
| `prompts/*.yaml` | 版本化 prompt 模板（5 个语义任务） |

# Request Schema

配置由 pydantic-settings 从 `.env` 读取（`extra="ignore"`），YAML 由 `scoring_config` / `llm_config` 带 `@lru_cache` 加载。

# Response Schema

Web 与 worker 启动时统一执行 `validate_runtime_config()`；缺文件、YAML/schema 错误、权重和阈值关系错误、prompt 缺失、候选参数越界会 fail-fast。生产环境拒绝默认/过短 `SECRET_KEY`、空 `MANAGER_PASSWORD` 及启用 TikTok 时缺失 cookie。

# State Transitions

生产部署（`docker-compose.prod.yml`）：

```text
Internet -> caddy (80/443, ACME TLS) -> web (uvicorn x2 workers, expose 8000)
postgres (16-alpine, healthcheck, postgres_data volume)
migrate (一次性 alembic upgrade head，成功后解锁 web/worker)
worker (python -m app.worker)
backup (optional profile: daily scripts/backup.sh, ./backups volume)
web/worker 不并发执行迁移
```

主机部署备选：`deploy/systemd/desiderium-{web,worker}.service` + 自备反向代理。

# Compatibility Notes

- 新增带默认值的环境变量与 YAML 键向后兼容；重命名或删除属破坏性变更。
- 修改 `scoring.yaml` 权重 / 阈值不是代码变更，但必须在 golden dataset 上回归并记录修改原因（见 conventions）。
- 密钥只存在于 `.env`（gitignored）；镜像与仓库中不得出现密钥。
- `config/` 中只允许非敏感、版本化运行配置并同时打入开发/生产镜像；`.dockerignore` 必须排除 `.env`、cache、测试与 memory-bank。
- 备份产物 `backups/desiderium-<UTC>.sql.gz`，恢复流程见 `RECOVERY.md`。

# Breaking Change Policy

环境变量重命名、compose 服务拓扑变更、备份格式变更需用户确认与 SemVer 评估，并同步 `OPS.md` 与本契约。

# Citations

- [Operations Manual](../../../OPS.md)
- [Recovery Guide](../../../RECOVERY.md)
