# Decisions Index

* [ADR-001 Split Template Source and Runtime Memory](adr-001-template-runtime-split.md) - Separates blank templates from runtime memory.
* [ADR-002 Adopt OKF-Compatible Memory Runtime Structure](adr-002-okf-compatible-memory-runtime.md) - Adopts runtime/logs/knowledge and OKF-compatible knowledge.

<!-- BEGIN PARADIGMA AUTO-INDEX -->
<!-- checksum: aa4824d6a2f0b124 -->
<!-- generated_by: pd-sync-index.py -->

| Path | Type | Title | Hints | Symbols | Relations |
|------|------|-------|-------|---------|-----------|
| [adr-001-template-runtime-split.md](adr-001-template-runtime-split.md) | `paradigma-decision` | ADR-001 Split Template Source and Runtime Memory | 模板拆分<br>运行记忆<br>初始化流程 ... | - | superseded_by:/decisions/adr-002-okf-compatible-memory-runtime.md |
| [adr-002-okf-compatible-memory-runtime.md](adr-002-okf-compatible-memory-runtime.md) | `paradigma-decision` | ADR-002 Adopt OKF-Compatible Memory Runtime Structure | OKF 迁移<br>runtime logs knowledge<br>三态结构 ... | - | constrains:/architecture.md<br>constrains:/contracts/repository-contract.md |
| [adr-003-strict-okf-production-rules.md](adr-003-strict-okf-production-rules.md) | `paradigma-decision` | ADR-003 Adopt Strict OKF Production Rules | strict lint<br>link check<br>index checksum ... | - | constrains:/architecture.md<br>constrains:/contracts/repository-contract.md<br>follows:/decisions/adr-002-okf-compatible-memory-runtime.md |

<!-- END PARADIGMA AUTO-INDEX -->
