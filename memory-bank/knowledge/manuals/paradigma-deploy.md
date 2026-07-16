---
type: paradigma-manual
title: Paradigma Release Preparation
description: Pre-release validation and deployment notes specific to the Paradigma repository itself.
tags: [manual, deploy, operations, paradigma]
timestamp: 2026-07-05T12:02:00+08:00
paradigma:
  schema_version: "0.1"
  temperature: cold
  lifecycle: evolving
  update_policy: agent-editable
  epistemic_status: confirmed
  retrieval_hints:
    zh:
      - Paradigma 发布
      - 部署前校验
      - 运维
      - 回滚
    en:
      - paradigma release
      - pre-release validation
      - operations
      - rollback
  relations:
    related_to:
      - /architecture.md
---

# Purpose

This manual records Paradigma-specific release preparation steps. It is **not** a general-purpose deploy guide for derived projects — it documents how the Paradigma repository itself reaches a releasable state. Derived projects should write their own deploy manual under `manuals/`.

# Preconditions

- The repository has an initialized `memory-bank/` structure.
- Tooling commands are run from the repository root.
- Production credentials or secrets are never stored in Memory-Bank files.

# Steps

1. Run OKF lint and link checks.
2. Sync indexes after knowledge changes.
3. Update `VERSION`, changelog, ADRs, and progress logs when required.
4. Review generated blocks and untracked files before release.

# Verification

```bash
python .paradigma/tools/pd-check-all.py
```

# Rollback

If a release preparation step produces incorrect generated content, restore the affected generated block by rerunning the relevant tool after fixing the source concept document. Do not rewrite historical changelog entries; add a corrective entry in the next release.

# Troubleshooting

| Symptom | Likely Cause | Action |
|---------|--------------|--------|
| Strict lint fails | Missing frontmatter field or section | Add the required field/section according to schema |
| Link check fails | Moved document or stale relation | Update the link or relation target |
| Index check fails | Concept changed after index generation | Run `pd-sync-index.py --write` |

# Citations

- `memory-bank/knowledge/contracts/repository-contract.md`
- `memory-bank/knowledge/conventions.md`
