---
type: paradigma-plan
title: Beta Stabilization Plan
description: Hardening iteration that freezes product features and gates Beta on engineering repeatability and recommendation relevance.
tags: [plan, beta, stabilization, ci, relevance]
timestamp: 2026-07-17T11:16:00+08:00
paradigma:
  schema_version: "0.1"
  temperature: warm
  lifecycle: evolving
  update_policy: agent-editable
  epistemic_status: confirmed
  status: in-progress
  retrieval_hints:
    zh:
      - Beta 稳定化
      - 发布门
      - 工程硬化
    en:
      - beta stabilization
      - release gates
      - engineering hardening
  relations:
    depends_on:
      - /project-brief.md
      - /architecture.md
    related_to:
      - /contracts/scheduler-jobs-contract.md
      - /contracts/config-deployment-contract.md
---

# Goal

将当前里程碑标记为 **MVP Feature Complete / Beta Readiness: Not Ready**，冻结新产品功能，先通过 G1 工程可重复性与 G2 推荐相关性发布门。

# Scope

- G1：Python 3.12 CI、静态检查、全量测试、真实 PostgreSQL 迁移、Docker 冒烟。
- G1：job 级互斥、字幕/语义软依赖、数据库最终幂等。
- G1：运行配置进入镜像、启动期 fail-fast、生产弱密钥拒绝。
- G1：候选阈值外置，analysis run 保存配置与算法版本。
- G2：英语动漫目标相关性过滤，Hindi / manhwa / generic 反例回归。

G3 跨表述保守合并与 G4 发布表现回收保留为后续发布门，本迭代不实现 embedding/LLM 聚类或自有账号 API。

# Approach

1. 先修锁冲突、写入幂等与容器配置，消除运行时不确定性。
2. 再把候选规则与运行版本变成可追溯配置。
3. 以 CI Wave A 固化工程门，再通过可复现 golden dataset 实现 G2。

# Tasks

- [x] 独立 transcript / semantic advisory lock，未知 job 禁止默认回退。
- [x] 保护成功字幕终态，为 creative angle 增加唯一约束。
- [x] 根 Dockerfile 打包 config，新增 `.dockerignore` 与启动配置校验。
- [x] 外置候选参数并新增 `analysis_runs`。
- [x] CI Wave A：pd-check、ruff、pytest、migration、integration、docker-smoke。
- [x] G2 relevance filter 与 golden regression。

# Status

**Completed** — 2026-07-17。G1/G2 自动门已落地；mypy 暂为 advisory，G3/G4 保留后续迭代。
