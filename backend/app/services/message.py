"""Outbound message sending + conversation listing helpers."""
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.conversation import Conversation
from app.models.message import Message
from app.models.whatsapp_number import WhatsAppNumber
from app.schemas.message import SendTextRequest
from app.services.evolution import EvolutionAPIError, evolution_client
from app.services.whatsapp_number import get_number


async def send_text_message(
    db: AsyncSession,
    organization_id: UUID,
    number_id: UUID,
    payload: SendTextRequest,
) -> dict:
    """Send a text via Evolution. Persistence happens via the SEND_MESSAGE webhook.
    Returns the Evolution response for the caller's reference.
    """
    number = await get_number(db, organization_id, number_id)
    if number.status != "connected":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Number is '{number.status}' — must be 'connected' to send messages",
        )
    try:
        response = await evolution_client.send_text(
            number.instance_name,
            to_phone_digits=payload.to,
            text=payload.text,
        )
    except EvolutionAPIError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Evolution API error: {exc.payload}",
        ) from exc
    return response


async def list_conversations_for_number(
    db: AsyncSession, organization_id: UUID, number_id: UUID
) -> list[Conversation]:
    await get_number(db, organization_id, number_id)  # tenant scoping check
    result = await db.execute(
        select(Conversation)
        .where(Conversation.whatsapp_number_id == number_id)
        .order_by(Conversation.last_message_at.desc().nullslast())
    )
    return list(result.scalars().all())


async def list_messages_for_conversation(
    db: AsyncSession,
    organization_id: UUID,
    conversation_id: UUID,
    limit: int = 100,
) -> list[Message]:
    # Tenant scoping via the conversation join.
    result = await db.execute(
        select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.organization_id == organization_id,
        )
    )
    conv = result.scalar_one_or_none()
    if conv is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found",
        )

    result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.sent_at.desc())
        .limit(limit)
    )
    return list(result.scalars().all())
