# Stage 5 — Admin Backend & Brief Export

**Date:** 2026-07-17 02:02  
**Stage:** 5  
**Status:** completed

## Summary

Built the manager's daily end-to-end web UI with Jinja2 + HTMX + Tailwind CDN:

- **Auth**: single-manager password (`MANAGER_PASSWORD`), signed session cookie, login/logout
- **CSRF**: token in session, form hidden fields + HTMX `X-CSRF-Token` header
- **Today's candidates** (`/candidates`): ~30 directions grouped by trend; filters for lifecycle, anime, format, priority channel; selection toggles, notes, status actions
- **Trend detail** (`/trends/{id}`): score timeline, components, member videos, channel distribution, angle history
- **History** (`/history`): browse by date with status filters (selected/adopted/published/reusable/blocked)
- **Brief preview** (`/brief`): sync from selections, reorder, edit notes, Markdown preview; download Markdown/HTML
- **Status machine**: `candidate→selected→adopted→published`, branches to `reusable`/`blocked`; `angle_status_audits` table
- **Candidate generation**: daily snapshot service hooked into semantic analysis pipeline

## Key files

| Area | Path |
|------|------|
| Auth / CSRF / session | `app/web/session.py`, `csrf.py`, `middleware.py`, `deps.py` |
| Routes | `app/web/routes/auth.py`, `candidates.py`, `trends.py`, `history.py`, `brief.py` |
| Services | `app/services/admin_*.py`, `brief_export.py`, `angle_status.py`, `candidate_generation.py` |
| Repositories | `app/repositories/daily_candidates.py`, `briefs.py` |
| Templates | `app/web/templates/candidates/`, `trends/`, `history/`, `brief/`, `export/` |
| Migration | `migrations/versions/b2c3d4e5f6a7_angle_status_audits.py` |
| Tests | `tests/unit/test_angle_status.py`, `test_csrf.py`, `test_session.py` |

## Verification

- `python -m pytest tests/ -q` → 57 passed

## Env

- `MANAGER_PASSWORD` — set in `.env` for production; empty skips auth in development
