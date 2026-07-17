---
type: paradigma-session-log
title: Memory-Bank Overhaul to Match Desiderium Application
description: Full rewrite of HOT knowledge, contracts, domains, decisions, known issues, and logs to reflect the delivered application; removal of upstream Paradigma project history.
tags: [session, memory-bank, documentation, overhaul]
timestamp: 2026-07-17T09:09:00+08:00
paradigma:
  layer: log
  lifecycle: append-only
  okf_export: optional
  update_policy: append-only
---

# Session Summary

## User Goal

按 Paradigma 契约要求，结合项目代码与设计，对 memory-bank 与 README 做完整审查：补齐缺失、修正错误，清除上游 Paradigma 项目自身的历史与决策残留。

## Actions Taken

- 重写 HOT：`project-brief.md`（补 OKF frontmatter，收敛为 Desiderium brief）、`architecture.md`（应用架构 + 数据流 + 应用侧 Open Questions）、`conventions.md`（应用编码/测试/双轨版本规范）、`contracts/repository-contract.md`（应用 + harness 双子系统边界，补 exit code 2 与工具参数）。
- 新增应用契约：`web-api-contract.md`、`data-model-contract.md`、`scheduler-jobs-contract.md`、`config-deployment-contract.md`。
- 新增应用领域文档：watchlist-ingestion、trend-engine、semantic-analysis、admin-web、tiktok-experiment、operations；删除 Paradigma 域（protocol/tooling/plans/migration-flows/design-system）。
- 重建 ADR：adr-001 单 Worker APScheduler、adr-002 规则聚类优先、adr-003 TikTok 隔离实验；删除 Paradigma ADR-001~003。
- 重建 known-issues：影子验证误报、冷启动基准置信度、API key 泄漏事故；删除 Paradigma known-issues。
- 重建 manuals：desiderium-ops / desiderium-recovery（canonical 指向根目录 OPS.md / RECOVERY.md）；删除 paradigma-* manuals。
- `plans/mvp-plan.md` 补 frontmatter（paradigma-plan，completed/cold）与 Goal/Scope/Approach/Tasks/Status 摘要；删除 pd-next-milestones。
- 重写 glossary 为业务术语表；删除 docs/rfc 中的 Paradigma RFC。
- 删除 2026-06-02 ~ 07-05 的 Paradigma 开发日志，重建 progress index（Stage 0–8 + 本次会话）。
- 重写 changelog 为 Desiderium 版本史；README 以应用为主体；版本对齐（VERSION / pyproject / harness version）。

## Files Read

- `.paradigma/schemas/paradigma-types.schema.yaml`、`memory-bank-template/**`
- `app/`（main/config/models/scheduler/worker/middleware）、`config/scoring.yaml`、`.env.example`、`docker-compose.prod.yml`、`OPS.md`、`RECOVERY.md`
- 全部原 memory-bank knowledge 与 Stage 0–8 progress logs

## Files Modified

见上文 Actions；净变化：knowledge 层 21 → 22 个 concept 文档，全部通过 strict lint。

## Decisions Proposed

- 双轨版本：根 `VERSION` = 应用 SemVer；`.paradigma/config.yaml` 的 `paradigma_harness_version` = harness 版本。

## Decisions Accepted

- 上游 Paradigma 项目的历史文档（ADR、known-issues、manuals、RFC、旧日志）从本项目 memory-bank 移除；harness 工具与协议文件保留。

## Knowledge Updates

- HOT 4 篇重写；contracts +4；domains 6 新 5 删；decisions 3 新 3 删；known-issues 3 新 3 删；manuals 2 新 4 删；glossary 重写；mvp-plan 补 frontmatter。

## Follow-ups

- CI 增加 Python 3.12 pytest 与 Alembic 迁移检查（architecture Open Questions 在案）。
- 泄漏 API key 已确认吊销（见 known-issues/api-key-leak-in-shadow-cache.md）；防复发脱敏/扫描仍待办。
