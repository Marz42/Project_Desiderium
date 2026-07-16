---
type: paradigma-convention
title: Coding and Collaboration Conventions
description: Coding, naming, testing, documentation, versioning, and prohibited patterns for Project Paradigma.
tags: [conventions, semver, collaboration, tooling]
timestamp: 2026-07-04T22:50:00+08:00
paradigma:
  schema_version: "0.1"
  temperature: hot
  lifecycle: stable
  update_policy: requires-human-confirmation
  epistemic_status: confirmed
  retrieval_hints:
    zh:
      - 代码规范
      - 版本规则
      - 文档约定
      - 工具校验
    en:
      - coding conventions
      - versioning
      - documentation
      - tooling
  symbols:
    - SemVer
    - VERSION
    - Update Phase
  relations:
    constrains:
      - /contracts/repository-contract.md
      - /manuals/paradigma-baseline-test.md
---

# Naming

| Target | Rule | Example |
|--------|------|---------|
| Files and directories | kebab-case, except established tool names | `pd-lint-okf.py`, `memory-bank` |
| Python functions/variables | snake_case | `parse_frontmatter` |
| Python classes | PascalCase | `LintIssue` |
| Constants | UPPER_SNAKE_CASE | `RESERVED_FILENAMES` |
| Markdown concept type | stable kebab-like string | `paradigma-contract` |

Avoid pinyin, ambiguous abbreviations, and generic names such as `data`, `info`, or `temp` unless scoped to a tiny local context.

# Code Style

- Prefer standard-library Python for Paradigma MVP tools.
- Keep tools single-purpose: lint, link check, index sync, hot-size check, archive, compact.
- Keep parsing conservative and deterministic. Do not rely on LLM interpretation for generated indexes or validation results.
- Avoid premature abstractions until duplicated logic proves stable across at least three tools.
- Use comments only when they explain why a rule exists or why a parser is intentionally limited.

# Error Handling

- Tool failures should use non-zero exit codes when they produce ERROR-level findings.
- WARNING-level findings should be visible but should not fail `warn` mode.
- CLI output should include repository-relative paths.
- Generated files should be updated only when the user passes an explicit write flag or archive/compact command.

# Testing Conventions

- Run `python .paradigma/tools/pd-check-all.py` after knowledge/RFC edits (aggregates lint, links, index, hot-size).
- Run `python .paradigma/tools/pd-sync-index.py --write` after adding/removing concept documents.
- Run `python .paradigma/tools/pd-check-hot-size.py` before ending substantial sessions.
- Compile Python tools with `python -m py_compile` when tool code changes, then remove or ignore `__pycache__` outputs.

# Documentation Conventions

- `AGENT_RULES.md` is the source of truth for Agent protocol.
- `.cursor/rules/memory-bank-protocol.mdc` is a synchronized Cursor adapter.
- `README.md` explains user-facing setup and maintenance workflows.
- `INIT_PROMPT.md` contains copyable conversation starters.
- `docs/rfc/*.md` stores proposal documents and must remain OKF-compatible.
- Long-lived knowledge belongs in `memory-bank/knowledge/`; runtime state belongs in `memory-bank/runtime/`; process logs belong in `memory-bank/logs/`.

## Versioning

Project Paradigma follows SemVer using the root `VERSION` file as the source of truth.

| Change type | Version action |
|-------------|----------------|
| Typo or wording only | May skip version bump |
| Template path, protocol, or tooling behavior change | PATCH or MINOR depending on scope |
| New workflow/tooling capability | MINOR |
| Breaking protocol/path change for derived projects | MAJOR proposal, requires user confirmation |

When bumping versions, update:

1. `VERSION`
2. `memory-bank/logs/changelog.md`
3. A progress session in `memory-bank/logs/progress/`
4. ADR when the change is architectural

## Document Size Limits

HOT 文档（`project-brief.md`、`architecture.md`、`conventions.md`、`repository-contract.md`）每次会话都会被完整读入 Agent 上下文。为控制 token 消耗，应遵守以下阈值：

| 文档类型 | WARN | ERROR | 超出后操作 |
|----------|------|-------|-----------|
| HOT knowledge 文档 | 260 行 | 420 行 | 拆分 |
| `active-task.md` | 160 行 | 260 行 | 归档 |
| Progress index | 160 行 | 260 行 | 压缩 |

### architecture.md 拆分策略

当 `architecture.md` 超过 260 行时，按模块拆分为核心 + 细节：

```text
architecture.md                   ← HOT, 核心骨架 (~100–150 行)
  保留: Overview, Technology Stack, Module Boundaries, Key Constraints,
        Open Questions, Citations
  移出: 每模块的技术选型理由、数据流细节、trade-off 讨论

domains/architecture/             ← WARM, 模块级架构细节
├── payment-architecture.md
├── auth-architecture.md
└── frontend-architecture.md
```

拆分后，`architecture.md` 的 Module Boundaries 表应包含指向细节文档的路径：

```markdown
| Module | Responsibility | Architecture Detail |
|--------|----------------|---------------------|
| Payment | 支付回调与订单生命周期 | domains/architecture/payment-architecture.md |
```

### contracts/ 拆分策略

当单个 `paradigma-contract` 文档超过 200 行时，按 `contract_kind` 拆分为独立业务域文件：

```text
contracts/
├── index.md                     ← auto-generated
├── repository-contract.md       ← HOT, Paradigma 专用
├── api/                         ← contract_kind: api
│   ├── payment-api.md
│   └── auth-api.md
├── database/                    ← contract_kind: database
│   ├── user-schema.md
│   └── order-schema.md
└── events/                      ← contract_kind: event
    └── order-events.md
```

每个拆分文件保持独立的 OKF frontmatter（独立的 hints/symbols/relations），让 Agent 通过 index 精确路由到相关 contract，避免一次性加载所有 contract。

### 拆分原则

- **按业务域拆分**：同一业务域的 API + DB + Events 放在不同子目录。
- **保持独立可读性**：每个拆分文件应包含完整的 context（Scope / Contract / Schema / Compatibility），Agent 不需要读原文件即可理解。
- **temperature 差异化**：频繁变动的 contract 设为 `warm`，基础设施级 contract 保留 `hot`。
- **拆分后更新 relations**：拆分出的子文件应在 `depends_on` 中引用 `architecture.md`，原文件涉及的跨文档关系应在子文件中重新声明。

# Prohibited Patterns

- Do not write long-lived facts into `memory-bank/runtime/active-task.md`.
- Do not manually edit generated index blocks.
- Do not add new concept documents without OKF frontmatter.
- Do not change contracts, architecture, or accepted ADRs without checking update policy.
- Do not keep legacy flat Memory-Bank paths in active protocol docs.
- Do not introduce external dependencies into tooling without explicit justification.
