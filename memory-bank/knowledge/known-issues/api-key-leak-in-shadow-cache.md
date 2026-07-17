---
type: paradigma-known-issue
title: API Keys Leaked into Shadow Data Cache
description: Stage 1 shadow validation cached raw API responses containing request URLs with API keys; keys were scrubbed from the repo and revoked in Google Cloud Console.
tags: [known-issue, security, secrets, incident]
timestamp: 2026-07-17T09:30:00+08:00
paradigma:
  schema_version: "0.1"
  temperature: cold
  lifecycle: evolving
  update_policy: agent-editable
  epistemic_status: confirmed
  retrieval_hints:
    zh:
      - 密钥泄漏
      - 事故记录
      - 影子缓存
      - 吊销
    en:
      - api key leak
      - incident
      - shadow cache
      - revoked
  relations:
    related_to:
      - /domains/watchlist-ingestion.md
---

# Symptom

Stage 1 影子验证脚本的 API 响应缓存（`data/shadow/` 下的原始数据文件）中包含带 API key 的请求 URL，随提交进入 git 历史。事后由提交 `addec5b`（"Remove leaked API keys from shadow data cache"）清除仓库内容。

# Impact

- API key 在仓库历史中短暂暴露；曾共享过仓库的场景下，该 key 必须视为已泄漏。
- 影子缓存目录已 gitignore（`data/shadow/`、`data/shadow/cache/`）。

# Root Cause

缓存层保存了完整原始响应与请求元数据，未对 URL 查询参数中的 `key=` 做脱敏；`.gitignore` 覆盖不完整。

# Workaround

- 提交数据文件前人工 grep `key=` / `api_key`。
- 泄漏 key 已在 Google Cloud Console **吊销**（2026-07-17 确认）；新密钥只放在 `.env`，不进 git。

# Permanent Fix

- 缓存写入层统一脱敏请求 URL 中的凭证参数（fetch 元数据只保留 endpoint 与参数名）。
- 为 `data/` 提交路径增加 pre-commit 秘密扫描（如 gitleaks），或在 CI 中扫描。
- 两项均未实施，列为防复发待办。

# Related Documents

- `memory-bank/knowledge/contracts/config-deployment-contract.md`
- `memory-bank/logs/progress/2026-07-17-stage-1-shadow-validation.md`

# Status

**Resolved (incident)** — 仓库内容已清除（`addec5b`）；泄漏的 YouTube Data API key 已于 2026-07-17 在 Google Cloud Console 吊销。防复发的自动脱敏与秘密扫描仍未实施。
