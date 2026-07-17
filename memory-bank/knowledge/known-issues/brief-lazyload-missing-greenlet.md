---
type: paradigma-known-issue
title: Fresh Brief Row Triggers MissingGreenlet on First Read
description: BriefRepository.get_or_create returned a freshly-flushed Brief whose items relationship had never been loaded, so the first attribute access under AsyncSession raised sqlalchemy.exc.MissingGreenlet.
tags: [known-issue, brief, sqlalchemy, asyncio, orm]
timestamp: 2026-07-17T12:50:00+08:00
paradigma:
  schema_version: "0.1"
  temperature: cold
  lifecycle: evolving
  update_policy: agent-editable
  epistemic_status: confirmed
  retrieval_hints:
    zh:
      - MissingGreenlet
      - 懒加载
      - 简报
      - 异步会话
    en:
      - MissingGreenlet
      - lazy load
      - brief
      - async session
  relations:
    related_to:
      - /domains/admin-web.md
      - /contracts/data-model-contract.md
---

# Symptom

首次对某个从未创建过 `Brief` 行的 `brief_date`调用 `GET /brief`（或直接调用 `BriefExportService.get_preview_data` / `render_markdown` / `finalize_brief`）时，若该请求恰好命中"当天首次访问、`briefs` 表尚无该日期记录"的路径，会抛出：

```text
sqlalchemy.exc.MissingGreenlet: greenlet_spawn has not been called; can't call await_only() here.
```

# Impact

- 任何全新日期的简报首次预览/导出/固化都会 500，而不是返回空简报；只有在同一进程内该日期已被访问过一次（例如同步过）之后才会"看起来正常"，因此本地手测容易漏掉。
- G4 为 brief 补齐只读 GET + 显式 sync/finalize 的集成测试时首次复现（`tests/integration/test_brief_workflow.py`）。

# Root Cause

`BriefRepository.get_or_create` 在没有既存行时构造 `Brief(...)`（未显式传 `items`），`session.add()` 后立刻 `await session.flush()`。flush 会让该实例从 transient 变为 persistent（获得数据库身份），但 `items` 集合此前从未被访问过、也未被 `flush()` 主动填充为"已加载"状态。调用方随后访问 `brief.items`（`get_preview_data` 中的 `for item in sorted(brief.items, ...)`）触发 SQLAlchemy 的懒加载策略，该策略需要发出一条 `SELECT ... WHERE brief_id = ...` 查询；但这次属性访问是在纯 Python 同步代码路径中发生的，并未处于 `greenlet_spawn` 上下文内，因此 `AsyncSession` 无法安全地同步等待这次隐式 IO，直接抛出 `MissingGreenlet`。

# Workaround

无（此前唯一的规避方式是先手动 `POST /brief/sync` 一次，让 `Brief` 行连带 `items` 一起被创建/加载，之后同日期的 GET 才不会踩到"从未加载过集合"的分支）。

# Permanent Fix

- `BriefRepository.get_or_create` 在构造新 `Brief` 时显式传入 `items=[]`。因为集合在对象仍是 transient 状态时就被赋值为空列表，SQLAlchemy 会把该集合标记为"已加载"，flush 之后不会再触发懒加载查询。
- `tests/integration/test_brief_workflow.py::test_get_preview_never_syncs_or_persists_a_brief_row` 覆盖"全新日期首次 GET"路径，防止回归。

# Related Documents

- `app/repositories/briefs.py`
- `app/services/brief_export.py`
- `tests/integration/test_brief_workflow.py`
- `memory-bank/knowledge/domains/admin-web.md`

# Status

**Resolved — 0.9.0（待发布）**（2026-07-17 12:50，`items=[]` 修复并配合集成测试实测通过）。
