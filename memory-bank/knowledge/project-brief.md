---
type: paradigma-project-brief
title: Project Brief
description: Vision, users, scope, and success criteria for Desiderium, an anime trend intelligence system for a content briefing team.
tags: [project, brief, scope, anime, trends]
timestamp: 2026-07-17T09:09:00+08:00
paradigma:
  schema_version: "0.1"
  temperature: hot
  lifecycle: stable
  update_policy: requires-human-confirmation
  epistemic_status: confirmed
  retrieval_hints:
    zh:
      - 项目愿景
      - 番剧解说
      - 选题辅助
      - 趋势发现
    en:
      - project vision
      - anime recap
      - topic selection
      - trend discovery
  symbols:
    - WatchItem
    - TrendTheme
    - CreativeAngle
    - BreakoutRatio
  relations:
    informs:
      - /architecture.md
      - /contracts/repository-contract.md
    related_to:
      - /plans/mvp-plan.md
---

# Vision

Desiderium 是一个面向单一管理者的番剧解说选题辅助系统：

> 维护不超过 100 个频道、账号、关键词和榜单监控项，以 YouTube 为稳定主数据源，每日识别"多个相关频道集中创作且视频相对频道平均表现更好"的趋势主题，生成约 30 个候选创作方向，由管理者筛选 10—15 个并导出简报。

核心判据是 **跨频道共振 × 相对频道基准的表现异常**，而不是绝对播放量。系统的核心不是 LLM，而是 Watchlist、统计快照、频道基准和趋势生命周期；LLM 只负责语义归纳（中文趋势解释、创作方向生成、标题翻译），不参与数值计算。

# Target Users

- **直接用户**：1 名运营策划兼管理者，使用 Web 后台完成每日审核。
- **间接用户**：5—10 名剪辑师，不登录系统，只接收管理者审核后的 Markdown / HTML 简报。
- **目标市场**：美国英语观众的番剧片段解说内容（每天约 25—50 条 Shorts、5—10 条长视频）。

# Scope

MVP 已交付的功能域（Stage 0–8，Stage 6 状态机并入 Stage 5 交付）：

1. 统一监控列表（Watchlist）：频道 / 账号 / 关键词 / 作品 / 榜单，CSV 批量导入，重点 / 一般 / 实验三级。
2. YouTube 频道采集与关键词搜索（配额感知，Uploads playlist 优先）。
3. 视频统计快照时间序列（按视频年龄动态调度）。
4. 频道中位数基准 + BreakoutRatio 单视频异常评分（四个年龄桶）。
5. 规则聚类 → 趋势主题（TrendTheme），趋势跨日复用同一 ID。
6. 综合趋势评分（共振 35% / 异常 25% / 动量 20% / 持续 10% / 规模 5% / 新鲜度 5%）与生命周期状态。
7. 重点视频字幕分层获取（公开字幕 → 可选 ASR → 元数据降级）。
8. LLM 语义层：中文趋势命名、热门原因、创作方向（含证据视频 ID 校验与语义去重）。
9. 管理后台五页：今日候选、趋势详情、监控列表、历史记录、简报预览与导出。
10. 选题状态机：candidate → selected → adopted → published，分支 reusable / blocked，含审计记录。
11. 可插拔 TikTok 实验适配器（默认关闭，低来源置信度，故障隔离）。
12. 生产部署与运维：Docker Compose + Caddy HTTPS、备份恢复、日志轮转、配额与 LLM 成本监控。

# Non-goals

第一版明确不做：

- 剪辑师账号和多角色权限；
- 自动分配选题、自动生成完整英文脚本 / 英文标题 / 钩子；
- 视频画面理解、自动下载或管理番剧素材；
- 完整稳定的 TikTok 全站数据服务；
- 个性化账号推荐、自动发布、复杂机器学习爆款预测；
- 自动读取团队发布账号数据（数据模型已预留 `published_*` 字段）。

# Success Criteria

| 类别 | 验收标准 |
|------|----------|
| 搜索效率 | 每日选题搜索和判断时间从 1—3 小时降至 30—60 分钟 |
| 候选数量 | 每天生成约 30 个候选创作方向 |
| 可执行性 | 管理者每天能选出至少 10 个可执行方向 |
| 推荐质量 | 排名前 15 的候选中至少 60% 具有参考价值 |
| 可解释性 | 每个趋势评分均有原始数据和公式依据 |
| 主流程稳定性 | YouTube 主流程连续稳定运行；重点频道数据新鲜度约 6 小时 |
| 故障隔离 | TikTok / LLM 失败不影响 YouTube 简报生成 |

Stage 1 影子验证结果：Precision@15 = 60%，高价值趋势召回 100%（golden dataset 见 `data/shadow/`）。

# Constraints

- YouTube Data API 默认配额：每日 10,000 单位，`search.list` 每日 100 次——关键词按组合并调度，频道发现优先走 Uploads playlist。
- LLM 结论必须关联原始视频 ID 证据，禁止无证据声称"多个频道都在做"或修改统计数据。
- 所有算法阈值集中在 `config/scoring.yaml`，不得硬编码。
- 单实例部署（Docker Compose 或 systemd），无 Redis / Celery / 向量数据库等重型依赖。
- 完整产品规格与分阶段开发计划见 [MVP Plan](plans/mvp-plan.md)。
