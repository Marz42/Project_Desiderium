# Active Task: Stage 4 — Subtitle & LLM Semantic Analysis

**Status:** completed | **Started:** 2026-07-17 | **Completed:** 2026-07-17 | **Depends on:** Stage 3 ✓

## Objective
Turn data trends into actionable creative directions for the manager.

## Deliverables

### Subtitle/Transcript (P4-01→07)
- [x] Transcript state machine (pending→success/failed/unavailable)
- [x] Priority channel subtitle extraction (public captions)
- [x] Fallback: no captions → metadata-only
- [x] Optional ASR adapter interface
- [x] Length limits + segment caching
- [x] Failure reason recording

### LLM Adapter (P4-08→15)
- [x] Provider-agnostic interface
- [x] JSON Schema-constrained output
- [x] Retry + timeout
- [x] Token/cost tracking
- [x] Prompt version management
- [x] Evidence content_ids in output
- [x] Output source validation (no hallucinated video IDs)

### Semantic Analysis (P4-16→22)
- [x] English title → Chinese translation
- [x] Trend Chinese naming
- [x] "Why trending" summary
- [x] Creative angle generation (1-4 per trend)
- [x] Short/Long/Both classification
- [x] Historical angle dedup (semantic)
- [x] Low-confidence fallback

## Notes
- LLM API key: LLM_API_KEY in .env (OpenAI-compatible, default gpt-4o-mini)
- LLM must NOT compute scores, only do language/semantic tasks
- All LLM output must reference evidence video IDs
- Prompt templates in config/prompts/
- Semantic analysis runs after trend scoring; LLM failures do not block scoring

## Next
Stage 5: Management UI and brief export
