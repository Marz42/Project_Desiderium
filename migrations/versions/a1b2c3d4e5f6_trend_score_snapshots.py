"""Stage 3: trend_score_snapshots table."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "83f6909e9adb"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "trend_score_snapshots",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("trend_id", sa.UUID(), nullable=False),
        sa.Column("snapshot_date", sa.Date(), nullable=False),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("score_components", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "lifecycle_status",
            # The enum already exists (created by the initial revision via
            # trend_themes); postgresql.ENUM honors create_type=False, plain
            # sa.Enum silently ignores it and re-emits CREATE TYPE.
            postgresql.ENUM(
                "new",
                "rising",
                "stable",
                "declining",
                "reviving",
                "dormant",
                name="lifecycle_status",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("member_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("channel_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["trend_id"], ["trend_themes.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "trend_id", "snapshot_date", name="uq_trend_score_snapshots_trend_date"
        ),
    )
    op.create_index(
        "ix_trend_score_snapshots_snapshot_date",
        "trend_score_snapshots",
        ["snapshot_date"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_trend_score_snapshots_snapshot_date", table_name="trend_score_snapshots")
    op.drop_table("trend_score_snapshots")
