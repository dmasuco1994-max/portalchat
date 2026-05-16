"""WebhookDelivery read schema — used by the debug endpoint."""
from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


DeliveryStatus = Literal[
    "pending", "in_progress", "success", "failed", "abandoned"
]


class WebhookDeliveryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    whatsapp_number_id: UUID
    target_url: str
    event_type: str
    attempts: int
    max_attempts: int
    status: DeliveryStatus
    last_attempt_at: datetime | None
    next_retry_at: datetime | None
    completed_at: datetime | None
    response_status: int | None
    response_body_excerpt: str | None
    error_message: str | None
    created_at: datetime
    updated_at: datetime
