"""Conversation listing endpoints."""
from uuid import UUID

from fastapi import APIRouter

from app.core.deps import CurrentUser, DbSession
from app.schemas.conversation import ConversationRead
from app.services.message import list_conversations_for_number


router = APIRouter(tags=["conversations"])


@router.get(
    "/numbers/{number_id}/conversations",
    response_model=list[ConversationRead],
    summary="List conversations for a number (most recent activity first).",
)
async def list_for_number(
    number_id: UUID,
    db: DbSession,
    current: CurrentUser,
) -> list[ConversationRead]:
    convs = await list_conversations_for_number(
        db, current.organization_id, number_id
    )
    return [ConversationRead.model_validate(c) for c in convs]
