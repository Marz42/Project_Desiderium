"""G3/G4 schema: trend membership soft-sync, embedding/facet/decision audits,
publication performance feedback, and brief finalize snapshot columns.

Idempotent on both paths: fresh `create_all` and incremental upgrade from
pre-G3/G4 databases.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "e5f6a7b8c9d0"
down_revision: Union[str, None] = "d4e5f6a7b8c9"
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

    inspector = sa.inspect(bind)
    pub_columns = {c["name"] for c in inspector.get_columns("publication_records")}
    if "platform" not in pub_columns:
        op.add_column(
            "publication_records",
            sa.Column(
                "platform",
                postgresql.ENUM("youtube", "tiktok", "other", name="platform", create_type=False),
                nullable=True,
            ),
        )
    if "external_video_id" not in pub_columns:
        op.add_column(
            "publication_records", sa.Column("external_video_id", sa.Text(), nullable=True)
        )
    if "channel_external_id" not in pub_columns:
        op.add_column(
            "publication_records", sa.Column("channel_external_id", sa.Text(), nullable=True)
        )
    if "trend_id" not in pub_columns:
        op.add_column("publication_records", sa.Column("trend_id", sa.UUID(), nullable=True))
    if "daily_candidate_id" not in pub_columns:
        op.add_column(
            "publication_records", sa.Column("daily_candidate_id", sa.UUID(), nullable=True)
        )
    if "format" not in pub_columns:
        op.add_column(
            "publication_records",
            sa.Column(
                "format",
                postgresql.ENUM("short", "long", "both", name="creative_format", create_type=False),
                nullable=True,
            ),
        )
    if "fetch_status" not in pub_columns:
        op.execute(
            """
            DO $$ BEGIN
                CREATE TYPE publication_fetch_status AS ENUM ('pending', 'success', 'failed');
            EXCEPTION WHEN duplicate_object THEN NULL;
            END $$;
            """,
        )
        op.add_column(
            "publication_records",
            sa.Column(
                "fetch_status",
                postgresql.ENUM(
                    "pending",
                    "success",
                    "failed",
                    name="publication_fetch_status",
                    create_type=False,
                ),
                nullable=True,
            ),
        )
    if "last_fetch_error" not in pub_columns:
        op.add_column(
            "publication_records", sa.Column("last_fetch_error", sa.Text(), nullable=True)
        )
    if "last_fetched_at" not in pub_columns:
        op.add_column(
            "publication_records",
            sa.Column("last_fetched_at", sa.DateTime(timezone=True), nullable=True),
        )

    inspector = sa.inspect(bind)
    pub_fks = {fk.get("referred_table") for fk in inspector.get_foreign_keys("publication_records")}
    if "trend_themes" not in pub_fks:
        op.create_foreign_key(
            "fk_publication_records_trend",
            "publication_records",
            "trend_themes",
            ["trend_id"],
            ["id"],
            ondelete="SET NULL",
        )
    if "daily_candidates" not in pub_fks:
        op.create_foreign_key(
            "fk_publication_records_daily_candidate",
            "publication_records",
            "daily_candidates",
            ["daily_candidate_id"],
            ["id"],
            ondelete="SET NULL",
        )

    if "publication_metric_snapshots" not in inspector.get_table_names():
        op.execute(
            """
            DO $$ BEGIN
                CREATE TYPE publication_window_key AS ENUM ('initial', '24h', '72h', '7d');
            EXCEPTION WHEN duplicate_object THEN NULL;
            END $$;
            """,
        )
        op.create_table(
            "publication_metric_snapshots",
            sa.Column("id", sa.UUID(), nullable=False),
            sa.Column("publication_record_id", sa.UUID(), nullable=False),
            sa.Column(
                "window_key",
                postgresql.ENUM(
                    "initial",
                    "24h",
                    "72h",
                    "7d",
                    name="publication_window_key",
                    create_type=False,
                ),
                nullable=False,
            ),
            sa.Column("captured_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("video_age_hours", sa.Float(), nullable=False),
            sa.Column(
                "age_bucket",
                postgresql.ENUM(
                    "0-6h", "6-24h", "24-72h", "3-7d", name="age_bucket", create_type=False
                ),
                nullable=True,
            ),
            sa.Column("views", sa.BigInteger(), nullable=False, server_default="0"),
            sa.Column("likes", sa.BigInteger(), nullable=True),
            sa.Column("comments", sa.BigInteger(), nullable=True),
            sa.Column(
                "source", sa.String(length=32), nullable=False, server_default="youtube_public"
            ),
            sa.Column("late_backfill", sa.Boolean(), nullable=False, server_default="false"),
            sa.Column("baseline_velocity", sa.Float(), nullable=True),
            sa.Column("baseline_sample_count", sa.Integer(), nullable=True),
            sa.Column(
                "baseline_confidence",
                postgresql.ENUM(
                    "low", "medium", "high", name="baseline_confidence", create_type=False
                ),
                nullable=True,
            ),
            sa.Column("performance_ratio", sa.Float(), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("now()"),
                nullable=False,
            ),
            sa.ForeignKeyConstraint(
                ["publication_record_id"], ["publication_records.id"], ondelete="CASCADE"
            ),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint(
                "publication_record_id",
                "window_key",
                name="uq_publication_metric_snapshots_record_window",
            ),
        )

    brief_columns = {c["name"] for c in inspector.get_columns("briefs")}
    if "finalized_snapshot" not in brief_columns:
        op.add_column(
            "briefs",
            sa.Column(
                "finalized_snapshot",
                postgresql.JSONB(astext_type=sa.Text()),
                nullable=True,
            ),
        )
    if "finalized_content_hash" not in brief_columns:
        op.add_column(
            "briefs", sa.Column("finalized_content_hash", sa.String(length=64), nullable=True)
        )
    if "finalized_at" not in brief_columns:
        op.add_column(
            "briefs", sa.Column("finalized_at", sa.DateTime(timezone=True), nullable=True)
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

    brief_columns = {c["name"] for c in inspector.get_columns("briefs")}
    if "finalized_at" in brief_columns:
        op.drop_column("briefs", "finalized_at")
    if "finalized_content_hash" in brief_columns:
        op.drop_column("briefs", "finalized_content_hash")
    if "finalized_snapshot" in brief_columns:
        op.drop_column("briefs", "finalized_snapshot")

    if "publication_metric_snapshots" in inspector.get_table_names():
        op.drop_table("publication_metric_snapshots")
    op.execute("DROP TYPE IF EXISTS publication_window_key")

    inspector = sa.inspect(bind)
    for fk in inspector.get_foreign_keys("publication_records"):
        if fk.get("referred_table") in ("trend_themes", "daily_candidates") and fk.get("name"):
            op.drop_constraint(fk["name"], "publication_records", type_="foreignkey")

    pub_columns = {c["name"] for c in inspector.get_columns("publication_records")}
    for column in (
        "last_fetched_at",
        "last_fetch_error",
        "fetch_status",
        "format",
        "daily_candidate_id",
        "trend_id",
        "channel_external_id",
        "external_video_id",
        "platform",
    ):
        if column in pub_columns:
            op.drop_column("publication_records", column)
    op.execute("DROP TYPE IF EXISTS publication_fetch_status")
