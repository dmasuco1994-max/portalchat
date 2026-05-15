"""Outbound message endpoints."""
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.core.deps import CurrentUser, DbSession, require_admin
from app.schemas.message import MessageRead, SendTextRequest
from app.services.message import (
    list_messages_for_conversation,
    send_text_message,
)


router = APIRouter(tags=["messages"])


@router.post(
    "/numbers/{number_id}/messages/text",
    dependencies=[Depends(require_admin)],
    summary="Send a text message via the given number.",
)
async def send_text(
    number_id: UUID,
    payload: SendTextRequest,
    db: DbSession,
    current: CurrentUser,
) -> dict[str, Any]:
    return await send_text_message(db, current.organization_id, number_id, payload)


@router.get(
    "/conversations/{conversation_id}/messages",
    response_model=list[MessageRead],
    summary="List messages in a conversation (newest first).",
)
async def list_conversation_messages(
    conversation_id: UUID,
    db: DbSession,
    current: CurrentUser,
    limit: int = Query(default=100, ge=1, le=500),
) -> list[MessageRead]:
    msgs = await list_messages_for_conversation(
        db, current.organization_id, conversation_id, limit=limit
    )
    return [MessageRead.model_validate(m) for m in msgs]
