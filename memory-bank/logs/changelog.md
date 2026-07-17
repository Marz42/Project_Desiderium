# 变更日志

> 记录 Desiderium 应用的版本发布历史。
>
> 格式遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/)，版本号遵循 [SemVer](https://semver.org/lang/zh-CN/)，以根目录 `VERSION` 为唯一真源。
>
> Memory-Bank harness 版本单独记录在 `.paradigma/config.yaml` 的 `paradigma_harness_version`。

---

## [Unreleased]

## [0.10.0] - 2026-07-17

### Added
- **Iteration 5 观察工具**：`scripts/observation/g3_report.py`、`g3_sample_export.py`（calibration/holdout 隔离）、`g4_report.py`（漏斗 + 成熟窗口关联）。
- **成员决策优先级**：`app/domain/membership_policy.py` 固化 `MANUAL > LLM > EMBEDDING > RULE`。
- **快照式回滚**：`manual_merge` / `manual_move_out` evidence 保存受影响成员；`rollback_decision` 事务化、幂等、冲突检测（`RollbackConflict`）。
- **Analysis run 重试语义**：显式 `analysis_run_id` 重试复用；`run_fingerprint` 区分任务重试与新运行。
- **G4 历史快照**：`daily_candidates.trend_score_snapshot` / `lifecycle_status_snapshot`；`publication_metric_snapshots.baseline_version` / `observed_ratio_at_window` / `calculated_at`。
- **发布失败退避**：`publication_records.consecutive_fetch_failures` / `next_retry_at` / `terminal_fetch_failure`。

### Changed
- **发布 URL 唯一性**：`UNIQUE(platform, external_video_id)` + 服务层 `PublishedUrlConflict` + 同 angle 幂等。
- **Brief finalize 不可变**：原子条件更新；新增 `finalized_by`；并发 finalize 只保留首份快照。
- **Publication 窗口幂等**：快照 upsert 改为 `ON CONFLICT DO NOTHING`；晚录入只捕获最新成熟窗口，不伪造历史 24h。
- **Performance 分析**：分组使用候选时 lifecycle/score 快照，而非当前 trend 状态。
- scoring.yaml publication 段增加 `baseline_version` / `max_consecutive_failures` / `retry_backoff_hours`。

### Fixed
- 人工移出后 RULE/EMBEDDING/LLM 自动 sync 不再重新激活成员。
- 合并回滚按审计快照恢复，不推断目标趋势当前成员。
- `video_age_hours` 正确处理 naive 与 DST 边界。

### Tests
- G3/G4 单元与 PostgreSQL 集成（URL 并发、finalize 并发、membership 优先级、回滚、窗口/退避）。
- 单元测试 140+ passed；integration 7+ passed（Postgres）。

## [0.9.0] - 2026-07-17

### Added
- **G3 有界聚类**：规则硬约束 + Embedding 有限召回（默认 local ONNX，远程 API 可选，失败降级 lexical）+ LLM 灰区裁决；支持 facet、决策审计、人工合并/移出与回滚标记。
- ADR-004：明确规则优先、Embedding 仅召回、LLM 只做有限枚举裁决。
- 新表 `embedding_cache` / `trend_facets` / `cluster_decision_audits`；`trend_members` 增加 `active` / `last_confirmed_at` / `deactivated_at` 软同步。
- 趋势发现写入 `analysis_runs(run_kind=trend_discovery)`；golden builder 同步调用生产 `cluster_videos`。
- **G4 发布表现回收**：published 必填合法 YouTube URL；`publication_metric_snapshots` 四窗口幂等回收；`/performance` 关联分析页；`publication_metrics` 定时任务。
- **简报只读化**：`GET /brief` 无副作用；显式 finalize 冻结快照。
- MyPy 阻断门：`mypy app` 零错误且 CI 不再 `continue-on-error`。

### Changed
- 正式趋势门改为 72h **distinct channels**；生命周期 `activity_24h` 统一为 `cluster_activity`；relevance_multiplier 进入成员评分行。
- scoring.yaml → `1.2`（clustering / publication 段）。

### Fixed
- 生产与 G2 golden 的 relevance / 阈值 / activity 口径漂移（见 known-issue `trend-consistency-baseline-drift`）。
- Brief 首次创建 `MissingGreenlet`（见 known-issue `brief-lazyload-missing-greenlet`）。

### Tests
- G3 约束/lexical embedding 单测；G4 URL/PerformanceRatio/发布状态单测与 brief/publication 集成测试。
- 单元测试 129 passed；integration 4 passed（Postgres）。

## [0.8.0] - 2026-07-17

### Added
- Beta Stabilization 发布门：Python 3.12 CI、ruff、全量 pytest、fresh/previous-schema migration、PostgreSQL integration、双镜像与 Compose readiness、golden regression。
- `analysis_runs` 追溯候选生成使用的 scoring/config/prompt/algorithm 版本与配置快照；候选阈值和 G2 相关性规则全部配置化。

### Changed
- 里程碑标记为 MVP Feature Complete；G1/G2 自动门已实施，G3/G4 保留后续。
- Hindi/非英语与 manhwa/webtoon/manhua 明确排除，generic list 降权；可复现 golden fixture Precision@15 66.7%、高价值召回 100%。

### Fixed
- transcript/semantic advisory lock 分离，未知任务不再回退共享锁；字幕终态/冷却与 creative angle 数据库幂等补齐。
- 开发镜像补齐 `config/`，两套 Dockerfile 改用真实 venv；Compose 使用单独 migrate 服务，消除 Web/Worker 并发迁移竞态；启动期配置 fail-fast。

## [0.7.2] - 2026-07-17

### Fixed
- 修复全新数据库 `alembic upgrade head` 失败的 P0 部署阻断：初始迁移 `create_all` 排除后续迁移拥有的 5 张表；`lifecycle_status` / `angle_status` 复用列改用 `postgresql.ENUM(..., create_type=False)`；`ix_metric_snapshots_content_captured` 创建改为 `if_not_exists`。fresh migration 与 downgrade/upgrade 往返在 PostgreSQL 16 实测通过。

## [0.7.1] - 2026-07-17

### Changed
- Memory-Bank 全面重构：HOT 知识（brief / architecture / conventions / repository contract）重写为 Desiderium 应用事实；新增 web-api / data-model / scheduler-jobs / config-deployment 四份契约与六份应用领域文档；重建 ADR、known-issues、manuals、glossary。
- README 以应用为主体重写；版本对齐（`VERSION` / `pyproject.toml` 统一为 0.7.1）。

### Removed
- 移除上游 Paradigma 项目自身的历史文档（ADR-001~003、框架 known-issues、paradigma-* manuals、OKF RFC、2026-06/07 框架开发日志）。harness 工具链（`.paradigma/tools/`）与协议文件保留。

## [0.7.0] - 2026-07-17

### Added
- **Stage 8 部署与运维**：`Dockerfile.prod`、`docker-compose.prod.yml`（Caddy HTTPS、backup profile）、备份/恢复脚本、日志轮转、磁盘监控、`/admin/status` 面板、扩展 `/health`、快照保留任务、YouTube 配额持久化、LLM 用量追踪、`OPS.md` / `RECOVERY.md`、systemd 单元。
- **Stage 7 TikTok 实验适配器**：隔离的账号/关键词/榜单抓取、cookie 失效检测、选择器版本隔离、`source_confidence: low`、独立任务与重试、`TIKTOK_ENABLED` 默认关闭。
- **Stage 5 管理后台**（含原 Stage 6 状态机）：单管理者认证 + CSRF、今日候选 / 趋势详情 / 历史 / 简报预览页面、Markdown/HTML 导出、candidate→selected→adopted→published 状态机与审计表。

## [0.6.0] - 2026-07-17

### Added
- **Stage 4 语义层**：字幕分层获取（公开字幕 → 可选 ASR → 元数据降级）、OpenAI-compatible LLM adapter（JSON Schema 输出）、版本化 prompts、语义管道（翻译 / 命名 / 热门原因 / 创作方向）、证据校验与语义去重、字幕与语义定时任务。
- **Stage 0–3（此前未单独发版）**：FastAPI + PostgreSQL 工程基线与全数据模型（Stage 0）；影子验证与 golden dataset，Precision@15 60%（Stage 1）；Watchlist CRUD + CSV 导入 + 配额感知 YouTube 采集 + 任务互斥（Stage 2）；指标快照、频道基准、BreakoutRatio、规则聚类、综合评分与生命周期（Stage 3）。

---

> 0.6.0 之前的版本号（≤0.5.0）属于本仓库作为 Paradigma harness 模板孵化期的历史，与应用无关，已随框架文档一并归档移除。
