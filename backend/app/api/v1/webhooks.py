"""Public webhook receiver — Evolution API posts events here.

NO bearer auth on this endpoint (Evolution doesn't carry one). Authentication
relies on:
  - the {instance_name} URL segment being a server-generated random id, AND
  - the request originating from inside the docker network in dev / from a
    trusted source in prod (use a firewall / reverse proxy ACL).

A future iteration could add a per-instance shared secret in a header.
"""
from typing import Any

from fastapi import APIRouter, HTTPException, status

from app.core.deps import ArqPool, DbSession
from app.services.webhook_inbound import handle_evolution_event
from app.services.whatsapp_number import get_number_by_instance


router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.post(
    "/evolution/{instance_name}",
    summary="Receive a webhook event from Evolution API for a given instance.",
)
async def receive_evolution_event(
    instance_name: str,
    payload: dict[str, Any],
    db: DbSession,
    arq_pool: ArqPool,
) -> dict[str, Any]:
    number = await get_number_by_instance(db, instance_name)
    if number is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Unknown instance",
        )
    summary = await handle_evolution_event(db, number, payload, arq_pool=arq_pool)
    return {"received": True, **summary}
