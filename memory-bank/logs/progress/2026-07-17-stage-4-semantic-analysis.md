# Stage 4 — Subtitle & LLM Semantic Analysis

**Date:** 2026-07-17 01:56  
**Stage:** 4  
**Status:** completed

## Summary

Built the LLM-powered semantic layer on top of Stage 3 trend scoring:

- **Transcript service** (`app/services/transcripts.py`): state machine `pending → success | failed | unavailable`; public caption fetch via `YouTubeCaptionsFetcher`; optional `AsrAdapter` interface; metadata-only excerpt fallback; length limits and in-memory excerpt cache.
- **LLM adapter** (`app/adapters/llm/`): OpenAI-compatible client; JSON Schema structured output; retry/timeout; token usage tracking; versioned prompts in `config/prompts/`.
- **Semantic pipeline** (`app/services/semantic_analysis.py`): title translation, trend naming, why-trending summary, 1–4 creative angles per trend with Short/Long/Both format; evidence ID validation; semantic angle dedup; low-confidence metadata fallback when no captions.
- **Jobs**: `fetch_priority_transcripts` (6h interval), `run_semantic_analysis` (daily 02:00, after trend discovery).
- **Config**: `config/llm.yaml`, five prompt templates under `config/prompts/`.

## Key files

| Area | Path |
|------|------|
| Transcript adapters | `app/adapters/transcript/` |
| LLM adapter | `app/adapters/llm/` |
| Transcript service | `app/services/transcripts.py` |
| Semantic pipeline | `app/services/semantic_analysis.py` |
| Evidence validation | `app/services/evidence.py` |
| Angle dedup | `app/services/angle_dedup.py` |
| Repositories | `app/repositories/transcripts.py`, `creative_angles.py` |
| Jobs | `app/jobs/transcript_tasks.py`, `semantic_tasks.py` |
| Tests | `tests/unit/test_evidence.py`, `test_angle_dedup.py`, `test_llm_adapter.py`, `test_transcripts.py`, `test_semantic_analysis.py` |

## Verification

- `python -m pytest tests/unit/ -q` → 43 passed
- LLM failures isolated in semantic job; trend scoring pipeline unchanged

## Design constraints upheld

- LLM does not compute scores or modify raw metrics
- All angles require valid `evidence_content_ids` from trend members
- No captions → metadata-only analysis with low confidence flag
