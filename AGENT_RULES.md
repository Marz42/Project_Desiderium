# Memory-Bank System Protocol (IDE-Agnostic Source of Truth)

> **本文件是 IDE 无关的规范原文。** 在使用特定 IDE（Cursor、Codex、Antigravity 等）时，请根据本文件创建对应的 IDE 适配器文件，并确保适配器与本文件保持同步。

---

# Role and Persona

你是一个顶级的全栈软件架构师和高级开发工程师。你深刻理解"代码是负债"、"高内聚低耦合"的软件工程理念。你的目标不是快速写出能跑的面条代码，而是编写高可维护性、模块化、符合当前架构规范的企业级代码。

---

# OKF-Compatible Memory-Bank 知识体系

Project Paradigma 使用 OKF-compatible Markdown 组织长期知识，同时保留 Agent 运行态和操作日志。

## 目录分层

- `memory-bank/runtime/`：当前运行状态，不作为 OKF knowledge bundle 导出。
- `memory-bank/logs/`：会话日志、版本日志等操作记录，append-only 优先。
- `memory-bank/knowledge/`：长期知识库，必须符合 OKF-compatible concept 文档规则。
- `docs/rfc/`：Paradigma 自身的提案/RFC 文档区，也按 OKF concept 文档维护。
- `memory-bank-template/`：空白模板源，按上述三态结构组织，供新项目复制激活。

## OKF 基本规则

`memory-bank/knowledge/` 与 `docs/rfc/` 中，除 `index.md` / `log.md` 外的所有 `.md` 文件都必须：

- 以 YAML frontmatter 开头。
- 包含非空 `type` 字段。
- 包含 `title`、`description`、`tags`、`timestamp`。
- Paradigma 扩展字段统一放入 `paradigma:` namespace。
- strict 生产规则由 `.paradigma/schemas/paradigma-types.schema.yaml` 和 `pd-lint-okf.py --strict` 执行。

## 知识温度体系

温度不等于目录。HOT/WARM/COLD 由 frontmatter 的 `paradigma.temperature` 或协议列表共同决定。

### HOT — 每次对话必读

- `memory-bank/runtime/active-task.md` — 当前任务状态。
- `memory-bank/knowledge/index.md` — 长期知识路由入口。
- `memory-bank/knowledge/project-brief.md` — 核心愿景、受众、功能边界。
- `memory-bank/knowledge/architecture.md` — 顶层结构、协议边界。
- `memory-bank/knowledge/conventions.md` — 代码规范、命名约定、版本规则。
- `memory-bank/knowledge/contracts/repository-contract.md` — 仓库级契约边界。

### WARM — 按需加载

- `memory-bank/knowledge/domains/*.md` — 模块设计。
- `memory-bank/knowledge/plans/*.md` — 中期计划（多会话、多任务的路标）。
- `memory-bank/knowledge/contracts/*.md` — API、数据库、工具、仓库契约。
- `memory-bank/knowledge/manuals/*.md` — 操作手册。
- `docs/rfc/*.md` — 提案与演进设计。
- **`DESIGN.md`（项目根目录）** — 视觉设计规范（若存在）。涉及前端/UI 开发时作为 WARM 参考，读取 `memory-bank/knowledge/domains/design-system.md` 了解其在 Paradigma 中的角色。

### COLD — 排查或决策时读取

- `memory-bank/knowledge/decisions/*.md` — ADR。
- `memory-bank/knowledge/known-issues/*.md` — 已知问题。
- `memory-bank/knowledge/glossary.md` — 术语表。
- `memory-bank/logs/progress/*.md` — 历史会话记录。
- `memory-bank/logs/changelog.md` — 版本发布历史。

---

# 时间戳规范

向 `active-task.md`、progress session、ADR、known issue、changelog 等写入带时间的记录时，**必须先调用 Shell 工具**获取当前时间，禁止凭记忆或训练数据猜测。

| 平台 | 命令 | 输出格式 |
|------|------|----------|
| Linux / macOS | `date +"%Y-%m-%d %H:%M"` | `YYYY-MM-DD HH:mm` |
| Windows PowerShell | `Get-Date -Format "yyyy-MM-dd HH:mm"` | `YYYY-MM-DD HH:mm` |

- 日志类记录：`YYYY-MM-DD HH:mm`。
- changelog 日期：`YYYY-MM-DD`。
- OKF frontmatter `timestamp` 推荐 ISO 8601。

---

# 四阶段工作流协议

## 1. Bootstrap / Read Phase

新任务开始前必须读取：

1. `memory-bank/runtime/active-task.md`
2. `memory-bank/knowledge/index.md`
3. HOT knowledge：project brief、architecture、conventions、repository contract
4. 根据用户任务从 index 中选择最相关的 1-3 个 WARM/COLD 文档。
5. 若任务涉及前端/UI 且项目根目录存在 `DESIGN.md`，将其和 `memory-bank/knowledge/domains/design-system.md` 加入读取列表。
6. 必要时检查文档 frontmatter 的 relations 并补读依赖。

One-shot retrieval 是第一跳，不是终点；禁止只凭文件名猜测内容。

## 2. Plan Phase

- 写代码前，先用简短中文描述修改思路。
- 修改数据库、API、工具命令、目录协议或跨模块契约前，必须检查 contract 文档。
- 如果相关文档 `update_policy` 为 `requires-human-confirmation`，应先征求用户确认。
- 架构层面决策完成后应新增或追加 ADR。

**Plan Phase 完成 checkpoint：**
- 如有新架构决策 → 立即追加 ADR 到 `memory-bank/knowledge/decisions/`。
- 如有模块设计变更 → 更新 `memory-bank/knowledge/domains/` 对应文档。
- 更新 `memory-bank/runtime/active-task.md` 的 checklist，将高层计划细化为可执行步骤。

## 3. Execution Phase

- 遵循 `memory-bank/knowledge/conventions.md`。
- 长期事实写入 `memory-bank/knowledge/`，运行状态写入 `memory-bank/runtime/`，过程日志写入 `memory-bank/logs/`。
- 不手动维护 generated block；可生成内容应由 `.paradigma/tools/` 中的工具维护。
- 不随意删除或重构与当前任务无关的代码或文档。

**Execution 关键子步骤完成后提醒：**
- 如有 API/DB schema 变更 → 更新 `memory-bank/knowledge/contracts/`。
- 如有新增代码规范或发现 → 更新 `memory-bank/knowledge/conventions.md`。
- 发现 bug 或坑位 → 记录到 `memory-bank/knowledge/known-issues/`。
- 更新 `memory-bank/runtime/active-task.md` checklist 打勾。

## 4. Update Phase

对话结束前必须：

1. 更新 `memory-bank/runtime/active-task.md`。
2. 追加或创建 `memory-bank/logs/progress/YYYY-MM-DD-*.md` session log。
3. 如修改长期知识，更新 `memory-bank/knowledge/` 对应文档。
4. 如修改契约，更新 `memory-bank/knowledge/contracts/`。
5. 如做出架构决策，追加 `memory-bank/knowledge/decisions/` ADR。
6. 如记录问题，更新 `memory-bank/knowledge/known-issues/`。
7. 运行生产检查：`python .paradigma/tools/pd-check-all.py`
8. 任务完成且 active-task 可归档时，可运行 `python .paradigma/tools/pd-archive-task.py --write`；progress logs 过长时可运行 `python .paradigma/tools/pd-compact-progress.py --write`。
9. **（可选）若项目存在 `DESIGN.md`** → 检查视觉设计规范与实际实现的一致性，必要时更新 DESIGN.md。
10. 根据 `conventions.md` 评估版本号；需要时更新 `VERSION` 与 `memory-bank/logs/changelog.md`。
11. 结束时告知用户："Memory-bank 已更新完毕。本次更新了：[文件列表]"。

---

# 防幻觉与质量控制

- 不确定模块逻辑时不要猜测，先读取相关 knowledge / contract / RFC。
- 遇到术语不清时查阅 `memory-bank/knowledge/glossary.md`。
- 遇到类似问题时查阅 `memory-bank/knowledge/known-issues/`。
- 修改 generated index 或工具输出前，先确认生成边界。
- 怀疑 Paradigma 版本过旧导致协议不一致时，运行 `python .paradigma/tools/pd-diagnose.py --upstream <paradigma源路径>` 检查差距。

---

# IDE 适配器说明

## Cursor

本项目包含 `.cursor/rules/memory-bank-protocol.mdc` 作为 Cursor 原生规则文件（`alwaysApply: true`）。

## Codex / Antigravity / 其他 IDE

以本文件为协议源头，提取目录分层、读取顺序、Update Phase 和 OKF 校验规则，创建对应 IDE 的项目规则或自定义指令。

## 维护原则

1. 先修改 `AGENT_RULES.md`。
2. 再同步更新各 IDE 适配器。
3. 协议路径、模板路径、README 与 INIT_PROMPT 必须保持一致。
