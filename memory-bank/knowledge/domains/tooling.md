---
type: paradigma-domain
title: Tooling Domain
description: Deterministic tooling layer for OKF lint, link checking, index sync, and runtime maintenance.
tags: [domain, tooling]
timestamp: 2026-07-05T11:45:00+08:00
paradigma:
  schema_version: "0.1"
  temperature: warm
  lifecycle: evolving
  update_policy: agent-editable
  epistemic_status: confirmed
  retrieval_hints:
    zh:
      - 工具
      - lint
      - link check
      - index sync
      - 归档
    en:
      - tooling
      - lint
      - link check
      - index sync
      - archive
  symbols:
    - pd-lint-okf.py
    - pd-check-links.py
    - pd-sync-index.py
    - pd-check-hot-size.py
    - pd-check-all.py
    - pd-archive-task.py
    - pd-compact-progress.py
  relations:
    depends_on:
      - /architecture.md
    constrains:
      - /contracts/repository-contract.md
    related_to:
      - /manuals/paradigma-baseline-test.md
---

# Responsibility

The tooling domain covers the L4 Deterministic Tooling Layer of Paradigma. All tools are self-contained Python standard-library scripts under `.paradigma/tools/`. They validate, generate, and maintain Memory-Bank artifacts without LLM interpretation.

# Public Interfaces

| Tool | Command | Purpose |
|------|---------|---------|
| `pd-check-all.py` | `python .paradigma/tools/pd-check-all.py` | Aggregates lint, link check, index check, hot-size, and DESIGN.md basic validation into a single quality gate |
| `pd-lint-okf.py` | `python .paradigma/tools/pd-lint-okf.py --strict` | Validates concept documents against schema, sections, timestamps, policies, and generated blocks |
| `pd-check-links.py` | `python .paradigma/tools/pd-check-links.py` | Checks Markdown links, frontmatter relations, and generated index entries |
| `pd-sync-index.py` | `python .paradigma/tools/pd-sync-index.py --write` | Scans concepts and generates root/subdirectory index blocks with checksums |
| `pd-check-hot-size.py` | `python .paradigma/tools/pd-check-hot-size.py` | Reports active-task, HOT knowledge, and progress index size status |
| `pd-archive-task.py` | `python .paradigma/tools/pd-archive-task.py --write` | Archives completed active task into session logs and resets active task |
| `pd-compact-progress.py` | `python .paradigma/tools/pd-compact-progress.py --write` | Writes a compact progress summary without deleting source logs |
| `pd-diagnose.py` | `python .paradigma/tools/pd-diagnose.py --upstream <path>` | Compares project harness against upstream; reports gaps in structure/tools/schema/config/protocol |

# Internal Flow

All tools share a common root resolution pattern (`Path(__file__).resolve().parents[2]`) and operate on the repository root. They read from `.paradigma/config.yaml` and `.paradigma/schemas/paradigma-types.schema.yaml` for configuration and type validation rules. Dry-run (no `--write`) is the default for mutation tools.

# Dependencies

- Python 3.11+ standard library (no third-party packages).
- `.paradigma/config.yaml` for knowledge roots, reserved filenames, and generated block markers.
- `.paradigma/schemas/paradigma-types.schema.yaml` for type registry, required sections, and field validation.
- `memory-bank-template/` for active-task reset template.

# Related Contracts

- `memory-bank/knowledge/contracts/repository-contract.md` — defines tool command contracts and exit codes.

# Known Risks

- Tools parse YAML frontmatter heuristically (not via a full YAML library); edge cases with complex YAML values may cause false negatives in lint.
- Adding a new tool requires manually updating this document, the repository contract, and the testing guide.
- `pd-archive-task.py` resets `active-task.md` from the template on write; an interrupted write could lose active-task content if the original was not committed.
