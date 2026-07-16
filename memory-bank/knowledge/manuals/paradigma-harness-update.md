---
type: paradigma-manual
title: Paradigma Harness Update
description: Guide for checking and updating Paradigma Harness (tools, protocol, schema, templates) in derived projects.
tags: [manual, harness, update, migration, paradigma]
timestamp: 2026-07-08T15:47:00+08:00
paradigma:
  schema_version: "0.1"
  temperature: cold
  lifecycle: evolving
  update_policy: agent-editable
  epistemic_status: confirmed
  retrieval_hints:
    zh:
      - 套件更新
      - 结构迁移
      - 诊断
      - 模式 H
      - pd-diagnose
    en:
      - harness update
      - structure migration
      - diagnose
      - mode H
      - pd-diagnose
  symbols:
    - pd-diagnose.py
    - paradigma_harness_version
    - INIT_PROMPT mode H
  relations:
    related_to:
      - /domains/design-system.md
      - /manuals/paradigma-design-wizard.md
      - /manuals/paradigma-baseline-test.md
---

# Purpose

This manual guides users through checking and updating the Paradigma Harness (tool chain, protocol files, schema, templates) in derived projects. The Harness is the set of infrastructure that makes Paradigma work — tools, rules, and knowledge structure — and it evolves across Paradigma releases.

There are two upgrade paths depending on the project's current state:

| Path | Current State | Paradigma Version | Process |
|------|--------------|-------------------|---------|
| A: Structure Migration | `memory_bank/` (underscore) or `memory-bank/` flat (no runtime/logs/knowledge) | pre-0.3.0 | Agent-guided migration via INIT_PROMPT mode H |
| B: Version Upgrade | `memory-bank/runtime|logs|knowledge` three-state | 0.3.0+ | Manual protocol review + automatic tool/schema copy |

# Preconditions

- Python 3.11+ available.
- Local copy of Paradigma latest source (e.g., `D:\Repos\paradigma`).
- The project was initialized from a Paradigma template.

# Steps

## 1. Run Diagnosis

```bash
python .paradigma/tools/pd-diagnose.py --upstream <paradigma源路径>
```

This produces a gap report across five dimensions: structure, tools, schema, config, and protocol.

If `pd-diagnose.py` is not yet available in the project, copy it from upstream first:
```bash
cp <paradigma源>/.paradigma/tools/pd-diagnose.py .paradigma/tools/
```

For CI/automation, use `--check-version` for a quick pass/fail check:
```bash
python .paradigma/tools/pd-diagnose.py --upstream <paradigma源> --check-version
# Exit 0 = version matches, 1 = update needed
```

## 2. Choose Upgrade Path

### Path A: Structure Migration (pre-OKF → OKF)

**Trigger**: Diagnose shows "pre-0.2.0" or "0.2.x (flat memory-bank/)" with many structure errors.

1. Use INIT_PROMPT mode H to guide the Agent through migration.
2. The Agent handles:
   - Directory creation (`memory-bank/runtime|logs|knowledge`)
   - File movement and OKF frontmatter addition
   - Breaking down flat `progress.md` into individual session logs
   - Splitting `decisions.md` into individual ADR files
3. Infrastructure files (tools, schema, templates) are copied from upstream.
4. The Agent does NOT automatically overwrite customized protocol files — it backs them up first.
5. After migration, run `pd-check-all.py` to verify.

### Path B: Version Upgrade (OKF → newer OKF)

**Trigger**: Diagnose shows "0.3.0+" or a specific version number, with only tool/schema/config gaps.

1. **Tools**: Copy all `.py` files from `<upstream>/.paradigma/tools/` to your project. Paradigma tools are designed to be drop-in replacements — derived projects rarely customize them.

2. **Schema**: Copy all `.yaml` files from `<upstream>/.paradigma/schemas/`. New types are backward-compatible.

3. **Config**: Merge new keys from upstream `config.yaml`. Never blindly overwrite — your `paradigma_harness_version` field and any custom keys must be preserved.

4. **Protocol**: Review differences manually.
   ```bash
   diff AGENT_RULES.md <upstream>/AGENT_RULES.md
   diff INIT_PROMPT.md <upstream>/INIT_PROMPT.md
   ```
   Protocol files are commonly customized for project-specific needs. NEVER auto-overwrite them. Apply upstream changes selectively.

## 3. Update Version Tracking

Edit `.paradigma/config.yaml`:
```yaml
paradigma_harness_version: "<new_version>"
```

## 4. Validate

```bash
python .paradigma/tools/pd-sync-index.py --write
python .paradigma/tools/pd-check-all.py
```

# Verification

- `pd-diagnose.py --upstream <upstream>` shows no gaps (exit 0).
- `pd-check-all.py` all checks pass.
- Agent reads new protocol files correctly in the next session.

# Rollback

| Scenario | Action |
|----------|--------|
| Migration broke something | `git revert` the migration commit |
| Protocol files lost customizations | Restore from `.bak` backup created by Agent |
| Tools don't work after copy | Check Python version (3.11+ required). Verify file permissions. |

# Troubleshooting

| Symptom | Likely Cause | Action |
|---------|--------------|--------|
| `pd-diagnose.py` not found | Tool not in project | Copy from upstream first |
| Diagnose shows "unknown" | Project has no Paradigma traces | Verify `memory-bank/` or `memory_bank/` directory exists |
| Protocol has many diffs but no obvious changes needed | Project heavily customized AGENT_RULES | Cherry-pick only the new sections (checkpoints, DESIGN.md, diagnostics reference) |
| `pd-check-all` fails after migration | Missing OKF frontmatter on migrated files | Re-run mode H Step 7 to add frontmatter |
| Agent can't find files after migration | Index not synced | Run `pd-sync-index.py --write` |

# Citations

- `memory-bank/knowledge/domains/design-system.md`
- `memory-bank/knowledge/contracts/repository-contract.md`
- `INIT_PROMPT.md` — Mode H
