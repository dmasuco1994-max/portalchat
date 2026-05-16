"""phase 8: webhook format + extra (apiwha/neotel adapter)

Revision ID: a1b2c3d4e5f6
Revises: d27fb295d8cc
Create Date: 2026-05-16 22:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "d27fb295d8cc"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


VALID_FORMATS = ("portal", "apiwha_neotel")


def upgrade() -> None:
    op.add_column(
        "whatsapp_numbers",
        sa.Column(
            "webhook_format",
            sa.String(length=32),
            nullable=False,
            server_default="portal",
        ),
    )
    op.add_column(
        "whatsapp_numbers",
        sa.Column(
            "webhook_extra",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
    )
    op.create_check_constraint(
        "ck_whatsapp_numbers_webhook_format",
        "whatsapp_numbers",
        f"webhook_format IN {VALID_FORMATS}",
    )

    op.add_column(
        "webhook_deliveries",
        sa.Column(
            "format",
            sa.String(length=32),
            nullable=False,
            server_default="portal",
        ),
    )
    op.create_check_constraint(
        "ck_webhook_deliveries_format",
        "webhook_deliveries",
        f"format IN {VALID_FORMATS}",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_webhook_deliveries_format", "webhook_deliveries", type_="check"
    )
    op.drop_column("webhook_deliveries", "format")

    op.drop_constraint(
        "ck_whatsapp_numbers_webhook_format", "whatsapp_numbers", type_="check"
    )
    op.drop_column("whatsapp_numbers", "webhook_extra")
    op.drop_column("whatsapp_numbers", "webhook_format")
