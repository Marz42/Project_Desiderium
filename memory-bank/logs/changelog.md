# 变更日志

> 记录 Desiderium 应用的版本发布历史。
>
> 格式遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/)，版本号遵循 [SemVer](https://semver.org/lang/zh-CN/)，以根目录 `VERSION` 为唯一真源。
>
> Memory-Bank harness 版本单独记录在 `.paradigma/config.yaml` 的 `paradigma_harness_version`。

---

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
