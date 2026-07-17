# Project Desiderium

*Anime trend intelligence system — 面向番剧解说团队的趋势发现与选题辅助系统*

当前版本：`0.7.2`（见根目录 `VERSION`）

系统每日从管理者维护的 YouTube 频道 / 关键词 / 作品监控列表采集内容，通过 **跨频道共振 × 相对频道基准表现异常** 判断热门题材，用 LLM 生成中文趋势解释与创作方向，最终产出约 30 个候选，供管理者审核并导出 Markdown / HTML 简报。

## Quick Start

```bash
cp .env.example .env        # 填入 YOUTUBE_DATA_API_KEY 等
docker compose up --build
```

健康检查：

- `GET http://localhost:8000/health/live` — liveness
- `GET http://localhost:8000/health/ready` — readiness（含 PostgreSQL）
- `GET http://localhost:8000/health` — DB + 磁盘 + worker 心跳

本地开发（无 Docker）：

```bash
pip install -e .
pytest
uvicorn app.main:app --reload      # Web
python -m app.worker               # Worker（另一终端）
```

**技术栈**：Python 3.12、FastAPI、Jinja2 + HTMX、PostgreSQL 16、SQLAlchemy 2 async、Alembic、APScheduler、Docker Compose。

## 系统组成

```text
Internet → Caddy (HTTPS) → web (FastAPI SSR 管理后台)
                              ↕ PostgreSQL 16
                           worker (APScheduler: 采集/快照/趋势/语义/运维任务)
```

| 页面 | 用途 |
|------|------|
| `/candidates` | 今日约 30 个候选方向，按趋势分组，勾选与备注 |
| `/trends/{id}` | 趋势详情：评分时间线、成员视频、频道分布 |
| `/watchlist` | 监控项管理、CSV 导入、手动触发抓取 |
| `/history` | 按日期回看候选与选题状态 |
| `/brief` | 简报排序、预览与 Markdown / HTML 导出 |

## 生产部署与运维

- 部署 / 监控 / 备份：[OPS.md](OPS.md)
- 故障恢复 runbook：[RECOVERY.md](RECOVERY.md)

```bash
docker compose -f docker-compose.prod.yml up -d --build
```

## 项目结构

```text
app/            # 应用源码：web / jobs → services → domain；adapters / repositories
config/         # 算法阈值、LLM、TikTok、prompts（评分参数全部在 scoring.yaml）
migrations/     # Alembic 迁移（容器启动自动 upgrade head）
tests/          # pytest 单测（不调用真实外部 API）
scripts/        # 备份 / 恢复 / 磁盘监控 / 影子验证
deploy/         # Caddy、systemd
memory-bank/    # Agent 长期记忆（见下节）
docs/rfc/       # 本项目 RFC / 提案区
```

## Memory-Bank（Agent 记忆）

本仓库内嵌 Paradigma harness（OKF-compatible Memory-Bank），为 AI Agent 提供跨会话的项目记忆。它与应用运行时无关，只服务于开发过程。

- `memory-bank/runtime/` — 当前任务状态
- `memory-bank/logs/` — 会话日志与 changelog
- `memory-bank/knowledge/` — 长期知识：HOT（brief / architecture / conventions / repository contract）+ contracts / domains / decisions / known-issues / manuals / plans

Agent 读取顺序与维护协议见 `AGENT_RULES.md`（Cursor 适配器：`.cursor/rules/memory-bank-protocol.mdc`）。

维护命令：

| 命令 | 用途 |
|------|------|
| `python .paradigma/tools/pd-check-all.py` | 质量门禁：strict lint + link check + index check + hot-size |
| `python .paradigma/tools/pd-sync-index.py --write` | 重新生成知识索引 |
| `python .paradigma/tools/pd-archive-task.py --write` | 归档已完成的 active task |
| `python .paradigma/tools/pd-compact-progress.py --write` | 压缩 progress 日志 |

版本双轨：根 `VERSION` 追踪应用 SemVer；`.paradigma/config.yaml` 的 `paradigma_harness_version` 追踪 harness 版本（更新 harness 用 `pd-diagnose.py --upstream <path>` 评估差距）。

## 致谢与许可

Memory-Bank harness 源自 [Paradigma](https://github.com/Marz42/paradigma)（MPL-2.0），其格式标准来自 [OKF](https://github.com/GoogleCloudPlatform/knowledge-catalog)。修改 harness 自身源码（`.paradigma/tools/` 等）需按 MPL-2.0 开源回馈；应用代码许可以仓库 LICENSE 为准。
