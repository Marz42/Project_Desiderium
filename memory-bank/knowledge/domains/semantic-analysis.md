---
type: paradigma-domain
title: Semantic Analysis Domain
description: Transcript acquisition with layered fallback and LLM-powered trend naming, explanation, and creative angle generation.
tags: [domain, llm, transcripts, semantic, creative-angles]
timestamp: 2026-07-17T09:09:00+08:00
paradigma:
  schema_version: "0.1"
  temperature: warm
  lifecycle: evolving
  update_policy: agent-editable
  epistemic_status: confirmed
  retrieval_hints:
    zh:
      - 语义分析
      - 字幕
      - 创作方向
      - LLM
    en:
      - semantic analysis
      - transcripts
      - creative angles
      - llm
  symbols:
    - SemanticAnalysis
    - TranscriptService
    - LlmAdapter
    - creative_angles
  relations:
    depends_on:
      - /architecture.md
      - /domains/trend-engine.md
    related_to:
      - /contracts/scheduler-jobs-contract.md
---

# Responsibility

把趋势引擎的数据结果转化为管理者可用的中文语义产物：趋势命名、热门原因、标题翻译和 1—4 个带证据的创作方向。LLM 只处理语言任务，不计算指标。

# Public Interfaces

| Interface | Role | Path |
|-----------|------|------|
| `TranscriptService` | 字幕状态机 pending→success/failed/unavailable；公开字幕 → 可选 ASR → 元数据降级 | `app/services/transcripts.py` |
| `YouTubeCaptionsFetcher` / `AsrAdapter` | 字幕来源适配 | `app/adapters/transcript/` |
| `LlmAdapter` | OpenAI-compatible client，JSON Schema 结构化输出，重试 / 超时 / token 记录 | `app/adapters/llm/` |
| `SemanticAnalysis` | 语义管道编排（翻译、命名、why-trending、角度生成） | `app/services/semantic_analysis.py` |
| `EvidenceValidator` | 校验 `evidence_content_ids` 均存在于 trend members | `app/services/evidence.py` |
| `AngleDedup` | 语义指纹去重（最近 7 天 / 已采用 / blocked） | `app/services/angle_dedup.py` |

# Internal Flow

```text
trend_themes (scored) + transcripts 摘要 + 代表视频元数据
  -> 版本化 prompts (config/prompts/*.yaml)
  -> LlmAdapter (JSON Schema 强约束)
  -> 证据 ID 校验 (不存在则拒绝)
  -> 语义去重 (semantic_fingerprint)
  -> creative_angles (status=candidate, generation_source=llm)
无字幕 -> 元数据-only 分析, 低置信标记
LLM 失败 -> 记录并跳过, 不阻断趋势评分
```

Token 用量与成本估算写入 `llm_usage_logs`（每次调用）。

# Dependencies

- `config/llm.yaml` 与 `config/prompts/`（5 个版本化 prompt 模板）。
- 环境变量 `LLM_API_KEY` / `LLM_BASE_URL` / `LLM_MODEL`（供应商无关）。
- 上游：`trend_discovery` 必须先完成（调度顺序 01:30 → 02:00）。

# Related Contracts

- `contracts/scheduler-jobs-contract.md` — `transcript_fetch`（6h）与 `semantic_analysis`（每日 02:00）任务。
- `contracts/data-model-contract.md` — `transcripts` / `creative_angles` / `llm_usage_logs` 表。

# Known Risks

- LLM 输出不符合 schema 时该趋势当日无语义产物；重试策略有限。
- 语义去重基于指纹与规则，改写措辞的重复方向仍可能漏网。
- prompt 变更缺少自动化回归（golden dataset 回放为手动流程）。
