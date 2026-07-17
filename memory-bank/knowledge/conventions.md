---
type: paradigma-convention
title: Coding and Collaboration Conventions
description: Coding, naming, testing, documentation, and versioning conventions for the Desiderium application and its memory-bank.
tags: [conventions, python, testing, versioning, memory-bank]
timestamp: 2026-07-17T09:09:00+08:00
paradigma:
  schema_version: "0.1"
  temperature: hot
  lifecycle: evolving
  update_policy: requires-human-confirmation
  epistemic_status: confirmed
  retrieval_hints:
    zh:
      - 代码规范
      - 测试规范
      - 版本规则
      - 文档约定
    en:
      - coding conventions
      - testing
      - versioning
      - documentation
  symbols:
    - SemVer
    - VERSION
    - pytest
    - config/scoring.yaml
  relations:
    constrains:
      - /contracts/repository-contract.md
---

# Naming

| Target | Rule | Example |
|--------|------|---------|
| Python modules / packages | snake_case | `trend_discovery.py`, `app/repositories/` |
| Python functions / variables | snake_case | `refresh_channel_baselines` |
| Python classes | PascalCase | `WatchlistService`, `TrendTheme` |
| Constants | UPPER_SNAKE_CASE | `EXEMPT_PREFIXES` |
| DB tables / columns | snake_case（复数表名） | `metric_snapshots`, `captured_at_bucket` |
| Enums | PascalCase 类 + 小写值 | `WatchTier.PRIORITY = "priority"` |
| Config / docs files | kebab-case 或既有约定 | `anime_entities.yaml`, `web-api-contract.md` |
| Env vars | UPPER_SNAKE_CASE | `YOUTUBE_DAILY_QUOTA_LIMIT` |

避免拼音、模糊缩写和 `data` / `info` / `temp` 之类的泛型名。

# Code Style

- Python ≥ 3.12，全面使用 `from __future__ import annotations` 与内建泛型标注。
- 数据访问统一走 `app/repositories/`（async `AsyncSession`）；业务逻辑在 `app/services/`；纯算法在 `app/domain/`（无 I/O、可单测）。
- 平台细节只允许出现在 `app/adapters/<platform>/`；领域与服务层不得 import 平台 SDK 或页面选择器。
- 算法阈值、权重、调度间隔一律来自 `config/*.yaml` 或 `Settings`，禁止在服务 / SQL / 模板中硬编码。
- 结构化 JSON 日志（`app/logging_config.py`），`extra` 中带 `service` / `component`；密钥与 cookie 不得进入日志。
- 注释只解释"为什么"（规则来源、解析器的刻意限制），不复述代码行为。

# Error Handling

- 外部 API 调用（YouTube / TikTok / LLM）必须有超时、指数退避与错误分类；配额耗尽时跳过低优先级任务而不是抛出。
- 采集任务失败记录到 `crawl_jobs`（error_code / error_message / retry_count），由重试任务收敛，单项失败不得中断批次。
- LLM / TikTok 失败必须被隔离：趋势评分与 YouTube 简报不受影响。
- Web 层：`/health/ready` 与 `/health` 在依赖不可用时返回 503；业务路由的表单错误渲染回页面而不是 500。
- 运维脚本（backup / restore / disk monitor）用非零退出码表达失败，供 cron 或告警钩子消费。

# Testing Conventions

- `python -m pytest -q` 必须全绿后才能结束会话；新服务 / 纯算法必须带 `tests/unit/` 测试。
- 单测不调用真实外部 API：适配器测试使用保存的响应样本或 fake client。
- 评分权重、趋势门槛、聚类规则、prompt、去重阈值变更时，应在 golden dataset（`data/shadow/golden_dataset.csv`）上回放对比。
- Memory-bank / RFC 文档编辑后运行 `python .paradigma/tools/pd-check-all.py`；新增或删除 concept 文档后运行 `python .paradigma/tools/pd-sync-index.py --write`。

# Documentation Conventions

- 长期知识在 `memory-bank/knowledge/`（OKF frontmatter + strict lint）；运行状态在 `memory-bank/runtime/`；会话日志在 `memory-bank/logs/`。
- 运维操作手册的 canonical 版本是仓库根目录 `OPS.md` / `RECOVERY.md`；`knowledge/manuals/` 中的对应文档是 OKF 包装层，链接而非复制。
- `AGENT_RULES.md` 是 Agent 协议源头，`.cursor/rules/memory-bank-protocol.mdc` 是同步的 Cursor 适配器。
- 写入日志、ADR、active-task 前先用 Shell 获取时间戳（PowerShell: `Get-Date -Format "yyyy-MM-dd HH:mm"`）。

## Versioning

应用与 harness 双轨版本：

- **应用版本**：根 `VERSION` 文件为唯一真源，SemVer；`pyproject.toml` 与 changelog 保持一致。
- **Paradigma harness 版本**：`.paradigma/config.yaml` 的 `paradigma_harness_version`，仅在从上游同步 harness 时更新。

| Change type | Version action |
|-------------|----------------|
| Typo / 文案 | 可跳过 bump |
| Bug 修复、文档体系重构 | PATCH |
| 新功能域 / 新任务 / 新契约能力 | MINOR |
| API / DB schema 破坏性变更 | MAJOR 提案，需用户确认 |

Bump 时同步更新：`VERSION`、`pyproject.toml`、`memory-bank/logs/changelog.md`、一条 progress session log。

## Document Size Limits

HOT 文档每次会话都会被完整读入 Agent 上下文：

| 文档类型 | WARN | ERROR | 超出后操作 |
|----------|------|-------|-----------|
| HOT knowledge 文档 | 260 行 | 420 行 | 拆分（细节移入 domains/ 或 contracts/ 子文件） |
| `active-task.md` | 160 行 | 260 行 | 归档 |
| Progress index | 160 行 | 260 行 | 压缩 |

单个 contract 超过 200 行时按 `contract_kind` 拆分为独立文件，每个文件保留完整 frontmatter 与独立可读的上下文。

# Prohibited Patterns

- 不在 `memory-bank/runtime/active-task.md` 写长期事实。
- 不手工编辑 generated index block（由 `pd-sync-index.py --write` 维护）。
- 不新增缺少 OKF frontmatter 的 concept 文档。
- 不在未检查 update policy 的情况下修改 contracts、architecture 或已接受的 ADR。
- 不在服务层硬编码评分常量或调度间隔。
- 不让 LLM 计算指标、生成无证据结论或修改原始数据。
- 不把密钥、cookie 写入代码、日志或 git（`.env` only）。
- 不在领域层（`app/domain/`）引入 I/O 或平台依赖。
