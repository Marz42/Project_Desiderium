"""G3 clustering tables and trend_members soft-sync columns.

Applies when e5f6a7b8c9d0 was stamped before G3 objects were added to that
revision. Fully idempotent.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "f6a7b8c9d0e1"
down_revision: Union[str, None] = "e5f6a7b8c9d0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    member_columns = {c["name"] for c in inspector.get_columns("trend_members")}
    if "active" not in member_columns:
        op.add_column(
            "trend_members",
            sa.Column("active", sa.Boolean(), nullable=False, server_default="true"),
        )
    if "last_confirmed_at" not in member_columns:
        op.add_column(
            "trend_members",
            sa.Column(
                "last_confirmed_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("now()"),
            ),
        )
    if "deactivated_at" not in member_columns:
        op.add_column(
            "trend_members",
            sa.Column("deactivated_at", sa.DateTime(timezone=True), nullable=True),
        )

    tables = set(inspector.get_table_names())
    if "embedding_cache" not in tables:
        op.create_table(
            "embedding_cache",
            sa.Column("id", sa.UUID(), nullable=False),
            sa.Column("embedding_space", sa.String(length=128), nullable=False),
            sa.Column("provider", sa.String(length=64), nullable=False),
            sa.Column("model_name", sa.String(length=256), nullable=True),
            sa.Column("model_revision", sa.String(length=128), nullable=True),
            sa.Column("input_hash", sa.String(length=64), nullable=False),
            sa.Column("vector", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("now()"),
                nullable=False,
            ),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint(
                "embedding_space",
                "input_hash",
                name="uq_embedding_cache_space_input",
            ),
        )
    if "trend_facets" not in tables:
        op.create_table(
            "trend_facets",
            sa.Column("id", sa.UUID(), nullable=False),
            sa.Column("trend_id", sa.UUID(), nullable=False),
            sa.Column("facet_key", sa.String(length=128), nullable=False),
            sa.Column("label", sa.Text(), nullable=False),
            sa.Column("evidence", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("now()"),
                nullable=False,
            ),
            sa.ForeignKeyConstraint(["trend_id"], ["trend_themes.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("trend_id", "facet_key", name="uq_trend_facets_trend_key"),
        )
    if "cluster_decision_audits" not in tables:
        op.execute(
            """
            DO $$ BEGIN
                CREATE TYPE cluster_decision_action AS ENUM (
                    'merge_same_angle',
                    'merge_theme_keep_angles_separate',
                    'create_new_theme',
                    'needs_review',
                    'manual_merge',
                    'manual_move_out',
                    'rollback'
                );
            EXCEPTION WHEN duplicate_object THEN NULL;
            END $$;
            """,
        )
        op.execute(
            """
            DO $$ BEGIN
                CREATE TYPE cluster_decision_source AS ENUM (
                    'auto_high', 'auto_low', 'llm', 'lexical', 'manual'
                );
            EXCEPTION WHEN duplicate_object THEN NULL;
            END $$;
            """,
        )
        op.create_table(
            "cluster_decision_audits",
            sa.Column("id", sa.UUID(), nullable=False),
            sa.Column("source_cluster_key", sa.String(length=128), nullable=False),
            sa.Column("target_trend_id", sa.UUID(), nullable=True),
            sa.Column(
                "action",
                postgresql.ENUM(
                    "merge_same_angle",
                    "merge_theme_keep_angles_separate",
                    "create_new_theme",
                    "needs_review",
                    "manual_merge",
                    "manual_move_out",
                    "rollback",
                    name="cluster_decision_action",
                    create_type=False,
                ),
                nullable=False,
            ),
            sa.Column(
                "source",
                postgresql.ENUM(
                    "auto_high",
                    "auto_low",
                    "llm",
                    "lexical",
                    "manual",
                    name="cluster_decision_source",
                    create_type=False,
                ),
                nullable=False,
            ),
            sa.Column("similarity", sa.Float(), nullable=True),
            sa.Column("confidence", sa.Float(), nullable=True),
            sa.Column("embedding_space", sa.String(length=128), nullable=True),
            sa.Column("reason", sa.Text(), nullable=True),
            sa.Column("evidence", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            sa.Column("rolled_back", sa.Boolean(), nullable=False, server_default="false"),
            sa.Column("rollback_of_id", sa.UUID(), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("now()"),
                nullable=False,
            ),
            sa.ForeignKeyConstraint(["target_trend_id"], ["trend_themes.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(
                ["rollback_of_id"], ["cluster_decision_audits.id"], ondelete="SET NULL"
            ),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(
            "ix_cluster_decision_audits_created",
            "cluster_decision_audits",
            ["created_at"],
        )
        op.create_index(
            "ix_cluster_decision_audits_target",
            "cluster_decision_audits",
            ["target_trend_id", "created_at"],
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "cluster_decision_audits" in inspector.get_table_names():
        op.drop_index("ix_cluster_decision_audits_target", table_name="cluster_decision_audits")
        op.drop_index("ix_cluster_decision_audits_created", table_name="cluster_decision_audits")
        op.drop_table("cluster_decision_audits")
    op.execute("DROP TYPE IF EXISTS cluster_decision_source")
    op.execute("DROP TYPE IF EXISTS cluster_decision_action")
    if "trend_facets" in inspector.get_table_names():
        op.drop_table("trend_facets")
    if "embedding_cache" in inspector.get_table_names():
        op.drop_table("embedding_cache")
    member_columns = {c["name"] for c in inspector.get_columns("trend_members")}
    for column in ("deactivated_at", "last_confirmed_at", "active"):
        if column in member_columns:
            op.drop_column("trend_members", column)
