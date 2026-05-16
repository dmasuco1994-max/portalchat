"""one-shot v2: clear conversation.remote_name when it equals the operator's
WhatsApp pushName (extracted from outbound messages' raw_payload)

The earlier migration `f6a7b8c9d0e1` cleared rows where `remote_name`
matched a user's portal `full_name`, but the operator's WhatsApp profile
name is set on their PHONE, not in our DB — so a portal user signed up as
\"Test Owner\" while their WhatsApp profile says \"Dani Masuco\", and the
earlier migration cleared nothing.

This migration is the right cut: for each WhatsApp number, derive the set
of pushNames that appear on outbound messages (those are by definition
operator-side names), and NULL `remote_name` on any conversation belonging
to that number whose name matches one of them.

Revision ID: a7b8c9d0e1f2
Revises: f6a7b8c9d0e1
Create Date: 2026-05-17 01:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


revision: str = "a7b8c9d0e1f2"
down_revision: Union[str, Sequence[str], None] = "f6a7b8c9d0e1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        WITH operator_names AS (
          SELECT DISTINCT
            m.whatsapp_number_id,
            m.raw_payload->'data'->>'pushName' AS name
          FROM messages m
          WHERE m.direction = 'outbound'
            AND m.raw_payload IS NOT NULL
            AND m.raw_payload->'data'->>'pushName' IS NOT NULL
            AND m.raw_payload->'data'->>'pushName' <> ''
        )
        UPDATE conversations c
        SET remote_name = NULL
        FROM operator_names o
        WHERE o.whatsapp_number_id = c.whatsapp_number_id
          AND o.name = c.remote_name;
        """
    )


def downgrade() -> None:
    # Irrecoverable — we don't store what we cleared.
    pass
