---
type: paradigma-glossary
title: Project Glossary
description: Core terms for the Desiderium anime trend intelligence system and its memory-bank.
tags: [glossary, terms, trends]
timestamp: 2026-07-17T09:09:00+08:00
paradigma:
  schema_version: "0.1"
  temperature: cold
  lifecycle: evolving
  update_policy: agent-editable
  epistemic_status: confirmed
  retrieval_hints:
    zh:
      - 术语
      - 缩写
      - 业务概念
    en:
      - terms
      - abbreviations
      - domain concepts
  relations:
    related_to:
      - /project-brief.md
---

# Terms

| 术语 | 定义 |
|------|------|
| WatchItem | 统一监控项：频道 / 账号 / 关键词 / 动漫作品 / 榜单页面，带平台、等级、标签与抓取状态（`watch_items` 表） |
| Tier（监控等级） | priority（重点，~5h 抓取）/ general（一般，~18h）/ experimental（实验，评分权重 0.5） |
| ContentItem | 采集到的视频等原始内容，含 `raw_payload` 原始响应（`content_items` 表） |
| Metric Snapshot | 视频指标时间序列快照，按小时桶去重；系统最重要的基础设施 |
| 年龄桶（Age Bucket） | 视频发布时长分段：0–6h / 6–24h / 24–72h / 3–7d，表现比较只在同桶内进行 |
| 播放速度（Velocity） | 观察窗口内新增播放 ÷ 窗口小时数；无历史快照时用冷启动估算 |
| Channel Baseline | 频道在某年龄桶下最近约 20 条视频的播放速度中位数，带样本量置信度 |
| BreakoutRatio | 视频速度 ÷ 频道同龄基准速度，截断上限 8；≥2 明显异常，≥4 强突破 |
| 跨频道共振 | 多个不同频道短期内发布同一题材——趋势判定的第一权重（35%） |
| TrendTheme | 趋势主题（作品 / 角色 / 篇章 / 事件），跨日复用同一 ID，带生命周期状态 |
| Lifecycle Status | new / rising / stable / declining / reviving / dormant，由活动值增长比判定 |
| TrendScore | 综合评分：共振 35% + 相对异常 25% + 动量 20% + 持续性 10% + 规模 5% + 新鲜度 5% |
| CreativeAngle | 每日可执行的中文创作方向，带 format（short/long/both）与证据视频 ID |
| Daily Candidate | 每日候选排序快照（约 30 个方向），保证历史可重现 |
| Brief | 管理者审核后导出的简报（Markdown / HTML），按趋势分组 |
| 状态机 | candidate → selected → adopted → published；分支 reusable / blocked；迁移有审计 |
| Source Confidence | 数据来源置信度：YouTube high，TikTok 实验抓取 low |
| Golden Dataset | Stage 1 影子验证产出的回归基线（真实视频 + 人工趋势标注） |
| 影子验证（Shadow Validation） | 开发完整后台前用真实数据验证评分算法的阶段（Stage 1） |
| Memory-Bank | 本仓库内嵌的 Agent 长期记忆结构（runtime / logs / knowledge 三态） |
| HOT / WARM / COLD | 知识温度：每次会话必读 / 按任务路由 / 按需检索 |

# Abbreviations

| 缩写 | 全称 |
|------|------|
| ADR | Architecture Decision Record |
| ASR | Automatic Speech Recognition（可选转录后备） |
| CSRF | Cross-Site Request Forgery（表单 + HTMX 头双通道 token） |
| OKF | Open Knowledge Format（knowledge 文档的 frontmatter 标准） |
| SSR | Server-Side Rendering（Jinja2 + HTMX） |
| MVP | Minimum Viable Product（Stage 0–8 交付范围） |

# Domain-specific Meanings

- **"热门破圈"**：不是绝对播放量高，而是"跨频道共振 × 相对频道基准表现异常"同时成立。
- **"早期信号"**：24h 内 ≥2 频道 + 1 条 BreakoutRatio ≥ 4 + 额外佐证；比正式趋势门槛更敏感，单独标记。
- **"证据"（Evidence）**：LLM 结论必须引用的 trend member 视频 ID；无证据的结论会被 `EvidenceValidator` 拒绝。
- **"实验来源"**：TikTok 等不承诺稳定性的数据源；进入候选池但降低置信度，不得单独认定趋势。
