"""Notification settings service + Telegram dispatcher.

Reactive alerts (one-line summaries pushed to Telegram):
  - notify_number_disconnected: the paired WhatsApp dropped its connection
  - notify_webhook_abandoned:   a CRM delivery hit max_attempts and gave up

Both fire from the inbound webhook + delivery worker as fire-and-forget
asyncio tasks (strong-ref-tracked via webhook_inbound._spawn).
"""
import asyncio
import logging
from typing import Any
from uuid import UUID

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import AsyncSessionLocal
from app.models.notification_settings import NotificationSettings
from app.schemas.notifications import NotificationSettingsUpdate


logger = logging.getLogger(__name__)


TELEGRAM_API = "https://api.telegram.org"
TELEGRAM_TIMEOUT = 10.0


async def get_or_create_settings(
    db: AsyncSession, organization_id: UUID
) -> NotificationSettings:
    result = await db.execute(
        select(NotificationSettings).where(
            NotificationSettings.organization_id == organization_id
        )
    )
    row = result.scalar_one_or_none()
    if row is None:
        row = NotificationSettings(organization_id=organization_id)
        db.add(row)
        await db.commit()
        await db.refresh(row)
    return row


async def update_settings(
    db: AsyncSession,
    organization_id: UUID,
    payload: NotificationSettingsUpdate,
) -> NotificationSettings:
    row = await get_or_create_settings(db, organization_id)
    # Treat empty strings as "clear this field" — easier for the form than
    # distinguishing missing-vs-null on the wire.
    token = (payload.telegram_bot_token or "").strip() or None
    chat_id = (payload.telegram_chat_id or "").strip() or None
    row.telegram_bot_token = token
    row.telegram_chat_id = chat_id
    row.notify_on_number_disconnected = payload.notify_on_number_disconnected
    row.notify_on_webhook_abandoned = payload.notify_on_webhook_abandoned
    await db.commit()
    await db.refresh(row)
    return row


def hint_for_token(token: str | None) -> str | None:
    if not token:
        return None
    # Telegram bot tokens look like `123456789:ABCdef…`. Mask everything past
    # the colon except the last 4 chars so the UI can confirm the right one
    # is configured without leaking it.
    head, _, tail = token.partition(":")
    if not tail:
        return "***"
    suffix = tail[-4:] if len(tail) >= 4 else tail
    return f"{head}:***{suffix}"


# ---- dispatch -----------------------------------------------------------
async def _post_telegram(
    bot_token: str, chat_id: str, text: str
) -> tuple[bool, str | None]:
    url = f"{TELEGRAM_API}/bot{bot_token}/sendMessage"
    body = {"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}
    try:
        async with httpx.AsyncClient(timeout=TELEGRAM_TIMEOUT) as client:
            res = await client.post(url, json=body)
    except httpx.HTTPError as exc:
        return False, f"{type(exc).__name__}: {exc}"
    if res.status_code >= 400:
        excerpt = (res.text or "")[:300]
        return False, f"HTTP {res.status_code} {excerpt}"
    return True, None


async def send_test_message(
    settings: NotificationSettings,
) -> tuple[bool, str | None]:
    if not settings.telegram_bot_token or not settings.telegram_chat_id:
        return False, "Falta el bot token o el chat id."
    return await _post_telegram(
        settings.telegram_bot_token,
        settings.telegram_chat_id,
        "✅ *Portal.chat* — prueba de notificaciones. Si ves este mensaje, "
        "el bot está bien configurado.",
    )


async def _notify(
    organization_id: UUID, text: str, *, flag: str
) -> None:
    """Look up the org's settings and push to Telegram if the flag is on."""
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(NotificationSettings).where(
                NotificationSettings.organization_id == organization_id
            )
        )
        settings = result.scalar_one_or_none()
        if settings is None:
            return
        if not getattr(settings, flag, False):
            return
        if not settings.telegram_bot_token or not settings.telegram_chat_id:
            return
        ok, err = await _post_telegram(
            settings.telegram_bot_token,
            settings.telegram_chat_id,
            text,
        )
        if not ok:
            logger.warning(
                "Telegram notification failed for org %s: %s",
                organization_id,
                err,
            )


async def notify_number_disconnected(
    organization_id: UUID, *, number_name: str, phone: str | None
) -> None:
    text = (
        f"⚠️ *Número desconectado*\n"
        f"{number_name}"
        + (f" (+{phone})" if phone else "")
        + "\n\nReconectalo escaneando el QR desde el portal."
    )
    await _notify(
        organization_id, text, flag="notify_on_number_disconnected"
    )


async def notify_webhook_abandoned(
    organization_id: UUID,
    *,
    number_name: str,
    target_url: str,
    event_type: str,
    attempts: int,
    error: str | None,
) -> None:
    text = (
        f"❌ *Webhook abandonado*\n"
        f"Número: {number_name}\n"
        f"Evento: `{event_type}`\n"
        f"URL: `{target_url}`\n"
        f"Intentos: {attempts}\n"
    )
    if error:
        text += f"Último error: `{error[:200]}`"
    await _notify(
        organization_id, text, flag="notify_on_webhook_abandoned"
    )


def fire_and_forget(coro: Any) -> None:
    """Schedule a Telegram notification without blocking the caller. The
    notification is best-effort — failures are logged inside _notify."""
    from app.services.webhook_inbound import _spawn

    _spawn(coro)
