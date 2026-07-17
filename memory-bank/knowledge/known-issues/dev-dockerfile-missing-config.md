---
type: paradigma-known-issue
title: Development Dockerfile Omits Runtime Config Directory
description: Root Dockerfile used by docker compose does not COPY config/, so scoring/LLM/prompt YAML are absent from the development image.
tags: [known-issue, docker, config, deployment]
timestamp: 2026-07-17T09:43:00+08:00
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

- 根 `Dockerfile` 增加 `COPY config ./config`（必要时同步 `scripts/`）。
- 在 Compose 构建后冒烟检查容器内存在 `/app/config/scoring.yaml`。

# Related Documents

- `Dockerfile`
- `Dockerfile.prod`
- `README.md`
- `memory-bank/knowledge/contracts/config-deployment-contract.md`

# Status

**Open — P1**（2026-07-17 代码审计确认）。
