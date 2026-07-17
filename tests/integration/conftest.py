"""Integration test fixtures.

pytest-asyncio creates a fresh event loop per test function (see
``asyncio_default_fixture_loop_scope = "function"``). The async SQLAlchemy
engine is cached at module scope in ``app.db``, so pooled asyncpg
connections opened during one test's event loop become unusable once that
loop closes. Disposing the engine after every test forces a fresh pool
bound to the next test's loop.
"""

from __future__ import annotations

import pytest

from app.db import dispose_engine


@pytest.fixture(autouse=True)
async def _dispose_engine_between_tests():
    yield
    await dispose_engine()
