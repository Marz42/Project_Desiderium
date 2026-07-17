---
type: paradigma-contract
title: Repository Contract
description: Repository-level boundaries for the Desiderium application and its embedded Paradigma memory-bank harness.
tags: [contract, repository, layout, tooling]
timestamp: 2026-07-17T09:09:00+08:00
paradigma:
  schema_version: "0.1"
  temperature: hot
  lifecycle: evolving
  update_policy: requires-human-confirmation
  epistemic_status: confirmed
  contract_kind: repository
  retrieval_hints:
    zh:
      - 仓库契约
      - 目录布局
      - 工具命令
      - 版本策略
    en:
      - repository contract
      - directory layout
      - tool commands
      - versioning policy
  symbols:
    - VERSION
    - pd-check-all.py
    - docker-compose.prod.yml
  relations:
    depends_on:
      - /architecture.md
    related_to:
      - /contracts/web-api-contract.md
      - /contracts/data-model-contract.md
      - /contracts/scheduler-jobs-contract.md
      - /contracts/config-deployment-contract.md
---

# Scope

本契约定义 Desiderium 仓库的外部有意义边界。仓库包含两个子系统：

1. **应用运行时**：FastAPI Web + APScheduler Worker + PostgreSQL 的番剧趋势情报系统。
2. **Memory-Bank harness**：Paradigma 派生的 Agent 记忆结构与确定性校验工具，仅服务于开发过程，不参与应用运行。

应用层细分契约见 web-api / data-model / scheduler-jobs / config-deployment 四个文档。

# Contract

## Repository Layout

| Area | Contract |
|------|----------|
| `app/` | 应用源码；依赖方向 web/jobs → services → domain，services → repositories/adapters |
| `migrations/` | Alembic 版本链；容器启动时自动 `upgrade head` |
| `tests/` | pytest 单测；不调用真实外部 API |
| `config/` | 运行时 YAML 配置（scoring / llm / tiktok / prompts / 实体词典） |
| `scripts/` | 运维与影子验证脚本；`data/shadow/` 为 golden dataset |
| `deploy/` | Caddy 与 systemd 部署配置 |
| `OPS.md` / `RECOVERY.md` | 运维与故障恢复手册的 canonical 版本 |
| `memory-bank/runtime/` | Agent 短期状态；不导出为 OKF knowledge |
| `memory-bank/logs/` | 会话日志与 changelog；append-first |
| `memory-bank/knowledge/` | OKF-compatible 长期知识库 |
| `docs/rfc/` | 本项目自身的 RFC / 提案区（OKF-compatible） |
| `memory-bank-template/` | harness 空白模板源，勿写入项目内容 |
| `.paradigma/` | harness 配置、schema 与工具 |

## Tool Commands（Memory-Bank harness）

| Command | Status | Contract |
|---------|--------|----------|
| `python .paradigma/tools/pd-check-all.py` | Stable | 聚合 strict lint、link check（`--allow-warnings`）、index `--check`、hot-size、DESIGN.md 校验；支持 `--keep-going` |
| `python .paradigma/tools/pd-lint-okf.py --strict` | Stable | 校验 concept 文档 schema、sections、timestamp、policy、generated block |
| `python .paradigma/tools/pd-check-links.py` | Stable | 校验 Markdown 链接、frontmatter relations、index 条目 |
| `python .paradigma/tools/pd-sync-index.py --write` | Stable | 重新生成根与子目录 index generated block；`--check` 验证 checksum |
| `python .paradigma/tools/pd-check-hot-size.py` | Stable | 报告 active-task、HOT 文档、progress index 体积 |
| `python .paradigma/tools/pd-archive-task.py --write` | Stable | 归档已完成 active task 并从模板重置；支持 `--force` |
| `python .paradigma/tools/pd-compact-progress.py --write` | Stable | 生成 progress 摘要，不删除原始日志 |
| `python .paradigma/tools/pd-diagnose.py --upstream <path>` | Experimental | 对比上游 harness 差距；支持 `--check-version` / `--json` |

# Request Schema

应用 HTTP 接口的请求约定见 [Web API Contract](web-api-contract.md)。harness 工具的命令行参数以各脚本 `--help` 为准，上表列出契约化参数。

# Response Schema

harness 工具退出码：

| Exit code | Meaning |
|-----------|---------|
| `0` | 成功 |
| `1` | 校验失败 |
| `2` | `pd-diagnose.py` 专用：upstream 无效或 harness 未检出 |

应用 HTTP 状态码约定见 Web API Contract。

# State Transitions

```text
应用: Watchlist -> crawl -> snapshots -> baselines/scoring -> semantic -> candidates -> review -> brief export
harness: User request -> runtime active task -> knowledge routing -> edits -> pd-check-all -> logs/knowledge update
```

# Compatibility Notes

- 新增可选 frontmatter 字段、新增 concept 类型向后兼容。
- 移动核心路径（`app/`、`memory-bank/knowledge/`）或更改必需工具命令属于兼容性影响变更，需版本评估。
- 双轨版本：根 `VERSION` 追踪应用 SemVer；`.paradigma/config.yaml` 的 `paradigma_harness_version` 追踪 harness，两者独立演进。
- harness 从上游 Paradigma 同步时用 `pd-diagnose.py --upstream` 评估差距，不得覆盖本项目 knowledge。

# Breaking Change Policy

破坏性变更（API / DB schema / 核心路径 / 工具命令）需显式用户确认，并按 `conventions.md` 的 SemVer 规则评估版本号。

# Citations

- [System Architecture](../architecture.md)
- [Coding Conventions](../conventions.md)
