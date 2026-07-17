---
type: paradigma-progress-log
title: G3/G4 and MyPy Hardening
description: Session log for trend consistency baseline, bounded clustering, publication metrics, and blocking MyPy.
tags: [progress, g3, g4, mypy, beta]
timestamp: 2026-07-17T13:13:00+08:00
paradigma:
  schema_version: "0.1"
  temperature: cold
  lifecycle: append-only
  update_policy: append-only
---

# G3/G4 and MyPy Hardening

## Summary

完成 0.9.0：G3 一致性基线与有界聚类、G4 公开 YouTube 表现回收与简报只读 finalize、MyPy 阻断门。

## Done

- ADR-004 + G3/G4 plan + baseline drift known-issue
- relevance / channels-72h / activity_24h / member soft-sync / trend discovery analysis_runs
- Embedding providers（local_onnx / remote_api / lexical）、灰区 LLM、人工合并/移出、审计表
- Publication URL 强制、四窗口快照、PerformanceRatio、`/performance`、brief finalize
- `mypy app` = 0；CI blocking；unit 129 + integration 4；golden Precision@15 66.7%

## Remaining / Observation

- 真实 Beta：G3 误合并/误拆分人工抽样；G4 ≥14 天与 ≥20 条有效发布
- Worker 镜像预置本地 embedding 模型仍可按部署需要加强（代码已支持降级）
