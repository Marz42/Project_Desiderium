---
type: paradigma-manual
title: Desiderium Failure Recovery Guide
description: Failure recovery entry point; canonical runbook lives in root RECOVERY.md.
tags: [manual, recovery, backup, incident]
timestamp: 2026-07-17T09:09:00+08:00
paradigma:
  schema_version: "0.1"
  temperature: cold
  lifecycle: evolving
  update_policy: agent-editable
  epistemic_status: confirmed
  retrieval_hints:
    zh:
      - 故障恢复
      - 数据库恢复
      - 事故处理
    en:
      - failure recovery
      - database restore
      - incident response
  relations:
    related_to:
      - /manuals/desiderium-ops.md
      - /domains/operations.md
---

# Purpose

常见生产故障的恢复入口。完整分症状 runbook 的 canonical 版本是仓库根目录的 [RECOVERY.md](../../../RECOVERY.md)；本文档提供 OKF 路由与最关键流程（数据库恢复）摘要。

# Preconditions

- 有可用备份：`backups/desiderium-<UTC>.sql.gz`（完整性检查 `gunzip -t`）。
- 破坏性操作前先快照当前状态（`docker compose ps` / 日志 / 现有数据）。

# Steps

数据库从备份恢复（覆盖现有数据）：

1. 停止写入方：`docker compose -f docker-compose.prod.yml stop web worker`
2. 恢复：`./scripts/restore.sh backups/desiderium-YYYYMMDDTHHMMSSZ.sql.gz --yes`
3. 迁移（幂等）：`docker compose -f docker-compose.prod.yml run --rm web alembic upgrade head`
4. 重启：`docker compose -f docker-compose.prod.yml up -d web worker`

其他症状（worker stale、配额耗尽、磁盘满、Caddy 证书）按 `RECOVERY.md` 对应小节处理。

# Verification

- `/health` 与 `/admin/status` 全绿，worker 心跳 5 分钟内。
- 对任一 watch item 手动触发抓取成功。

# Rollback

恢复操作本身不可逆（覆盖数据库）；唯一回退路径是换用另一份更早 / 更晚的备份重复上述流程。

# Troubleshooting

- 反复恢复失败 → 校验备份完整性（`gunzip -t`）。
- 磁盘恢复后 Postgres 起不来 → 参考 PostgreSQL WAL recovery 文档。
- 无备份的数据丢失 → 重新导入 watchlist，接受指标历史缺口。
- 复发性事故应记录到 `memory-bank/knowledge/known-issues/`。

# Citations

- [RECOVERY.md](../../../RECOVERY.md)（canonical）
- [Desiderium Operations Manual](desiderium-ops.md)
