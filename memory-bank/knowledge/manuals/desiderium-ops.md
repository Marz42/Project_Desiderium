---
type: paradigma-manual
title: Desiderium Operations Manual
description: Production deployment and day-to-day operations entry point; canonical detail lives in root OPS.md.
tags: [manual, ops, deployment, monitoring]
timestamp: 2026-07-17T11:16:00+08:00
paradigma:
  schema_version: "0.1"
  temperature: cold
  lifecycle: evolving
  update_policy: agent-editable
  epistemic_status: confirmed
  retrieval_hints:
    zh:
      - 运维手册
      - 部署
      - 监控
      - 备份
    en:
      - operations manual
      - deploy
      - monitoring
      - backup
  relations:
    related_to:
      - /domains/operations.md
      - /contracts/config-deployment-contract.md
---

# Purpose

生产部署与日常运维的入口文档。完整操作细节的 canonical 版本是仓库根目录的 [OPS.md](../../../OPS.md)，本文档提供 OKF 路由与关键步骤摘要，修改操作流程时应先改 `OPS.md` 再同步此处摘要。

# Preconditions

- Docker + Docker Compose 可用（或按 systemd 路线准备主机与 venv）。
- `.env` 已从 `.env.example` 复制并填好密钥：`POSTGRES_PASSWORD`、`SECRET_KEY`、`MANAGER_PASSWORD`、`YOUTUBE_DATA_API_KEY`，HTTPS 需 `DOMAIN` / `ACME_EMAIL`。
- `.env` 不进 git；备份目录 `backups/` 已创建。

# Steps

1. 首次部署：`docker compose -f docker-compose.prod.yml up -d --build`（一次性 `migrate` 服务先执行 `alembic upgrade head`，成功后再启动 web/worker）。
2. 可选每日备份 sidecar：`docker compose -f docker-compose.prod.yml --profile backup up -d backup`。
3. 升级：`git pull` → `build` → `up -d`。
4. 手动备份：`./scripts/backup.sh`；索引维护：`python scripts/optimize_db_indexes.py`。
5. 主机部署（备选）：安装 `deploy/systemd/*.service`，前置自备反向代理。

# Verification

- `GET /health` 返回 200 且 `database` / `disk` / `worker` 全部正常。
- 登录后 `GET /admin/status`：24h 无异常任务失败、配额未耗尽、worker 心跳在 5 分钟内。
- `docker compose -f docker-compose.prod.yml ps` 所有服务 running。

# Rollback

- 应用回滚：checkout 上一 tag / commit 后重新 build + up。
- 数据回滚：按 [Recovery Guide](desiderium-recovery.md) 从备份恢复（破坏性操作）。

# Troubleshooting

按症状路由到 [RECOVERY.md](../../../RECOVERY.md)：数据库不可用、worker stale、配额耗尽、LLM 失败、磁盘满、HTTPS 证书问题。

# Citations

- [OPS.md](../../../OPS.md)（canonical）
- [Config and Deployment Contract](../contracts/config-deployment-contract.md)
