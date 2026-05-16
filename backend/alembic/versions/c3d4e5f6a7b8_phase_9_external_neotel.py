"""phase 9: add external_neotel to webhook_format enum

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-05-16 23:55:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "c3d4e5f6a7b8"
down_revision: Union[str, Sequence[str], None] = "b2c3d4e5f6a7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


VALID_FORMATS_NEW = ("portal", "apiwha_neotel", "neotel_custom", "external_neotel")
VALID_FORMATS_OLD = ("portal", "apiwha_neotel", "neotel_custom")


def upgrade() -> None:
    op.drop_constraint(
        "ck_whatsapp_numbers_webhook_format", "whatsapp_numbers", type_="check"
    )
    op.create_check_constraint(
        "ck_whatsapp_numbers_webhook_format",
        "whatsapp_numbers",
        f"webhook_format IN {VALID_FORMATS_NEW}",
    )

    op.drop_constraint(
        "ck_webhook_deliveries_format", "webhook_deliveries", type_="check"
    )
    op.create_check_constraint(
        "ck_webhook_deliveries_format",
        "webhook_deliveries",
        f"format IN {VALID_FORMATS_NEW}",
    )

    # Per-delivery snapshot of extra HTTP headers the format requires (e.g.
    # external_neotel's ApplicationId + AccessToken). Nullable; portal-format
    # rows leave this null.
    op.add_column(
        "webhook_deliveries",
        sa.Column(
            "extra_headers",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("webhook_deliveries", "extra_headers")

    op.drop_constraint(
        "ck_webhook_deliveries_format", "webhook_deliveries", type_="check"
    )
    op.create_check_constraint(
        "ck_webhook_deliveries_format",
        "webhook_deliveries",
        f"format IN {VALID_FORMATS_OLD}",
    )

    op.drop_constraint(
        "ck_whatsapp_numbers_webhook_format", "whatsapp_numbers", type_="check"
    )
    op.create_check_constraint(
        "ck_whatsapp_numbers_webhook_format",
        "whatsapp_numbers",
        f"webhook_format IN {VALID_FORMATS_OLD}",
    )
