"""angle_status_audits table."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "b2c3d4e5f6a7"
down_revision: Union[str, None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "angle_status_audits",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("creative_angle_id", sa.UUID(), nullable=False),
        sa.Column(
            "from_status",
            sa.Enum(
                "candidate",
                "selected",
                "adopted",
                "published",
                "reusable",
                "blocked",
                name="angle_status",
                create_type=False,
            ),
            nullable=True,
        ),
        sa.Column(
            "to_status",
            sa.Enum(
                "candidate",
                "selected",
                "adopted",
                "published",
                "reusable",
                "blocked",
                name="angle_status",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["creative_angle_id"], ["creative_angles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_angle_status_audits_angle_created",
        "angle_status_audits",
        ["creative_angle_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_angle_status_audits_angle_created", table_name="angle_status_audits")
    op.drop_table("angle_status_audits")
