# Domains Index

Paradigma internal domain documents covering the tooling, protocol, and memory layers.

* [Tooling Domain](tooling.md) - Deterministic tooling layer for lint, link check, index sync, and runtime maintenance.
* [Protocol Domain](protocol.md) - Agent Runtime Protocol sources, IDE adapters, and bootstrap prompts.

<!-- BEGIN PARADIGMA AUTO-INDEX -->
<!-- checksum: 646ba1489f4fe674 -->
<!-- generated_by: pd-sync-index.py -->

| Path | Type | Title | Hints | Symbols | Relations |
|------|------|-------|-------|---------|-----------|
| [design-system.md](design-system.md) | `paradigma-domain` | Design System Domain | 设计系统<br>视觉规范<br>前端设计 ... | DESIGN.md<br>design.md<br>design-system | depends_on:/architecture.md<br>related_to:/contracts/repository-contract.md<br>related_to:/manuals/paradigma-design-wizard.md |
| [migration-flows.md](migration-flows.md) | `paradigma-domain` | Paradigma Migration Flows | 迁移流程<br>升级路径<br>结构迁移 ... | pd-diagnose.py<br>paradigma_harness_version<br>INIT_PROMPT mode H ... | related_to:/manuals/paradigma-harness-update.md<br>related_to:/manuals/paradigma-baseline-test.md<br>related_to:/contracts/repository-contract.md |
| [plans.md](plans.md) | `paradigma-domain` | Plans Domain | 计划<br>中期规划<br>实施路径 ... | paradigma-plan<br>knowledge/plans | depends_on:/architecture.md<br>depends_on:/domains/protocol.md<br>related_to:/contracts/repository-contract.md |
| [protocol.md](protocol.md) | `paradigma-domain` | Protocol Domain | 协议<br>Agent<br>规则 ... | AGENT_RULES.md<br>INIT_PROMPT.md<br>memory-bank-protocol.mdc | depends_on:/architecture.md<br>related_to:/contracts/repository-contract.md |
| [tooling.md](tooling.md) | `paradigma-domain` | Tooling Domain | 工具<br>lint<br>link check ... | pd-lint-okf.py<br>pd-check-links.py<br>pd-sync-index.py ... | depends_on:/architecture.md<br>constrains:/contracts/repository-contract.md<br>related_to:/manuals/paradigma-baseline-test.md |

<!-- END PARADIGMA AUTO-INDEX -->
