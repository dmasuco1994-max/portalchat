"""Media endpoints: serve inbound media + accept outbound media uploads."""
import base64
import logging
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import select

from app.core.deps import CurrentUser, DbSession, require_admin
from app.models.conversation import Conversation
from app.models.message import Message
from app.models.whatsapp_number import WhatsAppNumber
from app.services import media as media_service
from app.services.evolution import EvolutionAPIError, evolution_client


logger = logging.getLogger(__name__)
router = APIRouter(tags=["media"])


async def _load_tenant_message(
    db, organization_id: UUID, message_id: UUID
) -> tuple[Message, WhatsAppNumber]:
    """Fetch a message scoped to the current org; 404 if cross-tenant access."""
    result = await db.execute(
        select(Message, WhatsAppNumber)
        .join(
            Conversation, Conversation.id == Message.conversation_id
        )
        .join(
            WhatsAppNumber,
            WhatsAppNumber.id == Conversation.whatsapp_number_id,
        )
        .where(
            Message.id == message_id,
            Conversation.organization_id == organization_id,
        )
    )
    row = result.first()
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Message not found"
        )
    return row[0], row[1]


@router.get(
    "/messages/{message_id}/media",
    summary=(
        "Stream the decoded bytes of a media message. Pulls from Evolution on "
        "first hit, caches on disk for subsequent reads."
    ),
)
async def get_message_media(
    message_id: UUID,
    db: DbSession,
    current: CurrentUser,
) -> FileResponse:
    message, number = await _load_tenant_message(
        db, current.organization_id, message_id
    )
    if message.content_type not in (
        "image",
        "video",
        "audio",
        "document",
        "sticker",
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Message type '{message.content_type}' has no media body.",
        )

    cached = media_service.get_cached(message)
    if cached is None:
        cached = await media_service.fetch_and_cache(message, number.instance_name)
    if cached is None:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Could not fetch the media from Evolution.",
        )
    path, mimetype = cached
    filename = message.content_text or path.name
    return FileResponse(
        path,
        media_type=mimetype,
        # Inline for previewable types; attachment for documents.
        headers={
            "Content-Disposition": (
                f'attachment; filename="{filename}"'
                if message.content_type == "document"
                else "inline"
            ),
            # Cache aggressively in the browser — the URL has the message id,
            # so a re-render won't re-fetch.
            "Cache-Control": "private, max-age=3600",
        },
    )


_ALLOWED_OUTBOUND_MIME = {
    "image/jpeg",
    "image/png",
    "image/webp",
    "image/gif",
    "video/mp4",
    "audio/mpeg",
    "audio/mp4",
    "audio/ogg",
    "audio/webm",
    "application/pdf",
}

_MAX_UPLOAD_BYTES = 16 * 1024 * 1024  # 16 MB — WhatsApp limits images to ~16MB.


def _mediatype_for(mimetype: str) -> str | None:
    if mimetype.startswith("image/"):
        return "image"
    if mimetype.startswith("video/"):
        return "video"
    if mimetype == "application/pdf" or mimetype.startswith("application/"):
        return "document"
    return None


@router.post(
    "/numbers/{number_id}/messages/media",
    summary="Send an image, video, audio or document via the given WhatsApp number.",
    dependencies=[Depends(require_admin)],
)
async def send_media(
    number_id: UUID,
    db: DbSession,
    current: CurrentUser,
    to: str = Form(...),
    file: UploadFile = File(...),
    caption: str | None = Form(default=None),
) -> dict:
    # Tenant + status check via the standard get_number helper would be ideal,
    # but importing it here would cycle — query inline.
    result = await db.execute(
        select(WhatsAppNumber).where(
            WhatsAppNumber.id == number_id,
            WhatsAppNumber.organization_id == current.organization_id,
        )
    )
    number = result.scalar_one_or_none()
    if number is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Number not found"
        )
    if number.status != "connected":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Number is '{number.status}' — must be 'connected' to send.",
        )

    mimetype = (file.content_type or "").lower()
    if mimetype not in _ALLOWED_OUTBOUND_MIME:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported file type: {mimetype}.",
        )

    contents = await file.read()
    if len(contents) > _MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=(
                f"File too large ({len(contents)} bytes). Max {_MAX_UPLOAD_BYTES}."
            ),
        )

    phone_digits = "".join(ch for ch in to if ch.isdigit())
    if not phone_digits:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Field 'to' must contain at least one digit.",
        )

    b64 = base64.b64encode(contents).decode("ascii")

    try:
        if mimetype.startswith("audio/"):
            response = await evolution_client.send_audio(
                number.instance_name,
                phone_digits,
                audio_base64=b64,
            )
        else:
            mediatype = _mediatype_for(mimetype)
            if mediatype is None:
                raise HTTPException(
                    status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                    detail=f"Cannot map mimetype {mimetype} to a WhatsApp media type.",
                )
            response = await evolution_client.send_media(
                number.instance_name,
                phone_digits,
                mediatype=mediatype,
                mimetype=mimetype,
                media_base64=b64,
                caption=caption,
                file_name=file.filename if mediatype == "document" else None,
            )
    except EvolutionAPIError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Evolution rejected the send: {exc.payload}",
        ) from exc

    return {"success": True, "evolution_response": response}
