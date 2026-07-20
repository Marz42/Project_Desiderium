---
date: 2026-07-20 17:18
task: 2026-07-20-issue-hardening
status: completed
---

# 2026-07-20 — Issue Hardening (P0–P2 Error Report Fixes)

## Summary

修复 error-report 中的 P0–P2 问题，共 6 项（P2-1 git history 由用户明确跳过）。

## Changes

### P0-2 — CI migration check
- 移除 `.github/workflows/check.yml` 中的 `alembic check` advisory 步骤（原有 `continue-on-error: true`，但会在 CI 日志中产生误导性失败输出）。

### P2-2 — Production env validation
- 确认 `app/services/config_validation.py` 已于之前迭代实现完整校验（`SECRET_KEY` 非默认且 ≥32 字符、`MANAGER_PASSWORD` 非空、TikTok cookie）；无需新增代码。

### P1-1 — Log redaction
- `app/logging_config.py` 新增 `ApiKeyRedactFilter`，通过正则 `AIzaSy[A-Za-z0-9_-]{33}` 将 Google API key 替换为 `[REDACTED]`，挂载到根 handler，覆盖所有日志路径。

### P1-2 — Integration test setup
- 新增 `docker-compose.test.yml`：独立 `postgres-test` 服务 + `test` 容器，运行 `alembic upgrade head && pytest tests/integration`。
- 新增 `Makefile`：`make test-unit`、`make test-integration`、`make lint`、`make typecheck`。

### P1-3 — Offline migration head check
- 新增 `scripts/check_migration_head.py`：纯文本解析 `migrations/versions/` 中所有迁移文件，确认唯一 head 为 `a7b8c9d0e1f2`；可在 CI 和本地离线运行。

### P0-1 — Test monkeypatch comment
- `tests/unit/test_angle_status.py` `test_publish_with_valid_youtube_url_creates_retryable_publication_record` 添加注释，说明 monkeypatch 为测试隔离需要，非代码缺陷。

### P2-3 — Archive active-task
- `pd-archive-task.py --write` 归档上一 task；写入新 `active-task.md`。

## Test Results

152 passed, 8 skipped (integration tests 因无 DB 环境正常跳过)。

## Paradigma Checks

All 5 checks passed (OKF lint 0 errors, links 0 errors, index stale 0).
