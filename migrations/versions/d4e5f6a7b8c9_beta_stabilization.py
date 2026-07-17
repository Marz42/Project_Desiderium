"""Beta stabilization: idempotent angles and analysis-run metadata."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "d4e5f6a7b8c9"
down_revision: Union[str, None] = "c8d9e0f1a2b3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "analysis_runs" not in inspector.get_table_names():
        op.create_table(
            "analysis_runs",
            sa.Column("id", sa.UUID(), nullable=False),
            sa.Column("run_date", sa.Date(), nullable=False),
            sa.Column("run_kind", sa.String(length=64), nullable=False),
            sa.Column("scoring_version", sa.String(length=64), nullable=True),
            sa.Column("algorithm_version", sa.String(length=64), nullable=False),
            sa.Column("config_hash", sa.String(length=64), nullable=False),
            sa.Column("config_snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            sa.Column("prompt_versions", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("summary", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("run_date", "run_kind", name="uq_analysis_runs_date_kind"),
        )

    inspector = sa.inspect(bind)
    candidate_columns = {column["name"] for column in inspector.get_columns("daily_candidates")}
    if "analysis_run_id" not in candidate_columns:
        op.add_column("daily_candidates", sa.Column("analysis_run_id", sa.UUID(), nullable=True))
    foreign_keys = {key.get("name") for key in inspector.get_foreign_keys("daily_candidates")}
    if "fk_daily_candidates_analysis_run" not in foreign_keys and not any(
        key.get("referred_table") == "analysis_runs"
        for key in inspector.get_foreign_keys("daily_candidates")
    ):
        op.create_foreign_key(
            "fk_daily_candidates_analysis_run",
            "daily_candidates",
            "analysis_runs",
            ["analysis_run_id"],
            ["id"],
            ondelete="SET NULL",
        )

    # Preserve historical duplicates while making future generated angles
    # database-idempotent. Only duplicate fingerprints receive a legacy suffix.
    angle_constraints = {
        constraint.get("name") for constraint in inspector.get_unique_constraints("creative_angles")
    }
    if "uq_creative_angles_trend_date_fingerprint" not in angle_constraints:
        op.execute(
            """
            WITH duplicates AS (
                SELECT id,
                       row_number() OVER (
                           PARTITION BY trend_id, generated_date, semantic_fingerprint
                           ORDER BY created_at, id
                       ) AS duplicate_number
                FROM creative_angles
                WHERE semantic_fingerprint IS NOT NULL
            )
            UPDATE creative_angles AS angle
            SET semantic_fingerprint = angle.semantic_fingerprint || ':legacy:' || left(angle.id::text, 8)
            FROM duplicates
            WHERE angle.id = duplicates.id
              AND duplicates.duplicate_number > 1
            """,
        )
        op.create_unique_constraint(
            "uq_creative_angles_trend_date_fingerprint",
            "creative_angles",
            ["trend_id", "generated_date", "semantic_fingerprint"],
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    angle_constraints = {
        constraint.get("name") for constraint in inspector.get_unique_constraints("creative_angles")
    }
    if "uq_creative_angles_trend_date_fingerprint" in angle_constraints:
        op.drop_constraint(
            "uq_creative_angles_trend_date_fingerprint",
            "creative_angles",
            type_="unique",
        )
    for foreign_key in inspector.get_foreign_keys("daily_candidates"):
        if foreign_key.get("referred_table") == "analysis_runs" and foreign_key.get("name"):
            op.drop_constraint(
                foreign_key["name"],
                "daily_candidates",
                type_="foreignkey",
            )
            break
    op.drop_column("daily_candidates", "analysis_run_id")
    op.drop_table("analysis_runs")
