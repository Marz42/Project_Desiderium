# Active Task: Stage 0 — Engineering Baseline

**Plan:** knowledge/plans/mvp-plan.md (Section: 阶段0)
**Status:** completed
**Started:** 2026-07-17
**Completed:** 2026-07-17
**Cursor Mode:** auto

## Objective

Establish a runnable, testable, deployable project skeleton as the foundation for all subsequent stages.

## Required Deliverables (from plan.md Stage 0)

- [x] P0-01: Python project with dependency management
- [x] P0-02: FastAPI application skeleton
- [x] P0-03: PostgreSQL + SQLAlchemy setup
- [x] P0-04: Alembic migrations
- [x] P0-05: Docker Compose (web, worker, postgres)
- [x] P0-06: Config management + .env template
- [x] P0-07: Structured logging
- [x] P0-08: pytest test directory
- [x] P0-09: Adapter + Domain interfaces (SourceAdapter, TranscriptAdapter)
- [x] P0-10: Database task table (crawl_jobs)

## Acceptance Gate

```bash
docker compose up  # all services start
GET /health/live   # 200 OK
GET /health/ready  # 200 OK
```

## Notes

- Stack: Python 3.12, FastAPI, Jinja2+HTMX, PostgreSQL, SQLAlchemy 2 async, Alembic, httpx, Pydantic, pytest, Docker
- Commit: `Stage 0: Engineering baseline`
- Next: Stage 1 shadow validation (see mvp-plan.md)
