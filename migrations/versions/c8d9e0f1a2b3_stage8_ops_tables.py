"""Stage 8: ops tables, indexes, and LLM usage tracking."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "c8d9e0f1a2b3"
down_revision: Union[str, None] = "b2c3d4e5f6a7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "worker_heartbeats",
        sa.Column("component", sa.String(length=64), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("details", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.PrimaryKeyConstraint("component"),
    )
    op.create_table(
        "api_quota_daily",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column("usage_date", sa.Date(), nullable=False),
        sa.Column("quota_used", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("search_calls", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("quota_limit", sa.Integer(), nullable=True),
        sa.Column("max_search_calls", sa.Integer(), nullable=True),
        sa.Column("exhausted", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("provider", "usage_date", name="uq_api_quota_daily_provider_date"),
    )
    op.create_table(
        "llm_usage_logs",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("job_name", sa.String(length=64), nullable=False),
        sa.Column("prompt_name", sa.String(length=128), nullable=True),
        sa.Column("model", sa.String(length=128), nullable=True),
        sa.Column("prompt_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("completion_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("cost_usd_estimate", sa.Float(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_llm_usage_logs_created_at", "llm_usage_logs", ["created_at"], unique=False)
    op.create_index("ix_llm_usage_logs_job_name", "llm_usage_logs", ["job_name"], unique=False)
    op.create_index(
        "ix_metric_snapshots_content_captured",
        "metric_snapshots",
        ["content_item_id", "captured_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_metric_snapshots_content_captured", table_name="metric_snapshots")
    op.drop_index("ix_llm_usage_logs_job_name", table_name="llm_usage_logs")
    op.drop_index("ix_llm_usage_logs_created_at", table_name="llm_usage_logs")
    op.drop_table("llm_usage_logs")
    op.drop_table("api_quota_daily")
    op.drop_table("worker_heartbeats")
