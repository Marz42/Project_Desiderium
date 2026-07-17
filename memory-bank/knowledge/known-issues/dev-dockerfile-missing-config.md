---
type: paradigma-known-issue
title: Development Dockerfile Omits Runtime Config Directory
description: Root Dockerfile used by docker compose does not COPY config/, so scoring/LLM/prompt YAML are absent from the development image.
tags: [known-issue, docker, config, deployment]
timestamp: 2026-07-17T11:16:00+08:00
paradigma:
  schema_version: "0.1"
  temperature: cold
  lifecycle: evolving
  update_policy: agent-editable
  epistemic_status: confirmed
  retrieval_hints:
    zh:
      - 开发镜像
      - config 缺失
      - Dockerfile
    en:
      - development image
      - missing config
      - dockerfile
  relations:
    related_to:
      - /contracts/config-deployment-contract.md
      - /domains/operations.md
---

# Symptom

根目录 `Dockerfile`（`docker compose up` 使用）只复制 `app/` 与 `migrations/`，不复制 `config/`。`Dockerfile.prod` 正确包含 `COPY config ./config`。

# Impact

- README Quick Start 的 `docker compose up --build` 启动的 web/worker 缺少 `scoring.yaml`、`llm.yaml`、prompts 与实体词典。
- 趋势评分、语义分析等依赖 YAML 的路径在开发 Compose 环境下会失败或回退异常。

# Root Cause

开发 Dockerfile 与生产 Dockerfile 不同步；生产镜像补齐了 `config/` 与 `scripts/`，开发镜像未跟进。

# Workaround

- 本地开发优先用宿主机 venv（`uvicorn` / `python -m app.worker`），此时仓库内 `config/` 可用。
- 或临时挂载：`-v ./config:/app/config:ro`。
- 需要容器化验证时改用 `Dockerfile.prod`。

# Permanent Fix

- 根 `Dockerfile` 已复制 `config/`，并新增 `.dockerignore` 排除 secret/cache/测试资料。
- 开发与生产镜像已改为复制真实 `/opt/venv`，修复容器入口脚本存在但依赖不可导入的问题。
- Compose 已增加单独 `migrate` 服务，消除 Web/Worker 并发 Alembic 竞态。
- 启动执行配置 fail-fast；CI 验证 assets、`pip check`、镜像构建与 `/health/ready`。

# Related Documents

- `Dockerfile`
- `Dockerfile.prod`
- `README.md`
- `memory-bank/knowledge/contracts/config-deployment-contract.md`

# Status

**Resolved — 0.8.0**（2026-07-17 11:16，开发/生产镜像及 Compose 冒烟通过）。
