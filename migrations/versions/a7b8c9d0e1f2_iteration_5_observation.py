"""Iteration 5 integrity, rollback, and observation contracts.

Revision ID: a7b8c9d0e1f2
Revises: f6a7b8c9d0e1
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "a7b8c9d0e1f2"
down_revision = "f6a7b8c9d0e1"
branch_labels = None
depends_on = None


def _columns(inspector: sa.Inspector, table: str) -> set[str]:
    return {str(column["name"]) for column in inspector.get_columns(table)}


def _constraints(inspector: sa.Inspector, table: str) -> set[str]:
    return {
        str(item["name"])
        for item in inspector.get_unique_constraints(table)
        if item.get("name")
    }


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    trend_columns = _columns(inspector, "trend_themes")
    if "active" not in trend_columns:
        op.add_column(
            "trend_themes",
            sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        )
    if "merged_into_id" not in trend_columns:
        op.add_column("trend_themes", sa.Column("merged_into_id", sa.UUID(), nullable=True))
        op.create_foreign_key(
            "fk_trend_themes_merged_into",
            "trend_themes",
            "trend_themes",
            ["merged_into_id"],
            ["id"],
            ondelete="SET NULL",
        )

    member_columns = _columns(inspector, "trend_members")
    if "decision_version" not in member_columns:
        op.add_column(
            "trend_members",
            sa.Column("decision_version", sa.Integer(), nullable=False, server_default="0"),
        )

    audit_columns = _columns(inspector, "cluster_decision_audits")
    if "decision_version" not in audit_columns:
        op.add_column(
            "cluster_decision_audits",
            sa.Column("decision_version", sa.Integer(), nullable=False, server_default="1"),
        )
    if "rolled_back_at" not in audit_columns:
        op.add_column(
            "cluster_decision_audits",
            sa.Column("rolled_back_at", sa.DateTime(timezone=True), nullable=True),
        )
    if "rollback_audit_id" not in audit_columns:
        op.add_column(
            "cluster_decision_audits",
            sa.Column("rollback_audit_id", sa.UUID(), nullable=True),
        )
        op.create_foreign_key(
            "fk_cluster_decision_audits_rollback_audit",
            "cluster_decision_audits",
            "cluster_decision_audits",
            ["rollback_audit_id"],
            ["id"],
            ondelete="SET NULL",
        )
    audit_constraints = _constraints(sa.inspect(bind), "cluster_decision_audits")
    if "uq_cluster_decision_audits_rollback_of" not in audit_constraints:
        op.create_unique_constraint(
            "uq_cluster_decision_audits_rollback_of",
            "cluster_decision_audits",
            ["rollback_of_id"],
        )

    brief_columns = _columns(inspector, "briefs")
    if "finalized_by" not in brief_columns:
        op.add_column("briefs", sa.Column("finalized_by", sa.String(length=128), nullable=True))

    analysis_constraints = _constraints(inspector, "analysis_runs")
    if "uq_analysis_runs_date_kind" in analysis_constraints:
        op.drop_constraint("uq_analysis_runs_date_kind", "analysis_runs", type_="unique")
    analysis_indexes = {item["name"] for item in inspector.get_indexes("analysis_runs")}
    if "ix_analysis_runs_date_kind" not in analysis_indexes:
        op.create_index(
            "ix_analysis_runs_date_kind",
            "analysis_runs",
            ["run_date", "run_kind"],
        )
    analysis_columns = _columns(inspector, "analysis_runs")
    if "run_fingerprint" not in analysis_columns:
        op.add_column(
            "analysis_runs",
            sa.Column("run_fingerprint", sa.String(length=64), nullable=True),
        )
        op.execute(
            "UPDATE analysis_runs "
            "SET run_fingerprint = md5(id::text || ':' || run_kind || ':' || run_date::text)"
        )
        op.alter_column("analysis_runs", "run_fingerprint", nullable=False)

    candidate_columns = _columns(inspector, "daily_candidates")
    if "trend_score_snapshot" not in candidate_columns:
        op.add_column(
            "daily_candidates",
            sa.Column("trend_score_snapshot", sa.Float(), nullable=True),
        )
    if "lifecycle_status_snapshot" not in candidate_columns:
        op.add_column(
            "daily_candidates",
            sa.Column(
                "lifecycle_status_snapshot",
                postgresql.ENUM(name="lifecycle_status", create_type=False),
                nullable=True,
            ),
        )

    publication_columns = _columns(inspector, "publication_records")
    publication_additions: list[sa.Column] = [
        sa.Column("brief_id", sa.UUID(), nullable=True),
        sa.Column("brief_finalized_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "consecutive_fetch_failures",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column("next_retry_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "terminal_fetch_failure",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    ]
    for column in publication_additions:
        if column.name not in publication_columns:
            op.add_column("publication_records", column)
    if "brief_id" not in publication_columns:
        op.create_foreign_key(
            "fk_publication_records_brief",
            "publication_records",
            "briefs",
            ["brief_id"],
            ["id"],
            ondelete="SET NULL",
        )

    publication_constraints = _constraints(sa.inspect(bind), "publication_records")
    if "uq_publication_records_platform_video" not in publication_constraints:
        duplicates = bind.execute(
            sa.text(
                "SELECT platform::text, external_video_id, COUNT(*) "
                "FROM publication_records "
                "WHERE platform IS NOT NULL AND external_video_id IS NOT NULL "
                "GROUP BY platform, external_video_id HAVING COUNT(*) > 1"
            )
        ).all()
        if duplicates:
            preview = ", ".join(
                f"{platform}:{video_id} ({count})"
                for platform, video_id, count in duplicates[:20]
            )
            raise RuntimeError(
                "Cannot add publication video uniqueness; resolve duplicates first: "
                + preview
            )
        op.create_unique_constraint(
            "uq_publication_records_platform_video",
            "publication_records",
            ["platform", "external_video_id"],
        )

    snapshot_columns = _columns(inspector, "publication_metric_snapshots")
    if "baseline_version" not in snapshot_columns:
        op.add_column(
            "publication_metric_snapshots",
            sa.Column("baseline_version", sa.String(length=64), nullable=True),
        )
    if "calculated_at" not in snapshot_columns:
        op.add_column(
            "publication_metric_snapshots",
            sa.Column("calculated_at", sa.DateTime(timezone=True), nullable=True),
        )
    if "observed_ratio_at_window" not in snapshot_columns:
        op.add_column(
            "publication_metric_snapshots",
            sa.Column("observed_ratio_at_window", sa.Float(), nullable=True),
        )
        op.execute(
            "UPDATE publication_metric_snapshots "
            "SET observed_ratio_at_window = performance_ratio"
        )


def downgrade() -> None:
    op.drop_column("publication_metric_snapshots", "observed_ratio_at_window")
    op.drop_column("publication_metric_snapshots", "calculated_at")
    op.drop_column("publication_metric_snapshots", "baseline_version")

    op.drop_constraint(
        "uq_publication_records_platform_video",
        "publication_records",
        type_="unique",
    )
    op.drop_constraint("fk_publication_records_brief", "publication_records", type_="foreignkey")
    op.drop_column("publication_records", "terminal_fetch_failure")
    op.drop_column("publication_records", "next_retry_at")
    op.drop_column("publication_records", "consecutive_fetch_failures")
    op.drop_column("publication_records", "brief_finalized_at")
    op.drop_column("publication_records", "brief_id")

    op.drop_column("daily_candidates", "lifecycle_status_snapshot")
    op.drop_column("daily_candidates", "trend_score_snapshot")
    op.drop_column("analysis_runs", "run_fingerprint")
    op.drop_index("ix_analysis_runs_date_kind", table_name="analysis_runs")
    op.create_unique_constraint(
        "uq_analysis_runs_date_kind",
        "analysis_runs",
        ["run_date", "run_kind"],
    )
    op.drop_column("briefs", "finalized_by")

    op.drop_constraint(
        "uq_cluster_decision_audits_rollback_of",
        "cluster_decision_audits",
        type_="unique",
    )
    op.drop_constraint(
        "fk_cluster_decision_audits_rollback_audit",
        "cluster_decision_audits",
        type_="foreignkey",
    )
    op.drop_column("cluster_decision_audits", "rollback_audit_id")
    op.drop_column("cluster_decision_audits", "rolled_back_at")
    op.drop_column("cluster_decision_audits", "decision_version")
    op.drop_column("trend_members", "decision_version")
    op.drop_constraint("fk_trend_themes_merged_into", "trend_themes", type_="foreignkey")
    op.drop_column("trend_themes", "merged_into_id")
    op.drop_column("trend_themes", "active")
