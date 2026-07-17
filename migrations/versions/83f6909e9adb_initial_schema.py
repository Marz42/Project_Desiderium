"""initial schema

Revision ID: 83f6909e9adb
Revises:
Create Date: 2026-07-17 01:30:54.663859

"""

from typing import Sequence, Union

from alembic import op

from app import models  # noqa: F401
from app.db import Base

# revision identifiers, used by Alembic.
revision: str = "83f6909e9adb"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Tables owned by later revisions. Base.metadata reflects the *current* models,
# so create_all must exclude them or later revisions fail with duplicate objects
# on a fresh database (see known-issue fresh-database-migration-fails).
LATER_REVISION_TABLES = {
    "trend_score_snapshots",  # a1b2c3d4e5f6
    "angle_status_audits",  # b2c3d4e5f6a7
    "worker_heartbeats",  # c8d9e0f1a2b3
    "api_quota_daily",  # c8d9e0f1a2b3
    "llm_usage_logs",  # c8d9e0f1a2b3
}


def _initial_tables():
    return [
        table
        for table in Base.metadata.sorted_tables
        if table.name not in LATER_REVISION_TABLES
    ]


def upgrade() -> None:
    bind = op.get_bind()
    Base.metadata.create_all(bind, tables=_initial_tables())


def downgrade() -> None:
    bind = op.get_bind()
    Base.metadata.drop_all(bind, tables=_initial_tables())
