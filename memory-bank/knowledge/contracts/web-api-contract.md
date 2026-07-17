---
type: paradigma-contract
title: Web API Contract
description: HTTP routes, authentication, CSRF, and status code contract for the Desiderium FastAPI web process.
tags: [contract, api, http, auth, csrf]
timestamp: 2026-07-17T09:09:00+08:00
paradigma:
  schema_version: "0.1"
  temperature: warm
  lifecycle: evolving
  update_policy: requires-human-confirmation
  epistemic_status: confirmed
  contract_kind: api
  retrieval_hints:
    zh:
      - API 路由
      - 认证
      - 健康检查
      - 简报导出
    en:
      - API routes
      - authentication
      - health check
      - brief export
  symbols:
    - AuthMiddleware
    - /health
    - /admin/status
    - /candidates
  relations:
    depends_on:
      - /architecture.md
    related_to:
      - /contracts/data-model-contract.md
      - /domains/admin-web.md
---

# Scope

Desiderium Web 进程（`app/main.py`）暴露的全部 HTTP 面：健康检查、运维状态 API、单管理者认证，以及五页 SSR 管理后台。除 JSON 端点外均返回 HTML（Jinja2 + HTMX）。

# Contract

## Public endpoints（免认证）

| Route | Method | Response |
|-------|--------|----------|
| `/health/live` | GET | `{"status": "ok"}`，恒 200 |
| `/health/ready` | GET | DB 可达 200；否则 503 `{"status": "unavailable", "database": "down"}` |
| `/health` | GET | DB + 磁盘 + worker 心跳综合状态；`degraded` 仍 200，`unavailable` 503 |
| `/login` | GET/POST | 登录页 / 提交；成功 303 跳转 `next` |
| `/docs`, `/openapi.json`, `/redoc` | GET | FastAPI 自动文档 |

## Authenticated endpoints

| Route | Method | Purpose |
|-------|--------|---------|
| `/` | GET | 303 → `/candidates` |
| `/admin/status` | GET | 运维 JSON：24h 任务失败、YouTube 配额、当日 LLM 成本、快照统计、磁盘 |
| `/candidates` | GET | 今日候选（约 30 个方向，按趋势分组，支持筛选） |
| `/candidates/{daily_id}/toggle` | POST | 勾选 / 取消入选 |
| `/candidates/angles/{angle_id}/note` | POST | 管理者备注 |
| `/candidates/angles/{angle_id}/status` | POST | 状态机迁移（含审计） |
| `/trends/{trend_id}` | GET | 趋势详情：评分时间线、分项、成员视频、频道分布 |
| `/history` | GET | 按日期浏览历史候选与状态 |
| `/brief` | GET | 简报预览 |
| `/brief/sync` | POST | 从当日选中项同步简报 |
| `/brief/reorder` | POST | 调整条目顺序 |
| `/brief/items/{item_id}/note` | POST | 编辑条目备注 |
| `/brief/export/markdown` | GET | 下载 Markdown |
| `/brief/export/html` | GET | 下载 HTML |
| `/watchlist` + 子路由 | GET/POST | 监控项 CRUD、CSV 导入、启停、手动触发抓取、删除 |
| `/logout` | POST | 注销 session |

# Request Schema

- 表单提交为 `application/x-www-form-urlencoded`（HTMX 或原生 form）。
- 所有 POST 需携带 CSRF token：表单 hidden field 或 HTMX `X-CSRF-Token` 头，token 存于签名 session。
- CSV 导入字段：`type,platform,name,url_or_id,tier,tags,note,enabled`。

# Response Schema

- JSON 端点：`/health*`、`/admin/status`。
- HTML 端点返回完整页面或 HTMX 片段。
- 认证行为：`MANAGER_PASSWORD` 为空时跳过认证（开发模式）；已配置时未认证请求被 `AuthMiddleware` 303 重定向到 `/login?next=<path>`。豁免前缀：`/health`、`/login`、`/docs`、`/openapi.json`、`/redoc`。

# State Transitions

CreativeAngle 状态机（经 `/candidates/angles/{id}/status`，每次迁移写入 `angle_status_audits`）：

```text
candidate -> selected -> adopted -> published
adopted   -> reusable
published -> reusable
candidate | selected -> blocked
```

Brief 状态：`draft -> finalized -> exported`。

# Compatibility Notes

- 新增路由与可选表单字段向后兼容。
- 更改路由路径、认证豁免前缀或 CSRF 机制属破坏性变更。
- `/admin/status` 的 payload 字段是运维脚本与文档的依赖面（见 `OPS.md`），删除字段需版本评估。

# Breaking Change Policy

路由、认证或状态机变更需用户确认并按 `conventions.md` 评估 SemVer；同时更新本契约与 `domains/admin-web.md`。

# Citations

- [System Architecture](../architecture.md)
- [Operations Manual](../../../OPS.md)
