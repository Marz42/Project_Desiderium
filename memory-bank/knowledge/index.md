# Paradigma Knowledge Index

Agent 路由指南：先读取 runtime active task，再读取本 index，根据任务选择最相关的 1-3 个文档继续阅读。One-shot retrieval 是第一跳，不是终点。

## HOT Knowledge

* [Project Brief](project-brief.md) - Project vision, target users, and scope.
* [System Architecture](architecture.md) - Repository structure and protocol boundaries.
* [Conventions](conventions.md) - Coding, versioning, and collaboration conventions.
* [Repository Contract](contracts/repository-contract.md) - Repository-level contract boundaries.

## WARM Knowledge

* [Contracts](contracts/) - API, repository, and tooling contracts.
* [Domains](domains/) - Module-level design documents.
* [Manuals](manuals/) - Operational guides.

## COLD Knowledge

* [Decisions](decisions/) - Architecture decision records.
* [Known Issues](known-issues/) - Debugging notes and recurring issues.

<!-- BEGIN PARADIGMA AUTO-INDEX -->
<!-- checksum: d73cd8a106f5fa61 -->
<!-- generated_by: pd-sync-index.py -->

| Path | Type | Title | Hints | Symbols | Relations |
|------|------|-------|-------|---------|-----------|
| [architecture.md](architecture.md) | `paradigma-architecture` | System Architecture | 总体架构<br>三态记忆结构<br>工具链边界 ... | AGENT_RULES.md<br>memory-bank/runtime<br>memory-bank/knowledge | related_to:/contracts/repository-contract.md<br>related_to:/decisions/adr-002-okf-compatible-memory-runtime.md |
| [contracts/repository-contract.md](contracts/repository-contract.md) | `paradigma-contract` | Repository Contract | 仓库契约<br>工具命令<br>兼容策略 ... | pd-lint-okf.py<br>pd-sync-index.py<br>VERSION | depends_on:/architecture.md |
| [conventions.md](conventions.md) | `paradigma-convention` | Coding and Collaboration Conventions | 代码规范<br>版本规则<br>文档约定 ... | SemVer<br>VERSION<br>Update Phase | constrains:/contracts/repository-contract.md<br>constrains:/manuals/paradigma-baseline-test.md |
| [decisions/adr-001-template-runtime-split.md](decisions/adr-001-template-runtime-split.md) | `paradigma-decision` | ADR-001 Split Template Source and Runtime Memory | 模板拆分<br>运行记忆<br>初始化流程 ... | - | superseded_by:/decisions/adr-002-okf-compatible-memory-runtime.md |
| [decisions/adr-002-okf-compatible-memory-runtime.md](decisions/adr-002-okf-compatible-memory-runtime.md) | `paradigma-decision` | ADR-002 Adopt OKF-Compatible Memory Runtime Structure | OKF 迁移<br>runtime logs knowledge<br>三态结构 ... | - | constrains:/architecture.md<br>constrains:/contracts/repository-contract.md |
| [decisions/adr-003-strict-okf-production-rules.md](decisions/adr-003-strict-okf-production-rules.md) | `paradigma-decision` | ADR-003 Adopt Strict OKF Production Rules | strict lint<br>link check<br>index checksum ... | - | constrains:/architecture.md<br>constrains:/contracts/repository-contract.md<br>follows:/decisions/adr-002-okf-compatible-memory-runtime.md |
| [domains/design-system.md](domains/design-system.md) | `paradigma-domain` | Design System Domain | 设计系统<br>视觉规范<br>前端设计 ... | DESIGN.md<br>design.md<br>design-system | depends_on:/architecture.md<br>related_to:/contracts/repository-contract.md<br>related_to:/manuals/paradigma-design-wizard.md |
| [domains/migration-flows.md](domains/migration-flows.md) | `paradigma-domain` | Paradigma Migration Flows | 迁移流程<br>升级路径<br>结构迁移 ... | pd-diagnose.py<br>paradigma_harness_version<br>INIT_PROMPT mode H ... | related_to:/manuals/paradigma-harness-update.md<br>related_to:/manuals/paradigma-baseline-test.md<br>related_to:/contracts/repository-contract.md |
| [domains/plans.md](domains/plans.md) | `paradigma-domain` | Plans Domain | 计划<br>中期规划<br>实施路径 ... | paradigma-plan<br>knowledge/plans | depends_on:/architecture.md<br>depends_on:/domains/protocol.md<br>related_to:/contracts/repository-contract.md |
| [domains/protocol.md](domains/protocol.md) | `paradigma-domain` | Protocol Domain | 协议<br>Agent<br>规则 ... | AGENT_RULES.md<br>INIT_PROMPT.md<br>memory-bank-protocol.mdc | depends_on:/architecture.md<br>related_to:/contracts/repository-contract.md |
| [domains/tooling.md](domains/tooling.md) | `paradigma-domain` | Tooling Domain | 工具<br>lint<br>link check ... | pd-lint-okf.py<br>pd-check-links.py<br>pd-sync-index.py ... | depends_on:/architecture.md<br>constrains:/contracts/repository-contract.md<br>related_to:/manuals/paradigma-baseline-test.md |
| [glossary.md](glossary.md) | `paradigma-glossary` | Project Glossary | 术语<br>缩写<br>OKF ... | OKF<br>Memory-Bank | related_to:/project-brief.md |
| [known-issues/fstring-escape-in-compact.md](known-issues/fstring-escape-in-compact.md) | `paradigma-known-issue` | f-string backslash escape in pd-compact-progress.py | f-string<br>转义<br>语法错误 ... | - | related_to:/domains/tooling.md |
| [known-issues/session-context-fragmentation.md](known-issues/session-context-fragmentation.md) | `paradigma-known-issue` | Session Context Fragmentation Between Active Tasks | 会话上下文断裂<br>任务切换<br>handoff ... | - | related_to:/domains/protocol.md<br>related_to:/domains/plans.md<br>related_to:/decisions/adr-002-okf-compatible-memory-runtime.md |
| [known-issues/stale-section-structure-in-adr001.md](known-issues/stale-section-structure-in-adr001.md) | `paradigma-known-issue` | Stale section structure in ADR-001 and manuals after OKF hardening | schema registry<br>section<br>结构 ... | - | related_to:/decisions/adr-003-strict-okf-production-rules.md<br>related_to:/domains/tooling.md |
| [manuals/paradigma-baseline-test.md](manuals/paradigma-baseline-test.md) | `paradigma-manual` | Paradigma Baseline Validation | Paradigma 基线校验<br>校验命令<br>质量门禁 ... | - | related_to:/conventions.md<br>related_to:/contracts/repository-contract.md |
| [manuals/paradigma-deploy.md](manuals/paradigma-deploy.md) | `paradigma-manual` | Paradigma Release Preparation | Paradigma 发布<br>部署前校验<br>运维 ... | - | related_to:/architecture.md |
| [manuals/paradigma-design-wizard.md](manuals/paradigma-design-wizard.md) | `paradigma-manual` | Paradigma Design Wizard | 设计器<br>设计向导<br>视觉设计 ... | INIT_PROMPT<br>mode G<br>DESIGN.md | related_to:/domains/design-system.md<br>related_to:/manuals/paradigma-baseline-test.md |
| [manuals/paradigma-harness-update.md](manuals/paradigma-harness-update.md) | `paradigma-manual` | Paradigma Harness Update | 套件更新<br>结构迁移<br>诊断 ... | pd-diagnose.py<br>paradigma_harness_version<br>INIT_PROMPT mode H | related_to:/domains/design-system.md<br>related_to:/manuals/paradigma-design-wizard.md<br>related_to:/manuals/paradigma-baseline-test.md |
| [plans/pd-next-milestones.md](plans/pd-next-milestones.md) | `paradigma-plan` | Paradigma v0.5.0 Roadmap & Known Gaps | 路线图<br>里程碑<br>下一个迭代 ... | - | related_to:/known-issues/session-context-fragmentation.md<br>related_to:/architecture.md<br>related_to:/domains/protocol.md |
| [project-brief.md](project-brief.md) | `paradigma-project-brief` | Project Brief | 项目愿景<br>适用范围<br>Agent 外部记忆 ... | Project Paradigma<br>Memory-Bank<br>OKF | informs:/architecture.md<br>informs:/contracts/repository-contract.md |

<!-- END PARADIGMA AUTO-INDEX -->
