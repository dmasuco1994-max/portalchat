"""Thin async wrapper around the Evolution API HTTP endpoints.

Stateless. Keep this layer dumb — orchestration (DB updates, retries) belongs
in services.whatsapp_number / services.webhook_inbound.
"""
from contextlib import asynccontextmanager
from typing import Any

import httpx

from app.core.config import settings


class EvolutionAPIError(Exception):
    def __init__(self, status_code: int, payload: Any):
        self.status_code = status_code
        self.payload = payload
        super().__init__(f"Evolution API error {status_code}: {payload}")


class EvolutionClient:
    def __init__(self, base_url: str, api_key: str, timeout: float = 30.0):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout

    @asynccontextmanager
    async def _client(self):
        async with httpx.AsyncClient(
            base_url=self.base_url,
            headers={"apikey": self.api_key, "Content-Type": "application/json"},
            timeout=self.timeout,
        ) as client:
            yield client

    async def _request(self, method: str, path: str, **kwargs: Any):
        async with self._client() as c:
            response = await c.request(method, path, **kwargs)
            try:
                payload = response.json()
            except ValueError:
                payload = {"raw": response.text}
            if response.status_code >= 400:
                raise EvolutionAPIError(response.status_code, payload)
            return payload

    # ---- Instance lifecycle ---------------------------------------------
    async def create_instance(self, instance_name: str) -> dict[str, Any]:
        body = {
            "instanceName": instance_name,
            "qrcode": True,
            "integration": "WHATSAPP-BAILEYS",
        }
        return await self._request("POST", "/instance/create", json=body)

    async def connect_instance(self, instance_name: str) -> dict[str, Any]:
        return await self._request("GET", f"/instance/connect/{instance_name}")

    async def connection_state(self, instance_name: str) -> dict[str, Any]:
        return await self._request(
            "GET", f"/instance/connectionState/{instance_name}"
        )

    async def logout_instance(self, instance_name: str) -> dict[str, Any]:
        return await self._request("DELETE", f"/instance/logout/{instance_name}")

    async def delete_instance(self, instance_name: str) -> dict[str, Any]:
        return await self._request("DELETE", f"/instance/delete/{instance_name}")

    async def fetch_profile_picture_url(
        self, instance_name: str, jid: str
    ) -> str | None:
        """Best-effort fetch of the contact's profile picture URL.

        Returns None if Evolution fails or the contact has no picture.
        Note: WhatsApp signs the returned URL with a short-lived token (a few
        hours to a few days). Callers should refetch periodically.
        """
        try:
            response = await self._request(
                "POST",
                f"/chat/fetchProfilePictureUrl/{instance_name}",
                json={"number": jid},
            )
        except EvolutionAPIError:
            return None
        if not isinstance(response, dict):
            return None
        url = response.get("profilePictureUrl") or response.get("url")
        return url if isinstance(url, str) and url.startswith("http") else None

    async def fetch_instance_info(self, instance_name: str) -> dict[str, Any] | None:
        """Returns Evolution's full record for an instance (incl. ownerJid).

        Unlike /instance/connectionState/, this endpoint exposes the connected
        WhatsApp account (ownerJid → phone digits + @s.whatsapp.net).
        """
        result = await self._request(
            "GET",
            "/instance/fetchInstances",
            params={"instanceName": instance_name},
        )
        if isinstance(result, list):
            return result[0] if result else None
        if isinstance(result, dict):
            return result
        return None

    # ---- Webhook configuration -----------------------------------------
    async def set_webhook(
        self,
        instance_name: str,
        url: str,
        events: list[str] | None = None,
    ) -> dict[str, Any]:
        """Configure Evolution to POST events to `url` for this instance."""
        body = {
            "webhook": {
                "enabled": True,
                "url": url,
                "webhookByEvents": False,
                "webhookBase64": True,
                "events": events
                or [
                    "MESSAGES_UPSERT",
                    "MESSAGES_UPDATE",
                    "CONNECTION_UPDATE",
                    "QRCODE_UPDATED",
                    "SEND_MESSAGE",
                ],
            }
        }
        return await self._request(
            "POST", f"/webhook/set/{instance_name}", json=body
        )

    # ---- Messaging ------------------------------------------------------
    async def send_text(
        self,
        instance_name: str,
        to_phone_digits: str,
        text: str,
    ) -> dict[str, Any]:
        body = {
            "number": to_phone_digits,
            "text": text,
        }
        return await self._request(
            "POST", f"/message/sendText/{instance_name}", json=body
        )

    async def send_media(
        self,
        instance_name: str,
        to_phone_digits: str,
        *,
        mediatype: str,  # "image" | "video" | "document"
        mimetype: str,
        media_base64: str,
        caption: str | None = None,
        file_name: str | None = None,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {
            "number": to_phone_digits,
            "mediatype": mediatype,
            "mimetype": mimetype,
            "media": media_base64,
        }
        if caption:
            body["caption"] = caption
        if file_name:
            body["fileName"] = file_name
        return await self._request(
            "POST", f"/message/sendMedia/{instance_name}", json=body
        )

    async def send_audio(
        self,
        instance_name: str,
        to_phone_digits: str,
        *,
        audio_base64: str,
    ) -> dict[str, Any]:
        """Send as a WhatsApp voice note (PTT)."""
        body = {
            "number": to_phone_digits,
            "audio": audio_base64,
        }
        return await self._request(
            "POST",
            f"/message/sendWhatsAppAudio/{instance_name}",
            json=body,
        )

    # ---- Media retrieval ------------------------------------------------
    async def fetch_media_base64(
        self,
        instance_name: str,
        message_key: dict[str, Any],
        *,
        convert_to_mp4: bool = False,
    ) -> dict[str, Any] | None:
        """Decrypt and return a media message's bytes.

        Evolution's endpoint returns `{base64, mimetype, fileName?}` on success.
        Returns None if Evolution rejects (e.g. message expired from its store).
        """
        try:
            return await self._request(
                "POST",
                f"/chat/getBase64FromMediaMessage/{instance_name}",
                json={
                    "message": {"key": message_key},
                    "convertToMp4": convert_to_mp4,
                },
            )
        except EvolutionAPIError:
            return None


evolution_client = EvolutionClient(
    base_url=settings.evolution_base_url,
    api_key=settings.evolution_api_key,
)


def map_state_to_status(raw_state: str | None) -> str:
    if raw_state == "open":
        return "connected"
    if raw_state in ("connecting", "qr"):
        return "connecting"
    if raw_state in ("close", "closed", "logout", "logged_out"):
        return "disconnected"
    return "created"
