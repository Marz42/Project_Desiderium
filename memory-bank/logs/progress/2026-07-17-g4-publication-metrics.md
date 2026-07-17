# G4 — Publication Performance Feedback & Brief Read-only

- **时间**：2026-07-17 12:02–12:50 (UTC+8)
- **版本**：0.8.0 → 未发版（Unreleased，VERSION 未修改）
- **结果**：G4 发布表现回收 + 简报只读化的代码、迁移、测试、契约与领域文档全部完成；G3 一致性基线修复留待下一迭代。

## Delivered

- 发布链路：标记 `published` 强制要求合法 YouTube URL（watch/shorts/youtu.be），解析 video_id；`PublicationRecord` 扩展 `platform`/`external_video_id`/`channel_external_id`/`trend_id`/`daily_candidate_id`/`format`/`fetch_status`/`last_fetch_error`/`last_fetched_at`；发布时 best-effort 即时抓取一次，API 失败只标记 `fetch_status=failed`，绝不回滚 angle 状态。
- 新表 `publication_metric_snapshots`（`UNIQUE(publication_record_id, window_key)`），`app/services/publication_metrics.py` 负责到期窗口调度、YouTube 抓取、PerformanceRatio（团队基准速度 by format×age_bucket，样本不足降级为全量低置信度兜底）、幂等 upsert、逐记录错误隔离。
- 新任务 `publication_metrics`（每 2 小时，advisory lock `1401`），无 API key 时整体跳过并记录日志。
- `config/scoring.yaml` 新增 `publication:` 段（`team_channel_ids` / `windows_hours` / `late_backfill_grace_hours`），`config_validation.py` 校验窗口首项为 0、严格递增、宽限期非负。
- 简报只读化：`GET /brief` 不再自动同步/标记导出；新增 `POST /brief/finalize` 冻结当前草稿为 JSONB 快照 + SHA-256 content_hash；导出优先使用固化快照；`mark_exported` 不降级已固化简报。
- 历史页展示 `published_url` 与最新 `performance_ratio`；新页面 `/performance` 汇总 adopt/publish 转化率、发布时延、PerformanceRatio 均值（按窗口/format/lifecycle/score band），并明确标注仅为关联性。
- Alembic 迁移 `e5f6a7b8c9d0`（`d4e5f6a7b8c9` 之后）：全部按列/表存在性判断，兼容 fresh create_all 与增量升级；本地针对 Docker PostgreSQL 验证了 fresh upgrade、`d4e5f6a7b8c9 -> head`、downgrade→再 upgrade 三条路径。

## Fixed

- `BriefRepository.get_or_create` 为全新 `Brief` 显式预置 `items=[]`，修复了首次访问从未创建过简报的日期时的 `sqlalchemy.exc.MissingGreenlet` 崩溃（写入 known-issue `brief-lazyload-missing-greenlet`）。此前无测试覆盖"全新日期首次 GET"路径，因此该 bug 一直潜伏。

## Verification

- `mypy app`：0 错误（103 个源文件）。
- `ruff check app tests`：全部通过。
- `pytest tests/unit -q`：125 passed（含 42 个新增用例：YouTube URL 解析、G4 纯计算、发布 URL 校验/API 失败隔离）。
- `RUN_INTEGRATION_TESTS=1 pytest tests/integration -q`（针对本机 Docker PostgreSQL，已迁移到 head）：4 passed（含新增 `test_brief_workflow.py` × 2、`test_publication_workflow.py` × 1，以及既有 `test_database_hardening.py`）。
- `alembic check`（针对已迁移数据库）：`No new upgrade operations detected.`，模型与迁移无漂移。

## Notes

- Windows + pytest-asyncio 函数级 event loop 会导致跨测试复用同一全局异步引擎连接池报错（`Event loop is closed`）；新增 `tests/integration/conftest.py` 在每个集成测试结束后 `dispose_engine()`，强制下一个测试绑定新连接池。
- 未改动 `memory-bank/knowledge/plans/g3-g4-stabilization-plan.md`（按用户要求）；`VERSION` 未修改，改动记录在 changelog 的 `[Unreleased]` 段。

## Remaining

- G3 一致性基线（relevance 传递、正式趋势门频道计数、activity 口径统一、成员 upsert）尚未开始。
- 真实 G4 观察门（≥14 天、≥20 条发布记录）需要生产真实数据积累，本迭代只交付代码与自动化测试。
