"""Media proxy: fetch decoded bytes from Evolution, cache on disk, serve.

Path: /app/media-cache/{message_id}.{ext}

We don't pre-fetch on webhook receipt; we lazy-fetch on first GET. The first
hit pays Evolution+disk latency; subsequent hits stream straight from disk.

Retention is intentionally simple — files just accumulate. Operators can
either: (a) run a periodic prune (e.g. `find /var/lib/docker/volumes/...
-mtime +30 -delete`) or (b) let it grow. Each media item is typically <2MB,
so 10k cached items ≈ ~20GB.
"""
import base64
import logging
import mimetypes
import os
from pathlib import Path
from uuid import UUID

from app.models.message import Message
from app.services.evolution import evolution_client


logger = logging.getLogger(__name__)

CACHE_DIR = Path(os.environ.get("MEDIA_CACHE_DIR", "/app/media-cache"))
CACHE_DIR.mkdir(parents=True, exist_ok=True)


_MIMETYPE_EXTENSION_OVERRIDES = {
    "image/jpeg": ".jpg",
    "audio/ogg; codecs=opus": ".ogg",
    "audio/ogg;codecs=opus": ".ogg",
    "audio/mpeg": ".mp3",
    "image/webp": ".webp",
    "video/mp4": ".mp4",
    "application/pdf": ".pdf",
}


def _ext_for_mimetype(mimetype: str | None) -> str:
    if not mimetype:
        return ".bin"
    base = mimetype.split(";", 1)[0].strip()
    if mimetype in _MIMETYPE_EXTENSION_OVERRIDES:
        return _MIMETYPE_EXTENSION_OVERRIDES[mimetype]
    if base in _MIMETYPE_EXTENSION_OVERRIDES:
        return _MIMETYPE_EXTENSION_OVERRIDES[base]
    guessed = mimetypes.guess_extension(base)
    return guessed or ".bin"


def _cache_path(message_id: UUID, mimetype: str | None) -> Path:
    return CACHE_DIR / f"{message_id}{_ext_for_mimetype(mimetype)}"


def get_cached(message: Message) -> tuple[Path, str] | None:
    """Return (path, mimetype) if we have the file on disk, else None."""
    mimetype = message.media_mimetype or "application/octet-stream"
    path = _cache_path(message.id, mimetype)
    if path.exists():
        return path, mimetype
    return None


async def fetch_and_cache(
    message: Message, instance_name: str
) -> tuple[Path, str] | None:
    """Pull the decoded bytes from Evolution, cache, return (path, mimetype).

    Returns None if Evolution rejects (e.g. expired media or non-media type).
    """
    raw = message.raw_payload or {}
    key = (raw.get("data") or {}).get("key") if isinstance(raw, dict) else None
    if not key:
        # Some installations store the key at the root.
        key = raw.get("key") if isinstance(raw, dict) else None
    if not key:
        logger.warning(
            "Cannot fetch media for %s: no message.key in raw_payload", message.id
        )
        return None

    response = await evolution_client.fetch_media_base64(instance_name, key)
    if not response or "base64" not in response:
        logger.warning(
            "Evolution returned no base64 for %s (response keys: %s)",
            message.id,
            list(response.keys()) if response else None,
        )
        return None

    b64 = response["base64"]
    mimetype = (
        response.get("mimetype")
        or message.media_mimetype
        or "application/octet-stream"
    )

    try:
        data = base64.b64decode(b64)
    except (TypeError, ValueError) as exc:
        logger.warning("Bad base64 for message %s: %s", message.id, exc)
        return None

    path = _cache_path(message.id, mimetype)
    path.write_bytes(data)
    logger.info(
        "Cached media for message %s (%s, %d bytes)",
        message.id,
        mimetype,
        len(data),
    )
    return path, mimetype
