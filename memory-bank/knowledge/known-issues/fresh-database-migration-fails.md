---
type: paradigma-known-issue
title: Fresh Database Migration Fails After Initial Revision
description: Alembic cannot upgrade a fresh PostgreSQL database to head because the initial revision creates the current full metadata and later revisions recreate existing objects.
tags: [known-issue, database, alembic, deployment, blocker]
timestamp: 2026-07-17T09:54:00+08:00
paradigma:
  schema_version: "0.1"
  temperature: cold
  lifecycle: evolving
  update_policy: agent-editable
  epistemic_status: confirmed
  retrieval_hints:
    zh:
      - 全新数据库迁移失败
      - Alembic
      - 部署阻断
    en:
      - fresh database migration failure
      - alembic
      - deployment blocker
  relations:
    related_to:
      - /contracts/data-model-contract.md
      - /contracts/config-deployment-contract.md
---

# Symptom

在全新的 PostgreSQL 16 数据库上运行 `alembic upgrade head`：

1. `83f6909e9adb` 成功执行；
2. `a1b2c3d4e5f6` 创建 `trend_score_snapshots` 时失败；
3. PostgreSQL 报错 `DuplicateObjectError: type "lifecycle_status" already exists`。

# Impact

- `docker-compose.yml` 与 `docker-compose.prod.yml` 的 web / worker 启动命令都会先运行 `alembic upgrade head`，因此全新部署无法启动。
- 现有 75 个 pytest 测试未覆盖真实 PostgreSQL 的完整迁移链，常规单测全部通过时仍无法发现该问题。

# Root Cause

初始迁移 `83f6909e9adb` 调用 `Base.metadata.create_all(bind)`，执行时读取的是**当前** ORM metadata，因此会提前创建后续迁移应负责的表、枚举与索引。下一条迁移再次创建这些对象时发生重复。

此外，`sa.Enum(..., create_type=False)` 没有阻止表创建事件再次发出 `CREATE TYPE`，但即使单独修复枚举，`trend_score_snapshots` 表本身也已由初始迁移提前创建。

# Workaround

- 对已由当前 metadata 完整建表的空数据库，可在人工核对 schema 后使用 `alembic stamp head`；该操作绕过迁移，不应自动用于已有业务数据。
- 在修复迁移链前，不得把全新 Compose 部署标记为可用。

# Permanent Fix

已于 2026-07-17（v0.7.2）修复，方案：

- `83f6909e9adb` 的 `create_all` / `drop_all` 通过 `LATER_REVISION_TABLES` 排除后续迁移拥有的 5 张表（`trend_score_snapshots`、`angle_status_audits`、`worker_heartbeats`、`api_quota_daily`、`llm_usage_logs`），只创建初始 schema。
- `a1b2c3d4e5f6` / `b2c3d4e5f6a7` 中复用已有枚举的列改用 `postgresql.ENUM(..., create_type=False)`——普通 `sa.Enum` 会忽略 `create_type=False` 并重复发出 `CREATE TYPE`。
- `c8d9e0f1a2b3` 的 `ix_metric_snapshots_content_captured` 改为 `if_not_exists=True`：该索引在当前 model metadata 中，全新库会由初始迁移创建，旧库走本迁移创建。

验证：临时 PostgreSQL 16 上 `alembic upgrade head` 成功（19 张表含 `alembic_version`），`downgrade base` → 再次 `upgrade head` 往返正常，75 个单测全部通过。

遗留 follow-up：CI 尚未加入 fresh migration 集成测试（见 architecture Open Questions 的 CI 覆盖缺口）。

# Related Documents

- `memory-bank/knowledge/contracts/data-model-contract.md`
- `memory-bank/knowledge/contracts/config-deployment-contract.md`
- `migrations/versions/83f6909e9adb_initial_schema.py`

# Status

**Resolved**（2026-07-17，v0.7.2）。初始迁移限定表集合 + 枚举 `create_type=False` 修正 + 索引 `if_not_exists`；fresh migration 与 downgrade/upgrade 往返实测通过。
