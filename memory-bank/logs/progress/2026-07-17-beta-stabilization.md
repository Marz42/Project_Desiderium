# Beta Stabilization — G1/G2 Hardening

- **时间**：2026-07-17 10:37–11:16 (UTC+8)
- **版本**：0.8.0
- **结果**：MVP Feature Complete；G1/G2 自动发布门已实施。

## Delivered

- CI 拆为 memory-bank、quality、unit-tests、migration-tests、integration-tests、docker-smoke、golden-regression。
- transcript/semantic 独立 advisory lock；未知 job fail-fast；字幕 success 终态与 unavailable 7 天冷却。
- creative angle 唯一约束 + PostgreSQL conflict-safe 写入。
- 候选参数外置；新增 `analysis_runs` 和 `daily_candidates.analysis_run_id`，保存 config hash/snapshot、scoring、prompt、algorithm 版本。
- 运行配置启动验证；生产弱密钥保护；两套镜像使用真实 venv 并包含 config。
- Compose 使用一次性 migrate 服务，避免 Web/Worker 并发迁移。
- G2 规则过滤 Hindi/非英语及 manhwa/webtoon/manhua，generic list 配置化降权。
- 可复现 golden fixture 与 non-zero regression gate。

## Verification

- `ruff check .`：通过。
- `ruff format --check .`：140 files formatted。
- `pytest -q`：84 passed, 1 skipped（integration 默认跳过）。
- PostgreSQL 16：fresh upgrade、integration idempotency、downgrade base、re-upgrade head 全部通过；20 张 public 表（含 alembic_version）。
- Docker：dev/prod image build、`pip check`、runtime assets、单次迁移、Web/Worker 启动、`/health/ready` 通过。
- Golden：30 videos / 18 channels / 6 trends；Precision@15 66.7%；高价值召回 100%。

## Remaining

- mypy 已进入 CI advisory，当前基线仍有 52 个类型错误，不阻断 0.8.0。
- G3 跨表述保守合并与 G4 发布表现回收未在本迭代实施。
- 真实 Beta 流量需监控 G2 规则的误杀/漏报。
