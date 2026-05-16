"""one-shot: clear conversation.remote_name when it matches an operator's full_name

When `_get_or_create_conversation` used Evolution's `pushName` on every
event, outbound (fromMe=True) messages would stomp `remote_name` with the
sending operator's WhatsApp profile name. Result: every conversation the
operator answered ended up labelled with the operator's own name.

This migration NULLs `remote_name` wherever it equals the `full_name` of
any user in the same organization. The next inbound message in each
conversation re-populates it correctly with the contact's pushName.

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
Create Date: 2026-05-17 00:30:00.000000

"""
from typing import Sequence, Union

from alembic import op


revision: str = "f6a7b8c9d0e1"
down_revision: Union[str, Sequence[str], None] = "e5f6a7b8c9d0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        UPDATE conversations c
        SET remote_name = NULL
        FROM users u
        WHERE u.organization_id = c.organization_id
          AND u.full_name = c.remote_name;
        """
    )


def downgrade() -> None:
    # Irrecoverable — we don't know which names we cleared. No-op.
    pass
