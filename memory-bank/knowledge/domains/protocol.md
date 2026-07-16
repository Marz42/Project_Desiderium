---
type: paradigma-domain
title: Protocol Domain
description: Agent Runtime Protocol sources, IDE adapters, bootstrap prompts, and protocol synchronization rules.
tags: [domain, protocol, agent]
timestamp: 2026-07-05T11:45:00+08:00
paradigma:
  schema_version: "0.1"
  temperature: warm
  lifecycle: evolving
  update_policy: agent-editable
  epistemic_status: confirmed
  retrieval_hints:
    zh:
      - 协议
      - Agent
      - 规则
      - 适配器
    en:
      - protocol
      - Agent rules
      - adapter
      - bootstrap
  symbols:
    - AGENT_RULES.md
    - INIT_PROMPT.md
    - memory-bank-protocol.mdc
  relations:
    depends_on:
      - /architecture.md
    related_to:
      - /contracts/repository-contract.md
---

# Responsibility

The protocol domain covers L3 Runtime Protocol Layer sources and IDE adapters. It defines how agents read, update, archive, and validate Memory-Bank across sessions, and ensures the protocol is IDE-agnostic at source with IDE-specific adapters as synchronized derivatives.

# Public Interfaces

| Artifact | Role | Update Rule |
|----------|------|-------------|
| `AGENT_RULES.md` | IDE-agnostic protocol source of truth | Master; all changes start here |
| `.cursor/rules/memory-bank-protocol.mdc` | Cursor-specific always-on rule adapter | Must be synced after `AGENT_RULES.md` changes |
| `INIT_PROMPT.md` | Copyable conversation starters for new projects | Updated when bootstrap flow changes |
| `README.md` | User-facing setup and maintenance docs | Updated for new capabilities and bootstrap commands |

# Internal Flow

Protocol changes follow a single-source pattern:

```text
AGENT_RULES.md (source) → .cursor/rules/memory-bank-protocol.mdc (adapter)
AGENT_RULES.md → INIT_PROMPT.md (user prompts)
AGENT_RULES.md → README.md (user docs)
```

The Read Phase, Update Phase, timestamp convention, HOT/WARM/COLD routing, and tooling commands are all defined in `AGENT_RULES.md` and propagated to adapters and user docs.

# Dependencies

- `architecture.md` for directory structure and module boundaries.
- `.paradigma/config.yaml` for knowledge/logs/runtime root paths.
- `.paradigma/tools/` for Update Phase validation commands.

# Related Contracts

- `memory-bank/knowledge/contracts/repository-contract.md` — the protocol enforces the contract's tool commands and update policies.

# Known Risks

- Manual protocol changes that skip adapter synchronization create drift between `AGENT_RULES.md` and `.cursor/rules/memory-bank-protocol.mdc`.
- Adding new protocol phases (e.g., a Review Phase) requires updating at least 4 files and the template directory.
- The protocol assumes single-Agent sessions; multi-Agent task routing is noted as future work in the RFC.
