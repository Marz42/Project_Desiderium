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


def upgrade() -> None:
    bind = op.get_bind()
    Base.metadata.create_all(bind)


def downgrade() -> None:
    bind = op.get_bind()
    Base.metadata.drop_all(bind)
