"""phase 8.2: add neotel_custom to webhook_format enum

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-05-16 23:30:00.000000

"""
from typing import Sequence, Union

from alembic import op


revision: str = "b2c3d4e5f6a7"
down_revision: Union[str, Sequence[str], None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


VALID_FORMATS_NEW = ("portal", "apiwha_neotel", "neotel_custom")
VALID_FORMATS_OLD = ("portal", "apiwha_neotel")


def _replace_constraint(table: str, name: str, allowed: tuple[str, ...]) -> None:
    op.drop_constraint(name, table, type_="check")
    op.create_check_constraint(name, table, f"format IN {allowed}" if table == "webhook_deliveries" else f"webhook_format IN {allowed}")


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


def downgrade() -> None:
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
