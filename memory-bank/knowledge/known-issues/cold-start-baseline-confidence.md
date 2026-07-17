---
type: paradigma-known-issue
title: Cold-start Channel Baselines Have Low Confidence
description: Without accumulated metric snapshots, channel baselines rely on cold-start velocity estimates for the first 2-4 weeks.
tags: [known-issue, baselines, cold-start, snapshots]
timestamp: 2026-07-17T09:09:00+08:00
paradigma:
  schema_version: "0.1"
  temperature: cold
  lifecycle: evolving
  update_policy: agent-editable
  epistemic_status: confirmed
  retrieval_hints:
    zh:
      - 冷启动
      - 基准置信度
      - 快照积累
    en:
      - cold start
      - baseline confidence
      - snapshot accumulation
  relations:
    related_to:
      - /domains/trend-engine.md
---

# Symptom

新部署或新增频道后，`channel_baselines` 缺少足够快照样本，播放速度只能用冷启动估算（`当前播放量 ÷ max(视频年龄小时数, 2)`），BreakoutRatio 波动大且偏差不可控。

# Impact

- 上线后前 2—4 周的趋势评分置信度整体偏低，异常判定可能高估或低估。
- 样本 < 5 条的频道回退到全局基准，掩盖频道个体差异。

# Root Cause

YouTube 公开接口只返回当前累计统计，无法回溯历史时点播放量；基准必须靠系统自身持续保存快照才能建立。

# Workaround

- 基准带样本量置信度（low/medium/high，阈值在 `config/scoring.yaml` baselines 节），UI 与评分侧可见。
- 低置信基准不单独触发高置信趋势（趋势门槛要求多频道共振佐证）。

# Permanent Fix

无法根除，属数据积累问题。缓解路径：持续运行 4h 快照任务 2—4 周后，重点频道基准自然升级到 medium/high；新增频道的冷启动期同理。

# Related Documents

- `memory-bank/knowledge/domains/trend-engine.md`
- `memory-bank/knowledge/contracts/data-model-contract.md`

# Status

**Accepted limitation** — 机制性缓解已实施（置信度分级 + 全局回退），随快照积累自然收敛。
