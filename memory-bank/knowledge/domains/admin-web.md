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
| 六页路由 | candidates / trends / watchlist / history / brief / performance | `app/web/routes/` |
| Auth / Session / CSRF | 单密码登录、签名 session cookie、双通道 CSRF token | `app/web/middleware.py`, `session.py`, `csrf.py` |
| `AdminCandidatesService` 等 | 候选查询、筛选、勾选 | `app/services/admin_*.py` |
| `AngleStatusService` | 状态机迁移 + `angle_status_audits` 审计；标记 `published` 需合法 YouTube URL，解析 video_id 并链接 `PublicationRecord`（G4） | `app/services/angle_status.py` |
| `PublicationMetricsService` | 发布即时抓取（best-effort）+ 定时窗口回收 + PerformanceRatio 计算（G4） | `app/services/publication_metrics.py` |
| `CandidateGeneration` | 每日候选快照生成（挂在语义管道之后） | `app/services/candidate_generation.py` |
| `BriefExport` | 只读预览（不自动同步/不标记导出）+ 显式 `sync`/`finalize` POST + Markdown / HTML 渲染下载 | `app/services/brief_export.py` |
| `PerformanceAnalyticsService` | adopt/publish 转化率、发布时延、PerformanceRatio 按 format/lifecycle/score band 汇总（G4，仅关联性，非因果） | `app/services/performance_analytics.py` |
| Templates | 页面与 HTMX 片段 | `app/web/templates/` |

# Internal Flow

```text
GET /candidates -> daily_candidates (当日, 按趋势分组, 筛选: lifecycle/anime/format/priority)
POST toggle/note/status -> HTMX 片段更新 + 审计
  status=published 必须提交 published_url（watch/shorts/youtu.be），否则 400 级 flash 错误（PublishedUrlRequired），不迁移状态
  发布成功后：写 PublicationRecord（platform/external_video_id/trend_id/daily_candidate_id）+ best-effort 立即抓取一次 initial 窗口指标；抓取失败只标记 fetch_status=failed，不回滚 angle 状态
GET /brief -> 只读：渲染当前草稿，绝不自动同步、绝不标记 exported
POST /brief/sync -> 从选中项重建 brief_items（显式动作）
POST /brief/finalize -> 冻结当前草稿为 JSONB 快照 + SHA-256 content_hash，brief.status=finalized；无草稿内容时返回失败提示
GET /brief/export/{markdown,html} -> 存在 finalized_snapshot 则渲染快照（不受后续编辑影响），否则渲染当前草稿；导出后才调用 mark_exported（不会把已 finalized 降级为 exported）
GET /performance -> adopt/publish 转化率、平均发布时延、按窗口/format/lifecycle/score band 的 PerformanceRatio 均值，页面明确标注"仅为关联性，非因果提升"
```

历史页按日期回放 `daily_candidates` 与状态（selected/adopted/published/reusable/blocked），并展示 `published_url` 与最新一次 `performance_ratio`（若有抓取到的 metric snapshot）。

# Dependencies

- 上游数据：趋势引擎与语义分析产物（`daily_candidates` / `creative_angles`）。
- `MANAGER_PASSWORD` / `SECRET_KEY` 环境变量（空密码 = 开发模式免认证）。

# Related Contracts

- `contracts/web-api-contract.md` — 路由、认证豁免、状态机迁移规则。
- `contracts/data-model-contract.md` — briefs / brief_items / angle_status_audits / publication_records / publication_metric_snapshots。
- `contracts/scheduler-jobs-contract.md` — `publication_metrics` 定时任务与团队基准配置。

# Known Risks

- 单管理者假设深入 session 与 UI 设计，引入多用户需要 RBAC 层面的重构。
- Tailwind 经 CDN 引入，离线环境样式退化。
- 简报导出对超长标题 / 特殊 Markdown 字符的转义依赖模板层，新增字段时需回归导出测试。
- `BriefRepository.get_or_create` 为全新 Brief 显式预置 `items=[]`；若未来新增其它关系字段的懒加载访问，需同样在事务内先行赋值，否则在 `AsyncSession` 下直接访问未预热的懒加载集合会抛 `MissingGreenlet`（已在 G4 read-only 测试中复现并修复一次）。
- PerformanceRatio 依赖团队自有基准（`publication.team_channel_ids` 或全量兜底），样本不足时置信度自动降级为 low；页面与文档必须持续强调"关联不等于因果"。
