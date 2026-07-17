---
type: paradigma-domain
title: Admin Web Domain
description: Single-manager SSR admin backend — daily review workflow, status machine, and brief export.
tags: [domain, web, admin, htmx, brief]
timestamp: 2026-07-17T09:09:00+08:00
paradigma:
  schema_version: "0.1"
  temperature: warm
  lifecycle: evolving
  update_policy: agent-editable
  epistemic_status: confirmed
  retrieval_hints:
    zh:
      - 管理后台
      - 每日审核
      - 简报导出
      - 状态机
    en:
      - admin backend
      - daily review
      - brief export
      - status machine
  symbols:
    - AuthMiddleware
    - brief_export
    - angle_status
    - daily_candidates
  relations:
    depends_on:
      - /architecture.md
    related_to:
      - /contracts/web-api-contract.md
      - /contracts/data-model-contract.md
---

# Responsibility

管理者每日端到端工作闭环：查看约 30 个候选方向 → 勾选 10—15 个 → 备注与状态标记 → 调整简报顺序 → 导出 Markdown / HTML。技术形态为 Jinja2 + HTMX + Tailwind CDN 的服务端渲染。

# Public Interfaces

| Interface | Role | Path |
|-----------|------|------|
| 五页路由 | candidates / trends / watchlist / history / brief | `app/web/routes/` |
| Auth / Session / CSRF | 单密码登录、签名 session cookie、双通道 CSRF token | `app/web/middleware.py`, `session.py`, `csrf.py` |
| `AdminCandidatesService` 等 | 候选查询、筛选、勾选 | `app/services/admin_*.py` |
| `AngleStatusService` | 状态机迁移 + `angle_status_audits` 审计 | `app/services/angle_status.py` |
| `CandidateGeneration` | 每日候选快照生成（挂在语义管道之后） | `app/services/candidate_generation.py` |
| `BriefExport` | Markdown / HTML 渲染与下载 | `app/services/brief_export.py` |
| Templates | 页面与 HTMX 片段 | `app/web/templates/` |

# Internal Flow

```text
GET /candidates -> daily_candidates (当日, 按趋势分组, 筛选: lifecycle/anime/format/priority)
POST toggle/note/status -> HTMX 片段更新 + 审计
GET /brief -> POST /brief/sync (从选中项建 brief_items) -> reorder/note
GET /brief/export/{markdown,html} -> 按趋势分组渲染 (英文原标题 + 中文翻译 + 数据证据)
```

历史页按日期回放 `daily_candidates` 与状态（selected/adopted/published/reusable/blocked）。

# Dependencies

- 上游数据：趋势引擎与语义分析产物（`daily_candidates` / `creative_angles`）。
- `MANAGER_PASSWORD` / `SECRET_KEY` 环境变量（空密码 = 开发模式免认证）。

# Related Contracts

- `contracts/web-api-contract.md` — 路由、认证豁免、状态机迁移规则。
- `contracts/data-model-contract.md` — briefs / brief_items / angle_status_audits。

# Known Risks

- 单管理者假设深入 session 与 UI 设计，引入多用户需要 RBAC 层面的重构。
- Tailwind 经 CDN 引入，离线环境样式退化。
- 简报导出对超长标题 / 特殊 Markdown 字符的转义依赖模板层，新增字段时需回归导出测试。
