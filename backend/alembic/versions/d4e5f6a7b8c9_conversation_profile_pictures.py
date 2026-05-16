"""conversation profile pictures + last fetch timestamp

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-05-16 23:59:30.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d4e5f6a7b8c9"
down_revision: Union[str, Sequence[str], None] = "c3d4e5f6a7b8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "conversations",
        sa.Column("profile_picture_url", sa.String(length=1000), nullable=True),
    )
    op.add_column(
        "conversations",
        sa.Column(
            "profile_picture_fetched_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("conversations", "profile_picture_fetched_at")
    op.drop_column("conversations", "profile_picture_url")
