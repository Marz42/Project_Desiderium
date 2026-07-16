---
type: paradigma-manual
title: Paradigma Baseline Validation
description: Baseline validation sequence for Paradigma knowledge quality, deterministic tooling, and release readiness.
tags: [manual, testing, quality, paradigma]
timestamp: 2026-07-05T12:02:00+08:00
paradigma:
  schema_version: "0.1"
  temperature: warm
  lifecycle: evolving
  update_policy: agent-editable
  epistemic_status: confirmed
  retrieval_hints:
    zh:
      - Paradigma 基线校验
      - 校验命令
      - 质量门禁
    en:
      - paradigma baseline
      - validation commands
      - quality gate
  relations:
    related_to:
      - /conventions.md
      - /contracts/repository-contract.md
---

# Purpose

This guide defines the local validation sequence for Paradigma changes. It is **not** a general-purpose testing guide for derived projects — it documents the baseline quality gates that the Paradigma repository itself must pass. Derived projects should write their own testing guide under `manuals/`.

# Preconditions

- Run commands from the repository root.
- Use Python 3.11+ or another Python 3 version compatible with standard-library type syntax used by the tools.
- Set `PYTHONDONTWRITEBYTECODE=1` when running validation if you want to avoid local `__pycache__` files.

# Steps

1. Run strict OKF lint after concept or schema edits.
2. Run link checks after Markdown links, relations, or index entries change.
3. Run index sync in `--check` mode before deciding whether to write generated blocks.
4. Run hot-size checks before ending substantial sessions.
5. Compile Python tools when their implementation changes.

# Verification

Recommended command sequence:

```powershell
python .paradigma/tools/pd-check-all.py
```

Individual tools can also be run separately:

# Rollback

Validation tools should not delete source content. If a generated index update is wrong, fix the source frontmatter or relations and rerun `pd-sync-index.py --write`.

# Troubleshooting

| Symptom | Likely Cause | Action |
|---------|--------------|--------|
| `unknown type` | Schema registry missing the concept type | Add the type to `.paradigma/schemas/paradigma-types.schema.yaml` |
| Timestamp error | Non-ISO frontmatter timestamp | Use `YYYY-MM-DDTHH:mm:ss+08:00` |
| Link check reports a planned relation | The target is intentionally future work | Keep it under `paradigma.relations.planned` |

# Citations

- `.paradigma/tools/pd-lint-okf.py`
- `.paradigma/tools/pd-check-links.py`
- `.paradigma/tools/pd-sync-index.py`
