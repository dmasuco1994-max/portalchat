"""Notification settings schemas."""
from pydantic import BaseModel, Field


class NotificationSettingsRead(BaseModel):
    """Returned to the frontend. The bot token is masked (we only expose
    whether one is configured + the last 4 chars), never the full value."""

    telegram_chat_id: str | None
    notify_on_number_disconnected: bool
    notify_on_webhook_abandoned: bool
    has_telegram_bot_token: bool
    telegram_bot_token_hint: str | None = None


class NotificationSettingsUpdate(BaseModel):
    """Full replacement of the notification config. The frontend sends every
    field on save. Empty strings are treated as null (clears the field)."""

    telegram_bot_token: str | None = Field(default=None, max_length=200)
    telegram_chat_id: str | None = Field(default=None, max_length=80)
    notify_on_number_disconnected: bool = True
    notify_on_webhook_abandoned: bool = True


class TelegramTestResult(BaseModel):
    success: bool
    detail: str | None = None
